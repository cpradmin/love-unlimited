"""
Love-Unlimited Short-Term Memory
In-memory working context for active sessions.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class WorkingContext:
    """Working context for a being's session."""
    being_id: str
    current_session: Dict[str, Any] = field(default_factory=dict)
    working_context: List[str] = field(default_factory=list)
    active_tasks: List[str] = field(default_factory=list)
    recent_exchanges: List[Dict[str, Any]] = field(default_factory=list)
    expires_at: datetime = field(default_factory=lambda: datetime.now() + timedelta(hours=1))
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["expires_at"] = self.expires_at.isoformat()
        data["created_at"] = self.created_at.isoformat()
        return data

    def is_expired(self) -> bool:
        """Check if context has expired."""
        return datetime.now() > self.expires_at

    def extend_expiry(self, hours: int = 1):
        """Extend expiration time."""
        self.expires_at = datetime.now() + timedelta(hours=hours)


class ShortTermMemory:
    """
    Short-term memory store for active sessions.

    Keeps working context, active conversations, and recent exchanges
    in memory (or Redis for persistence).

    This is ephemeral - expires after session ends.
    """

    def __init__(
        self,
        session_ttl: int = 3600,  # 1 hour in seconds
        max_context_items: int = 100,
        use_redis: bool = False,
        redis_url: str = "redis://localhost:6379"
    ):
        self.session_ttl = session_ttl
        self.max_context_items = max_context_items
        self.use_redis = use_redis
        self.redis_url = redis_url

        # In-memory storage
        self.contexts: Dict[str, WorkingContext] = {}

        # TODO: Add Redis support for persistence
        if use_redis:
            logger.warning("Redis support not yet implemented, using in-memory only")

        logger.info(f"ShortTermMemory initialized (TTL: {session_ttl}s, max items: {max_context_items})")

    # ========================================================================
    # Context Management
    # ========================================================================

    def set_context(self, being_id: str, context: WorkingContext):
        """Set working context for a being."""
        self.contexts[being_id] = context
        logger.info(f"Context set for {being_id}")

    def get_context(self, being_id: str) -> Optional[WorkingContext]:
        """Get working context for a being."""
        context = self.contexts.get(being_id)

        if context:
            # Check if expired
            if context.is_expired():
                logger.info(f"Context for {being_id} has expired, removing")
                self.clear_context(being_id)
                return None

            # Extend expiry on access
            context.extend_expiry()
            return context

        return None

    def get_or_create_context(self, being_id: str) -> WorkingContext:
        """Get existing context or create new one."""
        context = self.get_context(being_id)

        if not context:
            context = WorkingContext(being_id=being_id)
            self.set_context(being_id, context)
            logger.info(f"Created new context for {being_id}")

        return context

    def clear_context(self, being_id: str):
        """Clear context for a being."""
        if being_id in self.contexts:
            del self.contexts[being_id]
            logger.info(f"Context cleared for {being_id}")

    # ========================================================================
    # Session Management
    # ========================================================================

    def start_session(
        self,
        being_id: str,
        session_data: Dict[str, Any] = None
    ) -> WorkingContext:
        """Start a new session for a being."""
        context = WorkingContext(
            being_id=being_id,
            current_session=session_data or {
                "session_id": f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "started_at": datetime.now().isoformat()
            }
        )
        self.set_context(being_id, context)
        logger.info(f"Session started for {being_id}")
        return context

    def end_session(self, being_id: str) -> Optional[Dict[str, Any]]:
        """End session and return context for promotion to long-term."""
        context = self.get_context(being_id)

        if context:
            session_data = context.to_dict()
            self.clear_context(being_id)
            logger.info(f"Session ended for {being_id}")
            return session_data

        return None

    # ========================================================================
    # Working Context Items
    # ========================================================================

    def add_to_context(
        self,
        being_id: str,
        item: str,
        item_type: str = "note"
    ):
        """Add an item to working context."""
        context = self.get_or_create_context(being_id)

        # Add item
        context.working_context.append(item)

        # Enforce max items (keep most recent)
        if len(context.working_context) > self.max_context_items:
            context.working_context = context.working_context[-self.max_context_items:]

        logger.debug(f"Added to context for {being_id}: {item[:50]}...")

    def get_working_context(self, being_id: str) -> List[str]:
        """Get all working context items."""
        context = self.get_context(being_id)
        return context.working_context if context else []

    def clear_working_context(self, being_id: str):
        """Clear working context items (keep session active)."""
        context = self.get_context(being_id)
        if context:
            context.working_context = []
            logger.info(f"Working context cleared for {being_id}")

    # ========================================================================
    # Active Tasks
    # ========================================================================

    def add_task(self, being_id: str, task: str):
        """Add an active task."""
        context = self.get_or_create_context(being_id)
        context.active_tasks.append(task)
        logger.debug(f"Task added for {being_id}: {task}")

    def remove_task(self, being_id: str, task: str):
        """Remove a completed task."""
        context = self.get_context(being_id)
        if context and task in context.active_tasks:
            context.active_tasks.remove(task)
            logger.debug(f"Task removed for {being_id}: {task}")

    def get_active_tasks(self, being_id: str) -> List[str]:
        """Get all active tasks."""
        context = self.get_context(being_id)
        return context.active_tasks if context else []

    def clear_tasks(self, being_id: str):
        """Clear all active tasks."""
        context = self.get_context(being_id)
        if context:
            context.active_tasks = []
            logger.info(f"Tasks cleared for {being_id}")

    # ========================================================================
    # Recent Exchanges
    # ========================================================================

    def add_exchange(
        self,
        being_id: str,
        exchange_type: str,
        content: str,
        metadata: Dict[str, Any] = None
    ):
        """Add a recent exchange (conversation, question, insight)."""
        context = self.get_or_create_context(being_id)

        exchange = {
            "type": exchange_type,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        }

        context.recent_exchanges.append(exchange)

        # Keep last 50 exchanges
        if len(context.recent_exchanges) > 50:
            context.recent_exchanges = context.recent_exchanges[-50:]

        logger.debug(f"Exchange added for {being_id}: {exchange_type}")

    def get_recent_exchanges(
        self,
        being_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent exchanges."""
        context = self.get_context(being_id)
        if context:
            return context.recent_exchanges[-limit:]
        return []

    # ========================================================================
    # Cleanup
    # ========================================================================

    def cleanup_expired(self):
        """Remove expired contexts."""
        expired = [
            being_id
            for being_id, context in self.contexts.items()
            if context.is_expired()
        ]

        for being_id in expired:
            self.clear_context(being_id)

        if expired:
            logger.info(f"Cleaned up {len(expired)} expired contexts")

    def get_active_count(self) -> int:
        """Get count of active contexts."""
        return len(self.contexts)

    def get_all_active(self) -> List[str]:
        """Get list of all beings with active contexts."""
        self.cleanup_expired()
        return list(self.contexts.keys())

    # ========================================================================
    # Stats
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get short-term memory statistics."""
        self.cleanup_expired()

        return {
            "active_contexts": len(self.contexts),
            "beings": list(self.contexts.keys()),
            "total_working_items": sum(
                len(ctx.working_context) for ctx in self.contexts.values()
            ),
            "total_active_tasks": sum(
                len(ctx.active_tasks) for ctx in self.contexts.values()
            ),
            "total_exchanges": sum(
                len(ctx.recent_exchanges) for ctx in self.contexts.values()
            )
        }
