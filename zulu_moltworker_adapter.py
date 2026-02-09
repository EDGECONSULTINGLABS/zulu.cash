"""
zulu_moltworker_adapter.py
===========================
Adapter for Zulu → MoltWorker (OpenClaw on Cloudflare Workers) communication.

MoltWorker runs the full OpenClaw Gateway on Cloudflare Sandbox containers.
Communication happens via WebSocket (the Gateway's chat protocol).

This adapter:
1. Connects to MoltWorker's WebSocket endpoint
2. Authenticates with the gateway token
3. Translates Zulu OpenClawRequest → WebSocket chat messages
4. Collects streamed responses into OpenClawResponse
5. Maintains the same contract as ZuluOpenClawAdapter

DESIGN:
- Drop-in replacement for ZuluOpenClawAdapter.dispatch()
- Same OpenClawRequest/OpenClawResponse types
- Same audit logging contract
- WebSocket connection pooling with reconnect
- Timeout enforcement on the Zulu side (don't trust the worker)

USAGE:
    adapter = ZuluMoltWorkerAdapter(
        moltworker_url="https://your-worker.workers.dev",
        gateway_token="your-token",
    )
    response = await adapter.dispatch(request)
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Callable
from contextlib import asynccontextmanager

import aiohttp

from zulu_openclaw_adapter import (
    OpenClawRequest,
    OpenClawResponse,
    OpenClawTaskType,
    ScopedCredentials,
    ToolAllowlist,
    OpenClawError,
    OpenClawConnectionError,
    OpenClawTimeoutError,
    OpenClawRejectedError,
    OpenClawValidationError,
    CredentialExpiredError,
    ErrorCode,
    BoundedAuditLog,
)

log = logging.getLogger("zulu.moltworker_adapter")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
class MoltWorkerConfig:
    """Environment-based configuration for MoltWorker adapter."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def moltworker_url(self) -> str:
        """HTTPS URL of your MoltWorker deployment (e.g. https://your-worker.workers.dev)."""
        return os.getenv("MOLTWORKER_URL", "")

    @property
    def gateway_token(self) -> str:
        """MOLTBOT_GATEWAY_TOKEN — required for WebSocket auth."""
        return os.getenv("MOLTWORKER_GATEWAY_TOKEN", "")

    @property
    def max_retries(self) -> int:
        return int(os.getenv("MOLTWORKER_MAX_RETRIES", "2"))

    @property
    def retry_backoff_base(self) -> float:
        return float(os.getenv("MOLTWORKER_RETRY_BACKOFF", "2.0"))

    @property
    def connection_timeout(self) -> int:
        """Timeout for initial WebSocket connection (seconds)."""
        return int(os.getenv("MOLTWORKER_CONN_TIMEOUT", "30"))

    @property
    def response_timeout(self) -> int:
        """Max time to wait for a complete response (seconds)."""
        return int(os.getenv("MOLTWORKER_RESPONSE_TIMEOUT", "300"))

    @property
    def credential_max_age(self) -> int:
        return int(os.getenv("MOLTWORKER_CRED_TTL", "3600"))

    @property
    def audit_log_max_size(self) -> int:
        return int(os.getenv("MOLTWORKER_AUDIT_MAX_SIZE", "1000"))

    @property
    def cf_access_client_id(self) -> str:
        """Optional: Cloudflare Access Service Token client ID."""
        return os.getenv("CF_ACCESS_CLIENT_ID", "")

    @property
    def cf_access_client_secret(self) -> str:
        """Optional: Cloudflare Access Service Token client secret."""
        return os.getenv("CF_ACCESS_CLIENT_SECRET", "")


def get_moltworker_config() -> MoltWorkerConfig:
    return MoltWorkerConfig()


# ---------------------------------------------------------------------------
# WebSocket message types (OpenClaw Gateway protocol)
# ---------------------------------------------------------------------------
# The OpenClaw Gateway communicates via JSON messages over WebSocket.
# Key message types:
#   Client → Server:
#     { "type": "message", "content": "...", "conversationId": "..." }
#   Server → Client:
#     { "type": "message_start", "messageId": "..." }
#     { "type": "content_delta", "delta": "..." }
#     { "type": "message_end", "messageId": "..." }
#     { "type": "error", "error": { "message": "..." } }
#     { "type": "tool_use", "tool": "...", "input": {...} }
#     { "type": "tool_result", "result": "..." }

MSG_TYPE_MESSAGE = "message"
MSG_TYPE_MESSAGE_START = "message_start"
MSG_TYPE_CONTENT_DELTA = "content_delta"
MSG_TYPE_MESSAGE_END = "message_end"
MSG_TYPE_ERROR = "error"
MSG_TYPE_TOOL_USE = "tool_use"
MSG_TYPE_TOOL_RESULT = "tool_result"


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------
class ZuluMoltWorkerAdapter:
    """
    Production adapter for Zulu → MoltWorker (Cloudflare) communication.

    Implements the same dispatch() contract as ZuluOpenClawAdapter but
    communicates via WebSocket to the MoltWorker Gateway instead of
    HTTP POST to a local container.

    Features:
    - WebSocket connection with auto-reconnect
    - Gateway token + optional CF Access authentication
    - Streaming response collection
    - Timeout enforcement (Zulu-side, independent of worker)
    - Bounded audit log
    - Same OpenClawRequest/OpenClawResponse contract
    """

    def __init__(
        self,
        moltworker_url: str = None,
        gateway_token: str = None,
        max_retries: int = None,
        audit_flush_callback: Optional[Callable[[list[dict]], None]] = None,
    ):
        config = get_moltworker_config()
        self.url = (moltworker_url or config.moltworker_url).rstrip("/")
        self.gateway_token = gateway_token or config.gateway_token
        self.max_retries = max_retries if max_retries is not None else config.max_retries

        if not self.url:
            raise OpenClawValidationError(
                "MOLTWORKER_URL is required. Set it in .env or pass moltworker_url."
            )
        if not self.gateway_token:
            raise OpenClawValidationError(
                "MOLTWORKER_GATEWAY_TOKEN is required. Set it in .env or pass gateway_token."
            )

        self._session: Optional[aiohttp.ClientSession] = None
        self._session_lock = asyncio.Lock()

        self._audit_log = BoundedAuditLog(
            max_size=config.audit_log_max_size,
            on_flush=audit_flush_callback,
        )

    # --- Session management ---

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            async with self._session_lock:
                if self._session is None or self._session.closed:
                    config = get_moltworker_config()
                    timeout = aiohttp.ClientTimeout(
                        connect=config.connection_timeout,
                    )
                    headers = {}
                    # Add CF Access service token headers if configured
                    if config.cf_access_client_id and config.cf_access_client_secret:
                        headers["CF-Access-Client-Id"] = config.cf_access_client_id
                        headers["CF-Access-Client-Secret"] = config.cf_access_client_secret

                    self._session = aiohttp.ClientSession(
                        timeout=timeout,
                        headers=headers,
                    )
        return self._session

    async def close(self):
        async with self._session_lock:
            if self._session and not self._session.closed:
                await self._session.close()
                self._session = None

        if len(self._audit_log) > 0 and self._audit_log._on_flush is None:
            log.warning(
                f"Closing adapter with {len(self._audit_log)} audit entries "
                "but no flush callback configured — entries will be discarded"
            )
        self._audit_log.flush()

    @asynccontextmanager
    async def session_context(self):
        try:
            yield self
        finally:
            await self.close()

    # --- Audit ---

    def _audit(self, event: str, task_id: str, **kwargs):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "task_id": task_id,
            "backend": "moltworker",
            **kwargs,
        }
        self._audit_log.append(entry)
        log.info(f"AUDIT: {event} task={task_id} {kwargs}")

    def get_audit_log(self) -> list[dict]:
        return self._audit_log.get_all()

    def flush_audit_log(self) -> list[dict]:
        return self._audit_log.flush()

    # --- Health check ---

    async def ping(self) -> OpenClawResponse:
        """Check if MoltWorker is reachable and the container is running."""
        task_id = f"ping-{int(time.time())}"
        self._audit("ping_start", task_id)

        try:
            session = await self._get_session()
            config = get_moltworker_config()

            # Use the /api/status endpoint (public, no CF Access needed)
            # Convert https:// to http:// isn't needed — aiohttp handles both
            async with session.get(
                f"{self.url}/sandbox-health",
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 200:
                    self._audit("ping_success", task_id)
                    return OpenClawResponse(
                        task_id=task_id,
                        status="completed",
                        output={"pong": True, "backend": "moltworker", "http_status": 200},
                        elapsed_seconds=0.0,
                    )
                else:
                    body = await resp.text()
                    self._audit("ping_failed", task_id, status=resp.status)
                    return OpenClawResponse(
                        task_id=task_id,
                        status="error",
                        error=f"MoltWorker returned HTTP {resp.status}: {body[:200]}",
                    )
        except Exception as e:
            self._audit("ping_error", task_id, error=str(e))
            return OpenClawResponse(
                task_id=task_id,
                status="error",
                error=f"MoltWorker unreachable: {e}",
            )

    # --- Core dispatch ---

    async def dispatch(self, request: OpenClawRequest) -> OpenClawResponse:
        """
        Dispatch task to MoltWorker via WebSocket.

        Translates the OpenClawRequest into a chat message, sends it
        through the Gateway WebSocket, and collects the streamed response.
        """
        config = get_moltworker_config()

        # Validate credential TTL
        if request.credentials.is_expired(config.credential_max_age):
            self._audit("credential_expired", request.task_id)
            raise CredentialExpiredError(
                f"Credentials for task {request.task_id} have expired"
            )

        self._audit("dispatch_start", request.task_id,
                     task_type=request.task_type.value)

        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = await self._execute_via_websocket(request)

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

            except (aiohttp.ClientError, aiohttp.WSServerHandshakeError) as e:
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
                    f"Task {request.task_id} timed out after {request.timeout_seconds}s"
                )

    async def _execute_via_websocket(self, request: OpenClawRequest) -> OpenClawResponse:
        """
        Connect to MoltWorker WebSocket, send task as chat message,
        collect streamed response.
        """
        session = await self._get_session()
        config = get_moltworker_config()
        start_time = time.monotonic()

        # Build WebSocket URL with gateway token
        ws_scheme = "wss" if self.url.startswith("https") else "ws"
        base = self.url.replace("https://", "").replace("http://", "")
        ws_url = f"{ws_scheme}://{base}/?token={self.gateway_token}"

        # Build the task prompt with context
        prompt = self._build_prompt(request)

        # Use a conversation ID scoped to this task
        conversation_id = f"zulu-{request.task_id}"

        collected_content = []
        steps_taken = 0
        error_message = None
        error_code = None
        status = "completed"

        try:
            async with session.ws_connect(
                ws_url,
                timeout=config.connection_timeout,
                heartbeat=30,
            ) as ws:
                # Send the task as a chat message
                await ws.send_json({
                    "type": MSG_TYPE_MESSAGE,
                    "content": prompt,
                    "conversationId": conversation_id,
                })

                log.info(f"Task {request.task_id}: sent to MoltWorker via {ws_url[:60]}..., awaiting response...")

                # Collect response with timeout
                deadline = time.monotonic() + request.timeout_seconds
                message_complete = False

                async for msg in ws:
                    # Check timeout
                    if time.monotonic() > deadline:
                        status = "timeout"
                        error_message = f"Task exceeded {request.timeout_seconds}s limit"
                        break

                    log.info(f"Task {request.task_id}: ws msg type={msg.type}, data={str(msg.data)[:200]}")

                    if msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            data = json.loads(msg.data)
                        except json.JSONDecodeError:
                            # Non-JSON message, treat as raw content
                            collected_content.append(msg.data)
                            continue

                        msg_type = data.get("type", "")

                        if msg_type == MSG_TYPE_CONTENT_DELTA:
                            delta = data.get("delta", "")
                            collected_content.append(delta)

                        elif msg_type == MSG_TYPE_MESSAGE_END:
                            message_complete = True
                            break

                        elif msg_type == MSG_TYPE_TOOL_USE:
                            steps_taken += 1
                            log.debug(
                                f"Task {request.task_id}: tool_use "
                                f"tool={data.get('tool')} step={steps_taken}"
                            )

                        elif msg_type == MSG_TYPE_TOOL_RESULT:
                            # Tool completed, content may follow
                            pass

                        elif msg_type == MSG_TYPE_ERROR:
                            err = data.get("error", {})
                            error_message = err.get("message", str(err))
                            status = "error"
                            error_code = self._categorize_error(error_message)
                            break

                        elif msg_type == MSG_TYPE_MESSAGE_START:
                            # Response starting, reset content
                            pass

                        else:
                            # Unknown message type — log but don't fail
                            log.debug(
                                f"Task {request.task_id}: unknown ws msg type: {msg_type}"
                            )

                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        error_message = f"WebSocket error: {ws.exception()}"
                        status = "error"
                        break

                    elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSING, aiohttp.WSMsgType.CLOSED):
                        log.warning(f"Task {request.task_id}: ws closed, complete={message_complete}, content_len={len(collected_content)}, close_code={getattr(ws, 'close_code', None)}")
                        if not message_complete and not collected_content:
                            error_message = "WebSocket closed before response"
                            status = "error"
                        break

                elapsed = time.monotonic() - start_time
                full_content = "".join(collected_content)

                return OpenClawResponse(
                    task_id=request.task_id,
                    status=status,
                    output={"content": full_content, "backend": "moltworker"} if status == "completed" else None,
                    error=error_message,
                    error_code=error_code,
                    steps_taken=steps_taken,
                    elapsed_seconds=round(elapsed, 2),
                    completed_at=datetime.now(timezone.utc).isoformat() if status == "completed" else None,
                )

        except aiohttp.WSServerHandshakeError as e:
            elapsed = time.monotonic() - start_time
            log.error(f"Task {request.task_id}: WebSocket handshake failed: {e}")
            raise
        except asyncio.TimeoutError:
            raise
        except Exception as e:
            elapsed = time.monotonic() - start_time
            log.error(f"Task {request.task_id}: unexpected error: {e}")
            return OpenClawResponse(
                task_id=request.task_id,
                status="error",
                error=str(e),
                error_code=ErrorCode.INTERNAL_ERROR.value,
                elapsed_seconds=round(elapsed, 2),
            )

    def _build_prompt(self, request: OpenClawRequest) -> str:
        """
        Build a structured prompt from the OpenClawRequest.

        Translates Zulu's task metadata into natural language instructions
        that OpenClaw's agent can understand and execute.
        """
        parts = []

        # Task type instruction
        type_instructions = {
            OpenClawTaskType.WEB_RESEARCH: "Research the following topic thoroughly using web search. Cite your sources.",
            OpenClawTaskType.DOCUMENT_SYNTHESIS: "Synthesize the following information into a well-structured document.",
            OpenClawTaskType.COMPARATIVE_ANALYSIS: "Perform a detailed comparative analysis of the following.",
            OpenClawTaskType.REPORT_DRAFTING: "Draft a professional report on the following topic.",
            OpenClawTaskType.CODE_REVIEW: "Review the following code and provide detailed feedback.",
            OpenClawTaskType.DATA_EXTRACTION: "Extract structured data from the following sources.",
        }

        instruction = type_instructions.get(request.task_type, "")
        if instruction:
            parts.append(f"[Task: {request.task_type.value}]\n{instruction}\n")

        # Domain constraints
        if request.domain_allowlist:
            domains = ", ".join(request.domain_allowlist)
            parts.append(f"[Allowed domains: {domains}]")

        # The actual prompt
        parts.append(request.prompt)

        # Context
        if request.context:
            parts.append(f"\n[Additional context: {json.dumps(request.context)}]")

        # Output schema hint
        if request.output_schema:
            parts.append(
                f"\n[Please structure your response as JSON matching this schema: "
                f"{json.dumps(request.output_schema)}]"
            )

        return "\n\n".join(parts)

    def _categorize_error(self, error: str) -> str:
        """Categorize error message into structured error code."""
        error_lower = error.lower()
        if "timeout" in error_lower:
            return ErrorCode.TIMEOUT.value
        if "rate limit" in error_lower:
            return ErrorCode.RATE_LIMITED.value
        if "unauthorized" in error_lower or "token" in error_lower:
            return ErrorCode.AUTH_FAILED.value
        if "pairing" in error_lower:
            return ErrorCode.AUTH_FAILED.value
        if "domain" in error_lower:
            return ErrorCode.DOMAIN_BLOCKED.value
        return ErrorCode.UNKNOWN.value

    # --- Convenience methods (same interface as ZuluOpenClawAdapter) ---

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
