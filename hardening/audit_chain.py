"""
Immutable Audit Chain — BLAKE3 Hash-Linked Audit Log
======================================================
Every audit record:
  1. Hashes its own contents
  2. Links to the previous record's hash
  3. Becomes tamper-evident

If any line is edited, deleted, or reordered, the chain breaks.

Additionally provides Merkle root compaction:
  - Hourly (or per N events), compute a single hash over all events
  - This root can be pinned to git, S3, email, or chain later

No blockchain. No database. No external dependency.
BLAKE3 everywhere — one primitive, zero confusion.

USAGE:
    from hardening.audit_chain import AuditChain

    chain = AuditChain("/app/logs/watchdog-audit.jsonl")
    chain.append("WORKER_KILLED", {"container": "clawd-runner", "reason": "memory"})
    chain.append("POLICY_LOADED", {"hash": "abc123..."})

    # Verify integrity
    valid, broken_at = chain.verify()

    # Compute Merkle root for current window
    root = chain.merkle_root()
"""

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger("zulu.audit_chain")

# ---------------------------------------------------------------------------
# BLAKE3 wrapper — falls back to SHA-256 if blake3 not installed
# ---------------------------------------------------------------------------
try:
    from blake3 import blake3 as _blake3

    def _hash(data: bytes) -> str:
        return _blake3(data).hexdigest()

    HASH_ALGO = "blake3"
except ImportError:
    log.warning("blake3 not available, falling back to sha256")

    def _hash(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    HASH_ALGO = "sha256"


# ---------------------------------------------------------------------------
# Genesis hash — the chain starts here
# ---------------------------------------------------------------------------
GENESIS_HASH = _hash(b"ZULU_AUDIT_GENESIS_v1")


# ---------------------------------------------------------------------------
# Record hashing
# ---------------------------------------------------------------------------
def hash_record(record: dict, prev_hash: str) -> str:
    """
    Hash a record deterministically.
    The record MUST include prev_hash before hashing.
    Sorted keys ensure identical output regardless of insertion order.
    """
    canonical = json.dumps(
        {**record, "prev_hash": prev_hash},
        sort_keys=True,
        separators=(",", ":"),  # Compact, no whitespace variance
        ensure_ascii=True
    )
    return _hash(canonical.encode("utf-8"))


# ---------------------------------------------------------------------------
# Merkle tree
# ---------------------------------------------------------------------------
def merkle_root(hashes: list[str]) -> str:
    """
    Compute a Merkle root from a list of hashes.
    If odd number of leaves, the last one is duplicated.
    Returns the single root hash.
    """
    if not hashes:
        return _hash(b"EMPTY_MERKLE")

    level = list(hashes)

    while len(level) > 1:
        next_level = []
        for i in range(0, len(level), 2):
            left = level[i]
            right = level[i + 1] if i + 1 < len(level) else level[i]
            combined = _hash((left + right).encode("utf-8"))
            next_level.append(combined)
        level = next_level

    return level[0]


# ---------------------------------------------------------------------------
# Audit Chain
# ---------------------------------------------------------------------------
class AuditChain:
    """
    Append-only, hash-chained audit log.

    Each line in the JSONL file is:
    {
        "ts": "2026-02-04T00:41:10.123Z",
        "seq": 0,
        "event": "WORKER_KILLED",
        "container": "clawd-runner",
        ...
        "prev_hash": "a8f3...",
        "hash": "c91d...",
        "algo": "blake3"
    }
    """

    def __init__(self, log_path: str,
                 merkle_path: Optional[str] = None,
                 merkle_interval: int = 360):
        self.log_path = Path(log_path)
        self.merkle_path = Path(
            merkle_path or str(log_path).replace(".jsonl", "-merkle.jsonl")
        )
        self.merkle_interval = merkle_interval  # events between Merkle roots

        self._prev_hash = GENESIS_HASH
        self._seq = 0
        self._window_hashes: list[str] = []

        # Resume chain from existing log
        self._resume()

    def _resume(self):
        """Load the last hash and sequence from existing log file."""
        if not self.log_path.exists():
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            return

        last_line = None
        try:
            with open(self.log_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        last_line = line
        except Exception as e:
            log.error(f"Failed to resume audit chain: {e}")
            return

        if last_line:
            try:
                record = json.loads(last_line)
                self._prev_hash = record.get("hash", GENESIS_HASH)
                self._seq = record.get("seq", 0) + 1
                log.info(
                    f"Audit chain resumed at seq={self._seq}, "
                    f"prev_hash={self._prev_hash[:16]}..."
                )
            except json.JSONDecodeError:
                log.warning("Last audit line malformed — starting fresh chain")

    def append(self, event: str, details: dict = None) -> dict:
        """
        Append a hash-chained record to the audit log.
        Returns the complete record (for callers who need it).
        """
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "seq": self._seq,
            "event": event,
            **(details or {}),
        }

        # Compute chain hash
        record_hash = hash_record(record, self._prev_hash)
        record["prev_hash"] = self._prev_hash
        record["hash"] = record_hash
        record["algo"] = HASH_ALGO

        # Write append-only
        try:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(record, sort_keys=False) + "\n")
        except Exception as e:
            log.error(f"CRITICAL: Failed to write audit record: {e}")
            # Still update in-memory state so chain doesn't fork
            # but log the failure loudly

        # Update chain state
        self._prev_hash = record_hash
        self._seq += 1
        self._window_hashes.append(record_hash)

        # Log to stdout
        log.info(
            f"AUDIT [{self._seq - 1}] {event} "
            f"hash={record_hash[:16]}..."
        )

        # Check if Merkle window is full
        if len(self._window_hashes) >= self.merkle_interval:
            self._emit_merkle_root()

        return record

    def _emit_merkle_root(self):
        """Compute and persist a Merkle root for the current window."""
        if not self._window_hashes:
            return

        root = merkle_root(self._window_hashes)
        window_record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "type": "merkle_root",
            "event_count": len(self._window_hashes),
            "first_seq": self._seq - len(self._window_hashes),
            "last_seq": self._seq - 1,
            "merkle_root": root,
            "algo": HASH_ALGO,
        }

        try:
            self.merkle_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.merkle_path, "a") as f:
                f.write(json.dumps(window_record) + "\n")
            log.info(
                f"MERKLE ROOT: {root[:16]}... "
                f"({len(self._window_hashes)} events)"
            )
        except Exception as e:
            log.error(f"Failed to write Merkle root: {e}")

        self._window_hashes.clear()

    def flush_merkle(self):
        """Force emit a Merkle root for whatever's in the current window."""
        self._emit_merkle_root()

    def verify(self) -> tuple[bool, Optional[int]]:
        """
        Verify the entire chain from genesis.
        Returns (is_valid, first_broken_seq).
        If valid, returns (True, None).
        """
        if not self.log_path.exists():
            return True, None

        prev_hash = GENESIS_HASH
        last_seq = -1

        with open(self.log_path, "r") as f:
            for line_num, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue

                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    log.error(f"Line {line_num}: malformed JSON")
                    return False, line_num

                stored_hash = record.pop("hash", None)
                stored_prev = record.pop("prev_hash", None)
                record.pop("algo", None)

                if stored_prev != prev_hash:
                    log.error(
                        f"Line {line_num} (seq {record.get('seq')}): "
                        f"prev_hash mismatch"
                    )
                    return False, record.get("seq", line_num)

                expected_hash = hash_record(record, prev_hash)
                if stored_hash != expected_hash:
                    log.error(
                        f"Line {line_num} (seq {record.get('seq')}): "
                        f"hash mismatch — expected {expected_hash[:16]}..., "
                        f"got {stored_hash[:16]}..."
                    )
                    return False, record.get("seq", line_num)

                prev_hash = stored_hash
                last_seq = record.get("seq", line_num)

        log.info(f"Chain verified: {last_seq + 1} records, all valid")
        return True, None

    @property
    def chain_head(self) -> str:
        """Current head of the hash chain."""
        return self._prev_hash

    @property
    def sequence(self) -> int:
        """Next sequence number."""
        return self._seq
