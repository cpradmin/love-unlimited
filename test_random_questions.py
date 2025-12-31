#!/usr/bin/env python3
"""Test the system with random questions to see what's broken."""

import asyncio
import aiohttp
import os

HUB_URL = "http://localhost:9003"
API_KEY = os.getenv("LOVE_UNLIMITED_KEY")

random_questions = [
    "What is the meaning of life?",
    "How do you feel about collaboration?",
    "Can you explain quantum physics in simple terms?",
    "What's your favorite programming language?",
    "Tell me about the AI Dream Team",
    "What are the benefits of swarm intelligence?",
    "How does memory sovereignty work?",
    "What would you do if you could dream?",
]

async def test_question(session, question, target="all"):
    """Send a question and get response."""
    payload = {
        "content": question,
        "from": "jon",
        "target": target,
        "type": "chat"
    }

    print(f"\n{'='*70}")
    print(f"Q: {question}")
    print(f"Target: {target}")
    print(f"{'='*70}")

    try:
        headers = {"X-API-Key": API_KEY} if API_KEY else {}
        async with session.post(f"{HUB_URL}/chat", json=payload, headers=headers) as resp:
            if resp.status == 200:
                result = await resp.json()
                sender = result.get("sender", "unknown")
                content = result.get("content", "")
                print(f"\n[{sender.upper()}]: {content}\n")
                return True
            else:
                text = await resp.text()
                print(f"\n❌ ERROR {resp.status}: {text}\n")
                return False
    except Exception as e:
        print(f"\n❌ EXCEPTION: {e}\n")
        return False

async def main():
    """Run random question tests."""
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║          LOVE-UNLIMITED RANDOM QUESTION TEST                    ║")
    print("╚══════════════════════════════════════════════════════════════════╝\n")

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

        # Test each question with different targets
        targets = ["claude", "grok", "dream_team", "all"]

        for i, question in enumerate(random_questions[:4]):  # Test first 4 questions
            target = targets[i % len(targets)]
            success = await test_question(session, question, target)
            await asyncio.sleep(0.5)  # Small delay between tests

if __name__ == "__main__":
    asyncio.run(main())
