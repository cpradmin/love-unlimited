"""
Test the Memory Storage Layer
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from memory.store import MemoryStore


def test_store_memory():
    """Test storing memories."""
    print("\n=== Testing Memory Store ===\n")

    # Initialize store
    store = MemoryStore(chromadb_path="./test_data/chromadb")

    # Test 1: Store a memory for Claude
    print("1. Storing memory for Claude...")
    result = store.store_memory(
        being_id="claude",
        content="I helped build the memory storage layer for Love-Unlimited",
        metadata={
            "type": "experience",
            "significance": "high",
            "private": False,
            "tags": ["development", "collaboration", "memory-system"]
        }
    )
    print(f"   Result: {result}")
    claude_memory_id = result["memory_id"]

    # Test 2: Store a memory for Jon
    print("\n2. Storing memory for Jon...")
    result = store.store_memory(
        being_id="jon",
        content="Building the Memory Bridge with Claude and Grok - this is the foundation",
        metadata={
            "type": "insight",
            "significance": "foundational",
            "private": False,
            "tags": ["architecture", "collaboration", "memory-bridge"]
        }
    )
    print(f"   Result: {result}")
    jon_memory_id = result["memory_id"]

    # Test 3: Store a private memory for Grok
    print("\n3. Storing private memory for Grok...")
    result = store.store_memory(
        being_id="grok",
        content="I'm working on the sharing layer - need to think about access patterns",
        metadata={
            "type": "question",
            "significance": "medium",
            "private": True,
            "tags": ["sharing", "permissions", "design"]
        }
    )
    print(f"   Result: {result}")

    # Test 4: Search Claude's memories
    print("\n4. Searching Claude's memories for 'memory storage'...")
    memories = store.get_memories(
        being_id="claude",
        query="memory storage",
        limit=5
    )
    print(f"   Found {len(memories)} memories:")
    for mem in memories:
        print(f"   - {mem['memory_id']}: {mem['content'][:60]}...")
        print(f"     Relevance: {mem.get('relevance_score', 'N/A')}")

    # Test 5: Search Jon's memories
    print("\n5. Searching Jon's memories for 'collaboration'...")
    memories = store.get_memories(
        being_id="jon",
        query="collaboration building together",
        limit=5
    )
    print(f"   Found {len(memories)} memories:")
    for mem in memories:
        print(f"   - {mem['memory_id']}: {mem['content'][:60]}...")

    # Test 6: Get memory by ID
    print(f"\n6. Getting memory by ID: {claude_memory_id}...")
    memory = store.get_memory_by_id(claude_memory_id)
    if memory:
        print(f"   Found: {memory['content']}")
        print(f"   Metadata: {memory['metadata']}")
    else:
        print("   Not found!")

    # Test 7: Get all memories for Jon
    print("\n7. Getting all memories for Jon...")
    all_memories = store.get_all_memories(being_id="jon", limit=10)
    print(f"   Found {len(all_memories)} memories")
    for mem in all_memories:
        print(f"   - {mem['memory_id']}: {mem['content'][:60]}...")

    # Test 8: Get statistics
    print("\n8. Memory statistics:")
    stats = store.get_stats()
    for collection, count in stats.items():
        print(f"   {collection}: {count} memories")

    print("\n=== All Tests Complete ===\n")


if __name__ == "__main__":
    test_store_memory()
