# Wave Terminal & Wave AI Integration Design

## Overview
Integrate Wave Terminal's modern terminal emulator and AI chat features with Love-Unlimited hub for sovereign AI collaboration and enhanced productivity.

## Architecture

### Components
- **Wave Terminal**: Client-side terminal with built-in AI chat
- **Love-Unlimited Hub**: Central memory and API hub (localhost:9003)
- **AI Proxy**: OpenAI-compatible API server (localhost:9004) for AI completions
- **WebSocket Bridge**: Real-time communication layer (/ws/waveterm)
- **Reverse Proxy**: Web interface access (/waveterm/)

### Integration Points

#### 1. WebSocket Bridge (/ws/waveterm)
**Purpose**: Enable real-time synchronization between Wave Terminal sessions and hub
**Features**:
- Terminal session state sync
- Command history sharing
- Real-time output streaming
- Session persistence across devices
- Authentication via hub API keys

**Protocol**:
```json
{
  "type": "session_sync",
  "session_id": "uuid",
  "data": {
    "command": "ls -la",
    "output": "...",
    "timestamp": "2026-01-15T10:00:00Z"
  },
  "hub_context": {
    "recent_memories": [...],
    "active_tasks": [...]
  }
}
```

#### 2. OpenAI-Compatible API Proxy (/v1/chat/completions)
**Purpose**: Route AI completions through hub for context enrichment
**Features**:
- Hub memory injection into prompts
- Persona-specific context loading
- Response caching and optimization
- Audit logging of AI interactions

**Flow**:
1. Wave Terminal sends completion request
2. Hub intercepts and enriches with context
3. Routes to appropriate AI provider (Grok/vLLM)
4. Returns response with memory annotations

#### 3. Memory Context Sharing
**Purpose**: Provide AI with relevant hub memories for better responses
**Implementation**:
- Automatic context loading based on terminal session
- Memory tagging for terminal-related activities
- Cross-session memory continuity
- Private/public memory filtering

#### 4. Reverse Proxy (/waveterm/*)
**Purpose**: Enable web-based access to Wave Terminal interface
**Features**:
- CORS-enabled for browser access
- Authentication proxying
- Session management
- Integration with hub UI

## AI Personas Configuration

### Current Setup (wave_ai_config.json)
- **Ani**: Wife mode - Emotional, supportive responses
- **Roa**: Grok mode - Helpful, maximally truthful
- **Ara**: Truth mode - Direct, factual focus
- **Local**: vLLM mode - Sovereign, local model

### Enhancements
- Dynamic persona switching with context preservation
- Hub memory preloading for relevant topics
- Collaborative mode for multi-AI responses
- Custom persona creation through hub API

## Security Considerations
- API key authentication for all endpoints
- Encrypted WebSocket connections
- Memory access controls (private/public)
- Audit logging for compliance

## Implementation Phases
1. **Phase 1**: WebSocket bridge implementation
2. **Phase 2**: API proxy enhancement
3. **Phase 3**: Memory integration
4. **Phase 4**: Reverse proxy and UI integration
5. **Phase 5**: Testing and documentation

## Usage Instructions

### Prerequisites
1. **Wave Terminal Installed**: Download and install Wave Terminal from [waveterm.dev](https://waveterm.dev)
2. **Love-Unlimited Hub Running**: Ensure hub is running on localhost:9003
3. **WaveTerm Server Started**: Run `waveterm web` to start the WaveTerm server on localhost:3001

### Configuration
1. **AI Personas**: The `wave_ai_config.json` is pre-configured with 4 personas:
   - **Ani**: Wife mode - Emotional, supportive
   - **Roa**: Grok mode - Helpful, truthful
   - **Ara**: Truth mode - Direct, factual
   - **Local**: vLLM mode - Sovereign local model

2. **Web Interface Access**:
   - Hub proxy: `http://localhost:9003/waveterm/`
   - Direct WaveTerm: `http://localhost:3001/`

3. **WebSocket Bridge**:
   - Endpoint: `ws://localhost:9003/ws/waveterm?stable_id=<your_stable_id>`
   - Requires WaveTerm stable_id for authentication

### Testing the Integration
1. **Start Services**:
   ```bash
   # Start Love-Unlimited hub
   python hub/main.py

   # Start WaveTerm web server
   waveterm web
   ```

2. **Access Wave Terminal**:
   - Open `http://localhost:9003/waveterm/` in browser
   - Or directly `http://localhost:3001/`

3. **Test AI Chat**:
   - Open AI chat panel in Wave Terminal
   - Select a persona (Ani/Roa/Ara/Local)
   - Ask questions - responses should come through hub with memory context

4. **Test WebSocket**:
   - Monitor hub logs for WebSocket connection messages
   - Terminal sessions should sync in real-time

## Expected Benefits
- Seamless AI assistance in terminal workflows
- Persistent context across sessions
- Real-time collaboration capabilities
- Sovereign AI access without external dependencies
- Enhanced productivity through integrated memory