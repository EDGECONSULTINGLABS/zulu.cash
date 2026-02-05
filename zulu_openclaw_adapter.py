"""
zulu_openclaw_adapter.py
========================
Production-ready adapter for Zulu → OpenClaw NightShift communication.

v2 fixes:
- None prompt handling
- Lazy config loading for testability
- Bounded audit log with auto-flush
- ScopedCredentials.extra collision guard
- asyncio.Lock for session init
- Structured error codes preferred over string matching
- Clean list formatting in convenience methods
"""

import asyncio
import logging
import os
import re
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Callable
from contextlib import asynccontextmanager

import aiohttp

log = logging.getLogger("zulu.openclaw_adapter")


# ---------------------------------------------------------------------------
# Configuration (lazy-loaded for testability)
# ---------------------------------------------------------------------------
class AdapterConfig:
    """
    Environment-based configuration with lazy loading.
    Reads env vars on access, not import — safe for test fixtures.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @property
    def openclaw_url(self) -> str:
        return os.getenv("OPENCLAW_URL", "http://openclaw-nightshift:8090")
    
    @property
    def max_retries(self) -> int:
        return int(os.getenv("OPENCLAW_MAX_RETRIES", "3"))
    
    @property
    def retry_backoff_base(self) -> float:
        return float(os.getenv("OPENCLAW_RETRY_BACKOFF", "1.0"))
    
    @property
    def connection_timeout(self) -> int:
        return int(os.getenv("OPENCLAW_CONN_TIMEOUT", "10"))
    
    @property
    def pool_size(self) -> int:
        return int(os.getenv("OPENCLAW_POOL_SIZE", "10"))
    
    @property
    def credential_max_age(self) -> int:
        return int(os.getenv("OPENCLAW_CRED_TTL", "3600"))
    
    @property
    def audit_log_max_size(self) -> int:
        return int(os.getenv("OPENCLAW_AUDIT_MAX_SIZE", "1000"))


def get_config() -> AdapterConfig:
    """Factory for config singleton."""
    return AdapterConfig()


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------
class OpenClawError(Exception):
    """Base exception for OpenClaw adapter errors."""
    pass


class OpenClawConnectionError(OpenClawError):
    """Failed to connect to OpenClaw service."""
    pass


class OpenClawTimeoutError(OpenClawError):
    """Task execution timed out."""
    pass


class OpenClawRejectedError(OpenClawError):
    """OpenClaw rejected the task (policy violation)."""
    def __init__(self, reason: str, task_id: str, error_code: str = None):
        self.reason = reason
        self.task_id = task_id
        self.error_code = error_code
        super().__init__(f"Task {task_id} rejected: {reason}")


class OpenClawValidationError(OpenClawError):
    """Request validation failed before dispatch."""
    pass


class CredentialExpiredError(OpenClawError):
    """Scoped credentials have expired."""
    pass


# ---------------------------------------------------------------------------
# Structured error codes (preferred over string matching)
# ---------------------------------------------------------------------------
class ErrorCode(str, Enum):
    """Canonical error codes — OpenClaw should return these directly."""
    TIMEOUT = "TIMEOUT"
    RATE_LIMITED = "RATE_LIMITED"
    AUTH_FAILED = "AUTH_FAILED"
    DOMAIN_BLOCKED = "DOMAIN_BLOCKED"
    TOOL_BLOCKED = "TOOL_BLOCKED"
    STEP_LIMIT = "STEP_LIMIT"
    INVALID_TASK = "INVALID_TASK"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    UNKNOWN = "UNKNOWN"


# ---------------------------------------------------------------------------
# Task types
# ---------------------------------------------------------------------------
class OpenClawTaskType(str, Enum):
    WEB_RESEARCH = "web_research"
    DOCUMENT_SYNTHESIS = "document_synthesis"
    COMPARATIVE_ANALYSIS = "comparative_analysis"
    REPORT_DRAFTING = "report_drafting"
    CODE_REVIEW = "code_review"
    DATA_EXTRACTION = "data_extraction"
    PING = "ping"


# ---------------------------------------------------------------------------
# Tool allowlist
# ---------------------------------------------------------------------------
@dataclass
class ToolAllowlist:
    """Explicit tool permissions for this task."""
    web_browse: bool = False
    web_fetch: bool = False
    document_read: bool = False
    document_write: bool = False
    llm_chat: bool = True
    code_analyze: bool = False

    def to_dict(self) -> dict:
        return {
            "web_browse": self.web_browse,
            "web_fetch": self.web_fetch,
            "document_read": self.document_read,
            "document_write": self.document_write,
            "llm_chat": self.llm_chat,
            "code_analyze": self.code_analyze,
        }


# ---------------------------------------------------------------------------
# Scoped credentials with lifecycle + collision guard
# ---------------------------------------------------------------------------
# Reserved keys that cannot appear in extra dict
_RESERVED_CREDENTIAL_KEYS = frozenset({"llm_api_key", "llm_provider", "issued_at"})


@dataclass
class ScopedCredentials:
    """
    Short-lived, per-task credentials.
    
    Lifecycle:
    1. Created by Zulu with issued_at timestamp
    2. Validated by adapter before dispatch (TTL check)
    3. Passed to OpenClaw in request
    4. Never persisted by OpenClaw
    5. Expire after CREDENTIAL_MAX_AGE seconds
    """
    llm_api_key: Optional[str] = None
    llm_provider: str = "anthropic"
    issued_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    extra: dict = field(default_factory=dict)

    def __post_init__(self):
        # Guard against key collisions in extra
        collisions = set(self.extra.keys()) & _RESERVED_CREDENTIAL_KEYS
        if collisions:
            raise ValueError(
                f"ScopedCredentials.extra cannot contain reserved keys: {collisions}"
            )

    def is_expired(self, max_age_seconds: int = 3600) -> bool:
        """Check if credentials have exceeded TTL."""
        try:
            issued = datetime.fromisoformat(self.issued_at.replace('Z', '+00:00'))
            age = (datetime.now(timezone.utc) - issued).total_seconds()
            return age > max_age_seconds
        except (ValueError, AttributeError):
            return True  # Invalid timestamp = expired

    def to_dict(self) -> dict:
        # Namespace extra under 'extra' key to prevent collisions
        return {
            "llm_api_key": self.llm_api_key,
            "llm_provider": self.llm_provider,
            "issued_at": self.issued_at,
            "extra": self.extra,  # Namespaced, not spread
        }


# ---------------------------------------------------------------------------
# Request with validation
# ---------------------------------------------------------------------------
@dataclass
class OpenClawRequest:
    """Validated request to OpenClaw."""
    task_id: str
    task_type: OpenClawTaskType
    prompt: str  # Can be empty string for PING, but not None
    tool_allowlist: ToolAllowlist = field(default_factory=ToolAllowlist)
    domain_allowlist: list[str] = field(default_factory=list)
    max_steps: int = 5
    timeout_seconds: int = 300
    output_schema: Optional[dict] = None
    credentials: ScopedCredentials = field(default_factory=ScopedCredentials)
    context: dict = field(default_factory=dict)

    def __post_init__(self):
        """Normalize fields, then validate."""
        self._normalize()
        self._validate()

    def _normalize(self):
        """
        Normalize fields before validation.
        Separated from validation for clarity and frozen-dataclass compatibility.
        """
        # Normalize None prompt to empty string for PING tasks
        if self.prompt is None and self.task_type == OpenClawTaskType.PING:
            object.__setattr__(self, 'prompt', "")

    def _validate(self):
        """Input validation (runs after normalization)."""
        errors = []
        
        # task_id: non-empty, safe characters
        if not self.task_id or not re.match(r'^[\w\-\.]+$', self.task_id):
            errors.append("task_id must be non-empty alphanumeric with -._")
        
        # prompt: must be string after normalization
        if self.prompt is None:
            errors.append("prompt cannot be None for non-ping tasks")
        elif not self.prompt and self.task_type != OpenClawTaskType.PING:
            # Empty string only allowed for PING
            errors.append("prompt required for non-ping tasks")
        elif len(self.prompt) > 100_000:
            errors.append("prompt exceeds 100k character limit")
        
        # domain_allowlist: valid domain patterns
        for domain in self.domain_allowlist:
            if not re.match(r'^[\w\.\-\*]+$', domain):
                errors.append(f"invalid domain pattern: {domain}")
        
        # max_steps: reasonable bounds
        if not 1 <= self.max_steps <= 50:
            errors.append("max_steps must be 1-50")
        
        # timeout: reasonable bounds
        if not 5 <= self.timeout_seconds <= 3600:
            errors.append("timeout_seconds must be 5-3600")
        
        if errors:
            raise OpenClawValidationError("; ".join(errors))

    def to_payload(self) -> dict:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "prompt": self.prompt,
            "tool_allowlist": self.tool_allowlist.to_dict(),
            "domain_allowlist": self.domain_allowlist,
            "max_steps": self.max_steps,
            "timeout_seconds": self.timeout_seconds,
            "output_schema": self.output_schema,
            "credentials": self.credentials.to_dict(),
            "context": self.context,
        }


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------
@dataclass
class OpenClawResponse:
    """Structured response from OpenClaw."""
    task_id: str
    status: str  # completed, timeout, error, rejected
    output: Optional[dict] = None
    error: Optional[str] = None
    error_code: Optional[str] = None  # Structured error code from OpenClaw
    steps_taken: int = 0
    elapsed_seconds: float = 0.0
    completed_at: Optional[str] = None

    @property
    def succeeded(self) -> bool:
        return self.status == "completed"

    @property
    def was_rejected(self) -> bool:
        return self.status == "rejected"


# ---------------------------------------------------------------------------
# Bounded audit log
# ---------------------------------------------------------------------------
class BoundedAuditLog:
    """
    Fixed-size audit log with optional flush callback.
    Prevents unbounded memory growth in long-running processes.
    """
    
    def __init__(
        self, 
        max_size: int = 1000,
        on_flush: Optional[Callable[[list[dict]], None]] = None
    ):
        self._entries: deque[dict] = deque(maxlen=max_size)
        self._on_flush = on_flush
        self._overflow_count = 0
    
    def append(self, entry: dict):
        if len(self._entries) == self._entries.maxlen:
            self._overflow_count += 1
        self._entries.append(entry)
    
    def get_all(self) -> list[dict]:
        return list(self._entries)
    
    def flush(self) -> list[dict]:
        """Return and clear entries. Calls on_flush callback if set."""
        entries = list(self._entries)
        if self._on_flush and entries:
            self._on_flush(entries)
        self._entries.clear()
        overflow = self._overflow_count
        self._overflow_count = 0
        if overflow > 0:
            log.warning(f"Audit log overflow: {overflow} entries dropped before flush")
        return entries
    
    def __len__(self) -> int:
        return len(self._entries)


# ---------------------------------------------------------------------------
# Adapter with connection pooling, retry, and thread-safe session init
# ---------------------------------------------------------------------------
class ZuluOpenClawAdapter:
    """
    Production adapter for Zulu → OpenClaw communication.
    
    Features:
    - Connection pooling (reusable session)
    - Thread-safe session initialization
    - Exponential backoff retry
    - Credential TTL validation
    - Bounded audit log
    - Structured error handling
    """

    def __init__(
        self,
        openclaw_url: str = None,
        max_retries: int = None,
        pool_size: int = None,
        audit_flush_callback: Optional[Callable[[list[dict]], None]] = None,
    ):
        config = get_config()
        self.url = openclaw_url or config.openclaw_url
        self.max_retries = max_retries or config.max_retries
        self.pool_size = pool_size or config.pool_size
        
        self._session: Optional[aiohttp.ClientSession] = None
        # Lock for session init - safe for single-threaded asyncio event loop.
        # NOTE: Must instantiate adapter inside async context (not at module level)
        # to avoid RuntimeError in Python 3.10+ from lock bound to wrong loop.
        self._session_lock = asyncio.Lock()
        
        self._audit_log = BoundedAuditLog(
            max_size=config.audit_log_max_size,
            on_flush=audit_flush_callback,
        )

    async def _get_session(self) -> aiohttp.ClientSession:
        """
        Lazy-init connection pool with lock for concurrent safety.
        
        Note: Double-check pattern is safe for single-threaded asyncio (no preemption
        between outer check and lock acquisition). Not thread-safe for run_in_executor.
        """
        if self._session is None or self._session.closed:
            async with self._session_lock:
                # Double-check after acquiring lock (handles concurrent awaits)
                if self._session is None or self._session.closed:
                    config = get_config()
                    connector = aiohttp.TCPConnector(
                        limit=self.pool_size,
                        limit_per_host=self.pool_size,
                    )
                    timeout = aiohttp.ClientTimeout(
                        connect=config.connection_timeout
                    )
                    self._session = aiohttp.ClientSession(
                        connector=connector,
                        timeout=timeout,
                    )
        return self._session

    async def close(self):
        """Close connection pool and flush audit log."""
        async with self._session_lock:
            if self._session and not self._session.closed:
                await self._session.close()
                self._session = None
        
        # Warn if audit entries will be discarded (no flush callback)
        if len(self._audit_log) > 0 and self._audit_log._on_flush is None:
            log.warning(
                f"Closing adapter with {len(self._audit_log)} audit entries "
                "but no flush callback configured — entries will be discarded"
            )
        self._audit_log.flush()

    @asynccontextmanager
    async def session_context(self):
        """Context manager for session lifecycle."""
        try:
            yield self
        finally:
            await self.close()

    def _audit(self, event: str, task_id: str, **kwargs):
        """Internal audit logging."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "task_id": task_id,
            **kwargs,
        }
        self._audit_log.append(entry)
        log.info(f"AUDIT: {event} task={task_id} {kwargs}")

    async def dispatch(self, request: OpenClawRequest) -> OpenClawResponse:
        """
        Dispatch task to OpenClaw with retry logic.
        
        Raises:
            CredentialExpiredError: If credentials exceed TTL
            OpenClawConnectionError: If all retries fail
            OpenClawTimeoutError: If task times out
            OpenClawRejectedError: If OpenClaw rejects the task
        """
        config = get_config()
        
        # Validate credential TTL
        if request.credentials.is_expired(config.credential_max_age):
            self._audit("credential_expired", request.task_id)
            raise CredentialExpiredError(
                f"Credentials for task {request.task_id} have expired"
            )

        payload = request.to_payload()
        self._audit("dispatch_start", request.task_id, 
                    task_type=request.task_type.value)

        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = await self._send_request(request, payload)
                
                # Handle rejection
                if response.was_rejected:
                    self._audit("task_rejected", request.task_id, 
                                reason=response.error,
                                error_code=response.error_code)
                    raise OpenClawRejectedError(
                        response.error or "Unknown rejection",
                        request.task_id,
                        response.error_code,
                    )
                
                self._audit("dispatch_complete", request.task_id,
                            status=response.status,
                            steps=response.steps_taken,
                            elapsed=response.elapsed_seconds)
                return response

            except aiohttp.ClientError as e:
                last_error = e
                self._audit("dispatch_retry", request.task_id,
                            attempt=attempt, error=str(e))
                
                if attempt < self.max_retries:
                    backoff = config.retry_backoff_base * (2 ** (attempt - 1))
                    await asyncio.sleep(backoff)
                    continue
                
                raise OpenClawConnectionError(
                    f"Failed after {self.max_retries} attempts: {e}"
                ) from e

            except asyncio.TimeoutError:
                self._audit("dispatch_timeout", request.task_id)
                raise OpenClawTimeoutError(
                    f"Task {request.task_id} timed out"
                )

    async def _send_request(
        self, request: OpenClawRequest, payload: dict
    ) -> OpenClawResponse:
        """Send HTTP request to OpenClaw."""
        session = await self._get_session()
        
        async with session.post(
            f"{self.url}/task",
            json=payload,
            timeout=aiohttp.ClientTimeout(
                total=request.timeout_seconds + 30
            )
        ) as resp:
            # Check HTTP status before parsing - raises ClientResponseError on 4xx/5xx
            # which dispatch() catches and retries via the ClientError handler
            resp.raise_for_status()
            data = await resp.json()
            
            # Prefer structured error_code from OpenClaw, fallback to string matching
            error_code = data.get("error_code")
            if not error_code and data.get("error"):
                error_code = self._categorize_error_fallback(data["error"])
            
            return OpenClawResponse(
                task_id=data.get("task_id", request.task_id),
                status=data.get("status", "error"),
                output=data.get("output"),
                error=data.get("error"),
                error_code=error_code,
                steps_taken=data.get("steps_taken", 0),
                elapsed_seconds=data.get("elapsed_seconds", 0.0),
                completed_at=data.get("completed_at"),
            )

    def _categorize_error_fallback(self, error: str) -> str:
        """
        Fallback error categorization via string matching.
        Only used when OpenClaw doesn't return structured error_code.
        """
        error_lower = error.lower()
        if "timeout" in error_lower:
            return ErrorCode.TIMEOUT.value
        if "rate limit" in error_lower:
            return ErrorCode.RATE_LIMITED.value
        if "unauthorized" in error_lower or "api key" in error_lower:
            return ErrorCode.AUTH_FAILED.value
        if "domain" in error_lower and "allowlist" in error_lower:
            return ErrorCode.DOMAIN_BLOCKED.value
        if "tool" in error_lower and "allowlist" in error_lower:
            return ErrorCode.TOOL_BLOCKED.value
        if "step" in error_lower and "limit" in error_lower:
            return ErrorCode.STEP_LIMIT.value
        return ErrorCode.UNKNOWN.value

    def get_audit_log(self) -> list[dict]:
        """Return audit entries (does not clear)."""
        return self._audit_log.get_all()

    def flush_audit_log(self) -> list[dict]:
        """Return and clear audit entries, triggering flush callback."""
        return self._audit_log.flush()

    # --- Convenience methods ---

    async def web_research(
        self, task_id: str, prompt: str, domains: list[str],
        credentials: ScopedCredentials, timeout: int = 300
    ) -> OpenClawResponse:
        return await self.dispatch(OpenClawRequest(
            task_id=task_id,
            task_type=OpenClawTaskType.WEB_RESEARCH,
            prompt=prompt,
            tool_allowlist=ToolAllowlist(web_browse=True, web_fetch=True, llm_chat=True),
            domain_allowlist=domains,
            credentials=credentials,
            timeout_seconds=timeout,
        ))

    async def comparative_analysis(
        self, task_id: str, items: list[str], criteria: list[str],
        credentials: ScopedCredentials, timeout: int = 120
    ) -> OpenClawResponse:
        # Clean list formatting for natural language prompt
        items_str = ", ".join(str(item) for item in items)
        criteria_str = ", ".join(str(c) for c in criteria)
        prompt = f"Compare the following items: {items_str}. Evaluate against these criteria: {criteria_str}."
        
        return await self.dispatch(OpenClawRequest(
            task_id=task_id,
            task_type=OpenClawTaskType.COMPARATIVE_ANALYSIS,
            prompt=prompt,
            tool_allowlist=ToolAllowlist(llm_chat=True),
            domain_allowlist=[],
            credentials=credentials,
            context={"items": items, "criteria": criteria},
            timeout_seconds=timeout,
        ))

    async def ping(self) -> OpenClawResponse:
        """
        Health check ping.
        Note: Empty prompt is valid for PING task type — validation permits this.
        """
        return await self.dispatch(OpenClawRequest(
            task_id=f"ping-{int(time.time())}",
            task_type=OpenClawTaskType.PING,
            prompt="",  # Explicitly empty, not None
            max_steps=1,
            timeout_seconds=10,
        ))
