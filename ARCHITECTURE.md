# ZULU.CASH — System Architecture

## Overview

Zulu is a **governed AI execution system** that delegates work to constrained agent workers while maintaining full authority over task dispatch, secrets, and audit.

This is not an "AI assistant" — it's an **airlock architecture** for safely running AI labor.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ZULU ARCHITECTURE                               │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         AUTHORITY LAYER                              │   │
│  │                                                                      │   │
│  │   ┌──────────────────────────────────────────────────────────────┐  │   │
│  │   │                        ZULU CORE                              │  │   │
│  │   │                                                               │  │   │
│  │   │  • Owns all secrets (API keys, credentials)                   │  │   │
│  │   │  • Owns task policy (what can run, what can't)                │  │   │
│  │   │  • Owns audit truth (immutable task log)                      │  │   │
│  │   │  • Owns the clock (no autonomous scheduling)                  │  │   │
│  │   │  • Routes tasks to appropriate executor                       │  │   │
│  │   │                                                               │  │   │
│  │   └──────────────────────────────────────────────────────────────┘  │   │
│  │                              │                                       │   │
│  │                              │ TaskDispatcher                        │   │
│  │                              │ (zulu_openclaw_adapter.py)            │   │
│  │                              ▼                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                 │                                           │
│  ┌──────────────────────────────┼───────────────────────────────────────┐   │
│  │                         EXECUTION LAYER                               │   │
│  │                              │                                        │   │
│  │         ┌────────────────────┴────────────────────┐                  │   │
│  │         │                                         │                  │   │
│  │         ▼                                         ▼                  │   │
│  │  ┌─────────────────┐                    ┌─────────────────────┐     │   │
│  │  │  clawd-runner   │                    │ openclaw-nightshift  │     │   │
│  │  │                 │                    │                      │     │   │
│  │  │  Fast tasks:    │                    │  Complex tasks:      │     │   │
│  │  │  • web_fetch    │                    │  • web_research      │     │   │
│  │  │  • summarize    │                    │  • doc_synthesis     │     │   │
│  │  │  • transform    │                    │  • comparative       │     │   │
│  │  │                 │                    │  • report_drafting   │     │   │
│  │  │  Python/aiohttp │                    │  • code_review       │     │   │
│  │  │  Stateless      │                    │                      │     │   │
│  │  │                 │                    │  Real OpenClaw Pi    │     │   │
│  │  │                 │                    │  Single-shot mode    │     │   │
│  │  └─────────────────┘                    └─────────────────────┘     │   │
│  │                                                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                         MONITORING LAYER                              │   │
│  │                                                                       │   │
│  │   ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │   │
│  │   │    watchdog     │    │   audit log     │    │  NightShift     │  │   │
│  │   │                 │    │                 │    │  dispatcher     │  │   │
│  │   │  • Kill switch  │    │  • Task events  │    │                 │  │   │
│  │   │  • Resource mon │    │  • Rejections   │    │  • Cron/queue   │  │   │
│  │   │  • Timeout kill │    │  • Completions  │    │  • Batch jobs   │  │   │
│  │   │                 │    │  • Errors       │    │  • Reports      │  │   │
│  │   └─────────────────┘    └─────────────────┘    └─────────────────┘  │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Core Principles

### 1. Zulu Decides. Workers Execute.

Workers (clawd-runner, openclaw-nightshift) have **zero authority**:
- Cannot access secrets directly
- Cannot spawn follow-up tasks
- Cannot modify their own prompts
- Cannot persist memory across tasks
- Cannot schedule future work

All decisions flow from Zulu. Workers are **runtimes, not authorities**.

### 2. Explicit Trust Boundaries

Every component has a defined trust level:

| Component | Internet | Secrets | Can Spawn Tasks | Persistence |
|-----------|----------|---------|-----------------|-------------|
| zulu-core | ❌ None | ✅ Full | ✅ Yes | ✅ SQLite |
| ollama | ❌ None | ❌ None | ❌ No | Model weights only |
| clawd-runner | ⚠️ Limited | ❌ None | ❌ No | ❌ Ephemeral |
| openclaw-nightshift | ⚠️ Limited | ❌ None | ❌ No | ❌ Ephemeral |
| watchdog | ❌ None | ❌ None | ❌ No | Audit log only |
| telegram-gateway | ✅ Yes | Bot token only | ❌ No | ❌ None |

### 3. Scoped Credentials

API keys are **never stored in workers**. Instead:

1. Zulu creates `ScopedCredentials` with TTL
2. Credentials are passed per-task in the request
3. Worker uses credentials for that task only
4. Credentials expire after task completion
5. Worker workspace is wiped

```python
credentials = ScopedCredentials(
    llm_api_key="sk-...",
    llm_provider="anthropic",
    issued_at="2026-02-04T22:00:00Z",  # TTL enforced
)
```

### 4. Defense in Depth

Multiple independent safety layers:

| Layer | Mechanism | Failure Mode |
|-------|-----------|--------------|
| Policy | `TaskPolicy.validate()` | Task rejected before dispatch |
| Adapter | Input validation, TTL check | Request rejected at adapter |
| Worker | Tool allowlist, domain allowlist | Action blocked at execution |
| Timeout | Local + watchdog enforcement | Task killed |
| Audit | Immutable log | Forensic trail preserved |
| Network | Docker network isolation | No lateral movement |

---

## Component Details

### Zulu Core

**Location:** `zulu-core` container  
**Network:** `zulu_internal` (no internet)  
**Secrets:** Full access via Docker secrets

Responsibilities:
- Task queue management
- Policy enforcement
- Secret injection (scoped, per-task)
- Audit log persistence
- Executor routing (clawd vs openclaw)

### OpenClaw NightShift

**Location:** `openclaw-nightshift` container  
**Network:** `clawd_dmz` (limited internet), `shared_bus`, `inference_bus`  
**Secrets:** None (passed per-task)

This is the **real OpenClaw Pi agent** running in constrained mode:

```
STRIPPED (disabled):
  ├── Gateway (WebSocket control plane)
  ├── All messaging channels
  ├── Persistent memory
  ├── ClawHub skill registry
  ├── Browser control (CDP)
  └── Cron/scheduling

KEPT (enabled):
  ├── Pi agent runtime
  ├── Tool execution (within allowlist)
  ├── Web research (within domain allowlist)
  ├── Document synthesis
  └── Structured output
```

### Zulu → OpenClaw Adapter

**Location:** `zulu_openclaw_adapter.py`  
**Purpose:** Contract enforcement between Zulu and OpenClaw

Key features:
- **Input validation** on construction (fail fast)
- **Credential TTL** enforcement
- **Connection pooling** with async lock
- **Retry with backoff** on transient failures
- **Bounded audit log** (no memory leaks)
- **Structured error codes** for precise handling

```python
adapter = ZuluOpenClawAdapter(
    audit_flush_callback=persist_to_sqlcipher
)

response = await adapter.dispatch(OpenClawRequest(
    task_id="research-001",
    task_type=OpenClawTaskType.WEB_RESEARCH,
    prompt="Research privacy-preserving AI techniques",
    tool_allowlist=ToolAllowlist(web_browse=True, llm_chat=True),
    domain_allowlist=["arxiv.org", "*.edu"],
    credentials=scoped_creds,
    timeout_seconds=300,
))
```

### NightShift Dispatcher

**Location:** `nightshift_dispatcher.py`  
**Purpose:** Cron/queue-based batch job execution

Features:
- SQLite-backed task queue
- Quiet hours enforcement (configurable)
- Priority-based task ordering
- "Work done while you slept" reports
- Zero autonomy (tasks are pre-defined)

```bash
# Add task to queue
python nightshift_dispatcher.py --add \
    --type web_research \
    --prompt "Research ZK proof systems for AI inference"

# Run daemon (checks every 30 min during quiet hours)
python nightshift_dispatcher.py --daemon --interval 1800
```

---

## Network Topology

```
┌─────────────────────────────────────────────────────────────────┐
│                         HOST MACHINE                             │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              zulu_internal (NO INTERNET)                    │ │
│  │                                                             │ │
│  │   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐   │ │
│  │   │  zulu-core  │    │   ollama    │    │  watchdog   │   │ │
│  │   │  (secrets)  │    │   (LLM)     │    │  (monitor)  │   │ │
│  │   └──────┬──────┘    └──────┬──────┘    └─────────────┘   │ │
│  │          │                  │                              │ │
│  └──────────┼──────────────────┼──────────────────────────────┘ │
│             │                  │                                 │
│  ┌──────────┼──────────────────┼──────────────────────────────┐ │
│  │          │   shared_bus     │   inference_bus              │ │
│  │          │   (task dispatch)│   (LLM inference)            │ │
│  └──────────┼──────────────────┼──────────────────────────────┘ │
│             │                  │                                 │
│  ┌──────────┼──────────────────┼──────────────────────────────┐ │
│  │          ▼                  ▼        clawd_dmz              │ │
│  │   ┌─────────────┐    ┌─────────────────┐                   │ │
│  │   │clawd-runner │    │openclaw-nightshift│  ← LIMITED      │ │
│  │   │             │    │                  │    INTERNET      │ │
│  │   └─────────────┘    └─────────────────┘                   │ │
│  │                                                             │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Task Flow

```
1. Request arrives (Telegram, API, NightShift queue)
        │
2. Zulu validates against TaskPolicy
        │ ← rejected tasks logged and dropped
        │
3. TaskPolicy.EXECUTOR_ROUTING determines target
        │
        ├─── Simple task ──→ clawd-runner
        │
        └─── Complex task ─→ openclaw-nightshift
                                    │
4. Adapter builds scoped request    │
        │                           │
        ├── Validates inputs        │
        ├── Checks credential TTL   │
        ├── Injects tool allowlist  │
        └── Injects domain allowlist│
                                    │
5. HTTP POST to executor ───────────┘
        │
6. Executor runs with local timeout
        │
7. Watchdog independently monitors
        │
8. Result returned to Zulu
        │
9. Audit logged (immutable)
        │
10. Workspace wiped
```

---

## Security Guarantees

### What Zulu Prevents

| Attack Vector | Mitigation |
|---------------|------------|
| Credential theft | Scoped per-task, TTL enforced, never persisted |
| Autonomous loops | Single-shot execution, no self-scheduling |
| Lateral movement | Network isolation, no shared volumes |
| Resource exhaustion | Watchdog kills, container limits |
| Prompt injection | Fixed system prompts, output schema enforcement |
| Data exfiltration | Domain allowlist, audit logging |

### What Zulu Does NOT Prevent

| Risk | Status |
|------|--------|
| Malicious task content | Operator responsibility |
| LLM hallucination | Inherent to LLMs |
| Denial of service (self) | Rate limiting recommended |
| Secrets in task output | Audit log review needed |

---

## File Structure

```
zulu-secure-docker/
├── docker-compose.yml          # Full stack definition
├── ARCHITECTURE.md             # This file
├── SECURITY.md                 # Security model details
├── DEPLOY.md                   # Deployment guide
│
├── zulu_openclaw_adapter.py    # Zulu → OpenClaw contract
├── nightshift_dispatcher.py    # Cron/queue dispatcher
├── task_contract.py            # Task types and policy
│
├── Dockerfile.zulu             # Zulu core container
├── Dockerfile.openclaw-nightshift  # OpenClaw worker
├── Dockerfile.telegram         # Telegram gateway
├── Dockerfile.clawd            # Clawd runner
├── Dockerfile.watchdog         # Kill switch
│
├── nightshift-openclaw/
│   └── server.mjs              # OpenClaw NightShift adapter
│
├── telegram_gateway/
│   └── bot.py                  # Telegram bot
│
├── clawd_runner/
│   └── server.py               # Clawd executor
│
├── watchdog/
│   └── monitor.py              # Resource monitor + kill switch
│
├── openclaw_worker/
│   └── server.py               # Python OpenClaw worker (alt)
│
└── secrets/                    # Docker secrets (gitignored)
    ├── anthropic_api_key.txt
    ├── telegram_bot_token.txt
    └── ...
```

---

## Deployment Checklist

### Before First Deploy

- [ ] Run `./setup-secrets.sh`
- [ ] Replace placeholder secrets with real values
- [ ] Verify `.gitignore` includes `secrets/`
- [ ] Review `TaskPolicy.ALLOWED_DOMAINS`
- [ ] Review `TOOL_ALLOWLISTS` in nightshift server
- [ ] Set resource limits for your hardware
- [ ] Pull Ollama model: `docker exec zulu-ollama ollama pull llama3.1:8b`

### Starting the Stack

```bash
# Build and start all services
docker-compose up -d --build

# Check health
docker-compose ps
docker logs openclaw-nightshift --tail 50

# Test OpenClaw
curl http://localhost:8090/health
```

### Adding NightShift Tasks

```bash
# Add a research task
python nightshift_dispatcher.py --add \
    --type web_research \
    --prompt "Research zero-knowledge proofs for ML inference" \
    --priority 5

# List pending tasks
python nightshift_dispatcher.py --list

# Run immediately (ignore quiet hours)
python nightshift_dispatcher.py --once --force
```

---

## Why This Architecture

### vs. "Just run Claude/GPT directly"

Direct API calls have no:
- Task policy enforcement
- Credential scoping
- Audit trail
- Kill switch
- Network isolation

### vs. "Just use LangChain agents"

LangChain agents are designed for autonomy. This architecture is designed for **governance**.

### vs. "Just containerize everything"

Containers isolate processes. This architecture isolates **trust boundaries**.

The difference:
- Container: "This process can't see that process's memory"
- Airlock: "This agent can't access secrets, can't spawn tasks, can't persist, and will be killed if it misbehaves"

---

## Future Directions

1. **MoltBot integration** — Lighter-weight executor for simple tasks
2. **Multi-tenant support** — Per-user task queues and credential vaults
3. **Encrypted audit log** — SQLCipher for at-rest encryption
4. **Remote attestation** — Prove task execution integrity
5. **Cost tracking** — Per-task LLM token accounting

---

## License

MIT License. See LICENSE file.

---

*Built for the Zcash ecosystem. Privacy-first AI infrastructure.*
