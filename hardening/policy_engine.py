"""
Policy Engine — Governance as Code
====================================
Loads policy from YAML. Validates container behavior against rules.
No redeploy needed — change policy, watchdog enforces immediately.

Policy covers:
    - Per-worker runtime limits
    - Per-worker CPU/memory thresholds
    - Filesystem access rules
    - Network rules (deny outbound, deny DNS)
    - Denied syscalls (advisory — requires seccomp for enforcement)
    - Attestation requirements

USAGE:
    from hardening.policy_engine import PolicyEngine

    engine = PolicyEngine("/app/policy/policy.yaml")
    violations = engine.check("clawd-runner", stats)
    for v in violations:
        kill_container(v.container, v.reason)

    # Reload on change
    engine.reload()
"""

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger("zulu.policy_engine")

# ---------------------------------------------------------------------------
# BLAKE3 wrapper
# ---------------------------------------------------------------------------
try:
    from blake3 import blake3 as _blake3

    def _hash_bytes(data: bytes) -> str:
        return _blake3(data).hexdigest()
except ImportError:
    def _hash_bytes(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# YAML loader (falls back to simple parser if PyYAML not available)
# ---------------------------------------------------------------------------
try:
    import yaml

    def _load_yaml(path: str) -> dict:
        with open(path, "r") as f:
            return yaml.safe_load(f)
except ImportError:
    log.warning("PyYAML not available — policy loading will fail")

    def _load_yaml(path: str) -> dict:
        raise ImportError("PyYAML required for policy engine")


# ---------------------------------------------------------------------------
# Policy violation
# ---------------------------------------------------------------------------
@dataclass
class PolicyViolation:
    """A single policy violation detected by the engine."""
    container: str
    rule: str
    reason: str
    severity: str  # "kill" | "warn" | "log"
    details: dict

    def to_dict(self) -> dict:
        return {
            "container": self.container,
            "rule": self.rule,
            "reason": self.reason,
            "severity": self.severity,
            "details": self.details,
            "ts": datetime.now(timezone.utc).isoformat(),
        }


# ---------------------------------------------------------------------------
# Default policy (used if no YAML loaded)
# ---------------------------------------------------------------------------
DEFAULT_POLICY = {
    "version": "1.0",
    "workers": {
        "clawd-runner": {
            "max_runtime_sec": 300,
            "max_cpu_pct": 90,
            "max_memory_mb": 1024,
            "require_attestation": True,
            "allow_filesystem": ["/tmp", "/app/workspace"],
            "deny_outbound": False,
            "deny_dns": False,
        },
        "openclaw-nightshift": {
            "max_runtime_sec": 300,
            "max_cpu_pct": 90,
            "max_memory_mb": 2048,
            "require_attestation": True,
            "allow_filesystem": ["/tmp", "/app/workspace", "/app/output"],
            "deny_outbound": False,
            "deny_dns": False,
        },
    },
    "global": {
        "max_concurrent_tasks": 5,
        "kill_on_violation": True,
        "audit_all_checks": False,
    },
}


# ---------------------------------------------------------------------------
# Policy Engine
# ---------------------------------------------------------------------------
class PolicyEngine:
    """
    Loads and enforces policy rules.
    Mounted read-only in the watchdog container.
    """

    def __init__(self, policy_path: Optional[str] = None):
        self.policy_path = policy_path
        self.policy = {}
        self.policy_hash = ""
        self._load_count = 0

        if policy_path and Path(policy_path).exists():
            self.reload()
        else:
            log.info("No policy file found — using defaults")
            self.policy = DEFAULT_POLICY
            self.policy_hash = _hash_bytes(
                json.dumps(DEFAULT_POLICY, sort_keys=True).encode()
            )

    def reload(self) -> bool:
        """
        Reload policy from YAML file.
        Returns True if policy changed.
        """
        if not self.policy_path or not Path(self.policy_path).exists():
            return False

        try:
            raw = Path(self.policy_path).read_bytes()
            new_hash = _hash_bytes(raw)

            if new_hash == self.policy_hash:
                return False  # No change

            new_policy = _load_yaml(self.policy_path)
            self.policy = new_policy
            self.policy_hash = new_hash
            self._load_count += 1

            log.info(
                f"Policy reloaded (v{self._load_count}): "
                f"hash={new_hash[:16]}..."
            )
            return True

        except Exception as e:
            log.error(f"Failed to reload policy: {e}")
            return False

    def get_worker_policy(self, container_name: str) -> dict:
        """Get policy rules for a specific worker."""
        workers = self.policy.get("workers", {})
        return workers.get(container_name, {})

    def check(self, container_name: str, stats: dict,
              runtime_seconds: float = 0) -> list[PolicyViolation]:
        """
        Check a container's current state against policy.
        Returns list of violations (empty = compliant).
        """
        violations = []
        worker_policy = self.get_worker_policy(container_name)

        if not worker_policy:
            # Unknown worker — this itself might be a violation
            if self.policy.get("global", {}).get("kill_unknown_workers", False):
                violations.append(PolicyViolation(
                    container=container_name,
                    rule="unknown_worker",
                    reason=f"Worker '{container_name}' not in policy",
                    severity="kill",
                    details={}
                ))
            return violations

        # --- Runtime limit ---
        max_runtime = worker_policy.get("max_runtime_sec", 300)
        if runtime_seconds > max_runtime:
            violations.append(PolicyViolation(
                container=container_name,
                rule="max_runtime_sec",
                reason=(
                    f"Runtime {runtime_seconds:.0f}s exceeds "
                    f"policy limit {max_runtime}s"
                ),
                severity="kill",
                details={
                    "runtime": runtime_seconds,
                    "limit": max_runtime
                }
            ))

        # --- CPU limit ---
        max_cpu = worker_policy.get("max_cpu_pct", 90)
        current_cpu = stats.get("cpu_percent", 0)
        if current_cpu > max_cpu:
            violations.append(PolicyViolation(
                container=container_name,
                rule="max_cpu_pct",
                reason=f"CPU {current_cpu}% exceeds policy limit {max_cpu}%",
                severity="warn",  # CPU is "warn" — watchdog escalates to kill
                details={"cpu_percent": current_cpu, "limit": max_cpu}
            ))

        # --- Memory limit ---
        max_memory = worker_policy.get("max_memory_mb", 1024)
        current_memory = stats.get("memory_mb", 0)
        if current_memory > max_memory:
            violations.append(PolicyViolation(
                container=container_name,
                rule="max_memory_mb",
                reason=(
                    f"Memory {current_memory}MB exceeds "
                    f"policy limit {max_memory}MB"
                ),
                severity="kill",
                details={"memory_mb": current_memory, "limit": max_memory}
            ))

        # --- Network rules (advisory — requires iptables for real enforcement) ---
        if worker_policy.get("deny_outbound", False):
            # This is checked by examining container network stats
            # Real enforcement happens at network level
            net_out = stats.get("network_tx_bytes", 0)
            if net_out > 0:
                violations.append(PolicyViolation(
                    container=container_name,
                    rule="deny_outbound",
                    reason=f"Outbound network detected ({net_out} bytes)",
                    severity="kill",
                    details={"network_tx_bytes": net_out}
                ))

        return violations

    def should_kill(self, violations: list[PolicyViolation]) -> bool:
        """Check if any violations warrant a kill."""
        kill_on_violation = self.policy.get("global", {}).get(
            "kill_on_violation", True
        )
        if not kill_on_violation:
            return False
        return any(v.severity == "kill" for v in violations)

    def requires_attestation(self, container_name: str) -> bool:
        """Check if a worker requires attestation before task dispatch."""
        worker_policy = self.get_worker_policy(container_name)
        return worker_policy.get("require_attestation", True)

    def fingerprint(self) -> str:
        """Return the current policy hash for audit chaining."""
        return self.policy_hash

    def to_dict(self) -> dict:
        """Serialize current policy state."""
        return {
            "policy": self.policy,
            "hash": self.policy_hash,
            "load_count": self._load_count,
        }
