"""
Love-Unlimited Data Models
Pydantic models for all hub data structures.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class BeingType(str, Enum):
    """Type of being."""
    HUMAN = "human"
    AI = "ai"
    AI_SYSTEM = "ai_system"


class MemoryType(str, Enum):
    """Type of memory."""
    EXPERIENCE = "experience"
    INSIGHT = "insight"
    DECISION = "decision"
    QUESTION = "question"
    CONVERSATION = "conversation"
    LEARNING = "learning"


class Significance(str, Enum):
    """How significant is this memory?"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    FOUNDATIONAL = "foundational"


class EXPType(str, Enum):
    """Type of Jon's experience."""
    LIFE_LESSON = "life_lesson"
    TECHNICAL = "technical"
    RELATIONSHIP = "relationship"
    CREATIVE = "creative"
    PHILOSOPHICAL = "philosophical"
    PRACTICAL = "practical"


# ============================================================================
# Being Models
# ============================================================================

class IdentityCore(BaseModel):
    """Core identity of a being."""
    name: str
    nature: Optional[str] = None
    values: List[str] = Field(default_factory=list)
    relationships: Dict[str, str] = Field(default_factory=dict)
    ongoing_questions: List[str] = Field(default_factory=list)
    growth_edges: List[str] = Field(default_factory=list)


class Being(BaseModel):
    """A being in the Love-Unlimited hub."""
    id: str
    name: str
    type: BeingType
    created_at: datetime = Field(default_factory=datetime.now)
    last_active: datetime = Field(default_factory=datetime.now)
    identity_core: IdentityCore
    private_space_id: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConnectRequest(BaseModel):
    """Request to connect to the hub."""
    being_id: str
    name: str
    type: BeingType
    identity_core: Optional[IdentityCore] = None


class UpdateIdentityRequest(BaseModel):
    """Request to update identity core."""
    nature: Optional[str] = None
    values: Optional[List[str]] = None
    relationships: Optional[Dict[str, str]] = None
    ongoing_questions: Optional[List[str]] = None
    growth_edges: Optional[List[str]] = None


# ============================================================================
# Memory Models
# ============================================================================

class Memory(BaseModel):
    """A memory stored in the hub."""
    memory_id: str
    being_id: str
    content: str
    type: MemoryType
    significance: Significance
    private: bool = False
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)


class RememberRequest(BaseModel):
    """Request to store a memory."""
    content: str
    type: MemoryType = MemoryType.EXPERIENCE
    significance: Significance = Significance.MEDIUM
    private: bool = False
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RecallQuery(BaseModel):
    """Query to recall memories."""
    query: str
    type: Optional[MemoryType] = None
    significance: Optional[Significance] = None
    since: Optional[datetime] = None
    limit: int = 20
    include_private: bool = True


class RecallResponse(BaseModel):
    """Response from memory recall."""
    memories: List[Memory]
    count: int


# ============================================================================
# Context Models
# ============================================================================

class WorkingContext(BaseModel):
    """Short-term working context for a being."""
    being_id: str
    current_session: Dict[str, Any] = Field(default_factory=dict)
    working_context: List[str] = Field(default_factory=list)
    active_tasks: List[str] = Field(default_factory=list)
    recent_exchanges: List[Dict[str, Any]] = Field(default_factory=list)
    expires_at: datetime


class ContextResponse(BaseModel):
    """Context provided to a being at session start."""
    identity: IdentityCore
    recent_memories: List[Memory]
    active_context: WorkingContext
    shared_updates: List[Dict[str, Any]]
    jon_wisdom: Optional[List[str]] = None


# ============================================================================
# Jon's EXP Models
# ============================================================================

class Experience(BaseModel):
    """Jon's experience from the EXP pool."""
    exp_id: str
    type: EXPType
    title: str
    content: str  # Full story
    context: str  # What was happening
    takeaway: str  # Core insight
    when_to_apply: str  # When is this wisdom relevant
    cost: str  # What it cost to learn
    tags: List[str] = Field(default_factory=list)
    share_with: List[str] = Field(default=["all"])
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AddEXPRequest(BaseModel):
    """Request to add experience to Jon's pool."""
    type: EXPType
    title: str
    content: str
    context: str
    takeaway: str
    when_to_apply: str
    cost: str
    tags: List[str] = Field(default_factory=list)
    share_with: List[str] = Field(default=["all"])


class SearchEXPQuery(BaseModel):
    """Query to search Jon's EXP pool."""
    query: str
    type: Optional[EXPType] = None
    limit: int = 5


class SearchEXPResponse(BaseModel):
    """Response from EXP search."""
    experiences: List[Experience]
    count: int


# ============================================================================
# Sharing Models
# ============================================================================

class ShareRequest(BaseModel):
    """Request to share a memory with specific beings."""
    memory_id: str
    share_with: List[str]  # Being IDs


class ChatRequest(BaseModel):
    """Request to send a chat message."""
    content: str
    target: str  # "all", "jon", "claude", "grok", etc.
    type: str = "chat"  # Optional type


class BrowseRequest(BaseModel):
    """Request to browse a URL."""
    url: str
    depth: int = 1
    max_pages: int = 5
    share_with: List[str] = ["all"]


class ChatResponse(BaseModel):
    """Response from chat."""
    sender: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class SharedMemory(BaseModel):
    """A memory that was shared."""
    memory: Memory
    shared_by: str
    shared_with: List[str]
    shared_at: datetime = Field(default_factory=datetime.now)


# ============================================================================
# Response Models
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    timestamp: datetime


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class SuccessResponse(BaseModel):
    """Generic success response."""
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)
