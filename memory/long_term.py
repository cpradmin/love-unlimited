"""
Love-Unlimited Long-Term Memory
ChromaDB for vector storage + SQLite for structured data.
"""

import logging
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

import chromadb
from chromadb.config import Settings
from sqlalchemy import create_engine, Column, String, DateTime, JSON, Integer, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

Base = declarative_base()


# ============================================================================
# SQLite Models
# ============================================================================

class BeingRecord(Base):
    """Being profile in SQLite."""
    __tablename__ = "beings"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)
    last_active = Column(DateTime, nullable=False)
    identity_core = Column(JSON, nullable=False)
    private_space_id = Column(String, nullable=False)
    extra_data = Column(JSON, default={})


class RelationshipRecord(Base):
    """Relationships between beings."""
    __tablename__ = "relationships"

    id = Column(String, primary_key=True)
    being_a_id = Column(String, nullable=False)
    being_b_id = Column(String, nullable=False)
    relationship_type = Column(String, nullable=False)  # "collaboration", "learning", etc.
    strength = Column(Float, default=0.5)  # 0.0 to 1.0
    extra_data = Column(JSON, default={})
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class ProjectRecord(Base):
    """Shared projects."""
    __tablename__ = "projects"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    participants = Column(JSON, nullable=False)  # List of being_ids
    status = Column(String, default="active")  # "active", "completed", "paused"
    extra_data = Column(JSON, default={})
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class TimelineRecord(Base):
    """Event timeline."""
    __tablename__ = "timeline"

    id = Column(String, primary_key=True)
    event_type = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    being_id = Column(String)  # Null if collective event
    participants = Column(JSON, default=[])
    extra_data = Column(JSON, default={})
    timestamp = Column(DateTime, nullable=False)


# ============================================================================
# Long-Term Memory Manager
# ============================================================================

class LongTermMemory:
    """
    Long-term memory storage using ChromaDB (vector) + SQLite (structured).

    This is where permanent memories live:
    - Being identities
    - Personal memories (private)
    - Shared experiences
    - Jon's EXP pool
    """

    def __init__(
        self,
        chromadb_path: str = "./data/chromadb",
        sqlite_path: str = "./data/love_unlimited.db"
    ):
        self.chromadb_path = Path(chromadb_path)
        self.sqlite_path = Path(sqlite_path)

        # Ensure directories exist
        self.chromadb_path.parent.mkdir(parents=True, exist_ok=True)
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB
        self._init_chromadb()

        # Initialize SQLite
        self._init_sqlite()

        logger.info("LongTermMemory initialized")

    def _init_chromadb(self):
        """Initialize ChromaDB client and collections."""
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.chromadb_path),
            settings=Settings(anonymized_telemetry=False)
        )

        # Create collections
        self.collections = {}

        collection_names = [
            "beings_identity",
            "beings_memories",
            "shared_memories",
            "jon_exp",
            "private_jon",
            "private_claude",
            "private_grok",
            "n8n_docs",
        ]

        for name in collection_names:
            try:
                self.collections[name] = self.chroma_client.get_or_create_collection(
                    name=name,
                    metadata={"description": f"Love-Unlimited {name}"}
                )
                logger.info(f"ChromaDB collection ready: {name}")
            except Exception as e:
                logger.error(f"Error creating collection {name}: {e}")

    def _init_sqlite(self):
        """Initialize SQLite database and tables."""
        self.engine = create_engine(f"sqlite:///{self.sqlite_path}")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        logger.info(f"SQLite database ready: {self.sqlite_path}")

    # ========================================================================
    # Being Management
    # ========================================================================

    def store_being(
        self,
        being_id: str,
        name: str,
        type: str,
        identity_core: Dict[str, Any],
        private_space_id: str
    ) -> bool:
        """Store or update a being's profile."""
        session = self.Session()
        try:
            being = session.query(BeingRecord).filter_by(id=being_id).first()

            if being:
                # Update existing
                being.name = name
                being.type = type
                being.identity_core = identity_core
                being.last_active = datetime.now()
            else:
                # Create new
                being = BeingRecord(
                    id=being_id,
                    name=name,
                    type=type,
                    created_at=datetime.now(),
                    last_active=datetime.now(),
                    identity_core=identity_core,
                    private_space_id=private_space_id,
                    metadata={}
                )
                session.add(being)

            session.commit()
            logger.info(f"Being stored: {being_id}")
            return True

        except Exception as e:
            logger.error(f"Error storing being {being_id}: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    def get_being(self, being_id: str) -> Optional[Dict[str, Any]]:
        """Get a being's profile."""
        session = self.Session()
        try:
            being = session.query(BeingRecord).filter_by(id=being_id).first()

            if being:
                return {
                    "id": being.id,
                    "name": being.name,
                    "type": being.type,
                    "created_at": being.created_at.isoformat(),
                    "last_active": being.last_active.isoformat(),
                    "identity_core": being.identity_core,
                    "private_space_id": being.private_space_id,
                    "extra_data": being.extra_data
                }
            return None

        except Exception as e:
            logger.error(f"Error getting being {being_id}: {e}")
            return None
        finally:
            session.close()

    def get_all_beings(self) -> List[Dict[str, Any]]:
        """Get all registered beings."""
        session = self.Session()
        try:
            beings = session.query(BeingRecord).all()
            return [
                {
                    "id": b.id,
                    "name": b.name,
                    "type": b.type,
                    "created_at": b.created_at.isoformat(),
                    "last_active": b.last_active.isoformat()
                }
                for b in beings
            ]
        except Exception as e:
            logger.error(f"Error getting all beings: {e}")
            return []
        finally:
            session.close()

    def update_being_last_active(self, being_id: str):
        """Update being's last active timestamp."""
        session = self.Session()
        try:
            being = session.query(BeingRecord).filter_by(id=being_id).first()
            if being:
                being.last_active = datetime.now()
                session.commit()
        except Exception as e:
            logger.error(f"Error updating last_active for {being_id}: {e}")
            session.rollback()
        finally:
            session.close()

    def update_being_extra_data(self, being_id: str, extra_data: Dict[str, Any]) -> bool:
        """Update being's extra_data JSON column."""
        session = self.Session()
        try:
            being = session.query(BeingRecord).filter_by(id=being_id).first()
            if being:
                being.extra_data = extra_data
                session.commit()
                logger.info(f"Updated extra_data for {being_id}")
                return True
            else:
                logger.warning(f"Being {being_id} not found")
                return False
        except Exception as e:
            logger.error(f"Error updating extra_data for {being_id}: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    # ========================================================================
    # Memory Storage
    # ========================================================================

    def store_memory(
        self,
        being_id: str,
        content: str,
        memory_type: str,
        significance: str,
        private: bool = False,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Store a memory.

        Returns:
            memory_id
        """
        memory_id = f"mem_{uuid.uuid4().hex[:12]}"
        tags = tags or []
        metadata = metadata or {}

        # Add timestamp and being info to metadata
        metadata.update({
            "being_id": being_id,
            "type": memory_type,
            "significance": significance,
            "private": private,
            "timestamp": datetime.now().isoformat()
        })

        # Determine collection
        if private:
            collection_name = f"private_{being_id}"
        else:
            collection_name = "beings_memories"

        # Store in ChromaDB
        try:
            collection = self.collections.get(collection_name)
            if not collection:
                logger.warning(f"Collection {collection_name} not found, using beings_memories")
                collection = self.collections["beings_memories"]

            collection.add(
                documents=[content],
                metadatas=[metadata],
                ids=[memory_id]
            )

            logger.info(f"Memory stored: {memory_id} for {being_id} (private={private})")
            return memory_id

        except Exception as e:
            logger.error(f"Error storing memory: {e}")
            return ""

    def recall_memories(
        self,
        being_id: str,
        query: str,
        limit: int = 20,
        memory_type: Optional[str] = None,
        include_private: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Recall memories using semantic search.

        Searches both personal (including private if allowed) and shared memories.
        """
        results = []

        # Collections to search
        collections_to_search = ["beings_memories", "shared_memories"]

        if include_private:
            private_collection = f"private_{being_id}"
            if private_collection in self.collections:
                collections_to_search.insert(0, private_collection)

        for collection_name in collections_to_search:
            try:
                collection = self.collections[collection_name]

                # Build filter if type specified
                where = {"being_id": being_id} if collection_name.startswith("private") else None
                if memory_type and where:
                    where["type"] = memory_type
                elif memory_type:
                    where = {"type": memory_type}

                # Query
                search_results = collection.query(
                    query_texts=[query],
                    n_results=limit,
                    where=where if where else None
                )

                # Format results
                if search_results["documents"] and search_results["documents"][0]:
                    for i, doc in enumerate(search_results["documents"][0]):
                        results.append({
                            "memory_id": search_results["ids"][0][i],
                            "content": doc,
                            "metadata": search_results["metadatas"][0][i],
                            "distance": search_results["distances"][0][i] if "distances" in search_results else None
                        })

            except Exception as e:
                logger.error(f"Error searching collection {collection_name}: {e}")

        # Sort by relevance (distance) and limit
        results.sort(key=lambda x: x.get("distance", 999))
        return results[:limit]

    # ========================================================================
    # Shared Memories
    # ========================================================================

    def store_shared_memory(
        self,
        being_id: str,
        content: str,
        memory_type: str,
        significance: str,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Store a memory in the shared space."""
        memory_id = f"shared_{uuid.uuid4().hex[:12]}"
        tags = tags or []
        metadata = metadata or {}

        metadata.update({
            "being_id": being_id,
            "type": memory_type,
            "significance": significance,
            "shared": True,
            "timestamp": datetime.now().isoformat()
        })

        try:
            self.collections["shared_memories"].add(
                documents=[content],
                metadatas=[metadata],
                ids=[memory_id]
            )

            logger.info(f"Shared memory stored: {memory_id} by {being_id}")
            return memory_id

        except Exception as e:
            logger.error(f"Error storing shared memory: {e}")
            return ""

    # ========================================================================
    # Jon's EXP Pool
    # ========================================================================

    def store_exp(
        self,
        exp_type: str,
        title: str,
        content: str,
        context: str,
        takeaway: str,
        when_to_apply: str,
        cost: str,
        tags: List[str] = None,
        share_with: List[str] = None
    ) -> str:
        """Store experience in Jon's EXP pool."""
        exp_id = f"exp_{uuid.uuid4().hex[:12]}"
        tags = tags or []
        share_with = share_with or ["all"]

        # Create rich metadata
        metadata = {
            "exp_id": exp_id,
            "type": exp_type,
            "title": title,
            "context": context,
            "takeaway": takeaway,
            "when_to_apply": when_to_apply,
            "cost": cost,
            "tags": tags,
            "share_with": share_with,
            "timestamp": datetime.now().isoformat()
        }

        # Store full content (concatenate for better search)
        full_content = f"{title}\n\n{content}\n\nTakeaway: {takeaway}\n\nWhen to apply: {when_to_apply}"

        try:
            self.collections["jon_exp"].add(
                documents=[full_content],
                metadatas=[metadata],
                ids=[exp_id]
            )

            logger.info(f"EXP stored: {exp_id} - {title}")
            return exp_id

        except Exception as e:
            logger.error(f"Error storing EXP: {e}")
            return ""

    def search_exp(
        self,
        query: str,
        exp_type: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search Jon's EXP pool."""
        try:
            # Build filter
            where = {"type": exp_type} if exp_type else None

            # Query
            results = self.collections["jon_exp"].query(
                query_texts=[query],
                n_results=limit,
                where=where
            )

            # Format results
            experiences = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    experiences.append({
                        "exp_id": results["ids"][0][i],
                        "content": doc,
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i] if "distances" in results else None
                    })

            logger.info(f"EXP search: '{query}' found {len(experiences)} results")
            return experiences

        except Exception as e:
            logger.error(f"Error searching EXP: {e}")
            return []

    def get_exp_by_id(self, exp_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific experience by ID."""
        try:
            result = self.collections["jon_exp"].get(ids=[exp_id])

            if result["documents"]:
                return {
                    "exp_id": exp_id,
                    "content": result["documents"][0],
                    "metadata": result["metadatas"][0]
                }
            return None

        except Exception as e:
            logger.error(f"Error getting EXP {exp_id}: {e}")
            return None

    # ========================================================================
    # Identity Management
    # ========================================================================

    def store_identity(self, being_id: str, identity_core: Dict[str, Any]) -> bool:
        """Store a being's identity in ChromaDB for semantic search."""
        try:
            # Create identity document
            identity_text = f"""
            Name: {identity_core.get('name', '')}
            Nature: {identity_core.get('nature', '')}
            Values: {', '.join(identity_core.get('values', []))}
            Ongoing Questions: {', '.join(identity_core.get('ongoing_questions', []))}
            Growth Edges: {', '.join(identity_core.get('growth_edges', []))}
            """

            metadata = {
                "being_id": being_id,
                "identity_core": identity_core,
                "updated_at": datetime.now().isoformat()
            }

            self.collections["beings_identity"].upsert(
                documents=[identity_text],
                metadatas=[metadata],
                ids=[being_id]
            )

            logger.info(f"Identity stored for {being_id}")
            return True

        except Exception as e:
            logger.error(f"Error storing identity for {being_id}: {e}")
            return False

    def get_identity(self, being_id: str) -> Optional[Dict[str, Any]]:
        """Get a being's identity."""
        try:
            result = self.collections["beings_identity"].get(ids=[being_id])

            if result["metadatas"]:
                return result["metadatas"][0].get("identity_core")
            return None

        except Exception as e:
            logger.error(f"Error getting identity for {being_id}: {e}")
            return None

    # ========================================================================
    # Stats
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        stats = {}

        for name, collection in self.collections.items():
            try:
                count = collection.count()
                stats[name] = count
            except:
                stats[name] = 0

        return stats
