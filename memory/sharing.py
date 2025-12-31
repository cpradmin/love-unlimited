"""
Love-Unlimited Memory Sharing Layer
Handles sharing memories between beings and access control.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from .store import MemoryStore

logger = logging.getLogger(__name__)


class SharingManager:
    """
    Manages memory sharing and access control.

    Handles:
    - Sharing memories between beings
    - Access control (who can see what)
    - Visibility tracking
    - Shared memory discovery
    """

    def __init__(self, memory_store: MemoryStore):
        """
        Initialize sharing manager.

        Args:
            memory_store: MemoryStore instance to use for storage
        """
        self.store = memory_store
        logger.info("SharingManager initialized")

    def share_memory(
        self,
        memory_id: str,
        from_being: str,
        to_beings: List[str]
    ) -> Dict[str, Any]:
        """
        Share a memory with other beings.

        Args:
            memory_id: ID of the memory to share
            from_being: Being who is sharing the memory
            to_beings: List of being IDs to share with

        Returns:
            Dict with sharing status and visibility list
        """
        logger.info(f"Sharing memory {memory_id} from {from_being} to {to_beings}")

        # 1. Get the original memory
        original = self.store.get_memory_by_id(memory_id)
        if not original:
            return {
                "shared": False,
                "error": "Memory not found",
                "visible_to": []
            }

        # 2. Verify ownership
        owner = original["metadata"].get("being_id")
        if owner != from_being:
            return {
                "shared": False,
                "error": "Only the owner can share this memory",
                "visible_to": [owner]
            }

        # Note: Private memories can now be shared

        # 4. Get existing shared_with list
        existing_shared = original["metadata"].get("shared_with", "")
        if existing_shared:
            # Convert comma-separated string back to list
            existing_list = [b.strip() for b in existing_shared.split(",") if b.strip()]
        else:
            existing_list = []

        # 5. Add new beings to shared list (avoid duplicates)
        updated_shared = set(existing_list)
        updated_shared.update(to_beings)
        updated_shared_str = ",".join(sorted(updated_shared))

        # 6. Create shared memory entry in memories_shared collection
        for being in to_beings:
            if being not in existing_list:
                self._add_to_shared_collection(
                    memory_id=memory_id,
                    content=original["content"],
                    metadata=original["metadata"],
                    shared_with=being,
                    shared_by=from_being
                )

        # 7. Update original memory's metadata with new shared_with list
        self._update_memory_metadata(
            memory_id=memory_id,
            being_id=owner,
            shared_with=updated_shared_str
        )

        # 8. Build visibility list (owner + shared_with)
        visible_to = [owner] + list(updated_shared)

        logger.info(f"Memory {memory_id} now visible to: {visible_to}")

        return {
            "shared": True,
            "visible_to": visible_to
        }

    def get_shared_with_me(self, being_id: str) -> List[Dict[str, Any]]:
        """
        Get all memories that others have shared with this being.

        Args:
            being_id: The being requesting shared memories

        Returns:
            List of shared memories
        """
        try:
            collection = self.store.collections.get("memories_shared")
            if not collection:
                return []

            # Get all memories from shared collection
            result = collection.get()

            if not result["documents"]:
                return []

            # Filter for memories shared with this being
            shared_memories = []
            for i, doc in enumerate(result["documents"]):
                metadata = result["metadatas"][i]
                shared_with = metadata.get("shared_with_being")

                if shared_with == being_id:
                    shared_memories.append({
                        "memory_id": metadata.get("original_memory_id"),
                        "content": doc,
                        "metadata": metadata,
                        "shared_by": metadata.get("shared_by"),
                        "shared_at": metadata.get("shared_at")
                    })

            # Sort by shared_at (most recent first)
            shared_memories.sort(
                key=lambda x: x.get("shared_at", ""),
                reverse=True
            )

            logger.info(f"Found {len(shared_memories)} memories shared with {being_id}")
            return shared_memories

        except Exception as e:
            logger.error(f"Error getting shared memories for {being_id}: {e}")
            return []

    def check_access(self, being_id: str, memory_id: str) -> bool:
        """
        Check if a being has access to a specific memory.

        Args:
            being_id: The being requesting access
            memory_id: The memory ID

        Returns:
            True if the being can access the memory, False otherwise
        """
        memory = self.store.get_memory_by_id(memory_id)
        if not memory:
            return False

        metadata = memory["metadata"]
        owner = metadata.get("being_id")

        # 1. Owner always has access
        if being_id == owner:
            return True

        # 2. Private memories can only be accessed by owner
        is_private = metadata.get("private", False)
        if is_private:
            return False

        # 3. Check if memory is shared with this being
        shared_with = metadata.get("shared_with", "")
        if shared_with:
            shared_list = [b.strip() for b in shared_with.split(",") if b.strip()]
            if being_id in shared_list:
                return True

        # 4. No access
        return False

    def get_visibility(self, memory_id: str) -> Dict[str, Any]:
        """
        Get visibility information for a memory.

        Args:
            memory_id: The memory ID

        Returns:
            Dict with owner and list of beings who can see this memory
        """
        memory = self.store.get_memory_by_id(memory_id)
        if not memory:
            return {
                "memory_id": memory_id,
                "exists": False,
                "owner": None,
                "visible_to": []
            }

        metadata = memory["metadata"]
        owner = metadata.get("being_id")
        is_private = metadata.get("private", False)

        # Build visibility list
        visible_to = [owner]

        if not is_private:
            shared_with = metadata.get("shared_with", "")
            if shared_with:
                shared_list = [b.strip() for b in shared_with.split(",") if b.strip()]
                visible_to.extend(shared_list)

        return {
            "memory_id": memory_id,
            "exists": True,
            "owner": owner,
            "private": is_private,
            "visible_to": list(set(visible_to))  # Remove duplicates
        }

    def _add_to_shared_collection(
        self,
        memory_id: str,
        content: str,
        metadata: Dict[str, Any],
        shared_with: str,
        shared_by: str
    ):
        """
        Add a memory to the shared collection.

        Creates a reference in memories_shared that points to the original memory
        and tracks who it's shared with.
        """
        try:
            collection = self.store.collections["memories_shared"]

            # Create unique ID for shared reference
            shared_ref_id = f"shared_{shared_with}_{memory_id}"

            # Build metadata for shared reference
            shared_metadata = {
                "original_memory_id": memory_id,
                "shared_with_being": shared_with,
                "shared_by": shared_by,
                "shared_at": datetime.now().isoformat(),
                "type": metadata.get("type", ""),
                "significance": metadata.get("significance", ""),
                "tags": metadata.get("tags", "")
            }

            # Add to shared collection
            collection.add(
                documents=[content],
                metadatas=[shared_metadata],
                ids=[shared_ref_id]
            )

            logger.debug(f"Added {memory_id} to shared collection for {shared_with}")

        except Exception as e:
            logger.error(f"Error adding to shared collection: {e}")

    def _update_memory_metadata(
        self,
        memory_id: str,
        being_id: str,
        shared_with: str
    ):
        """
        Update a memory's metadata to reflect new sharing status.

        ChromaDB doesn't support updating metadata directly, so we need to
        delete and re-add with updated metadata.
        """
        try:
            # Get the memory
            memory = self.store.get_memory_by_id(memory_id)
            if not memory:
                return

            collection_name = f"memories_{being_id}"
            collection = self.store.collections.get(collection_name)
            if not collection:
                return

            # Update metadata
            updated_metadata = memory["metadata"].copy()
            updated_metadata["shared_with"] = shared_with

            # Delete and re-add with updated metadata
            collection.delete(ids=[memory_id])
            collection.add(
                documents=[memory["content"]],
                metadatas=[updated_metadata],
                ids=[memory_id]
            )

            logger.debug(f"Updated metadata for {memory_id}")

        except Exception as e:
            logger.error(f"Error updating memory metadata: {e}")

    def unshare_memory(
        self,
        memory_id: str,
        from_being: str,
        unshare_with: List[str]
    ) -> Dict[str, Any]:
        """
        Revoke sharing access for specific beings.

        Args:
            memory_id: ID of the memory
            from_being: Being who is revoking access
            unshare_with: List of being IDs to revoke access from

        Returns:
            Dict with success status and updated visibility
        """
        # Get the original memory
        original = self.store.get_memory_by_id(memory_id)
        if not original:
            return {
                "success": False,
                "error": "Memory not found"
            }

        # Verify ownership
        owner = original["metadata"].get("being_id")
        if owner != from_being:
            return {
                "success": False,
                "error": "Only the owner can unshare this memory"
            }

        # Get existing shared_with list
        existing_shared = original["metadata"].get("shared_with", "")
        if existing_shared:
            existing_list = [b.strip() for b in existing_shared.split(",") if b.strip()]
        else:
            existing_list = []

        # Remove beings from shared list
        updated_shared = [b for b in existing_list if b not in unshare_with]
        updated_shared_str = ",".join(updated_shared)

        # Remove from shared collection
        collection = self.store.collections.get("memories_shared")
        if collection:
            for being in unshare_with:
                shared_ref_id = f"shared_{being}_{memory_id}"
                try:
                    collection.delete(ids=[shared_ref_id])
                    logger.debug(f"Removed {shared_ref_id} from shared collection")
                except Exception as e:
                    logger.debug(f"Could not remove {shared_ref_id}: {e}")

        # Update original memory's metadata
        self._update_memory_metadata(
            memory_id=memory_id,
            being_id=owner,
            shared_with=updated_shared_str
        )

        # Build updated visibility list
        visible_to = [owner] + updated_shared

        logger.info(f"Memory {memory_id} unshared from {unshare_with}")

        return {
            "success": True,
            "visible_to": visible_to
        }
