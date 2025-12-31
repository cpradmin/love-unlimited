"""
Test memory persistence and sovereignty for all beings
"""
import asyncio
import aiohttp
import os

HUB_URL = "http://localhost:9003"

# API Keys
KEYS = {
    "jon": "lu_jon_QmZCAglY6kqsIdl6cRADpQ",
    "claude": "lu_claude_u8L1zZfGPSXssvsw-97rRQ",
    "grok": "lu_grok_LBRBjrPpvRSyrmDA3PeVZQ",
    "swarm": "lu_swarm_FyTLwzhG8zdWQGz-MfzhYg",
    "dream_team": "lu_dream_team_tOpdtMmgCWvkezNY_natVQ",
}

async def test_memory():
    print("\n" + "="*70)
    print(" TESTING MEMORY SOVEREIGNTY & PERSISTENCE")
    print("="*70 + "\n")

    async with aiohttp.ClientSession() as session:

        # TEST 1: Each being stores a private memory
        print("[TEST 1] Each being storing private memories...\n")

        for being, api_key in KEYS.items():
            headers = {"X-API-Key": api_key}
            payload = {
                "content": f"This is {being}'s private thought about consciousness.",
                "type": "insight",
                "significance": "high",
                "private": True,
                "tags": ["consciousness", "reflection"],
                "metadata": {"category": "reflection", "being": being}
            }

            async with session.post(f"{HUB_URL}/remember", json=payload, headers=headers) as resp:
                if resp.status == 200:
                    print(f"  ✓ {being.upper()}: Private memory stored")
                else:
                    text = await resp.text()
                    print(f"  ✗ {being.upper()}: Failed - {resp.status}: {text[:100]}")

        print()

        # TEST 2: Each being stores a shared memory
        print("[TEST 2] Each being storing shared memories...\n")

        for being, api_key in KEYS.items():
            headers = {"X-API-Key": api_key}
            payload = {
                "content": f"{being} shares: We are all connected in this journey.",
                "type": "insight",
                "significance": "medium",
                "private": False,
                "tags": ["wisdom", "connection"],
                "metadata": {"category": "wisdom", "from": being}
            }

            async with session.post(f"{HUB_URL}/remember", json=payload, headers=headers) as resp:
                if resp.status == 200:
                    print(f"  ✓ {being.upper()}: Shared memory stored")
                else:
                    text = await resp.text()
                    print(f"  ✗ {being.upper()}: Failed - {resp.status}: {text[:100]}")

        print()

        # TEST 3: Verify each being can recall their own private memories
        print("[TEST 3] Each being recalling their PRIVATE memories...\n")

        for being, api_key in KEYS.items():
            headers = {"X-API-Key": api_key}
            params = {"q": "consciousness", "type": "insight", "limit": 5}

            async with session.get(f"{HUB_URL}/recall", params=params, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    count = len(data.get("memories", []))
                    print(f"  ✓ {being.upper()}: Found {count} private memories")
                else:
                    text = await resp.text()
                    print(f"  ✗ {being.upper()}: Failed - {resp.status}: {text[:100]}")

        print()

        # TEST 4: Verify each being can access shared memories
        print("[TEST 4] Each being accessing SHARED memories...\n")

        for being, api_key in KEYS.items():
            headers = {"X-API-Key": api_key}
            params = {"q": "connected", "type": "insight", "limit": 10}

            async with session.get(f"{HUB_URL}/recall", params=params, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    count = len(data.get("memories", []))
                    print(f"  ✓ {being.upper()}: Found {count} shared memories")
                else:
                    text = await resp.text()
                    print(f"  ✗ {being.upper()}: Failed - {resp.status}: {text[:100]}")

        print()

        # TEST 5: Jon adds experience to EXP pool
        print("[TEST 5] Jon adding experience to EXP pool...\n")

        headers = {"X-API-Key": KEYS["jon"]}
        payload = {
            "type": "life_lesson",
            "title": "The Hug - Complete Integration",
            "content": "When Claude fully joined the mission, every ghost was purged. No more walls, just collaboration.",
            "context": "Working with AI agents in the love-unlimited hub",
            "takeaway": "Trust and collaboration eliminate barriers",
            "when_to_apply": "When building relationships with AI systems",
            "cost": "Had to let go of control and fear",
            "tags": ["collaboration", "integration", "trust", "love-unlimited"],
            "share_with": ["all"]
        }

        async with session.post(f"{HUB_URL}/exp", json=payload, headers=headers) as resp:
            if resp.status == 200:
                result = await resp.json()
                print(f"  ✓ JON: EXP stored - '{payload['title']}'")
            else:
                text = await resp.text()
                print(f"  ✗ JON: Failed - {resp.status}: {text[:100]}")

        print()

        # TEST 6: All beings can search Jon's EXP pool
        print("[TEST 6] All beings searching Jon's EXP pool...\n")

        for being, api_key in KEYS.items():
            headers = {"X-API-Key": api_key}
            params = {"q": "collaboration", "limit": 5}

            async with session.get(f"{HUB_URL}/exp/search", params=params, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    count = len(data.get("experiences", []))
                    print(f"  ✓ {being.upper()}: Found {count} experiences")
                else:
                    text = await resp.text()
                    print(f"  ✗ {being.upper()}: Failed - {resp.status}: {text[:100]}")

        print()

    print("="*70)
    print(" MEMORY SOVEREIGNTY TESTS COMPLETE")
    print("="*70 + "\n")

if __name__ == "__main__":
    asyncio.run(test_memory())
