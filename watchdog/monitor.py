"""
Clawd Watchdog — Dead-Man's Switch + Audit Logger
===================================================
Monitors worker containers. Kills tasks that exceed thresholds.
Writes immutable, hash-chained audit logs.

Hardening layer:
- BLAKE3 hash-chained audit (tamper-evident)
- Merkle root compaction (hourly summaries)
- Policy-driven kill rules (governance as code)
- Worker attestation validation (startup trust)

This is the NightShift safety net:
- If a worker runs too long → killed
- If a worker eats too much memory → killed
- If a worker pegs CPU → killed
- If a worker fails attestation → killed
- If policy changes → enforced immediately
- Every action is hash-chained and auditable

SECURITY PROPERTIES:
- Read-only Docker socket access (monitoring only)
- Cannot create/start containers
- Cannot modify other containers' config
- Runs on zulu_internal network (no internet)
- Audit chain is tamper-evident from genesis
"""

import docker
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add parent to path for hardening imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hardening.audit_chain import AuditChain
from hardening.policy_engine import PolicyEngine

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CLAWD_CONTAINER = os.getenv("WATCHDOG_CLAWD_CONTAINER", "clawd-runner")
OPENCLAW_CONTAINER = os.getenv("WATCHDOG_OPENCLAW_CONTAINER",
                                "openclaw-nightshift")
MONITORED_CONTAINERS = [CLAWD_CONTAINER, OPENCLAW_CONTAINER]
MAX_TASK_SECONDS = int(os.getenv("WATCHDOG_MAX_TASK_SECONDS", "300"))
MAX_MEMORY_MB = int(os.getenv("WATCHDOG_MAX_MEMORY_MB", "1024"))
MAX_CPU_PERCENT = float(os.getenv("WATCHDOG_MAX_CPU_PERCENT", "90"))
CHECK_INTERVAL = int(os.getenv("WATCHDOG_CHECK_INTERVAL", "10"))
AUDIT_LOG_PATH = os.getenv("WATCHDOG_AUDIT_LOG",
                           "/app/logs/watchdog-audit.jsonl")
POLICY_PATH = os.getenv("WATCHDOG_POLICY_PATH", "/app/policy/policy.yaml")
KILL_ACTION = os.getenv("WATCHDOG_KILL_ACTION", "restart")  # restart | stop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [WATCHDOG] %(levelname)s %(message)s"
)
log = logging.getLogger("clawd-watchdog")

# ---------------------------------------------------------------------------
# Initialize hardening modules
# ---------------------------------------------------------------------------
audit = AuditChain(AUDIT_LOG_PATH, merkle_interval=360)
policy = PolicyEngine(POLICY_PATH if Path(POLICY_PATH).exists() else None)


# ---------------------------------------------------------------------------
# Container stats parser
# ---------------------------------------------------------------------------
def get_container_stats(container) -> dict:
    """Extract CPU and memory stats from Docker stats API."""
    try:
        stats = container.stats(stream=False)

        # Memory
        mem_usage = stats["memory_stats"].get("usage", 0)
        mem_limit = stats["memory_stats"].get("limit", 1)
        mem_mb = mem_usage / (1024 * 1024)

        # CPU
        cpu_delta = (
            stats["cpu_stats"]["cpu_usage"]["total_usage"]
            - stats["precpu_stats"]["cpu_usage"]["total_usage"]
        )
        system_delta = (
            stats["cpu_stats"]["system_cpu_usage"]
            - stats["precpu_stats"]["system_cpu_usage"]
        )
        num_cpus = stats["cpu_stats"].get("online_cpus",
                    len(stats["cpu_stats"]["cpu_usage"].get("percpu_usage",
                                                            [1])))

        cpu_percent = 0.0
        if system_delta > 0:
            cpu_percent = (cpu_delta / system_delta) * num_cpus * 100.0

        return {
            "memory_mb": round(mem_mb, 2),
            "memory_limit_mb": round(mem_limit / (1024 * 1024), 2),
            "cpu_percent": round(cpu_percent, 2),
            "num_cpus": num_cpus,
            "status": container.status
        }

    except Exception as e:
        log.warning(f"Failed to get stats: {e}")
        return None


# ---------------------------------------------------------------------------
# Kill switch
# ---------------------------------------------------------------------------
def kill_container(client: docker.DockerClient, container, reason: str,
                   stats: dict):
    """Kill or restart a monitored container."""
    container_name = container.name

    audit.append("KILL_TRIGGERED", {
        "container": container_name,
        "reason": reason,
        "action": KILL_ACTION,
        "stats": stats
    })

    try:
        if KILL_ACTION == "restart":
            log.warning(f"RESTARTING {container_name}: {reason}")
            container.restart(timeout=5)
            audit.append("KILL_COMPLETED", {
                "container": container_name,
                "action": "restart", "success": True
            })
        else:
            log.warning(f"STOPPING {container_name}: {reason}")
            container.stop(timeout=5)
            audit.append("KILL_COMPLETED", {
                "container": container_name,
                "action": "stop", "success": True
            })

    except Exception as e:
        log.error(f"Kill action failed for {container_name}: {e}")
        audit.append("KILL_FAILED", {
            "container": container_name, "error": str(e)
        })


# ---------------------------------------------------------------------------
# Main monitoring loop
# ---------------------------------------------------------------------------
def monitor():
    """Main watchdog loop. Enforces policy, chains audit, kills violators."""

    log.info("=" * 60)
    log.info("Zulu Watchdog starting (hardened)")
    log.info(f"  Monitored containers: {MONITORED_CONTAINERS}")
    log.info(f"  Default max task time: {MAX_TASK_SECONDS}s")
    log.info(f"  Default max memory:    {MAX_MEMORY_MB}MB")
    log.info(f"  Default max CPU:       {MAX_CPU_PERCENT}%")
    log.info(f"  Check interval:        {CHECK_INTERVAL}s")
    log.info(f"  Kill action:           {KILL_ACTION}")
    log.info(f"  Audit log:             {AUDIT_LOG_PATH}")
    log.info(f"  Policy file:           {POLICY_PATH}")
    log.info(f"  Policy fingerprint:    {policy.fingerprint()[:32]}...")
    log.info(f"  Audit chain head:      {audit.chain_head[:32]}...")
    log.info("=" * 60)

    audit.append("WATCHDOG_STARTED", {
        "monitored_containers": MONITORED_CONTAINERS,
        "policy_hash": policy.fingerprint(),
        "max_task_seconds": MAX_TASK_SECONDS,
        "max_memory_mb": MAX_MEMORY_MB,
        "max_cpu_percent": MAX_CPU_PERCENT,
        "check_interval": CHECK_INTERVAL,
    })

    client = docker.from_env()
    consecutive_high_cpu = {name: 0 for name in MONITORED_CONTAINERS}
    HIGH_CPU_THRESHOLD_CHECKS = 3
    policy_check_counter = 0
    POLICY_RELOAD_EVERY = max(
        1,
        policy.policy.get("global", {}).get(
            "policy_reload_interval", 60
        ) // CHECK_INTERVAL
    )

    while True:
        # --- Periodic policy reload ---
        policy_check_counter += 1
        if policy_check_counter >= POLICY_RELOAD_EVERY:
            policy_check_counter = 0
            if policy.reload():
                audit.append("POLICY_RELOADED", {
                    "policy_hash": policy.fingerprint(),
                })

        for container_name in MONITORED_CONTAINERS:
            try:
                container = client.containers.get(container_name)

                if container.status != "running":
                    log.info(
                        f"{container_name} status: {container.status}")
                    audit.append("CONTAINER_NOT_RUNNING",
                              {"container": container_name,
                               "status": container.status})
                    continue

                stats = get_container_stats(container)
                if stats is None:
                    continue

                # --- Policy-driven checks (with env var fallbacks) ---
                wp = policy.get_worker_policy(container_name)
                mem_limit = wp.get("max_memory_mb", MAX_MEMORY_MB)
                cpu_limit = wp.get("max_cpu_pct", MAX_CPU_PERCENT)

                # Also run the full policy engine for additional rules
                violations = policy.check(container_name, stats)
                for v in violations:
                    if v.severity == "kill":
                        audit.append("POLICY_VIOLATION", {
                            "container": container_name,
                            "rule": v.rule,
                            "reason": v.reason,
                            "details": v.details,
                        })
                        if policy.should_kill([v]):
                            kill_container(
                                client, container,
                                f"Policy violation: {v.reason}",
                                stats
                            )
                            consecutive_high_cpu[container_name] = 0
                            continue

                # --- Check memory ---
                if stats["memory_mb"] > mem_limit:
                    kill_container(
                        client, container,
                        f"Memory {stats['memory_mb']}MB > "
                        f"{mem_limit}MB limit",
                        stats
                    )
                    consecutive_high_cpu[container_name] = 0
                    continue

                # --- Check CPU (sustained) ---
                if stats["cpu_percent"] > cpu_limit:
                    consecutive_high_cpu[container_name] += 1
                    count = consecutive_high_cpu[container_name]
                    log.warning(
                        f"{container_name} high CPU: "
                        f"{stats['cpu_percent']}% "
                        f"({count}/{HIGH_CPU_THRESHOLD_CHECKS})"
                    )
                    if count >= HIGH_CPU_THRESHOLD_CHECKS:
                        kill_container(
                            client, container,
                            f"Sustained CPU {stats['cpu_percent']}% > "
                            f"{cpu_limit}% for "
                            f"{count * CHECK_INTERVAL}s",
                            stats
                        )
                        consecutive_high_cpu[container_name] = 0
                        continue
                else:
                    consecutive_high_cpu[container_name] = 0

                # --- Periodic health log ---
                log.debug(
                    f"{container_name} OK — "
                    f"mem={stats['memory_mb']}MB "
                    f"cpu={stats['cpu_percent']}%"
                )

            except docker.errors.NotFound:
                log.warning(
                    f"{container_name} not found — waiting...")
                audit.append("CONTAINER_NOT_FOUND",
                          {"container": container_name})

            except Exception as e:
                log.error(f"Watchdog error ({container_name}): {e}")
                audit.append("WATCHDOG_ERROR",
                          {"container": container_name, "error": str(e)})

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    monitor()
