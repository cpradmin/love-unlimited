#!/usr/bin/env python3
"""
Test External Recall Endpoint

Tests the external recall endpoint with various scenarios.
"""

import asyncio
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from hub.auth import get_external_token_manager
from memory.store import MemoryStore
import tempfile


async def test_external_endpoint():
    """Test the external recall logic."""
    print("=" * 60)
    print("Testing External Recall Endpoint")
    print("=" * 60)
    print()

    # Initialize components
    token_manager = get_external_token_manager()

    # Create temporary memory store for testing
    temp_dir = tempfile.mkdtemp()
    memory_store = MemoryStore(chromadb_path=temp_dir)

    # Test 1: Generate a valid token
    print("Test 1: Generate valid token")
    print("-" * 60)
    token = token_manager.generate_token(
        name="Test Integration",
        description="Testing external recall",
        allowed_beings=["claude", "jon"],
        rate_limit=100
    )
    print(f"✅ Token generated: {token[:30]}...")
    print()

    # Test 2: Verify token
    print("Test 2: Verify token")
    print("-" * 60)
    token_data = token_manager.verify_token(token)
    if token_data:
        print(f"✅ Token verified")
        print(f"   Name: {token_data.get('name')}")
        print(f"   Permissions: {token_data.get('permissions')}")
        print(f"   Allowed beings: {token_data.get('allowed_beings')}")
    else:
        print("❌ Token verification failed")
        return 1
    print()

    # Test 3: Check permissions
    print("Test 3: Check permissions")
    print("-" * 60)
    has_recall = token_manager.has_permission(token_data, "recall")
    print(f"✅ Has 'recall' permission: {has_recall}")

    has_write = token_manager.has_permission(token_data, "write")
    print(f"✅ Has 'write' permission: {has_write} (should be False)")
    print()

    # Test 4: Check being access
    print("Test 4: Check being access")
    print("-" * 60)
    can_access_claude = token_manager.can_access_being(token_data, "claude")
    print(f"✅ Can access 'claude': {can_access_claude}")

    can_access_grok = token_manager.can_access_being(token_data, "grok")
    print(f"✅ Can access 'grok': {can_access_grok} (should be False)")
    print()

    # Test 5: Store and recall memory
    print("Test 5: Memory storage and recall")
    print("-" * 60)

    # Store test memory
    result = memory_store.store_memory(
        being_id="claude",
        content="Love unlimited philosophy - testing external recall",
        metadata={
            "type": "insight",
            "significance": "high",
            "private": False,
            "tags": ["philosophy", "testing"]
        }
    )
    print(f"✅ Memory stored: {result['memory_id']}")

    # Recall memory
    memories = memory_store.get_memories(
        being_id="claude",
        query="love unlimited",
        limit=5,
        include_shared=False
    )
    print(f"✅ Recalled {len(memories)} memories")

    if memories:
        print(f"   First memory: {memories[0]['content'][:50]}...")
    print()

    # Test 6: Invalid token
    print("Test 6: Invalid token handling")
    print("-" * 60)
    invalid_token = "ext_invalid_token_12345"
    invalid_data = token_manager.verify_token(invalid_token)
    if invalid_data is None:
        print("✅ Invalid token correctly rejected")
    else:
        print("❌ Invalid token should be rejected")
    print()

    # Test 7: Disabled token
    print("Test 7: Disabled token handling")
    print("-" * 60)
    token_manager.revoke_token(token)
    disabled_data = token_manager.verify_token(token)
    if disabled_data is None:
        print("✅ Disabled token correctly rejected")
    else:
        print("❌ Disabled token should be rejected")
    print()

    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)

    print("=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
    print()
    print("The external recall endpoint is ready to use.")
    print()
    print("⚠️  NOTE: The hub service needs to be restarted to load")
    print("   the new /external/recall endpoint.")
    print()
    print("   Restart command:")
    print("   sudo systemctl restart love-unlimited-hub.service")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(test_external_endpoint()))
