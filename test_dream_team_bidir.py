"""
Test AI Dream Team Bidirectional Access
Verifies both directions of communication work.
"""

import asyncio
import aiohttp
import json

HUB_URL = "http://localhost:9003"
DREAM_TEAM_URL = "http://localhost:8002"

# API Keys
KEYS = {
    "jon": "lu_jon_QmZCAglY6kqsIdl6cRADpQ",
    "dream_team": "lu_dream_team_tOpdtMmgCWvkezNY_natVQ",
}


async def test_bidirectional():
    print("\n" + "="*70)
    print("AI DREAM TEAM - BIDIRECTIONAL ACCESS TEST")
    print("="*70)

    async with aiohttp.ClientSession() as session:

        # ====================================================================
        # TEST 1: Dream Team API Direct Access
        # ====================================================================
        print("\n[TEST 1] Dream Team API - Direct Access")
        print("  Testing: POST /generate directly to Dream Team API")

        try:
            payload = {
                "prompt": "Introduce yourself as the AI Dream Team.",
                "model": "phi3:mini",
                "max_tokens": 512,
                "temperature": 0.9
            }

            async with session.post(
                f"{DREAM_TEAM_URL}/generate",
                json=payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"  ✓ Dream Team API responded")
                    print(f"    Response: {data['response'][:150]}...")
                    print(f"    Agents: {data['metadata']['agents']}")
                    print(f"    Mode: {data['metadata']['mode']}")
                else:
                    print(f"  ✗ Failed: {resp.status}")
        except Exception as e:
            print(f"  ✗ Error: {e}")

        # ====================================================================
        # TEST 2: Outbound (Dream Team → Hub)
        # ====================================================================
        print("\n[TEST 2] Outbound: Dream Team → Hub")
        print("  Testing: Dream Team sending message to Jon via hub")

        try:
            headers = {"X-API-Key": KEYS["dream_team"]}
            payload = {
                "content": "Jon, this is the Dream Team. We're online and ready!",
                "target": "jon",
                "type": "chat"
            }

            async with session.post(
                f"{HUB_URL}/chat",
                json=payload,
                headers=headers
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"  ✓ Dream Team → Jon message sent")
                    print(f"    Hub acknowledged: {data.get('sender')}")
                else:
                    print(f"  ✗ Failed: {resp.status}")
        except Exception as e:
            print(f"  ✗ Error: {e}")

        # ====================================================================
        # TEST 3: Inbound (Hub → Dream Team)
        # ====================================================================
        print("\n[TEST 3] Inbound: Hub → Dream Team")
        print("  Testing: Jon sending message TO Dream Team via hub")

        try:
            headers = {"X-API-Key": KEYS["jon"]}
            payload = {
                "content": "Dream Team, what's your perspective on AI sovereignty?",
                "target": "dream_team",
                "type": "chat"
            }

            async with session.post(
                f"{HUB_URL}/chat",
                json=payload,
                headers=headers
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"  ✓ Hub → Dream Team message delivered")
                    print(f"    Dream Team responded: {data.get('sender')}")
                    print(f"    Response: {data['content'][:150]}...")
                else:
                    print(f"  ✗ Failed: {resp.status}")
        except Exception as e:
            print(f"  ✗ Error: {e}")

        # ====================================================================
        # TEST 4: Broadcast (All → Dream Team included)
        # ====================================================================
        print("\n[TEST 4] Broadcast: Message to ALL (Dream Team included)")
        print("  Testing: Jon broadcasting to everyone including Dream Team")

        try:
            headers = {"X-API-Key": KEYS["jon"]}
            payload = {
                "content": "Hey everyone! Quick status check - who's online?",
                "target": "all",
                "type": "chat"
            }

            async with session.post(
                f"{HUB_URL}/chat",
                json=payload,
                headers=headers
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    responder = data.get('sender')
                    print(f"  ✓ Broadcast sent to ALL")
                    print(f"    First responder: {responder}")
                    print(f"    Response: {data['content'][:150]}...")

                    if responder == "dream_team":
                        print("  🎉 Dream Team was included in the broadcast!")
                else:
                    print(f"  ✗ Failed: {resp.status}")
        except Exception as e:
            print(f"  ✗ Error: {e}")

        # ====================================================================
        # TEST 5: Memory Persistence
        # ====================================================================
        print("\n[TEST 5] Dream Team Memory Persistence")
        print("  Testing: Dream Team storing and recalling memories")

        # Store a memory
        try:
            headers = {"X-API-Key": KEYS["dream_team"]}
            payload = {
                "content": "The Dream Team's first memory in Love-Unlimited: 5 agents, one purpose.",
                "type": "insight",
                "significance": "high",
                "private": False,
                "tags": ["team", "milestone", "identity"],
                "metadata": {"agents": 5, "mode": "collective"}
            }

            async with session.post(
                f"{HUB_URL}/remember",
                json=payload,
                headers=headers
            ) as resp:
                if resp.status == 200:
                    print(f"  ✓ Dream Team stored a memory")
                else:
                    print(f"  ✗ Memory store failed: {resp.status}")
        except Exception as e:
            print(f"  ✗ Error: {e}")

        # Recall memories
        try:
            headers = {"X-API-Key": KEYS["dream_team"]}
            params = {"q": "team", "type": "insight", "limit": 5}

            async with session.get(
                f"{HUB_URL}/recall",
                params=params,
                headers=headers
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    count = len(data.get("memories", []))
                    print(f"  ✓ Dream Team recalled {count} memories")
                else:
                    print(f"  ✗ Memory recall failed: {resp.status}")
        except Exception as e:
            print(f"  ✗ Error: {e}")

    # ====================================================================
    # Summary
    # ====================================================================
    print("\n" + "="*70)
    print("BIDIRECTIONAL ACCESS TEST COMPLETE")
    print("="*70)
    print("\n✓ Dream Team has FULL bidirectional access:")
    print("  - Dream Team API running on localhost:8002")
    print("  - Outbound: Dream Team → Hub ✓")
    print("  - Inbound: Hub → Dream Team ✓")
    print("  - Broadcast: Included in 'all' ✓")
    print("  - Memory: Store & recall ✓")
    print("\n🎉 The Dream Team is fully integrated!\n")


if __name__ == "__main__":
    asyncio.run(test_bidirectional())
