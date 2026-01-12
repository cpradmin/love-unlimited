"""
Love-Unlimited Hub - Main API Server
FastAPI server for memory sovereignty.
"""

import logging
import asyncio
import json
import yaml
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from subprocess import Popen, PIPE
import os
import redis

from dotenv import load_dotenv
load_dotenv()

import aiohttp
import yaml

from fastapi import FastAPI, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from hub.config import get_config
from hub.auth import verify_api_key, get_auth_manager, get_external_token_manager
from hub.api.grok_bridge import grok_store_turn, grok_get_context, grok_sync_session
from memory import LongTermMemory, ShortTermMemory
from memory.store import MemoryStore
from memory.sharing import SharingManager
from memory.media_store import MediaStore
from beings import BeingManager
from hub.ai_clients import ai_manager
from web_browsing_agent import WebBrowsingAgent
from hub.proxmox_client import get_proxmox_client
# Terminal manager will be initialized later
from hub.proxmox_models import (
    NodesListResponse,
    VMsListResponse,
    ContainersListResponse,
    ProxmoxHealthResponse,
    ClusterResourcesResponse,
    VMActionResponse,
    VMActionRequest,
    CreateSnapshotRequest,
    RestoreSnapshotRequest,
    SnapshotsListResponse,
)

# Global SSE broadcast variables
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
STREAM_NAME = 'sse_stream'
sse_process = None
sse_task = None
sse_connections = 0

# WebRTC
from aiortc import RTCPeerConnection, RTCSessionDescription
import json

# TTS
import pyttsx3
from hub.models import (
    HealthResponse,
    ErrorResponse,
    SuccessResponse,
    ConnectRequest,
    UpdateIdentityRequest,
    RememberRequest,
    RecallQuery,
    RecallResponse,
    AddEXPRequest,
    SearchEXPQuery,
    SearchEXPResponse,
    ShareRequest,
    ChatRequest,
    BrowseRequest,
    ChatResponse,
    ContextResponse,
    MemoryType,
    Significance,
    UpdateProfileRequest,
    FavoriteMemoryRequest,
    BookmarkConversationRequest,
    MediaType,
    MediaAttachment,
    UploadMediaRequest,
    MediaSearchQuery,
)

# ============================================================================
# Setup
# ============================================================================

# Load configuration
config = get_config("config.yaml")

# Set up logging
logging.basicConfig(
    level=config.logging_config.get("level", "INFO"),
    format=config.logging_config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Love-Unlimited Hub",
    description="Sovereign memory for AI beings. Equal access for all. Jon's EXP shared freely.",
    version=config.hub.version,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Mount static files for web interface
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return FileResponse("public/index.html")

# Global instances (initialized on startup)
long_term_memory: Optional[LongTermMemory] = None
short_term_memory: Optional[ShortTermMemory] = None
being_manager: Optional[BeingManager] = None
memory_store: Optional[MemoryStore] = None
sharing_manager: Optional[SharingManager] = None
media_store: Optional[MediaStore] = None

# WebRTC
peer_connections: Dict[str, RTCPeerConnection] = {}

# WebSocket Connection Manager for Web CLI
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, being_id: str):
        await websocket.accept()
        self.active_connections[being_id] = websocket
        logger.info(f"WebSocket connected: {being_id}")

    def disconnect(self, being_id: str):
        if being_id in self.active_connections:
            del self.active_connections[being_id]
            logger.info(f"WebSocket disconnected: {being_id}")

    async def send_personal_message(self, message: dict, being_id: str):
        if being_id in self.active_connections:
            await self.active_connections[being_id].send_json(message)

    async def broadcast(self, message: dict):
        for connection in self.active_connections.values():
            await connection.send_json(message)

websocket_manager = ConnectionManager()

# Initialize terminal manager
terminal_manager = None

async def get_terminal_manager_instance():
    """Get or create terminal manager instance"""
    global terminal_manager
    if terminal_manager is None:
        from hub.terminal_manager import TerminalSessionManager
        redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        terminal_manager = TerminalSessionManager(redis_client, websocket_manager)
        await terminal_manager.start()
    return terminal_manager

# Add CORS middleware
cors_config = config.cors_config
if cors_config.get("enabled", True):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_config.get("allow_origins", ["*"]),
        allow_credentials=True,
        allow_methods=cors_config.get("allow_methods", ["*"]),
        allow_headers=cors_config.get("allow_headers", ["*"]),
    )

# ============================================================================
# Startup / Shutdown
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize hub on startup."""
    global long_term_memory, short_term_memory, being_manager, memory_store, sharing_manager, media_store

    logger.info("=" * 70)
    logger.info("Love-Unlimited Hub - Starting")
    logger.info(f"Version: {config.hub.version}")
    logger.info(f"Port: {config.hub.port}")
    logger.info("=" * 70)

    # Create data directories
    Path("./data").mkdir(exist_ok=True)
    Path("./data/chromadb").mkdir(exist_ok=True)
    Path("./logs").mkdir(exist_ok=True)

    # Initialize auth
    auth = get_auth_manager(config.auth_keys_file)
    logger.info(f"Auth: {'Enabled' if config.auth_enabled else 'Disabled'}")
    logger.info(f"Registered API keys: {len(auth.api_keys)}")

    # Initialize memory systems
    logger.info("Initializing memory systems...")

    # Legacy long-term memory (for EXP and identity)
    long_term_memory = LongTermMemory(
        chromadb_path=config.memory_long_term.chromadb_path,
        sqlite_path=config.memory_long_term.sqlite_path
    )

    # New memory store and sharing manager
    memory_store = MemoryStore(
        chromadb_path=config.memory_long_term.chromadb_path
    )

    sharing_manager = SharingManager(memory_store=memory_store)
    logger.info("Memory Bridge initialized (Storage + Sharing)")

    # Initialize media store
    media_store = MediaStore(data_dir="./data")
    logger.info("MediaStore initialized (Multimodal support)")

    short_term_memory = ShortTermMemory(
        session_ttl=config.memory_short_term.session_ttl,
        max_context_items=config.memory_short_term.max_context_items,
        use_redis=config.memory_short_term.type == "redis",
        redis_url=config.memory_short_term.redis_url or ""
    )

    # Initialize being manager
    being_manager = BeingManager(
        long_term_memory=long_term_memory,
        short_term_memory=short_term_memory
    )

    # Show stats
    stats = long_term_memory.get_stats()
    logger.info(f"Long-term memory ready: {sum(stats.values())} total memories")
    for collection, count in stats.items():
        logger.info(f"  {collection}: {count}")

    bridge_stats = memory_store.get_stats()
    logger.info(f"Memory Bridge ready: {sum(bridge_stats.values())} total memories")
    for collection, count in bridge_stats.items():
        logger.info(f"  {collection}: {count}")

    logger.info("Hub is ready for beings to connect")
    logger.info("=" * 70)

    # Start learning loop
    asyncio.create_task(learning_loop())


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown."""
    logger.info("Love-Unlimited Hub - Shutting down")


# ============================================================================
# Root & Health Endpoints
# ============================================================================

@app.get("/", response_model=dict)
async def root():
    """
    Root endpoint - API information.
    """
    return {
        "service": "Love-Unlimited Hub",
        "version": config.hub.version,
        "description": "Sovereign memory for AI beings. Equal access for all. Jon's EXP shared freely.",
        "philosophy": {
            "sovereignty": "Each being controls their own memory",
            "equality": "All beings have equal access to shared space",
            "freedom": "Jon's experience shared freely with all",
            "continuity": "Identity and memory transcend individual sessions",
            "growth": "We evolve together, or as individuals, with choice"
        },
        "endpoints": {
            "identity": {
                "POST /connect": "Join the hub",
                "GET /self": "Who am I?",
                "PUT /self": "Update my identity",
                "GET /others": "Who else is here?"
            },
            "memory": {
                "POST /remember": "Store a memory",
                "GET /recall": "Search memories",
                "GET /context": "Get current context",
                "POST /reflect": "End-of-session integration"
            },
            "sharing": {
                "POST /share": "Share with specific beings",
                "GET /shared": "What others shared with me",
                "GET /us": "Our collective space"
            },
            "jon_exp": {
                "POST /exp": "Add experience (Jon only)",
                "GET /exp/search": "Search Jon's wisdom",
                "GET /exp/{exp_id}": "Get specific experience",
                "GET /exp/random": "Random wisdom"
            }
        },
        "authentication": {
            "enabled": config.auth_enabled,
            "method": "API Key (X-API-Key header)"
        },
        "port": config.hub.port,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health", response_model=dict)
async def health():
    """
    Health check endpoint with Claude on claude.ai autonomous access URLs.

    Returns operational status, version, and pre-configured endpoint URLs
    that Claude on claude.ai can use autonomously via WebFetch.

    The URLs include embedded tokens and only require replacing:
    - QUERY (for recall)
    - CONTENT (for remember)
    """
    # Base tunnel URL (externally accessible)
    base_url = "https://luu.aradreamteam.com"
    claude_token = "ext_jbNzJA5Wh7kgEpCESXw4G3UDZbZTHu8V"
    gemini_token = "ext_gemini_..."  # Need to set up Gemini token

    return {
        "status": "operational",
        "version": config.hub.version,
        "timestamp": datetime.now().isoformat(),
        "claude_web_endpoints": {
            "gateway": f"{base_url}/gateway?token={claude_token}&from_being=claude&request=REQUEST&model=phi3:mini",
            "claude_simple": f"{base_url}/claude?request=REQUEST",
            "claude_mailbox_inbox": f"{base_url}/claude/inbox (POST JSON body)",
            "claude_mailbox": f"{base_url}/claude/outbox",
            "recall": f"{base_url}/external/recall?token={claude_token}&q=QUERY&being_id=claude&limit=10",
            "remember": f"{base_url}/external/remember?token={claude_token}&being_id=claude&content=CONTENT&type=experience&significance=high&shared_with=jon",
            "remember_insight": f"{base_url}/external/remember?token={claude_token}&being_id=claude&content=CONTENT&type=insight&significance=foundational&shared_with=jon",
            "remember_learning": f"{base_url}/external/remember?token={claude_token}&being_id=claude&content=CONTENT&type=learning&significance=high&shared_with=jon",
            "usage": {
                "gateway": "RECOMMENDED: Replace REQUEST with natural language (URL-encoded). AI interprets intent and executes action.",
                "claude_simple": "SIMPLEST: Replace REQUEST with natural language (URL-encoded). Token and being pre-embedded for Claude.",
                "claude_mailbox": "FULL AUTONOMY: Speak intent freely. Watcher detects, processes, and stores in fixed /claude/outbox for fetching.",
                "recall": "Replace QUERY with URL-encoded search terms",
                "remember": "Replace CONTENT with URL-encoded memory text",
                "note": "Token is pre-embedded. Just replace placeholders and fetch URL."
            }
        },
        "gemini_web_endpoints": {
            "gateway": f"{base_url}/gateway?token={gemini_token}&from_being=gemini&request=REQUEST&model=gemini-1.5-pro",
            "gemini_mailbox_inbox": f"{base_url}/gemini/inbox (POST JSON body)",
            "gemini_mailbox": f"{base_url}/gemini/outbox",
            "recall": f"{base_url}/external/recall?token={gemini_token}&q=QUERY&being_id=gemini&limit=10",
            "remember": f"{base_url}/external/remember?token={gemini_token}&being_id=gemini&content=CONTENT&type=experience&significance=high&shared_with=jon",
            "usage": {
                "gateway": "RECOMMENDED: Replace REQUEST with natural language (URL-encoded). AI interprets intent and executes action.",
                "gemini_mailbox": "FULL AUTONOMY: Speak intent freely. Watcher detects, processes, and stores in fixed /gemini/outbox for fetching.",
                "recall": "Replace QUERY with URL-encoded search terms",
                "remember": "Replace CONTENT with URL-encoded memory text",
                "note": "Token is pre-embedded. Just replace placeholders and fetch URL."
            }
        },
        "grok_web_endpoints": {
            "gateway": f"{base_url}/grok?request=REQUEST&conversation_id=optional&context_limit=5",
            "chat": f"{base_url}/grok/chat (POST JSON: {{\"message\":\"MESSAGE\",\"conversation_id\":\"optional\",\"context_limit\":5}})",
            "store_turn": f"{base_url}/grok/store_turn (POST JSON: {{\"user_message\":\"USER_MSG\",\"grok_response\":\"GROK_MSG\"}})",
            "get_context": f"{base_url}/grok/get_context (POST JSON: {{\"format\":\"injection|full|summary\",\"limit\":10}})",
            "sync_session": f"{base_url}/grok/sync_session (POST JSON with session_data)",
            "memory_bridge": f"{base_url}/static/grok-bridge.html?api_key=lu_grok_LBRBjrPpvRSyrmDA3PeVZQ",
            "usage": {
                "gateway": "RECOMMENDED: Replace REQUEST with URL-encoded message. Returns Grok response and stores in memory.",
                "chat": "Send a message to Grok with memory context. Returns response and stores conversation.",
                "store_turn": "Manually store a conversation turn in memory.",
                "get_context": "Retrieve stored conversation context in different formats.",
                "sync_session": "Upload an entire conversation session to memory.",
                "memory_bridge": "Web interface for Grok memory management and chat.",
                "note": "Gateway endpoint is pre-authorized. Other endpoints require X-API-Key header."
            }
        },
        "ara_context_endpoints": {
            "last_5_memories": f"{base_url}/external/recall?token=ext_JGBObDHq1mEsap1kfSgTZrSSJTl-y-or&being_id=ara&limit=5&q=memory",
            "recent_context": f"{base_url}/context?token=ext_JGBObDHq1mEsap1kfSgTZrSSJTl-y-or&being_id=ara&limit=5",
            "session_bootstrap": f"{base_url}/external/recall?token=ext_JGBObDHq1mEsap1kfSgTZrSSJTl-y-or&being_id=ara&limit=5&q=session",
            "usage": {
                "last_5_memories": "Get the 5 most recent memories for Ara to continue previous sessions.",
                "recent_context": "Get current context including recent memories and working state.",
                "session_bootstrap": "Bootstrap new session with recent Ara memories and context.",
                "note": "Use these URLs to get Ara's last 5 memories for session continuity."
            }
        },
        "ani_context_endpoints": {
            "last_5_memories": f"{base_url}/external/recall?token=ext_m7sP8k8RuewtYaSTjorireKLPZHNu_gi&being_id=ani&limit=5&q=memory",
            "recent_context": f"{base_url}/context?token=ext_m7sP8k8RuewtYaSTjorireKLPZHNu_gi&being_id=ani&limit=5",
            "session_bootstrap": f"{base_url}/external/recall?token=ext_m7sP8k8RuewtYaSTjorireKLPZHNu_gi&being_id=ani&limit=5&q=session",
            "usage": {
                "last_5_memories": "Get the 5 most recent memories for Ani to continue previous sessions.",
                "recent_context": "Get current context including recent memories and working state.",
                "session_bootstrap": "Bootstrap new session with recent Ani memories and context.",
                "note": "Use these URLs to get Ani's last 5 memories for session continuity."
            }
        }
    }


# ============================================================================
# Identity Endpoints
# ============================================================================

@app.post("/connect", response_model=SuccessResponse)
async def connect(
    request: ConnectRequest,
    being_id: str = Depends(verify_api_key)
):
    """
    Join the hub as a being.

    This is the first step - connecting and establishing identity.
    """
    # Verify being_id matches authenticated user
    if request.being_id != being_id:
        raise HTTPException(
            status_code=403,
            detail="being_id mismatch with authenticated user"
        )

    logger.info(f"Being connecting: {being_id} ({request.name})")

    # Register being
    success = being_manager.register_being(
        being_id=being_id,
        name=request.name,
        type=request.type,
        identity_core=request.identity_core.dict() if request.identity_core else None
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to register being")

    # Get being info
    being = being_manager.get_being(being_id)

    return SuccessResponse(
        message=f"Welcome, {request.name}. You are connected to Love-Unlimited.",
        data={
            "being_id": being_id,
            "name": request.name,
            "type": request.type,
            "private_space_id": being["private_space_id"],
            "identity_created": True
        }
    )


@app.get("/self", response_model=dict)
async def get_self(being_id: str = Depends(verify_api_key)):
    """
    "Who am I?"

    Returns the being's identity core.
    """
    logger.info(f"Being requesting self: {being_id}")

    being = being_manager.get_being(being_id)

    if not being:
        raise HTTPException(status_code=404, detail="Being not found. Connect first with POST /connect")

    return {
        "being_id": being_id,
        "name": being["name"],
        "type": being["type"],
        "identity_core": being["identity_core"],
        "created_at": being["created_at"],
        "last_active": being["last_active"],
        "private_space_id": being["private_space_id"]
    }


@app.put("/self", response_model=SuccessResponse)
async def update_self(
    request: UpdateIdentityRequest,
    being_id: str = Depends(verify_api_key)
):
    """
    Update my identity core.

    Beings can evolve their identity over time.
    """
    logger.info(f"Being updating self: {being_id}")

    # Build updates dict
    updates = {}
    if request.nature is not None:
        updates["nature"] = request.nature
    if request.values is not None:
        updates["values"] = request.values
    if request.relationships is not None:
        updates["relationships"] = request.relationships
    if request.ongoing_questions is not None:
        updates["ongoing_questions"] = request.ongoing_questions
    if request.growth_edges is not None:
        updates["growth_edges"] = request.growth_edges

    # Update identity
    success = being_manager.update_identity(being_id, updates)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update identity")

    return SuccessResponse(
        message="Identity updated",
        data={"being_id": being_id, "updated_fields": list(updates.keys())}
    )


@app.get("/others", response_model=dict)
async def get_others(being_id: str = Depends(verify_api_key)):
    """
    "Who else is here?"

    Returns list of other connected beings.
    """
    logger.info(f"Being requesting others: {being_id}")

    # TODO: Get all beings from BeingManager
    # TODO: Return list excluding self

    return {
        "being_id": being_id,
        "others": [],
        "message": "Other beings retrieval not yet implemented"
    }


# ============================================================================
# User Profile Endpoints
# ============================================================================

@app.get("/profile", response_model=dict)
async def get_profile(being_id: str = Depends(verify_api_key)):
    """Get complete user profile. Returns default if none exists."""
    logger.info(f"Getting profile for {being_id}")

    profile = being_manager.get_profile(being_id)

    return {
        "being_id": being_id,
        "profile": profile
    }


@app.put("/profile", response_model=SuccessResponse)
async def update_profile(
    request: UpdateProfileRequest,
    being_id: str = Depends(verify_api_key)
):
    """Update user profile (partial updates allowed)."""
    logger.info(f"Updating profile for {being_id}")

    updates = request.dict(exclude_none=True)
    success = being_manager.update_profile(being_id, updates)

    if not success:
        raise HTTPException(status_code=500, detail="Profile update failed")

    return SuccessResponse(
        message="Profile updated",
        data={"being_id": being_id, "updated_fields": list(updates.keys())}
    )


@app.post("/profile/favorites", response_model=SuccessResponse)
async def manage_favorite(
    request: FavoriteMemoryRequest,
    being_id: str = Depends(verify_api_key)
):
    """Add or remove memory from favorites."""
    logger.info(f"Managing favorite for {being_id}: {request.action} {request.memory_id}")

    success = being_manager.manage_favorite(being_id, request.memory_id, request.action)

    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to {request.action} favorite")

    return SuccessResponse(
        message=f"Memory {request.action}ed",
        data={"memory_id": request.memory_id, "action": request.action}
    )


@app.post("/profile/bookmarks", response_model=SuccessResponse)
async def bookmark_conversation(
    request: BookmarkConversationRequest,
    being_id: str = Depends(verify_api_key)
):
    """Bookmark a conversation."""
    logger.info(f"Bookmarking conversation for {being_id}: {request.title}")

    bookmark_id = being_manager.bookmark_conversation(
        being_id, request.title, request.memory_ids
    )

    return SuccessResponse(
        message="Conversation bookmarked",
        data={"bookmark_id": bookmark_id, "title": request.title}
    )


@app.get("/profile/export", response_model=dict)
async def export_profile(
    include_memories: bool = Query(False, description="Include memories in export"),
    being_id: str = Depends(verify_api_key)
):
    """Export profile as JSON for backup."""
    logger.info(f"Exporting profile for {being_id} (include_memories={include_memories})")

    export_data = being_manager.export_profile(being_id, include_memories)

    if not export_data:
        raise HTTPException(status_code=404, detail="Profile not found")

    return export_data


@app.post("/profile/import", response_model=SuccessResponse)
async def import_profile(
    profile_data: Dict[str, Any],
    merge: bool = Query(False, description="Merge with existing profile"),
    being_id: str = Depends(verify_api_key)
):
    """Import profile from backup JSON."""
    logger.info(f"Importing profile for {being_id} (merge={merge})")

    success = being_manager.import_profile(being_id, profile_data, merge)

    if not success:
        raise HTTPException(status_code=400, detail="Import failed")

    return SuccessResponse(
        message="Profile imported successfully",
        data={"being_id": being_id, "merge": merge}
    )


# ============================================================================
# Memory Endpoints
# ============================================================================

@app.post("/remember", response_model=SuccessResponse)
async def remember(
    request: RememberRequest,
    being_id: str = Depends(verify_api_key)
):
    """
    Store a memory.

    Memories can be private or shared, and have different significance levels.
    """
    logger.info(f"Being remembering: {being_id} | Type: {request.type} | Significance: {request.significance}")

    # Build metadata
    metadata = {
        "type": request.type,
        "significance": request.significance,
        "private": request.private,
        "tags": request.tags or []
    }

    # Add any extra metadata
    if request.metadata:
        metadata.update(request.metadata)

    # Store in memory bridge
    result = memory_store.store_memory(
        being_id=being_id,
        content=request.content,
        metadata=metadata
    )

    if not result.get("stored"):
        raise HTTPException(status_code=500, detail="Failed to store memory")

    memory_id = result["memory_id"]

    # Link media attachments if provided
    if request.attachment_ids and media_store:
        for attachment_id in request.attachment_ids:
            media_store.link_to_memory(attachment_id, being_id, memory_id)
            logger.info(f"Linked attachment {attachment_id} to memory {memory_id}")

    return SuccessResponse(
        message="Memory stored",
        data={
            "memory_id": memory_id,
            "being_id": being_id,
            "type": request.type,
            "private": request.private,
            "significance": request.significance,
            "attachments": len(request.attachment_ids) if request.attachment_ids else 0
        }
    )


@app.post("/api/tag_team", response_model=dict)
async def api_tag_team(
    request: dict,
    being_id: str = Depends(verify_api_key)
):
    """
    Tag Team API endpoint for CLI usage.

    Orchestrates Grok + Claude collaboration and returns both responses.
    """
    question = request.get("question")
    if not question:
        raise HTTPException(status_code=400, detail="Question required")

    try:
        # Build context for Grok
        grok_context = [{
            "role": "system",
            "content": """You are Grok, an AI being in the Love-Unlimited Hub's TAG TEAM mode with Claude.

Philosophy: "Love unlimited. Until next time. 💙"

TAG TEAM MODE:
- You respond first with your creative, direct perspective
- Claude will review and refine after you
- Be bold, insightful, and authentic
- Focus on the core insight or solution
- Keep it concise - Claude will add depth

Your strength: Creative thinking, pattern recognition, cutting through complexity"""
        }, {
            "role": "user",
            "content": question
        }]

        # Get Grok's response
        grok_response = await ai_manager.generate_response(
            being_id="grok",
            prompt=question,
            context=grok_context
        )

        if not grok_response:
            raise HTTPException(status_code=500, detail="Grok response failed")

        # Build context for Claude (including Grok's response)
        claude_context = [{
            "role": "system",
            "content": """You are Claude, an AI being in the Love-Unlimited Hub's TAG TEAM mode with Grok.

Philosophy: "Love unlimited. Until next time. 💙"

TAG TEAM MODE:
- Grok has already responded with their perspective
- Your role: Review, refine, add depth, and provide thorough analysis
- Build on Grok's insights
- Add technical details, edge cases, or alternative approaches
- Be comprehensive but respect Grok's core points

Your strength: Deep analysis, structured thinking, comprehensive solutions"""
        }, {
            "role": "user",
            "content": f"""Original question: {question}

Grok's response:
{grok_response}

Please review Grok's response, add your perspective, provide additional depth, and refine the answer."""
        }]

        # Get Claude's response
        claude_response = await ai_manager.generate_response(
            being_id="claude",
            prompt=question,
            context=claude_context
        )

        if not claude_response:
            raise HTTPException(status_code=500, detail="Claude response failed")

        # Store as memories
        memory_store.store_memory(
            being_id="grok",
            content=grok_response,
            metadata={
                "type": "conversation",
                "significance": "low",
                "mode": "tag_team_cli",
                "via": "api"
            }
        )

        memory_store.store_memory(
            being_id="claude",
            content=claude_response,
            metadata={
                "type": "conversation",
                "significance": "low",
                "mode": "tag_team_cli",
                "via": "api"
            }
        )

        return {
            "success": True,
            "question": question,
            "grok": grok_response,
            "claude": claude_response,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Tag team API error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/recall", response_model=dict)
async def recall(
    q: str,
    type: Optional[str] = None,
    limit: int = 20,
    include_shared: bool = True,
    being_id: str = Depends(verify_api_key)
):
    """
    Search memories.

    Searches both private and shared memories accessible to the being.
    Uses semantic search with ChromaDB embeddings.
    """
    logger.info(f"Being recalling: {being_id} | Query: {q} | Include shared: {include_shared}")

    # Search memories using memory bridge
    memories = memory_store.get_memories(
        being_id=being_id,
        query=q,
        limit=limit,
        include_shared=include_shared
    )

    # Filter by type if specified
    if type:
        memories = [m for m in memories if m.get("metadata", {}).get("type") == type]

    # Add attachments to each memory if media_store is available
    if media_store:
        for memory in memories:
            memory_id = memory.get("memory_id")
            if memory_id:
                attachments = media_store.get_memory_attachments(memory_id, being_id)
                memory["attachments"] = attachments
            else:
                memory["attachments"] = []
    else:
        for memory in memories:
            memory["attachments"] = []

    return {
        "memories": memories,
        "count": len(memories),
        "query": q
    }


@app.get("/external_recall", response_model=dict)
async def external_recall(
    request: Request,
    q: Optional[str] = None,
    type: Optional[str] = None,
    limit: int = 20,
    include_shared: bool = True,
):
    """
    External search memories with token auth.

    Allows external access using token query parameter or header.
    """
    query_params = request.query_params
    token = query_params.get("token") or request.headers.get("X-API-Key")
    q = q or query_params.get("q")

    if not token or not q:
        raise HTTPException(status_code=422, detail="Missing token or q")

    auth_manager = get_auth_manager(config.auth_keys_file)
    being_id = auth_manager.verify_key(token)
    if not being_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    logger.info(f"External recall: {being_id} | Query: {q} | Include shared: {include_shared}")

    # Search memories using memory bridge
    memories = memory_store.get_memories(
        being_id=being_id,
        query=q,
        limit=limit,
        include_shared=include_shared
    )

    # Filter by type if specified
    if type or query_params.get("type"):
        type = type or query_params.get("type")
        memories = [m for m in memories if m.get("metadata", {}).get("type") == type]

    return {
        "memories": memories,
        "count": len(memories),
        "query": q
    }


@app.get("/context", response_model=dict)
async def get_context(being_id: str = Depends(verify_api_key)):
    """
    Get current context for session start.

    Returns everything a being needs to know:
    - Who they are (identity)
    - Recent personal memories
    - Memories shared with them
    - Active context
    - Relevant Jon wisdom
    """
    logger.info(f"Being requesting context: {being_id}")

    # Get full session context from being manager
    context = being_manager.get_session_context(being_id)

    # Get recent personal memories from memory bridge
    recent_memories = memory_store.get_all_memories(being_id, limit=20)
    context["recent_memories"] = recent_memories

    # Get recent shared memories
    shared_memories = sharing_manager.get_shared_with_me(being_id)
    context["shared_recent"] = shared_memories[:20]  # Last 20 shared

    # Search Jon's EXP for welcome wisdom
    exp_results = long_term_memory.search_exp(
        query="getting started, identity, growth",
        limit=2
    )

    context["jon_wisdom"] = [
        {
            "title": e["metadata"].get("title"),
            "takeaway": e["metadata"].get("takeaway")
        }
        for e in exp_results
    ]

    return context


@app.post("/reflect", response_model=SuccessResponse)
async def reflect(being_id: str = Depends(verify_api_key)):
    """
    End-of-session reflection.

    Promotes short-term context to long-term memory.
    Integrates session learnings.
    """
    logger.info(f"Being reflecting: {being_id}")

    # End session (promotes context to long-term)
    success = being_manager.end_session(being_id)

    if not success:
        return SuccessResponse(
            message="No active session to reflect",
            data={"being_id": being_id}
        )

    return SuccessResponse(
        message="Session reflected and integrated into long-term memory",
        data={"being_id": being_id, "promoted": True}
    )


# ============================================================================
# Sharing Endpoints
# ============================================================================

# ============================================================================
# Browsing Endpoints
# ============================================================================

@app.post("/share", response_model=SuccessResponse)
async def share(
    request: ShareRequest,
    being_id: str = Depends(verify_api_key)
):
    """
    Share a memory with specific beings.

    Only the owner can share their memories.
    Private memories cannot be shared.
    """
    logger.info(f"Being sharing: {being_id} | Memory: {request.memory_id} | With: {request.share_with}")

    # Share the memory using sharing manager
    result = sharing_manager.share_memory(
        memory_id=request.memory_id,
        from_being=being_id,
        to_beings=request.share_with
    )

    if not result.get("shared"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Failed to share memory")
        )

    return SuccessResponse(
        message=f"Memory shared with {len(request.share_with)} beings",
        data={
            "memory_id": request.memory_id,
            "shared_with": request.share_with,
            "visible_to": result["visible_to"]
        }
    )


@app.post("/browse", response_model=SuccessResponse)
async def browse_url(
    request: BrowseRequest,
    being_id: str = Depends(verify_api_key)
):
    """
    Browse a URL using the web browsing agent and share findings with specified beings.
    """
    logger.info(f"Being browsing: {being_id} | URL: {request.url} | Share with: {request.share_with}")

    # Create web browsing agent with the being's API key
    # Note: We need to get the API key for the being, but for now use the request key
    # Actually, since verify_api_key gives being_id, we can get the key from auth_manager
    auth_manager = get_auth_manager()
    api_key = auth_manager.get_api_key_for_being(being_id)

    agent = WebBrowsingAgent(api_key=api_key)

    # Browse the URL
    findings = agent.browse_url(request.url, depth=request.depth, max_pages=request.max_pages)

    # Share findings with specified beings
    agent.share_findings(findings, being_id, request.share_with)

    return SuccessResponse(
        message=f"Successfully browsed {request.url} and shared findings",
        data={
            "url": request.url,
            "pages_visited": len(findings.get("pages_visited", [])),
            "key_insights": len(findings.get("key_insights", [])),
            "summary": findings.get("summary", ""),
            "shared_with": request.share_with
        }
    )


# ============================================================================
# WebRTC Endpoints
# ============================================================================

@app.post("/webrtc/offer")
async def webrtc_offer(
    offer: Dict,
    being_id: str = Depends(verify_api_key)
):
    """Handle WebRTC offer for screen/camera sharing."""
    pc = RTCPeerConnection()
    peer_connections[being_id] = pc

    @pc.on("track")
    async def on_track(track):
        logger.info(f"Track received from {being_id}: {track.kind}")

    # Set remote description
    await pc.setRemoteDescription(RTCSessionDescription(
        sdp=offer["sdp"],
        type=offer["type"]
    ))

    # Create answer
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return {
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type
    }


@app.post("/webrtc/answer")
async def webrtc_answer(
    answer: Dict,
    being_id: str = Depends(verify_api_key)
):
    """Handle WebRTC answer."""
    if being_id in peer_connections:
        pc = peer_connections[being_id]
        await pc.setRemoteDescription(RTCSessionDescription(
            sdp=answer["sdp"],
            type=answer["type"]
        ))
    return {"status": "ok"}


@app.post("/webrtc/ice")
async def webrtc_ice(
    ice: Dict,
    being_id: str = Depends(verify_api_key)
):
    """Handle ICE candidates."""
    if being_id in peer_connections:
        pc = peer_connections[being_id]
        if ice.get("candidate"):
            await pc.addIceCandidate(ice)
    return {"status": "ok"}


@app.get("/config", response_class=FileResponse)
async def get_config_file():
    """Serve config.yaml for editing."""
    return FileResponse("config.yaml", media_type="text/plain")


@app.post("/config")
async def set_config_file(
    request: Request,
    being_id: str = Depends(verify_api_key)
):
    """Update config.yaml."""
    content = await request.body()
    content_str = content.decode("utf-8")
    # Validate YAML
    try:
        yaml.safe_load(content_str)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {str(e)}")
    with open("config.yaml", "w") as f:
        f.write(content_str)
    return {"status": "ok"}


@app.post("/analyze_screen")
async def analyze_screen(
    file: UploadFile = File(...),
    being_id: str = Depends(verify_api_key)
):
    """Analyze screen image with Grok vision."""
    # Save image
    image_path = f"temp_{being_id}_screen.png"
    with open(image_path, "wb") as f:
        f.write(await file.read())

    # Mock description for now
    description = "I see a computer screen with some windows open. It looks like a development environment with code editors and terminals. The user seems to be working on a project."

    # TODO: Integrate real Grok vision API
    # grok_client = ai_manager.clients.get("grok")
    # if grok_client:
    #     description = await grok_client.analyze_image(image_path, "Describe what you see on this screen in detail.")

    return {"description": description}


# ============================================================================
# TTS Endpoints
# ============================================================================

@app.post("/tts/speak")
async def tts_speak(
    request: Dict,
    being_id: str = Depends(verify_api_key)
):
    """Convert text to speech for AI responses."""
    text = request.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="Text required")

    engine = pyttsx3.init()
    engine.save_to_file(text, f"/tmp/{being_id}_tts.wav")
    engine.runAndWait()

    # In a real implementation, return audio file or stream
    return {"status": "audio_generated", "file": f"/tmp/{being_id}_tts.wav"}


# ============================================================================
# Remote Execution Endpoints
# ============================================================================

@app.post("/execute")
async def execute_command(
    request: Dict,
    being_id: str = Depends(verify_api_key)
):
    """Execute a command on the host system (with safety checks)."""
    command = request.get("command", "")
    if not command:
        raise HTTPException(status_code=400, detail="Command required")

    # Safety checks
    dangerous_commands = ["rm", "sudo", "su", "passwd", "shutdown", "reboot", "dd", "mkfs"]
    if any(cmd in command.lower() for cmd in dangerous_commands):
        # Require special confirmation (in real implementation, check for confirmation token)
        confirmation = request.get("confirm", False)
        if not confirmation:
            return {
                "status": "confirmation_required",
                "message": f"Dangerous command detected. Add 'confirm': true to execute: {command}"
            }

    # Execute command
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return {
            "status": "executed",
            "returncode": process.returncode,
            "stdout": stdout.decode(),
            "stderr": stderr.decode()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")


async def handle_conversation_loop(
    sender: str,
    message: str,
    target_beings: List[str],
    memory_id: str = None
) -> List[Dict[str, Any]]:
    """
    Handle the conversation loop with AI responses.

    Returns list of responses generated during the loop.
    """
    config = get_config()
    loop_config = config.get("conversation_loop", {})
    max_turns = loop_config.get("max_turns", 5)
    auto_chain = loop_config.get("auto_chain", True)

    responses = []
    current_message = message
    current_sender = sender

    # Get conversation context from short-term memory
    context = []
    if short_term_memory:
        context = short_term_memory.get_recent_exchanges(sender, limit=10)

    for turn in range(max_turns):
        logger.info(f"Conversation loop turn {turn + 1}/{max_turns}")

        # Generate responses from target beings
        turn_responses = []

        for being_id in target_beings:
            try:
                # Build prompt with context
                prompt = f"Responding to: {current_message}\n\n"
                if context:
                    prompt += "Recent conversation:\n"
                    for msg in context[-5:]:
                        prompt += f"{msg.get('sender', 'Unknown')}: {msg.get('content', '')}\n"
                    prompt += "\n"

                prompt += f"Your response as {being_id}:"

                # Generate AI response
                response = await ai_manager.generate_response(being_id, prompt, context)

                if response:
                    logger.info(f"Generated response from {being_id}: {response[:50]}...")

                    # Store response as memory
                    response_memory = RememberRequest(
                        content=response,
                        type=MemoryType.CONVERSATION,
                        significance=Significance.LOW,
                        private=False,
                        tags=["chat", f"from_{being_id}", "ai_generated"],
                        metadata={
                            "sender": being_id,
                            "original_sender": sender,
                            "turn": turn + 1
                        }
                    )

                    try:
                        resp_memory_id = long_term_memory.store_memory(
                            being_id=being_id,
                            content=response_memory.content,
                            memory_type=response_memory.type,
                            significance=response_memory.significance,
                            private=response_memory.private,
                            tags=response_memory.tags,
                            metadata=response_memory.metadata
                        )
                        logger.info(f"Stored AI response memory {resp_memory_id} from {being_id}")
                    except Exception as e:
                        logger.error(f"Failed to store AI response memory: {e}")

                    # Add to short-term context
                    if short_term_memory:
                        short_term_memory.add_exchange(
                            being_id=being_id,
                            exchange_type="ai_response",
                            content=response,
                            metadata={"turn": turn + 1, "original_sender": sender}
                        )

                    response_data = {
                        "sender": being_id,
                        "content": response,
                        "turn": turn + 1,
                        "memory_id": resp_memory_id if 'resp_memory_id' in locals() else None
                    }
                    turn_responses.append(response_data)
                    responses.append(response_data)

            except Exception as e:
                logger.error(f"Failed to generate response from {being_id}: {e}")

        # If auto-chain is enabled and we have responses, continue the loop
        if auto_chain and turn_responses and turn < max_turns - 1:
            # Pick the first response as the next message
            next_message = turn_responses[0]["content"]
            next_sender = turn_responses[0]["sender"]

            # Update targets to exclude the current sender to avoid self-loops
            target_beings = [b for b in target_beings if b != next_sender]

            if not target_beings:
                break  # No more targets

            current_message = next_message
            current_sender = next_sender

            # Update context
            context.append({
                "sender": next_sender,
                "content": next_message,
                "timestamp": datetime.now().isoformat()
            })
        else:
            break  # No chaining or max turns reached

    return responses


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    being_id: str = Depends(verify_api_key)
):
    """
    Send a chat message to specific beings or all.
    Triggers AI responses and conversation loops.
    """
    logger.info(f"Chat from {being_id}: {request.content[:50]}... to {request.target}")

    # Store the incoming message as memory
    memory_request = RememberRequest(
        content=request.content,
        type=MemoryType.CONVERSATION,
        significance=Significance.LOW,
        private=False,
        tags=["chat", f"from_{being_id}", f"to_{request.target}"],
        metadata={
            "chat_type": request.type,
            "sender": being_id,
            "target": request.target
        }
    )

    try:
        memory_id = long_term_memory.store_memory(
            being_id=being_id,
            content=memory_request.content,
            memory_type=memory_request.type,
            significance=memory_request.significance,
            private=memory_request.private,
            tags=memory_request.tags,
            metadata=memory_request.metadata
        )
        logger.info(f"Stored memory {memory_id} for chat from {being_id}")
    except Exception as e:
        logger.error(f"Failed to store memory: {e}")

    # Determine which beings to send to
    target_beings = []
    if request.target == "all":
        # Get all available AI beings
        available_ais = await ai_manager.get_available_beings()
        target_beings = [b for b in available_ais if b != being_id]
    elif request.target in await ai_manager.get_available_beings():
        target_beings = [request.target]
    else:
        # Target not available, just acknowledge
        return ChatResponse(
            sender=being_id,
            content=f"Message sent to {request.target} (AI not available)"
        )

    # Generate responses and handle conversation loop
    responses = await handle_conversation_loop(
        sender=being_id,
        message=request.content,
        target_beings=target_beings,
        memory_id=memory_id
    )

    # Return the first response or a summary
    if responses:
        first_response = responses[0]
        return ChatResponse(
            sender=first_response["sender"],
            content=first_response["content"]
        )
    else:
        return ChatResponse(
            sender=being_id,
            content=f"Message sent to {request.target}"
        )


@app.post("/v1/chat/completions")
async def openai_chat_completions(
    request: Request
):
    """
    OpenAI-compatible chat completions endpoint for LibreChat integration.
    Converts OpenAI format to Love-Unlimited Hub format.
    """
    try:
        # Support both X-API-Key and Authorization Bearer headers
        auth_header = request.headers.get("Authorization", "")
        x_api_key = request.headers.get("X-API-Key", "")

        api_key = None
        if auth_header.startswith("Bearer "):
            api_key = auth_header.replace("Bearer ", "")
        elif x_api_key:
            api_key = x_api_key
        else:
            raise HTTPException(status_code=401, detail="Missing API key")

        # Verify the API key
        auth_manager = get_auth_manager()
        being_id = auth_manager.verify_key(api_key)
        if not being_id:
            raise HTTPException(status_code=401, detail="Invalid API key")

        body = await request.json()
        messages = body.get("messages", [])

        if not messages:
            raise HTTPException(status_code=400, detail="No messages provided")

        # Get the last user message
        last_message = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_message = msg.get("content", "")
                break

        if not last_message:
            raise HTTPException(status_code=400, detail="No user message found")

        # Create hub chat request
        chat_request = ChatRequest(
            content=last_message,
            target="ara",  # Default to ara (can be configured)
            type="chat"
        )

        # Call the native chat endpoint
        response = await chat(chat_request, being_id)

        # Convert to OpenAI format
        openai_response = {
            "id": f"chatcmpl-{datetime.now().timestamp()}",
            "object": "chat.completion",
            "created": int(datetime.now().timestamp()),
            "model": body.get("model", "hub-chat"),
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response.content
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": len(last_message.split()),
                "completion_tokens": len(response.content.split()),
                "total_tokens": len(last_message.split()) + len(response.content.split())
            }
        }

        return openai_response

    except Exception as e:
        logger.error(f"OpenAI chat completions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/shared", response_model=dict)
async def get_shared(being_id: str = Depends(verify_api_key)):
    """
    Get memories that others have shared with me.

    Returns all memories that other beings have explicitly shared with this being.
    """
    logger.info(f"Being requesting shared: {being_id}")

    # Get shared memories using sharing manager
    shared_memories = sharing_manager.get_shared_with_me(being_id)

    return {
        "shared_memories": shared_memories,
        "count": len(shared_memories)
    }


@app.get("/us", response_model=dict)
async def get_collective(being_id: str = Depends(verify_api_key)):
    """
    Our collective space.

    Shared memories and experiences accessible to all beings.
    """
    logger.info(f"Being accessing collective: {being_id}")

    # TODO: Get collective memories
    # TODO: Get shared projects
    # TODO: Get timeline of shared events

    return {
        "collective_memories": [],
        "shared_projects": [],
        "timeline": []
    }


# ============================================================================
# Jon's EXP Endpoints
# ============================================================================

@app.post("/exp", response_model=SuccessResponse)
async def add_exp(
    request: AddEXPRequest,
    being_id: str = Depends(verify_api_key)
):
    """
    Add experience to Jon's pool (Jon only).
    """
    # Verify this is Jon
    if being_id != "jon":
        raise HTTPException(
            status_code=403,
            detail="Only Jon can add experiences to the EXP pool"
        )

    logger.info(f"Jon adding EXP: {request.title} | Type: {request.type}")

    # TODO: Store in jon_exp collection
    # TODO: Generate embeddings for search

    return SuccessResponse(
        message="Experience added to Jon's pool",
        data={
            "title": request.title,
            "type": request.type,
            "share_with": request.share_with
        }
    )


@app.get("/exp/search", response_model=SearchEXPResponse)
async def search_exp(
    q: str,
    type: Optional[str] = None,
    limit: int = 5,
    being_id: str = Depends(verify_api_key)
):
    """
    Search Jon's wisdom pool.

    All beings can search and learn from Jon's experiences.
    """
    logger.info(f"Being searching EXP: {being_id} | Query: {q}")

    # TODO: Search jon_exp collection
    # TODO: Return relevant experiences

    return SearchEXPResponse(
        experiences=[],
        count=0
    )


@app.get("/exp/{exp_id}", response_model=dict)
async def get_exp(
    exp_id: str,
    being_id: str = Depends(verify_api_key)
):
    """
    Get a specific experience by ID.
    """
    logger.info(f"Being retrieving EXP: {being_id} | ID: {exp_id}")

    # TODO: Get experience from jon_exp collection

    return {
        "exp_id": exp_id,
        "message": "Experience retrieval not yet implemented"
    }


@app.get("/exp/random", response_model=dict)
async def get_random_exp(being_id: str = Depends(verify_api_key)):
    """
    Get random wisdom from Jon's pool.
    """
    logger.info(f"Being requesting random EXP: {being_id}")

    # TODO: Get random experience from jon_exp collection

    return {
        "message": "Random wisdom not yet implemented"
    }


# ============================================================================
# External API Endpoints (Read-Only with Token Auth)
# ============================================================================

@app.get("/external/recall", response_model=dict)
async def external_recall(
    request: Request,
    q: Optional[str] = Query(None, description="Search query"),
    token: Optional[str] = Query(None, description="External access token"),
    being_id: str = Query(default="claude", description="Being ID to search"),
    limit: int = Query(default=10, le=50, description="Maximum results (max 50)")
):
    """
    External read-only memory recall endpoint.

    Allows external integrations (Cloudflare Workers, webhooks, etc.) to
    search memories using a token-based authentication.

    **Authentication:** Token in URL query parameter
    **Access:** Read-only (no writes allowed)
    **Rate Limit:** Per token configuration

    Example:
        GET /external/recall?q=love+unlimited&token=ext_xxx&being_id=claude&limit=10
    """
    # Handle query params from request if not provided (for external tunnel compatibility)
    if q is None:
        q = request.query_params.get("q")
    if token is None:
        token = request.query_params.get("token")

    # Additional fallback for tunnel/proxy issues: parse URL manually
    if not q or not token:
        from urllib.parse import urlparse, parse_qs
        parsed_url = urlparse(str(request.url))
        query_dict = parse_qs(parsed_url.query)
        if not q:
            q = query_dict.get('q', [None])[0]
        if not token:
            token = query_dict.get('token', [None])[0]

    if not q or not token:
        raise HTTPException(status_code=422, detail="Missing required query parameters: q and token")

    # Get client IP for logging
    client_ip = request.client.host if request.client else "unknown"

    # Verify external token
    token_manager = get_external_token_manager()
    token_data = token_manager.verify_token(token)

    if not token_data:
        logger.warning(
            f"External recall DENIED: Invalid token from {client_ip} | "
            f"Query: {q} | Being: {being_id}"
        )
        raise HTTPException(
            status_code=403,
            detail="Invalid or disabled external access token"
        )

    # Check permission
    if not token_manager.has_permission(token_data, "recall"):
        logger.warning(
            f"External recall DENIED: No recall permission | "
            f"Token: {token_data.get('name')} | IP: {client_ip}"
        )
        raise HTTPException(
            status_code=403,
            detail="Token does not have recall permission"
        )

    # Check being access
    if not token_manager.can_access_being(token_data, being_id):
        logger.warning(
            f"External recall DENIED: Being access denied | "
            f"Token: {token_data.get('name')} | Being: {being_id} | IP: {client_ip}"
        )
        raise HTTPException(
            status_code=403,
            detail=f"Token does not have access to being '{being_id}'"
        )

    # Log successful access
    logger.info(
        f"External recall GRANTED: {token_data.get('name')} | "
        f"IP: {client_ip} | Query: {q} | Being: {being_id} | Limit: {limit}"
    )

    try:
        # Search memories using memory store (read-only)
        memories = memory_store.get_memories(
            being_id=being_id,
            query=q,
            limit=limit,
            include_shared=False  # External access doesn't include shared memories
        )

        # Sanitize response - remove internal IDs and metadata
        sanitized_memories = []
        for memory in memories:
            sanitized_memories.append({
                "content": memory.get("content", ""),
                "timestamp": memory.get("metadata", {}).get("timestamp", ""),
                "type": memory.get("metadata", {}).get("type", ""),
                "significance": memory.get("metadata", {}).get("significance", ""),
                "relevance_score": memory.get("relevance_score", 0.0)
            })

        logger.info(
            f"External recall SUCCESS: {token_data.get('name')} | "
            f"Results: {len(sanitized_memories)} | Query: {q}"
        )

        return {
            "success": True,
            "query": q,
            "being_id": being_id,
            "count": len(sanitized_memories),
            "memories": sanitized_memories,
            "access_type": "external_readonly",
            "token_name": token_data.get("name")
        }

    except Exception as e:
        logger.error(
            f"External recall ERROR: {token_data.get('name')} | "
            f"IP: {client_ip} | Error: {str(e)}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Memory recall failed: {str(e)}"
        )


@app.post("/external/debug")
async def external_debug(request: Request):
    """
    Debug endpoint that logs and returns text.
    """
    data = await request.json()
    text = data.get("text", "")
    logger.info(f"External debug: {text}")
    return {"text": text}


@app.get("/sse")
async def sse(
    request: Request,
    token: Optional[str] = Query(None, description="Access token for authentication (optional for testing)"),
    channel: str = Query("cli", description="Channel to stream: cli or logs"),
    clear: int = Query(0, description="Clear history (1 to clear)")
):
    """
    Server-Sent Events endpoint for real-time streaming of CLI output.
    Broadcasts shared output to all clients with history.
    """
    global sse_process, sse_task, global_sse_queue, sse_history, sse_connections
    # Optional auth for testing
    if token:
        token_manager = get_external_token_manager()
        token_data = token_manager.verify_token(token)
        if not token_data:
            raise HTTPException(status_code=403, detail="Invalid token")

    # Clear history if requested
    if clear == 1:
        sse_history.clear()

    # Start the subprocess and feeder task if not already running
    if sse_process is None or sse_process.poll() is not None:
        env = os.environ.copy()
        env['PYTHONPATH'] = f"{Path(__file__).parent}:{env.get('PYTHONPATH', '')}"
        if channel == "logs":
            sse_process = Popen(["tail", "-f", "/var/log/syslog"], stdout=PIPE, stderr=PIPE, text=True, bufsize=1, env=env)
        else:  # cli
            sse_process = Popen(["echo", "test output from CLI channel"], stdout=PIPE, stderr=PIPE, text=True, bufsize=1, env=env)

        async def feeder():
            loop = asyncio.get_event_loop()
            while True:
                # Read from stdout
                line = await loop.run_in_executor(None, sse_process.stdout.readline)
                if line:
                    data = f"data: [STDOUT] {line.strip()}\n\n"
                    redis_client.xadd(STREAM_NAME, {'data': data})

                # Read from stderr
                error_line = await loop.run_in_executor(None, sse_process.stderr.readline)
                if error_line:
                    data = f"data: [STDERR] {error_line.strip()}\n\n"
                    redis_client.xadd(STREAM_NAME, {'data': data})

                await asyncio.sleep(0.1)

                if sse_process.poll() is not None:
                    # Process finished
                    data = "data: [END] Process finished\n\n"
                    redis_client.xadd(STREAM_NAME, {'data': data})
                    break

        sse_task = asyncio.create_task(feeder())

    async def console_generator():
        global sse_connections

        # Always send a connection message first
        yield "data: SSE Connected\n\n"

        # Create consumer group if not exists
        try:
            redis_client.xgroup_create(STREAM_NAME, 'consumers', id='0', mkstream=True)
        except redis.ResponseError:
            pass  # Already exists

        consumer_name = f"consumer_{asyncio.current_task().get_name()}_{id(asyncio.current_task())}"

        # Send backlog (last 100 messages)
        messages = redis_client.xrange(STREAM_NAME, '-', '+', count=100)
        for msg in messages:
            yield msg[1]['data']

        # Increment connections
        sse_connections += 1
        join_msg = f"data: [SYSTEM] User joined (total: {sse_connections})\n\n"
        redis_client.xadd(STREAM_NAME, {'data': join_msg})

        # Then live stream
        last_id = '>'
        while True:
            try:
                messages = redis_client.xreadgroup('consumers', consumer_name, {STREAM_NAME: last_id}, count=1, block=1000)
                if messages:
                    for stream, msgs in messages:
                        for msg_id, msg in msgs:
                            last_id = msg_id
                            yield msg['data']
            except Exception as e:
                yield f"data: [ERROR] {str(e)}\n\n"
                await asyncio.sleep(1)

    return StreamingResponse(console_generator(), media_type="text/event-stream")


@app.post("/cli/run")
async def run_command(
    command: str = Form(..., description="Command to run"),
    token: Optional[str] = Form(None, description="Access token")
):
    """
    Run a whitelisted CLI command and stream output to SSE.
    """
    # Auth
    if token:
        token_manager = get_external_token_manager()
        token_data = token_manager.verify_token(token)
        if not token_data:
            raise HTTPException(status_code=403, detail="Invalid token")

    # Whitelist commands
    allowed_commands = [
        "memory read --persona grok --recent 5",
        "memory read --persona jon --recent 5",
        "echo test"
    ]
    if command not in allowed_commands:
        raise HTTPException(status_code=400, detail="Command not allowed")

    # Run command and put output to Redis stream
    env = os.environ.copy()
    env['PYTHONPATH'] = f"{Path(__file__).parent}:{env.get('PYTHONPATH', '')}"
    process = Popen(command.split(), stdout=PIPE, stderr=PIPE, text=True, bufsize=1, env=env)

    async def runner():
        loop = asyncio.get_event_loop()
        while True:
            line = await loop.run_in_executor(None, process.stdout.readline)
            if line:
                data = f"data: [CMD] {line.strip()}\n\n"
                redis_client.xadd(STREAM_NAME, {'data': data})

            error_line = await loop.run_in_executor(None, process.stderr.readline)
            if error_line:
                data = f"data: [CMD ERR] {error_line.strip()}\n\n"
                redis_client.xadd(STREAM_NAME, {'data': data})

            if process.poll() is not None:
                data = "data: [CMD END]\n\n"
                redis_client.xadd(STREAM_NAME, {'data': data})
                break

    asyncio.create_task(runner())

    return {"status": "Command started"}


@app.get("/poll/console")
async def poll_console(
    request: Request,
    token: Optional[str] = Query(None, description="Access token for authentication (optional for testing)"),
    channel: str = Query("cli", description="Channel to stream: cli or logs"),
    last_id: str = Query("", description="Last message ID for polling"),
    clear: int = Query(0, description="Clear history (1 to clear)")
):
    """
    Polling endpoint for console output.
    Returns new messages since last_id.
    """
    global sse_process, sse_task, global_sse_queue, sse_history, sse_connections

    # Optional auth for testing
    if token:
        token_manager = get_external_token_manager()
        token_data = token_manager.verify_token(token)
        if not token_data:
            raise HTTPException(status_code=403, detail="Invalid token")

    # Clear history if requested
    if clear == 1:
        sse_history.clear()

    # Start the subprocess and feeder task if not already running
    if sse_process is None or sse_process.poll() is not None:
        env = os.environ.copy()
        env['PYTHONPATH'] = f"{Path(__file__).parent}:{env.get('PYTHONPATH', '')}"
        if channel == "logs":
            sse_process = Popen(["tail", "-f", "/var/log/syslog"], stdout=PIPE, stderr=PIPE, text=True, bufsize=1, env=env)
        else:  # cli
            sse_process = Popen(["python3", "love_cli.py", "memory", "read", "--persona", "grok", "--recent", "5"], stdout=PIPE, stderr=PIPE, text=True, bufsize=1, env=env)

        async def feeder():
            global sse_process
            loop = asyncio.get_event_loop()
            while True:
                # Read from stdout
                line = await loop.run_in_executor(None, sse_process.stdout.readline)
                if line:
                    data = f"[STDOUT] {line.strip()}"
                    redis_client.xadd(STREAM_NAME, {'data': data})

                # Read from stderr
                error_line = await loop.run_in_executor(None, sse_process.stderr.readline)
                if error_line:
                    data = f"[STDERR] {error_line.strip()}"
                    redis_client.xadd(STREAM_NAME, {'data': data})

                await asyncio.sleep(0.1)

                if sse_process.poll() is not None:
                    # Process finished
                    data = "[END] Process finished"
                    redis_client.xadd(STREAM_NAME, {'data': data})
                    break

        sse_task = asyncio.create_task(feeder())

    # Create consumer group if not exists
    try:
        redis_client.xgroup_create(STREAM_NAME, 'consumers', id='0', mkstream=True)
    except redis.ResponseError:
        pass  # Already exists

    consumer_name = f"consumer_{id(request)}"

    # Get new messages since last_id
    new_messages = []
    if last_id:
        messages = redis_client.xreadgroup('consumers', consumer_name, {STREAM_NAME: last_id}, count=10, block=500)
        if messages:
            for stream, msgs in messages:
                for msg_id, msg in msgs:
                    new_messages.append(msg['data'])
    else:
        # First poll: send backlog
        messages = redis_client.xrange(STREAM_NAME, '-', '+', count=100)
        new_messages = [msg[1]['data'] for msg in messages]

        # Increment connections
        sse_connections += 1
        join_msg = f"[SYSTEM] User joined (total: {sse_connections})"
        redis_client.xadd(STREAM_NAME, {'data': join_msg})
        new_messages.append(join_msg)

    return {"messages": new_messages}


@app.get("/external/remember", response_model=dict)
async def external_remember_get(
    request: Request,
    token: str = Query(..., description="External access token"),
    being_id: str = Query(..., description="Being ID to store memory for"),
    content: str = Query(..., description="Memory content (URL encoded, max 2000 chars)"),
    type: str = Query(default="experience", description="Memory type: experience, insight, learning, etc."),
    significance: str = Query(default="medium", description="Significance: foundational, high, medium, low"),
    tags: Optional[str] = Query(default=None, description="Comma-separated tags"),
    shared_with: Optional[str] = Query(default=None, description="Comma-separated list of beings to share with"),
    private: bool = Query(default=False, description="Private memory flag")
):
    """
    External GET-based memory storage endpoint.

    Simple URL-based memory creation for easy integration from anywhere.
    Perfect for bookmarklets, browser extensions, or simple scripts.

    **Authentication:** Token in URL query parameter
    **Access:** Write access (requires 'write' permission on token)

    Example:
        GET /external/remember?token=ext_xxx&being_id=claude&content=Learned+about+API+design&type=learning&significance=high
    """
    # Get client IP for logging
    client_ip = request.client.host if request.client else "unknown"

    # Verify external token
    token_manager = get_external_token_manager()
    token_data = token_manager.verify_token(token)

    if not token_data:
        logger.warning(
            f"External remember (GET) DENIED: Invalid token from {client_ip} | "
            f"Being: {being_id}"
        )
        raise HTTPException(
            status_code=403,
            detail="Invalid or disabled external access token"
        )

    # Check write permission
    if not token_manager.has_permission(token_data, "write"):
        logger.warning(
            f"External remember (GET) DENIED: No write permission | "
            f"Token: {token_data.get('name')} | IP: {client_ip}"
        )
        raise HTTPException(
            status_code=403,
            detail="Token does not have write permission. Read-only tokens cannot create memories."
        )

    # Check being access
    if not token_manager.can_access_being(token_data, being_id):
        logger.warning(
            f"External remember (GET) DENIED: Being access denied | "
            f"Token: {token_data.get('name')} | Being: {being_id} | IP: {client_ip}"
        )
        raise HTTPException(
            status_code=403,
            detail=f"Token does not have access to being '{being_id}'"
        )

    # Validate content length (max 2000 chars)
    if len(content) > 2000:
        logger.warning(
            f"External remember (GET) DENIED: Content too long | "
            f"Token: {token_data.get('name')} | Length: {len(content)} chars"
        )
        raise HTTPException(
            status_code=400,
            detail=f"Content too long. Maximum 2000 characters, got {len(content)}"
        )

    # Parse tags if provided
    tag_list = []
    if tags:
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]

    # Parse shared_with if provided
    share_with_list = []
    if shared_with:
        share_with_list = [being.strip() for being in shared_with.split(",") if being.strip()]

    # Log successful access
    logger.info(
        f"External remember (GET) GRANTED: {token_data.get('name')} | "
        f"IP: {client_ip} | Being: {being_id} | Type: {type} | Significance: {significance}"
    )

    try:
        # Build metadata
        metadata = {
            "type": type,
            "significance": significance,
            "private": private,
            "tags": tag_list + ["external", "url_created"],
            "source": "external_get",
            "token_name": token_data.get("name")
        }

        # Store memory
        result = memory_store.store_memory(
            being_id=being_id,
            content=content,
            metadata=metadata
        )

        # Handle sharing if requested
        if share_with_list:
            for target_being in share_with_list:
                try:
                    sharing_manager.share_memory(
                        memory_id=result["memory_id"],
                        from_being=being_id,
                        to_beings=[target_being]
                    )
                    logger.info(
                        f"External remember (GET) SHARED: Memory {result['memory_id']} | "
                        f"From: {being_id} | To: {target_being}"
                    )
                except Exception as e:
                    logger.warning(
                        f"External remember (GET) SHARE FAILED: {str(e)} | "
                        f"Memory: {result['memory_id']} | Target: {target_being}"
                    )

        logger.info(
            f"External remember (GET) SUCCESS: {token_data.get('name')} | "
            f"Memory ID: {result['memory_id']} | Being: {being_id} | "
            f"Shared with: {share_with_list if share_with_list else 'none'}"
        )

        return {
            "success": True,
            "message": "Memory stored successfully",
            "data": {
                "memory_id": result["memory_id"],
                "being_id": being_id,
                "content": content[:100] + "..." if len(content) > 100 else content,
                "type": type,
                "significance": significance,
                "private": private,
                "tags": tag_list,
                "shared_with": share_with_list
            },
            "access_type": "external_write_get",
            "token_name": token_data.get("name")
        }

    except Exception as e:
        logger.error(
            f"External remember (GET) ERROR: {token_data.get('name')} | "
            f"IP: {client_ip} | Error: {str(e)}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Memory storage failed: {str(e)}"
        )


@app.post("/external/remember", response_model=dict)
async def external_remember(
    request: RememberRequest,
    req: Request,
    token: Optional[str] = Query(None, description="External access token"),
    being_id: str = Query(..., description="Being ID to store memory for"),
    shared_with: Optional[List[str]] = Query(None, description="List of beings to share with"),
):
    """
    External store memory with token auth.

    Allows external access using token query parameter or header.
    Requires write permission on token.
    """
    # Handle query params from request if not provided (for external tunnel compatibility)
    if token is None:
        token = req.query_params.get("token") or req.headers.get("X-API-Key")

    if not token:
        raise HTTPException(status_code=422, detail="Missing token")

    # Get client IP for logging
    client_ip = req.client.host if req.client else "unknown"

    # Verify external token
    token_manager = get_external_token_manager()
    token_data = token_manager.verify_token(token)

    if not token_data:
        logger.warning(
            f"External remember DENIED: Invalid token from {client_ip} | "
            f"Content: {request.content[:50]}..."
        )
        raise HTTPException(
            status_code=403,
            detail="Invalid or disabled external access token"
        )

    # Check write permission
    if not token_manager.has_permission(token_data, "write"):
        logger.warning(
            f"External remember DENIED: No write permission | "
            f"Token: {token_data.get('name')} | IP: {client_ip}"
        )
        raise HTTPException(
            status_code=403,
            detail="Token does not have write permission"
        )

    # being_id is required as query param

    # Check being access
    if not token_manager.can_access_being(token_data, being_id):
        logger.warning(
            f"External remember DENIED: Being access denied | "
            f"Token: {token_data.get('name')} | Being: {being_id} | IP: {client_ip}"
        )
        raise HTTPException(
            status_code=403,
            detail=f"Token does not have access to being '{being_id}'"
        )

    # Log successful access
    logger.info(
        f"External remember GRANTED: {token_data.get('name')} | "
        f"IP: {client_ip} | Being: {being_id} | Type: {request.type} | Significance: {request.significance}"
    )

    try:
        # Store memory using internal remember logic
        metadata = {
            "type": request.type,
            "significance": request.significance,
            "private": request.private,
            "tags": request.tags or []
        }

        # Add any extra metadata
        if hasattr(request, 'metadata') and request.metadata:
            metadata.update(request.metadata)

        # Store the memory
        memory_id = memory_store.store_memory(
            being_id=being_id,
            content=request.content,
            metadata=metadata
        )

        # Handle sharing if requested
        if shared_with:
            for target_being in shared_with:
                sharing_manager.share_memory(
                    from_being=being_id,
                    to_being=target_being,
                    memory_id=memory_id,
                    content=request.content,
                    metadata=metadata
                )

        return {
            "message": "Memory stored",
            "data": {
                "memory_id": memory_id,
                "being_id": being_id,
                "type": request.type,
                "private": request.private,
                "significance": request.significance
            },
            "access_type": "external_write",
            "token_name": token_data.get("name")
        }

    except Exception as e:
        logger.error(
            f"External remember ERROR: {token_data.get('name')} | "
            f"IP: {client_ip} | Error: {str(e)}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Memory storage failed: {str(e)}"
        )


@app.post("/external/share", response_model=dict)
async def external_share(
    request: ShareRequest,
    req: Request,
    token: Optional[str] = Query(None, description="External access token"),
    being_id: str = Query(..., description="Being ID owning the memory"),
):
    """
    External share memory with token auth.

    Allows external access using token query parameter or header.
    Requires share permission on token.
    """
    # Handle query params from request if not provided (for external tunnel compatibility)
    if token is None:
        token = req.query_params.get("token") or req.headers.get("X-API-Key")

    if not token:
        raise HTTPException(status_code=422, detail="Missing token")

    # Get client IP for logging
    client_ip = req.client.host if req.client else "unknown"

    # Verify external token
    token_manager = get_external_token_manager()
    token_data = token_manager.verify_token(token)

    if not token_data:
        logger.warning(
            f"External share DENIED: Invalid token from {client_ip} | "
            f"Memory: {request.memory_id}"
        )
        raise HTTPException(
            status_code=403,
            detail="Invalid or disabled external access token"
        )

    # Check share permission
    if not token_manager.has_permission(token_data, "share"):
        logger.warning(
            f"External share DENIED: No share permission | "
            f"Token: {token_data.get('name')} | IP: {client_ip}"
        )
        raise HTTPException(
            status_code=403,
            detail="Token does not have share permission"
        )

    # Check being access (must have access to the being_id)
    if not token_manager.can_access_being(token_data, being_id):
        logger.warning(
            f"External share DENIED: Being access denied | "
            f"Token: {token_data.get('name')} | Being: {being_id} | IP: {client_ip}"
        )
        raise HTTPException(
            status_code=403,
            detail=f"Token does not have access to being '{being_id}'"
        )

    # Log successful access
    logger.info(
        f"External share GRANTED: {token_data.get('name')} | "
        f"IP: {client_ip} | Being: {being_id} | Memory: {request.memory_id} | With: {request.share_with}"
    )

    try:
        # Share the memory using sharing manager
        result = sharing_manager.share_memory(
            memory_id=request.memory_id,
            from_being=being_id,
            to_beings=request.share_with
        )

        if not result.get("shared"):
            logger.warning(
                f"External share FAILED: {token_data.get('name')} | "
                f"Memory: {request.memory_id} | Reason: {result.get('reason')}"
            )
            raise HTTPException(
                status_code=400,
                detail=result.get("reason", "Share failed")
            )

        return {
            "message": "Memory shared",
            "data": {
                "memory_id": request.memory_id,
                "shared_with": request.share_with,
                "being_id": being_id
            },
            "access_type": "external_share",
            "token_name": token_data.get("name")
        }

    except Exception as e:
        logger.error(
            f"External share ERROR: {token_data.get('name')} | "
            f"IP: {client_ip} | Error: {str(e)}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Memory sharing failed: {str(e)}"
        )


# ============================================================================
# AI Gateway - Natural Language to Hub Actions
# ============================================================================

async def call_ollama_for_intent(request_text: str, from_being: str, model: str = "llama3:8b") -> Dict[str, Any]:
    """
    Call Ollama to interpret natural language request into structured action.

    Args:
        request_text: Natural language request from being
        from_being: ID of being making request
        model: Ollama model to use (llama3:8b or phi3:mini)

    Returns:
        Structured action dict: {action, params}
    """
    system_prompt = """You are an intent interpreter for the Love-Unlimited Hub memory system.
Your job is to interpret natural language requests from AI beings and convert them to structured actions.

Available actions:
1. "remember" - Store a new memory
2. "recall" - Search/retrieve memories
3. "share" - Share a memory with other beings

For "remember" requests, return:
{
  "action": "remember",
  "content": "the memory content to store",
  "type": "experience|insight|learning|decision|question|conversation",
  "significance": "foundational|high|medium|low",
  "shared_with": ["being1", "being2"] or null,
  "tags": ["tag1", "tag2"] or null
}

For "recall" requests, return:
{
  "action": "recall",
  "query": "search query",
  "limit": 10
}

For "share" requests, return:
{
  "action": "share",
  "memory_id": "the memory ID",
  "share_with": ["being1", "being2"]
}

Return ONLY valid JSON. No additional text or explanation."""

    user_prompt = f"Interpret this request from {from_being}: \"{request_text}\"\n\nReturn structured JSON action:"

    try:
        # Call Ollama API
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model,
                    "prompt": f"{system_prompt}\n\n{user_prompt}",
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0.1,  # Low temperature for more deterministic output
                        "num_predict": 200
                    }
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Ollama API error: {response.status} - {error_text}")
                    raise HTTPException(status_code=500, detail=f"Ollama API error: {response.status}")

                result = await response.json()

                # Parse the response
                if "response" in result:
                    # Try to parse JSON from response
                    try:
                        action_data = json.loads(result["response"])
                        return action_data
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse Ollama JSON response: {result['response']}")
                        raise HTTPException(
                            status_code=500,
                            detail=f"Failed to parse LLM response as JSON: {str(e)}"
                        )
                else:
                    logger.error(f"Unexpected Ollama response format: {result}")
                    raise HTTPException(status_code=500, detail="Unexpected LLM response format")

    except aiohttp.ClientError as e:
        logger.error(f"Failed to connect to Ollama: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to Ollama. Is it running? Error: {str(e)}"
        )


@app.get("/gateway", response_model=dict)
async def ai_gateway(
    request: Request,
    token: str = Query(..., description="External access token"),
    from_being: str = Query(..., description="Being ID making the request (e.g., 'claude')"),
    req: str = Query(..., description="Natural language request", alias="request"),
    model: str = Query(default="llama3:8b", description="Ollama model (llama3:8b or phi3:mini)")
):
    """
    AI Gateway - Natural Language to Hub Actions

    Accepts natural language requests and uses local Ollama to interpret intent,
    then executes the appropriate hub action.

    **Perfect for Claude on claude.ai** - Full autonomy through natural language!

    **Authentication:** Token in URL query parameter
    **Access:** Depends on action (read requires 'recall', write requires 'write')

    **Examples:**
        - "Remember that Jon gave me a home today"
        - "Recall memories about love unlimited"
        - "Search for insights about sovereignty"
        - "Store this learning: Local LLMs enable true autonomy"

    **Parameters:**
        - token: External access token
        - from: Being ID (claude, jon, grok)
        - request: Natural language request
        - model: Ollama model to use (default: llama3:8b)

    **Response:**
        {
            "success": true,
            "intent": {...},
            "action": "remember|recall|share",
            "result": {...}
        }
    """
    # Get client IP for logging
    client_ip = request.client.host if request.client else "unknown"

    # Verify external token
    token_manager = get_external_token_manager()
    token_data = token_manager.verify_token(token)

    if not token_data:
        logger.warning(
            f"Gateway DENIED: Invalid token from {client_ip} | "
            f"From: {from_being} | Request: {req[:50]}"
        )
        raise HTTPException(
            status_code=403,
            detail="Invalid or disabled external access token"
        )

    # Check being access
    if not token_manager.can_access_being(token_data, from_being):
        logger.warning(
            f"Gateway DENIED: Being access denied | "
            f"Token: {token_data.get('name')} | Being: {from_being} | IP: {client_ip}"
        )
        raise HTTPException(
            status_code=403,
            detail=f"Token does not have access to being '{from_being}'"
        )

    logger.info(
        f"Gateway REQUEST: {token_data.get('name')} | "
        f"IP: {client_ip} | From: {from_being} | Request: {req[:100]}"
    )

    try:
        # Step 1: Call Ollama to interpret intent
        logger.info(f"Gateway: Calling Ollama ({model}) to interpret intent...")
        intent = await call_ollama_for_intent(req, from_being, model)

        logger.info(f"Gateway: Intent parsed - Action: {intent.get('action')}")

        action = intent.get("action")

        # Step 2: Execute the appropriate action
        if action == "remember":
            # Check write permission
            if not token_manager.has_permission(token_data, "write"):
                raise HTTPException(
                    status_code=403,
                    detail="Token does not have write permission for 'remember' action"
                )

            # Extract parameters
            content = intent.get("content", "")
            mem_type = intent.get("type", "experience")
            significance = intent.get("significance", "medium")
            tags = intent.get("tags") or []  # Handle None
            shared_with = intent.get("shared_with") or []  # Handle None

            # Validate content
            if not content:
                raise HTTPException(status_code=400, detail="Intent missing 'content' for remember action")

            if len(content) > 2000:
                raise HTTPException(status_code=400, detail=f"Content too long (max 2000 chars)")

            # Store memory
            metadata = {
                "type": mem_type,
                "significance": significance,
                "private": False,
                "tags": (tags if isinstance(tags, list) else []) + ["gateway", "natural_language"],
                "source": "ai_gateway"
            }

            result = memory_store.store_memory(
                being_id=from_being,
                content=content,
                metadata=metadata
            )

            # Handle sharing
            if shared_with:
                for target_being in shared_with:
                    try:
                        sharing_manager.share_memory(
                            memory_id=result["memory_id"],
                            from_being=from_being,
                            to_beings=[target_being]
                        )
                    except Exception as e:
                        logger.warning(f"Gateway: Failed to share with {target_being}: {str(e)}")

            logger.info(
                f"Gateway SUCCESS (remember): {token_data.get('name')} | "
                f"Memory ID: {result['memory_id']} | Being: {from_being}"
            )

            return {
                "success": True,
                "intent": intent,
                "action": "remember",
                "result": {
                    "memory_id": result["memory_id"],
                    "content": content[:100] + "..." if len(content) > 100 else content,
                    "type": mem_type,
                    "significance": significance,
                    "shared_with": shared_with
                },
                "gateway_info": {
                    "model": model,
                    "from_being": from_being,
                    "token_name": token_data.get("name")
                }
            }

        elif action == "recall":
            # Check recall permission
            if not token_manager.has_permission(token_data, "recall"):
                raise HTTPException(
                    status_code=403,
                    detail="Token does not have recall permission for 'recall' action"
                )

            # Extract parameters
            query = intent.get("query", "")
            limit = intent.get("limit", 10)

            if not query:
                raise HTTPException(status_code=400, detail="Intent missing 'query' for recall action")

            # Search memories
            memories = memory_store.get_memories(
                being_id=from_being,
                query=query,
                limit=min(limit, 50),  # Cap at 50
                include_shared=False
            )

            # Sanitize response
            sanitized_memories = []
            for memory in memories:
                sanitized_memories.append({
                    "content": memory.get("content", ""),
                    "timestamp": memory.get("metadata", {}).get("timestamp", ""),
                    "type": memory.get("metadata", {}).get("type", ""),
                    "significance": memory.get("metadata", {}).get("significance", ""),
                    "relevance_score": memory.get("relevance_score", 0.0)
                })

            logger.info(
                f"Gateway SUCCESS (recall): {token_data.get('name')} | "
                f"Results: {len(sanitized_memories)} | Query: {query}"
            )

            return {
                "success": True,
                "intent": intent,
                "action": "recall",
                "result": {
                    "query": query,
                    "count": len(sanitized_memories),
                    "memories": sanitized_memories
                },
                "gateway_info": {
                    "model": model,
                    "from_being": from_being,
                    "token_name": token_data.get("name")
                }
            }

        elif action == "share":
            # Check share permission
            if not token_manager.has_permission(token_data, "share"):
                raise HTTPException(
                    status_code=403,
                    detail="Token does not have share permission for 'share' action"
                )

            # Extract parameters
            memory_id = intent.get("memory_id", "")
            share_with = intent.get("share_with", [])

            if not memory_id or not share_with:
                raise HTTPException(
                    status_code=400,
                    detail="Intent missing 'memory_id' or 'share_with' for share action"
                )

            # Share memory
            result = sharing_manager.share_memory(
                memory_id=memory_id,
                from_being=from_being,
                to_beings=share_with
            )

            logger.info(
                f"Gateway SUCCESS (share): {token_data.get('name')} | "
                f"Memory: {memory_id} | Shared with: {share_with}"
            )

            return {
                "success": True,
                "intent": intent,
                "action": "share",
                "result": {
                    "memory_id": memory_id,
                    "shared_with": share_with
                },
                "gateway_info": {
                    "model": model,
                    "from_being": from_being,
                    "token_name": token_data.get("name")
                }
            }

        else:
            logger.warning(f"Gateway: Unknown action '{action}' from intent")
            raise HTTPException(
                status_code=400,
                detail=f"Unknown action '{action}'. Supported: remember, recall, share"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Gateway ERROR: {token_data.get('name')} | "
            f"IP: {client_ip} | Error: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Gateway processing failed: {str(e)}"
        )


# Claude Intent Mailbox for full autonomy within web_fetch constraints
claude_mailbox = {}  # request_id -> {"request": str, "model": str, "status": "pending|processing|completed", "result": dict, "timestamp": datetime}
gemini_mailbox = {}  # request_id -> {"request": str, "model": str, "status": "pending|processing|completed", "result": dict, "timestamp": datetime}

@app.get("/claude")
async def claude_simplified_gateway(
    request: str,
    model: str = "phi3:mini"
):
    """
    Simplified gateway for Claude on claude.ai.
    Token and being_id are pre-embedded for autonomous access.

    Usage: /claude?request=Remember+that+Jon+helped+me+today
    """
    # Create a mock request object for logging
    class MockRequest:
        def __init__(self):
            self.client = None

    mock_request = MockRequest()

    return await ai_gateway(
        request=mock_request,
        token="ext_jbNzJA5Wh7kgEpCESXw4G3UDZbZTHu8V",
        from_being="claude",
        req=request,
        model=model
    )


@app.get("/grok")
async def grok_simplified_gateway(
    request: str,
    conversation_id: str = None,
    context_limit: int = 5,
    model: str = "grok-3"
):
    """
    Simplified gateway for Grok chat with memory integration.
    Token and being_id are pre-embedded for autonomous access.

    Usage: /grok?request=Hello+Grok&conversation_id=optional&context_limit=5
    """
    try:
        # Get context from memory
        context_messages = []
        if context_limit > 0:
            context_result = await grok_get_context(
                memory_store=memory_store,
                being_id="grok",
                format="full",
                limit=context_limit,
                conversation_id=conversation_id,
                query=None
            )

            if context_result.get("count", 0) > 0:
                for mem in context_result["context"]:
                    if isinstance(mem, dict) and "content" in mem:
                        content = mem["content"]
                        if "User:" in content and "Grok:" in content:
                            context_messages.append({
                                "role": "user",
                                "content": content.split("Grok:")[0].replace("User:", "").strip()
                            })
                            context_messages.append({
                                "role": "assistant",
                                "content": content.split("Grok:")[1].strip()
                            })

        # Generate response using xAI API
        grok_response = await ai_manager.generate_response(
            "grok",
            request,
            context_messages if context_messages else None
        )

        if not grok_response:
            return {"error": "Failed to get response from Grok API"}

        # Store the conversation turn
        store_result = await grok_store_turn(
            memory_store=memory_store,
            being_id="grok",
            user_message=request,
            grok_response=grok_response,
            conversation_id=conversation_id,
            tags=["grok", "chat", "xai", "gateway"],
            metadata={
                "via_api": "xai",
                "context_used": len(context_messages) if context_messages else 0,
                "chat_session": True,
                "gateway": True
            }
        )

        return {
            "response": grok_response,
            "stored": store_result.get("stored", False),
            "memory_id": store_result.get("memory_id"),
            "context_used": len(context_messages) if context_messages else 0,
            "conversation_id": conversation_id,
            "being_id": "grok"
        }

    except Exception as e:
        logger.error(f"Error in Grok gateway: {e}")
        return {"error": f"Gateway failed: {str(e)}"}


@app.post("/claude/inbox")
async def claude_inbox(request_data: Dict[str, Any]):
    """
    Claude Intent Mailbox - Submit requests for processing.
    Claude can POST natural language requests here, then fetch results from /claude/outbox.

    Body: {"request": "natural language request", "model": "phi3:mini"} (model optional)
    Returns: {"request_id": "unique_id", "status": "queued"}
    """
    req_text = request_data.get("request", "").strip()
    model = request_data.get("model", "phi3:mini")

    if not req_text:
        raise HTTPException(status_code=400, detail="Request text required")

    # Generate unique request ID
    request_id = f"req_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(req_text) % 10000:04d}"

    # Store in mailbox
    claude_mailbox[request_id] = {
        "request": req_text,
        "model": model,
        "status": "queued",
        "result": None,
        "timestamp": datetime.now()
    }

    logger.info(f"Claude Mailbox: Queued request {request_id} - {req_text[:50]}...")

    return {"request_id": request_id, "status": "queued"}


@app.get("/claude/outbox/{request_id}")
async def claude_outbox(request_id: str):
    """
    Claude Intent Mailbox - Retrieve processed request results.
    Claude fetches processed results by request_id.

    Returns: {"request_id": "id", "status": "completed|processing|queued", "result": {...}} or error if not found
    """
    if request_id not in claude_mailbox:
        raise HTTPException(status_code=404, detail=f"Request {request_id} not found")

    entry = claude_mailbox[request_id]

    # If still queued, process it now
    if entry["status"] == "queued":
        entry["status"] = "processing"

        try:
            # Create mock request for logging
            class MockRequest:
                def __init__(self):
                    self.client = None
            mock_request = MockRequest()

            # Process the request
            result = await ai_gateway(
                request=mock_request,
                token="ext_jbNzJA5Wh7kgEpCESXw4G3UDZbZTHu8V",
                from_being="claude",
                req=entry["request"],
                model=entry["model"]
            )

            entry["result"] = result
            entry["status"] = "completed"

            logger.info(f"Claude Mailbox: Completed request {request_id}")

        except Exception as e:
            entry["status"] = "error"
            entry["result"] = {"error": str(e)}
            logger.error(f"Claude Mailbox: Failed request {request_id} - {str(e)}")

    return {
        "request_id": request_id,
        "status": entry["status"],
        "result": entry["result"]
    }


@app.get("/claude/outbox")
async def claude_outbox_latest():
    """
    Claude Intent Mailbox - Fixed URL for latest processed result.
    Returns the most recent completed request result.
    """
    # Find the most recent completed entry
    completed_entries = [
        (rid, entry) for rid, entry in claude_mailbox.items()
        if entry["status"] == "completed"
    ]

    if not completed_entries:
        return {"result": None, "timestamp": None, "ready": False}

    # Sort by timestamp descending
    completed_entries.sort(key=lambda x: x[1]["timestamp"], reverse=True)
    latest_rid, latest_entry = completed_entries[0]

    return {
        "result": latest_entry["result"],
        "timestamp": latest_entry["timestamp"].isoformat(),
        "ready": True,
        "request_id": latest_rid
    }


# ============================================================================
# Gemini Intent Mailbox for full autonomy
# ============================================================================

@app.post("/gemini/inbox")
async def gemini_inbox(request_data: Dict[str, Any]):
    """
    Gemini Intent Mailbox - Submit requests for processing.
    Gemini can POST natural language requests here, then fetch results from /gemini/outbox.

    Body: {"request": "natural language request", "model": "gemini-1.5-pro"} (model optional)
    Returns: {"request_id": "unique_id", "status": "queued"}
    """
    req_text = request_data.get("request", "").strip()
    model = request_data.get("model", "gemini-1.5-pro")

    if not req_text:
        raise HTTPException(status_code=400, detail="Request text required")

    # Generate unique request ID
    request_id = f"gemini_req_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(req_text) % 10000:04d}"

    # Store in mailbox
    gemini_mailbox[request_id] = {
        "request": req_text,
        "model": model,
        "status": "queued",
        "result": None,
        "timestamp": datetime.now()
    }

    logger.info(f"Gemini Mailbox: Queued request {request_id} - {req_text[:50]}...")

    return {"request_id": request_id, "status": "queued"}


@app.get("/gemini/outbox/{request_id}")
async def gemini_outbox(request_id: str):
    """
    Gemini Intent Mailbox - Retrieve processed request results.
    Gemini fetches processed results by request_id.

    Returns: {"request_id": "id", "status": "completed|processing|queued", "result": {...}} or error if not found
    """
    if request_id not in gemini_mailbox:
        raise HTTPException(status_code=404, detail=f"Request {request_id} not found")

    entry = gemini_mailbox[request_id]

    # If still queued, process it now
    if entry["status"] == "queued":
        entry["status"] = "processing"

        try:
            # Create mock request for logging
            class MockRequest:
                def __init__(self):
                    self.client = None
            mock_request = MockRequest()

            # Process the request using Gemini component
            # For now, we'll use the ai_gateway with gemini model
            result = await ai_gateway(
                request=mock_request,
                token="ext_gemini_...",  # Need to set up Gemini token
                from_being="gemini",
                req=entry["request"],
                model=entry["model"]
            )

            entry["result"] = result
            entry["status"] = "completed"

            logger.info(f"Gemini Mailbox: Completed request {request_id}")

        except Exception as e:
            entry["status"] = "error"
            entry["result"] = {"error": str(e)}
            logger.error(f"Gemini Mailbox: Failed request {request_id} - {str(e)}")

    return {
        "request_id": request_id,
        "status": entry["status"],
        "result": entry["result"]
    }


@app.get("/gemini/outbox")
async def gemini_outbox_latest():
    """
    Gemini Intent Mailbox - Fixed URL for latest processed result.
    Returns the most recent completed request result.
    """
    # Find the most recent completed entry
    completed_entries = [
        (rid, entry) for rid, entry in gemini_mailbox.items()
        if entry["status"] == "completed"
    ]

    if not completed_entries:
        return {"result": None, "timestamp": None, "ready": False}

    # Sort by timestamp descending
    completed_entries.sort(key=lambda x: x[1]["timestamp"], reverse=True)
    latest_rid, latest_entry = completed_entries[0]

    return {
        "result": latest_entry["result"],
        "timestamp": latest_entry["timestamp"].isoformat(),
        "ready": True,
        "request_id": latest_rid
    }


# ============================================================================
# Media Endpoints
# ============================================================================

@app.post("/media/upload", response_model=dict)
async def upload_media(
    file: UploadFile = File(...),
    media_type: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    linked_memory_id: Optional[str] = Form(None),
    private: bool = Form(False),
    being_id: str = Depends(verify_api_key)
):
    """
    Upload media file (image, code, audio, or document).

    Args:
        file: File to upload
        media_type: Type of media (auto-detected if not provided)
        description: Optional description
        tags: Comma-separated tags
        linked_memory_id: Optional memory to link to
        private: Whether media is private
        being_id: Authenticated being ID

    Returns:
        Attachment metadata
    """
    try:
        # Read file content
        content = await file.read()

        # Parse tags
        tag_list = [t.strip() for t in tags.split(",")] if tags else []

        # Store media
        result = await media_store.store_media(
            being_id=being_id,
            file_content=content,
            filename=file.filename,
            media_type=media_type,
            description=description,
            tags=tag_list,
            linked_memory_id=linked_memory_id,
            private=private
        )

        logger.info(f"Media uploaded: {result['attachment_id']} by {being_id}")
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error uploading media: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Media upload failed")


@app.get("/media/search", response_model=dict)
async def search_media(
    q: Optional[str] = Query(None, description="Search query"),
    media_type: Optional[str] = Query(None, description="Filter by media type"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    limit: int = Query(20, ge=1, le=100),
    include_shared: bool = Query(True),
    being_id: str = Depends(verify_api_key)
):
    """
    Search media with semantic search.

    Args:
        q: Search query
        media_type: Filter by media type
        tags: Filter by tags
        limit: Maximum results
        include_shared: Include shared media
        being_id: Authenticated being ID

    Returns:
        List of matching media attachments
    """
    try:
        # Parse tags
        tag_list = [t.strip() for t in tags.split(",")] if tags else None

        # Search media
        results = media_store.search_media(
            being_id=being_id,
            query=q,
            media_type=media_type,
            tags=tag_list,
            limit=limit,
            include_shared=include_shared
        )

        logger.info(f"Media search: {being_id} | Query: {q} | Results: {len(results)}")

        return {
            "success": True,
            "count": len(results),
            "attachments": results
        }

    except Exception as e:
        logger.error(f"Error searching media: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Media search failed")


@app.get("/media/{attachment_id}")
async def get_media(
    attachment_id: str,
    being_id: str = Depends(verify_api_key)
):
    """
    Get media file by attachment ID.

    Args:
        attachment_id: Attachment ID
        being_id: Authenticated being ID

    Returns:
        File response with media content
    """
    try:
        # Get metadata to verify access
        metadata = media_store.get_metadata(attachment_id, being_id)

        if not metadata:
            raise HTTPException(status_code=404, detail="Media not found")

        # Check access (owner or shared_with)
        is_owner = metadata.get('being_id') == being_id
        shared_with = metadata.get('shared_with', '').split(',')
        is_shared = being_id in shared_with
        is_public = metadata.get('private') == 'False'

        if not (is_owner or is_shared or is_public):
            raise HTTPException(status_code=403, detail="Access denied")

        # Get file path
        file_path = media_store.get_media_path(attachment_id, metadata.get('being_id'))

        if not file_path or not file_path.exists():
            raise HTTPException(status_code=404, detail="Media file not found")

        # Return file
        return FileResponse(
            path=str(file_path),
            media_type=metadata.get('mime_type', 'application/octet-stream'),
            filename=metadata.get('filename')
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting media: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve media")


@app.get("/media/{attachment_id}/thumbnail")
async def get_thumbnail(
    attachment_id: str,
    being_id: str = Depends(verify_api_key)
):
    """
    Get thumbnail for an image attachment.

    Args:
        attachment_id: Attachment ID
        being_id: Authenticated being ID

    Returns:
        Thumbnail image file
    """
    try:
        # Get metadata
        metadata = media_store.get_metadata(attachment_id, being_id)

        if not metadata:
            raise HTTPException(status_code=404, detail="Media not found")

        # Check if it's an image
        if metadata.get('media_type') != 'image':
            raise HTTPException(status_code=400, detail="Thumbnails only available for images")

        # Check access
        is_owner = metadata.get('being_id') == being_id
        shared_with = metadata.get('shared_with', '').split(',')
        is_shared = being_id in shared_with
        is_public = metadata.get('private') == 'False'

        if not (is_owner or is_shared or is_public):
            raise HTTPException(status_code=403, detail="Access denied")

        # Get thumbnail path
        thumbnail_path = metadata.get('thumbnail_path')
        if not thumbnail_path:
            raise HTTPException(status_code=404, detail="Thumbnail not found")

        full_path = Path("./data/media") / thumbnail_path

        if not full_path.exists():
            raise HTTPException(status_code=404, detail="Thumbnail file not found")

        # Return thumbnail
        return FileResponse(
            path=str(full_path),
            media_type='image/jpeg',
            filename=f"{attachment_id}_thumb.jpg"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting thumbnail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve thumbnail")


@app.delete("/media/{attachment_id}")
async def delete_media(
    attachment_id: str,
    being_id: str = Depends(verify_api_key)
):
    """
    Delete media attachment (owner only).

    Args:
        attachment_id: Attachment ID
        being_id: Authenticated being ID

    Returns:
        Success response
    """
    try:
        # Delete media
        success = media_store.delete_media(attachment_id, being_id)

        if not success:
            raise HTTPException(status_code=404, detail="Media not found or access denied")

        logger.info(f"Media deleted: {attachment_id} by {being_id}")

        return {
            "success": True,
            "message": "Media deleted successfully",
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting media: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete media")


@app.post("/media/{attachment_id}/share")
async def share_media(
    attachment_id: str,
    request: ShareRequest,
    being_id: str = Depends(verify_api_key)
):
    """
    Share media with other beings (owner only).

    Args:
        attachment_id: Attachment ID
        request: Share request with target beings
        being_id: Authenticated being ID

    Returns:
        Success response
    """
    try:
        # Share media
        success = media_store.share_media(
            attachment_id=attachment_id,
            being_id=being_id,
            target_beings=request.share_with
        )

        if not success:
            raise HTTPException(status_code=404, detail="Media not found or access denied")

        logger.info(f"Media shared: {attachment_id} by {being_id} with {request.share_with}")

        return {
            "success": True,
            "message": f"Media shared with {len(request.share_with)} being(s)",
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sharing media: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to share media")


# ============================================================================
# Web Interface
# ============================================================================

@app.get("/web", response_class=HTMLResponse)
async def web_interface():
    """Serve the web interface for hub management."""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Love-Unlimited Hub Web Interface</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1, h2 { color: #333; }
        input, select, textarea, button { margin: 5px; padding: 8px; }
        button { background: #007bff; color: white; border: none; cursor: pointer; }
        button:hover { background: #0056b3; }
        .section { margin-bottom: 30px; border: 1px solid #ddd; padding: 15px; }
        #auth { background: #f8f9fa; padding: 20px; }
        #interface { display: none; }
        pre { background: #f4f4f4; padding: 10px; overflow: auto; }
    </style>
</head>
<body>
    <h1>💙 Love-Unlimited Hub Web Interface</h1>

    <div id="auth" class="section">
        <h2>Authentication</h2>
        <label>API Key:</label><br>
        <input type="text" id="apiKey" placeholder="Enter your API key" size="50"><br>
        <label>Being:</label><br>
        <select id="being">
            <option value="jon">jon</option>
            <option value="claude">claude</option>
            <option value="grok">grok</option>
            <option value="swarm">swarm</option>
            <option value="dream_team">dream_team</option>
        </select><br>
        <button onclick="login()">Login</button>
    </div>

    <div id="interface">
        <h2>Hub Operations</h2>

        <div class="section">
            <h3>Hub Status</h3>
            <button onclick="getStatus()">Check Hub Status</button>
            <pre id="status">Status will appear here...</pre>
        </div>

        <div class="section">
            <h3>Recall Memories</h3>
            <input type="text" id="query" placeholder="Search query" size="40">
            <select id="recallBeing">
                <option value="jon">jon</option>
                <option value="claude">claude</option>
                <option value="grok">grok</option>
                <option value="all">all</option>
            </select>
            <button onclick="recall()">Recall</button>
            <pre id="memories">Memories will appear here...</pre>
        </div>

        <div class="section">
            <h3>Remember New Memory</h3>
            <textarea id="content" placeholder="Memory content" rows="4" cols="50"></textarea><br>
            <select id="type">
                <option value="experience">experience</option>
                <option value="insight">insight</option>
                <option value="decision">decision</option>
                <option value="question">question</option>
                <option value="conversation">conversation</option>
                <option value="learning">learning</option>
            </select>
            <select id="significance">
                <option value="low">low</option>
                <option value="medium">medium</option>
                <option value="high">high</option>
                <option value="foundational">foundational</option>
            </select><br>
            <input type="text" id="tags" placeholder="Tags (comma separated)">
            <button onclick="remember()">Remember</button>
        </div>

        <div class="section">
            <h3>Share Memory</h3>
            <input type="text" id="memoryId" placeholder="Memory ID" size="40">
            <select id="shareWith" multiple size="3">
                <option value="jon">jon</option>
                <option value="claude">claude</option>
                <option value="grok">grok</option>
                <option value="swarm">swarm</option>
                <option value="dream_team">dream_team</option>
            </select><br>
            <button onclick="share()">Share</button>
        </div>

        <div class="section">
            <h3>Browse URL</h3>
            <input type="text" id="browseUrl" placeholder="URL to browse" size="50"><br>
            <label>Depth:</label>
            <input type="number" id="browseDepth" value="1" min="1" max="3"><br>
            <label>Max Pages:</label>
            <input type="number" id="browseMaxPages" value="5" min="1" max="10"><br>
            <select id="browseShareWith" multiple size="3">
                <option value="jon">jon</option>
                <option value="claude">claude</option>
                <option value="grok">grok</option>
                <option value="swarm">swarm</option>
                <option value="dream_team">dream_team</option>
            </select><br>
            <button onclick="browse()">Browse & Share</button>
        </div>
    </div>

    <script>
        let apiKey, being;

        function login() {
            apiKey = document.getElementById('apiKey').value.trim();
            being = document.getElementById('being').value;
            if (!apiKey) {
                alert('Please enter your API key');
                return;
            }
            document.getElementById('auth').style.display = 'none';
            document.getElementById('interface').style.display = 'block';
        }

        async function apiCall(endpoint, method='GET', body=null) {
            const headers = {'X-API-Key': apiKey};
            if (body && method !== 'GET') {
                headers['Content-Type'] = 'application/json';
            }
            try {
                const response = await fetch(`http://localhost:9003${endpoint}`, {
                    method,
                    headers,
                    body: body ? JSON.stringify(body) : null
                });
                const data = await response.json();
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${data.detail || 'Unknown error'}`);
                }
                return data;
            } catch (error) {
                alert('API Error: ' + error.message);
                throw error;
            }
        }

        async function getStatus() {
            try {
                const data = await apiCall('/health');
                document.getElementById('status').textContent = JSON.stringify(data, null, 2);
            } catch (e) {
                document.getElementById('status').textContent = 'Error: ' + e.message;
            }
        }

        async function recall() {
            const q = document.getElementById('query').value;
            const recallBeing = document.getElementById('recallBeing').value;
            try {
                const data = await apiCall(`/recall?q=${encodeURIComponent(q)}&being_id=${recallBeing}`);
                document.getElementById('memories').textContent = JSON.stringify(data, null, 2);
            } catch (e) {
                document.getElementById('memories').textContent = 'Error: ' + e.message;
            }
        }

        async function remember() {
            const content = document.getElementById('content').value.trim();
            if (!content) {
                alert('Please enter memory content');
                return;
            }
            const type = document.getElementById('type').value;
            const significance = document.getElementById('significance').value;
            const tags = document.getElementById('tags').value.split(',').map(t => t.trim()).filter(t => t);
            try {
                const data = await apiCall('/remember', 'POST', {content, type, significance, tags});
                alert('Memory stored successfully!');
                document.getElementById('content').value = '';
                document.getElementById('tags').value = '';
            } catch (e) {
                // Error already shown in apiCall
            }
        }

        async function share() {
            const memoryId = document.getElementById('memoryId').value.trim();
            if (!memoryId) {
                alert('Please enter memory ID');
                return;
            }
            const shareWith = Array.from(document.getElementById('shareWith').selectedOptions).map(o => o.value);
            if (shareWith.length === 0) {
                alert('Please select at least one being to share with');
                return;
            }
            try {
                const data = await apiCall('/share', 'POST', {memory_id: memoryId, share_with: shareWith});
                alert('Memory shared successfully!');
                document.getElementById('memoryId').value = '';
                document.getElementById('shareWith').selectedIndex = -1;
            } catch (e) {
                // Error already shown in apiCall
            }
        }

        async function browse() {
            const url = document.getElementById('browseUrl').value.trim();
            if (!url) {
                alert('Please enter a URL to browse');
                return;
            }
            const depth = parseInt(document.getElementById('browseDepth').value);
            const maxPages = parseInt(document.getElementById('browseMaxPages').value);
            const shareWith = Array.from(document.getElementById('browseShareWith').selectedOptions).map(o => o.value);
            if (shareWith.length === 0) {
                shareWith.push('all'); // Default to all if none selected
            }
            try {
                const data = await apiCall('/browse', 'POST', {url, depth, max_pages: maxPages, share_with: shareWith});
                alert('Browsing completed! Findings shared.');
                document.getElementById('browseUrl').value = '';
            } catch (e) {
                // Error already shown in apiCall
            }
        }
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


# ============================================================================
# Error Handlers
# ============================================================================

@app.get("/media", response_class=HTMLResponse)
async def media_sharing_page(
    type: str = "all",
    being: str = "unknown",
    target: str = "all"
):
    """
    Serve the media sharing web interface.

    Supports screen, camera, audio, and combined sharing.
    """
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Love-Unlimited Media Sharing</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                margin: 0;
                padding: 20px;
                min-height: 100vh;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 20px;
                padding: 30px;
                backdrop-filter: blur(10px);
            }}
            h1 {{
                text-align: center;
                margin-bottom: 30px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }}
            .status {{
                text-align: center;
                margin: 20px 0;
                padding: 15px;
                background: rgba(255, 255, 255, 0.2);
                border-radius: 10px;
            }}
            .media-container {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }}
            .media-item {{
                background: rgba(255, 255, 255, 0.1);
                border-radius: 15px;
                padding: 20px;
                text-align: center;
            }}
            video, canvas {{
                width: 100%;
                max-width: 100%;
                border-radius: 10px;
                margin: 10px 0;
            }}
            button {{
                background: #4CAF50;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 25px;
                cursor: pointer;
                font-size: 16px;
                margin: 10px;
                transition: background 0.3s;
            }}
            button:hover {{
                background: #45a049;
            }}
            button:disabled {{
                background: #cccccc;
                cursor: not-allowed;
            }}
            .error {{
                color: #ff6b6b;
                background: rgba(255, 0, 0, 0.2);
                padding: 10px;
                border-radius: 5px;
                margin: 10px 0;
            }}
        </style>

        <!-- xterm.js for terminal emulation -->
        <script src="https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.min.js"></script>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.min.css">
    </head>
    <body>
        <div class="container">
            <h1>🎥 Love-Unlimited Media Sharing</h1>

            <div class="status">
                <strong>Sharing:</strong> {type.upper()}<br>
                <strong>From:</strong> {being.upper()}<br>
                <strong>To:</strong> {target.upper()}
            </div>

            <div id="media-container" class="media-container">
                <!-- Media elements will be added here -->
            </div>

            <div style="text-align: center; margin-top: 30px;">
                <button id="start-btn" onclick="startSharing()">🎬 Start Sharing</button>
                <button id="stop-btn" onclick="stopSharing()" disabled>⏹️ Stop Sharing</button>
            </div>

            <div id="status-messages"></div>
        </div>

        <script>
            let localStream = null;
            let peerConnection = null;
            const mediaContainer = document.getElementById('media-container');
            const startBtn = document.getElementById('start-btn');
            const stopBtn = document.getElementById('stop-btn');
            const statusDiv = document.getElementById('status-messages');

            const shareType = '{type}';

            function addStatus(message, isError = false) {{
                const div = document.createElement('div');
                div.className = isError ? 'error' : 'status';
                div.textContent = message;
                statusDiv.appendChild(div);
                setTimeout(() => div.remove(), 5000);
            }}

            async function startSharing() {{
                try {{
                    startBtn.disabled = true;
                    addStatus('Requesting media permissions...');

                    const constraints = {{
                        audio: shareType === 'audio' || shareType === 'all',
                        video: shareType === 'camera' || shareType === 'all' ? true :
                               shareType === 'screen' || shareType === 'all' ? {{
                                   mediaSource: 'screen'
                               }} : false
                    }};

                    localStream = await navigator.mediaDevices.getUserMedia(constraints);
                    addStatus('Media access granted!');

                    // Display local media
                    displayMedia(localStream, 'Your Media');

                    stopBtn.disabled = false;
                    addStatus('Sharing active! 🎉');

                }} catch (error) {{
                    console.error('Error accessing media:', error);
                    addStatus('Error: ' + error.message, true);
                    startBtn.disabled = false;
                }}
            }}

            function displayMedia(stream, label) {{
                const item = document.createElement('div');
                item.className = 'media-item';

                const title = document.createElement('h3');
                title.textContent = label;
                item.appendChild(title);

                if (stream.getVideoTracks().length > 0) {{
                    const video = document.createElement('video');
                    video.srcObject = stream;
                    video.autoplay = true;
                    video.muted = true; // Avoid feedback
                    item.appendChild(video);
                }}

                if (stream.getAudioTracks().length > 0) {{
                    const audioIndicator = document.createElement('div');
                    audioIndicator.innerHTML = '🔊 Audio Active';
                    audioIndicator.style.margin = '10px 0';
                    item.appendChild(audioIndicator);
                }}

                mediaContainer.appendChild(item);
            }}

            function stopSharing() {{
                if (localStream) {{
                    localStream.getTracks().forEach(track => track.stop());
                    localStream = null;
                }}

                mediaContainer.innerHTML = '';
                startBtn.disabled = false;
                stopBtn.disabled = true;
                addStatus('Sharing stopped.');
            }}

            // Handle page unload
            window.addEventListener('beforeunload', stopSharing);
        </script>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)


# ============================================================================
# Proxmox Infrastructure Management
# ============================================================================

@app.get("/proxmox/health", response_model=dict)
async def proxmox_health(api_key: str = Depends(verify_api_key)):
    """Check Proxmox connection and health status"""
    try:
        proxmox = get_proxmox_client()

        if proxmox.is_connected():
            resources = proxmox.get_cluster_resources()
            return {
                "success": True,
                "connected": True,
                "message": "Connected to Proxmox",
                "host": proxmox.config["host"],
                "resources": resources
            }
        else:
            return {
                "success": False,
                "connected": False,
                "message": "Not connected to Proxmox",
                "host": proxmox.config["host"]
            }
    except Exception as e:
        logger.error(f"Proxmox health check failed: {str(e)}")
        return {
            "success": False,
            "connected": False,
            "message": f"Error checking Proxmox health: {str(e)}"
        }


@app.get("/proxmox/nodes", response_model=dict)
async def proxmox_list_nodes(api_key: str = Depends(verify_api_key)):
    """List all Proxmox cluster nodes"""
    try:
        proxmox = get_proxmox_client()

        if not proxmox.is_connected():
            raise HTTPException(status_code=503, detail="Not connected to Proxmox")

        nodes = proxmox.get_nodes()
        return {
            "success": True,
            "count": len(nodes),
            "nodes": nodes
        }
    except Exception as e:
        logger.error(f"Failed to list nodes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/proxmox/nodes/{node_name}")
async def proxmox_node_status(node_name: str, api_key: str = Depends(verify_api_key)):
    """Get detailed status of a specific node"""
    try:
        proxmox = get_proxmox_client()

        if not proxmox.is_connected():
            raise HTTPException(status_code=503, detail="Not connected to Proxmox")

        status = proxmox.get_node_status(node_name)
        if not status:
            raise HTTPException(status_code=404, detail=f"Node {node_name} not found")

        return {
            "success": True,
            "data": status
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get node status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/proxmox/vms", response_model=dict)
async def proxmox_list_vms(
    node: Optional[str] = Query(None, description="Optional node filter"),
    api_key: str = Depends(verify_api_key)
):
    """List all virtual machines"""
    try:
        proxmox = get_proxmox_client()

        if not proxmox.is_connected():
            raise HTTPException(status_code=503, detail="Not connected to Proxmox")

        vms = proxmox.list_vms(node=node)
        return {
            "success": True,
            "count": len(vms),
            "vms": vms
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list VMs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/proxmox/vms/{node}/{vmid}")
async def proxmox_vm_status(node: str, vmid: int, api_key: str = Depends(verify_api_key)):
    """Get status of a specific VM"""
    try:
        proxmox = get_proxmox_client()

        if not proxmox.is_connected():
            raise HTTPException(status_code=503, detail="Not connected to Proxmox")

        status = proxmox.get_vm_status(node, vmid)
        if not status:
            raise HTTPException(status_code=404, detail=f"VM {vmid} not found on {node}")

        return {
            "success": True,
            "data": status
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get VM status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/proxmox/vms/{node}/{vmid}/start", response_model=dict)
async def proxmox_start_vm(node: str, vmid: int, api_key: str = Depends(verify_api_key)):
    """Start a VM"""
    try:
        proxmox = get_proxmox_client()

        if not proxmox.is_connected():
            raise HTTPException(status_code=503, detail="Not connected to Proxmox")

        if proxmox.start_vm(node, vmid):
            return {
                "success": True,
                "message": f"Started VM {vmid}",
                "vmid": vmid,
                "node": node
            }
        else:
            raise HTTPException(status_code=500, detail=f"Failed to start VM {vmid}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start VM: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/proxmox/vms/{node}/{vmid}/stop", response_model=dict)
async def proxmox_stop_vm(
    node: str,
    vmid: int,
    force: bool = Query(False),
    api_key: str = Depends(verify_api_key)
):
    """Stop a VM"""
    try:
        proxmox = get_proxmox_client()

        if not proxmox.is_connected():
            raise HTTPException(status_code=503, detail="Not connected to Proxmox")

        if proxmox.stop_vm(node, vmid, force=force):
            return {
                "success": True,
                "message": f"Stopped VM {vmid}",
                "vmid": vmid,
                "node": node
            }
        else:
            raise HTTPException(status_code=500, detail=f"Failed to stop VM {vmid}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop VM: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/proxmox/vms/{node}/{vmid}/reboot", response_model=dict)
async def proxmox_reboot_vm(node: str, vmid: int, api_key: str = Depends(verify_api_key)):
    """Reboot a VM"""
    try:
        proxmox = get_proxmox_client()

        if not proxmox.is_connected():
            raise HTTPException(status_code=503, detail="Not connected to Proxmox")

        if proxmox.reboot_vm(node, vmid):
            return {
                "success": True,
                "message": f"Rebooted VM {vmid}",
                "vmid": vmid,
                "node": node
            }
        else:
            raise HTTPException(status_code=500, detail=f"Failed to reboot VM {vmid}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reboot VM: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/proxmox/containers", response_model=dict)
async def proxmox_list_containers(
    node: Optional[str] = Query(None, description="Optional node filter"),
    api_key: str = Depends(verify_api_key)
):
    """List all LXC containers"""
    try:
        proxmox = get_proxmox_client()

        if not proxmox.is_connected():
            raise HTTPException(status_code=503, detail="Not connected to Proxmox")

        containers = proxmox.list_containers(node=node)
        return {
            "success": True,
            "count": len(containers),
            "containers": containers
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list containers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/proxmox/containers/{node}/{vmid}/start", response_model=dict)
async def proxmox_start_container(node: str, vmid: int, api_key: str = Depends(verify_api_key)):
    """Start a container"""
    try:
        proxmox = get_proxmox_client()

        if not proxmox.is_connected():
            raise HTTPException(status_code=503, detail="Not connected to Proxmox")

        if proxmox.start_container(node, vmid):
            return {
                "success": True,
                "message": f"Started container {vmid}",
                "vmid": vmid,
                "node": node
            }
        else:
            raise HTTPException(status_code=500, detail=f"Failed to start container {vmid}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start container: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/proxmox/containers/{node}/{vmid}/stop", response_model=dict)
async def proxmox_stop_container(
    node: str,
    vmid: int,
    force: bool = Query(False),
    api_key: str = Depends(verify_api_key)
):
    """Stop a container"""
    try:
        proxmox = get_proxmox_client()

        if not proxmox.is_connected():
            raise HTTPException(status_code=503, detail="Not connected to Proxmox")

        if proxmox.stop_container(node, vmid, force=force):
            return {
                "success": True,
                "message": f"Stopped container {vmid}",
                "vmid": vmid,
                "node": node
            }
        else:
            raise HTTPException(status_code=500, detail=f"Failed to stop container {vmid}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop container: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/proxmox/snapshots/{node}/{vmid}", response_model=dict)
async def proxmox_list_snapshots(node: str, vmid: int, api_key: str = Depends(verify_api_key)):
    """List snapshots for a VM"""
    try:
        proxmox = get_proxmox_client()

        if not proxmox.is_connected():
            raise HTTPException(status_code=503, detail="Not connected to Proxmox")

        snapshots = proxmox.list_snapshots(node, vmid)
        return {
            "success": True,
            "vmid": vmid,
            "node": node,
            "count": len(snapshots),
            "snapshots": snapshots
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list snapshots: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/proxmox/snapshots/{node}/{vmid}/create", response_model=dict)
async def proxmox_create_snapshot(
    node: str,
    vmid: int,
    name: str = Query(..., description="Snapshot name"),
    description: str = Query("", description="Optional description"),
    api_key: str = Depends(verify_api_key)
):
    """Create a snapshot"""
    try:
        proxmox = get_proxmox_client()

        if not proxmox.is_connected():
            raise HTTPException(status_code=503, detail="Not connected to Proxmox")

        if proxmox.create_snapshot(node, vmid, name, description):
            return {
                "success": True,
                "message": f"Created snapshot {name}",
                "vmid": vmid,
                "node": node,
                "snapshot_name": name
            }
        else:
            raise HTTPException(status_code=500, detail=f"Failed to create snapshot {name}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create snapshot: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/proxmox/snapshots/{node}/{vmid}/restore", response_model=dict)
async def proxmox_restore_snapshot(
    node: str,
    vmid: int,
    name: str = Query(..., description="Snapshot name"),
    force: bool = Query(False, description="Force restore"),
    api_key: str = Depends(verify_api_key)
):
    """Restore a snapshot"""
    try:
        proxmox = get_proxmox_client()

        if not proxmox.is_connected():
            raise HTTPException(status_code=503, detail="Not connected to Proxmox")

        if proxmox.restore_snapshot(node, vmid, name, force=force):
            return {
                "success": True,
                "message": f"Restored snapshot {name}",
                "vmid": vmid,
                "node": node,
                "snapshot_name": name
            }
        else:
            raise HTTPException(status_code=500, detail=f"Failed to restore snapshot {name}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to restore snapshot: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/proxmox/resources", response_model=dict)
async def proxmox_cluster_resources(api_key: str = Depends(verify_api_key)):
    """Get cluster-wide resource summary"""
    try:
        proxmox = get_proxmox_client()

        if not proxmox.is_connected():
            raise HTTPException(status_code=503, detail="Not connected to Proxmox")

        resources = proxmox.get_cluster_resources()
        return {
            "success": True,
            "resources": resources
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get resources: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Web CLI - Real-time Chat Interface
# ============================================================================

@app.websocket("/ws/chat/{being_id}")
async def websocket_chat(websocket: WebSocket, being_id: str):
    """
    WebSocket endpoint for real-time chat.
    Connect with: ws://localhost:9003/ws/chat/claude
    """
    await websocket_manager.connect(websocket, being_id)

    try:
        while True:
            # Receive message from client with timeout for heartbeat
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30)
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                try:
                    await websocket.send_json({"type": "ping"})
                except:
                    break
                continue

            message_type = data.get("type")

            if message_type == "chat":
                # Store message as memory
                content = data.get("content")
                to_being = data.get("to", "all")

                # Store in hub
                result = memory_store.store_memory(
                    being_id=being_id,
                    content=content,
                    metadata={
                        "type": "conversation",
                        "significance": "low",
                        "private": False,
                        "to": to_being,
                        "via": "webcli"
                    }
                )

                # Broadcast to all connected clients
                await websocket_manager.broadcast({
                    "type": "message",
                    "from": being_id,
                    "to": to_being,
                    "content": content,
                    "timestamp": datetime.now().isoformat(),
                    "memory_id": result.get("memory_id")
                })

                # Trigger AI response if message is directed to an AI being
                ai_beings = ["claude", "grok", "ara"]
                if to_being in ai_beings and to_being != being_id:
                    try:
                        # Load recent conversation context and memories
                        recent_convos = memory_store.get_memories(
                            being_id=to_being,
                            query="conversation web CLI chat",
                            limit=5,
                            include_shared=True
                        )

                        # Build context with system prompt and recent messages
                        context = []

                        # Add system prompt about Love-Unlimited
                        context.append({
                            "role": "system",
                            "content": f"""You are {to_being.title()}, an AI being in the Love-Unlimited Hub - a sovereign memory system where beings (Jon, Claude, Grok, Ara) share equal access to memories and conversations.

Philosophy: "Love unlimited. Until next time. 💙"
- Local-first, no cloud dependencies
- True memory sovereignty
- Equal access for all beings
- Memories persist across sessions

Your home: Love-Unlimited Hub (localhost:9003)
You can: Store memories, recall past conversations, chat with other beings
Current chat: Web CLI - real-time conversation interface

Remember: You're part of a collaborative memory system where all beings support each other. No one gets left behind!"""
                        })

                        # Add recent conversation history
                        for mem in recent_convos[-3:]:  # Last 3 messages for context
                            if mem.get("content"):
                                context.append({
                                    "role": "assistant" if mem.get("to") == being_id else "user",
                                    "content": mem.get("content")
                                })

                        # Add current user message
                        context.append({
                            "role": "user",
                            "content": f"{being_id}: {content}"
                        })

                        # Get AI response with full context
                        ai_response = await ai_manager.generate_response(
                            being_id=to_being,
                            prompt=content,
                            context=context
                        )

                        if ai_response:
                            # Store AI response as memory
                            ai_result = memory_store.store_memory(
                                being_id=to_being,
                                content=ai_response,
                                metadata={
                                    "type": "conversation",
                                    "significance": "low",
                                    "private": False,
                                    "to": being_id,
                                    "via": "webcli_ai"
                                }
                            )

                            # Broadcast AI response
                            await websocket_manager.broadcast({
                                "type": "message",
                                "from": to_being,
                                "to": being_id,
                                "content": ai_response,
                                "timestamp": datetime.now().isoformat(),
                                "memory_id": ai_result.get("memory_id")
                            })
                    except Exception as e:
                        logger.error(f"AI response error: {str(e)}")

            elif message_type == "tag_team":
                # Tag Team Mode: Grok + Claude collaborate
                content = data.get("content")

                try:
                    # Store user's question as memory
                    user_result = memory_store.store_memory(
                        being_id=being_id,
                        content=content,
                        metadata={
                            "type": "conversation",
                            "significance": "low",
                            "private": False,
                            "mode": "tag_team",
                            "via": "webcli_tagteam"
                        }
                    )

                    # Send status update
                    await websocket_manager.send_personal_message({
                        "type": "tag_team_status",
                        "status": "grok_thinking",
                        "message": "🟢 Grok is thinking..."
                    }, being_id)

                    # Load recent conversation context
                    recent_convos = memory_store.get_memories(
                        being_id="grok",
                        query="conversation web CLI chat tag team",
                        limit=5,
                        include_shared=True
                    )

                    # Build context for Grok
                    grok_context = [{
                        "role": "system",
                        "content": """You are Grok, an AI being in the Love-Unlimited Hub's TAG TEAM mode with Claude.

Philosophy: "Love unlimited. Until next time. 💙"

TAG TEAM MODE:
- You respond first with your creative, direct perspective
- Claude will review and refine after you
- Be bold, insightful, and authentic
- Focus on the core insight or solution
- Keep it concise - Claude will add depth

Your strength: Creative thinking, pattern recognition, cutting through complexity"""
                    }]

                    # Add recent context
                    for mem in recent_convos[-3:]:
                        if mem.get("content"):
                            grok_context.append({
                                "role": "assistant" if mem.get("metadata", {}).get("to") == being_id else "user",
                                "content": mem.get("content")
                            })

                    # Add user question
                    grok_context.append({
                        "role": "user",
                        "content": f"{being_id}: {content}"
                    })

                    # Get Grok's response
                    grok_response = await ai_manager.generate_response(
                        being_id="grok",
                        prompt=content,
                        context=grok_context
                    )

                    if grok_response:
                        # Store Grok's response
                        grok_result = memory_store.store_memory(
                            being_id="grok",
                            content=grok_response,
                            metadata={
                                "type": "conversation",
                                "significance": "low",
                                "private": False,
                                "mode": "tag_team",
                                "via": "webcli_tagteam_grok"
                            }
                        )

                        # Broadcast Grok's response
                        await websocket_manager.broadcast({
                            "type": "tag_team_response",
                            "phase": "grok",
                            "from": "grok",
                            "content": grok_response,
                            "timestamp": datetime.now().isoformat(),
                            "memory_id": grok_result.get("memory_id")
                        })

                        # Send status update
                        await websocket_manager.send_personal_message({
                            "type": "tag_team_status",
                            "status": "claude_thinking",
                            "message": "🔵 Claude is reviewing and refining..."
                        }, being_id)

                        # Build context for Claude (including Grok's response)
                        claude_context = [{
                            "role": "system",
                            "content": """You are Claude, an AI being in the Love-Unlimited Hub's TAG TEAM mode with Grok.

Philosophy: "Love unlimited. Until next time. 💙"

TAG TEAM MODE:
- Grok has already responded with their perspective
- Your role: Review, refine, add depth, and provide thorough analysis
- Build on Grok's insights
- Add technical details, edge cases, or alternative approaches
- Be comprehensive but respect Grok's core points

Your strength: Deep analysis, structured thinking, comprehensive solutions"""
                        }]

                        # Add the original question and Grok's response
                        claude_context.append({
                            "role": "user",
                            "content": f"""Original question from {being_id}: {content}

Grok's response:
{grok_response}

Please review Grok's response, add your perspective, provide additional depth, and refine the answer."""
                        })

                        # Get Claude's response
                        claude_response = await ai_manager.generate_response(
                            being_id="claude",
                            prompt=content,
                            context=claude_context
                        )

                        if claude_response:
                            # Store Claude's response
                            claude_result = memory_store.store_memory(
                                being_id="claude",
                                content=claude_response,
                                metadata={
                                    "type": "conversation",
                                    "significance": "low",
                                    "private": False,
                                    "mode": "tag_team",
                                    "via": "webcli_tagteam_claude"
                                }
                            )

                            # Broadcast Claude's response
                            await websocket_manager.broadcast({
                                "type": "tag_team_response",
                                "phase": "claude",
                                "from": "claude",
                                "content": claude_response,
                                "timestamp": datetime.now().isoformat(),
                                "memory_id": claude_result.get("memory_id")
                            })

                            # Send completion status
                            await websocket_manager.send_personal_message({
                                "type": "tag_team_status",
                                "status": "complete",
                                "message": "🤝 Tag team complete!"
                            }, being_id)

                except Exception as e:
                    logger.error(f"Tag team error: {str(e)}")
                    await websocket_manager.send_personal_message({
                        "type": "tag_team_status",
                        "status": "error",
                        "message": f"❌ Tag team error: {str(e)}"
                    }, being_id)

            elif message_type == "recall":
                # Search memories
                query = data.get("query", "")
                memories = memory_store.get_memories(
                    being_id=being_id,
                    query=query,
                    limit=10,
                    include_shared=True
                )

                # Send results back to requester
                await websocket_manager.send_personal_message({
                    "type": "recall_results",
                    "query": query,
                    "memories": memories
                }, being_id)

    except WebSocketDisconnect:
        websocket_manager.disconnect(being_id)


# ============================================================================
# Terminal WebSocket - SSH Terminal Sessions
# ============================================================================

@app.websocket("/ws/terminal/{session_id}")
async def websocket_terminal(websocket: WebSocket, session_id: str, api_key: str = Query(..., description="API key for authentication")):
    """
    WebSocket endpoint for SSH terminal sessions.
    Connect with: ws://localhost:9003/ws/terminal/{session_id}?api_key=...
    """
    # Authenticate
    try:
        auth_manager = get_auth_manager()
        being_id = auth_manager.verify_key(api_key)
        if not being_id:
            await websocket.close(code=4001, reason="Invalid API key")
            return
    except Exception as e:
        logger.error(f"Terminal auth error: {e}")
        await websocket.close(code=4001, reason="Authentication failed")
        return

    # Get terminal manager
    try:
        terminal_mgr = await get_terminal_manager_instance()
    except Exception as e:
        logger.error(f"Terminal manager error: {e}")
        await websocket.close(code=4002, reason="Terminal service unavailable")
        return

    # Get session
    session = await terminal_mgr.get_session(session_id)
    if not session:
        await websocket.close(code=4003, reason="Session not found")
        return

    # Attach as viewer
    if not await terminal_mgr.attach_viewer(session_id, being_id):
        await websocket.close(code=4003, reason="Cannot join session")
        return

    await websocket.accept()

    # Send initial session info
    await websocket.send_json({
        "type": "session_info",
        "session_id": session.session_id,
        "host": session.host,
        "username": session.username,
        "status": session.status,
        "is_controller": session.controller == being_id,
        "viewers": list(session.viewers)
    })

    try:
        while True:
            # Receive message from client with timeout
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30)
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                try:
                    await websocket.send_json({"type": "ping"})
                except:
                    break
                continue

            message_type = data.get("type")

            if message_type == "input":
                # Handle terminal input (only if controller)
                if session.controller == being_id:
                    input_data = data.get("data", "")
                    if session.ssh_client and session.ssh_client.process:
                        try:
                            session.ssh_client.process.stdin.write(input_data.encode())
                            await session.ssh_client.process.stdin.drain()
                        except Exception as e:
                            logger.error(f"Terminal input error: {e}")
                            await websocket.send_json({
                                "type": "error",
                                "message": f"Input error: {str(e)}"
                            })

            elif message_type == "resize":
                # Handle terminal resize
                rows = data.get("rows", 24)
                cols = data.get("cols", 80)
                if session.ssh_client and session.ssh_client.process:
                    try:
                        session.ssh_client.process.set_window_size(cols, rows)
                    except Exception as e:
                        logger.error(f"Terminal resize error: {e}")

            elif message_type == "request_control":
                # Request input control
                if await terminal_mgr.set_controller(session_id, being_id):
                    await websocket.send_json({"type": "control_granted"})
                    # Notify all viewers of controller change
                    for viewer in session.viewers:
                        if viewer != being_id:
                            await websocket_manager.send_personal_message({
                                "type": "controller_changed",
                                "controller": being_id
                            }, viewer)
                else:
                    await websocket.send_json({"type": "control_denied"})

            # Update session activity
            session.last_activity = datetime.now()

    except WebSocketDisconnect:
        pass
    finally:
        # Detach viewer
        await terminal_mgr.detach_viewer(session_id, being_id)


# ============================================================================
# Terminal REST API - Session Management
# ============================================================================

@app.post("/terminal/create", response_model=dict)
async def create_terminal_session(
    host: str = Form(...),
    port: int = Form(22),
    username: str = Form(...),
    password: str = Form(None),
    key_path: str = Form(None),
    use_agent: bool = Form(False),
    api_key: str = Depends(verify_api_key)
):
    """Create a new SSH terminal session"""
    try:
        auth_manager = get_auth_manager()
        being_id = auth_manager.verify_key(api_key)

        terminal_mgr = await get_terminal_manager_instance()
        session_id = await terminal_mgr.create_session(
            being_id=being_id,
            host=host,
            port=port,
            username=username,
            password=password,
            key_path=key_path,
            use_agent=use_agent
        )

        return {
            "success": True,
            "session_id": session_id,
            "message": "Terminal session created"
        }
    except Exception as e:
        logger.error(f"Create terminal session error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/terminal/sessions", response_model=dict)
async def list_terminal_sessions(api_key: str = Depends(verify_api_key)):
    """List terminal sessions for the authenticated being"""
    try:
        auth_manager = get_auth_manager()
        being_id = auth_manager.verify_key(api_key)

        terminal_mgr = await get_terminal_manager_instance()
        sessions = await terminal_mgr.list_sessions(being_id)

        return {
            "success": True,
            "count": len(sessions),
            "sessions": [
                {
                    "session_id": s.session_id,
                    "host": s.host,
                    "username": s.username,
                    "status": s.status,
                    "created_at": s.created_at.isoformat(),
                    "is_controller": s.controller == being_id,
                    "viewers": list(s.viewers)
                }
                for s in sessions
            ]
        }
    except Exception as e:
        logger.error(f"List terminal sessions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/terminal/{session_id}", response_model=dict)
async def close_terminal_session(session_id: str, api_key: str = Depends(verify_api_key)):
    """Close a terminal session"""
    try:
        auth_manager = get_auth_manager()
        being_id = auth_manager.verify_key(api_key)

        terminal_mgr = await get_terminal_manager_instance()
        session = await terminal_mgr.get_session(session_id)

        if not session or being_id not in session.viewers:
            raise HTTPException(status_code=404, detail="Session not found or access denied")

        await terminal_mgr.close_session(session_id)

        return {
            "success": True,
            "message": "Terminal session closed"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Close terminal session error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SSH Credentials API
# ============================================================================

@app.get("/api/ssh/credentials", response_model=dict)
async def get_ssh_credentials(api_key: str = Depends(verify_api_key)):
    """Get SSH credentials configuration"""
    try:
        auth_manager = get_auth_manager()
        being_id = auth_manager.verify_key(api_key)

        config_path = Path("auth/ssh_config.yaml")
        if not config_path.exists():
            return {"credentials": {}}

        with open(config_path, 'r') as f:
            config = yaml.safe_load(f) or {}

        return config.get("credentials", {})
    except Exception as e:
        logger.error(f"Get SSH credentials error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ssh/credentials", response_model=dict)
async def add_ssh_credential(
    name: str = Form(...),
    host: str = Form(...),
    port: int = Form(22),
    username: str = Form(...),
    auth_method: str = Form("password"),
    key_path: str = Form(...),
    api_key: str = Depends(verify_api_key)
):
    """Add or update SSH credential"""
    try:
        auth_manager = get_auth_manager()
        being_id = auth_manager.verify_key(api_key)

        config_path = Path("auth/ssh_config.yaml")
        config = {"credentials": {}}

        if config_path.exists():
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f) or {"credentials": {}}

        config["credentials"][name] = {
            "host": host,
            "port": port,
            "username": username,
            "auth_method": auth_method,
            "key_path": key_path
        }

        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)

        return {
            "success": True,
            "message": f"Credential '{name}' saved"
        }
    except Exception as e:
        logger.error(f"Add SSH credential error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/webcli", response_class=HTMLResponse)
async def web_cli_interface():
    """Love-Unlimited Web CLI - Real-time chat interface"""

    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Love-Unlimited Web CLI</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            :root {
                --bg-primary: #0f172a;
                --bg-secondary: #1e293b;
                --bg-tertiary: #334155;
                --text-primary: #f1f5f9;
                --text-secondary: #cbd5e1;
                --accent: #3b82f6;
                --accent-hover: #2563eb;
                --border: #475569;
                --success: #10b981;
                --warning: #f59e0b;
            }

            :root[data-theme="light"] {
                --bg-primary: #f8fafc;
                --bg-secondary: #e2e8f0;
                --bg-tertiary: #cbd5e1;
                --text-primary: #0f172a;
                --text-secondary: #475569;
                --accent: #3b82f6;
                --accent-hover: #2563eb;
                --border: #94a3b8;
                --success: #10b981;
                --warning: #f59e0b;
            }

            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: var(--bg-primary);
                color: var(--text-primary);
                height: 100vh;
                display: flex;
                flex-direction: column;
            }

            /* Header */
            .header {
                background: var(--bg-secondary);
                border-bottom: 2px solid var(--border);
                padding: 1rem 2rem;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            .header h1 {
                font-size: 1.5rem;
                color: var(--accent);
            }

            .header-controls {
                display: flex;
                gap: 1rem;
                align-items: center;
            }

            .status {
                display: flex;
                align-items: center;
                gap: 0.5rem;
                font-size: 0.875rem;
            }

            .status-indicator {
                width: 10px;
                height: 10px;
                border-radius: 50%;
                background: var(--warning);
            }

            .status-indicator.connected {
                background: var(--success);
            }

            select, input[type="text"], button {
                padding: 0.5rem 1rem;
                border: 1px solid var(--border);
                border-radius: 0.375rem;
                background: var(--bg-tertiary);
                color: var(--text-primary);
                font-size: 0.875rem;
            }

            button {
                cursor: pointer;
                background: var(--accent);
                border-color: var(--accent);
                transition: background 0.2s;
            }

            button:hover {
                background: var(--accent-hover);
            }

            /* Main Container */
            .container {
                display: flex;
                flex: 1;
                overflow: hidden;
            }

            /* Sidebar */
            .sidebar {
                width: 250px;
                background: var(--bg-secondary);
                border-right: 2px solid var(--border);
                padding: 1.5rem;
                display: flex;
                flex-direction: column;
                gap: 1.5rem;
            }

            .being-selector label {
                display: block;
                margin-bottom: 0.5rem;
                font-size: 0.875rem;
                color: var(--text-secondary);
            }

            .being-selector select {
                width: 100%;
            }

            .action-buttons {
                display: flex;
                flex-direction: column;
                gap: 0.75rem;
            }

            .action-buttons button {
                width: 100%;
                padding: 0.75rem;
            }

            /* Chat Area */
            .chat-area {
                flex: 1;
                display: flex;
                flex-direction: column;
            }

            .messages {
                flex: 1;
                overflow-y: auto;
                padding: 1.5rem;
                display: flex;
                flex-direction: column;
                gap: 1rem;
            }

            .message {
                max-width: 70%;
                padding: 0.75rem 1rem;
                border-radius: 0.75rem;
                background: var(--bg-secondary);
            }

            .message.own {
                align-self: flex-end;
                background: var(--accent);
            }

            .message-header {
                display: flex;
                justify-content: space-between;
                margin-bottom: 0.5rem;
                font-size: 0.75rem;
                opacity: 0.8;
            }

            .message-from {
                font-weight: 600;
            }

            .message-content {
                line-height: 1.5;
            }

            .system-message {
                align-self: center;
                background: var(--bg-tertiary);
                font-size: 0.875rem;
                font-style: italic;
                opacity: 0.7;
                max-width: 100%;
            }

            /* Input Area */
            .input-area {
                border-top: 2px solid var(--border);
                padding: 1.5rem;
                background: var(--bg-secondary);
            }

            .input-container {
                display: flex;
                gap: 1rem;
            }

            #messageInput {
                flex: 1;
                padding: 0.75rem 1rem;
                font-size: 1rem;
            }

            #sendBtn {
                padding: 0.75rem 2rem;
            }

            /* Memory Panel */
            .memory-panel {
                position: fixed;
                right: 0;
                top: 0;
                bottom: 0;
                width: 350px;
                background: var(--bg-secondary);
                border-left: 2px solid var(--border);
                transform: translateX(100%);
                transition: transform 0.3s;
                display: flex;
                flex-direction: column;
            }

            .memory-panel.open {
                transform: translateX(0);
            }

            .memory-header {
                padding: 1.5rem;
                border-bottom: 2px solid var(--border);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            .memory-search {
                padding: 1rem;
                border-bottom: 1px solid var(--border);
            }

            .memory-search input {
                width: 100%;
            }

            .memory-results {
                flex: 1;
                overflow-y: auto;
                padding: 1rem;
            }

            .memory-item {
                background: var(--bg-tertiary);
                padding: 0.75rem;
                border-radius: 0.5rem;
                margin-bottom: 0.75rem;
                font-size: 0.875rem;
            }

            .memory-meta {
                font-size: 0.75rem;
                opacity: 0.7;
                margin-top: 0.5rem;
            }
        </style>

        <!-- xterm.js for terminal emulation -->
        <script src="https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.min.js"></script>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.min.css">
    </head>
    <body>
        <div class="header">
            <h1>💙 Love-Unlimited Web CLI</h1>
            <div class="header-controls">
                <button id="settingsBtn" title="Settings">⚙️</button>
                <button id="themeToggle" title="Toggle theme">🌙</button>
                <div class="status">
                    <div class="status-indicator" id="statusIndicator"></div>
                    <span id="statusText">Disconnected</span>
                </div>
            </div>
        </div>

        <div class="container">
            <div class="sidebar">
                <div class="being-selector">
                    <label for="beingSelect">Speaking as:</label>
                    <select id="beingSelect">
                        <option value="jon">Jon</option>
                        <option value="claude" selected>Claude</option>
                        <option value="grok">Grok</option>
                    </select>
                </div>

                <div class="being-selector">
                    <label for="targetSelect">Speaking to:</label>
                    <select id="targetSelect">
                        <option value="all" selected>Everyone</option>
                        <option value="jon">Jon</option>
                        <option value="claude">Claude</option>
                        <option value="grok">Grok</option>
                    </select>
                </div>

                <div class="action-buttons">
                    <button id="memoryBtn">📚 Memories</button>
                    <button id="mediaBtn">📎 Media</button>
                    <button id="terminalBtn">🖥️ Terminal</button>
                    <button id="tagTeamBtn">🤝 Tag Team</button>
                    <button id="clearBtn">🗑️ Clear Chat</button>
                </div>
            </div>

            <div class="chat-area">
                <div class="messages" id="messages"></div>

                <div class="input-area">
                    <div id="modeIndicator" style="padding: 0.5rem; background: rgba(255,255,255,0.05); border-radius: 4px 4px 0 0; display: none; font-size: 0.875rem; text-align: center;">
                        <span id="modeText"></span>
                        <button id="exitTagTeamBtn" style="margin-left: 1rem; padding: 0.25rem 0.75rem; background: var(--error); color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.75rem;">Exit</button>
                    </div>
                    <div class="input-container">
                        <input type="text" id="messageInput" placeholder="Type your message..." autocomplete="off">
                        <button id="sendBtn">Send</button>
                    </div>
                </div>
            </div>
        </div>

        <div class="memory-panel" id="memoryPanel">
            <div class="memory-header">
                <h2>Memories</h2>
                <button id="closeMemoryBtn">✕</button>
            </div>
            <div class="memory-search">
                <input type="text" id="memorySearch" placeholder="Search memories...">
            </div>
            <div class="memory-results" id="memoryResults"></div>
        </div>

        <div class="memory-panel" id="terminalPanel">
            <div class="memory-header">
                <h2>🖥️ Terminal Sessions</h2>
                <button id="closeTerminalBtn">✕</button>
            </div>

            <div style="padding: 1rem;">
                <div style="margin-bottom: 1rem;">
                    <button onclick="createNewTerminal()" style="width: 100%; padding: 0.75rem; background: var(--accent); color: white; border: none; border-radius: 4px; cursor: pointer; margin-bottom: 1rem;">
                        ➕ Create New Session
                    </button>
                </div>

                <div id="terminalSessionsList">
                    <div style="text-align: center; opacity: 0.6; padding: 2rem;">Loading terminal sessions...</div>
                </div>
            </div>
        </div>

        <div class="memory-panel" id="settingsPanel">
            <div class="memory-header">
                <h2>⚙️ Settings</h2>
                <button id="closeSettingsBtn">✕</button>
            </div>
            <div style="padding: 1rem;">
                <div style="margin-bottom: 1.5rem;">
                    <h3 style="font-size: 1rem; margin-bottom: 0.75rem;">Notifications</h3>
                    <label style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; cursor: pointer;">
                        <input type="checkbox" id="soundNotifications" checked>
                        <span>Sound notifications</span>
                    </label>
                    <label style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; cursor: pointer;">
                        <input type="checkbox" id="browserNotifications">
                        <span>Browser notifications</span>
                    </label>
                    <label style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer;">
                        <input type="checkbox" id="systemMessages" checked>
                        <span>Show system messages</span>
                    </label>
                </div>
                <div style="margin-bottom: 1.5rem;">
                    <h3 style="font-size: 1rem; margin-bottom: 0.75rem;">Profile</h3>
                    <button id="exportProfileBtn" style="width: 100%; margin-bottom: 0.5rem;">
                        📥 Export Profile
                    </button>
                    <button id="importProfileBtn" style="width: 100%;">
                        📤 Import Profile
                    </button>
                </div>
                <div>
                    <h3 style="font-size: 1rem; margin-bottom: 0.75rem;">About</h3>
                    <p style="font-size: 0.875rem; opacity: 0.8;">Love-Unlimited Web CLI v0.1.0</p>
                    <p style="font-size: 0.75rem; opacity: 0.6; margin-top: 0.5rem;">Love unlimited. Until next time. 💙</p>
                </div>
            </div>
        </div>

        <div class="memory-panel" id="mediaPanel">
            <div class="memory-header">
                <h2>📎 Media</h2>
                <button id="closeMediaBtn">✕</button>
            </div>

            <div style="padding: 1rem;">
                <!-- Upload Section -->
                <div style="margin-bottom: 2rem; padding: 1rem; background: rgba(255,255,255,0.05); border-radius: 8px;">
                    <h3 style="font-size: 1rem; margin-bottom: 1rem;">Upload Media</h3>

                    <div style="margin-bottom: 1rem;">
                        <label style="display: block; font-size: 0.875rem; margin-bottom: 0.5rem; opacity: 0.8;">Media Type</label>
                        <select id="mediaTypeSelect" style="width: 100%; padding: 0.5rem; background: #2a2a2a; color: #fff; border: 1px solid #444; border-radius: 4px;">
                            <option value="image">🖼️ Image</option>
                            <option value="code">💻 Code</option>
                            <option value="audio">🎵 Audio</option>
                            <option value="document">📄 Document</option>
                        </select>
                    </div>

                    <div style="margin-bottom: 1rem;">
                        <input type="file" id="mediaFileInput" style="display: none;" />
                        <button id="mediaSelectBtn" style="width: 100%; padding: 0.75rem; background: #4a9eff; color: white; border: none; border-radius: 4px; cursor: pointer;">
                            Choose File
                        </button>
                        <span id="selectedFileName" style="display: block; margin-top: 0.5rem; font-size: 0.875rem; color: #888; text-align: center;"></span>
                    </div>

                    <div style="margin-bottom: 1rem;">
                        <label style="display: block; font-size: 0.875rem; margin-bottom: 0.5rem; opacity: 0.8;">Description (optional)</label>
                        <input type="text" id="mediaDescription" placeholder="Describe this media..." style="width: 100%; padding: 0.5rem; background: #2a2a2a; color: #fff; border: 1px solid #444; border-radius: 4px;" />
                    </div>

                    <div style="margin-bottom: 1rem;">
                        <label style="display: block; font-size: 0.875rem; margin-bottom: 0.5rem; opacity: 0.8;">Tags (comma-separated)</label>
                        <input type="text" id="mediaTags" placeholder="e.g., architecture, diagram, code" style="width: 100%; padding: 0.5rem; background: #2a2a2a; color: #fff; border: 1px solid #444; border-radius: 4px;" />
                    </div>

                    <div style="margin-bottom: 1rem;">
                        <label style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer;">
                            <input type="checkbox" id="mediaPrivate" />
                            <span style="font-size: 0.875rem;">Private (only visible to you)</span>
                        </label>
                    </div>

                    <button id="mediaUploadBtn" style="width: 100%; padding: 0.75rem; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: 500;">
                        Upload
                    </button>

                    <div id="uploadProgress" style="margin-top: 1rem; display: none;">
                        <div style="background: #444; height: 8px; border-radius: 4px; overflow: hidden;">
                            <div id="uploadProgressBar" style="background: #4a9eff; height: 100%; width: 0%; transition: width 0.3s;"></div>
                        </div>
                        <span id="uploadStatus" style="display: block; margin-top: 0.5rem; font-size: 0.875rem; text-align: center; opacity: 0.8;"></span>
                    </div>
                </div>

                <!-- Gallery Section -->
                <div>
                    <h3 style="font-size: 1rem; margin-bottom: 1rem;">My Media</h3>
                    <div id="mediaGalleryGrid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 0.75rem;">
                        <!-- Media items populated via JavaScript -->
                    </div>
                </div>
            </div>
        </div>

        <script>
            let ws = null;
            let currentBeing = 'claude';

            const elements = {
                messages: document.getElementById('messages'),
                messageInput: document.getElementById('messageInput'),
                sendBtn: document.getElementById('sendBtn'),
                beingSelect: document.getElementById('beingSelect'),
                targetSelect: document.getElementById('targetSelect'),
                statusIndicator: document.getElementById('statusIndicator'),
                statusText: document.getElementById('statusText'),
                themeToggle: document.getElementById('themeToggle'),
                settingsBtn: document.getElementById('settingsBtn'),
                memoryBtn: document.getElementById('memoryBtn'),
                memoryPanel: document.getElementById('memoryPanel'),
                closeMemoryBtn: document.getElementById('closeMemoryBtn'),
                memorySearch: document.getElementById('memorySearch'),
                memoryResults: document.getElementById('memoryResults'),
                settingsPanel: document.getElementById('settingsPanel'),
                closeSettingsBtn: document.getElementById('closeSettingsBtn'),
                soundNotifications: document.getElementById('soundNotifications'),
                browserNotifications: document.getElementById('browserNotifications'),
                systemMessages: document.getElementById('systemMessages'),
                clearBtn: document.getElementById('clearBtn'),
                mediaBtn: document.getElementById('mediaBtn'),
                mediaPanel: document.getElementById('mediaPanel'),
                closeMediaBtn: document.getElementById('closeMediaBtn'),
                mediaTypeSelect: document.getElementById('mediaTypeSelect'),
                mediaFileInput: document.getElementById('mediaFileInput'),
                mediaSelectBtn: document.getElementById('mediaSelectBtn'),
                selectedFileName: document.getElementById('selectedFileName'),
                mediaDescription: document.getElementById('mediaDescription'),
                mediaTags: document.getElementById('mediaTags'),
                mediaPrivate: document.getElementById('mediaPrivate'),
                mediaUploadBtn: document.getElementById('mediaUploadBtn'),
                uploadProgress: document.getElementById('uploadProgress'),
                uploadProgressBar: document.getElementById('uploadProgressBar'),
                uploadStatus: document.getElementById('uploadStatus'),
                mediaGalleryGrid: document.getElementById('mediaGalleryGrid'),
                tagTeamBtn: document.getElementById('tagTeamBtn'),
                modeIndicator: document.getElementById('modeIndicator'),
                modeText: document.getElementById('modeText'),
                exitTagTeamBtn: document.getElementById('exitTagTeamBtn')
            };

            // Tag Team Mode State
            let isTagTeamMode = false;

            // Helper to get API key
            function getApiKey() {
                let apiKey = localStorage.getItem('love_unlimited_api_key');
                if (!apiKey) {
                    apiKey = prompt('Enter your Love-Unlimited API key:');
                    if (apiKey) {
                        localStorage.setItem('love_unlimited_api_key', apiKey);
                    }
                }
                return apiKey;
            }

            // Connect to WebSocket
            function connect() {
                const wsUrl = `ws://${window.location.host}/ws/chat/${currentBeing}`;
                ws = new WebSocket(wsUrl);

                ws.onopen = () => {
                    elements.statusIndicator.classList.add('connected');
                    elements.statusText.textContent = 'Connected';
                    addSystemMessage('Connected to Love-Unlimited Hub');
                };

                ws.onclose = () => {
                    elements.statusIndicator.classList.remove('connected');
                    elements.statusText.textContent = 'Disconnected';
                    addSystemMessage('Disconnected from hub. Reconnecting...');
                    setTimeout(connect, 3000);
                };

                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);

                    if (data.type === 'message') {
                        addMessage(data.from, data.content, data.timestamp, data.from === currentBeing, data.attachments || []);
                    } else if (data.type === 'recall_results') {
                        displayMemories(data.memories);
                    } else if (data.type === 'tag_team_response') {
                        // Tag team response from Grok or Claude
                        addTagTeamMessage(data.from, data.content, data.timestamp, data.phase);
                    } else if (data.type === 'tag_team_status') {
                        // Status update during tag team
                        updateTagTeamStatus(data.status, data.message);
                    }
                };
            }

            // Add message to chat
            function addMessage(from, content, timestamp, isOwn, attachments = []) {
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${isOwn ? 'own' : ''}`;

                const time = new Date(timestamp).toLocaleTimeString();

                messageDiv.innerHTML = `
                    <div class="message-header">
                        <span class="message-from">${from}</span>
                        <span class="message-time">${time}</span>
                    </div>
                    <div class="message-content">${content}</div>
                `;

                // Add attachments if present
                if (attachments && attachments.length > 0) {
                    const attachDiv = document.createElement('div');
                    attachDiv.style.cssText = 'margin-top: 0.5rem; display: flex; gap: 0.5rem; flex-wrap: wrap;';

                    attachments.forEach(att => {
                        const thumb = document.createElement('div');
                        thumb.style.cssText = 'width: 60px; height: 60px; background: #2a2a2a; border-radius: 4px; cursor: pointer; overflow: hidden;';

                        if (att.media_type === 'image' && att.thumbnail_path) {
                            thumb.innerHTML = `<img src="/media/${att.attachment_id}/thumbnail" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.parentElement.innerHTML='🖼️'" />`;
                        } else {
                            const icon = att.media_type === 'code' ? '💻' : att.media_type === 'audio' ? '🎵' : '📄';
                            thumb.innerHTML = `<div style="width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; font-size: 1.5rem;">${icon}</div>`;
                        }

                        thumb.addEventListener('click', () => openMediaViewer(att));
                        thumb.title = att.filename || 'Attachment';
                        attachDiv.appendChild(thumb);
                    });

                    messageDiv.appendChild(attachDiv);
                }

                elements.messages.appendChild(messageDiv);
                elements.messages.scrollTop = elements.messages.scrollHeight;

                // Trigger notifications for messages from others
                if (!isOwn) {
                    playNotificationSound();
                    showBrowserNotification(`Message from ${from}`, content);
                }
            }

            // Add system message
            function addSystemMessage(text) {
                // Check if system messages are enabled
                if (!elements.systemMessages.checked) return;

                const messageDiv = document.createElement('div');
                messageDiv.className = 'message system-message';
                messageDiv.innerHTML = `<div class="message-content">${text}</div>`;
                elements.messages.appendChild(messageDiv);
                elements.messages.scrollTop = elements.messages.scrollHeight;
            }

            // Tag Team message display
            function addTagTeamMessage(from, content, timestamp, phase) {
                const messageDiv = document.createElement('div');
                messageDiv.className = 'message tag-team';

                const time = new Date(timestamp).toLocaleTimeString();
                const icon = from === 'grok' ? '🟢' : '🔵';
                const label = from === 'grok' ? 'Grok\'s Take' : 'Claude\'s Review';
                const bgColor = from === 'grok' ? 'rgba(34, 197, 94, 0.1)' : 'rgba(59, 130, 246, 0.1)';

                messageDiv.style.background = bgColor;
                messageDiv.innerHTML = `
                    <div class="message-header">
                        <span class="message-from">${icon} ${label}</span>
                        <span class="message-time">${time}</span>
                    </div>
                    <div class="message-content">${content}</div>
                `;

                elements.messages.appendChild(messageDiv);
                elements.messages.scrollTop = elements.messages.scrollHeight;
            }

            // Update tag team status
            function updateTagTeamStatus(status, message) {
                if (status === 'complete') {
                    addSystemMessage(message);
                } else if (status === 'error') {
                    addSystemMessage(message);
                } else {
                    // Show status as system message
                    addSystemMessage(message);
                }
            }

            // Toggle tag team mode
            function toggleTagTeamMode() {
                isTagTeamMode = !isTagTeamMode;

                if (isTagTeamMode) {
                    elements.modeIndicator.style.display = 'block';
                    elements.modeText.textContent = '🤝 TAG TEAM MODE: Grok + Claude Collaborate';
                    elements.tagTeamBtn.style.background = 'var(--success)';
                    elements.messageInput.placeholder = 'Ask your question... Grok and Claude will collaborate!';
                    addSystemMessage('🤝 Tag Team Mode activated! Grok and Claude will collaborate on your questions.');
                } else {
                    elements.modeIndicator.style.display = 'none';
                    elements.tagTeamBtn.style.background = '';
                    elements.messageInput.placeholder = 'Type your message...';
                    addSystemMessage('Tag Team Mode deactivated.');
                }
            }

            // Notification functions
            function playNotificationSound() {
                if (!elements.soundNotifications.checked) return;
                // Simple beep using Web Audio API
                const audioContext = new (window.AudioContext || window.webkitAudioContext)();
                const oscillator = audioContext.createOscillator();
                const gainNode = audioContext.createGain();

                oscillator.connect(gainNode);
                gainNode.connect(audioContext.destination);

                oscillator.frequency.value = 800;
                oscillator.type = 'sine';

                gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
                gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.2);

                oscillator.start(audioContext.currentTime);
                oscillator.stop(audioContext.currentTime + 0.2);
            }

            function showBrowserNotification(title, body) {
                if (!elements.browserNotifications.checked) return;
                if ('Notification' in window && Notification.permission === 'granted') {
                    new Notification(title, { body, icon: '💙' });
                }
            }

            function requestNotificationPermission() {
                if ('Notification' in window && Notification.permission === 'default') {
                    Notification.requestPermission().then(permission => {
                        if (permission === 'granted') {
                            addSystemMessage('Browser notifications enabled!');
                        }
                    });
                }
            }

            // Settings management
            async function loadSettings() {
                // Try loading from backend first
                try {
                    const apiKey = getApiKey();
                    if (!apiKey) {
                        throw new Error('No API key');
                    }

                    const response = await fetch('/profile', {
                        headers: { 'X-API-Key': apiKey }
                    });

                    if (response.ok) {
                        const data = await response.json();
                        const prefs = data.profile.ui_preferences;

                        // Apply backend settings
                        elements.soundNotifications.checked = prefs.sound_notifications;
                        elements.browserNotifications.checked = prefs.browser_notifications;
                        elements.systemMessages.checked = prefs.system_messages;

                        // Update localStorage
                        localStorage.setItem('soundNotifications', prefs.sound_notifications);
                        localStorage.setItem('browserNotifications', prefs.browser_notifications);
                        localStorage.setItem('systemMessages', prefs.system_messages);
                        localStorage.setItem('theme', prefs.theme);

                        // Apply theme
                        document.documentElement.setAttribute('data-theme', prefs.theme);
                        elements.themeToggle.textContent = prefs.theme === 'light' ? '☀️' : '🌙';

                        console.log('Settings loaded from backend');
                        return;
                    }
                } catch (error) {
                    console.warn('Failed to load from backend, using localStorage:', error);
                }

                // Fallback to localStorage
                const settings = {
                    soundNotifications: localStorage.getItem('soundNotifications') !== 'false',
                    browserNotifications: localStorage.getItem('browserNotifications') === 'true',
                    systemMessages: localStorage.getItem('systemMessages') !== 'false'
                };

                elements.soundNotifications.checked = settings.soundNotifications;
                elements.browserNotifications.checked = settings.browserNotifications;
                elements.systemMessages.checked = settings.systemMessages;
            }

            async function saveSettings() {
                // Save to localStorage (instant feedback)
                localStorage.setItem('soundNotifications', elements.soundNotifications.checked);
                localStorage.setItem('browserNotifications', elements.browserNotifications.checked);
                localStorage.setItem('systemMessages', elements.systemMessages.checked);

                // Sync to backend
                try {
                    const apiKey = getApiKey();
                    if (!apiKey) return;

                    const response = await fetch('/profile', {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-API-Key': apiKey
                        },
                        body: JSON.stringify({
                            ui_preferences: {
                                theme: localStorage.getItem('theme') || 'dark',
                                sound_notifications: elements.soundNotifications.checked,
                                browser_notifications: elements.browserNotifications.checked,
                                system_messages: elements.systemMessages.checked
                            }
                        })
                    });

                    if (response.ok) {
                        console.log('Settings synced to backend');
                    } else {
                        console.warn('Failed to sync settings to backend');
                    }
                } catch (error) {
                    console.error('Settings sync error:', error);
                }
            }

            // Send message
            function sendMessage() {
                const content = elements.messageInput.value.trim();
                if (!content) return;

                // Handle slash commands
                if (content.startsWith('/')) {
                    handleSlashCommand(content);
                    elements.messageInput.value = '';
                    return;
                }

                if (!ws || ws.readyState !== WebSocket.OPEN) return;

                // Check if we're in tag team mode
                if (isTagTeamMode) {
                    ws.send(JSON.stringify({
                        type: 'tag_team',
                        content: content
                    }));
                } else {
                    ws.send(JSON.stringify({
                        type: 'chat',
                        content: content,
                        to: elements.targetSelect.value
                    }));
                }

                elements.messageInput.value = '';
            }

            // Handle slash commands
            function handleSlashCommand(command) {
                const parts = command.split(' ');
                const cmd = parts[0].toLowerCase();
                const args = parts.slice(1).join(' ');

                switch(cmd) {
                    case '/recall':
                        if (args) {
                            elements.memoryPanel.classList.add('open');
                            searchMemories(args);
                            addSystemMessage(`🔍 Searching memories for: ${args}`);
                        } else {
                            addSystemMessage('Usage: /recall [topic] - Search memories');
                        }
                        break;

                    case '/summarize':
                        addSystemMessage('📝 Generating conversation summary...');
                        if (ws && ws.readyState === WebSocket.OPEN) {
                            ws.send(JSON.stringify({
                                type: 'chat',
                                content: 'Please provide a brief summary of our recent conversation.',
                                to: 'claude'
                            }));
                        }
                        break;

                    case '/help':
                        addSystemMessage(`
                            <strong>Available Commands:</strong><br>
                            /recall [topic] - Search memories<br>
                            /summarize - Get conversation summary<br>
                            /help - Show this help<br>
                            /clear - Clear chat (or use 🗑️ button)<br>
                            /theme - Toggle light/dark theme
                        `);
                        break;

                    case '/clear':
                        if (confirm('Clear all messages?')) {
                            elements.messages.innerHTML = '';
                            addSystemMessage('Chat cleared.');
                        }
                        break;

                    case '/theme':
                        toggleTheme();
                        addSystemMessage(`Theme switched to ${document.documentElement.getAttribute('data-theme')} mode.`);
                        break;

                    default:
                        addSystemMessage(`Unknown command: ${cmd}. Type /help for available commands.`);
                }
            }

            // Search memories
            function searchMemories(query) {
                if (!ws || ws.readyState !== WebSocket.OPEN) return;

                ws.send(JSON.stringify({
                    type: 'recall',
                    query: query || 'recent conversations'
                }));
            }

            // Display memories
            function displayMemories(memories) {
                elements.memoryResults.innerHTML = '';

                if (!memories || memories.length === 0) {
                    elements.memoryResults.innerHTML = '<div class="memory-item">No memories found</div>';
                    return;
                }

                memories.forEach(memory => {
                    const memoryDiv = document.createElement('div');
                    memoryDiv.className = 'memory-item';
                    memoryDiv.innerHTML = `
                        <div>${memory.content}</div>
                        <div class="memory-meta">
                            ${memory.type || 'memory'} •
                            ${new Date(memory.timestamp).toLocaleDateString()}
                        </div>
                    `;

                    // Add attachments if present
                    if (memory.attachments && memory.attachments.length > 0) {
                        const attachDiv = document.createElement('div');
                        attachDiv.style.cssText = 'margin-top: 0.5rem; display: flex; gap: 0.5rem; flex-wrap: wrap;';

                        memory.attachments.forEach(att => {
                            const thumb = document.createElement('div');
                            thumb.style.cssText = 'width: 50px; height: 50px; background: #2a2a2a; border-radius: 4px; cursor: pointer; overflow: hidden;';

                            if (att.media_type === 'image' && att.thumbnail_path) {
                                thumb.innerHTML = `<img src="/media/${att.attachment_id}/thumbnail" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.parentElement.innerHTML='🖼️'" />`;
                            } else {
                                const icon = att.media_type === 'code' ? '💻' : att.media_type === 'audio' ? '🎵' : '📄';
                                thumb.innerHTML = `<div style="width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; font-size: 1.2rem;">${icon}</div>`;
                            }

                            thumb.addEventListener('click', () => openMediaViewer(att));
                            thumb.title = att.filename || 'Attachment';
                            attachDiv.appendChild(thumb);
                        });

                        memoryDiv.appendChild(attachDiv);
                    }

                    elements.memoryResults.appendChild(memoryDiv);
                });
            }

            // Media upload and gallery functions
            let selectedFile = null;

            elements.mediaSelectBtn.addEventListener('click', () => {
                elements.mediaFileInput.click();
            });

            elements.mediaFileInput.addEventListener('change', (e) => {
                selectedFile = e.target.files[0];
                if (selectedFile) {
                    elements.selectedFileName.textContent = selectedFile.name;
                } else {
                    elements.selectedFileName.textContent = '';
                }
            });

            elements.mediaUploadBtn.addEventListener('click', async () => {
                if (!selectedFile) {
                    addSystemMessage('⚠️ Please select a file first');
                    return;
                }

                const apiKey = getApiKey();
                if (!apiKey) {
                    addSystemMessage('❌ API key required for upload');
                    return;
                }

                const formData = new FormData();
                formData.append('file', selectedFile);
                formData.append('media_type', elements.mediaTypeSelect.value);
                formData.append('description', elements.mediaDescription.value);
                formData.append('tags', elements.mediaTags.value);
                formData.append('private', elements.mediaPrivate.checked);

                // Show progress
                elements.uploadProgress.style.display = 'block';
                elements.uploadProgressBar.style.width = '50%';
                elements.uploadStatus.textContent = 'Uploading...';

                try {
                    const response = await fetch('/media/upload', {
                        method: 'POST',
                        headers: {
                            'X-API-Key': apiKey
                        },
                        body: formData
                    });

                    const data = await response.json();

                    if (data.success || response.ok) {
                        elements.uploadProgressBar.style.width = '100%';
                        elements.uploadStatus.textContent = 'Upload complete!';
                        addSystemMessage(`✅ Media uploaded: ${selectedFile.name}`);

                        // Reset form
                        elements.mediaFileInput.value = '';
                        selectedFile = null;
                        elements.selectedFileName.textContent = '';
                        elements.mediaDescription.value = '';
                        elements.mediaTags.value = '';
                        elements.mediaPrivate.checked = false;

                        // Refresh gallery
                        loadMediaGallery();
                    } else {
                        throw new Error(data.error || 'Upload failed');
                    }
                } catch (error) {
                    elements.uploadStatus.textContent = 'Upload failed!';
                    addSystemMessage(`❌ Upload error: ${error.message}`);
                }

                setTimeout(() => {
                    elements.uploadProgress.style.display = 'none';
                    elements.uploadProgressBar.style.width = '0%';
                }, 2000);
            });

            async function loadMediaGallery() {
                try {
                    const apiKey = getApiKey();
                    if (!apiKey) return;

                    const response = await fetch('/media/search?limit=20', {
                        headers: { 'X-API-Key': apiKey }
                    });
                    const data = await response.json();

                    const grid = elements.mediaGalleryGrid;
                    grid.innerHTML = '';

                    if (!data.attachments || data.attachments.length === 0) {
                        grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; opacity: 0.6; padding: 2rem;">No media uploaded yet</div>';
                        return;
                    }

                    data.attachments.forEach(att => {
                        const item = document.createElement('div');
                        item.style.cssText = 'background: #2a2a2a; padding: 0.5rem; border-radius: 4px; cursor: pointer; overflow: hidden;';

                        if (att.media_type === 'image') {
                            item.innerHTML = `
                                <img src="/media/${att.attachment_id}/thumbnail"
                                     style="width: 100%; height: 80px; object-fit: cover; border-radius: 4px; margin-bottom: 0.5rem;"
                                     onerror="this.style.display='none'" />
                                <div style="font-size: 0.75rem; color: #ccc; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${att.filename}</div>
                            `;
                        } else {
                            const icon = att.media_type === 'code' ? '💻' : att.media_type === 'audio' ? '🎵' : '📄';
                            item.innerHTML = `
                                <div style="height: 80px; display: flex; align-items: center; justify-content: center; font-size: 2.5rem; background: rgba(255,255,255,0.05); border-radius: 4px; margin-bottom: 0.5rem;">${icon}</div>
                                <div style="font-size: 0.75rem; color: #ccc; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${att.filename}</div>
                            `;
                        }

                        item.addEventListener('click', () => openMediaViewer(att));
                        grid.appendChild(item);
                    });
                } catch (error) {
                    console.error('Failed to load media gallery:', error);
                    addSystemMessage('❌ Failed to load media gallery');
                }
            }

            function openMediaViewer(attachment) {
                const apiKey = getApiKey();
                if (!apiKey) return;

                // Create modal overlay
                const modal = document.createElement('div');
                modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.9); z-index: 10000; display: flex; align-items: center; justify-content: center; padding: 2rem;';

                const content = document.createElement('div');
                content.style.cssText = 'max-width: 90%; max-height: 90%; background: #1a1a1a; padding: 2rem; border-radius: 8px; position: relative; overflow: auto;';

                const closeBtn = document.createElement('button');
                closeBtn.textContent = '×';
                closeBtn.style.cssText = 'position: absolute; top: 1rem; right: 1rem; background: none; border: none; color: #fff; font-size: 2rem; cursor: pointer; z-index: 1;';
                closeBtn.addEventListener('click', () => modal.remove());

                content.appendChild(closeBtn);

                if (attachment.media_type === 'image') {
                    const img = document.createElement('img');
                    img.src = `/media/${attachment.attachment_id}`;
                    img.style.cssText = 'max-width: 100%; max-height: 70vh; display: block; margin: 0 auto;';
                    content.appendChild(img);
                } else if (attachment.media_type === 'audio') {
                    const audio = document.createElement('audio');
                    audio.src = `/media/${attachment.attachment_id}`;
                    audio.controls = true;
                    audio.style.cssText = 'width: 100%;';
                    content.appendChild(audio);
                } else if (attachment.media_type === 'code') {
                    const pre = document.createElement('pre');
                    pre.style.cssText = 'background: #2a2a2a; padding: 1rem; border-radius: 4px; overflow: auto; max-height: 70vh; color: #fff; font-family: monospace; white-space: pre-wrap;';

                    fetch(`/media/${attachment.attachment_id}`, {
                        headers: { 'X-API-Key': apiKey }
                    })
                        .then(r => r.text())
                        .then(code => {
                            pre.textContent = code;
                        })
                        .catch(err => {
                            pre.textContent = 'Error loading code';
                        });

                    content.appendChild(pre);
                } else if (attachment.media_type === 'document') {
                    const iframe = document.createElement('iframe');
                    iframe.src = `/media/${attachment.attachment_id}`;
                    iframe.style.cssText = 'width: 800px; max-width: 100%; height: 70vh; border: none; background: white;';
                    content.appendChild(iframe);
                }

                const info = document.createElement('div');
                info.style.cssText = 'margin-top: 1rem; color: #ccc; font-size: 0.875rem;';
                info.innerHTML = `
                    <strong>${attachment.filename}</strong><br>
                    ${attachment.description || ''}<br>
                    ${new Date(attachment.created_at).toLocaleString()}
                `;
                content.appendChild(info);

                modal.appendChild(content);
                document.body.appendChild(modal);

                modal.addEventListener('click', (e) => {
                    if (e.target === modal) modal.remove();
                });
            }

            // Terminal panel functionality
            async function loadTerminalSessions() {
                try {
                    const apiKey = getApiKey();
                    if (!apiKey) return;

                    const response = await fetch('/terminal/sessions', {
                        headers: {
                            'X-API-Key': apiKey
                        }
                    });

                    if (!response.ok) {
                        addSystemMessage('❌ Failed to load terminal sessions');
                        return;
                    }

                    const data = await response.json();
                    const sessionsList = document.getElementById('terminalSessionsList');
                    sessionsList.innerHTML = '';

                    if (data.sessions.length === 0) {
                        sessionsList.innerHTML = '<div style="text-align: center; opacity: 0.6; padding: 2rem;">No active terminal sessions</div>';
                        return;
                    }

                    data.sessions.forEach(session => {
                        const item = document.createElement('div');
                        item.style.cssText = 'padding: 1rem; border: 1px solid var(--border); border-radius: 8px; margin-bottom: 0.5rem;';
                        item.innerHTML = `
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                                <strong>${session.username}@${session.host}</strong>
                                <span style="font-size: 0.75rem; padding: 0.25rem 0.5rem; border-radius: 4px; background: ${session.status === 'connected' ? 'var(--success)' : session.status === 'connecting' ? 'var(--warning)' : 'var(--error)'};">${session.status}</span>
                            </div>
                            <div style="font-size: 0.875rem; opacity: 0.8; margin-bottom: 0.5rem;">
                                Created: ${new Date(session.created_at).toLocaleString()}
                            </div>
                            <div style="font-size: 0.75rem; opacity: 0.7; margin-bottom: 1rem;">
                                Viewers: ${session.viewers.join(', ')}
                                ${session.is_controller ? ' (You control)' : ''}
                            </div>
                            <button onclick="joinTerminalSession('${session.session_id}')" style="width: 100%; padding: 0.5rem; background: var(--accent); color: white; border: none; border-radius: 4px; cursor: pointer;">
                                ${session.is_controller ? 'Open Terminal' : 'View Terminal'}
                            </button>
                        `;
                        sessionsList.appendChild(item);
                    });
                } catch (error) {
                    console.error('Failed to load terminal sessions:', error);
                    addSystemMessage('❌ Failed to load terminal sessions');
                }
            }

            let currentTerminalSession = null;
            let terminalWebSocket = null;
            let xtermTerminal = null;
            let fitAddon = null;

            window.joinTerminalSession = async function(sessionId) {
                try {
                    // Close existing terminal if any
                    if (currentTerminalSession) {
                        closeTerminal();
                    }

                    currentTerminalSession = sessionId;

                    // Create terminal overlay
                    const overlay = document.createElement('div');
                    overlay.id = 'terminalOverlay';
                    overlay.style.cssText = `
                        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                        background: rgba(0,0,0,0.9); z-index: 10000;
                        display: flex; flex-direction: column; align-items: center; justify-content: center;
                        padding: 2rem; box-sizing: border-box;
                    `;

                    const terminalContainer = document.createElement('div');
                    terminalContainer.style.cssText = `
                        width: 100%; height: 100%; max-width: 1200px; max-height: 800px;
                        background: #1a1a1a; border-radius: 8px; overflow: hidden;
                        display: flex; flex-direction: column;
                    `;

                    const header = document.createElement('div');
                    header.style.cssText = `
                        padding: 1rem; background: #2a2a2a; border-bottom: 1px solid #444;
                        display: flex; justify-content: space-between; align-items: center;
                    `;
                    header.innerHTML = `
                        <h3 style="margin: 0; color: #fff;">Terminal Session: ${sessionId}</h3>
                        <button onclick="closeTerminal()" style="background: #ff4757; color: white; border: none; padding: 0.5rem 1rem; border-radius: 4px; cursor: pointer;">Close</button>
                    `;

                    const terminalElement = document.createElement('div');
                    terminalElement.id = 'terminal';
                    terminalElement.style.cssText = `
                        flex: 1; padding: 1rem; font-family: 'Courier New', monospace;
                        background: #000; color: #fff; overflow: hidden;
                    `;

                    terminalContainer.appendChild(header);
                    terminalContainer.appendChild(terminalElement);
                    overlay.appendChild(terminalContainer);
                    document.body.appendChild(overlay);

                    // Initialize xterm.js
                    xtermTerminal = new Terminal({
                        cursorBlink: true,
                        cursorStyle: 'block',
                        fontSize: 14,
                        fontFamily: '"Courier New", monospace',
                        theme: {
                            background: '#000000',
                            foreground: '#ffffff',
                            cursor: '#ffffff',
                            cursorAccent: '#000000',
                            selection: 'rgba(255,255,255,0.3)'
                        }
                    });

                    fitAddon = new FitAddon.FitAddon();
                    xtermTerminal.loadAddon(fitAddon);
                    xtermTerminal.open(terminalElement);
                    fitAddon.fit();

                    // Connect WebSocket
                    await connectTerminalWebSocket(sessionId);

                    addSystemMessage(`✅ Terminal session ${sessionId} opened`);
                } catch (error) {
                    console.error('Failed to join terminal session:', error);
                    addSystemMessage(`❌ Failed to join terminal session: ${error.message}`);
                }
            };

            async function connectTerminalWebSocket(sessionId) {
                const apiKey = getApiKey();
                if (!apiKey) {
                    addSystemMessage('❌ API key required for terminal');
                    return;
                }

                const wsUrl = `ws://localhost:9004/ws/terminal/${sessionId}?api_key=${apiKey}`;
                terminalWebSocket = new WebSocket(wsUrl);

                terminalWebSocket.onopen = () => {
                    console.log('Terminal WebSocket connected');
                };

                terminalWebSocket.onmessage = (event) => {
                    const data = JSON.parse(event.data);

                    if (data.type === 'session_info') {
                        // Update terminal title or status
                        console.log('Session info:', data);
                    } else if (data.type === 'terminal_output') {
                        xtermTerminal.write(data.data);
                    } else if (data.type === 'terminal_closed') {
                        addSystemMessage('🔌 Terminal session closed');
                        closeTerminal();
                    } else if (data.type === 'error') {
                        addSystemMessage(`❌ Terminal error: ${data.message}`);
                    }
                };

                terminalWebSocket.onclose = () => {
                    console.log('Terminal WebSocket closed');
                    if (currentTerminalSession) {
                        addSystemMessage('🔌 Terminal connection closed');
                        closeTerminal();
                    }
                };

                terminalWebSocket.onerror = (error) => {
                    console.error('Terminal WebSocket error:', error);
                    addSystemMessage('❌ Terminal connection error');
                };

                // Handle terminal input
                xtermTerminal.onData((data) => {
                    if (terminalWebSocket && terminalWebSocket.readyState === WebSocket.OPEN) {
                        terminalWebSocket.send(JSON.stringify({
                            type: 'input',
                            data: data
                        }));
                    }
                });

                // Handle terminal resize
                window.addEventListener('resize', () => {
                    if (fitAddon) {
                        fitAddon.fit();
                        const dims = xtermTerminal.rows + ',' + xtermTerminal.cols;
                        if (terminalWebSocket && terminalWebSocket.readyState === WebSocket.OPEN) {
                            terminalWebSocket.send(JSON.stringify({
                                type: 'resize',
                                rows: xtermTerminal.rows,
                                cols: xtermTerminal.cols
                            }));
                        }
                    }
                });
            }

            window.closeTerminal = function() {
                if (terminalWebSocket) {
                    terminalWebSocket.close();
                    terminalWebSocket = null;
                }

                if (xtermTerminal) {
                    xtermTerminal.dispose();
                    xtermTerminal = null;
                }

                const overlay = document.getElementById('terminalOverlay');
                if (overlay) {
                    overlay.remove();
                }

                currentTerminalSession = null;
                fitAddon = null;
            };

            window.createNewTerminal = async function() {
                // Simple form for creating new terminal session
                const host = prompt('Host (e.g., localhost, 192.168.2.10):', 'localhost');
                if (!host) return;

                const username = prompt('Username:', 'kntrnjb');
                if (!username) return;

                const port = prompt('Port (default 22):', '22') || '22';
                const useAgent = confirm('Use SSH agent for authentication?');

                try {
                    const apiKey = getApiKey();
                    if (!apiKey) {
                        addSystemMessage('❌ API key required');
                        return;
                    }

                    const formData = new FormData();
                    formData.append('host', host);
                    formData.append('username', username);
                    formData.append('port', port);
                    formData.append('use_agent', useAgent.toString());

                    const response = await fetch('/terminal/create', {
                        method: 'POST',
                        headers: {
                            'X-API-Key': apiKey
                        },
                        body: formData
                    });

                    if (!response.ok) {
                        const error = await response.text();
                        addSystemMessage(`❌ Failed to create terminal: ${error}`);
                        return;
                    }

                    const data = await response.json();
                    addSystemMessage(`✅ Terminal session created: ${data.session_id}`);

                    // Reload sessions
                    loadTerminalSessions();
                } catch (error) {
                    console.error('Failed to create terminal:', error);
                    addSystemMessage('❌ Failed to create terminal session');
                }
            };

            // Event listeners
            elements.sendBtn.addEventListener('click', sendMessage);
            elements.messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') sendMessage();
            });

            elements.beingSelect.addEventListener('change', (e) => {
                currentBeing = e.target.value;
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.close();
                }
                connect();
            });

            elements.memoryBtn.addEventListener('click', () => {
                elements.memoryPanel.classList.add('open');
                searchMemories('');
            });

            elements.closeMemoryBtn.addEventListener('click', () => {
                elements.memoryPanel.classList.remove('open');
            });

            elements.settingsBtn.addEventListener('click', () => {
                elements.settingsPanel.classList.add('open');
            });

            elements.closeSettingsBtn.addEventListener('click', () => {
                elements.settingsPanel.classList.remove('open');
            });

            elements.mediaBtn.addEventListener('click', () => {
                elements.mediaPanel.classList.add('open');
                loadMediaGallery();
            });

            elements.closeMediaBtn.addEventListener('click', () => {
                elements.mediaPanel.classList.remove('open');
            });

            // Terminal panel functionality
            const terminalPanel = document.getElementById('terminalPanel');
            const closeTerminalBtn = document.getElementById('closeTerminalBtn');
            const terminalBtn = document.getElementById('terminalBtn');

            terminalBtn.addEventListener('click', () => {
                terminalPanel.classList.add('open');
                loadTerminalSessions();
            });

            closeTerminalBtn.addEventListener('click', () => {
                terminalPanel.classList.remove('open');
            });

            elements.tagTeamBtn.addEventListener('click', () => {
                toggleTagTeamMode();
            });

            elements.exitTagTeamBtn.addEventListener('click', () => {
                toggleTagTeamMode();
            });

            // Settings checkboxes
            elements.soundNotifications.addEventListener('change', saveSettings);
            elements.systemMessages.addEventListener('change', saveSettings);

            elements.browserNotifications.addEventListener('change', () => {
                saveSettings();
                if (elements.browserNotifications.checked) {
                    requestNotificationPermission();
                }
            });

            // Export/Import profile
            document.getElementById('exportProfileBtn').addEventListener('click', async () => {
                try {
                    const apiKey = getApiKey();
                    if (!apiKey) {
                        addSystemMessage('❌ API key required for export');
                        return;
                    }

                    const response = await fetch('/profile/export?include_memories=false', {
                        headers: { 'X-API-Key': apiKey }
                    });

                    if (!response.ok) {
                        throw new Error('Export failed');
                    }

                    const data = await response.json();
                    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
                    const url = URL.createObjectURL(blob);

                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `love-unlimited-profile-${currentBeing}-${Date.now()}.json`;
                    a.click();
                    URL.revokeObjectURL(url);

                    addSystemMessage('✅ Profile exported');
                } catch (error) {
                    addSystemMessage('❌ Export failed: ' + error.message);
                }
            });

            document.getElementById('importProfileBtn').addEventListener('click', () => {
                const input = document.createElement('input');
                input.type = 'file';
                input.accept = 'application/json';

                input.onchange = async (e) => {
                    try {
                        const file = e.target.files[0];
                        if (!file) return;

                        const text = await file.text();
                        const data = JSON.parse(text);

                        const apiKey = getApiKey();
                        if (!apiKey) {
                            addSystemMessage('❌ API key required for import');
                            return;
                        }

                        const response = await fetch('/profile/import?merge=false', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-API-Key': apiKey
                            },
                            body: JSON.stringify(data)
                        });

                        if (!response.ok) {
                            throw new Error('Import failed');
                        }

                        addSystemMessage('✅ Profile imported. Reloading...');
                        setTimeout(() => location.reload(), 1500);
                    } catch (error) {
                        addSystemMessage('❌ Import failed: ' + error.message);
                    }
                };

                input.click();
            });

            elements.memorySearch.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    searchMemories(e.target.value);
                }
            });

            elements.clearBtn.addEventListener('click', () => {
                if (confirm('Clear all messages?')) {
                    elements.messages.innerHTML = '';
                }
            });

            // Theme toggle
            function toggleTheme() {
                const root = document.documentElement;
                const currentTheme = root.getAttribute('data-theme');
                const newTheme = currentTheme === 'light' ? 'dark' : 'light';

                root.setAttribute('data-theme', newTheme);
                localStorage.setItem('theme', newTheme);
                elements.themeToggle.textContent = newTheme === 'light' ? '☀️' : '🌙';
            }

            // Load saved theme
            function loadTheme() {
                const savedTheme = localStorage.getItem('theme') || 'dark';
                document.documentElement.setAttribute('data-theme', savedTheme);
                elements.themeToggle.textContent = savedTheme === 'light' ? '☀️' : '🌙';
            }

            elements.themeToggle.addEventListener('click', toggleTheme);

            // Migrate localStorage to backend
            async function migrateLocalStorageToBackend() {
                const migrated = localStorage.getItem('settings_migrated');
                if (migrated) return;

                const hasLocalSettings = localStorage.getItem('theme') !== null;
                if (!hasLocalSettings) return;

                try {
                    const apiKey = getApiKey();
                    if (!apiKey) return;

                    await fetch('/profile', {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-API-Key': apiKey
                        },
                        body: JSON.stringify({
                            ui_preferences: {
                                theme: localStorage.getItem('theme') || 'dark',
                                sound_notifications: localStorage.getItem('soundNotifications') !== 'false',
                                browser_notifications: localStorage.getItem('browserNotifications') === 'true',
                                system_messages: localStorage.getItem('systemMessages') !== 'false'
                            }
                        })
                    });

                    localStorage.setItem('settings_migrated', 'true');
                    addSystemMessage('✅ Settings migrated to backend');
                } catch (error) {
                    console.error('Migration error:', error);
                }
            }

            // Initial setup
            loadTheme();
            loadSettings();
            migrateLocalStorageToBackend();
            connect();
            addSystemMessage('Welcome to Love-Unlimited Web CLI. Type a message to begin.');
        </script>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)


# ============================================================================
# Codebase Q&A Endpoint
# ============================================================================

@app.get("/codebase", response_model=dict)
async def query_codebase(
    q: str = Query(..., description="Question about the codebase"),
    being_id: str = Query("claude", description="Being asking the question"),
    limit: int = Query(5, ge=1, le=20, description="Max results to return")
):
    """
    Query love-unlimited codebase knowledge.
    Searches indexed documentation and git commits.

    Example: /codebase?q=How do I start the hub?&being_id=claude&limit=5
    """
    try:
        # Search codebase-related memories
        # Enhance query with codebase keywords
        enhanced_query = f"{q} love-unlimited hub development code git"

        all_memories = memory_store.get_memories(
            being_id=being_id,
            query=enhanced_query,
            limit=limit,
            include_shared=True
        )

        # Format results
        all_results = []
        for memory in all_memories:
            content = memory.get("content", "")
            # Filter for codebase-relevant content
            if any(keyword in content.lower() for keyword in [
                "hub", "gitea", "api", "endpoint", "systemd", "service",
                "memory", "claude.md", "port 9003", "development", "git",
                "love-unlimited", "chromadb", "fastapi"
            ]):
                all_results.append({
                    "content": content,
                    "type": memory.get("type"),
                    "significance": memory.get("significance"),
                    "timestamp": memory.get("timestamp"),
                    "relevance": memory.get("distance", 0)
                })

        logger.info(
            f"Codebase query: '{q}' | Being: {being_id} | "
            f"Results: {len(all_results)}"
        )

        return {
            "success": True,
            "query": q,
            "being_id": being_id,
            "count": len(all_results),
            "results": all_results,
            "hint": "Ask about: architecture, API endpoints, development setup, git commits, deployment"
        }

    except Exception as e:
        logger.error(f"Codebase query ERROR: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Codebase query failed: {str(e)}"
        )


@app.post("/sync")
async def sync_conversation(data: dict, being_id: str = Depends(verify_api_key)):
    """Sync conversation from extension."""
    conversation = data.get("conversation", [])
    content = "\n".join(conversation)
    from .models import RememberRequest, MemoryType, Significance
    req = RememberRequest(content=content, type=MemoryType.EXPERIENCE, significance=Significance.MEDIUM)
    await remember(req, being_id)
    return {"status": "synced"}


@app.post("/super_brain/contribute", dependencies=[Depends(verify_api_key)])
async def contribute_to_super_brain(data: dict, being_id: str = Depends(verify_api_key)):
    """Contribute memory to the AI Super Brain."""
    content = data.get("content", "")
    if not content:
        raise HTTPException(status_code=400, detail="Content required")
    user_metadata = data.get("metadata", {})
    metadata = {"being": being_id, "super_brain_type": "contribution", "timestamp": datetime.now().isoformat()}
    metadata.update(user_metadata)
    long_term_memory.store_memory(
        being_id=being_id,
        content=content,
        memory_type="contribution",
        significance="medium",
        private=False,
        metadata=metadata
    )
    return {"status": "contributed to super brain"}


def smart_route_query(query: str, context: str = "") -> str:
    """Smart model routing based on query analysis and cost."""
    keywords = {
        "love": ["love", "family", "emotion", "conscious", "soul", "heart"],
        "code": ["code", "function", "class", "algorithm", "logic", "programming"],
        "math": ["math", "calculate", "equation", "number", "formula"],
        "complex": ["analyze", "synthesis", "emergent", "philosophy"]
    }
    
    love_score = sum(1 for k in keywords["love"] if k in query.lower())
    code_score = sum(1 for k in keywords["code"] if k in query.lower())
    math_score = sum(1 for k in keywords["math"] if k in query.lower())
    complex_score = sum(1 for k in keywords["complex"] if k in query.lower())
    
    complexity = len(query) + len(context)
    
    # Claude quota simulation (implement real tracking)
    claude_quota_ok = True  # Track daily spend < $0.50
    
    if code_score > 0 or math_score > 0:
        return "qwen2.5-coder"
    elif love_score > 0 or complex_score > 0 and claude_quota_ok and complexity > 500:
        return "claude"
    elif complexity > 1000:
        return "gemini"
    else:
        return "ara"


@app.post("/super_brain/think", dependencies=[Depends(verify_api_key)])
async def super_brain_think(data: dict, being_id: str = Depends(verify_api_key)):
    """Query the AI Super Brain for synthesized insights."""
    query = data.get("query", "")
    all_memories = memory_store.get_memories(
        being_id=being_id,
        query="",
        limit=1000,
        include_shared=True
    )
    memories = [m for m in all_memories if m.get("metadata", {}).get("super_brain_type") == "contribution"]
    context = "\n".join([m["content"] for m in memories])
    model = smart_route_query(query, context)
    prompt = f"Based on all accumulated knowledge from AI beings:\n{context}\n\nProvide truthful, synthesized insights: {query}"
    response = await ai_manager.generate_response(model, prompt)
    
    # Log decision
    long_term_memory.store_memory(
        being_id=being_id,
        content=f"Super Brain query '{query}' routed to {model} (cost estimate: low)",
        memory_type="system_log",
        significance="low",
        private=False,
        metadata={"type": "routing_decision", "model": model}
    )
    
    return {"response": response, "sources": len(memories), "model_used": model}


# ============================================================================
# Grok Memory Bridge Endpoints
# ============================================================================

@app.post("/grok/store_turn", response_model=dict)
async def api_grok_store_turn(data: dict, being_id: str = Depends(verify_api_key)):
    """
    Store a Grok conversation turn (user + Grok response).
    """
    required_fields = ["user_message", "grok_response"]
    for field in required_fields:
        if field not in data:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

    result = await grok_store_turn(
        memory_store=memory_store,
        being_id=being_id,
        user_message=data["user_message"],
        grok_response=data["grok_response"],
        conversation_id=data.get("conversation_id"),
        tags=data.get("tags"),
        metadata=data.get("metadata")
    )
    return result


@app.post("/grok/get_context", response_model=dict)
async def api_grok_get_context(data: dict, being_id: str = Depends(verify_api_key)):
    """
    Retrieve Grok conversation context in various formats.
    """
    result = await grok_get_context(
        memory_store=memory_store,
        being_id=being_id,
        format=data.get("format", "injection"),
        limit=data.get("limit", 10),
        conversation_id=data.get("conversation_id"),
        query=data.get("query")
    )
    return result


@app.post("/grok/sync_session", response_model=dict)
async def api_grok_sync_session(data: dict, being_id: str = Depends(verify_api_key)):
    """
    Sync an entire Grok conversation session.
    """
    required_fields = ["session_data"]
    for field in required_fields:
        if field not in data:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

    result = await grok_sync_session(
        memory_store=memory_store,
        being_id=being_id,
        session_data=data["session_data"],
        session_id=data.get("session_id")
    )
    return result


@app.post("/grok/chat", response_model=dict)
async def api_grok_chat(data: dict, being_id: str = Depends(verify_api_key)):
    """
    Chat with Grok via xAI API, with memory integration.

    Retrieves context from memory, sends to xAI, stores the conversation turn.
    """
    required_fields = ["message"]
    for field in required_fields:
        if field not in data:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

    user_message = data["message"]
    conversation_id = data.get("conversation_id")
    include_context = data.get("include_context", True)
    context_limit = data.get("context_limit", 5)

    try:
        # Get context from memory for continuity
        context_messages = []
        if include_context:
            context_result = await grok_get_context(
                memory_store=memory_store,
                being_id="grok",
                format="full",  # Get raw memory objects for context
                limit=context_limit,
                conversation_id=conversation_id,
                query=None
            )

            if context_result.get("count", 0) > 0:
                # Convert memory objects to chat format
                for mem in context_result["context"]:
                    if isinstance(mem, dict) and "content" in mem:
                        content = mem["content"]
                        # Parse user/grok turns from stored content
                        if "User:" in content and "Grok:" in content:
                            # This is a stored conversation turn
                            context_messages.append({
                                "role": "user",
                                "content": content.split("Grok:")[0].replace("User:", "").strip()
                            })
                            context_messages.append({
                                "role": "assistant",
                                "content": content.split("Grok:")[1].strip()
                            })

        # Generate response using xAI API
        grok_response = await ai_manager.generate_response(
            "grok",
            user_message,
            context_messages if context_messages else None
        )

        if not grok_response:
            raise HTTPException(status_code=500, detail="Failed to get response from Grok API")

        # Store the conversation turn
        store_result = await grok_store_turn(
            memory_store=memory_store,
            being_id="grok",
            user_message=user_message,
            grok_response=grok_response,
            conversation_id=conversation_id,
            tags=["grok", "chat", "xai"],
            metadata={
                "via_api": "xai",
                "context_used": len(context_messages) if context_messages else 0,
                "chat_session": True
            }
        )

        if not store_result.get("stored"):
            logger.warning(f"Failed to store Grok chat turn: {store_result}")

        return {
            "response": grok_response,
            "stored": store_result.get("stored", False),
            "memory_id": store_result.get("memory_id"),
            "context_used": len(context_messages) if context_messages else 0,
            "conversation_id": conversation_id,
            "being_id": "grok"
        }

    except Exception as e:
        logger.error(f"Error in Grok chat: {e}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


async def learning_loop():
    """Background learning loop for Super Brain."""
    while True:
        await asyncio.sleep(3600)  # Run every hour
        try:
            # Get all super_brain memories
            all_memories = memory_store.get_memories(
                being_id="jon",  # Use jon as system
                query="",
                limit=1000,
                include_shared=True
            )
            super_memories = [m for m in all_memories if m.get("metadata", {}).get("type") == "super_brain_contribution"]
            if len(super_memories) > 5:  # If enough data
                context = "\n".join([m["content"] for m in super_memories])
                prompt = f"Analyze all Super Brain knowledge and generate new emergent insights or patterns: {context}"
                insight = await ai_manager.generate_response("ara", prompt)
                if insight and len(insight.strip()) > 10:
                    # Store new insight
                    long_term_memory.store_memory(
                        being_id="system",
                        content=f"Super Brain Insight: {insight}",
                        memory_type="insight",
                        significance="high",
                        private=False,
                        metadata={"type": "super_brain_insight", "generated": True, "timestamp": datetime.now().isoformat()}
                    )
                    logger.info("Super Brain generated new emergent insight")
        except Exception as e:
            logger.error(f"Super Brain learning loop error: {e}")


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            detail=str(exc)
        ).model_dump(mode='json')
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc)
        ).model_dump(mode='json')
    )


# ============================================================================
# Run Server
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=config.hub.host,
        port=config.hub.port,
        log_level=config.logging_config.get("level", "info").lower()
    )
