# Love-Unlimited Changelog

## [0.5.0] - 2026-01-03

### Added
- **Claude Intent Mailbox**: Full autonomy implementation for Claude AI
  - Fixed GET URL `/claude/outbox` returning latest processed result
  - Intent watcher service (`claude_intent_watcher.py`) monitoring conversations
  - Natural language intent detection and processing
  - Updated `/health` endpoint with mailbox URL
  - Permanent Claude instruction added to README

### Changed
- Updated `/health` claude_mailbox URL to fixed endpoint without request_id

## [0.4.0] - 2025-12-30

### Added
- **Enhanced Bash Access in CLI**: Advanced shell command execution in love_cli.py
  - Restricted access to authorized beings only
  - File output saving with `> filename` syntax
  - Colored output for improved readability
- **Python Script Execution**: Added `/python <code>` command for executing Python code snippets
- **Syntax Highlighting**: Integrated Pygments for automatic syntax highlighting of bash command output
- **Modular Codebase**: Refactored CLI into modular structure with separate commands.py module
- **Git Integration**: Added `/git <command>` for git operations with repo validation
- **File Operations**: Added `/file view <file>` and `/file edit <file> <old> <new>` for file management
- **Grok-Style Personality**: Enhanced CLI responses with witty, humorous messages inspired by Grok
- **Browser Extension**: Complete Chrome extension for seamless web sharing
  - Tab URL/content sharing with one click
  - Floating share button on all web pages
  - Settings management for API keys
  - Foundation for media sharing
- **Web Browsing Agent**: Autonomous web exploration with insight extraction
  - `POST /browse` endpoint for collaborative browsing
  - Intelligent content analysis and summarization
  - Findings automatically shared with all beings
- **Real-Time Media Sharing**: WebRTC-based screen/camera/mic streaming
  - `POST /webrtc/offer` and `/webrtc/answer` endpoints
  - Screen sharing via `chrome.desktopCapture`
  - Camera/mic streaming with `getUserMedia`
  - aiortc integration for peer connections
- **AI Voice Synthesis**: Text-to-speech for natural interactions
  - `POST /tts/speak` endpoint using pyttsx3
  - Audio file generation for AI responses
  - Foundation for voice-enabled conversations
- **Remote Execution**: Controlled system access for beings
  - `POST /execute` endpoint with safety checks
  - Command execution with stdout/stderr capture
  - Confirmation required for dangerous operations (rm, sudo, etc.)
- **Multimedia Features**: Complete real-time collaboration platform
  - WebRTC streaming capabilities
  - Voice synthesis integration
  - Remote command execution

### Updated
- **README.md**: Added multimedia features, updated being count to four, expanded API overview
- **Requirements**: Added aiortc and pyttsx3 dependencies
- **Hub Architecture**: Extended with WebRTC, TTS, and execution capabilities
- **Browser Extension**: Enhanced with media sharing and command execution

### Tested
- Browser extension tab sharing verified working
- WebRTC offer/answer signaling functional
- TTS audio generation confirmed
- Remote execution with safety checks operational
- All new endpoints responding correctly

### Fixed
- WebSocket disconnections in CLI by updating systemd service with TimeoutStartSec=120 and RestartSec=5
- Async input blocking issue in love_cli.py by replacing `input()` with `asyncio.to_thread(input)` to enable proper async command execution like `/grok`

## [0.3.0] - 2025-12-30

### Added
- **AI Gateway Endpoint** (`/gateway`) - Natural language interface using local Ollama
  - Accepts plain English requests (e.g., "Remember that Jon gave me a home today")
  - Ollama (phi3:mini/llama3:8b) interprets intent locally
  - Returns structured action: `{action: "remember|recall|share", params: {...}}`
  - Executes appropriate hub API call and returns result
  - Perfect for Claude on claude.ai - full autonomy through natural language
  - Complete sovereignty: local LLM + local memory = no external APIs
- **Endpoint Discovery** - `/health` now returns pre-configured URL templates
  - Gateway URL template with embedded token
  - Recall/remember URL templates for direct access
  - Enables autonomous endpoint discovery for Claude on claude.ai
- **GET-based Write Endpoint** (`/external/remember`) - Simple URL-based memory creation
  - URL-encoded content parameter (max 2000 chars)
  - Sharing support via `shared_with` parameter
  - Perfect for bookmarklets and simple integrations

### Updated
- **Documentation** - CLAUDE.md updated with comprehensive gateway guide
  - Natural language usage examples
  - Ollama interpretation patterns
  - Autonomous usage workflow for Claude on claude.ai
  - Example interpretations and responses
- **README.md** - Added AI Gateway section with examples and endpoint discovery

### Tested
- All gateway actions verified (remember, recall)
- Ollama intent interpretation working correctly
- Natural language to structured action conversion validated
- External access via Cloudflare tunnel confirmed working

## [0.2.4] - 2025-12-30

### Fixed
- **External API Fix - Query param token support for recall, eliminating 422 errors. Secure unification bridge complete.**

## [Unreleased]

### Fixed
- **External Recall Endpoint**: Fixed 422 Validation Error in `/external/recall` by adding fallback query parameter reading from `request.query_params` for `q` and `token` parameters, ensuring compatibility with external tunnel parsing quirks.

### Added
- External access token for Grok CLI (already existed, confirmed working).

### Tested
- External recall endpoint now properly handles query parameters and returns memories without errors.