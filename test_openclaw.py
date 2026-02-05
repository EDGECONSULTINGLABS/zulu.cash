#!/usr/bin/env python3
"""
Test script to dispatch a task to OpenClaw worker.
Run this from the host to test the airlock architecture.
"""
import asyncio
import aiohttp
import json

# OpenClaw worker endpoint (exposed via shared_bus network)
# From host, we need to use localhost if ports are exposed, or exec into a container
OPENCLAW_URL = "http://localhost:8081"

async def test_openclaw_task():
    """Send a test task directly to OpenClaw worker."""
    
    # Read API key from secrets
    try:
        with open("secrets/anthropic_api_key.txt", "r") as f:
            api_key = f.read().strip()
    except FileNotFoundError:
        print("ERROR: secrets/anthropic_api_key.txt not found")
        api_key = None
    
    # Test 1: Simple ping (no LLM needed)
    print("--- Test 1: Ping ---")
    ping_payload = {
        "task_id": "ping-001",
        "task_type": "ping",
        "prompt": "",
        "tool_allowlist": {},
        "domain_allowlist": [],
        "max_steps": 1,
        "timeout_seconds": 10,
        "credentials": {},
        "context": {}
    }
    await send_task(ping_payload)
    print()
    
    # Test 2: Comparative analysis with Claude (if API key available)
    if api_key:
        print("--- Test 2: Comparative Analysis with Claude ---")
        analysis_payload = {
            "task_id": "analysis-001",
            "task_type": "comparative_analysis",
            "prompt": "Compare these two programming languages for building AI agents. Which is better for safety-critical systems?",
            "tool_allowlist": {
                "web_browse": False,
                "web_fetch": False,
                "document_read": False,
                "document_write": False,
                "llm_chat": True,
                "code_analyze": False
            },
            "domain_allowlist": [],
            "max_steps": 3,
            "timeout_seconds": 60,
            "credentials": {
                "llm_api_key": api_key,
                "llm_provider": "anthropic"
            },
            "context": {
                "items": ["Python", "Rust"],
                "criteria": ["memory safety", "ecosystem", "ease of use", "performance"]
            }
        }
        await send_task(analysis_payload)
    else:
        print("--- Skipping Claude test (no API key) ---")
    
    return

async def send_task(task_payload):
    
    print(f"Sending task to OpenClaw worker...")
    print(f"Task ID: {task_payload['task_id']}")
    print(f"Task type: {task_payload['task_type']}")
    print()
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{OPENCLAW_URL}/task",
                json=task_payload,
                timeout=aiohttp.ClientTimeout(total=130)
            ) as resp:
                result = await resp.json()
                
                print(f"Status: {result.get('status')}")
                print(f"Steps taken: {result.get('steps_taken')}")
                print(f"Elapsed: {result.get('elapsed_seconds')}s")
                print()
                
                if result.get('output'):
                    print("Output:")
                    print(json.dumps(result['output'], indent=2)[:2000])
                
                if result.get('error'):
                    print(f"Error: {result['error']}")
                    
    except aiohttp.ClientError as e:
        print(f"Connection error: {e}")
        print()
        print("The OpenClaw worker port (8081) is not exposed to the host.")
        print("You can either:")
        print("  1. Add port mapping in docker-compose.yml")
        print("  2. Run this test from inside the zulu-core container")

async def test_health():
    """Check if OpenClaw worker is reachable."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{OPENCLAW_URL}/health", timeout=5) as resp:
                data = await resp.json()
                print(f"OpenClaw worker health: {data.get('status')}")
                return True
    except Exception as e:
        print(f"Cannot reach OpenClaw worker: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("OpenClaw NightShift Worker Test")
    print("=" * 60)
    print()
    
    asyncio.run(test_health())
    print()
    asyncio.run(test_openclaw_task())
