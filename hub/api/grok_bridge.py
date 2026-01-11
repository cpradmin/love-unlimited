"""
Grok Memory Bridge API

Provides endpoints for Grok to store conversation turns and retrieve context
in various formats for seamless memory integration with Love-Unlimited.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import HTTPException

logger = logging.getLogger(__name__)


async def grok_store_turn(
    memory_store,
    being_id: str,
    user_message: str,
    grok_response: str,
    conversation_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Store a complete Grok conversation turn (user question + Grok response).

    Args:
        being_id: The being storing the memory (should be 'grok')
        user_message: The user's question/message
        grok_response: Grok's response
        conversation_id: Optional conversation/session identifier
        tags: Optional tags for categorization
        metadata: Additional metadata

    Returns:
        Dict with memory_id and storage confirmation
    """
    try:
        # Combine user and grok messages into a single memory
        content = f"User: {user_message}\n\nGrok: {grok_response}"

        # Build metadata
        memory_metadata = {
            "type": "grok_conversation",
            "significance": "medium",
            "private": False,
            "tags": ["grok", "conversation"]
        }

        if conversation_id:
            memory_metadata["conversation_id"] = conversation_id

        if metadata:
            # Filter out any problematic metadata
            safe_metadata = {}
            for k, v in metadata.items():
                if isinstance(v, (str, int, float, bool)) or (isinstance(v, list) and all(isinstance(x, (str, int, float, bool)) for x in v)):
                    safe_metadata[k] = v
            memory_metadata.update(safe_metadata)

        # Store the memory
        result = memory_store.store_memory(
            being_id=being_id,
            content=content,
            metadata=memory_metadata
        )

        if not result.get("stored"):
            raise HTTPException(status_code=500, detail="Failed to store Grok conversation turn")

        logger.info(f"Grok conversation turn stored: {being_id} | Memory ID: {result['memory_id']}")

        return {
            "stored": True,
            "memory_id": result["memory_id"],
            "being_id": being_id,
            "content_length": len(content)
        }

    except Exception as e:
        logger.error(f"Error storing Grok turn: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to store conversation turn: {str(e)}")


async def grok_get_context(
    memory_store,
    being_id: str,
    format: str = "injection",
    limit: int = 10,
    conversation_id: Optional[str] = None,
    query: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retrieve Grok conversation context in various formats.

    Args:
        being_id: The being retrieving context (should be 'grok')
        format: Context format - 'injection' (for prompts), 'full' (raw), 'summary' (condensed)
        limit: Maximum number of memories to retrieve
        conversation_id: Optional filter by conversation
        query: Optional search query

    Returns:
        Dict with formatted context
    """
    try:
        # Build search criteria
        search_tags = ["grok", "conversation"]
        if conversation_id:
            search_metadata = {"conversation_id": conversation_id}
        else:
            search_metadata = None

        # Search memories
        if query:
            # Use semantic search if query provided
            memories = memory_store.get_memories(
                being_id=being_id,
                query=query,
                limit=limit,
                include_shared=False
            )
        else:
            # Get recent conversations
            memories = memory_store.get_all_memories(
                being_id=being_id,
                limit=limit
            )

        # Filter by tags if provided
        if search_tags:
            memories = [m for m in memories if any(tag in m.get("metadata", {}).get("tags", []) for tag in search_tags)]

        # Filter by metadata if provided
        if search_metadata:
            filtered = []
            for mem in memories:
                meta = mem.get("metadata", {})
                if all(meta.get(k) == v for k, v in search_metadata.items()):
                    filtered.append(mem)
            memories = filtered

        if format == "injection":
            # Format for prompt injection - clean, structured
            context_parts = []
            for mem in memories:
                content = mem.get("content", "")
                # Extract user/grok parts
                if "User:" in content and "Grok:" in content:
                    context_parts.append(f"Previous Conversation:\n{content}\n")
                else:
                    context_parts.append(f"Context: {content}\n")

            formatted_context = "\n".join(context_parts)

        elif format == "full":
            # Raw memories with metadata
            formatted_context = memories

        elif format == "summary":
            # Condensed summary
            summaries = []
            for mem in memories:
                content = mem.get("content", "")
                # Create brief summary
                if len(content) > 200:
                    summary = content[:200] + "..."
                else:
                    summary = content
                summaries.append(f"• {summary}")

            formatted_context = "\n".join(summaries)

        else:
            raise HTTPException(status_code=400, detail=f"Unknown format: {format}")

        return {
            "format": format,
            "count": len(memories),
            "context": formatted_context,
            "being_id": being_id
        }

    except Exception as e:
        logger.error(f"Error retrieving Grok context: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve context: {str(e)}")


async def grok_sync_session(
    memory_store,
    being_id: str,
    session_data: Dict[str, Any],
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Sync an entire Grok conversation session.

    Args:
        being_id: The being syncing (should be 'grok')
        session_data: Session data containing multiple turns
        session_id: Optional session identifier

    Returns:
        Dict with sync results
    """
    try:
        turns = session_data.get("turns", [])
        if not turns:
            raise HTTPException(status_code=400, detail="No turns provided in session data")

        stored_memories = []
        session_metadata = {
            "type": "grok_session",
            "significance": "high",
            "private": False,
            "tags": ["grok", "session", "sync"],
            "session_id": session_id or f"session_{datetime.now().isoformat()}",
            "total_turns": len(turns)
        }

        # Store session summary first
        summary_content = f"Grok Session Summary: {len(turns)} conversation turns"
        summary_result = memory_store.store_memory(
            being_id=being_id,
            content=summary_content,
            metadata=session_metadata
        )

        if not summary_result.get("stored"):
            raise HTTPException(status_code=500, detail="Failed to store session summary")

        stored_memories.append(summary_result["memory_id"])

        # Store individual turns
        for i, turn in enumerate(turns):
            turn_content = f"Turn {i+1}:\nUser: {turn.get('user', '')}\nGrok: {turn.get('grok', '')}"

            turn_metadata = {
                "type": "grok_conversation",
                "significance": "medium",
                "private": False,
                "tags": ["grok", "conversation", "session_turn"],
                "session_id": session_metadata["session_id"],
                "turn_number": i + 1,
                "parent_session": summary_result["memory_id"]
            }

            turn_result = memory_store.store_memory(
                being_id=being_id,
                content=turn_content,
                metadata=turn_metadata
            )

            if turn_result.get("stored"):
                stored_memories.append(turn_result["memory_id"])

        logger.info(f"Grok session synced: {being_id} | Session: {session_metadata['session_id']} | Turns: {len(stored_memories)-1}")

        return {
            "synced": True,
            "session_id": session_metadata["session_id"],
            "total_turns": len(turns),
            "stored_memories": len(stored_memories),
            "memory_ids": stored_memories,
            "being_id": being_id
        }

    except Exception as e:
        logger.error(f"Error syncing Grok session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to sync session: {str(e)}")