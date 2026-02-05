#!/usr/bin/env python3
"""
Zulu Telegram Bot — Event-Driven Task Dispatch
===============================================
Receives messages from Telegram, routes through Zulu task planner,
dispatches to OpenClaw, returns results.

This is the "send a message, wake up to results" interface.

FLOW:
    User message → Intent parsing → Task decomposition → OpenClaw execution → Reply

SECURITY:
- User allowlist enforced
- Rate limiting per user
- Credentials scoped per-task
- Runs in isolated container
"""

import asyncio
import base64
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Optional

import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zulu_task_planner import (
    ZuluTaskPlanner,
    PlannerResult,
    ExecutionResult,
    create_planner,
)
from zulu_model_provider import get_provider, ModelConfig
from zulu_openclaw_adapter import ScopedCredentials

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CLAWD_URL = os.environ.get("CLAWD_URL", "http://clawd-runner:8080")
ALLOWED_USERS = os.environ.get("TELEGRAM_ALLOWED_USERS", "").split(",")
RATE_LIMIT_PER_MINUTE = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "10"))

# Rate limiting state
user_requests: dict[int, list[float]] = {}

# Conversation memory (per-user message history)
# Stores last N messages per user for context
MAX_CONVERSATION_HISTORY = 10
conversation_history: dict[int, list[dict]] = {}

# Global planner instance (initialized on startup)
planner: Optional[ZuluTaskPlanner] = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [ZULU-TG] %(levelname)s %(message)s"
)
log = logging.getLogger("zulu.telegram")


# ---------------------------------------------------------------------------
# Security: User allowlist
# ---------------------------------------------------------------------------
def is_allowed(user_id: int, username: str = None) -> bool:
    """Check if user is in allowlist."""
    if not ALLOWED_USERS or ALLOWED_USERS == [""]:
        log.warning(f"No allowlist configured - allowing user {user_id}")
        return True
    
    user_id_str = str(user_id)
    if user_id_str in ALLOWED_USERS:
        return True
    if username and f"@{username}" in ALLOWED_USERS:
        return True
    
    log.warning(f"Blocked user: {user_id} (@{username})")
    return False


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------
def check_rate_limit(user_id: int) -> bool:
    """Check if user is within rate limit."""
    now = time.time()
    minute_ago = now - 60
    
    if user_id not in user_requests:
        user_requests[user_id] = []
    
    user_requests[user_id] = [t for t in user_requests[user_id] if t > minute_ago]
    
    if len(user_requests[user_id]) >= RATE_LIMIT_PER_MINUTE:
        return False
    
    user_requests[user_id].append(now)
    return True


# ---------------------------------------------------------------------------
# Response formatting
# ---------------------------------------------------------------------------
class TelegramFormatter:
    """Formats planner results for Telegram."""
    
    MAX_MESSAGE_LENGTH = 4000
    
    @classmethod
    def format_result(cls, result: ExecutionResult | PlannerResult) -> list[str]:
        """Format a planner/execution result for Telegram."""
        if isinstance(result, PlannerResult):
            return cls._format_planner_result(result)
        else:
            return cls._format_execution_result(result)
    
    @classmethod
    def _format_planner_result(cls, result: PlannerResult) -> list[str]:
        """Format a planner result (clarification, chitchat, error)."""
        if result.is_chitchat:
            return [result.chitchat_response or "👋"]
        
        if result.needs_clarification:
            return [f"❓ {result.clarification_question}"]
        
        if result.error:
            return [f"❌ {result.error}"]
        
        return ["🤔 Something went wrong."]
    
    @classmethod
    def _format_execution_result(cls, result: ExecutionResult) -> list[str]:
        """Format an execution result."""
        messages = []
        
        # Status header
        if result.success:
            header = f"✅ Completed {result.tasks_completed} task(s) in {result.elapsed_seconds:.1f}s"
        else:
            header = f"⚠️ {result.tasks_completed} completed, {result.tasks_failed} failed"
        messages.append(header)
        
        # Task results
        for task_id, task_result in result.results.items():
            task_text = cls._format_task_result(task_id, task_result)
            messages.append(task_text)
        
        # Errors
        for task_id, error in result.errors.items():
            messages.append(f"❌ {task_id}: {error}")
        
        # Combine and split if needed
        combined = "\n\n".join(messages)
        return cls._split_message(combined)
    
    @classmethod
    def _format_task_result(cls, task_id: str, result: dict) -> str:
        """Format a single task result."""
        if isinstance(result, dict):
            # Try to extract meaningful content
            content = (
                result.get("summary") or
                result.get("output") or
                result.get("result") or
                result.get("content") or
                json.dumps(result, indent=2)
            )
        else:
            content = str(result)
        
        # Truncate if too long
        if len(content) > 2000:
            content = content[:2000] + "...\n\n_(truncated)_"
        
        return f"📋 {task_id}\n{content}"
    
    @classmethod
    def _split_message(cls, text: str) -> list[str]:
        """Split long messages for Telegram's limit."""
        if len(text) <= cls.MAX_MESSAGE_LENGTH:
            return [text]
        
        parts = []
        while text:
            if len(text) <= cls.MAX_MESSAGE_LENGTH:
                parts.append(text)
                break
            
            # Find a good split point
            split_at = text.rfind("\n\n", 0, cls.MAX_MESSAGE_LENGTH)
            if split_at == -1:
                split_at = text.rfind("\n", 0, cls.MAX_MESSAGE_LENGTH)
            if split_at == -1:
                split_at = cls.MAX_MESSAGE_LENGTH
            
            parts.append(text[:split_at])
            text = text[split_at:].lstrip()
        
        return parts


# ---------------------------------------------------------------------------
# Clawd-runner for simple tasks
# ---------------------------------------------------------------------------
async def send_to_clawd(message: str, user_id: int) -> Optional[dict]:
    """Send a simple task to clawd-runner. Returns None if not a clawd task."""
    message_lower = message.lower().strip()
    task_id = f"tg-{user_id}-{int(time.time())}"
    
    if message_lower.startswith("/fetch "):
        url = message[7:].strip()
        payload = {
            "task_id": task_id,
            "task_type": "web_fetch",
            "params": {"url": url},
            "timeout_seconds": 30
        }
    elif message_lower == "/ping" or message_lower == "ping":
        payload = {
            "task_id": task_id,
            "task_type": "ping",
            "params": {},
            "timeout_seconds": 10
        }
    else:
        return None  # Not a clawd task
    
    log.info(f"Sending task {task_id} ({payload['task_type']}) to clawd-runner")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(f"{CLAWD_URL}/task", json=payload)
            result = resp.json()
            log.info(f"Task {task_id} completed: {result.get('status')}")
            return result
        except Exception as e:
            log.error(f"Clawd error: {e}")
            return {"status": "error", "error": str(e)}


# ---------------------------------------------------------------------------
# Telegram handlers
# ---------------------------------------------------------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user
    
    if not is_allowed(user.id, user.username):
        await update.message.reply_text(
            f"⛔ You are not authorized to use this bot.\n"
            f"Your user ID: {user.id}"
        )
        return
    
    await update.message.reply_text(
        f"🦞 *Welcome to Zulu, {user.first_name}!*\n\n"
        "I'm your AI research assistant. Send me a message and I'll:\n"
        "• Research topics across the web\n"
        "• Analyze and compare information\n"
        "• Draft documents and reports\n"
        "• Extract data from sources\n\n"
        "*Commands:*\n"
        "/start - This message\n"
        "/status - Check system status\n"
        "/ping - Test connectivity\n"
        "/fetch <url> - Fetch a URL\n\n"
        "*Or just tell me what you need:*\n"
        "_\"Research my competitors in the EV charging space\"_\n"
        "_\"Draft a one-pager on AI safety trends\"_\n"
        "_\"Compare Rust vs Go for backend development\"_",
        parse_mode=ParseMode.MARKDOWN
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command."""
    user = update.effective_user
    if not is_allowed(user.id, user.username):
        return
    
    status_parts = ["*System Status*\n"]
    
    # Check clawd-runner
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{CLAWD_URL}/health")
            health = resp.json()
            status_parts.append(f"✅ Clawd-runner: {health.get('status')}")
    except Exception as e:
        status_parts.append(f"❌ Clawd-runner: {e}")
    
    # Check planner
    if planner:
        status_parts.append("✅ Task planner: ready")
    else:
        status_parts.append("❌ Task planner: not initialized")
    
    await update.message.reply_text("\n".join(status_parts), parse_mode=ParseMode.MARKDOWN)


async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ping command."""
    user = update.effective_user
    if not is_allowed(user.id, user.username):
        return
    
    result = await send_to_clawd("ping", user.id)
    if result and result.get("status") == "completed":
        ts = result.get("result", {}).get("timestamp", "unknown")
        await update.message.reply_text(f"🏓 Pong! Server time: {ts}")
    else:
        error = result.get("error", "Unknown error") if result else "No response"
        await update.message.reply_text(f"❌ Error: {error}")


async def fetch_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /fetch command."""
    user = update.effective_user
    if not is_allowed(user.id, user.username):
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /fetch <url>")
        return
    
    url = context.args[0]
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    result = await send_to_clawd(f"/fetch {url}", user.id)
    if result and result.get("status") == "completed":
        data = result.get("result", {})
        await update.message.reply_text(
            f"🌐 *Fetched:* {data.get('url')}\n"
            f"*Status:* {data.get('status_code')}\n"
            f"*Length:* {data.get('content_length')} chars\n\n"
            f"*Preview:*\n{data.get('content', '')[:1500]}",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        error = result.get("error", "Unknown error") if result else "No response"
        await update.message.reply_text(f"❌ Error: {error}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming text messages — route through task planner."""
    user = update.effective_user
    message = update.message.text
    
    # Security check
    if not is_allowed(user.id, user.username):
        await update.message.reply_text(f"⛔ Not authorized. Your ID: {user.id}")
        return
    
    # Rate limit check
    if not check_rate_limit(user.id):
        await update.message.reply_text("⏳ Rate limit exceeded. Please wait a moment.")
        return
    
    log.info(f"Message from {user.id} (@{user.username}): {message[:50]}...")
    
    # Store message in conversation history
    if user.id not in conversation_history:
        conversation_history[user.id] = []
    conversation_history[user.id].append({
        "role": "user",
        "content": message,
        "timestamp": time.time()
    })
    # Keep only last N messages
    if len(conversation_history[user.id]) > MAX_CONVERSATION_HISTORY:
        conversation_history[user.id] = conversation_history[user.id][-MAX_CONVERSATION_HISTORY:]
    
    # Try clawd-runner first for simple commands
    clawd_result = await send_to_clawd(message, user.id)
    if clawd_result is not None:
        # Format clawd response
        if clawd_result.get("status") == "completed":
            data = clawd_result.get("result", {})
            if data.get("pong"):
                await update.message.reply_text(f"🏓 Pong! Server time: {data.get('timestamp')}")
            else:
                await update.message.reply_text(
                    f"✅ Task completed\n```json\n{json.dumps(data, indent=2)[:2000]}\n```",
                    parse_mode=ParseMode.MARKDOWN
                )
        else:
            await update.message.reply_text(f"❌ Error: {clawd_result.get('error')}")
        return
    
    # Route to task planner
    if not planner:
        await update.message.reply_text("❌ Task planner not initialized. Please try again later.")
        return
    
    # Send typing indicator
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        # Build conversation context for the planner
        user_history = conversation_history.get(user.id, [])
        context_messages = []
        if len(user_history) > 1:
            # Include previous messages as context (exclude current message)
            for msg in user_history[:-1]:
                context_messages.append(f"[Previous] {msg['content']}")
        
        # Combine context with current message
        if context_messages:
            full_input = "CONVERSATION CONTEXT:\n" + "\n".join(context_messages[-5:]) + "\n\nCURRENT REQUEST:\n" + message
        else:
            full_input = message
        
        # Plan the request
        plan_result = await planner.plan(full_input)
        
        # Handle clarification/chitchat
        if plan_result.is_chitchat or plan_result.needs_clarification or not plan_result.success:
            responses = TelegramFormatter.format_result(plan_result)
            for response in responses:
                await update.message.reply_text(response)
                # Store bot response in history
                conversation_history[user.id].append({
                    "role": "assistant",
                    "content": response,
                    "timestamp": time.time()
                })
            return
        
        # We have a task graph — notify user and execute
        task_count = len(plan_result.task_graph.tasks)
        task_types = ", ".join(set(t.task_type.value for t in plan_result.task_graph.tasks))
        
        await update.message.reply_text(
            f"🚀 Planning complete\n"
            f"Tasks: {task_count} ({task_types})\n"
            f"Executing..."
        )
        
        # Keep sending typing indicator during execution
        async def keep_typing():
            while True:
                await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
                await asyncio.sleep(5)
        
        typing_task = asyncio.create_task(keep_typing())
        
        try:
            # Execute the plan
            exec_result = await planner.execute(plan_result.task_graph)
            
            # Format and send results
            responses = TelegramFormatter.format_result(exec_result)
            for response in responses:
                # Use plain text to avoid markdown parsing errors
                await update.message.reply_text(response)
        
        finally:
            typing_task.cancel()
            try:
                await typing_task
            except asyncio.CancelledError:
                pass
    
    except Exception as e:
        log.exception(f"Error processing message from {user.id}")
        await update.message.reply_text(f"❌ Error: {str(e)[:200]}")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming photos — analyze with vision model."""
    user = update.effective_user
    
    if not is_allowed(user.id, user.username):
        await update.message.reply_text(f"⛔ Not authorized. Your ID: {user.id}")
        return
    
    if not check_rate_limit(user.id):
        await update.message.reply_text("⏳ Rate limit exceeded. Please wait a moment.")
        return
    
    caption = update.message.caption or "Analyze this image and describe what you see."
    
    log.info(f"Photo from {user.id} (@{user.username}), caption: {caption[:50]}...")
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    await update.message.reply_text("📸 Analyzing image...")
    
    # For now, route photo analysis through the planner as a text task
    # In the future, this could use vision models directly
    await update.message.reply_text(
        "🚧 Image analysis coming soon. For now, please describe what you'd like me to help with."
    )


# ---------------------------------------------------------------------------
# Initialization and main
# ---------------------------------------------------------------------------
async def post_init(application: Application):
    """Initialize planner after bot starts."""
    global planner
    
    log.info("Initializing task planner...")
    try:
        planner = create_planner()
        log.info("Task planner initialized successfully")
    except Exception as e:
        log.error(f"Failed to initialize planner: {e}")
        planner = None


async def shutdown(application: Application):
    """Clean up on shutdown."""
    global planner
    
    if planner:
        log.info("Shutting down task planner...")
        await planner.close()
        planner = None


def main():
    if not BOT_TOKEN:
        log.error("TELEGRAM_BOT_TOKEN not set!")
        return
    
    log.info("=" * 60)
    log.info("Zulu Telegram Bot")
    log.info(f"  Clawd URL: {CLAWD_URL}")
    log.info(f"  Allowed users: {ALLOWED_USERS}")
    log.info(f"  Rate limit: {RATE_LIMIT_PER_MINUTE}/min")
    log.info("=" * 60)
    
    # Create application
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).post_shutdown(shutdown).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("ping", ping_command))
    app.add_handler(CommandHandler("fetch", fetch_command))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start polling
    log.info("Starting Zulu Telegram bot...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
