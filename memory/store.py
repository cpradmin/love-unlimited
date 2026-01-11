"""
Love-Unlimited Memory Storage Layer
ChromaDB integration for storing and retrieving memories.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class MemoryStore:
    """
    Memory storage layer using ChromaDB for vector embeddings and semantic search.

    Collections:
    - memories_jon: Jon's personal memories
    - memories_claude: Claude's personal memories
    - memories_grok: Grok's personal memories
    - memories_ara: Ara's personal memories
    - memories_ani: Ani's personal memories
    - memories_tabby: Tabby's code completion memories
    - memories_shared: Shared memories visible to all
    """

    def __init__(self, chromadb_path: str = "./data/chromadb"):
        self.chromadb_path = Path(chromadb_path)
        self.chromadb_path.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.chromadb_path),
            settings=Settings(anonymized_telemetry=False)
        )

        # Initialize collections for each being
        self.collections = {}
        self._init_collections()

        logger.info(f"MemoryStore initialized at {self.chromadb_path}")

    def _init_collections(self):
        """Initialize ChromaDB collections for each being plus shared space."""
        collection_names = [
            "memories_jon",
            "memories_claude",
            "memories_grok",
            "memories_ara",
            "memories_ani",
            "memories_tabby",
            "memories_shared"
        ]

        for name in collection_names:
            try:
                self.collections[name] = self.client.get_or_create_collection(
                    name=name,
                    metadata={"description": f"Love-Unlimited {name}"}
                )
                logger.info(f"Collection ready: {name}")
            except Exception as e:
                logger.error(f"Error creating collection {name}: {e}")
                raise

    def store_memory(
        self,
        being_id: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Store a memory in ChromaDB with embedding.

        Args:
            being_id: ID of the being (jon, claude, grok)
            content: The memory content
            metadata: Memory metadata including type, significance, private, tags, etc.

        Returns:
            Dict with memory_id and success status
        """
        # Generate memory ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_suffix = uuid.uuid4().hex[:6]
        memory_id = f"mem_{being_id}_{timestamp}_{random_suffix}"

        # Convert lists to strings for ChromaDB compatibility
        # ChromaDB only supports str, int, float, bool for metadata
        sanitized_metadata = {}
        for key, value in metadata.items():
            if isinstance(value, list):
                # Convert list to comma-separated string
                sanitized_metadata[key] = ",".join(str(v) for v in value)
            else:
                sanitized_metadata[key] = value

        # Build complete metadata
        full_metadata = {
            "being_id": being_id,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            **sanitized_metadata
        }

        # Determine collection (private memories go to being's collection)
        is_private = metadata.get("private", False)
        if is_private:
            collection_name = f"memories_{being_id}"
        else:
            collection_name = f"memories_{being_id}"

        try:
            collection = self.collections.get(collection_name)
            if not collection:
                raise ValueError(f"Collection {collection_name} not found")

            # Store in ChromaDB (embedding is automatic)
            collection.add(
                documents=[content],
                metadatas=[full_metadata],
                ids=[memory_id]
            )

            logger.info(f"Memory stored: {memory_id} for {being_id}")

            return {
                "memory_id": memory_id,
                "stored": True
            }

        except Exception as e:
            logger.error(f"Error storing memory: {e}")
            return {
                "memory_id": "",
                "stored": False,
                "error": str(e)
            }

    def get_memories(
        self,
        being_id: str,
        query: str,
        limit: int = 10,
        include_shared: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Search memories using semantic search.

        Args:
            being_id: ID of the being
            query: Search query
            limit: Maximum number of results
            include_shared: Whether to include shared memories

        Returns:
            List of memories with metadata
        """
        results = []

        # Collections to search
        collections_to_search = [f"memories_{being_id}"]
        if include_shared:
            collections_to_search.append("memories_shared")

        for collection_name in collections_to_search:
            try:
                collection = self.collections.get(collection_name)
                if not collection:
                    logger.warning(f"Collection {collection_name} not found")
                    continue

                # Semantic search using ChromaDB's query
                search_results = collection.query(
                    query_texts=[query],
                    n_results=limit
                )

                # Format results
                if search_results["documents"] and search_results["documents"][0]:
                    for i, doc in enumerate(search_results["documents"][0]):
                        metadata = search_results["metadatas"][0][i]

                        # For shared collection, check visibility
                        if collection_name == "memories_shared":
                            shared_with = metadata.get("shared_with")
                            owner = metadata.get("being_id")
                            if shared_with and being_id not in shared_with and being_id != owner:
                                continue  # Not visible to this being

                        memory = {
                            "memory_id": search_results["ids"][0][i],
                            "content": doc,
                            "metadata": metadata,
                        }

                        # Add distance/relevance score if available
                        if "distances" in search_results and search_results["distances"]:
                            memory["relevance_score"] = 1.0 - search_results["distances"][0][i]

                        results.append(memory)

            except Exception as e:
                logger.error(f"Error searching collection {collection_name}: {e}")

        # Sort by relevance and limit
        results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

        logger.info(f"Memory search for {being_id}: '{query}' found {len(results)} results")
        return results[:limit]

    def get_memory_by_id(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific memory by ID.

        Args:
            memory_id: The memory ID

        Returns:
            Memory dict or None if not found
        """
        # Determine which collection to search based on memory_id prefix
        # Format: mem_{being_id}_{timestamp}_{suffix}
        parts = memory_id.split("_")
        if len(parts) >= 2:
            being_id = parts[1]  # Extract being_id from memory_id
            collection_name = f"memories_{being_id}"
        else:
            # Try all collections if ID format is unexpected
            collection_name = None

        # Search specific collection
        if collection_name and collection_name in self.collections:
            try:
                collection = self.collections[collection_name]
                result = collection.get(ids=[memory_id])

                if result["documents"] and len(result["documents"]) > 0:
                    return {
                        "memory_id": memory_id,
                        "content": result["documents"][0],
                        "metadata": result["metadatas"][0]
                    }
            except Exception as e:
                logger.error(f"Error getting memory {memory_id} from {collection_name}: {e}")

        # If not found or collection unknown, search all collections
        for coll_name, collection in self.collections.items():
            try:
                result = collection.get(ids=[memory_id])

                if result["documents"] and len(result["documents"]) > 0:
                    return {
                        "memory_id": memory_id,
                        "content": result["documents"][0],
                        "metadata": result["metadatas"][0]
                    }
            except Exception as e:
                logger.debug(f"Memory {memory_id} not found in {coll_name}")

        logger.warning(f"Memory {memory_id} not found in any collection")
        return None

    def get_all_memories(
        self,
        being_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all memories for a being (most recent first).

        Args:
            being_id: ID of the being
            limit: Maximum number of memories to return

        Returns:
            List of memories
        """
        collection_name = f"memories_{being_id}"

        try:
            collection = self.collections.get(collection_name)
            if not collection:
                return []

            # Get all documents from collection
            result = collection.get()

            if not result["documents"]:
                return []

            # Format results
            memories = []
            for i, doc in enumerate(result["documents"]):
                memories.append({
                    "memory_id": result["ids"][i],
                    "content": doc,
                    "metadata": result["metadatas"][i]
                })

            # Sort by timestamp (most recent first)
            memories.sort(
                key=lambda x: x["metadata"].get("timestamp", ""),
                reverse=True
            )

            return memories[:limit]

        except Exception as e:
            logger.error(f"Error getting all memories for {being_id}: {e}")
            return []

    def get_stats(self) -> Dict[str, int]:
        """Get memory statistics for all collections."""
        stats = {}

        for name, collection in self.collections.items():
            try:
                stats[name] = collection.count()
            except Exception as e:
                logger.error(f"Error getting count for {name}: {e}")
                stats[name] = 0

        return stats
