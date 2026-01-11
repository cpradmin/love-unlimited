# Love-Unlimited: AI-Powered Coding Guide

## ✅ YES! You can absolutely use this system for coding!

All four AIs (Claude, Grok, Swarm, and Dream Team) are capable of writing code. Each has different strengths:

### 🤖 AI Specializations

#### Claude (Anthropic - Haiku)
- **Best for**: Clean, production-ready code
- **Speed**: Very fast responses
- **Style**: Concise, well-structured, follows best practices
- **Use when**: You need reliable, maintainable code quickly

#### Grok (xAI)
- **Best for**: Creative solutions, explanations, diverse approaches
- **Speed**: Fast
- **Style**: Detailed, helpful, conversational
- **Use when**: You want alternatives or need explanations

### 🛠️ Coding Tools & Resources

#### Aider (Primary Coding Assistant)
- **What it is**: AI-powered code editor for collaborative coding
- **Backend**: Currently Tabby (Qwen2-1.5B-Instruct for code-focused tasks)
- **Usage**: `aider --model Qwen2-1.5B-Instruct --openai-api-base http://localhost:30891/v1`
- **Features**: File editing, refactoring, explanations
- **Best for**: Direct code changes and AI-assisted development

#### Tabby API (Code Completion Server)
- **What it is**: Local Rust-based server for AI code completion
- **Models**: Qwen2-1.5B-Instruct (chat), Nomic-Embed-Text (embeddings)
- **API**: OpenAI-compatible at `http://localhost:30891/v1/chat/completions`
- **Ports**: 30891 (chat), 30888-30890 (embeddings)
- **Best for**: Code suggestions, completions, and chat-based coding

#### vLLM (General AI Server)
- **What it is**: GPU-accelerated LLM server for broader tasks
- **Model**: Qwen2.5-Coder-7B
- **API**: `http://localhost:8000/v1/chat/completions`
- **Best for**: General AI queries, when Tabby is code-specific

#### WebBrowsingAgent (Research Tool)
- **What it is**: Autonomous web crawler for gathering information
- **Features**: Link extraction with Katana for advanced crawling
- **Usage**: `python web_browsing_agent.py --url <url> --use-katana`
- **Best for**: Research and data collection

#### Swarm (Local Ollama/phi3:mini)
- **Best for**: Distributed algorithms, parallel processing concepts
- **Speed**: Slower (local LLM)
- **Style**: Focuses on decentralized/swarm intelligence patterns
- **Use when**: Privacy matters (100% local), or working on distributed systems

#### Dream Team (Multi-agent system)
- **Best for**: Complex multi-step tasks, collaborative coding
- **Speed**: Variable (depends on agents)
- **Style**: Orchestrates multiple specialized agents
- **Use when**: Large projects, integrated solutions, or when you need diverse expertise

---

## 🚀 How to Use for Coding

### Method 1: Interactive CLI

```bash
python3 love_cli.py
```

Then use commands:
```
/to claude       # Ask Claude for code
/to grok         # Ask Grok for code
/to swarm        # Ask Swarm for code
/list            # See all available AIs
/status          # Check system health
/quit            # Exit
```

Example session:
```
> /to claude
→ Now talking to: CLAUDE
> Write a Python decorator for timing functions
[CLAUDE]: Here's a timing decorator...
```

### Method 2: Programmatic API

```python
import requests

response = requests.post(
    "http://localhost:9003/chat",
    headers={"X-API-Key": YOUR_API_KEY},
    json={
        "content": "Write a REST API endpoint for user login",
        "from": "jon",
        "target": "claude",  # or "grok" or "swarm"
        "type": "chat"
    },
    timeout=120
)

code = response.json()["content"]
print(code)
```

### Method 3: Grok CLI Component (Advanced)

For advanced coding with AI tools and teaming:

```bash
python3 love_cli.py
# Then in CLI:
> /grok  # Launch Grok CLI component
grok> /team  # Enable team mode (Grok + Claude collaboration)
grok> view file my_code.py  # Natural language file operations
grok> create file new_feature.py with content class NewFeature: pass
grok> run python -m pytest  # Execute commands
grok> search def test_  # Search codebase
grok> @claude Review this function  # Relay to Claude
```

**Grok CLI Features:**
- **Natural Language Commands**: "view file", "create file", "run command", "search code"
- **Teaming Modes**: `/as grok`, `/as claude`, `/team` for different collaboration styles
- **Context Awareness**: Accesses hub memories for relevant coding context
- **File Operations**: AI-powered editing with `str_replace_editor`, directory listing
- **System Integration**: Restricted bash/python execution with mode-based permissions

### Method 4: Collaborative Coding

Use different AIs for different parts:

```python
# Claude: Write the main API logic
# Grok: Create error handling
# Swarm: Design database schema

# Then combine their outputs into a complete application!
```

---

## 💡 Coding Use Cases

### ✅ Proven Capabilities (Tested)

1. **Algorithm Implementation**
   - String manipulation
   - Sorting algorithms
   - Prime number checkers
   - Data structures

2. **Web Development**
   - FastAPI routes
   - Error handling middleware
   - Database models (SQLAlchemy)
   - REST API endpoints

3. **Code Review & Optimization**
   - Get suggestions from multiple AIs
   - Compare different implementation approaches
   - Ask for performance optimization tips

### 🎯 Best Practices

1. **Be Specific**: "Write a Python function that validates email using regex"
   - Better than: "Help me with validation"

2. **Request Format**: "Just the code, no explanation"
   - Gets cleaner output for copy-paste

3. **Iterate**: If output isn't perfect, refine your prompt
   - "Make it more efficient"
   - "Add error handling"
   - "Use type hints"

4. **Compare**: Ask same question to 2-3 AIs, pick the best solution

---

## 📊 Performance Comparison

| AI | Speed | Quality | Best For |
|----|-------|---------|----------|
| **Claude** | ⚡⚡⚡ | ⭐⭐⭐⭐⭐ | Production code |
| **Grok** | ⚡⚡⚡ | ⭐⭐⭐⭐ | Explanations & creativity |
| **Swarm** | ⚡ | ⭐⭐⭐ | Local/private, distributed systems |

---

## 🔧 System Status

### Running Services:
- **Hub**: `http://localhost:9003` (Coordinator)
- **Swarm API**: `http://localhost:8001` (Local Ollama backend)
- **Ollama**: `http://localhost:11434` (LLM server)

### Check Status:
```bash
# Hub health
curl http://localhost:9003/health

# Swarm health
curl http://localhost:8001/status

# Ollama models
curl http://localhost:11434/api/tags
```

---

## 🎓 Example Coding Session

Ask Claude to create a complete Flask app:

```python
# Prompt to Claude:
"Create a minimal Flask API with GET /users and POST /users endpoints.
Include SQLAlchemy models. Just the code."

# Claude returns a complete, working Flask application
# Copy, paste, run: python app.py
# It works!
```

Ask Grok for code review:

```python
# Prompt to Grok:
"Review this code and suggest improvements: [paste code]"

# Grok provides detailed feedback on:
# - Potential bugs
# - Security issues
# - Performance optimizations
# - Better patterns
```

Ask Swarm for distributed architecture:

```python
# Prompt to Swarm:
"How would you design a distributed cache system?"

# Swarm provides architecture focused on:
# - Mesh networking
# - Peer-to-peer communication
# - Decentralized coordination
```

---

## 💻 Remote Execution for Coding

The system now supports remote command execution, allowing AIs to run code, tests, and tools directly on your laptop:

### Safe Commands (Execute Immediately)
- `python my_script.py` - Run Python scripts
- `npm test` - Run tests
- `git status` - Check repository status
- `make build` - Build projects
- `docker run hello-world` - Container operations

### Dangerous Commands (Require Confirmation)
- `rm -rf /tmp/test` - File deletion
- `sudo apt update` - System administration
- `shutdown now` - System control

### Using Remote Execution
1. **Via Browser Extension**: Type command in popup and execute
2. **Via API**: `POST /execute` with authenticated request
3. **Via CLI**: `python3 love_cli.py execute "command"`

### Coding Workflow
1. AI writes code collaboratively
2. AI executes tests: `pytest test_file.py`
3. AI runs linters: `flake8 my_code.py`
4. AI builds project: `python setup.py build`
5. AI commits changes: `git add . && git commit -m "AI improvements"`

**Safety Note**: All executions are logged and require your approval for dangerous operations.

---

## 🚦 Next Steps

1. **Try the CLI**: `python3 love_cli.py`
2. **Run the coding tests**: `python3 test_coding.py`
3. **Experiment with collaborative coding**: `python3 collaborative_coding.py`
4. **Build something!** Use all three AIs to create a real project

---

## 📝 Tips & Tricks

- **Short prompts work best** for Claude and Grok
- **Swarm is slower** - use for local/private tasks only
- **Compare outputs** - different AIs = different perspectives

## 🔄 Workflow Integration

The multi-model sync workflow is now active for AI-to-AI memory sharing:
- **Webhook URL:** http://localhost:5678/webhook/multi-sync
- **Usage:** POST with JSON body like `{"model": "grok"}` to trigger sync.
- **Features:** Token truncation, optional cloud sync, error logging.

Test with: `curl -X POST http://localhost:5678/webhook/multi-sync -H "Content-Type: application/json" -d '{"model": "grok"}'`
- **Iterate** - refine prompts if first output isn't perfect
- **Memory sovereignty** - All conversations are stored in private memory
- **Use `/to all`** carefully (can timeout with slow AIs like Swarm)

---

**Happy Coding! 🎉**

All three AIs are operational and ready to help you build amazing things!
