"""
Clawd Runner — Scoped Task Executor
====================================
Receives tasks from Zulu control plane.
Executes within resource/time constraints.
Returns results. Dies and forgets.

SECURITY PROPERTIES:
- No filesystem access beyond /app/workspace (tmpfs)
- No secrets access
- No persistent state
- Task timeout enforced locally + by watchdog
- All outputs returned via HTTP response (not written to disk)
"""

import asyncio
import json
import logging
import os
import signal
import time
import traceback
from datetime import datetime, timezone

from aiohttp import web

# ---------------------------------------------------------------------------
# Configuration (from environment — no secrets here)
# ---------------------------------------------------------------------------
LISTEN_PORT = int(os.getenv("CLAWD_LISTEN_PORT", "8080"))
MAX_TASK_DURATION = int(os.getenv("CLAWD_MAX_TASK_DURATION", "300"))
MAX_MEMORY_MB = int(os.getenv("CLAWD_MAX_MEMORY_MB", "1024"))
WORKSPACE = os.getenv("CLAWD_WORKSPACE", "/app/workspace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [CLAWD] %(levelname)s %(message)s"
)
log = logging.getLogger("clawd-runner")


# ---------------------------------------------------------------------------
# Task execution with timeout
# ---------------------------------------------------------------------------
async def execute_task(task_payload: dict) -> dict:
    """
    Execute a scoped task from Zulu.

    task_payload schema:
    {
        "task_id": "uuid",
        "task_type": "web_fetch | summarize | transform | code_exec",
        "params": { ... },
        "scoped_credentials": { ... },  # One-time, task-specific only
        "timeout_seconds": 300,
        "callback_url": null  # Optional async callback
    }
    """
    task_id = task_payload.get("task_id", "unknown")
    task_type = task_payload.get("task_type", "unknown")
    timeout = min(
        task_payload.get("timeout_seconds", MAX_TASK_DURATION),
        MAX_TASK_DURATION  # Never exceed global max
    )

    log.info(f"Task {task_id} ({task_type}) — started, timeout={timeout}s")
    start_time = time.monotonic()

    try:
        result = await asyncio.wait_for(
            _dispatch_task(task_type, task_payload.get("params", {}),
                           task_payload.get("scoped_credentials", {})),
            timeout=timeout
        )

        elapsed = time.monotonic() - start_time
        log.info(f"Task {task_id} — completed in {elapsed:.2f}s")

        return {
            "task_id": task_id,
            "status": "completed",
            "result": result,
            "elapsed_seconds": round(elapsed, 2),
            "completed_at": datetime.now(timezone.utc).isoformat()
        }

    except asyncio.TimeoutError:
        elapsed = time.monotonic() - start_time
        log.warning(f"Task {task_id} — KILLED after {elapsed:.2f}s (timeout)")
        return {
            "task_id": task_id,
            "status": "timeout",
            "error": f"Task exceeded {timeout}s limit",
            "elapsed_seconds": round(elapsed, 2)
        }

    except Exception as e:
        elapsed = time.monotonic() - start_time
        log.error(f"Task {task_id} — FAILED: {e}")
        return {
            "task_id": task_id,
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "elapsed_seconds": round(elapsed, 2)
        }
    finally:
        # CLEANUP: Wipe workspace after every task
        _clean_workspace()


async def _dispatch_task(task_type: str, params: dict,
                         credentials: dict) -> dict:
    """Route task to the appropriate handler."""

    handlers = {
        "web_fetch": _handle_web_fetch,
        "summarize": _handle_summarize,
        "transform": _handle_transform,
        "code_exec": _handle_code_exec,
        "ping": _handle_ping,
    }

    handler = handlers.get(task_type)
    if not handler:
        raise ValueError(f"Unknown task type: {task_type}")

    return await handler(params, credentials)


# ---------------------------------------------------------------------------
# Task handlers — each is scoped and stateless
# ---------------------------------------------------------------------------
async def _handle_web_fetch(params: dict, credentials: dict) -> dict:
    """Fetch a URL and return content. Credentials are per-request."""
    import aiohttp

    url = params.get("url")
    if not url:
        raise ValueError("Missing 'url' in params")

    headers = {}
    if credentials.get("auth_header"):
        headers["Authorization"] = credentials["auth_header"]

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, timeout=30) as resp:
            text = await resp.text()
            return {
                "url": url,
                "status_code": resp.status,
                "content_length": len(text),
                "content": text[:10000]  # Truncate — Clawd doesn't need full pages
            }


async def _handle_summarize(params: dict, credentials: dict) -> dict:
    """Summarize text. Does NOT call LLM directly — returns structured data
    for Zulu to process through Ollama on the internal network."""
    text = params.get("text", "")
    max_length = params.get("max_length", 500)

    # Clawd does basic preprocessing; Zulu handles LLM inference
    return {
        "preprocessed_text": text[:5000],
        "char_count": len(text),
        "needs_llm": True,
        "suggested_prompt": f"Summarize in {max_length} chars"
    }


async def _handle_transform(params: dict, credentials: dict) -> dict:
    """Transform data according to spec. Pure function, no side effects."""
    data = params.get("data")
    transform_type = params.get("transform_type", "identity")

    if transform_type == "json_extract":
        keys = params.get("keys", [])
        if isinstance(data, dict):
            return {"extracted": {k: data.get(k) for k in keys}}

    return {"data": data, "transform": "identity"}


async def _handle_code_exec(params: dict, credentials: dict) -> dict:
    """Execute sandboxed code snippet. EXTREMELY restricted."""
    # In production, this should use a further-sandboxed runtime
    # (e.g., gVisor, Firecracker, or WASM)
    return {
        "status": "rejected",
        "reason": "code_exec requires additional sandboxing — not enabled"
    }


async def _handle_ping(params: dict, credentials: dict) -> dict:
    """Health/connectivity test."""
    return {"pong": True, "timestamp": datetime.now(timezone.utc).isoformat()}


# ---------------------------------------------------------------------------
# Workspace cleanup — called after EVERY task
# ---------------------------------------------------------------------------
def _clean_workspace():
    """Wipe the workspace directory. Clawd remembers nothing."""
    import shutil
    try:
        if os.path.exists(WORKSPACE):
            shutil.rmtree(WORKSPACE)
            os.makedirs(WORKSPACE, exist_ok=True)
        log.info("Workspace cleaned")
    except Exception as e:
        log.warning(f"Workspace cleanup failed: {e}")


# ---------------------------------------------------------------------------
# HTTP server
# ---------------------------------------------------------------------------
async def handle_task(request: web.Request) -> web.Response:
    """POST /task — receive and execute a scoped task."""
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return web.json_response(
            {"error": "Invalid JSON"}, status=400
        )

    # Validate required fields
    if "task_id" not in payload or "task_type" not in payload:
        return web.json_response(
            {"error": "Missing task_id or task_type"}, status=400
        )

    result = await execute_task(payload)

    status_code = 200 if result["status"] == "completed" else 500
    if result["status"] == "timeout":
        status_code = 408

    return web.json_response(result, status=status_code)


async def handle_health(request: web.Request) -> web.Response:
    """GET /health — liveness check."""
    return web.json_response({
        "status": "healthy",
        "service": "clawd-runner",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "max_task_duration": MAX_TASK_DURATION,
        "workspace": WORKSPACE
    })


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_post("/task", handle_task)
    app.router.add_get("/health", handle_health)
    return app


if __name__ == "__main__":
    log.info(f"Clawd Runner starting on port {LISTEN_PORT}")
    log.info(f"Max task duration: {MAX_TASK_DURATION}s")
    log.info(f"Max memory: {MAX_MEMORY_MB}MB")
    log.info(f"Workspace: {WORKSPACE}")
    web.run_app(create_app(), host="0.0.0.0", port=LISTEN_PORT)
