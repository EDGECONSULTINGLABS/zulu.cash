"""
Zulu → Clawd Task Contract
============================
Defines the task dispatch interface between Zulu (control plane)
and Clawd (executor).

SECURITY MODEL:
- Zulu creates a TaskRequest with scoped credentials
- Credentials are one-time, per-task, and expire with the task
- Clawd receives the task, executes, and returns TaskResponse
- Clawd NEVER persists credentials or task data

USAGE (from Zulu core):
    from task_contract import TaskDispatcher

    dispatcher = TaskDispatcher(clawd_url="http://clawd-runner:8080")
    result = await dispatcher.dispatch(
        task_type="web_fetch",
        params={"url": "https://example.com"},
        scoped_credentials={"auth_header": "Bearer <one-time-token>"},
        timeout_seconds=30
    )
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

import aiohttp

log = logging.getLogger("zulu.task_contract")


# ---------------------------------------------------------------------------
# Task types — exhaustive list of what Clawd is allowed to do
# ---------------------------------------------------------------------------
class TaskType(str, Enum):
    WEB_FETCH = "web_fetch"
    SUMMARIZE = "summarize"
    TRANSFORM = "transform"
    CODE_EXEC = "code_exec"  # Disabled by default
    PING = "ping"
    # NightShift OpenClaw task types
    WEB_RESEARCH = "web_research"
    DOCUMENT_SYNTHESIS = "document_synthesis"
    COMPARATIVE_ANALYSIS = "comparative_analysis"
    REPORT_DRAFTING = "report_drafting"
    CODE_REVIEW = "code_review"
    DATA_EXTRACTION = "data_extraction"


class TaskStatus(str, Enum):
    PENDING = "pending"
    DISPATCHED = "dispatched"
    COMPLETED = "completed"
    TIMEOUT = "timeout"
    ERROR = "error"
    REJECTED = "rejected"


# ---------------------------------------------------------------------------
# Task request — what Zulu sends to Clawd
# ---------------------------------------------------------------------------
@dataclass
class TaskRequest:
    task_type: TaskType
    params: dict = field(default_factory=dict)
    scoped_credentials: dict = field(default_factory=dict)
    timeout_seconds: int = 300
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    callback_url: Optional[str] = None

    def to_payload(self) -> dict:
        """Serialize for HTTP dispatch."""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "params": self.params,
            "scoped_credentials": self.scoped_credentials,
            "timeout_seconds": self.timeout_seconds,
            "callback_url": self.callback_url
        }


# ---------------------------------------------------------------------------
# Task response — what Clawd returns to Zulu
# ---------------------------------------------------------------------------
@dataclass
class TaskResponse:
    task_id: str
    status: TaskStatus
    result: Optional[dict] = None
    error: Optional[str] = None
    elapsed_seconds: float = 0.0
    completed_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "TaskResponse":
        return cls(
            task_id=data.get("task_id", "unknown"),
            status=TaskStatus(data.get("status", "error")),
            result=data.get("result"),
            error=data.get("error"),
            elapsed_seconds=data.get("elapsed_seconds", 0.0),
            completed_at=data.get("completed_at")
        )


# ---------------------------------------------------------------------------
# Policy engine — validates tasks before dispatch
# ---------------------------------------------------------------------------
class TaskPolicy:
    """Validates that a task is allowed before sending to Clawd."""

    # Tasks that are allowed by default
    ALLOWED_TYPES = {
        TaskType.WEB_FETCH,
        TaskType.SUMMARIZE,
        TaskType.TRANSFORM,
        TaskType.PING,
        # NightShift OpenClaw tasks
        TaskType.WEB_RESEARCH,
        TaskType.DOCUMENT_SYNTHESIS,
        TaskType.COMPARATIVE_ANALYSIS,
        TaskType.REPORT_DRAFTING,
        TaskType.CODE_REVIEW,
        TaskType.DATA_EXTRACTION,
    }

    # Maximum timeout per task type
    MAX_TIMEOUTS = {
        TaskType.WEB_FETCH: 60,
        TaskType.SUMMARIZE: 120,
        TaskType.TRANSFORM: 60,
        TaskType.CODE_EXEC: 0,   # Disabled
        TaskType.PING: 10,
        # NightShift tasks get longer timeouts (overnight work)
        TaskType.WEB_RESEARCH: 300,
        TaskType.DOCUMENT_SYNTHESIS: 300,
        TaskType.COMPARATIVE_ANALYSIS: 300,
        TaskType.REPORT_DRAFTING: 300,
        TaskType.CODE_REVIEW: 120,
        TaskType.DATA_EXTRACTION: 120,
    }

    # Which executor handles each task type
    EXECUTOR_ROUTING = {
        TaskType.WEB_FETCH: "clawd",
        TaskType.SUMMARIZE: "clawd",
        TaskType.TRANSFORM: "clawd",
        TaskType.PING: "clawd",
        TaskType.WEB_RESEARCH: "openclaw-nightshift",
        TaskType.DOCUMENT_SYNTHESIS: "openclaw-nightshift",
        TaskType.COMPARATIVE_ANALYSIS: "openclaw-nightshift",
        TaskType.REPORT_DRAFTING: "openclaw-nightshift",
        TaskType.CODE_REVIEW: "openclaw-nightshift",
        TaskType.DATA_EXTRACTION: "openclaw-nightshift",
    }

    # URL allowlist for web_fetch
    ALLOWED_DOMAINS = [
        "api.github.com",
        "raw.githubusercontent.com",
        "arxiv.org",
        "api.coingecko.com",
        # Add more as needed
    ]

    @classmethod
    def validate(cls, task: TaskRequest) -> tuple[bool, str]:
        """
        Returns (is_valid, reason).
        Zulu calls this BEFORE dispatching to Clawd.
        """

        # Check task type is allowed
        if task.task_type not in cls.ALLOWED_TYPES:
            return False, f"Task type '{task.task_type}' is not permitted"

        # Check timeout is within bounds
        max_timeout = cls.MAX_TIMEOUTS.get(task.task_type, 0)
        if max_timeout == 0:
            return False, f"Task type '{task.task_type}' is disabled"
        if task.timeout_seconds > max_timeout:
            return False, (
                f"Timeout {task.timeout_seconds}s exceeds max "
                f"{max_timeout}s for {task.task_type}"
            )

        # Check URL allowlist for web_fetch
        if task.task_type == TaskType.WEB_FETCH:
            url = task.params.get("url", "")
            if not any(domain in url for domain in cls.ALLOWED_DOMAINS):
                return False, f"URL domain not in allowlist: {url}"

        return True, "ok"


# ---------------------------------------------------------------------------
# Task dispatcher — Zulu's interface to Clawd
# ---------------------------------------------------------------------------
class TaskDispatcher:
    """
    Dispatches validated tasks from Zulu to the correct executor.
    Routes to clawd-runner OR openclaw-nightshift based on task type.
    """

    EXECUTOR_URLS = {
        "clawd": "http://clawd-runner:8080",
        "openclaw-nightshift": "http://openclaw-nightshift:8090",
    }

    def __init__(self, max_retries: int = 1):
        self.max_retries = max_retries
        self._audit_log: list[dict] = []

    def _get_executor_url(self, task_type: TaskType) -> str:
        """Route task to the correct executor."""
        executor = TaskPolicy.EXECUTOR_ROUTING.get(task_type, "clawd")
        return self.EXECUTOR_URLS.get(executor, self.EXECUTOR_URLS["clawd"])

    async def dispatch(self, task_type: TaskType, params: dict,
                       scoped_credentials: dict = None,
                       timeout_seconds: int = 60,
                       prompt: str = None) -> TaskResponse:
        """
        Validate, route, dispatch, and return result.
        This is the ONLY way Zulu talks to executors.
        """

        task = TaskRequest(
            task_type=task_type,
            params=params,
            scoped_credentials=scoped_credentials or {},
            timeout_seconds=timeout_seconds
        )

        # --- Policy check ---
        is_valid, reason = TaskPolicy.validate(task)
        if not is_valid:
            log.warning(f"Task {task.task_id} REJECTED: {reason}")
            self._audit("task_rejected", task.task_id, reason=reason)
            return TaskResponse(
                task_id=task.task_id,
                status=TaskStatus.REJECTED,
                error=reason
            )

        # --- Route to correct executor ---
        executor_url = self._get_executor_url(task_type)
        executor_name = TaskPolicy.EXECUTOR_ROUTING.get(task_type, "clawd")

        self._audit("task_dispatched", task.task_id,
                     task_type=task_type.value,
                     executor=executor_name)

        # Build payload — OpenClaw NightShift uses a different schema
        if executor_name == "openclaw-nightshift":
            payload = {
                "task_id": task.task_id,
                "task_type": task.task_type.value,
                "prompt": prompt or params.get("prompt", ""),
                "output_schema": params.get("output_schema"),
                "scoped_credentials": task.scoped_credentials,
                "timeout_ms": timeout_seconds * 1000,
            }
        else:
            payload = task.to_payload()

        for attempt in range(1, self.max_retries + 1):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{executor_url}/task",
                        json=payload,
                        timeout=aiohttp.ClientTimeout(
                            total=timeout_seconds + 10
                        )
                    ) as resp:
                        data = await resp.json()
                        response = TaskResponse.from_dict(data)

                        self._audit(
                            "task_completed", task.task_id,
                            status=response.status.value,
                            elapsed=response.elapsed_seconds,
                            executor=executor_name
                        )
                        return response

            except asyncio.TimeoutError:
                log.error(
                    f"Task {task.task_id} — dispatch timeout "
                    f"(attempt {attempt}/{self.max_retries})"
                )
                if attempt == self.max_retries:
                    self._audit("task_timeout", task.task_id,
                                executor=executor_name)
                    return TaskResponse(
                        task_id=task.task_id,
                        status=TaskStatus.TIMEOUT,
                        error="Dispatch timeout"
                    )

            except Exception as e:
                log.error(f"Task {task.task_id} — dispatch error: {e}")
                if attempt == self.max_retries:
                    self._audit("task_error", task.task_id, error=str(e),
                                executor=executor_name)
                    return TaskResponse(
                        task_id=task.task_id,
                        status=TaskStatus.ERROR,
                        error=str(e)
                    )

    def _audit(self, event: str, task_id: str, **kwargs):
        """Internal audit log. Zulu writes these to persistent storage."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "task_id": task_id,
            **kwargs
        }
        self._audit_log.append(entry)
        log.info(f"AUDIT: {json.dumps(entry)}")

    def get_audit_log(self) -> list[dict]:
        """Return audit entries for Zulu to persist."""
        return list(self._audit_log)

    def flush_audit_log(self) -> list[dict]:
        """Return and clear audit entries."""
        entries = list(self._audit_log)
        self._audit_log.clear()
        return entries
