"""
Quick end-to-end test for ZuluMoltWorkerAdapter against live MoltWorker.

Usage:
    set MOLTWORKER_URL=https://moltbot-sandbox.alula-cb1.workers.dev
    set MOLTWORKER_GATEWAY_TOKEN=<your-token>
    python test_moltworker_adapter.py
"""

import asyncio
import logging
import os
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("test")

# Ensure we can import from the repo root
sys.path.insert(0, os.path.dirname(__file__))

from zulu_openclaw_adapter import (
    OpenClawRequest,
    OpenClawTaskType,
    ScopedCredentials,
    ToolAllowlist,
)
from zulu_moltworker_adapter import ZuluMoltWorkerAdapter


async def test_ping():
    """Test 1: Health check via ping()."""
    log.info("=" * 60)
    log.info("TEST 1: ping()")
    log.info("=" * 60)

    adapter = ZuluMoltWorkerAdapter()
    async with adapter.session_context():
        resp = await adapter.ping()
        log.info(f"  Status:  {resp.status}")
        log.info(f"  Output:  {resp.output}")
        log.info(f"  Error:   {resp.error}")
        assert resp.status == "completed", f"Ping failed: {resp.error}"
        log.info("  ✓ PASS")
    return True


async def test_simple_dispatch():
    """Test 2: Simple dispatch — ask the agent a basic question."""
    log.info("=" * 60)
    log.info("TEST 2: dispatch() — simple question")
    log.info("=" * 60)

    adapter = ZuluMoltWorkerAdapter()
    async with adapter.session_context():
        request = OpenClawRequest(
            task_id=f"test-{int(time.time())}",
            task_type=OpenClawTaskType.WEB_RESEARCH,
            prompt="What is 2 + 2? Reply with just the number.",
            tool_allowlist=ToolAllowlist(llm_chat=True),
            domain_allowlist=[],
            credentials=ScopedCredentials(
                llm_api_key="test",
                llm_provider="test",
            ),
            timeout_seconds=60,
        )

        start = time.monotonic()
        resp = await adapter.dispatch(request)
        elapsed = time.monotonic() - start

        log.info(f"  Status:  {resp.status}")
        log.info(f"  Output:  {resp.output}")
        log.info(f"  Error:   {resp.error}")
        log.info(f"  Elapsed: {elapsed:.1f}s")

        assert resp.status == "completed", f"Dispatch failed: {resp.error}"
        content = resp.output.get("content", "") if resp.output else ""
        assert "4" in content, f"Expected '4' in response, got: {content[:200]}"
        log.info("  ✓ PASS")
    return True


async def test_audit_log():
    """Test 3: Verify audit log entries are recorded."""
    log.info("=" * 60)
    log.info("TEST 3: audit log")
    log.info("=" * 60)

    adapter = ZuluMoltWorkerAdapter()
    async with adapter.session_context():
        await adapter.ping()
        audit = adapter.get_audit_log()
        log.info(f"  Audit entries: {len(audit)}")
        for entry in audit:
            log.info(f"    {entry['event']} — task={entry['task_id']}")
        assert len(audit) >= 2, f"Expected >=2 audit entries, got {len(audit)}"
        log.info("  ✓ PASS")
    return True


async def main():
    # Validate env vars
    url = os.getenv("MOLTWORKER_URL", "")
    token = os.getenv("MOLTWORKER_GATEWAY_TOKEN", "")

    if not url:
        log.error("Set MOLTWORKER_URL env var (e.g. https://moltbot-sandbox.alula-cb1.workers.dev)")
        sys.exit(1)
    if not token:
        log.error("Set MOLTWORKER_GATEWAY_TOKEN env var")
        sys.exit(1)

    log.info(f"MoltWorker URL: {url}")
    log.info(f"Token: {token[:8]}...{token[-4:]}")
    log.info("")

    results = {}
    tests = [
        ("ping", test_ping),
        ("dispatch", test_simple_dispatch),
        ("audit", test_audit_log),
    ]

    for name, test_fn in tests:
        try:
            results[name] = await test_fn()
        except Exception as e:
            log.error(f"  ✗ FAIL: {e}")
            results[name] = False

    log.info("")
    log.info("=" * 60)
    log.info("RESULTS")
    log.info("=" * 60)
    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        log.info(f"  {name}: {status}")

    if all(results.values()):
        log.info("\nAll tests passed!")
        sys.exit(0)
    else:
        log.error("\nSome tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
