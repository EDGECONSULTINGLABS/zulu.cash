#!/usr/bin/env python3
"""
Test OpenClaw NightShift Worker with Ollama (no API key needed)
"""
import asyncio
import aiohttp
import json

# OpenClaw NightShift endpoint
NIGHTSHIFT_URL = "http://localhost:8090"

async def test_health():
    """Check if NightShift worker is reachable."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{NIGHTSHIFT_URL}/health", timeout=5) as resp:
                data = await resp.json()
                print(f"Health: {data.get('status')}")
                print(f"Strategy: {data.get('execution_strategy')}")
                print(f"Provider: {data.get('default_provider')}")
                print(f"Model: {data.get('default_model')}")
                return True
    except Exception as e:
        print(f"Cannot reach NightShift worker: {e}")
        return False

async def test_ping():
    """Simple ping test."""
    payload = {
        "task_id": "ping-001",
        "task_type": "ping",
        "prompt": "ping",
        "timeout_ms": 5000,
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{NIGHTSHIFT_URL}/task", json=payload, timeout=10) as resp:
            result = await resp.json()
            print(f"Ping status: {result.get('status')}")
            return result.get('status') == 'completed'

async def test_comparative_analysis():
    """Test comparative analysis with Ollama (no API key)."""
    payload = {
        "task_id": "analysis-001",
        "task_type": "comparative_analysis",
        "prompt": "Compare Python and Rust for building AI agents. Which is better for safety-critical systems? Give a brief 2-3 sentence answer.",
        "timeout_ms": 60000,
        "scoped_credentials": {
            "provider": "ollama",
            "model": "llama3.2:1b"
        }
    }
    
    print("Sending comparative analysis task to NightShift...")
    print("(Using Ollama locally - no API key needed)")
    print()
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{NIGHTSHIFT_URL}/task", 
            json=payload, 
            timeout=aiohttp.ClientTimeout(total=120)
        ) as resp:
            result = await resp.json()
            
            print(f"Status: {result.get('status')}")
            print(f"Elapsed: {result.get('elapsed_ms')}ms")
            print(f"Strategy: {result.get('execution_strategy')}")
            print()
            
            if result.get('result'):
                print("Result:")
                print(json.dumps(result['result'], indent=2)[:2000])
            
            if result.get('error'):
                print(f"Error: {result['error']}")
            
            return result

async def main():
    print("=" * 60)
    print("OpenClaw NightShift Worker Test (Ollama Backend)")
    print("=" * 60)
    print()
    
    print("--- Health Check ---")
    healthy = await test_health()
    if not healthy:
        print("Worker not healthy, exiting")
        return
    print()
    
    print("--- Ping Test ---")
    await test_ping()
    print()
    
    print("--- Comparative Analysis (Ollama) ---")
    await test_comparative_analysis()

if __name__ == "__main__":
    asyncio.run(main())
