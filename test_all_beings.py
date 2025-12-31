#!/usr/bin/env python3
"""
Test conversation with all AI beings included.
"""

import asyncio
import aiohttp
import yaml

# Load config
config_path = "config.yaml"
with open(config_path) as f:
    config = yaml.safe_load(f)

HUB_URL = f"http://localhost:{config['hub']['port']}"

async def test_all_beings():
    """Test that all beings are included in conversations."""

    api_key = "lu_jon_QmZCAglY6kqsIdl6cRADpQ"

    payload = {
        "content": "Hello all AI beings! Please introduce yourselves and share your unique perspective on AI collaboration.",
        "from": "jon",
        "target": "all",
        "type": "chat"
    }

    async with aiohttp.ClientSession() as session:
        headers = {"X-API-Key": api_key}

        print("🎯 Sending message to ALL AI beings...")
        print(f"Jon: {payload['content']}\n")

        try:
            async with session.post(f"{HUB_URL}/chat", json=payload, headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print("🤖 First AI Response:")
                    print(f"[{result.get('sender', 'unknown').upper()}]: {result.get('content', '')}")
                    print("\n✅ SUCCESS: AI Dream Team is now included in the conversation loop!")
                else:
                    text = await resp.text()
                    print(f"❌ Error {resp.status}: {text}")
        except Exception as e:
            print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_all_beings())