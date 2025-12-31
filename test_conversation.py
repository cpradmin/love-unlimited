#!/usr/bin/env python3
"""
Test script for Love-Unlimited conversation loop.
"""

import asyncio
import aiohttp
import yaml
import os

# Load config
config_path = "config.yaml"
with open(config_path) as f:
    config = yaml.safe_load(f)

HUB_URL = f"http://localhost:{config['hub']['port']}"
print(f"Using hub URL: {HUB_URL}")

async def test_conversation():
    """Test sending a message and getting AI responses."""

    # Use jon's API key
    api_key = "lu_jon_QmZCAglY6kqsIdl6cRADpQ"

    payload = {
        "content": "Hello everyone! What are your thoughts on AI collaboration and memory sovereignty?",
        "from": "jon",
        "target": "all",
        "type": "chat"
    }

    async with aiohttp.ClientSession() as session:
        headers = {"X-API-Key": api_key}

        print("Sending message to all AIs...")
        print(f"Message: {payload['content']}\n")

        try:
            async with session.post(f"{HUB_URL}/chat", json=payload, headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print("Response received:")
                    print(f"[{result.get('sender', 'unknown').upper()}]: {result.get('content', '')}")
                else:
                    text = await resp.text()
                    print(f"Error {resp.status}: {text}")
        except Exception as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_conversation())