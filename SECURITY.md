# ZULU.CASH — Security Architecture

## Airlock Model

This deployment uses an **airlock architecture**, not just containers.
The difference: containers isolate processes; airlocks isolate *trust boundaries*.

```
┌───────────────────────────────────────────────────────────────────────┐
│                            HOST MACHINE                               │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │              zulu_internal (NO INTERNET)                        │  │
│  │                                                                 │  │
│  │   ┌──────────────┐      ┌──────────────────┐                   │  │
│  │   │  zulu-core    │      │     ollama        │                  │  │
│  │   │              │      │                   │                  │  │
│  │   │  • Policy     │◄────►│  • Local LLM      │                  │  │
│  │   │  • Secrets    │      │  • GPU inference   │                  │  │
│  │   │  • Task queue │      │  • No internet     │                  │  │
│  │   │  • Audit log  │      │                   │                  │  │
│  │   └──────┬───────┘      └──────────────────┘                   │  │
│  │          │                        │                             │  │
│  │   ┌──────────────┐               │ inference_bus (NO INTERNET) │  │
│  │   │  watchdog     │ (monitors     │ (Ollama ↔ OpenClaw only)   │  │
│  │   │              │  + kills)     │                             │  │
│  │   └──────────────┘               │                             │  │
│  └──────────┼───────────────────────┼─────────────────────────────┘  │
│             │ shared_bus             │                                │
│             │ (internal only)        │                                │
│  ┌──────────┼────────────────────────┼────────────────────────────┐  │
│  │          ▼            clawd_dmz   │   (LIMITED INTERNET)       │  │
│  │   ┌──────────────┐   ┌───────────┴─────────┐                  │  │
│  │   │ clawd-runner  │   │ openclaw-nightshift  │                 │  │
│  │   │              │   │ (real OpenClaw Pi)   │                  │  │
│  │   │ • web_fetch   │   │ • web_research      │                  │  │
│  │   │ • summarize   │   │ • doc_synthesis     │                  │  │
│  │   │ • transform   │   │ • report_drafting   │                  │  │
│  │   │ • No secrets  │   │ • code_review       │                  │  │
│  │   │ • Ephemeral   │   │ • Ollama inference  │                  │  │
│  │   │              │   │ • No Gateway        │                  │  │
│  │   │              │   │ • No memory         │                  │  │
│  │   └──────────────┘   └─────────────────────┘                   │  │
│  └────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────┘
```

### Network Isolation Matrix

| Network        | Internet | Purpose                        | Members                              |
|----------------|----------|--------------------------------|--------------------------------------|
| zulu_internal  | ❌ None   | Control plane + secrets        | zulu-core, ollama, watchdog          |
| shared_bus     | ❌ None   | Task dispatch only             | zulu-core, clawd, openclaw           |
| inference_bus  | ❌ None   | LLM inference (Ollama access)  | ollama, openclaw                     |
| clawd_dmz      | ✅ Limited| External resource fetching     | clawd, openclaw                      |

## Trust Boundaries

| Component | Trusts | Trusted By | Internet | Secrets | UID |
|-----------|--------|------------|----------|---------|-----|
| zulu-core | Ollama | Host operator | None | Full | 1000 |
| ollama | — | zulu-core | None | None | root* |
| clawd-runner | — | Nobody | Limited | None | 1001 |
| openclaw-nightshift | — | Nobody | Limited | None | 1003 |
| watchdog | Docker API (RO) | zulu-core | None | None | 1002 |

*Ollama requires root for GPU access but has no internet and no secrets.

## The Golden Rule

> **Zulu decides. Clawd executes. OpenClaw executes. Nothing else.**

## Two Executor Model

Zulu dispatches tasks to two separate workers based on complexity:

**clawd-runner** handles lightweight, fast tasks (web_fetch, summarize, transform).
Stateless Python service. Simple request/response.

**openclaw-nightshift** handles complex, multi-step tasks (web_research,
document_synthesis, comparative_analysis, report_drafting, code_review).
Stripped OpenClaw runtime running as a single-shot executor.
No Gateway, no channels, no persistent memory, no self-scheduling.

Both workers receive scoped tasks from Zulu via `shared_bus`, have limited
internet via `clawd_dmz`, run as different non-root users, have read-only
filesystems with tmpfs workspaces, wipe workspace after every task, and
are monitored by the watchdog.

## OpenClaw: What's Stripped vs. Kept

```
STRIPPED (disabled at container + code level):
  Gateway (WebSocket control plane)
  All messaging channels (WhatsApp, Telegram, Discord, etc.)
  Persistent sessions / memory
  ClawHub skill registry (no auto-pulling new skills)
  Canvas / A2UI (visual workspace)
  Browser control (CDP)
  Cron / scheduling (Zulu owns the clock)
  Pi coding agent's autonomous loop
  Self-reflection / self-prompting
  Task spawning / chaining

KEPT:
  Core tool execution runtime
  Single-shot task processing
  Structured output formatting
  HTTP task endpoint (receives from Zulu)
```

OpenClaw is a **runtime, not an authority**. If it can decide its own
next step, you've lost the airlock.


## Security Controls

### Container Hardening (all services)
- `privileged: false` (implicit — never set to true)
- `cap_drop: ALL` on every container
- `read_only: true` filesystem
- `no-new-privileges` security option
- Non-root users (separate UIDs: 1000, 1001, 1002, 1003)
- Resource limits (CPU + memory) on every container
- No Docker socket mounting (except watchdog, read-only)

### Network Isolation
- `zulu_internal`: `internal: true` — zero internet access
- `clawd_dmz`: limited egress (firewall/proxy recommended)
- `shared_bus`: `internal: true` — Zulu to executors only
- No `host` network mode
- No default bridge network
- Separate subnets per network (172.28.1.0/24, .2.0/24, .3.0/24)

### Secrets Management
- Docker secrets (file-based in dev, Swarm-native in prod)
- Secrets mounted at `/run/secrets/` (read-only, in-memory tmpfs)
- Only zulu-core has secrets access
- Clawd and OpenClaw receive scoped, one-time credentials per task
- No `.env` files in production
- `setup-secrets.sh` generates keys + enforces .gitignore

### Task Contract (Zulu to Executors)
- Exhaustive task type allowlist per executor
- Per-type timeout limits
- URL domain allowlist for web_fetch
- Tool allowlist per NightShift task type
- Basic prompt injection detection
- Blocked task type denylist (infra_change, wallet_operation, etc.)
- Policy validation before dispatch
- Audit logging on every task lifecycle event
- Automatic routing: Zulu to clawd or Zulu to openclaw based on type

### Kill Switch (Watchdog)
- Monitors BOTH clawd-runner AND openclaw-nightshift
- Per-container memory threshold monitoring
- Per-container sustained CPU threshold monitoring
- Automatic container restart on violation
- Structured JSONL audit logs with container identification
- NightShift-safe: kills runaway tasks at 3am without human intervention
- Configurable kill action (restart or stop)

### OpenClaw-Specific Controls
- Gateway disabled via env var (`OPENCLAW_GATEWAY=disabled`)
- All channels disabled (`OPENCLAW_CHANNELS=disabled`)
- Memory disabled (`OPENCLAW_MEMORY=disabled`)
- ClawHub disabled (`OPENCLAW_CLAWHUB=disabled`)
- Cron disabled (`OPENCLAW_CRON=disabled`)
- Browser disabled (`OPENCLAW_BROWSER=disabled`)
- Constrained system prompt injected per task
- `maxTurns: 1` (single turn only, no autonomous loops)
- Output schema enforced per task type

## Task Dispatch Flow

```
1. Zulu receives work request (user, NightShift schedule, or API)
        |
2. TaskPolicy.validate() — checks allowlist, timeout, domain rules
        | (rejected tasks logged and dropped)
3. TaskPolicy.EXECUTOR_ROUTING — determines clawd vs openclaw
        |
4. TaskDispatcher builds scoped payload:
   - clawd: {task_id, task_type, params, scoped_credentials}
   - openclaw: {task_id, task_type, prompt, output_schema, scoped_credentials}
        |
5. HTTP POST to executor on shared_bus
        |
6. Executor runs with local timeout enforcement
        |
7. Watchdog independently monitors resource usage
        |
8. Result returned to Zulu -> audit logged -> workspace wiped
```


## Operational Checklist

### Before First Deploy
- Run `./setup-secrets.sh`
- Replace placeholder secrets with real values
- Verify `.gitignore` includes `secrets/`
- Review `TaskPolicy.ALLOWED_DOMAINS` for your use case
- Review `TOOL_ALLOWLISTS` in nightshift server.mjs
- Set appropriate resource limits for your hardware
- Pull Ollama model: `docker exec zulu-ollama ollama pull phi3:mini`

### Weekly
- Review `watchdog-audit.jsonl` for kill events
- Review `audit.jsonl` for rejected tasks
- Rotate secrets (especially if any were exposed)
- Check for Docker image updates (`docker compose pull`)
- Review NightShift task logs for anomalies

### On Incident
1. `docker compose stop clawd-runner openclaw-nightshift` (immediate isolation)
2. Review watchdog audit log — which container triggered?
3. Review Zulu audit log — what task was dispatched?
4. Check if any secrets were in task payloads (they shouldn't be)
5. Rotate all secrets as precaution
6. Restart with `docker compose up -d`


## What This Does NOT Protect Against

Be honest about limits:

- **Compromised host OS**: If the host is owned, containers won't save you
- **Supply chain attacks**: Malicious base images, npm packages, or pip packages
- **Side-channel attacks**: Timing, cache, speculative execution
- **Ollama model poisoning**: If the model itself is adversarial
- **OpenClaw upstream changes**: Pin your fork to a specific commit hash
- **LLM prompt injection at runtime**: Basic detection exists, but not bulletproof
- **Physical access**: Self-explanatory

For these, you need additional layers (secure boot, image signing, air-gapped
hardware, reproducible builds, etc.) that are outside the scope of this
Docker configuration.


## CI Safety Gate (Recommended)

Add to `.github/workflows/security-lint.yml`:

```yaml
name: Security Lint
on: [push, pull_request]
jobs:
  docker-socket-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Block Docker socket mounts
        run: |
          if grep -r 'docker.sock' --include='*.yml' --include='*.yaml' | \
             grep -v ':ro' | grep -v 'watchdog'; then
            echo "FAIL: Docker socket mounted without :ro outside watchdog"
            exit 1
          fi
      - name: Block privileged mode
        run: |
          if grep -r 'privileged: true' --include='*.yml' --include='*.yaml'; then
            echo "FAIL: Privileged mode detected"
            exit 1
          fi
      - name: Block host network
        run: |
          if grep -r 'network_mode.*host' --include='*.yml' --include='*.yaml'; then
            echo "FAIL: Host network mode detected"
            exit 1
          fi
```
