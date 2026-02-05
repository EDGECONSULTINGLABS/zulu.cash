#!/usr/bin/env python3
"""
Zulu CLI — stub for airlock demo
"""
import sys

def serve():
    """Start the Zulu control plane server."""
    print("Zulu control plane starting...")
    print("This is a stub — replace with actual Zulu agent_core")
    # Keep running
    import time
    while True:
        time.sleep(60)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        serve()
    else:
        print("Usage: python cli.py serve")
