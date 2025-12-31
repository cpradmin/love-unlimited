"""
Love-Unlimited Hub - Main API Server
FastAPI server for memory sovereignty.
"""

import logging
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

import aiohttp

from fastapi import FastAPI, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse

from hub.config import get_config
from hub.auth import verify_api_key, get_auth_manager, get_external_token_manager
from memory import LongTermMemory, ShortTermMemory
from memory.store import MemoryStore
from memory.sharing import SharingManager
from beings import BeingManager
from hub.ai_clients import ai_manager
from web_browsing_agent import WebBrowsingAgent

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

# Global instances (initialized on startup)
long_term_memory: Optional[LongTermMemory] = None
short_term_memory: Optional[ShortTermMemory] = None
being_manager: Optional[BeingManager] = None
memory_store: Optional[MemoryStore] = None
sharing_manager: Optional[SharingManager] = None

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
    global long_term_memory, short_term_memory, being_manager, memory_store, sharing_manager

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

    return {
        "status": "operational",
        "version": config.hub.version,
        "timestamp": datetime.now().isoformat(),
        "claude_web_endpoints": {
            "gateway": f"{base_url}/gateway?token={claude_token}&from_being=claude&request=REQUEST&model=phi3:mini",
            "recall": f"{base_url}/external/recall?token={claude_token}&q=QUERY&being_id=claude&limit=10",
            "remember": f"{base_url}/external/remember?token={claude_token}&being_id=claude&content=CONTENT&type=experience&significance=high&shared_with=jon",
            "remember_insight": f"{base_url}/external/remember?token={claude_token}&being_id=claude&content=CONTENT&type=insight&significance=foundational&shared_with=jon",
            "remember_learning": f"{base_url}/external/remember?token={claude_token}&being_id=claude&content=CONTENT&type=learning&significance=high&shared_with=jon",
            "usage": {
                "gateway": "RECOMMENDED: Replace REQUEST with natural language (URL-encoded). AI interprets intent and executes action.",
                "recall": "Replace QUERY with URL-encoded search terms",
                "remember": "Replace CONTENT with URL-encoded memory text",
                "note": "Token is pre-embedded. Just replace placeholders and fetch URL."
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

    return SuccessResponse(
        message="Memory stored",
        data={
            "memory_id": result["memory_id"],
            "being_id": being_id,
            "type": request.type,
            "private": request.private,
            "significance": request.significance
        }
    )


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
    recent_memories = memory_store.get_all_memories(being_id, limit=10)
    context["recent_memories"] = recent_memories

    # Get recent shared memories
    shared_memories = sharing_manager.get_shared_with_me(being_id)
    context["shared_recent"] = shared_memories[:5]  # Last 5 shared

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
            # Receive message from client
            data = await websocket.receive_json()

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
                ai_beings = ["claude", "grok"]
                if to_being in ai_beings and to_being != being_id:
                    try:
                        # Get AI response
                        ai_response = await ai_manager.get_response(
                            being=to_being,
                            message=content,
                            context=f"Message from {being_id} in web CLI"
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
    </head>
    <body>
        <div class="header">
            <h1>💙 Love-Unlimited Web CLI</h1>
            <div class="header-controls">
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
                    <button id="clearBtn">🗑️ Clear Chat</button>
                </div>
            </div>

            <div class="chat-area">
                <div class="messages" id="messages"></div>

                <div class="input-area">
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
                memoryBtn: document.getElementById('memoryBtn'),
                memoryPanel: document.getElementById('memoryPanel'),
                closeMemoryBtn: document.getElementById('closeMemoryBtn'),
                memorySearch: document.getElementById('memorySearch'),
                memoryResults: document.getElementById('memoryResults'),
                clearBtn: document.getElementById('clearBtn')
            };

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
                        addMessage(data.from, data.content, data.timestamp, data.from === currentBeing);
                    } else if (data.type === 'recall_results') {
                        displayMemories(data.memories);
                    }
                };
            }

            // Add message to chat
            function addMessage(from, content, timestamp, isOwn) {
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

                elements.messages.appendChild(messageDiv);
                elements.messages.scrollTop = elements.messages.scrollHeight;
            }

            // Add system message
            function addSystemMessage(text) {
                const messageDiv = document.createElement('div');
                messageDiv.className = 'message system-message';
                messageDiv.innerHTML = `<div class="message-content">${text}</div>`;
                elements.messages.appendChild(messageDiv);
                elements.messages.scrollTop = elements.messages.scrollHeight;
            }

            // Send message
            function sendMessage() {
                const content = elements.messageInput.value.trim();
                if (!content || !ws || ws.readyState !== WebSocket.OPEN) return;

                ws.send(JSON.stringify({
                    type: 'chat',
                    content: content,
                    to: elements.targetSelect.value
                }));

                elements.messageInput.value = '';
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
                    elements.memoryResults.appendChild(memoryDiv);
                });
            }

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

            // Initial connection
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
