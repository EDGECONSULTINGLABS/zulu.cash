"""
Worker Attestation — Startup Trust Handshake
=============================================
Prevents rogue containers, replay execution, and unauthorized workers.

FLOW:
    1. Worker boots, requests nonce from zulu-core
    2. Zulu-core generates nonce, stores it with expiry
    3. Worker signs (nonce + worker_secret) with BLAKE3
    4. Worker sends attestation to watchdog (or core)
    5. Watchdog validates signature
    6. If invalid → kill container + audit

SECURITY PROPERTIES:
    - Workers prove identity at startup
    - Nonces are single-use, time-limited
    - Worker secrets are per-container, injected via env
    - No PKI required (can upgrade to Ed25519 later)
    - Works fully offline

USAGE (from zulu-core):
    from hardening.attestation import AttestationAuthority
    authority = AttestationAuthority(known_workers={...})
    nonce = authority.issue_nonce("clawd-runner")
    ok = authority.verify("clawd-runner", nonce, signature)

USAGE (from worker):
    from hardening.attestation import WorkerAttester
    attester = WorkerAttester(worker_id="clawd-runner", secret="...")
    sig = attester.sign_nonce(nonce)
"""

import hashlib
import json
import logging
import os
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

log = logging.getLogger("zulu.attestation")

# ---------------------------------------------------------------------------
# BLAKE3 wrapper (same pattern as audit_chain)
# ---------------------------------------------------------------------------
try:
    from blake3 import blake3 as _blake3

    def _hash(data: bytes) -> str:
        return _blake3(data).hexdigest()
except ImportError:
    def _hash(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Nonce management
# ---------------------------------------------------------------------------
@dataclass
class IssuedNonce:
    """A nonce issued to a specific worker."""
    worker_id: str
    nonce: str
    issued_at: float
    expires_at: float
    used: bool = False


# ---------------------------------------------------------------------------
# Authority (runs on zulu-core / watchdog)
# ---------------------------------------------------------------------------
class AttestationAuthority:
    """
    Issues nonces, validates worker attestations.
    Runs on zulu-core (the only component that knows worker secrets).

    known_workers: {
        "clawd-runner": "secret-for-clawd",
        "openclaw-nightshift": "secret-for-openclaw",
    }
    """

    def __init__(self, known_workers: dict[str, str],
                 nonce_ttl_seconds: int = 60):
        self.known_workers = known_workers
        self.nonce_ttl = nonce_ttl_seconds
        self._issued: dict[str, IssuedNonce] = {}
        self._attestation_log: list[dict] = []

    def issue_nonce(self, worker_id: str) -> Optional[str]:
        """
        Generate a cryptographic nonce for a worker.
        Returns None if worker_id is not recognized.
        """
        if worker_id not in self.known_workers:
            log.warning(f"Nonce requested by unknown worker: {worker_id}")
            self._log_event("NONCE_DENIED", worker_id, reason="unknown_worker")
            return None

        nonce = secrets.token_hex(32)  # 256-bit random
        now = time.time()

        self._issued[nonce] = IssuedNonce(
            worker_id=worker_id,
            nonce=nonce,
            issued_at=now,
            expires_at=now + self.nonce_ttl,
        )

        self._log_event("NONCE_ISSUED", worker_id, nonce_prefix=nonce[:16])
        return nonce

    def verify(self, worker_id: str, nonce: str,
               signature: str) -> tuple[bool, str]:
        """
        Verify a worker's attestation.
        Returns (is_valid, reason).
        """
        # Check nonce exists
        issued = self._issued.get(nonce)
        if issued is None:
            reason = "nonce_not_found"
            self._log_event("ATTESTATION_FAILED", worker_id, reason=reason)
            return False, reason

        # Check nonce belongs to this worker
        if issued.worker_id != worker_id:
            reason = "nonce_worker_mismatch"
            self._log_event("ATTESTATION_FAILED", worker_id, reason=reason)
            return False, reason

        # Check nonce not expired
        if time.time() > issued.expires_at:
            reason = "nonce_expired"
            self._log_event("ATTESTATION_FAILED", worker_id, reason=reason)
            del self._issued[nonce]
            return False, reason

        # Check nonce not already used (replay protection)
        if issued.used:
            reason = "nonce_already_used"
            self._log_event("ATTESTATION_FAILED", worker_id, reason=reason)
            return False, reason

        # Compute expected signature
        worker_secret = self.known_workers.get(worker_id, "")
        expected = _compute_signature(nonce, worker_secret)

        if not secrets.compare_digest(signature, expected):
            reason = "signature_mismatch"
            self._log_event("ATTESTATION_FAILED", worker_id, reason=reason)
            return False, reason

        # Success — mark nonce as used
        issued.used = True
        self._log_event("ATTESTATION_OK", worker_id)

        # Cleanup expired nonces
        self._cleanup_expired()

        return True, "ok"

    def revoke_worker(self, worker_id: str):
        """Revoke all nonces for a worker (e.g., after kill)."""
        revoked = 0
        for nonce, issued in list(self._issued.items()):
            if issued.worker_id == worker_id:
                del self._issued[nonce]
                revoked += 1
        if revoked:
            self._log_event("WORKER_REVOKED", worker_id,
                            nonces_revoked=revoked)

    def _cleanup_expired(self):
        """Remove expired nonces."""
        now = time.time()
        expired = [n for n, i in self._issued.items() if now > i.expires_at]
        for n in expired:
            del self._issued[n]

    def _log_event(self, event: str, worker_id: str, **kwargs):
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "worker_id": worker_id,
            **kwargs
        }
        self._attestation_log.append(entry)
        log.info(f"ATTEST: {json.dumps(entry)}")

    def get_log(self) -> list[dict]:
        return list(self._attestation_log)

    def flush_log(self) -> list[dict]:
        entries = list(self._attestation_log)
        self._attestation_log.clear()
        return entries


# ---------------------------------------------------------------------------
# Worker-side attester
# ---------------------------------------------------------------------------
class WorkerAttester:
    """
    Runs inside the worker container.
    Signs nonces to prove identity to the authority.
    """

    def __init__(self, worker_id: str, secret: str):
        self.worker_id = worker_id
        self.secret = secret

    def sign_nonce(self, nonce: str) -> str:
        """
        Sign a nonce with this worker's secret.
        Returns the BLAKE3 signature.
        """
        return _compute_signature(nonce, self.secret)

    def build_attestation(self, nonce: str) -> dict:
        """Build a complete attestation payload for HTTP."""
        return {
            "worker_id": self.worker_id,
            "nonce": nonce,
            "signature": self.sign_nonce(nonce),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ---------------------------------------------------------------------------
# Shared signature computation
# ---------------------------------------------------------------------------
def _compute_signature(nonce: str, secret: str) -> str:
    """
    Compute BLAKE3(nonce + secret).
    Both authority and worker use this — must be identical.
    """
    payload = (nonce + secret).encode("utf-8")
    return _hash(payload)
