#!/usr/bin/env python3
"""Test with real AI APIs (fixing environment variable names)."""

import asyncio
import aiohttp
import os

HUB_URL = "http://localhost:9003"
API_KEY = os.getenv("LOVE_UNLIMITED_KEY")

# Set the correct environment variable for Grok
if os.getenv("GROK_API_KEY"):
    os.environ["XAI_API_KEY"] = os.getenv("GROK_API_KEY")
    print(f"✓ Set XAI_API_KEY from GROK_API_KEY")

questions = [
    ("grok", "What is 2+2?"),
    ("grok", "Tell me a joke about programmers"),
    ("grok", "What's the capital of France?"),
]

async def test_question(session, target, question):
    """Send a question to a specific AI."""
    payload = {
        "content": question,
        "from": "jon",
        "target": target,
        "type": "chat"
    }

    print(f"\n{'='*70}")
    print(f"Q to {target.upper()}: {question}")
    print(f"{'='*70}")

    try:
        headers = {"X-API-Key": API_KEY} if API_KEY else {}
        async with session.post(f"{HUB_URL}/chat", json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as resp:
            if resp.status == 200:
                result = await resp.json()
                sender = result.get("sender", "unknown")
                content = result.get("content", "")
                print(f"\n[{sender.upper()}]: {content}\n")

                # Check if response is on-topic
                if "2+2" in question and "4" in content:
                    print("✓ Response seems accurate!")
                elif "joke" in question.lower() and len(content) > 20:
                    print("✓ Got a response (checking if it's a joke)")
                elif "France" in question and "Paris" in content:
                    print("✓ Response is correct!")
                else:
                    print("⚠ Response might be generic/canned")

                return True
            else:
                text = await resp.text()
                print(f"\n❌ ERROR {resp.status}: {text}\n")
                return False
    except Exception as e:
        print(f"\n❌ EXCEPTION: {e}\n")
        return False

async def main():
    """Run tests."""
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║          TESTING WITH REAL AI APIs                              ║")
    print("╚══════════════════════════════════════════════════════════════════╝\n")

    # Restart the hub to pick up new environment variables
    print("⚠ NOTE: You may need to restart the hub for env var changes to take effect\n")

    async with aiohttp.ClientSession() as session:
        # Test hub health
        try:
            headers = {"X-API-Key": API_KEY} if API_KEY else {}
            async with session.get(f"{HUB_URL}/health", headers=headers) as resp:
                if resp.status == 200:
                    health = await resp.json()
                    print(f"✅ Hub Status: {health.get('status', 'unknown').upper()}")
                    print(f"   Version: {health.get('version', 'unknown')}\n")
                else:
                    print(f"❌ Hub unhealthy: {resp.status}\n")
                    return
        except Exception as e:
            print(f"❌ Hub unreachable: {e}\n")
            return

        # Run tests
        for target, question in questions:
            await test_question(session, target, question)
            await asyncio.sleep(1)  # Small delay between tests

if __name__ == "__main__":
    asyncio.run(main())
