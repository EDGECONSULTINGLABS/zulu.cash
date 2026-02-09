#!/usr/bin/env python3
"""
Telegram Gateway for Zulu NightShift
=====================================
Receives messages from Telegram, forwards to NightShift worker, returns responses.

Security:
- User allowlist enforced
- Rate limiting per user
- No secrets access (bot token passed via env)
- Runs in isolated container
"""

import asyncio
import base64
import json
import logging
import os
import time
from datetime import datetime, timezone

import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CLAWD_URL = os.environ.get("CLAWD_URL", "http://clawd-runner:8080")
CLAWD_AUTH_TOKEN = os.environ.get("CLAWD_AUTH_TOKEN", "")
NIGHTSHIFT_URL = os.environ.get("NIGHTSHIFT_URL", "http://openclaw-nightshift:8090")
ALLOWED_USERS = os.environ.get("TELEGRAM_ALLOWED_USERS", "").split(",")
RATE_LIMIT_PER_MINUTE = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "10"))
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "llama3.2:1b")

# MoltWorker (Cloudflare) configuration
MOLTWORKER_URL = os.environ.get("MOLTWORKER_URL", "")
MOLTWORKER_GATEWAY_TOKEN = os.environ.get("MOLTWORKER_GATEWAY_TOKEN", "")
CF_ACCESS_CLIENT_ID = os.environ.get("CF_ACCESS_CLIENT_ID", "")
CF_ACCESS_CLIENT_SECRET = os.environ.get("CF_ACCESS_CLIENT_SECRET", "")
MOLTWORKER_TIMEOUT = int(os.environ.get("MOLTWORKER_TIMEOUT", "120"))

# Rate limiting state
user_requests: dict[int, list[float]] = {}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [TELEGRAM-GW] %(levelname)s %(message)s"
)
log = logging.getLogger("telegram-gateway")

# ---------------------------------------------------------------------------
# Security: User allowlist
# ---------------------------------------------------------------------------
def is_allowed(user_id: int, username: str = None) -> bool:
    """Check if user is in allowlist."""
    if not ALLOWED_USERS or ALLOWED_USERS == [""]:
        # No allowlist = allow all (dev mode)
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
    
    # Clean old requests
    user_requests[user_id] = [t for t in user_requests[user_id] if t > minute_ago]
    
    if len(user_requests[user_id]) >= RATE_LIMIT_PER_MINUTE:
        return False
    
    user_requests[user_id].append(now)
    return True

# ---------------------------------------------------------------------------
# Clawd-runner task dispatch (for simple tasks)
# ---------------------------------------------------------------------------
async def send_to_clawd(message: str, user_id: int) -> dict:
    """Send a task to clawd-runner."""
    task_id = f"tg-{user_id}-{int(time.time())}"
    
    # Parse command from message
    message_lower = message.lower().strip()
    
    if message_lower.startswith("/fetch "):
        url = message[7:].strip()
        payload = {
            "task_id": task_id,
            "task_type": "web_fetch",
            "params": {"url": url},
            "timeout_seconds": 30
        }
    elif message_lower.startswith("/transform "):
        try:
            data = json.loads(message[11:].strip())
            payload = {
                "task_id": task_id,
                "task_type": "transform",
                "params": {"data": data, "transform_type": "identity"},
                "timeout_seconds": 30
            }
        except json.JSONDecodeError:
            return {"status": "error", "error": "Invalid JSON for transform"}
    elif message_lower == "/ping" or message_lower == "ping":
        payload = {
            "task_id": task_id,
            "task_type": "ping",
            "params": {},
            "timeout_seconds": 10
        }
    else:
        return None  # Not a clawd task, route to NightShift
    
    log.info(f"Sending task {task_id} ({payload['task_type']}) to clawd-runner")
    
    headers = {}
    if CLAWD_AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {CLAWD_AUTH_TOKEN}"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(f"{CLAWD_URL}/task", json=payload, headers=headers)
            result = resp.json()
            log.info(f"Task {task_id} completed: {result.get('status')}")
            return result
        except Exception as e:
            log.error(f"Clawd error: {e}")
            return {"status": "error", "error": str(e)}

# ---------------------------------------------------------------------------
# Claude API direct call (for LLM questions/analysis)
# ---------------------------------------------------------------------------
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

async def send_to_claude(message: str, user_id: int, image_data: str = None, image_media_type: str = None) -> dict:
    """Send a question directly to Claude API, optionally with an image."""
    task_id = f"tg-{user_id}-{int(time.time())}"
    
    if not ANTHROPIC_API_KEY:
        return {"status": "error", "error": "No Anthropic API key configured"}
    
    log.info(f"Sending task {task_id} to Claude API" + (" (with image)" if image_data else ""))
    
    # Build content - either text only or text + image
    if image_data and image_media_type:
        content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": image_media_type,
                    "data": image_data
                }
            },
            {
                "type": "text",
                "text": message
            }
        ]
    else:
        content = message
    
    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 2048,
        "messages": [
            {"role": "user", "content": content}
        ]
    }
    
    headers = {
        "Content-Type": "application/json",
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01"
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                json=payload,
                headers=headers
            )
            
            if resp.status_code != 200:
                error_text = resp.text
                log.error(f"Claude API error: {resp.status_code} - {error_text}")
                return {"status": "error", "error": f"API error: {resp.status_code}"}
            
            result = resp.json()
            content = result.get("content", [])
            
            # Extract text from response
            response_text = ""
            for block in content:
                if block.get("type") == "text":
                    response_text += block.get("text", "")
            
            log.info(f"Task {task_id} completed successfully")
            return {
                "status": "completed",
                "result": {"summary": response_text}
            }
            
        except Exception as e:
            log.error(f"Claude error: {e}")
            return {"status": "error", "error": str(e)}

# ---------------------------------------------------------------------------
# MoltWorker HTTP task dispatch
# ---------------------------------------------------------------------------
async def send_to_moltworker(message: str, user_id: int) -> dict:
    """Send a message to MoltWorker via HTTP /api/task endpoint."""
    if not MOLTWORKER_URL or not MOLTWORKER_GATEWAY_TOKEN:
        return {"status": "error", "error": "MoltWorker not configured"}

    task_id = f"tg-{user_id}-{int(time.time())}"
    task_url = f"{MOLTWORKER_URL.rstrip('/')}/api/task"
    log.info(f"Sending task {task_id} to MoltWorker: {task_url}")

    headers = {"Content-Type": "application/json"}
    if CF_ACCESS_CLIENT_ID and CF_ACCESS_CLIENT_SECRET:
        headers["CF-Access-Client-Id"] = CF_ACCESS_CLIENT_ID
        headers["CF-Access-Client-Secret"] = CF_ACCESS_CLIENT_SECRET

    payload = {
        "message": message,
        "timeout": MOLTWORKER_TIMEOUT * 1000,  # ms
        "session_id": f"zulu-{user_id}",
    }

    async with httpx.AsyncClient(timeout=float(MOLTWORKER_TIMEOUT + 30)) as client:
        try:
            resp = await client.post(task_url, json=payload, headers=headers)

            if resp.status_code != 200:
                log.error(f"Task {task_id}: MoltWorker HTTP {resp.status_code}: {resp.text[:200]}")
                return {"status": "error", "error": f"MoltWorker HTTP {resp.status_code}"}

            result = resp.json()
            log.info(f"Task {task_id}: MoltWorker response status={result.get('status')}")

            # Normalize response to match expected format
            if result.get("status") == "completed":
                agent_result = result.get("result", {})
                content = (
                    agent_result.get("content") or
                    agent_result.get("summary") or
                    agent_result.get("text") or
                    json.dumps(agent_result)
                )
                return {"status": "completed", "result": {"summary": content}}

            return result

        except httpx.TimeoutException:
            log.error(f"Task {task_id}: MoltWorker timeout after {MOLTWORKER_TIMEOUT}s")
            return {"status": "timeout", "error": f"Timed out after {MOLTWORKER_TIMEOUT}s"}
        except Exception as e:
            log.error(f"Task {task_id}: MoltWorker error: {e}")
            return {"status": "error", "error": f"MoltWorker error: {e}"}


# ---------------------------------------------------------------------------
# Telegram handlers
# ---------------------------------------------------------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user
    
    if not is_allowed(user.id, user.username):
        await update.message.reply_text(
            "⛔ You are not authorized to use this bot.\n"
            f"Your user ID: {user.id}"
        )
        return
    
    await update.message.reply_text(
        f"🦞 Welcome to Zulu Agent, {user.first_name}!\n\n"
        "I'm powered by Claude (Anthropic) and can answer questions, analyze data, and help with tasks.\n\n"
        "Commands:\n"
        "/start - This message\n"
        "/status - Check system status\n"
        "/ping - Test connectivity\n"
        "/fetch <url> - Fetch a URL\n"
        "/research <url> - Fetch and analyze a URL\n\n"
        "Or just ask me anything!"
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command."""
    user = update.effective_user
    if not is_allowed(user.id, user.username):
        return
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{CLAWD_URL}/health")
            health = resp.json()
            
            await update.message.reply_text(
                f"✅ System Status\n\n"
                f"Clawd-runner: {health.get('status')}\n"
                f"Service: {health.get('service')}\n"
                f"Max task duration: {health.get('max_task_duration')}s\n"
                f"Workspace: {health.get('workspace')}"
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Error checking status: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages."""
    user = update.effective_user
    message = update.message.text
    
    # Security check
    if not is_allowed(user.id, user.username):
        await update.message.reply_text(
            f"⛔ Not authorized. Your ID: {user.id}"
        )
        return
    
    # Rate limit check
    if not check_rate_limit(user.id):
        await update.message.reply_text(
            "⏳ Rate limit exceeded. Please wait a moment."
        )
        return
    
    # Send typing indicator
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    log.info(f"Message from {user.id} (@{user.username}): {message[:50]}...")
    
    # Try clawd-runner first (for /fetch, /transform, ping)
    result = await send_to_clawd(message, user.id)
    
    # If clawd returned None, route to MoltWorker (if configured) or Claude API
    if result is None:
        if MOLTWORKER_URL and MOLTWORKER_GATEWAY_TOKEN:
            log.info("Routing to MoltWorker for LLM response")
            result = await send_to_moltworker(message, user.id)
            # Fall back to Claude if MoltWorker fails
            if result.get("status") == "error":
                log.warning(f"MoltWorker failed: {result.get('error')}, falling back to Claude")
                result = await send_to_claude(message, user.id)
        else:
            log.info("Routing to Claude API for LLM response")
            result = await send_to_claude(message, user.id)
        
        # Format NightShift response
        if result.get("status") == "completed":
            response_data = result.get("result", {})
            
            # Extract LLM response
            if isinstance(response_data, dict):
                response_text = (
                    response_data.get("summary") or
                    response_data.get("result") or
                    response_data.get("status") or
                    json.dumps(response_data, indent=2)[:3000]
                )
            else:
                response_text = str(response_data)[:3000]
            
            await update.message.reply_text(response_text or "🤖 (No response)")
        
        elif result.get("status") == "timeout":
            await update.message.reply_text("⏱️ Request timed out. Try a shorter question.")
        
        else:
            error = result.get("error", "Unknown error")
            await update.message.reply_text(f"❌ Error: {error}")
        return
    
    # Format clawd-runner response
    if result.get("status") == "completed":
        response_data = result.get("result", {})
        
        if isinstance(response_data, dict):
            if response_data.get("pong"):
                response_text = f"🏓 Pong! Server time: {response_data.get('timestamp')}"
            elif response_data.get("url"):
                response_text = (
                    f"🌐 Fetched: {response_data.get('url')}\n"
                    f"Status: {response_data.get('status_code')}\n"
                    f"Length: {response_data.get('content_length')} chars\n\n"
                    f"Preview:\n{response_data.get('content', '')[:1500]}"
                )
            else:
                response_text = json.dumps(response_data, indent=2)[:3000]
        else:
            response_text = str(response_data)[:3000]
        
        await update.message.reply_text(response_text or "✅ Task completed")
    
    elif result.get("status") == "timeout":
        await update.message.reply_text("⏱️ Task timed out.")
    
    else:
        error = result.get("error", "Unknown error")
        await update.message.reply_text(f"❌ Error: {error}")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ping command."""
    user = update.effective_user
    if not is_allowed(user.id, user.username):
        return
    
    result = await send_to_clawd("ping", user.id)
    if result.get("status") == "completed":
        ts = result.get("result", {}).get("timestamp", "unknown")
        await update.message.reply_text(f"🏓 Pong! Server time: {ts}")
    else:
        await update.message.reply_text(f"❌ Error: {result.get('error')}")

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
    if result.get("status") == "completed":
        data = result.get("result", {})
        await update.message.reply_text(
            f"🌐 Fetched: {data.get('url')}\n"
            f"Status: {data.get('status_code')}\n"
            f"Length: {data.get('content_length')} chars\n\n"
            f"Preview:\n{data.get('content', '')[:1500]}"
        )
    else:
        await update.message.reply_text(f"❌ Error: {result.get('error')}")

async def research_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /research command - fetch URL and analyze with Claude."""
    user = update.effective_user
    if not is_allowed(user.id, user.username):
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /research <url>\n\nI'll fetch the URL and analyze its content.")
        return
    
    url = context.args[0]
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    # Step 1: Fetch the URL
    await update.message.reply_text(f"🔍 Fetching {url}...")
    fetch_result = await send_to_clawd(f"/fetch {url}", user.id)
    
    if fetch_result.get("status") != "completed":
        await update.message.reply_text(f"❌ Failed to fetch URL: {fetch_result.get('error')}")
        return
    
    content = fetch_result.get("result", {}).get("content", "")
    if not content:
        await update.message.reply_text("❌ No content retrieved from URL")
        return
    
    # Step 2: Send to Claude for analysis
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    await update.message.reply_text("🧠 Analyzing with Claude...")
    
    analysis_prompt = f"""Analyze this webpage content and provide:
1. A brief summary of what this page/site is about
2. Key information or offerings
3. Target audience
4. Any notable observations or suggestions

URL: {url}

Content:
{content[:8000]}"""
    
    result = await send_to_claude(analysis_prompt, user.id)
    
    if result.get("status") == "completed":
        analysis = result.get("result", {}).get("summary", "No analysis generated")
        await update.message.reply_text(f"📊 **Analysis of {url}**\n\n{analysis[:4000]}")
    else:
        await update.message.reply_text(f"❌ Analysis failed: {result.get('error')}")

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /analyze command - deep dive analysis of URL or text."""
    user = update.effective_user
    if not is_allowed(user.id, user.username):
        return
    
    if not context.args:
        await update.message.reply_text(
            "Usage: /analyze <url or text>\n\n"
            "Deep analysis options:\n"
            "• URL: Full SEO, technical, content, and competitive analysis\n"
            "• Text: Sentiment, tone, key themes, and actionable insights\n\n"
            "Example: /analyze https://example.com"
        )
        return
    
    input_text = " ".join(context.args)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    # Check if it's a URL
    is_url = input_text.startswith("http://") or input_text.startswith("https://")
    
    if is_url:
        # Deep URL analysis
        await update.message.reply_text(f"🔬 Deep analyzing {input_text}...")
        fetch_result = await send_to_clawd(f"/fetch {input_text}", user.id)
        
        if fetch_result.get("status") != "completed":
            await update.message.reply_text(f"❌ Failed to fetch URL: {fetch_result.get('error')}")
            return
        
        content = fetch_result.get("result", {}).get("content", "")
        if not content:
            await update.message.reply_text("❌ No content retrieved from URL")
            return
        
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        analysis_prompt = f"""Perform a comprehensive deep-dive analysis of this webpage. Be thorough and actionable.

## URL: {input_text}

## Content:
{content[:12000]}

---

Provide analysis in these sections:

### 1. EXECUTIVE SUMMARY
One paragraph overview of what this is and its purpose.

### 2. CONTENT ANALYSIS
- Main message and value proposition
- Content quality and clarity
- Call-to-actions present
- Missing content that should be added

### 3. SEO & TECHNICAL
- Title and meta description effectiveness
- Keyword opportunities
- Structure and hierarchy
- Mobile/accessibility considerations

### 4. COMPETITIVE POSITIONING
- Unique differentiators
- Industry positioning
- Strengths vs typical competitors
- Weaknesses or gaps

### 5. USER EXPERIENCE
- First impression
- Navigation and flow
- Trust signals present
- Conversion optimization opportunities

### 6. ACTIONABLE RECOMMENDATIONS
Top 5 specific, prioritized improvements with expected impact.

Be specific, cite examples from the content, and provide actionable advice."""
        
    else:
        # Deep text analysis
        await update.message.reply_text("🔬 Deep analyzing text...")
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        analysis_prompt = f"""Perform a comprehensive deep-dive analysis of this text. Be thorough and actionable.

## Text to analyze:
{input_text}

---

Provide analysis in these sections:

### 1. SUMMARY
What is this text about? Key points in 2-3 sentences.

### 2. SENTIMENT & TONE
- Overall sentiment (positive/negative/neutral) with confidence %
- Tone characteristics (formal, casual, urgent, etc.)
- Emotional undertones detected

### 3. KEY THEMES & TOPICS
- Main themes identified
- Important keywords and phrases
- Subject matter expertise level

### 4. AUDIENCE ANALYSIS
- Intended audience
- Reading level required
- Cultural or contextual assumptions

### 5. STRENGTHS & WEAKNESSES
- What works well in this text
- What could be improved
- Clarity and coherence assessment

### 6. ACTIONABLE INSIGHTS
- Key takeaways
- Suggested next steps or responses
- Questions this raises

Be specific and provide examples from the text."""
    
    result = await send_to_claude(analysis_prompt, user.id)
    
    if result.get("status") == "completed":
        analysis = result.get("result", {}).get("summary", "No analysis generated")
        # Split long responses into multiple messages if needed
        if len(analysis) > 4000:
            parts = [analysis[i:i+4000] for i in range(0, len(analysis), 4000)]
            for i, part in enumerate(parts[:3]):  # Max 3 parts
                await update.message.reply_text(part)
        else:
            await update.message.reply_text(f"🔬 **Deep Analysis**\n\n{analysis}")
    else:
        await update.message.reply_text(f"❌ Analysis failed: {result.get('error')}")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming photos - analyze with Claude Vision."""
    user = update.effective_user
    
    # Security check
    if not is_allowed(user.id, user.username):
        await update.message.reply_text(f"⛔ Not authorized. Your ID: {user.id}")
        return
    
    # Rate limit check
    if not check_rate_limit(user.id):
        await update.message.reply_text("⏳ Rate limit exceeded. Please wait a moment.")
        return
    
    # Get the photo (largest size)
    photo = update.message.photo[-1]  # Last element is highest resolution
    caption = update.message.caption or ""
    
    log.info(f"Photo from {user.id} (@{user.username}), caption: {caption[:50]}...")
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    await update.message.reply_text("📸 Analyzing image...")
    
    try:
        # Download the photo
        file = await context.bot.get_file(photo.file_id)
        photo_bytes = await file.download_as_bytearray()
        
        # Convert to base64
        image_base64 = base64.b64encode(photo_bytes).decode('utf-8')
        
        # Determine media type (Telegram photos are usually JPEG)
        media_type = "image/jpeg"
        
        # Build analysis prompt
        if caption:
            prompt = f"""Analyze this image based on the user's request: "{caption}"

Provide a detailed, helpful response addressing what they asked about."""
        else:
            prompt = """Analyze this image comprehensively:

1. **What's in the image**: Describe what you see
2. **Key details**: Important text, numbers, people, objects
3. **Context**: What's happening, what this appears to be
4. **Insights**: Any notable observations or actionable information

If this is a screenshot of text/social media/document, extract and summarize the key information."""
        
        # Send to Claude with image
        result = await send_to_claude(prompt, user.id, image_data=image_base64, image_media_type=media_type)
        
        if result.get("status") == "completed":
            analysis = result.get("result", {}).get("summary", "No analysis generated")
            # Split long responses
            if len(analysis) > 4000:
                parts = [analysis[i:i+4000] for i in range(0, len(analysis), 4000)]
                for part in parts[:3]:
                    await update.message.reply_text(part)
            else:
                await update.message.reply_text(f"🖼️ **Image Analysis**\n\n{analysis}")
        else:
            await update.message.reply_text(f"❌ Analysis failed: {result.get('error')}")
            
    except Exception as e:
        log.error(f"Photo analysis error: {e}")
        await update.message.reply_text(f"❌ Error processing image: {e}")

def main():
    if not BOT_TOKEN:
        log.error("TELEGRAM_BOT_TOKEN not set!")
        return
    
    log.info("=" * 60)
    log.info("Telegram Gateway for Zulu Clawd-Runner")
    log.info(f"  Clawd URL: {CLAWD_URL}")
    log.info(f"  MoltWorker: {MOLTWORKER_URL or 'not configured'}")
    log.info(f"  CF Access: {'configured' if CF_ACCESS_CLIENT_ID else 'not configured'}")
    log.info(f"  Allowed users: {ALLOWED_USERS}")
    log.info(f"  Rate limit: {RATE_LIMIT_PER_MINUTE}/min")
    log.info("=" * 60)
    
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("ping", ping_command))
    app.add_handler(CommandHandler("fetch", fetch_command))
    app.add_handler(CommandHandler("research", research_command))
    app.add_handler(CommandHandler("analyze", analyze_command))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start polling
    log.info("Starting Telegram bot...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
