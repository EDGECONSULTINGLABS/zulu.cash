# ZULU

Zulu is a **local-first execution harness for AI systems**.

It sits *below agents and applications* and *above the operating system*,
enforcing privacy, integrity, and control for AI running on-device.

Zulu is not an agent framework.
It is the environment agents run inside — and the governor that keeps them honest.

📄 [Architecture](ARCHITECTURE.md) · 🔒 [Security](SECURITY.md) · 🚀 [Deploy](DEPLOY.md)

---

## Why Zulu exists

Most AI systems assume cloud execution, loose data boundaries, trust-by-brand, and non-reproducible runs.

Zulu replaces assumptions with enforcement.

If an AI system runs inside Zulu, you can prove what data it accessed, what it was allowed to do, that memory stayed local, and that the system was not tampered with.

---

## What Zulu does now

Zulu delegates tasks to fenced AI workers on your behalf — while you sleep, while you work, while you live.

You send a message. Zulu interprets it, scopes the work, dispatches it to a contained execution engine, and delivers results back to you. The agent never touches your data directly. Credentials are short-lived. Every action is audited. Nothing persists that you didn't authorize.

```
You (Telegram / messaging)
    │
    ▼
Zulu — interprets intent, plans tasks, holds authority
    │
    ▼
OpenClaw NightShift — fenced execution, no persistence, no escalation
    │
    ▼
Results — delivered back through Zulu, logged, verifiable
```

This is governed AI labor: scoped, auditable, and containment-first.

---

## Where Zulu fits

```
Applications / Messaging (Telegram, etc.)
    ↑
Zulu Task Planner — intent parsing, decomposition, chaining
    ↑
Zulu Adapter — credential lifecycle, retry, audit enforcement
    ↑
🔒 ZULU EXECUTION HARNESS
    • policy enforcement
    • encrypted local memory
    • deterministic installs
    • integrity verification
    ↑
OpenClaw NightShift — bounded worker (replaceable)
    ↑
OS / Hardware
```

---

## Harness capabilities

**Execution guarantees:**
Local-only execution by default. Encrypted, structured memory via SQLCipher (not prompt stuffing). Deterministic installs and runs. Integrity verification that detects single-bit tampering. Explicit data and tool permissions per task.

**Task delegation:**
Natural language to concrete task graphs. Automatic decomposition of complex requests into dependent subtasks. Result extraction between chained tasks. Credential-scoped execution with bounded retry. Full audit trail from request to delivery.

**Model-agnostic:**
Ships with Anthropic Claude as the default. Swap to Ollama, OpenAI, Groq, or Gemini via environment config. Per-role model selection — use a fast model for intent classification, a strong model for planning, a cheap model for extraction.

**Agent-agnostic:**
OpenClaw is the default execution engine. Replace it with any worker that respects the adapter contract. The airlock stays the same regardless of what runs behind it.

---

## Architecture

Zulu's security model separates authority from execution:

**Zulu (authority layer)** owns credentials, owns retry logic, owns the audit log, owns task lifecycle, and owns the kill switch. Zulu decides what happens and enforces how it happens.

**OpenClaw NightShift (execution layer)** is a bounded worker. It runs in its own container with no persistent storage, no network access beyond an allowlist, no ability to escalate permissions, and no self-direction. It does what Zulu tells it to do and returns results.

**The adapter** is the contract between them. It enforces credential TTL, validates inputs before dispatch, categorizes errors, manages connection pooling with retry, and maintains a bounded audit log. The adapter is also the swap boundary — change what runs behind it without changing Zulu.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full trust model, network topology, and deployment checklist.

---

## Model provider configuration

Zulu uses a provider abstraction that reads from environment variables at runtime, not at import time.

```bash
# Provider selection
ZULU_LLM_PROVIDER=anthropic    # or: ollama, openai, groq, gemini

# API key (provider-specific)
ANTHROPIC_API_KEY=sk-ant-...

# Per-role model selection
ZULU_INTENT_MODEL=claude-haiku-4-5-20251001        # fast classification
ZULU_PLANNING_MODEL=claude-sonnet-4-5-20250929      # reasoning for decomposition
ZULU_EXTRACTION_MODEL=claude-haiku-4-5-20251001     # between-task extraction

# Execution credentials (separate from planning)
ZULU_EXECUTION_API_KEY=sk-ant-...
```

Self-hosted users can point all three roles at the same Ollama model. Production deployments can optimize cost and latency per step.

---

## Quick start

### Requirements

- Python 3.10+
- Docker and Docker Compose
- Anthropic API key (or Ollama for local inference)

### Setup

```bash
# Clone and configure
git clone https://github.com/EDGECONSULTINGLABS/zulu.cash.git
cd zulu.cash
cp .env.example .env
# Edit .env with your API keys

# Start clawd-runner
docker compose up -d clawd-runner

# Set environment and run bot
export TELEGRAM_BOT_TOKEN="your-bot-token"
export ANTHROPIC_API_KEY="your-api-key"
export TELEGRAM_ALLOWED_USERS="your-telegram-id"
python3 telegram_gateway/zulu_bot.py
```

---

## Repository structure

```
zulu/
├── zulu_task_planner.py         # Intent → task graph decomposition
├── zulu_model_provider.py       # LLM provider abstraction (5 providers)
├── zulu_openclaw_adapter.py     # Adapter contract + enforcement layer
├── telegram_gateway/            # Telegram bot integration
│   └── zulu_bot.py
├── clawd_runner/                # Clawd execution service
├── nightshift-openclaw/         # OpenClaw NightShift worker
├── hardening/                   # Security and audit modules
├── watchdog/                    # Task monitoring and kill switch
├── docker-compose.yml           # Full stack deployment
├── ARCHITECTURE.md              # Trust model and security
├── SECURITY.md                  # Security documentation
└── DEPLOY.md                    # Deployment guide
```

---

## Who Zulu is for

**Entrepreneurs and founders** who need AI working for them around the clock — research, analysis, document drafting — without giving up control of their data or trusting a black-box cloud service.

**Builders shipping local-first AI** who need an execution environment with real guarantees, not just promises.

**Enterprises handling sensitive data** in regulated workflows where audit trails and data provenance are not optional.

---

## What Zulu is not

Zulu is not an agent framework, not a cloud AI service, not a model provider, not a blockchain, and not a SaaS platform.

It is the environment that makes AI systems trustworthy by construction.

---

## License

MIT License
