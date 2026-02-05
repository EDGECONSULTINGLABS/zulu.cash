#!/usr/bin/env python3
"""
Zulu Audit CLI — Verification & Inspection Tools
==================================================
Usage:
    python -m cli.zulu_audit verify [--log PATH]
    python -m cli.zulu_audit tail [--log PATH] [-n LINES]
    python -m cli.zulu_audit merkle [--log PATH]
    python -m cli.zulu_audit policy [--policy PATH]
    python -m cli.zulu_audit demo-violation [--log PATH]

Commands:
    verify          Verify the full audit chain from genesis
    tail            Show the last N audit records
    merkle          Show Merkle roots
    policy          Show current policy + fingerprint
    demo-violation  Inject a tampered record (for demo purposes)
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hardening.audit_chain import AuditChain, GENESIS_HASH, hash_record


# ---------------------------------------------------------------------------
# Colors for terminal output
# ---------------------------------------------------------------------------
class C:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def ok(msg):
    print(f"  {C.GREEN}✓{C.RESET} {msg}")

def fail(msg):
    print(f"  {C.RED}✗{C.RESET} {msg}")

def warn(msg):
    print(f"  {C.YELLOW}⚠{C.RESET} {msg}")

def info(msg):
    print(f"  {C.BLUE}ℹ{C.RESET} {msg}")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def cmd_verify(args):
    """Verify the full audit chain."""
    log_path = args.log
    print(f"\n{C.BOLD}Zulu Audit Chain Verification{C.RESET}")
    print(f"{'─' * 40}")
    print(f"  Log: {log_path}")

    if not Path(log_path).exists():
        fail(f"Log file not found: {log_path}")
        return 1

    # Count records
    with open(log_path) as f:
        lines = [l.strip() for l in f if l.strip()]
    info(f"Records: {len(lines)}")

    # Verify chain
    chain = AuditChain(log_path)
    is_valid, broken_at = chain.verify()

    print()
    if is_valid:
        ok(f"Chain integrity: {C.GREEN}{C.BOLD}VALID{C.RESET}")
        ok(f"All {len(lines)} records verified")
        ok(f"Chain head: {chain.chain_head[:32]}...")
        print(f"\n  {C.DIM}Genesis: {GENESIS_HASH[:32]}...{C.RESET}")
    else:
        fail(f"Chain integrity: {C.RED}{C.BOLD}BROKEN{C.RESET}")
        fail(f"First tampered record at seq: {broken_at}")
        warn("The audit log has been modified. Investigate immediately.")

    print()
    return 0 if is_valid else 1


def cmd_tail(args):
    """Show the last N audit records."""
    log_path = args.log
    n = args.n

    if not Path(log_path).exists():
        fail(f"Log file not found: {log_path}")
        return 1

    with open(log_path) as f:
        lines = [l.strip() for l in f if l.strip()]

    print(f"\n{C.BOLD}Last {min(n, len(lines))} Audit Records{C.RESET}")
    print(f"{'─' * 60}")

    for line in lines[-n:]:
        try:
            record = json.loads(line)
            seq = record.get("seq", "?")
            event = record.get("event", "?")
            ts = record.get("ts", "?")
            h = record.get("hash", "?")[:16]

            # Color by event type
            if "KILL" in event or "FAIL" in event:
                color = C.RED
            elif "WARN" in event or "VIOLATION" in event:
                color = C.YELLOW
            elif "OK" in event or "STARTED" in event:
                color = C.GREEN
            else:
                color = C.RESET

            print(
                f"  {C.DIM}[{seq:>4}]{C.RESET} "
                f"{color}{event:<30}{C.RESET} "
                f"{C.DIM}{ts}{C.RESET} "
                f"{C.DIM}#{h}...{C.RESET}"
            )

            # Show relevant details
            skip_keys = {"ts", "seq", "event", "hash", "prev_hash", "algo"}
            details = {k: v for k, v in record.items() if k not in skip_keys}
            if details:
                print(f"         {C.DIM}{json.dumps(details)}{C.RESET}")

        except json.JSONDecodeError:
            warn(f"Malformed line: {line[:80]}...")

    print()
    return 0


def cmd_merkle(args):
    """Show Merkle roots."""
    log_path = args.log
    merkle_path = str(log_path).replace(".jsonl", "-merkle.jsonl")

    print(f"\n{C.BOLD}Merkle Roots{C.RESET}")
    print(f"{'─' * 60}")

    if not Path(merkle_path).exists():
        warn(f"No Merkle roots found at: {merkle_path}")
        info("Merkle roots are emitted periodically during operation.")
        print()
        return 0

    with open(merkle_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                root = record.get("merkle_root", "?")[:32]
                count = record.get("event_count", "?")
                first = record.get("first_seq", "?")
                last = record.get("last_seq", "?")
                ts = record.get("ts", "?")

                print(
                    f"  {C.GREEN}◆{C.RESET} "
                    f"{root}... "
                    f"{C.DIM}({count} events, seq {first}-{last}){C.RESET} "
                    f"{C.DIM}{ts}{C.RESET}"
                )
            except json.JSONDecodeError:
                pass

    print()
    return 0


def cmd_policy(args):
    """Show current policy + fingerprint."""
    policy_path = args.policy

    print(f"\n{C.BOLD}Zulu Policy{C.RESET}")
    print(f"{'─' * 40}")

    if not Path(policy_path).exists():
        warn(f"Policy file not found: {policy_path}")
        info("Using default policy.")
        print()
        return 0

    from hardening.policy_engine import PolicyEngine

    engine = PolicyEngine(policy_path)
    info(f"Path: {policy_path}")
    ok(f"Fingerprint: {engine.fingerprint()[:32]}...")

    print(f"\n  {C.BOLD}Workers:{C.RESET}")
    for name, rules in engine.policy.get("workers", {}).items():
        runtime = rules.get("max_runtime_sec", "?")
        cpu = rules.get("max_cpu_pct", "?")
        mem = rules.get("max_memory_mb", "?")
        attest = rules.get("require_attestation", "?")
        print(
            f"    {C.BLUE}{name}{C.RESET}: "
            f"runtime={runtime}s, cpu={cpu}%, mem={mem}MB, "
            f"attest={attest}"
        )

    global_rules = engine.policy.get("global", {})
    if global_rules:
        print(f"\n  {C.BOLD}Global:{C.RESET}")
        for k, v in global_rules.items():
            print(f"    {k}: {v}")

    print()
    return 0


def cmd_demo_violation(args):
    """
    Inject a tampered record for demo purposes.
    This INTENTIONALLY breaks the chain to demonstrate detection.
    """
    log_path = args.log

    if not Path(log_path).exists():
        fail(f"Log file not found: {log_path}")
        return 1

    print(f"\n{C.BOLD}{C.RED}Demo: Injecting Tampered Record{C.RESET}")
    print(f"{'─' * 40}")

    # Read existing records
    with open(log_path) as f:
        lines = f.readlines()

    if len(lines) < 2:
        fail("Need at least 2 records to demonstrate tampering")
        return 1

    # Tamper with a middle record
    mid = len(lines) // 2
    try:
        record = json.loads(lines[mid])
        original_event = record.get("event", "UNKNOWN")
        record["event"] = "TAMPERED_BY_DEMO"
        lines[mid] = json.dumps(record) + "\n"

        with open(log_path, "w") as f:
            f.writelines(lines)

        warn(f"Tampered record at seq {record.get('seq', mid)}")
        warn(f"Changed event '{original_event}' → 'TAMPERED_BY_DEMO'")
        print()
        info("Now run: python -m cli.zulu_audit verify")
        info("The chain will detect the tampering.")

    except Exception as e:
        fail(f"Demo injection failed: {e}")
        return 1

    print()
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        prog="zulu-audit",
        description="Zulu Audit Chain — Verification & Inspection"
    )

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # verify
    p_verify = sub.add_parser("verify", help="Verify audit chain integrity")
    p_verify.add_argument(
        "--log", default="/app/logs/watchdog-audit.jsonl",
        help="Path to audit log"
    )

    # tail
    p_tail = sub.add_parser("tail", help="Show last N audit records")
    p_tail.add_argument(
        "--log", default="/app/logs/watchdog-audit.jsonl",
        help="Path to audit log"
    )
    p_tail.add_argument("-n", type=int, default=20, help="Number of records")

    # merkle
    p_merkle = sub.add_parser("merkle", help="Show Merkle roots")
    p_merkle.add_argument(
        "--log", default="/app/logs/watchdog-audit.jsonl",
        help="Path to audit log"
    )

    # policy
    p_policy = sub.add_parser("policy", help="Show policy + fingerprint")
    p_policy.add_argument(
        "--policy", default="/app/policy/policy.yaml",
        help="Path to policy file"
    )

    # demo-violation
    p_demo = sub.add_parser(
        "demo-violation",
        help="Inject tampered record (for demos)"
    )
    p_demo.add_argument(
        "--log", default="/app/logs/watchdog-audit.jsonl",
        help="Path to audit log"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    commands = {
        "verify": cmd_verify,
        "tail": cmd_tail,
        "merkle": cmd_merkle,
        "policy": cmd_policy,
        "demo-violation": cmd_demo_violation,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
