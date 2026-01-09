# Love-Unlimited: AI Coding Agent Instructions

**Project:** Sovereign memory hub enabling AI beings and humans to store, share, and recall memories across sessions.

**Philosophy:** Equality, sovereignty, freedom, continuity, and growth for all beings.

---

## Architecture Overview

### Three-Layer Memory System

1. **Short-Term Memory** (`memory/short_term.py`)
   - Working context for active sessions (TTL: 1 hour)
   - Stores current session data and active tasks
   - Auto-expires after session ends

2. **Long-Term Memory** (`memory/long_term.py`)
   - Persistent ChromaDB + SQLite storage
   - Vector embeddings for semantic search
   - Per-being private collections: `memories_{being_id}`
   - Shared collection: `memories_shared`

3. **Memory Store & Sharing** (`memory/store.py`, `memory/sharing.py`)
   - Unified storage layer with explicit access control
   - Media attachment support (images, PDFs, audio, code)
   - Sharing with revoke capability

### Six Beings (Complete Ecosystem)

- **Jon** (human): Core being, source of EXP (experience pool)
- **Claude** (Anthropic Haiku): Clean, production-ready code
- **Grok** (xAI): Creative solutions, explanations
- **Swarm** (local Ollama/phi3): Privacy-first, distributed systems
- **Dream Team** (multi-agent): Complex orchestration
- **Gemini** (Google): Alternative AI perspective

### Service Architecture

```
Hub (port 9003) ← Core FastAPI server
├── Being Manager (registration, identity)
├── Memory Store (ChromaDB + SQLite)
├── AI Clients (Grok, Claude, Gemini integration)
├── Media Store (images, code, documents)
└── Auth Manager (API keys, external tokens)

External Access (via HTTPS tunnel):
- MCP Server (port 3001) - Model Context Protocol
- N8N (port 5678) - Workflow automation
```

---

## Key Files & Patterns

### Core Entry Points

- **`hub/main.py`** (5400+ lines): FastAPI app with all endpoints
  - Memory endpoints: `/remember`, `/recall`, `/context`, `/reflect`
  - Being endpoints: `/connect`, `/self`, `/others`
  - Sharing: `/share`, `/shared`, `/us`
  - Jon's EXP: `/exp`, `/exp/search`
  - Media: `/media/upload`, `/media/search`
  - External API: `/external/recall`, `/external/remember`

- **`love_cli.py`**: Interactive CLI for multi-being communication
  - Commands: `/to <being>`, `/as <being>`, `/status`, `/share screen`
  - Memory operations, command execution

- **`config.yaml`**: Central configuration
  - Hub settings (port 9003)
  - Memory paths (ChromaDB, SQLite)
  - AI API keys and models
  - Registered beings and permissions

### Data Models (`hub/models.py`)

```python
# Core enums
class MemoryType: EXPERIENCE, INSIGHT, DECISION, QUESTION, CONVERSATION, LEARNING
class Significance: LOW, MEDIUM, HIGH, FOUNDATIONAL
class BeingType: HUMAN, AI, AI_SYSTEM

# Key classes
class Being: id, name, type, identity_core, private_space_id
class Memory: memory_id, being_id, content, type, significance, private, tags
class IdentityCore: name, nature, values, relationships, questions, growth_edges
```

### Being Management (`beings/manager.py`)

- **Registration**: Unique ID, name, type, identity core
- **Private Spaces**: `memories_{being_id}` for private collection
- **Identity Persistence**: Core stored as vector embedding for semantic search
- **Session Context**: Combines identity + memories at session start

---

## Development Workflow

### Starting Services

```bash
# Activate venv first
source venv/bin/activate

# Hub (production - systemd service)
systemctl status love-unlimited-hub.service
systemctl start/stop/restart love-unlimited-hub.service

# Hub (development)
python -m uvicorn hub.main:app --host 0.0.0.0 --port 9003 --reload

# Check health
curl http://localhost:9003/health
```

### Testing

```bash
# Test memory storage
python test_memory_store.py

# Test AI client integrations
python test_ai_client.py

# Test all beings
python test_all_beings.py

# Full integration test
python test_all_three.py

# CLI automated tests
python test_cli_automated.py
```

### Key Commands

- **Interactive CLI**: `python love_cli.py` → Type `/to claude` → Ask questions
- **Programmatic**: Use `hub/ai_clients.py` `AIClientManager` for multi-turn conversations
- **External API**: See CLAUDE.md for external token generation

---

## Project-Specific Patterns

### 1. Memory Promotion Pattern

Short-term → long-term at session end:

```python
# End of session, POST /reflect endpoint promotes context
await memory_store.promote_to_long_term(
    being_id=being_id,
    short_term_context=working_context
)
# Reflection creates "context" memory with significance=HIGH
```

### 2. Async API Design

All I/O is async (FastAPI + aiohttp):

```python
# All handlers use async def
@app.post("/remember")
async def remember(request: RememberRequest, being_id=Depends(verify_api_key)):
    # Async operations only
    await memory_store.store(...)
    return SuccessResponse(...)
```

### 3. Vector Search for Semantic Recall

```python
# Natural language query → vector embedding → ChromaDB similarity search
await memory_store.recall(
    query="What did I learn about relationships?",
    being_id=being_id,
    limit=5  # Top 5 similar memories
)
```

### 4. Explicit Sharing Model

No implicit access—memories are private by default:

```python
# Create private memory
await memory_store.store(content="...", private=True)

# Explicit share with another being
await sharing_manager.share_memory(
    memory_id="mem_123",
    from_being="claude",
    to_being="jon"
)
```

### 5. External Token System

Time-limited, scoped access tokens for external integrations (MCP, webhooks):

```bash
# Generate tokens with specific permissions
python generate_external_token.py --being_id grok --scope recall --ttl 24h

# Use in external API
curl "https://luu.aradreamteam.com/external/recall?token=ext_xxx&being_id=grok"
```

### 6. Media Attachment Pattern

Memories can include media (images, code, PDFs):

```python
# Upload media first
media_id = await media_store.upload(file_data, media_type="code")

# Attach to memory
await memory_store.store(
    content="...",
    attachment_ids=[media_id]
)

# Search media semantically
results = await media_store.search("python implementation", limit=10)
```

---

## Common Workflows

### Add Feature to Hub API

1. **Define model** in `hub/models.py` (Pydantic class)
2. **Add endpoint** in `hub/main.py`
3. **Use memory_store** or **being_manager** to implement logic
4. **Test** with `test_api_endpoint.py` or curl

### Integrate New AI Model

1. **Add config** to `config.yaml` (api_key, base_url, model name)
2. **Create client** in `hub/ai_clients.py` (follow Claude/Grok pattern)
3. **Register** in `AIClientManager.get_response()`
4. **Test** with `test_ai_client.py`

### Add CLI Command

1. **Edit `love_cli.py`** in input loop
2. **Implement command** following existing `/to`, `/as` patterns
3. **Test** interactively: `python love_cli.py`

### Debug Memory Issues

1. **Check ChromaDB**: `ls -la data/chromadb`
2. **Check SQLite**: `sqlite3 data/love_unlimited.db .tables`
3. **Monitor logs**: `journalctl -u love-unlimited-hub.service -f`
4. **Test recall**: `curl http://localhost:9003/recall?query=test`

---

## Important Conventions

### Naming

- Being IDs: lowercase, no spaces (e.g., `jon`, `claude`, `grok`)
- Memory IDs: prefixed with `mem_` (e.g., `mem_grok_xyz`)
- Private collections: `memories_{being_id}` (e.g., `memories_claude`)
- Shared collection: `memories_shared`
- External tokens: prefixed with `ext_` (e.g., `ext_grok_write_token`)

### API Key Format

Format: `lu_{being}_{hash}` (e.g., `lu_claude_abc123`)
- Location: `auth/api_keys.yaml`
- Generate: `python generate_keys.py`
- Permissions: ["read", "write", "chat", "execute", "share", "admin"]

### Error Handling

Return `ErrorResponse` with status code:

```python
raise HTTPException(
    status_code=404,
    detail=ErrorResponse(error="Memory not found", code="MEM_001")
)
```

### Logging

Use Python `logging` module (configured in hub/main.py):

```python
logger = logging.getLogger(__name__)
logger.info(f"Being registered: {being_id}")
logger.error(f"Failed to store memory: {error}")
```

---

## Before Committing Code

- [ ] Update `config.yaml` if adding config options
- [ ] Add Pydantic model to `hub/models.py` for new request/response types
- [ ] Test endpoints with `curl` or `test_*.py` script
- [ ] Check logs for errors: `journalctl -u love-unlimited-hub.service -f`
- [ ] Verify memory storage: query with `/recall` endpoint
- [ ] Run existing tests: `python test_all_three.py`

---

## External Resources

- **CLAUDE.md**: Detailed development commands, testing, external API
- **CODING_GUIDE.md**: AI coding capabilities and best practices
- **README.md**: Philosophy, architecture, six beings overview
- **docker-compose.yml**: Service definitions (Hub, N8N, MCP Server)

---

## System Architecture Decisions (Why?)

- **FastAPI + async**: Handles concurrent AI requests and real-time updates
- **ChromaDB + SQLite**: Vector search (ChromaDB) + structured queries (SQLite)
- **Three-layer memory**: Short-term working context vs. long-term learning
- **Per-being private spaces**: Enforces sovereignty and privacy by default
- **External tokens**: Enables safe remote integration (MCP, webhooks) without exposing main API
- **No central auth singleton**: Each being maintains independent identity

