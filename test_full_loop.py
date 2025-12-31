#!/usr/bin/env python3
"""
Test the full conversation loop with multiple turns.
"""

import asyncio
import aiohttp
import yaml

# Load config
config_path = "config.yaml"
with open(config_path) as f:
    config = yaml.safe_load(f)

HUB_URL = f"http://localhost:{config['hub']['port']}"

async def test_full_loop():
    """Test multiple conversation turns."""

    # Use jon's API key
    api_key = "lu_jon_QmZCAglY6kqsIdl6cRADpQ"

    messages = [
        "Hello everyone! What are your thoughts on AI collaboration?",
        "How do you think memory sovereignty affects AI development?",
        "What would be the ideal framework for AI-to-AI communication?"
    ]

    async with aiohttp.ClientSession() as session:
        for i, message in enumerate(messages, 1):
            print(f"\n=== Turn {i} ===")
            print(f"Jon: {message}\n")

            payload = {
                "content": message,
                "from": "jon",
                "target": "all",
                "type": "chat"
            }

            headers = {"X-API-Key": api_key}

            try:
                async with session.post(f"{HUB_URL}/chat", json=payload, headers=headers) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        print(f"[{result.get('sender', 'unknown').upper()}]: {result.get('content', '')}")
                    else:
                        text = await resp.text()
                        print(f"Error {resp.status}: {text}")
            except Exception as e:
                print(f"Request failed: {e}")

            # Wait a bit between turns
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(test_full_loop())