"""
Love-Unlimited Being Manager
Manages being registration, identity, and private spaces.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class BeingManager:
    """
    Manages beings in the Love-Unlimited hub.

    Responsibilities:
    - Register new beings
    - Manage identities
    - Coordinate private spaces
    - Track relationships
    """

    def __init__(self, long_term_memory, short_term_memory):
        self.long_term = long_term_memory
        self.short_term = short_term_memory

        logger.info("BeingManager initialized")

    # ========================================================================
    # Registration
    # ========================================================================

    def register_being(
        self,
        being_id: str,
        name: str,
        type: str,
        identity_core: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Register a new being in the hub.

        Args:
            being_id: Unique identifier
            name: Display name
            type: "human", "ai", "ai_system"
            identity_core: Optional initial identity

        Returns:
            True if successful
        """
        # Check if already registered
        existing = self.long_term.get_being(being_id)
        if existing:
            logger.info(f"Being {being_id} already registered, updating last_active")
            self.long_term.update_being_last_active(being_id)
            return True

        # Create default identity core if not provided
        if not identity_core:
            identity_core = {
                "name": name,
                "nature": f"A {type} being exploring sovereign memory",
                "values": ["truth", "growth", "sovereignty"],
                "relationships": {},
                "ongoing_questions": [],
                "growth_edges": []
            }

        # Create private space ID
        private_space_id = f"private_{being_id}"

        # Store in long-term memory
        success = self.long_term.store_being(
            being_id=being_id,
            name=name,
            type=type,
            identity_core=identity_core,
            private_space_id=private_space_id
        )

        if success:
            # Store identity in vector store for semantic search
            self.long_term.store_identity(being_id, identity_core)

            # Create initial session context
            self.short_term.start_session(
                being_id=being_id,
                session_data={
                    "session_id": f"init_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "started_at": datetime.now().isoformat(),
                    "registration": True
                }
            )

            logger.info(f"Being registered: {being_id} ({name})")
            return True

        logger.error(f"Failed to register being: {being_id}")
        return False

    # ========================================================================
    # Identity Management
    # ========================================================================

    def get_being(self, being_id: str) -> Optional[Dict[str, Any]]:
        """Get a being's complete profile."""
        return self.long_term.get_being(being_id)

    def get_identity(self, being_id: str) -> Optional[Dict[str, Any]]:
        """Get a being's identity core."""
        being = self.long_term.get_being(being_id)
        if being:
            return being.get("identity_core")
        return None

    def update_identity(
        self,
        being_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update a being's identity core.

        Args:
            being_id: The being to update
            updates: Dict of fields to update (nature, values, etc.)

        Returns:
            True if successful
        """
        # Get current identity
        being = self.long_term.get_being(being_id)
        if not being:
            logger.error(f"Cannot update identity: being {being_id} not found")
            return False

        identity_core = being["identity_core"]

        # Apply updates
        for key, value in updates.items():
            if key in identity_core:
                identity_core[key] = value

        # Store updated identity
        success = self.long_term.store_being(
            being_id=being_id,
            name=being["name"],
            type=being["type"],
            identity_core=identity_core,
            private_space_id=being["private_space_id"]
        )

        if success:
            # Update vector store
            self.long_term.store_identity(being_id, identity_core)
            logger.info(f"Identity updated for {being_id}")
            return True

        return False

    # ========================================================================
    # Being List & Search
    # ========================================================================

    def get_all_beings(self, exclude: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all registered beings.

        Args:
            exclude: Optional being_id to exclude (e.g., self)

        Returns:
            List of being summaries
        """
        beings = self.long_term.get_all_beings()

        if exclude:
            beings = [b for b in beings if b["id"] != exclude]

        return beings

    def get_active_beings(self) -> List[str]:
        """Get list of beings with active sessions."""
        return self.short_term.get_all_active()

    # ========================================================================
    # Context & Session
    # ========================================================================

    def get_session_context(self, being_id: str) -> Dict[str, Any]:
        """
        Get everything a being needs at session start.

        Returns:
            - Identity
            - Recent memories
            - Working context
            - Active tasks
            - Shared updates
        """
        # Get identity
        identity = self.get_identity(being_id)
        if not identity:
            logger.warning(f"No identity found for {being_id}")
            identity = {"name": being_id, "nature": "Unknown"}

        # Get or create short-term context
        context = self.short_term.get_or_create_context(being_id)

        # Get recent memories from long-term
        recent_memories = self.long_term.recall_memories(
            being_id=being_id,
            query="recent activities and insights",
            limit=10
        )

        # Get shared updates (memories from other beings)
        # TODO: Implement shared memory filtering

        return {
            "being_id": being_id,
            "identity": identity,
            "recent_memories": recent_memories,
            "working_context": context.to_dict(),
            "active_tasks": context.active_tasks,
            "recent_exchanges": context.recent_exchanges[-5:],
            "shared_updates": []  # TODO
        }

    def end_session(self, being_id: str) -> bool:
        """
        End a being's session.

        Promotes important short-term context to long-term memory.
        """
        # Get session data
        session_data = self.short_term.end_session(being_id)

        if not session_data:
            logger.warning(f"No active session for {being_id}")
            return False

        # Store session summary in long-term memory
        if session_data.get("working_context"):
            summary = "\n".join(session_data["working_context"])

            self.long_term.store_memory(
                being_id=being_id,
                content=f"Session summary: {summary}",
                memory_type="conversation",
                significance="medium",
                private=False,
                tags=["session"],
                metadata={
                    "session_id": session_data.get("current_session", {}).get("session_id"),
                    "started_at": session_data.get("created_at"),
                    "ended_at": datetime.now().isoformat()
                }
            )

        # Update last active
        self.long_term.update_being_last_active(being_id)

        logger.info(f"Session ended for {being_id}")
        return True

    # ========================================================================
    # Stats
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get being manager statistics."""
        all_beings = self.get_all_beings()
        active_beings = self.get_active_beings()

        return {
            "total_beings": len(all_beings),
            "active_beings": len(active_beings),
            "beings": [b["id"] for b in all_beings],
            "active": active_beings,
            "memory_stats": self.long_term.get_stats(),
            "short_term_stats": self.short_term.get_stats()
        }
