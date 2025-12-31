#!/usr/bin/env python3
"""
Test AI client directly.
"""

import asyncio
import sys
sys.path.insert(0, '/home/kntrnjb/ai-dream-team/micro-ai-swarm/love-unlimited')

from hub.ai_clients import ai_manager

async def test_ai():
    print("Testing AI clients...")

    available = await ai_manager.get_available_beings()
    print(f"Available beings: {available}")

    for being in available:
        print(f"\nTesting {being}...")
        response = await ai_manager.generate_response(
            being,
            "Hello! What are your thoughts on AI collaboration?",
            []
        )
        print(f"Response from {being}: {response[:100]}...")

if __name__ == "__main__":
    asyncio.run(test_ai())