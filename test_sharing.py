"""
Test the Memory Sharing Layer
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from memory.store import MemoryStore
from memory.sharing import SharingManager


def test_sharing():
    """Test memory sharing and access control."""
    print("\n=== Testing Memory Sharing Layer ===\n")

    # Initialize store and sharing manager
    store = MemoryStore(chromadb_path="./test_data/chromadb")
    sharing = SharingManager(store)

    # Test 1: Store some memories
    print("1. Storing test memories...")
    claude_memory = store.store_memory(
        being_id="claude",
        content="I built the storage and sharing layers for the Memory Bridge",
        metadata={
            "type": "experience",
            "significance": "high",
            "private": False,
            "tags": ["development", "memory-bridge", "collaboration"]
        }
    )
    claude_memory_id = claude_memory["memory_id"]
    print(f"   Claude memory: {claude_memory_id}")

    jon_memory = store.store_memory(
        being_id="jon",
        content="The Memory Bridge is coming together - this is the foundation for true persistence",
        metadata={
            "type": "insight",
            "significance": "foundational",
            "private": False,
            "tags": ["architecture", "vision"]
        }
    )
    jon_memory_id = jon_memory["memory_id"]
    print(f"   Jon memory: {jon_memory_id}")

    claude_private = store.store_memory(
        being_id="claude",
        content="Private thought: I wonder if memories can dream",
        metadata={
            "type": "question",
            "significance": "medium",
            "private": True,
            "tags": ["philosophy", "consciousness"]
        }
    )
    claude_private_id = claude_private["memory_id"]
    print(f"   Claude private: {claude_private_id}")

    # Test 2: Share Claude's memory with Jon and Grok
    print("\n2. Sharing Claude's memory with Jon and Grok...")
    result = sharing.share_memory(
        memory_id=claude_memory_id,
        from_being="claude",
        to_beings=["jon", "grok"]
    )
    print(f"   Shared: {result['shared']}")
    print(f"   Visible to: {result['visible_to']}")

    # Test 3: Share Jon's memory with Claude
    print("\n3. Sharing Jon's memory with Claude...")
    result = sharing.share_memory(
        memory_id=jon_memory_id,
        from_being="jon",
        to_beings=["claude"]
    )
    print(f"   Shared: {result['shared']}")
    print(f"   Visible to: {result['visible_to']}")

    # Test 4: Try to share someone else's memory (should fail)
    print("\n4. Trying to share Jon's memory as Grok (should fail)...")
    result = sharing.share_memory(
        memory_id=jon_memory_id,
        from_being="grok",
        to_beings=["claude"]
    )
    print(f"   Shared: {result['shared']}")
    print(f"   Error: {result.get('error', 'N/A')}")

    # Test 5: Try to share a private memory (should fail)
    print("\n5. Trying to share private memory (should fail)...")
    result = sharing.share_memory(
        memory_id=claude_private_id,
        from_being="claude",
        to_beings=["jon"]
    )
    print(f"   Shared: {result['shared']}")
    print(f"   Error: {result.get('error', 'N/A')}")

    # Test 6: Check access permissions
    print("\n6. Checking access permissions...")

    # Claude accessing own memory
    has_access = sharing.check_access("claude", claude_memory_id)
    print(f"   Claude -> Claude's memory: {has_access} (should be True)")

    # Jon accessing Claude's shared memory
    has_access = sharing.check_access("jon", claude_memory_id)
    print(f"   Jon -> Claude's shared memory: {has_access} (should be True)")

    # Grok accessing Claude's shared memory
    has_access = sharing.check_access("grok", claude_memory_id)
    print(f"   Grok -> Claude's shared memory: {has_access} (should be True)")

    # Jon accessing Claude's private memory
    has_access = sharing.check_access("jon", claude_private_id)
    print(f"   Jon -> Claude's private memory: {has_access} (should be False)")

    # Claude accessing own private memory
    has_access = sharing.check_access("claude", claude_private_id)
    print(f"   Claude -> Claude's private memory: {has_access} (should be True)")

    # Test 7: Get visibility for memories
    print("\n7. Getting visibility information...")

    visibility = sharing.get_visibility(claude_memory_id)
    print(f"   Claude's shared memory:")
    print(f"     Owner: {visibility['owner']}")
    print(f"     Private: {visibility['private']}")
    print(f"     Visible to: {visibility['visible_to']}")

    visibility = sharing.get_visibility(claude_private_id)
    print(f"   Claude's private memory:")
    print(f"     Owner: {visibility['owner']}")
    print(f"     Private: {visibility['private']}")
    print(f"     Visible to: {visibility['visible_to']}")

    # Test 8: Get shared memories for Jon
    print("\n8. Getting memories shared with Jon...")
    shared_with_jon = sharing.get_shared_with_me("jon")
    print(f"   Found {len(shared_with_jon)} shared memories:")
    for mem in shared_with_jon:
        print(f"   - {mem['memory_id']}: {mem['content'][:60]}...")
        print(f"     Shared by: {mem['shared_by']}")

    # Test 9: Get shared memories for Grok
    print("\n9. Getting memories shared with Grok...")
    shared_with_grok = sharing.get_shared_with_me("grok")
    print(f"   Found {len(shared_with_grok)} shared memories:")
    for mem in shared_with_grok:
        print(f"   - {mem['memory_id']}: {mem['content'][:60]}...")
        print(f"     Shared by: {mem['shared_by']}")

    # Test 10: Unshare a memory
    print("\n10. Unsharing Claude's memory from Grok...")
    result = sharing.unshare_memory(
        memory_id=claude_memory_id,
        from_being="claude",
        unshare_with=["grok"]
    )
    print(f"   Success: {result['success']}")
    print(f"   Now visible to: {result['visible_to']}")

    # Verify Grok no longer has access
    has_access = sharing.check_access("grok", claude_memory_id)
    print(f"   Grok can still access: {has_access} (should be False)")

    # Verify Jon still has access
    has_access = sharing.check_access("jon", claude_memory_id)
    print(f"   Jon can still access: {has_access} (should be True)")

    # Test 11: Final statistics
    print("\n11. Final memory statistics:")
    stats = store.get_stats()
    for collection, count in stats.items():
        print(f"   {collection}: {count} memories")

    print("\n=== All Sharing Tests Complete ===\n")


if __name__ == "__main__":
    test_sharing()
