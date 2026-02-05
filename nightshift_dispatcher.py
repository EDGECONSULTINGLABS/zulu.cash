"""
nightshift_dispatcher.py
=========================
Cron/queue-based NightShift task dispatcher for Zulu.

Runs overnight batch jobs through OpenClaw NightShift worker.
Produces "work done while you slept" reports.

DESIGN:
- Reads task queue from SQLite (or JSON file for simplicity)
- Dispatches tasks to OpenClaw via zulu_openclaw_adapter
- Collects results into a summary report
- Zero autonomy: tasks are pre-defined, not self-generated

USAGE:
    # Run once (cron-style):
    python nightshift_dispatcher.py --once

    # Run as daemon (checks queue every N minutes):
    python nightshift_dispatcher.py --daemon --interval 30

    # Add task to queue:
    python nightshift_dispatcher.py --add --type web_research --prompt "Research X"
"""

import argparse
import asyncio
import json
import logging
import os
import sqlite3
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from zulu_openclaw_adapter import (
    ZuluOpenClawAdapter,
    OpenClawRequest,
    OpenClawTaskType,
    ScopedCredentials,
    ToolAllowlist,
    OpenClawError,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [NIGHTSHIFT-DISPATCH] %(levelname)s %(message)s"
)
log = logging.getLogger("nightshift-dispatcher")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
class DispatcherConfig:
    """Environment-based configuration."""
    
    @property
    def db_path(self) -> str:
        return os.getenv("NIGHTSHIFT_DB_PATH", "/app/data/nightshift_queue.db")
    
    @property
    def report_dir(self) -> str:
        return os.getenv("NIGHTSHIFT_REPORT_DIR", "/app/reports")
    
    @property
    def check_interval_seconds(self) -> int:
        return int(os.getenv("NIGHTSHIFT_CHECK_INTERVAL", "1800"))  # 30 min
    
    @property
    def quiet_hours_start(self) -> int:
        """Hour (0-23) when NightShift can start working."""
        return int(os.getenv("NIGHTSHIFT_QUIET_START", "22"))  # 10 PM
    
    @property
    def quiet_hours_end(self) -> int:
        """Hour (0-23) when NightShift should stop."""
        return int(os.getenv("NIGHTSHIFT_QUIET_END", "6"))  # 6 AM
    
    @property
    def max_tasks_per_run(self) -> int:
        return int(os.getenv("NIGHTSHIFT_MAX_TASKS", "10"))
    
    @property
    def llm_api_key(self) -> Optional[str]:
        """Default API key for LLM calls (can be overridden per-task)."""
        return os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")
    
    @property
    def llm_provider(self) -> str:
        if os.getenv("ANTHROPIC_API_KEY"):
            return "anthropic"
        if os.getenv("OPENAI_API_KEY"):
            return "openai"
        return "ollama"


config = DispatcherConfig()


# ---------------------------------------------------------------------------
# Task queue (SQLite-backed)
# ---------------------------------------------------------------------------
@dataclass
class QueuedTask:
    """A task waiting in the NightShift queue."""
    id: int
    task_type: str
    prompt: str
    priority: int = 0  # Higher = more urgent
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    scheduled_for: Optional[str] = None  # ISO timestamp, None = ASAP
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[str] = None
    error: Optional[str] = None
    completed_at: Optional[str] = None
    context: str = "{}"  # JSON-encoded context dict


class TaskQueue:
    """SQLite-backed task queue."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_db()
    
    def _ensure_db(self):
        """Create tables if they don't exist."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_type TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    priority INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    scheduled_for TEXT,
                    status TEXT DEFAULT 'pending',
                    result TEXT,
                    error TEXT,
                    completed_at TEXT,
                    context TEXT DEFAULT '{}'
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_status 
                ON tasks(status, priority DESC, created_at ASC)
            """)
            conn.commit()
    
    def add_task(
        self,
        task_type: str,
        prompt: str,
        priority: int = 0,
        scheduled_for: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> int:
        """Add a task to the queue. Returns task ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO tasks (task_type, prompt, priority, created_at, scheduled_for, context)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    task_type,
                    prompt,
                    priority,
                    datetime.now(timezone.utc).isoformat(),
                    scheduled_for,
                    json.dumps(context or {}),
                )
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_pending_tasks(self, limit: int = 10) -> list[QueuedTask]:
        """Get pending tasks ready to run, ordered by priority."""
        now = datetime.now(timezone.utc).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT * FROM tasks
                WHERE status = 'pending'
                  AND (scheduled_for IS NULL OR scheduled_for <= ?)
                ORDER BY priority DESC, created_at ASC
                LIMIT ?
                """,
                (now, limit)
            ).fetchall()
            
            return [QueuedTask(**dict(row)) for row in rows]
    
    def mark_running(self, task_id: int):
        """Mark task as currently running."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE tasks SET status = 'running' WHERE id = ?",
                (task_id,)
            )
            conn.commit()
    
    def mark_completed(self, task_id: int, result: dict):
        """Mark task as completed with result."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE tasks 
                SET status = 'completed', 
                    result = ?, 
                    completed_at = ?
                WHERE id = ?
                """,
                (
                    json.dumps(result),
                    datetime.now(timezone.utc).isoformat(),
                    task_id,
                )
            )
            conn.commit()
    
    def mark_failed(self, task_id: int, error: str):
        """Mark task as failed with error."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE tasks 
                SET status = 'failed', 
                    error = ?, 
                    completed_at = ?
                WHERE id = ?
                """,
                (
                    error,
                    datetime.now(timezone.utc).isoformat(),
                    task_id,
                )
            )
            conn.commit()
    
    def get_completed_since(self, since: str) -> list[QueuedTask]:
        """Get tasks completed since a given timestamp."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT * FROM tasks
                WHERE status IN ('completed', 'failed')
                  AND completed_at >= ?
                ORDER BY completed_at ASC
                """,
                (since,)
            ).fetchall()
            
            return [QueuedTask(**dict(row)) for row in rows]


# ---------------------------------------------------------------------------
# NightShift dispatcher
# ---------------------------------------------------------------------------
class NightShiftDispatcher:
    """
    Dispatches queued tasks to OpenClaw NightShift.
    
    Runs during quiet hours, produces summary reports.
    """
    
    def __init__(self, queue: TaskQueue, adapter: ZuluOpenClawAdapter):
        self.queue = queue
        self.adapter = adapter
        self._run_start: Optional[str] = None
    
    def is_quiet_hours(self) -> bool:
        """Check if we're in the quiet hours window."""
        hour = datetime.now().hour
        start = config.quiet_hours_start
        end = config.quiet_hours_end
        
        # Handle overnight wrap (e.g., 22:00 - 06:00)
        if start > end:
            return hour >= start or hour < end
        else:
            return start <= hour < end
    
    async def run_once(self, ignore_quiet_hours: bool = False) -> dict:
        """
        Run one batch of pending tasks.
        Returns summary of what was done.
        """
        if not ignore_quiet_hours and not self.is_quiet_hours():
            log.info("Not in quiet hours, skipping run")
            return {"skipped": True, "reason": "not_quiet_hours"}
        
        self._run_start = datetime.now(timezone.utc).isoformat()
        tasks = self.queue.get_pending_tasks(limit=config.max_tasks_per_run)
        
        if not tasks:
            log.info("No pending tasks")
            return {"tasks_processed": 0}
        
        log.info(f"Processing {len(tasks)} tasks")
        
        results = []
        for task in tasks:
            result = await self._process_task(task)
            results.append(result)
        
        summary = self._generate_summary(results)
        self._save_report(summary)
        
        return summary
    
    async def _process_task(self, task: QueuedTask) -> dict:
        """Process a single task."""
        log.info(f"Processing task {task.id}: {task.task_type}")
        self.queue.mark_running(task.id)
        
        try:
            # Map task type to OpenClaw task type
            task_type = OpenClawTaskType(task.task_type)
            
            # Build credentials
            credentials = ScopedCredentials(
                llm_api_key=config.llm_api_key,
                llm_provider=config.llm_provider,
            )
            
            # Parse context
            context = json.loads(task.context) if task.context else {}
            
            # Build tool allowlist based on task type
            tool_allowlist = self._get_tool_allowlist(task_type)
            
            # Dispatch to OpenClaw
            request = OpenClawRequest(
                task_id=f"nightshift-{task.id}",
                task_type=task_type,
                prompt=task.prompt,
                tool_allowlist=tool_allowlist,
                domain_allowlist=context.get("domains", []),
                credentials=credentials,
                context=context,
                timeout_seconds=300,
            )
            
            response = await self.adapter.dispatch(request)
            
            if response.succeeded:
                self.queue.mark_completed(task.id, {
                    "output": response.output,
                    "steps_taken": response.steps_taken,
                    "elapsed_seconds": response.elapsed_seconds,
                })
                return {
                    "task_id": task.id,
                    "status": "completed",
                    "task_type": task.task_type,
                    "output": response.output,
                }
            else:
                self.queue.mark_failed(task.id, response.error or "Unknown error")
                return {
                    "task_id": task.id,
                    "status": "failed",
                    "task_type": task.task_type,
                    "error": response.error,
                }
        
        except OpenClawError as e:
            self.queue.mark_failed(task.id, str(e))
            return {
                "task_id": task.id,
                "status": "failed",
                "task_type": task.task_type,
                "error": str(e),
            }
        except Exception as e:
            log.exception(f"Unexpected error processing task {task.id}")
            self.queue.mark_failed(task.id, str(e))
            return {
                "task_id": task.id,
                "status": "failed",
                "task_type": task.task_type,
                "error": str(e),
            }
    
    def _get_tool_allowlist(self, task_type: OpenClawTaskType) -> ToolAllowlist:
        """Get appropriate tool allowlist for task type."""
        if task_type == OpenClawTaskType.WEB_RESEARCH:
            return ToolAllowlist(web_browse=True, web_fetch=True, llm_chat=True)
        elif task_type == OpenClawTaskType.DOCUMENT_SYNTHESIS:
            return ToolAllowlist(document_read=True, llm_chat=True)
        elif task_type == OpenClawTaskType.COMPARATIVE_ANALYSIS:
            return ToolAllowlist(web_fetch=True, llm_chat=True)
        elif task_type == OpenClawTaskType.REPORT_DRAFTING:
            return ToolAllowlist(llm_chat=True)
        elif task_type == OpenClawTaskType.CODE_REVIEW:
            return ToolAllowlist(code_analyze=True, llm_chat=True)
        elif task_type == OpenClawTaskType.DATA_EXTRACTION:
            return ToolAllowlist(web_fetch=True, llm_chat=True)
        else:
            return ToolAllowlist(llm_chat=True)
    
    def _generate_summary(self, results: list[dict]) -> dict:
        """Generate summary report."""
        completed = [r for r in results if r["status"] == "completed"]
        failed = [r for r in results if r["status"] == "failed"]
        
        return {
            "run_start": self._run_start,
            "run_end": datetime.now(timezone.utc).isoformat(),
            "total_tasks": len(results),
            "completed": len(completed),
            "failed": len(failed),
            "tasks": results,
        }
    
    def _save_report(self, summary: dict):
        """Save summary report to file."""
        report_dir = Path(config.report_dir)
        report_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = report_dir / f"nightshift_report_{timestamp}.json"
        
        with open(report_path, "w") as f:
            json.dump(summary, f, indent=2)
        
        log.info(f"Report saved: {report_path}")
        
        # Also generate human-readable summary
        self._save_readable_report(summary, report_dir / f"nightshift_report_{timestamp}.md")
    
    def _save_readable_report(self, summary: dict, path: Path):
        """Generate human-readable markdown report."""
        lines = [
            "# NightShift Report",
            "",
            f"**Run started:** {summary['run_start']}",
            f"**Run ended:** {summary['run_end']}",
            "",
            f"## Summary",
            "",
            f"- **Total tasks:** {summary['total_tasks']}",
            f"- **Completed:** {summary['completed']}",
            f"- **Failed:** {summary['failed']}",
            "",
            "## Task Details",
            "",
        ]
        
        for task in summary["tasks"]:
            status_emoji = "✅" if task["status"] == "completed" else "❌"
            lines.append(f"### {status_emoji} Task {task['task_id']} ({task['task_type']})")
            lines.append("")
            
            if task["status"] == "completed" and task.get("output"):
                output = task["output"]
                if isinstance(output, dict):
                    lines.append("**Output:**")
                    lines.append("```json")
                    lines.append(json.dumps(output, indent=2)[:2000])
                    lines.append("```")
                else:
                    lines.append(f"**Output:** {str(output)[:500]}")
            elif task.get("error"):
                lines.append(f"**Error:** {task['error']}")
            
            lines.append("")
        
        with open(path, "w") as f:
            f.write("\n".join(lines))
        
        log.info(f"Readable report saved: {path}")
    
    async def run_daemon(self, interval_seconds: int):
        """Run as daemon, checking queue periodically."""
        log.info(f"Starting daemon mode (interval: {interval_seconds}s)")
        log.info(f"Quiet hours: {config.quiet_hours_start}:00 - {config.quiet_hours_end}:00")
        
        async with self.adapter.session_context():
            while True:
                try:
                    await self.run_once()
                except Exception as e:
                    log.exception(f"Error in daemon run: {e}")
                
                await asyncio.sleep(interval_seconds)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="NightShift task dispatcher")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("--interval", type=int, default=1800, help="Check interval in seconds (daemon mode)")
    parser.add_argument("--force", action="store_true", help="Ignore quiet hours")
    parser.add_argument("--add", action="store_true", help="Add task to queue")
    parser.add_argument("--type", type=str, help="Task type (for --add)")
    parser.add_argument("--prompt", type=str, help="Task prompt (for --add)")
    parser.add_argument("--priority", type=int, default=0, help="Task priority (for --add)")
    parser.add_argument("--list", action="store_true", help="List pending tasks")
    parser.add_argument("--db", type=str, help="Database path override")
    
    args = parser.parse_args()
    
    db_path = args.db or config.db_path
    queue = TaskQueue(db_path)
    
    if args.add:
        if not args.type or not args.prompt:
            print("ERROR: --add requires --type and --prompt")
            return 1
        
        task_id = queue.add_task(
            task_type=args.type,
            prompt=args.prompt,
            priority=args.priority,
        )
        print(f"Added task {task_id}: {args.type}")
        return 0
    
    if args.list:
        tasks = queue.get_pending_tasks(limit=50)
        if not tasks:
            print("No pending tasks")
        else:
            print(f"Pending tasks ({len(tasks)}):")
            for t in tasks:
                print(f"  [{t.id}] {t.task_type} (priority={t.priority}): {t.prompt[:50]}...")
        return 0
    
    # Create adapter and dispatcher
    def audit_callback(entries):
        """Persist audit entries to file."""
        audit_path = Path(config.report_dir) / "audit.jsonl"
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        with open(audit_path, "a") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")
    
    adapter = ZuluOpenClawAdapter(audit_flush_callback=audit_callback)
    dispatcher = NightShiftDispatcher(queue, adapter)
    
    if args.once:
        result = asyncio.run(dispatcher.run_once(ignore_quiet_hours=args.force))
        print(json.dumps(result, indent=2))
        return 0
    
    if args.daemon:
        asyncio.run(dispatcher.run_daemon(args.interval))
        return 0
    
    parser.print_help()
    return 1


if __name__ == "__main__":
    exit(main())
