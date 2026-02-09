"""
zulu_task_planner.py
====================
Task planning and decomposition layer for Zulu.

Takes natural language requests and decomposes them into concrete OpenClaw task graphs.
This is where Zulu's intelligence lives — between user intent and executor dispatch.

RESPONSIBILITIES:
- Parse natural language into structured intent
- Decompose complex requests into task DAGs
- Handle ambiguity (clarification vs. best-effort)
- Chain results between dependent tasks
- Aggregate final results for user delivery

DESIGN PRINCIPLES:
- Uses model provider abstraction (Anthropic default, others optional)
- Per-role model selection (intent/planning/extraction)
- Planning credentials separate from execution credentials
- Ambiguity threshold is configurable — ask vs. attempt

EXAMPLE FLOW:
    User: "Research my competitors in the EV charging space and draft a one-pager"
    
    Planner decomposes to:
    1. web_research: "EV charging market competitors" → research_results
    2. document_synthesis: "one-pager from {research_results}" → final_doc
    
    Planner returns TaskGraph with dependencies.
    Executor runs tasks in order, passing outputs forward.

USAGE:
    from zulu_task_planner import ZuluTaskPlanner
    from zulu_model_provider import get_provider, ModelConfig
    from zulu_openclaw_adapter import ScopedCredentials
    
    # Planning uses your Anthropic key
    provider = get_provider()
    model_config = ModelConfig.from_env()
    
    # Execution uses scoped credentials (may be different)
    exec_credentials = ScopedCredentials(...)
    
    planner = ZuluTaskPlanner(
        provider=provider,
        model_config=model_config,
        execution_credentials=exec_credentials,
    )
    
    result = await planner.plan_and_execute("Research competitors and draft a one-pager")
"""

import asyncio
import json
import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Any, Callable

from zulu_model_provider import ModelProvider, ModelConfig, get_provider
from zulu_openclaw_adapter import (
    ZuluOpenClawAdapter,
    OpenClawRequest,
    OpenClawResponse,
    OpenClawTaskType,
    ScopedCredentials,
    ToolAllowlist,
    OpenClawError,
)

# MoltWorker adapter — same dispatch() contract, different backend
try:
    from zulu_moltworker_adapter import ZuluMoltWorkerAdapter
except ImportError:
    ZuluMoltWorkerAdapter = None  # Optional dependency

# Union type for any adapter that implements dispatch()
AdapterType = ZuluOpenClawAdapter  # Base type; MoltWorker is duck-type compatible
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [ZULU-PLANNER] %(levelname)s %(message)s"
)
log = logging.getLogger("zulu.planner")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
@dataclass
class PlannerConfig:
    """Planner behavior configuration."""
    
    ambiguity_threshold: float = 0.4
    max_tasks_per_request: int = 5
    default_timeout_seconds: int = 300
    max_retries_per_task: int = 2
    
    @classmethod
    def from_env(cls) -> "PlannerConfig":
        return cls(
            ambiguity_threshold=float(os.getenv("ZULU_AMBIGUITY_THRESHOLD", "0.6")),
            max_tasks_per_request=int(os.getenv("ZULU_MAX_TASKS_PER_REQUEST", "5")),
            default_timeout_seconds=int(os.getenv("ZULU_DEFAULT_TASK_TIMEOUT", "300")),
            max_retries_per_task=int(os.getenv("ZULU_MAX_RETRIES_PER_TASK", "2")),
        )


# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------
class IntentType(str, Enum):
    """High-level intent categories."""
    RESEARCH = "research"
    SYNTHESIZE = "synthesize"
    ANALYZE = "analyze"
    DRAFT = "draft"
    REVIEW = "review"
    EXTRACT = "extract"
    CLARIFY = "clarify"
    CHITCHAT = "chitchat"
    UNKNOWN = "unknown"


@dataclass
class ParsedIntent:
    """Structured representation of user intent."""
    intent_type: IntentType
    confidence: float
    subject: str
    deliverable: Optional[str] = None
    constraints: list[str] = field(default_factory=list)
    context: dict = field(default_factory=dict)
    raw_input: str = ""
    needs_clarification: bool = False
    clarification_question: Optional[str] = None


# ---------------------------------------------------------------------------
# Task graph
# ---------------------------------------------------------------------------
@dataclass
class PlannedTask:
    """A single task in the execution plan."""
    task_id: str
    task_type: OpenClawTaskType
    prompt: str
    depends_on: list[str] = field(default_factory=list)
    tool_allowlist: ToolAllowlist = field(default_factory=ToolAllowlist)
    domain_allowlist: list[str] = field(default_factory=list)
    timeout_seconds: int = 300
    context: dict = field(default_factory=dict)
    
    status: str = "pending"
    result: Optional[dict] = None
    error: Optional[str] = None


@dataclass
class TaskGraph:
    """DAG of tasks to execute."""
    request_id: str
    tasks: list[PlannedTask]
    original_input: str
    parsed_intent: ParsedIntent
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def get_ready_tasks(self) -> list[PlannedTask]:
        """Get tasks whose dependencies are all completed."""
        completed_ids = {t.task_id for t in self.tasks if t.status == "completed"}
        return [
            t for t in self.tasks
            if t.status == "pending" and all(dep in completed_ids for dep in t.depends_on)
        ]
    
    def is_complete(self) -> bool:
        """Check if all tasks are done."""
        return all(t.status in ("completed", "failed") for t in self.tasks)
    
    def has_runnable_tasks(self) -> bool:
        """Check if there are tasks that can still run (not blocked by failed deps)."""
        if self.is_complete():
            return False
        completed_ids = {t.task_id for t in self.tasks if t.status == "completed"}
        failed_ids = {t.task_id for t in self.tasks if t.status == "failed"}
        for task in self.tasks:
            if task.status == "pending":
                # Task is runnable if all deps are completed (not failed)
                deps_satisfied = all(dep in completed_ids for dep in task.depends_on)
                deps_failed = any(dep in failed_ids for dep in task.depends_on)
                if deps_satisfied and not deps_failed:
                    return True
        return False
    
    def get_final_results(self) -> dict:
        """Aggregate results from all completed tasks."""
        return {
            task.task_id: task.result
            for task in self.tasks
            if task.status == "completed" and task.result
        }


# ---------------------------------------------------------------------------
# Planner response types
# ---------------------------------------------------------------------------
@dataclass
class PlannerResult:
    """Result of planning operation."""
    success: bool
    task_graph: Optional[TaskGraph] = None
    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    error: Optional[str] = None
    is_chitchat: bool = False
    chitchat_response: Optional[str] = None


@dataclass
class ExecutionResult:
    """Result of executing a task graph."""
    request_id: str
    success: bool
    tasks_completed: int
    tasks_failed: int
    results: dict
    errors: dict
    summary: str
    elapsed_seconds: float
    task_graph: Optional[TaskGraph] = None


# ---------------------------------------------------------------------------
# Intent parser
# ---------------------------------------------------------------------------
class IntentParser:
    """Parses natural language into structured intent."""
    
    SYSTEM_PROMPT = """You are Zulu's intent parser. Analyze user messages and extract structured intent.

Given a user message, respond with JSON:
{
    "intent_type": one of ["research", "synthesize", "analyze", "draft", "review", "extract", "clarify", "chitchat", "unknown"],
    "confidence": float 0.0-1.0,
    "subject": what the task is about,
    "deliverable": what user expects back (or null),
    "constraints": list of constraints mentioned,
    "needs_clarification": boolean,
    "clarification_question": question to ask if needs_clarification is true
}

RULES:
1. If the request references content that wasn't provided (code to review, documents to analyze, data to extract from), set needs_clarification to true and ask for the missing content.
2. If the message is malformed, empty, or genuinely unparseable, return {"intent_type": "unknown", "confidence": 0.0, "subject": "", "needs_clarification": true, "clarification_question": "I couldn't understand that. Could you rephrase?"}.
3. If the request is vague but you can make a reasonable guess, set confidence lower (0.4-0.6) rather than asking for clarification.
4. IMPORTANT: If the message describes criteria, preferences, or constraints for finding/researching something, treat it as a RESEARCH request, NOT chitchat. Statements like "romantic dinner downtown" or "escape rooms for couples" are research requests.
5. Only classify as "chitchat" for pure greetings, small talk, or off-topic conversation. When in doubt, classify as "research".

Examples:

User: "Research my competitors in the EV charging space and draft a one-pager"
{"intent_type": "research", "confidence": 0.9, "subject": "competitors in EV charging market", "deliverable": "one-pager document", "constraints": ["EV charging industry"], "needs_clarification": false, "clarification_question": null}

User: "Can you help me with something?"
{"intent_type": "clarify", "confidence": 0.3, "subject": "unknown", "deliverable": null, "constraints": [], "needs_clarification": true, "clarification_question": "I'd be happy to help! What are you working on?"}

User: "Hey, how's it going?"
{"intent_type": "chitchat", "confidence": 0.95, "subject": "greeting", "deliverable": null, "constraints": [], "needs_clarification": false, "clarification_question": null}

User: "Analyze the pros and cons of Rust vs Go for our backend"
{"intent_type": "analyze", "confidence": 0.95, "subject": "Rust vs Go for backend development", "deliverable": "comparative analysis", "constraints": ["backend context"], "needs_clarification": false, "clarification_question": null}

User: "Write me a blog post about AI safety"
{"intent_type": "draft", "confidence": 0.9, "subject": "AI safety", "deliverable": "blog post", "constraints": [], "needs_clarification": false, "clarification_question": null}

User: "Review this code for security issues" 
{"intent_type": "review", "confidence": 0.85, "subject": "code security review", "deliverable": "security assessment", "constraints": ["security focus"], "needs_clarification": true, "clarification_question": "I can help review code for security issues. Could you share the code you'd like me to review?"}

User: "Romantic evening activity near downtown Houston two couples mid thirties to early fourties. Enjoy activities like escape rooms"
{"intent_type": "research", "confidence": 0.85, "subject": "romantic evening activities in downtown Houston", "deliverable": "activity recommendations", "constraints": ["downtown Houston", "two couples", "mid 30s to early 40s", "escape room style activities"], "needs_clarification": false, "clarification_question": null}

User: "Best restaurants in Austin for a business dinner"
{"intent_type": "research", "confidence": 0.9, "subject": "business dinner restaurants in Austin", "deliverable": "restaurant recommendations", "constraints": ["Austin", "business appropriate"], "needs_clarification": false, "clarification_question": null}

Respond ONLY with JSON."""

    INTENT_SCHEMA = {
        "type": "object",
        "properties": {
            "intent_type": {
                "type": "string",
                "enum": ["research", "synthesize", "analyze", "draft", "review", "extract", "clarify", "chitchat", "unknown"]
            },
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "subject": {"type": "string"},
            "deliverable": {"type": ["string", "null"]},
            "constraints": {"type": "array", "items": {"type": "string"}},
            "needs_clarification": {"type": "boolean"},
            "clarification_question": {"type": ["string", "null"]},
        },
        "required": ["intent_type", "confidence", "subject", "needs_clarification"],
    }

    def __init__(self, provider: ModelProvider, model: str):
        self.provider = provider
        self.model = model
    
    async def parse(self, user_input: str) -> ParsedIntent:
        """Parse user input into structured intent."""
        try:
            parsed = await self.provider.complete_json(
                messages=[{"role": "user", "content": user_input}],
                model=self.model,
                system=self.SYSTEM_PROMPT,
                schema=self.INTENT_SCHEMA,
                temperature=0.1,
            )
            
            intent_type_str = parsed.get("intent_type", "unknown")
            try:
                intent_type = IntentType(intent_type_str)
            except ValueError:
                intent_type = IntentType.UNKNOWN
            
            return ParsedIntent(
                intent_type=intent_type,
                confidence=float(parsed.get("confidence", 0.5)),
                subject=parsed.get("subject", ""),
                deliverable=parsed.get("deliverable"),
                constraints=parsed.get("constraints", []),
                raw_input=user_input,
                needs_clarification=parsed.get("needs_clarification", False),
                clarification_question=parsed.get("clarification_question"),
            )
        
        except Exception as e:
            log.error(f"Intent parsing failed: {e}")
            return ParsedIntent(
                intent_type=IntentType.UNKNOWN,
                confidence=0.0,
                subject="",
                raw_input=user_input,
                needs_clarification=True,
                clarification_question="I had trouble understanding that. Could you rephrase?",
            )


# ---------------------------------------------------------------------------
# Task decomposer
# ---------------------------------------------------------------------------
class TaskDecomposer:
    """Decomposes parsed intent into concrete task graph."""
    
    SYSTEM_PROMPT = """You are Zulu's task decomposer. Given a parsed intent, create a plan of concrete tasks.

Available task types:
- web_research: Search the web and gather information
- document_synthesis: Create a document from provided information  
- comparative_analysis: Compare multiple items against criteria
- report_drafting: Write a report or document
- code_review: Review code for issues
- data_extraction: Extract structured data from sources

Rules:
1. Break complex requests into 1-5 simple tasks
2. Each task should have a single clear objective
3. Tasks can depend on other tasks (use their output)
4. Be specific in prompts — vague prompts produce vague results
5. First task index is 0

Respond with JSON array:
[
    {
        "task_type": "web_research",
        "prompt": "specific prompt for this task",
        "depends_on": [],
        "tools_needed": ["web_browse", "web_fetch"],
        "domains": [],
        "timeout_seconds": 300
    }
]

Tools available: web_browse, web_fetch, document_read, document_write, llm_chat, code_analyze

Example:

Intent: research competitors in EV charging, draft one-pager
[
    {
        "task_type": "web_research",
        "prompt": "Research the top 5 companies in the EV charging market. For each, identify: company name, founding year, business model, key differentiators, funding raised, and market position.",
        "depends_on": [],
        "tools_needed": ["web_browse", "web_fetch", "llm_chat"],
        "domains": [],
        "timeout_seconds": 300
    },
    {
        "task_type": "document_synthesis",
        "prompt": "Using the competitor research provided, create a one-page executive summary covering: market overview, key players, competitive landscape, and strategic implications. Format as a professional one-pager.",
        "depends_on": [0],
        "tools_needed": ["llm_chat"],
        "domains": [],
        "timeout_seconds": 180
    }
]

Respond ONLY with JSON array."""

    DECOMPOSITION_SCHEMA = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "task_type": {
                    "type": "string",
                    "enum": ["web_research", "document_synthesis", "comparative_analysis", "report_drafting", "code_review", "data_extraction"]
                },
                "prompt": {"type": "string"},
                "depends_on": {"type": "array", "items": {"type": "integer"}},
                "tools_needed": {"type": "array", "items": {"type": "string"}},
                "domains": {"type": "array", "items": {"type": "string"}},
                "timeout_seconds": {"type": "integer"},
            },
            "required": ["task_type", "prompt"],
        },
    }

    def __init__(self, provider: ModelProvider, model: str, config: PlannerConfig):
        self.provider = provider
        self.model = model
        self.config = config
    
    async def decompose(self, intent: ParsedIntent) -> list[PlannedTask]:
        """Decompose intent into task list."""
        if intent.intent_type == IntentType.CHITCHAT:
            return []
        
        if intent.needs_clarification:
            return []
        
        try:
            decomp_input = self._build_decomposition_prompt(intent)
            
            tasks_data = await self.provider.complete_json(
                messages=[{"role": "user", "content": decomp_input}],
                model=self.model,
                system=self.SYSTEM_PROMPT,
                schema=self.DECOMPOSITION_SCHEMA,
                temperature=0.2,
            )
            
            # Handle case where result is wrapped
            if isinstance(tasks_data, dict) and "items" in tasks_data:
                tasks_data = tasks_data["items"]
            
            if not isinstance(tasks_data, list):
                log.warning(f"Decomposition returned non-list: {type(tasks_data)}")
                return [self._fallback_task(intent)]
            
            tasks = []
            for i, task_data in enumerate(tasks_data[:self.config.max_tasks_per_request]):
                task_id = f"task-{i}"
                depends_on = [f"task-{dep}" for dep in task_data.get("depends_on", [])]
                
                tools = task_data.get("tools_needed", ["llm_chat"])
                tool_allowlist = ToolAllowlist(
                    web_browse="web_browse" in tools,
                    web_fetch="web_fetch" in tools,
                    document_read="document_read" in tools,
                    document_write="document_write" in tools,
                    llm_chat="llm_chat" in tools,
                    code_analyze="code_analyze" in tools,
                )
                
                task_type_str = task_data.get("task_type", "web_research")
                try:
                    task_type = OpenClawTaskType(task_type_str)
                except ValueError:
                    task_type = OpenClawTaskType.WEB_RESEARCH
                
                tasks.append(PlannedTask(
                    task_id=task_id,
                    task_type=task_type,
                    prompt=task_data.get("prompt", ""),
                    depends_on=depends_on,
                    tool_allowlist=tool_allowlist,
                    domain_allowlist=task_data.get("domains", []),
                    timeout_seconds=task_data.get("timeout_seconds", self.config.default_timeout_seconds),
                ))
            
            if not tasks:
                return [self._fallback_task(intent)]
            
            # Validate dependency graph
            validation_error = self._validate_graph(tasks)
            if validation_error:
                log.warning(f"Invalid task graph: {validation_error}. Using fallback.")
                return [self._fallback_task(intent)]
            
            return tasks
            
        except Exception as e:
            log.error(f"Task decomposition failed: {e}")
            return [self._fallback_task(intent)]
    
    def _validate_graph(self, tasks: list[PlannedTask]) -> Optional[str]:
        """
        Validate task dependency graph.
        
        Returns error message if invalid, None if valid.
        Checks for:
        - Orphaned dependencies (referencing non-existent tasks)
        - Circular dependencies
        """
        task_ids = {t.task_id for t in tasks}
        
        # Check for orphaned dependencies
        for task in tasks:
            for dep in task.depends_on:
                if dep not in task_ids:
                    return f"Task {task.task_id} depends on non-existent task {dep}"
        
        # Check for cycles using DFS
        visited = set()
        rec_stack = set()
        
        def has_cycle(task_id: str) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)
            
            task = next((t for t in tasks if t.task_id == task_id), None)
            if task:
                for dep in task.depends_on:
                    if dep not in visited:
                        if has_cycle(dep):
                            return True
                    elif dep in rec_stack:
                        return True
            
            rec_stack.remove(task_id)
            return False
        
        for task in tasks:
            if task.task_id not in visited:
                if has_cycle(task.task_id):
                    return "Circular dependency detected in task graph"
        
        return None
    
    def _build_decomposition_prompt(self, intent: ParsedIntent) -> str:
        """Build prompt for decomposition."""
        parts = [
            f"Intent type: {intent.intent_type.value}",
            f"Subject: {intent.subject}",
            f"Deliverable: {intent.deliverable or 'not specified'}",
        ]
        
        if intent.constraints:
            parts.append(f"Constraints: {', '.join(intent.constraints)}")
        
        parts.append(f"Original request: {intent.raw_input}")
        
        return "\n".join(parts)
    
    def _fallback_task(self, intent: ParsedIntent) -> PlannedTask:
        """Create single fallback task when decomposition fails."""
        task_type_map = {
            IntentType.RESEARCH: OpenClawTaskType.WEB_RESEARCH,
            IntentType.SYNTHESIZE: OpenClawTaskType.DOCUMENT_SYNTHESIS,
            IntentType.ANALYZE: OpenClawTaskType.COMPARATIVE_ANALYSIS,
            IntentType.DRAFT: OpenClawTaskType.REPORT_DRAFTING,
            IntentType.REVIEW: OpenClawTaskType.CODE_REVIEW,
            IntentType.EXTRACT: OpenClawTaskType.DATA_EXTRACTION,
        }
        
        task_type = task_type_map.get(intent.intent_type, OpenClawTaskType.WEB_RESEARCH)
        
        return PlannedTask(
            task_id="task-0",
            task_type=task_type,
            prompt=intent.raw_input,
            tool_allowlist=ToolAllowlist(web_browse=True, web_fetch=True, llm_chat=True),
            timeout_seconds=self.config.default_timeout_seconds,
        )


# ---------------------------------------------------------------------------
# Result extractor
# ---------------------------------------------------------------------------
class ResultExtractor:
    """Extracts and formats results between dependent tasks."""
    
    SYSTEM_PROMPT = """You are extracting key information from task results to pass to dependent tasks.

Given a task result, extract the most relevant information in a clear, structured format.
Focus on facts, data points, and conclusions that would be useful for follow-up tasks.

Respond with a concise summary (max 2000 chars) that captures the essential information."""

    def __init__(self, provider: ModelProvider, model: str):
        self.provider = provider
        self.model = model
    
    async def extract_for_dependent(self, result: dict, dependent_task: PlannedTask) -> str:
        """Extract relevant info from result for a dependent task."""
        if not result:
            return ""
        
        result_str = json.dumps(result, indent=2) if isinstance(result, dict) else str(result)
        
        if len(result_str) < 2000:
            return result_str
        
        try:
            prompt = f"""Task result to extract from:
{result_str[:8000]}

Dependent task that needs this information:
Type: {dependent_task.task_type.value}
Prompt: {dependent_task.prompt}

Extract the most relevant information for the dependent task."""

            extracted = await self.provider.complete(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                system=self.SYSTEM_PROMPT,
                temperature=0.1,
                max_tokens=1024,
            )
            
            return extracted
            
        except Exception as e:
            log.error(f"Result extraction failed: {e}")
            return result_str[:2000]


# ---------------------------------------------------------------------------
# Task executor
# ---------------------------------------------------------------------------
class TaskExecutor:
    """Executes task graphs through OpenClaw or MoltWorker adapter."""
    
    def __init__(
        self,
        adapter,  # ZuluOpenClawAdapter or ZuluMoltWorkerAdapter (duck-typed)
        credentials: ScopedCredentials,
        extractor: ResultExtractor,
        config: PlannerConfig,
    ):
        self.adapter = adapter
        self.credentials = credentials
        self.extractor = extractor
        self.config = config
    
    async def execute(self, graph: TaskGraph) -> ExecutionResult:
        """Execute all tasks in the graph respecting dependencies.
        
        Independent tasks (no unmet dependencies) run in parallel via asyncio.gather.
        """
        start_time = datetime.now(timezone.utc)
        results = {}
        errors = {}
        
        while not graph.is_complete():
            ready_tasks = graph.get_ready_tasks()
            
            if not ready_tasks:
                # No tasks ready but graph not complete = stuck (failed deps or invalid graph)
                # Mark remaining pending tasks as failed due to blocked dependencies
                for task in graph.tasks:
                    if task.status == "pending":
                        task.status = "failed"
                        task.error = "Blocked: dependency failed or missing"
                        errors[task.task_id] = task.error
                break
            
            # Execute all ready tasks in parallel
            if len(ready_tasks) == 1:
                # Single task - run directly
                await self._execute_single_task(ready_tasks[0], graph.request_id, results, errors)
            else:
                # Multiple independent tasks - run in parallel
                log.info(f"Executing {len(ready_tasks)} tasks in parallel")
                await asyncio.gather(*[
                    self._execute_single_task(task, graph.request_id, results, errors)
                    for task in ready_tasks
                ])
        
        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        completed = sum(1 for t in graph.tasks if t.status == "completed")
        failed = sum(1 for t in graph.tasks if t.status == "failed")
        
        summary = self._generate_summary(graph, results, errors)
        
        return ExecutionResult(
            request_id=graph.request_id,
            success=failed == 0 and completed > 0,
            tasks_completed=completed,
            tasks_failed=failed,
            results=results,
            errors=errors,
            summary=summary,
            elapsed_seconds=elapsed,
            task_graph=graph,
        )
    
    async def _execute_single_task(
        self,
        task: PlannedTask,
        request_id: str,
        results: dict,
        errors: dict,
    ) -> None:
        """Execute a single task and update results/errors dicts."""
        task.status = "running"
        log.info(f"Executing task {task.task_id}: {task.task_type.value}")
        
        try:
            dep_context = await self._build_dependency_context(task, results)
            
            prompt = task.prompt
            if dep_context:
                prompt = f"{task.prompt}\n\n--- Context from previous tasks ---\n{dep_context}"
            
            # Try OpenClaw first, fall back to direct LLM if unavailable
            try:
                # Refresh credential timestamp before each dispatch to avoid TTL expiry
                fresh_credentials = ScopedCredentials(
                    llm_api_key=self.credentials.llm_api_key,
                    llm_provider=self.credentials.llm_provider,
                    issued_at=datetime.now(timezone.utc).isoformat(),
                    extra=self.credentials.extra,
                )
                
                request = OpenClawRequest(
                    task_id=f"{request_id}-{task.task_id}",
                    task_type=task.task_type,
                    prompt=prompt,
                    tool_allowlist=task.tool_allowlist,
                    domain_allowlist=task.domain_allowlist,
                    credentials=fresh_credentials,
                    timeout_seconds=task.timeout_seconds,
                    context={"dependency_results": dep_context},
                )
                
                response = await self.adapter.dispatch(request)
                
                if response.succeeded:
                    task.status = "completed"
                    task.result = response.output
                    results[task.task_id] = response.output
                    log.info(f"Task {task.task_id} completed via OpenClaw")
                else:
                    # If OpenClaw failed due to connection, try direct LLM
                    if "Cannot connect" in (response.error or "") or "getaddrinfo" in (response.error or ""):
                        log.warning(f"OpenClaw unavailable, falling back to direct LLM for {task.task_id}")
                        await self._execute_via_llm(task, prompt, results, errors)
                    else:
                        task.status = "failed"
                        task.error = response.error
                        errors[task.task_id] = response.error
                        log.error(f"Task {task.task_id} failed: {response.error}")
            
            except (OpenClawError, Exception) as e:
                error_str = str(e)
                if "Cannot connect" in error_str or "getaddrinfo" in error_str or "Connection refused" in error_str:
                    log.warning(f"OpenClaw unavailable, falling back to direct LLM for {task.task_id}")
                    await self._execute_via_llm(task, prompt, results, errors)
                else:
                    raise
        
        except OpenClawError as e:
            task.status = "failed"
            task.error = str(e)
            errors[task.task_id] = str(e)
            log.error(f"Task {task.task_id} error: {e}")
        
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            errors[task.task_id] = str(e)
            log.exception(f"Unexpected error in task {task.task_id}")
    
    async def _execute_via_llm(
        self,
        task: PlannedTask,
        prompt: str,
        results: dict,
        errors: dict,
    ) -> None:
        """Execute task directly via LLM when OpenClaw is unavailable."""
        try:
            # Build a research-focused prompt
            llm_prompt = f"""You are a research assistant. Complete this task thoroughly.

TASK TYPE: {task.task_type.value}

REQUEST:
{prompt}

Provide a comprehensive, well-structured response. Include specific details, facts, and actionable information."""

            response = await self.extractor.provider.complete(
                messages=[{"role": "user", "content": llm_prompt}],
                model=self.extractor.model,
                temperature=0.3,
                max_tokens=4096,
            )
            
            task.status = "completed"
            task.result = {"summary": response, "source": "direct_llm"}
            results[task.task_id] = task.result
            log.info(f"Task {task.task_id} completed via direct LLM fallback")
            
        except Exception as e:
            task.status = "failed"
            task.error = f"LLM fallback failed: {str(e)}"
            errors[task.task_id] = task.error
            log.error(f"Task {task.task_id} LLM fallback failed: {e}")
    
    async def _build_dependency_context(self, task: PlannedTask, results: dict) -> str:
        """Build context string from dependency results.
        
        Extracts from multiple dependencies in parallel.
        """
        if not task.depends_on:
            return ""
        
        # Filter to deps that have results
        deps_with_results = [(dep_id, results[dep_id]) for dep_id in task.depends_on if dep_id in results]
        
        if not deps_with_results:
            return ""
        
        # Extract from all dependencies in parallel
        async def extract_one(dep_id: str, result: dict) -> str:
            extracted = await self.extractor.extract_for_dependent(result, task)
            return f"[{dep_id}]:\n{extracted}"
        
        context_parts = await asyncio.gather(*[
            extract_one(dep_id, result) for dep_id, result in deps_with_results
        ])
        
        return "\n\n".join(context_parts)
    
    def _generate_summary(self, graph: TaskGraph, results: dict, errors: dict) -> str:
        """Generate human-readable summary."""
        lines = []
        
        if errors:
            lines.append(f"⚠️ {len(errors)} task(s) encountered issues.")
        
        if results:
            lines.append(f"✅ {len(results)} task(s) completed successfully.")
            
            for task_id, result in results.items():
                task = next((t for t in graph.tasks if t.task_id == task_id), None)
                if task:
                    if isinstance(result, dict):
                        summary = result.get("summary", result.get("output", ""))
                        if not summary:
                            summary = json.dumps(result)[:300]
                    else:
                        summary = str(result)[:300]
                    
                    lines.append(f"\n**{task.task_type.value}**: {summary}")
        
        return "\n".join(lines) if lines else "No results."


# ---------------------------------------------------------------------------
# Main planner interface
# ---------------------------------------------------------------------------
class ZuluTaskPlanner:
    """
    Main interface for task planning and execution.
    
    Usage:
        provider = get_provider()
        model_config = ModelConfig.from_env()
        exec_credentials = ScopedCredentials(...)
        
        planner = ZuluTaskPlanner(
            provider=provider,
            model_config=model_config,
            execution_credentials=exec_credentials,
        )
        
        # Plan from natural language
        result = await planner.plan("Research competitors and draft a one-pager")
        
        if result.needs_clarification:
            return result.clarification_question
        
        if result.task_graph:
            exec_result = await planner.execute(result.task_graph)
            return exec_result.summary
    """
    
    def __init__(
        self,
        provider: ModelProvider,
        model_config: ModelConfig,
        execution_credentials: ScopedCredentials,
        adapter = None,  # ZuluOpenClawAdapter or ZuluMoltWorkerAdapter (duck-typed)
        planner_config: Optional[PlannerConfig] = None,
    ):
        self.provider = provider
        self.model_config = model_config
        self.execution_credentials = execution_credentials
        self.adapter = adapter or _create_default_adapter()
        self.config = planner_config or PlannerConfig.from_env()
        
        self.intent_parser = IntentParser(provider, model_config.intent_model)
        self.decomposer = TaskDecomposer(provider, model_config.planning_model, self.config)
        self.extractor = ResultExtractor(provider, model_config.extraction_model)
    
    async def plan(self, user_input: str) -> PlannerResult:
        """
        Plan tasks from natural language input.
        
        Returns PlannerResult with either:
        - task_graph: Ready to execute
        - needs_clarification: True with clarification_question
        - is_chitchat: True with chitchat_response
        - error: If planning failed
        """
        log.info(f"Planning for input: {user_input[:100]}...")
        
        intent = await self.intent_parser.parse(user_input)
        log.info(f"Parsed intent: {intent.intent_type.value} (confidence: {intent.confidence:.2f}, needs_clarification: {intent.needs_clarification})")
        
        if intent.intent_type == IntentType.CHITCHAT:
            return PlannerResult(
                success=True,
                is_chitchat=True,
                chitchat_response=self._chitchat_response(intent),
            )
        
        if intent.needs_clarification or intent.confidence < self.config.ambiguity_threshold:
            return PlannerResult(
                success=True,
                needs_clarification=True,
                clarification_question=intent.clarification_question or
                    "Could you tell me more about what you'd like me to help with?",
            )
        
        tasks = await self.decomposer.decompose(intent)
        
        if not tasks:
            return PlannerResult(
                success=False,
                error="Could not decompose request into actionable tasks.",
            )
        
        request_id = f"req-{uuid.uuid4().hex[:8]}"
        graph = TaskGraph(
            request_id=request_id,
            tasks=tasks,
            original_input=user_input,
            parsed_intent=intent,
        )
        
        log.info(f"Created task graph {request_id} with {len(tasks)} tasks")
        
        return PlannerResult(
            success=True,
            task_graph=graph,
        )
    
    async def execute(self, graph: TaskGraph) -> ExecutionResult:
        """Execute a planned task graph."""
        executor = TaskExecutor(
            self.adapter,
            self.execution_credentials,
            self.extractor,
            self.config,
        )
        return await executor.execute(graph)
    
    async def plan_and_execute(self, user_input: str) -> ExecutionResult | PlannerResult:
        """
        Convenience method: plan and execute in one call.
        
        Returns ExecutionResult if successful, PlannerResult if clarification needed.
        """
        plan_result = await self.plan(user_input)
        
        if not plan_result.success or plan_result.needs_clarification or plan_result.is_chitchat:
            return plan_result
        
        return await self.execute(plan_result.task_graph)
    
    def _chitchat_response(self, intent: ParsedIntent) -> str:
        """Generate response for chitchat messages."""
        greetings = ["hey", "hi", "hello", "how are you", "what's up", "good morning", "good evening"]
        if any(g in intent.raw_input.lower() for g in greetings):
            return "Hey! I'm Zulu, your AI research assistant. What can I help you with today?"
        
        return "I'm here to help with research, analysis, and document drafting. What would you like me to work on?"
    
    async def close(self):
        """Clean up resources."""
        await self.adapter.close()
        await self.provider.close()


# ---------------------------------------------------------------------------
# Adapter factory — auto-selects MoltWorker or local OpenClaw
# ---------------------------------------------------------------------------
def _create_default_adapter():
    """
    Create the appropriate execution adapter based on environment config.
    
    If MOLTWORKER_URL is set → use MoltWorker (Cloudflare) as backend.
    Otherwise → use local OpenClaw NightShift container.
    """
    moltworker_url = os.getenv("MOLTWORKER_URL", "")
    
    if moltworker_url and ZuluMoltWorkerAdapter is not None:
        log.info(f"Using MoltWorker backend: {moltworker_url}")
        return ZuluMoltWorkerAdapter(moltworker_url=moltworker_url)
    
    if moltworker_url and ZuluMoltWorkerAdapter is None:
        log.warning(
            "MOLTWORKER_URL is set but zulu_moltworker_adapter is not available. "
            "Falling back to local OpenClaw adapter."
        )
    
    log.info("Using local OpenClaw NightShift adapter")
    return ZuluOpenClawAdapter()


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------
def create_planner(
    execution_api_key: Optional[str] = None,
    execution_provider: Optional[str] = None,
) -> ZuluTaskPlanner:
    """
    Create a planner with default configuration.
    
    Planning uses ZULU_LLM_PROVIDER + ANTHROPIC_API_KEY (or provider-specific key).
    Execution uses ZULU_EXECUTION_API_KEY (separate billing surface).
    
    This separation is intentional: planning costs are yours, execution costs
    may be passed to clients or use different rate limits.
    """
    provider = get_provider()
    model_config = ModelConfig.from_env()
    
    # Execution credentials are separate from planning credentials
    # Use distinct env var to make the separation visible in configuration
    exec_key = execution_api_key or os.getenv("ZULU_EXECUTION_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    exec_provider = execution_provider or os.getenv("ZULU_EXECUTION_PROVIDER", "anthropic")
    
    if not exec_key and exec_provider != "ollama":
        log.warning(
            "No execution API key found. Set ZULU_EXECUTION_API_KEY or pass execution_api_key. "
            "Falling back to planning API key."
        )
    
    exec_credentials = ScopedCredentials(
        llm_api_key=exec_key,
        llm_provider=exec_provider,
    )
    
    return ZuluTaskPlanner(
        provider=provider,
        model_config=model_config,
        execution_credentials=exec_credentials,
    )


# ---------------------------------------------------------------------------
# CLI for testing
# ---------------------------------------------------------------------------
async def main():
    """Test the planner interactively."""
    print("Zulu Task Planner (type 'quit' to exit)")
    print("-" * 40)
    
    planner = create_planner()
    
    try:
        while True:
            try:
                user_input = input("\nYou: ").strip()
            except EOFError:
                break
            
            if not user_input or user_input.lower() == "quit":
                break
            
            result = await planner.plan(user_input)
            
            if result.is_chitchat:
                print(f"\nZulu: {result.chitchat_response}")
            
            elif result.needs_clarification:
                print(f"\nZulu: {result.clarification_question}")
            
            elif result.task_graph:
                print(f"\nPlanned {len(result.task_graph.tasks)} tasks:")
                for task in result.task_graph.tasks:
                    deps = f" (depends on: {', '.join(task.depends_on)})" if task.depends_on else ""
                    print(f"  [{task.task_id}] {task.task_type.value}{deps}")
                    print(f"       {task.prompt[:80]}...")
                
                execute = input("\nExecute? (y/n): ").strip().lower()
                if execute == "y":
                    print("\nExecuting...")
                    exec_result = await planner.execute(result.task_graph)
                    print(f"\n{exec_result.summary}")
            
            elif result.error:
                print(f"\nError: {result.error}")
    
    finally:
        await planner.close()


if __name__ == "__main__":
    asyncio.run(main())
