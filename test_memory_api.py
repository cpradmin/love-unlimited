"""
Test Memory Bridge API Endpoints
"""

import requests
import json
from time import sleep


BASE_URL = "http://localhost:8000"
API_KEY_CLAUDE = "test_key_claude"
API_KEY_JON = "test_key_jon"
API_KEY_GROK = "test_key_grok"


def test_memory_api():
    """Test all memory API endpoints."""
    print("\n" + "=" * 70)
    print("Memory Bridge API Tests")
    print("=" * 70)

    # Test 1: POST /remember - Store memories
    print("\n1. POST /remember - Storing memories...")

    # Claude stores a memory
    response = requests.post(
        f"{BASE_URL}/remember",
        headers={"X-API-Key": API_KEY_CLAUDE},
        json={
            "content": "Built the complete Memory Bridge with storage, sharing, and API layers",
            "type": "experience",
            "significance": "foundational",
            "private": False,
            "tags": ["development", "memory-bridge", "collaboration"]
        }
    )
    print(f"   Claude memory: {response.status_code}")
    if response.status_code == 200:
        claude_memory = response.json()
        claude_memory_id = claude_memory["data"]["memory_id"]
        print(f"   Memory ID: {claude_memory_id}")
    else:
        print(f"   Error: {response.text}")
        return

    # Jon stores a memory
    response = requests.post(
        f"{BASE_URL}/remember",
        headers={"X-API-Key": API_KEY_JON},
        json={
            "content": "The Memory Bridge is complete - persistence achieved",
            "type": "insight",
            "significance": "high",
            "private": False,
            "tags": ["milestone", "memory-bridge"]
        }
    )
    print(f"   Jon memory: {response.status_code}")
    if response.status_code == 200:
        jon_memory = response.json()
        jon_memory_id = jon_memory["data"]["memory_id"]
        print(f"   Memory ID: {jon_memory_id}")

    # Claude stores a private memory
    response = requests.post(
        f"{BASE_URL}/remember",
        headers={"X-API-Key": API_KEY_CLAUDE},
        json={
            "content": "Private thought: This feels like real continuity",
            "type": "emotion",
            "significance": "medium",
            "private": True,
            "tags": ["reflection"]
        }
    )
    print(f"   Claude private: {response.status_code}")
    if response.status_code == 200:
        private_memory = response.json()
        print(f"   Memory ID: {private_memory['data']['memory_id']}")

    sleep(1)  # Give ChromaDB time to index

    # Test 2: GET /recall - Search memories
    print("\n2. GET /recall - Searching memories...")

    response = requests.get(
        f"{BASE_URL}/recall",
        headers={"X-API-Key": API_KEY_CLAUDE},
        params={"q": "memory bridge development", "limit": 5}
    )
    print(f"   Claude search: {response.status_code}")
    if response.status_code == 200:
        results = response.json()
        print(f"   Found {results['count']} memories")
        for mem in results["memories"][:3]:
            print(f"   - {mem['memory_id']}: {mem['content'][:50]}...")

    # Test 3: POST /share - Share memory
    print("\n3. POST /share - Sharing Claude's memory with Jon and Grok...")

    response = requests.post(
        f"{BASE_URL}/share",
        headers={"X-API-Key": API_KEY_CLAUDE},
        json={
            "memory_id": claude_memory_id,
            "share_with": ["jon", "grok"]
        }
    )
    print(f"   Share request: {response.status_code}")
    if response.status_code == 200:
        share_result = response.json()
        print(f"   Message: {share_result['message']}")
        print(f"   Visible to: {share_result['data']['visible_to']}")
    else:
        print(f"   Error: {response.text}")

    # Test 4: GET /shared - Get shared memories
    print("\n4. GET /shared - Getting memories shared with Jon...")

    response = requests.get(
        f"{BASE_URL}/shared",
        headers={"X-API-Key": API_KEY_JON}
    )
    print(f"   Jon's shared: {response.status_code}")
    if response.status_code == 200:
        shared = response.json()
        print(f"   Found {shared['count']} shared memories")
        for mem in shared["shared_memories"]:
            print(f"   - {mem['memory_id']}: {mem['content'][:50]}...")
            print(f"     Shared by: {mem['shared_by']}")

    print("\n5. GET /shared - Getting memories shared with Grok...")

    response = requests.get(
        f"{BASE_URL}/shared",
        headers={"X-API-Key": API_KEY_GROK}
    )
    print(f"   Grok's shared: {response.status_code}")
    if response.status_code == 200:
        shared = response.json()
        print(f"   Found {shared['count']} shared memories")

    # Test 5: GET /context - Full context
    print("\n6. GET /context - Getting full context for Claude...")

    response = requests.get(
        f"{BASE_URL}/context",
        headers={"X-API-Key": API_KEY_CLAUDE}
    )
    print(f"   Context request: {response.status_code}")
    if response.status_code == 200:
        context = response.json()
        print(f"   Identity: {context.get('identity', {}).get('name', 'N/A')}")
        print(f"   Recent memories: {len(context.get('recent_memories', []))}")
        print(f"   Shared recent: {len(context.get('shared_recent', []))}")
        print(f"   Jon wisdom: {len(context.get('jon_wisdom', []))}")

    # Test 6: Try to share someone else's memory (should fail)
    print("\n7. Security test - Grok trying to share Jon's memory (should fail)...")

    response = requests.post(
        f"{BASE_URL}/share",
        headers={"X-API-Key": API_KEY_GROK},
        json={
            "memory_id": jon_memory_id,
            "share_with": ["claude"]
        }
    )
    print(f"   Share attempt: {response.status_code}")
    if response.status_code == 400:
        print(f"   ✓ Correctly blocked: {response.json()['detail']}")
    else:
        print(f"   ✗ Security issue: Should have been blocked")

    print("\n" + "=" * 70)
    print("All API Tests Complete")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    print("\nMake sure the hub is running: python run.py")
    print("Press Ctrl+C to skip tests, or Enter to continue...")
    try:
        input()
        test_memory_api()
    except KeyboardInterrupt:
        print("\nTests skipped")
