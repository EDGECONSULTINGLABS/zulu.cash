"""
OpenClaw NightShift Worker — Constrained Executor
===================================================
OpenClaw as a RUNTIME, not an AUTHORITY.

SECURITY MODEL:
- Boots, receives ONE task, executes within constraints, returns output, exits
- No persistent memory
- No autonomous planning loops
- No self-reflection / self-prompting
- No task spawning
- Zulu owns the leash

WHAT THIS STRIPS FROM FULL OPENCLAW:
- Autonomous planning loops → DISABLED
- Persistent memory modules → DISABLED
- Self-reflection / self-prompting → DISABLED
- Task spawning / chaining → DISABLED
- REPL mode → DISABLED
- Background workers → DISABLED

WHAT REMAINS:
- Single-shot task execution
- Tool use (within allowlist)
- Web research (within domain allowlist)
- Document synthesis
- Structured output generation
"""

import asyncio
import json
import logging
import os
import shutil
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Optional

from aiohttp import web
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Configuration (from environment — API keys passed per-task, NOT here)
# ---------------------------------------------------------------------------
LISTEN_PORT = int(os.getenv("OPENCLAW_LISTEN_PORT", "8081"))
MAX_TASK_DURATION = int(os.getenv("OPENCLAW_MAX_TASK_DURATION", "600"))
MAX_STEPS = int(os.getenv("OPENCLAW_MAX_STEPS", "10"))
WORKSPACE = os.getenv("OPENCLAW_WORKSPACE", "/app/workspace")
OUTPUT_DIR = os.getenv("OPENCLAW_OUTPUT_DIR", "/app/output")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [OPENCLAW] %(levelname)s %(message)s"
)
log = logging.getLogger("openclaw-worker")


# ---------------------------------------------------------------------------
# Task specification — what Zulu sends
# ---------------------------------------------------------------------------
class ToolAllowlist(BaseModel):
    """Explicit list of tools OpenClaw is allowed to use for this task."""
    web_browse: bool = False
    web_fetch: bool = False
    document_read: bool = False
    document_write: bool = False
    llm_chat: bool = False
    code_analyze: bool = False


class TaskSpec(BaseModel):
    """
    The ONLY input OpenClaw receives. Zulu defines everything.
    OpenClaw cannot modify this or spawn sub-tasks.
    """
    task_id: str
    task_type: str  # web_research, doc_synthesis, comparative_analysis, etc.
    
    # The fixed prompt — OpenClaw executes this, doesn't modify it
    prompt: str
    
    # Constraints — OpenClaw cannot exceed these
    tool_allowlist: ToolAllowlist = Field(default_factory=ToolAllowlist)
    domain_allowlist: list[str] = Field(default_factory=list)
    max_steps: int = 10
    timeout_seconds: int = 300
    
    # Expected output schema (JSON Schema)
    output_schema: Optional[dict] = None
    
    # Per-task credentials (short-lived, scoped)
    credentials: dict = Field(default_factory=dict)
    
    # Context from Zulu (read-only)
    context: dict = Field(default_factory=dict)


class TaskResult(BaseModel):
    """Structured output returned to Zulu."""
    task_id: str
    status: str  # completed, timeout, error, rejected
    output: Optional[dict] = None
    error: Optional[str] = None
    steps_taken: int = 0
    elapsed_seconds: float = 0.0
    completed_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Constrained executor — the core of the worker
# ---------------------------------------------------------------------------
class ConstrainedExecutor:
    """
    Executes tasks within strict constraints.
    
    KEY INVARIANTS:
    - Cannot spawn sub-tasks
    - Cannot modify its own prompt
    - Cannot exceed step limit
    - Cannot access domains outside allowlist
    - Cannot use tools outside allowlist
    - Cannot persist anything
    """
    
    def __init__(self, spec: TaskSpec):
        self.spec = spec
        self.steps_taken = 0
        self.start_time = None
        
    async def execute(self) -> TaskResult:
        """Single-shot execution. Returns result. Dies."""
        self.start_time = time.monotonic()
        
        try:
            result = await asyncio.wait_for(
                self._run_task(),
                timeout=self.spec.timeout_seconds
            )
            
            elapsed = time.monotonic() - self.start_time
            return TaskResult(
                task_id=self.spec.task_id,
                status="completed",
                output=result,
                steps_taken=self.steps_taken,
                elapsed_seconds=round(elapsed, 2),
                completed_at=datetime.now(timezone.utc).isoformat()
            )
            
        except asyncio.TimeoutError:
            elapsed = time.monotonic() - self.start_time
            log.warning(f"Task {self.spec.task_id} — TIMEOUT after {elapsed:.2f}s")
            return TaskResult(
                task_id=self.spec.task_id,
                status="timeout",
                error=f"Task exceeded {self.spec.timeout_seconds}s limit",
                steps_taken=self.steps_taken,
                elapsed_seconds=round(elapsed, 2)
            )
            
        except Exception as e:
            elapsed = time.monotonic() - self.start_time
            log.error(f"Task {self.spec.task_id} — ERROR: {e}")
            return TaskResult(
                task_id=self.spec.task_id,
                status="error",
                error=str(e),
                steps_taken=self.steps_taken,
                elapsed_seconds=round(elapsed, 2)
            )
    
    async def _run_task(self) -> dict:
        """Route to appropriate handler based on task type."""
        handlers = {
            "web_research": self._handle_web_research,
            "doc_synthesis": self._handle_doc_synthesis,
            "comparative_analysis": self._handle_comparative_analysis,
            "structured_report": self._handle_structured_report,
            "code_review": self._handle_code_review,
            "ping": self._handle_ping,
        }
        
        handler = handlers.get(self.spec.task_type)
        if not handler:
            raise ValueError(f"Unknown task type: {self.spec.task_type}")
        
        return await handler()
    
    def _check_step_limit(self):
        """Enforce step limit. Raises if exceeded."""
        self.steps_taken += 1
        if self.steps_taken > self.spec.max_steps:
            raise RuntimeError(
                f"Step limit exceeded: {self.steps_taken} > {self.spec.max_steps}"
            )
    
    def _check_domain(self, url: str) -> bool:
        """Check if URL is in domain allowlist."""
        if not self.spec.domain_allowlist:
            return False  # No allowlist = no access
        return any(domain in url for domain in self.spec.domain_allowlist)
    
    def _check_tool(self, tool: str) -> bool:
        """Check if tool is allowed."""
        allowlist = self.spec.tool_allowlist
        tool_map = {
            "web_browse": allowlist.web_browse,
            "web_fetch": allowlist.web_fetch,
            "document_read": allowlist.document_read,
            "document_write": allowlist.document_write,
            "llm_chat": allowlist.llm_chat,
            "code_analyze": allowlist.code_analyze,
        }
        return tool_map.get(tool, False)
    
    # -----------------------------------------------------------------------
    # Task handlers — each is constrained and stateless
    # -----------------------------------------------------------------------
    async def _handle_web_research(self) -> dict:
        """
        Multi-step web research within domain allowlist.
        Returns structured findings.
        """
        if not self._check_tool("web_fetch"):
            return {"error": "web_fetch not allowed for this task"}
        
        self._check_step_limit()
        
        # Extract URLs from context or prompt
        urls = self.spec.context.get("urls", [])
        results = []
        
        for url in urls[:5]:  # Hard cap on URLs per task
            if not self._check_domain(url):
                results.append({"url": url, "error": "domain not in allowlist"})
                continue
            
            self._check_step_limit()
            content = await self._fetch_url(url)
            results.append({"url": url, "content": content})
        
        # If LLM is allowed, synthesize
        if self._check_tool("llm_chat") and self.spec.credentials.get("llm_api_key"):
            self._check_step_limit()
            synthesis = await self._llm_synthesize(
                self.spec.prompt,
                results
            )
            return {"sources": results, "synthesis": synthesis}
        
        return {"sources": results, "synthesis": None}
    
    async def _handle_doc_synthesis(self) -> dict:
        """
        Synthesize multiple documents into structured output.
        """
        if not self._check_tool("document_read"):
            return {"error": "document_read not allowed for this task"}
        
        self._check_step_limit()
        
        documents = self.spec.context.get("documents", [])
        processed = []
        
        for doc in documents[:10]:  # Hard cap
            self._check_step_limit()
            # Documents are passed as content, not file paths (no host FS access)
            processed.append({
                "title": doc.get("title", "untitled"),
                "content": doc.get("content", "")[:10000]  # Truncate
            })
        
        if self._check_tool("llm_chat") and self.spec.credentials.get("llm_api_key"):
            self._check_step_limit()
            synthesis = await self._llm_synthesize(
                self.spec.prompt,
                processed
            )
            return {"documents": len(processed), "synthesis": synthesis}
        
        return {"documents": processed, "synthesis": None}
    
    async def _handle_comparative_analysis(self) -> dict:
        """
        Compare multiple items according to criteria in prompt.
        """
        self._check_step_limit()
        
        items = self.spec.context.get("items", [])
        criteria = self.spec.context.get("criteria", [])
        
        if self._check_tool("llm_chat") and self.spec.credentials.get("llm_api_key"):
            self._check_step_limit()
            analysis = await self._llm_analyze(
                self.spec.prompt,
                {"items": items, "criteria": criteria}
            )
            return {"analysis": analysis}
        
        return {"items": items, "criteria": criteria, "analysis": None}
    
    async def _handle_structured_report(self) -> dict:
        """
        Generate a structured report according to output schema.
        """
        self._check_step_limit()
        
        if not self.spec.output_schema:
            return {"error": "No output_schema provided for structured_report"}
        
        if self._check_tool("llm_chat") and self.spec.credentials.get("llm_api_key"):
            self._check_step_limit()
            report = await self._llm_structured_output(
                self.spec.prompt,
                self.spec.context,
                self.spec.output_schema
            )
            return {"report": report}
        
        return {"error": "llm_chat required for structured_report"}
    
    async def _handle_code_review(self) -> dict:
        """
        Review code snippets (passed in context, not from filesystem).
        """
        if not self._check_tool("code_analyze"):
            return {"error": "code_analyze not allowed for this task"}
        
        self._check_step_limit()
        
        code_snippets = self.spec.context.get("code", [])
        
        if self._check_tool("llm_chat") and self.spec.credentials.get("llm_api_key"):
            self._check_step_limit()
            review = await self._llm_analyze(
                self.spec.prompt,
                {"code": code_snippets}
            )
            return {"review": review}
        
        return {"code_snippets": len(code_snippets), "review": None}
    
    async def _handle_ping(self) -> dict:
        """Health check."""
        return {
            "pong": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "task_id": self.spec.task_id
        }
    
    # -----------------------------------------------------------------------
    # Tool implementations — all constrained
    # -----------------------------------------------------------------------
    async def _fetch_url(self, url: str) -> str:
        """Fetch URL content. Domain must be in allowlist."""
        import httpx
        
        if not self._check_domain(url):
            raise PermissionError(f"Domain not in allowlist: {url}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text[:20000]  # Truncate
    
    async def _llm_synthesize(self, prompt: str, sources: list) -> str:
        """Call LLM to synthesize sources. API key from per-task credentials."""
        api_key = self.spec.credentials.get("llm_api_key")
        provider = self.spec.credentials.get("llm_provider", "anthropic")
        
        if not api_key:
            return "No LLM API key provided"
        
        system_prompt = (
            "You are a research assistant. Synthesize the provided sources "
            "according to the user's prompt. Be concise and factual."
        )
        
        user_content = f"{prompt}\n\nSources:\n{json.dumps(sources, indent=2)}"
        
        if provider == "anthropic":
            return await self._call_anthropic(api_key, system_prompt, user_content)
        elif provider == "openai":
            return await self._call_openai(api_key, system_prompt, user_content)
        else:
            return f"Unknown LLM provider: {provider}"
    
    async def _llm_analyze(self, prompt: str, data: dict) -> str:
        """Call LLM to analyze data."""
        api_key = self.spec.credentials.get("llm_api_key")
        provider = self.spec.credentials.get("llm_provider", "anthropic")
        
        if not api_key:
            return "No LLM API key provided"
        
        system_prompt = (
            "You are an analyst. Analyze the provided data according to "
            "the user's prompt. Be thorough but concise."
        )
        
        user_content = f"{prompt}\n\nData:\n{json.dumps(data, indent=2)}"
        
        if provider == "anthropic":
            return await self._call_anthropic(api_key, system_prompt, user_content)
        elif provider == "openai":
            return await self._call_openai(api_key, system_prompt, user_content)
        else:
            return f"Unknown LLM provider: {provider}"
    
    async def _llm_structured_output(self, prompt: str, context: dict,
                                      schema: dict) -> dict:
        """Call LLM to generate structured output matching schema."""
        api_key = self.spec.credentials.get("llm_api_key")
        provider = self.spec.credentials.get("llm_provider", "anthropic")
        
        if not api_key:
            return {"error": "No LLM API key provided"}
        
        system_prompt = (
            "You are a report generator. Generate output that strictly matches "
            f"the following JSON schema:\n{json.dumps(schema, indent=2)}\n\n"
            "Return ONLY valid JSON, no explanation."
        )
        
        user_content = f"{prompt}\n\nContext:\n{json.dumps(context, indent=2)}"
        
        if provider == "anthropic":
            result = await self._call_anthropic(api_key, system_prompt, user_content)
        elif provider == "openai":
            result = await self._call_openai(api_key, system_prompt, user_content)
        else:
            return {"error": f"Unknown LLM provider: {provider}"}
        
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"raw_output": result, "parse_error": "Failed to parse as JSON"}
    
    async def _call_anthropic(self, api_key: str, system: str,
                               user_content: str) -> str:
        """Call Anthropic Claude API."""
        import anthropic
        
        client = anthropic.AsyncAnthropic(api_key=api_key)
        
        message = await client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user_content}]
        )
        
        return message.content[0].text
    
    async def _call_openai(self, api_key: str, system: str,
                            user_content: str) -> str:
        """Call OpenAI API."""
        import openai
        
        client = openai.AsyncOpenAI(api_key=api_key)
        
        response = await client.chat.completions.create(
            model="gpt-4-turbo-preview",
            max_tokens=4096,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content}
            ]
        )
        
        return response.choices[0].message.content


# ---------------------------------------------------------------------------
# Workspace cleanup — called after EVERY task
# ---------------------------------------------------------------------------
def clean_workspace():
    """Wipe the workspace directory. OpenClaw remembers nothing."""
    try:
        for dir_path in [WORKSPACE, OUTPUT_DIR]:
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path)
                os.makedirs(dir_path, exist_ok=True)
        log.info("Workspace cleaned")
    except Exception as e:
        log.warning(f"Workspace cleanup failed: {e}")


# ---------------------------------------------------------------------------
# HTTP server — single entrypoint
# ---------------------------------------------------------------------------
async def handle_task(request: web.Request) -> web.Response:
    """POST /task — receive and execute a scoped task."""
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    
    # Parse and validate task spec
    try:
        spec = TaskSpec(**payload)
    except Exception as e:
        return web.json_response(
            {"error": f"Invalid task spec: {e}"}, status=400
        )
    
    log.info(f"Task {spec.task_id} ({spec.task_type}) — received")
    
    # Execute with constraints
    executor = ConstrainedExecutor(spec)
    result = await executor.execute()
    
    # ALWAYS clean workspace after task
    clean_workspace()
    
    log.info(
        f"Task {spec.task_id} — {result.status} "
        f"({result.steps_taken} steps, {result.elapsed_seconds}s)"
    )
    
    status_code = 200 if result.status == "completed" else 500
    if result.status == "timeout":
        status_code = 408
    
    return web.json_response(result.model_dump(), status=status_code)


async def handle_health(request: web.Request) -> web.Response:
    """GET /health — liveness check."""
    return web.json_response({
        "status": "healthy",
        "service": "openclaw-worker",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "max_task_duration": MAX_TASK_DURATION,
        "max_steps": MAX_STEPS
    })


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_post("/task", handle_task)
    app.router.add_get("/health", handle_health)
    return app


if __name__ == "__main__":
    log.info(f"OpenClaw NightShift Worker starting on port {LISTEN_PORT}")
    log.info(f"Max task duration: {MAX_TASK_DURATION}s")
    log.info(f"Max steps per task: {MAX_STEPS}")
    log.info(f"Workspace: {WORKSPACE}")
    log.info("=" * 60)
    log.info("CONSTRAINTS ACTIVE:")
    log.info("  - No autonomous planning loops")
    log.info("  - No persistent memory")
    log.info("  - No task spawning")
    log.info("  - Single-shot execution only")
    log.info("  - Zulu owns the leash")
    log.info("=" * 60)
    web.run_app(create_app(), host="0.0.0.0", port=LISTEN_PORT)
