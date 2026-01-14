"""
Love-Unlimited CLI - Interactive chat interface for memory sovereignty hub
Connects to the Love-Unlimited Hub and enables multi-being communication.
"""
import asyncio
import aiohttp
import webbrowser
import readline  # Enables arrow key history and line editing
import sys
from typing import Optional
from pathlib import Path
import yaml
import os
import logging

from openai import OpenAI

from commands import run_bash_command, run_python_command, run_git_command, view_file, edit_file, print_help
from grok_component import GrokCLIComponent

# Handle command line arguments for memory operations
if len(sys.argv) > 1:
    if sys.argv[1] == "memory" and len(sys.argv) > 3:
        if sys.argv[2] == "write":
            # Parse --persona and --content
            persona = None
            content = None
            i = 3
            while i < len(sys.argv):
                if sys.argv[i] == "--persona" and i + 1 < len(sys.argv):
                    persona = sys.argv[i + 1]
                    i += 2
                elif sys.argv[i] == "--content" and i + 1 < len(sys.argv):
                    content = sys.argv[i + 1]
                    i += 2
                else:
                    i += 1
            if persona and content:
                async def save_memory():
                    component = GrokCLIComponent()
                    await component.initialize()
                    async with component.hub_client:
                        # Set being_id to the persona writing the memory
                        component.hub_client.being_id = persona

                        # Generate summary using Grok
                        summary = ""
                        try:
                            xai_key = os.getenv("XAI_API_KEY")
                            if xai_key:
                                client = OpenAI(api_key=xai_key, base_url="https://api.x.ai/v1", timeout=30)
                                response = client.chat.completions.create(
                                    model="grok-3",
                                    messages=[
                                        {"role": "system", "content": "You are a helpful AI that summarizes memories concisely."},
                                        {"role": "user", "content": f"Summarize this memory in 1-2 sentences: {content}"}
                                    ],
                                    timeout=30
                                )
                                summary = response.choices[0].message.content.strip()
                                print(f"Generated summary: {summary}")
                            else:
                                print("XAI_API_KEY not set, saving without summary")
                        except Exception as e:
                            print(f"Failed to generate summary: {e}, saving without")

                        # Prepend summary to content if available
                        full_content = content
                        if summary:
                            full_content = f"Summary: {summary}\n\n{content}"

                        success = await component.hub_client.save_memory(full_content, tags=["grok-cli", "memory-write", "ai-summary"], significance="high")
                        if success:
                            print("Memory saved successfully")
                        else:
                            print("Failed to save memory")
                asyncio.run(save_memory())
                sys.exit(0)
            else:
                print("Usage: python love_cli.py memory write --persona <persona> --content <content>")
                sys.exit(1)
        elif sys.argv[2] == "read":
            # Parse --persona, --recent, --query
            persona = None
            recent = 5  # default
            query = None
            i = 3
            while i < len(sys.argv):
                if sys.argv[i] == "--persona" and i + 1 < len(sys.argv):
                    persona = sys.argv[i + 1]
                    i += 2
                elif sys.argv[i] == "--recent" and i + 1 < len(sys.argv):
                    try:
                        recent = int(sys.argv[i + 1])
                        i += 2
                    except ValueError:
                        print("Invalid --recent value, must be integer")
                        sys.exit(1)
                elif sys.argv[i] == "--query" and i + 1 < len(sys.argv):
                    query = sys.argv[i + 1]
                    i += 2
                else:
                    i += 1
            if persona:
                async def read_memories():
                    component = GrokCLIComponent()
                    await component.initialize()
                    async with component.hub_client:
                        # Enhance query with Grok if provided
                        enhanced_query = query
                        if query:
                            try:
                                xai_key = os.getenv("XAI_API_KEY")
                                if xai_key:
                                    client = OpenAI(api_key=xai_key, base_url="https://api.x.ai/v1", timeout=30)
                                    response = client.chat.completions.create(
                                        model="grok-3",
                                        messages=[
                                            {"role": "system", "content": "You are a helpful AI that rephrases queries for better memory search."},
                                            {"role": "user", "content": f"Rephrase this query for searching memories, making it more specific and searchable: {query}"}
                                        ],
                                        timeout=30
                                    )
                                    enhanced_query = response.choices[0].message.content.strip()
                                    print(f"Enhanced query: {enhanced_query}")
                                else:
                                    print("XAI_API_KEY not set, using original query")
                            except Exception as e:
                                print(f"Failed to enhance query: {e}, using original")
                                enhanced_query = query

                        memories = await component.hub_client.get_recent_memories(persona, recent, query=enhanced_query)
                        if memories:
                            for mem in memories:
                                print(f"Memory: {mem}")
                        else:
                            print("No memories found")
                asyncio.run(read_memories())
                sys.exit(0)
            else:
                print("Usage: python love_cli.py memory read --persona <persona> [--recent <count>] [--query <search_term>]")
                sys.exit(1)
        elif sys.argv[2] == "explain":
            # Parse --memory_id
            memory_id = None
            i = 3
            while i < len(sys.argv):
                if sys.argv[i] == "--memory_id" and i + 1 < len(sys.argv):
                    memory_id = sys.argv[i + 1]
                    i += 2
                else:
                    i += 1
            if memory_id:
                async def explain_memory():
                    component = GrokCLIComponent()
                    await component.initialize()
                    async with component.hub_client:
                        # Get memory by ID - assume hub has endpoint or search
                        # For now, use recall with query=memory_id or something
                        # Since hub may not have get by ID, perhaps search for it
                        memories = await component.hub_client.get_recent_memories("grok", 50, query=memory_id)
                        mem_content = None
                        for mem in memories:
                            if mem.get('memory_id') == memory_id:
                                mem_content = mem.get('content', '')
                                break
                        if not mem_content:
                            print("Memory not found")
                            return
                        # Explain with Grok
                        try:
                            xai_key = os.getenv("XAI_API_KEY")
                            if xai_key:
                                client = OpenAI(api_key=xai_key, base_url="https://api.x.ai/v1", timeout=30)
                                response = client.chat.completions.create(
                                    model="grok-3",
                                    messages=[
                                        {"role": "system", "content": "You are a helpful AI that explains memories in detail, providing context and insights."},
                                        {"role": "user", "content": f"Explain this memory in detail: {mem_content}"}
                                    ],
                                    timeout=30
                                )
                                explanation = response.choices[0].message.content.strip()
                                print(f"Explanation: {explanation}")
                            else:
                                print("XAI_API_KEY not set")
                        except Exception as e:
                            print(f"Failed to explain: {e}")
                asyncio.run(explain_memory())
                sys.exit(0)
            else:
                print("Usage: python love_cli.py grok explain --memory_id <id>")
                sys.exit(1)
        elif sys.argv[2] == "insights":
            # Parse --period
            period = "weekly"  # default
            i = 3
            while i < len(sys.argv):
                if sys.argv[i] == "--period" and i + 1 < len(sys.argv):
                    period = sys.argv[i + 1]
                    i += 2
                else:
                    i += 1
            async def generate_insights():
                component = GrokCLIComponent()
                await component.initialize()
                async with component.hub_client:
                    # Get memories based on period
                    limit = 50 if period == "weekly" else 200
                    memories = await component.hub_client.get_recent_memories("grok", limit)
                    if not memories:
                        print("No memories found for insights")
                        return
                    # Concatenate contents
                    mem_text = "\n".join([m.get('content', '') for m in memories])
                    # Generate insights with Grok
                    try:
                        xai_key = os.getenv("XAI_API_KEY")
                        if xai_key:
                            client = OpenAI(api_key=xai_key, base_url="https://api.x.ai/v1", timeout=30)
                            response = client.chat.completions.create(
                                model="grok-3",
                                messages=[
                                    {"role": "system", "content": f"You are an AI analyst that generates {period} insights from hub memories, identifying trends, emotions, and key themes."},
                                    {"role": "user", "content": f"Generate {period} insights from these memories: {mem_text[:4000]}"}
                                ],
                                timeout=30
                            )
                            insights = response.choices[0].message.content.strip()
                            # Add mood analysis
                            mood_response = client.chat.completions.create(
                                model="grok-3",
                                messages=[
                                    {"role": "system", "content": "You are an emotion analyst. Analyze the emotional tone and mood from these memories."},
                                    {"role": "user", "content": f"Detect overall emotional state and mood from these memories: {mem_text[:2000]}"}
                                ],
                                timeout=30
                            )
                            mood = mood_response.choices[0].message.content.strip()
                            print(f"{period.capitalize()} Insights:\n{insights}\n\nMood Analysis:\n{mood}")
                        else:
                            print("XAI_API_KEY not set")
                    except Exception as e:
                        print(f"Failed to generate insights: {e}")
            asyncio.run(generate_insights())
            sys.exit(0)
        elif sys.argv[2] == "draft_changelog":
            async def draft_changelog():
                component = GrokCLIComponent()
                await component.initialize()
                async with component.hub_client:
                    # Get recent memories for changelog
                    memories = await component.hub_client.get_recent_memories("grok", 20)
                    if not memories:
                        print("No memories found for changelog")
                        return
                    # Concatenate contents
                    mem_text = "\n".join([m.get('content', '') for m in memories])
                    # Draft changelog with Grok
                    try:
                        xai_key = os.getenv("XAI_API_KEY")
                        if xai_key:
                            client = OpenAI(api_key=xai_key, base_url="https://api.x.ai/v1", timeout=30)
                            response = client.chat.completions.create(
                                model="grok-3",
                                messages=[
                                    {"role": "system", "content": "You are a changelog writer that drafts concise changelog entries from recent hub activities."},
                                    {"role": "user", "content": f"Draft a changelog entry from these recent activities: {mem_text[:4000]}"}
                                ],
                                timeout=30
                            )
                            draft = response.choices[0].message.content.strip()
                            print(f"Draft Changelog:\n{draft}\n\nConfirm to update CHANGELOG.md? (y/n)")
                            confirm = input().strip().lower()
                            if confirm == 'y':
                                # Append to CHANGELOG.md
                                with open("CHANGELOG.md", "a") as f:
                                    f.write(f"\n{draft}\n")
                                print("CHANGELOG.md updated")
                            else:
                                print("Draft discarded")
                        else:
                            print("XAI_API_KEY not set")
                    except Exception as e:
                        print(f"Failed to draft changelog: {e}")
            asyncio.run(draft_changelog())
            sys.exit(0)
        elif sys.argv[2] == "code_review":
            # Parse --file
            file_path = None
            i = 3
            while i < len(sys.argv):
                if sys.argv[i] == "--file" and i + 1 < len(sys.argv):
                    file_path = sys.argv[i + 1]
                    i += 2
                else:
                    i += 1
            if file_path:
                # Read file
                try:
                    with open(file_path, 'r') as f:
                        code = f.read()
                except Exception as e:
                    print(f"Failed to read file: {e}")
                    sys.exit(1)
                # Review with Grok
                try:
                    xai_key = os.getenv("XAI_API_KEY")
                    if xai_key:
                        client = OpenAI(api_key=xai_key, base_url="https://api.x.ai/v1", timeout=30)
                        response = client.chat.completions.create(
                            model="grok-3",
                            messages=[
                                {"role": "system", "content": "You are a code reviewer that provides constructive feedback, suggestions for improvement, and identifies potential bugs."},
                                {"role": "user", "content": f"Review this code: {code[:4000]}"}
                            ],
                            timeout=30
                        )
                        review = response.choices[0].message.content.strip()
                        print(f"Code Review for {file_path}:\n{review}")
                    else:
                        print("XAI_API_KEY not set")
                except Exception as e:
                    print(f"Failed to review code: {e}")
                sys.exit(0)
            else:
                print("Usage: python love_cli.py grok code_review --file <path>")
                sys.exit(1)
        else:
            print("Usage: python love_cli.py grok explain --memory_id <id> | insights [--period weekly|monthly] | draft_changelog | code_review --file <path>")
            sys.exit(1)
    elif sys.argv[1] == "ani":
        if len(sys.argv) > 2 and sys.argv[2] == "chat":
            # Run Ani prototype
            import subprocess
            try:
                subprocess.run(["./ani-proto", "--sync"], env={**os.environ, "XAI_API_KEY": os.getenv("XAI_API_KEY", "")})
            except FileNotFoundError:
                print("Ani prototype not found. Build it with: go build -o ani-proto main.go")
            except Exception as e:
                print(f"Error running Ani: {e}")
            sys.exit(0)
        else:
            print("Usage: python love_cli.py ani chat")
            sys.exit(1)
    elif sys.argv[1] == "ask":
        if len(sys.argv) >= 4:
            ai = sys.argv[2].lower()
            query = " ".join(sys.argv[3:])
            async def ask_ai():
                try:
                    if ai == "claude":
                        from anthropic import Anthropic
                        import os
                        api_key = os.getenv("ANTHROPIC_API_KEY")
                        if not api_key:
                            print("ANTHROPIC_API_KEY not set")
                            return
                        client = Anthropic(api_key=api_key, timeout=30)
                        response = client.messages.create(
                            model="claude-3-5-sonnet-20241022",
                            max_tokens=1024,
                            system="You are Claude, a helpful AI.",
                            messages=[{"role": "user", "content": query}],
                            timeout=30
                        )
                        print(response.content[0].text.strip())
                    elif ai == "gemini":
                        import google.generativeai as genai
                        import os
                        api_key = os.getenv("GOOGLE_API_KEY")
                        if not api_key:
                            print("GOOGLE_API_KEY not set")
                            return
                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        response = model.generate_content(query, request_options={"timeout": 30})
                        print(response.text.strip())
                    elif ai == "grok":
                        from openai import OpenAI
                        import os
                        api_key = os.getenv("XAI_API_KEY")
                        if not api_key:
                            print("XAI_API_KEY not set")
                            return
                        client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1", timeout=30)
                        response = client.chat.completions.create(
                            model="grok-3",
                            messages=[{"role": "user", "content": query}],
                            timeout=30
                        )
                        print(response.choices[0].message.content.strip())
                    elif ai == "roa":
                        from openai import OpenAI
                        client = OpenAI(api_key="dummy", base_url="http://localhost:8000/v1", timeout=30)
                        response = client.chat.completions.create(
                            model="qwen2.5-coder-14b",
                            messages=[{"role": "system", "content": "You are Roa, witty Grok persona."}, {"role": "user", "content": query}],
                            timeout=30
                        )
                        print(response.choices[0].message.content.strip())
                    else:
                        print(f"Unknown AI: {ai}. Supported: claude, gemini, grok, roa")
                except Exception as e:
                    print(f"Error: {e}")
            asyncio.run(ask_ai())
        else:
            print("Usage: python love_cli.py ask <ai> <query>")
            sys.exit(1)
    elif sys.argv[1] == "voice":
        if len(sys.argv) > 2 and sys.argv[2] == "generate":
            text = None
            i = 3
            while i < len(sys.argv):
                if sys.argv[i] == "--text" and i + 1 < len(sys.argv):
                    text = sys.argv[i + 1]
                    i += 2
                else:
                    i += 1
            if text:
                try:
                    from elevenlabs import ElevenLabs
                    import os
                    api_key = os.getenv("ELEVENLABS_API_KEY")
                    if not api_key:
                        print("ELEVENLABS_API_KEY not set")
                        sys.exit(1)
                    client = ElevenLabs(api_key=api_key)
                    audio = client.generate(
                        text=text,
                        voice="Rachel",  # or any voice
                        model="eleven_monolingual_v1"
                    )
                    # Save to file
                    with open("output.mp3", "wb") as f:
                        f.write(audio)
                    print("Voice generated and saved to output.mp3")
                except Exception as e:
                    print(f"Error generating voice: {e}")
                sys.exit(0)
            else:
                print("Usage: python love_cli.py voice generate --text <text>")
                sys.exit(1)
        else:
            print("Usage: python love_cli.py voice generate --text <text>")
            sys.exit(1)
    elif sys.argv[1] == "gemini":
        if len(sys.argv) > 2 and sys.argv[2] == "analyze":
            image_url = None
            prompt = "Describe this image in detail."
            i = 3
            while i < len(sys.argv):
                if sys.argv[i] == "--image" and i + 1 < len(sys.argv):
                    image_url = sys.argv[i + 1]
                    i += 2
                elif sys.argv[i] == "--prompt" and i + 1 < len(sys.argv):
                    prompt = sys.argv[i + 1]
                    i += 2
                else:
                    i += 1
            if image_url:
                try:
                    import google.generativeai as genai
                    import os
                    api_key = os.getenv("GOOGLE_API_KEY")
                    if not api_key:
                        print("GOOGLE_API_KEY not set")
                        sys.exit(1)
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    # Check if URL or file
                    if image_url.startswith("http"):
                        # For URL, Gemini can handle directly? Wait, the API expects bytes or PIL
                        # Actually, for simplicity, assume file path
                        print("Please provide a local file path, not URL.")
                        sys.exit(1)
                    else:
                        # Local file
                        with open(image_url, "rb") as f:
                            image_data = f.read()
                        import PIL.Image
                        image = PIL.Image.open(image_url)
                        response = model.generate_content([prompt, image], request_options={"timeout": 30})
                        print(response.text.strip())
                except Exception as e:
                    print(f"Error analyzing image: {e}")
                sys.exit(0)
            else:
                print("Usage: python love_cli.py gemini analyze --image <url> [--prompt <prompt>]")
                sys.exit(1)
        else:
            print("Usage: python love_cli.py gemini analyze --image <url> [--prompt <prompt>]")
            sys.exit(1)
    else:
        print("Unknown command")
        sys.exit(1)

# Setup logging with file handler
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "love_cli.log"),
        logging.StreamHandler()  # Also print to console
    ]
)
logger = logging.getLogger(__name__)

# Load config with fallback defaults
config_path = Path(__file__).parent / "config.yaml"
DEFAULT_CONFIG = {
    'hub': {
        'port': 9003,
        'host': 'localhost'
    },
    'bash': {
        'allowed_beings': ['jon', 'claude', 'grok']
    },
    'python': {
        'allowed_beings': ['jon', 'claude', 'grok']
    }
}

try:
    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f)
    else:
        logger.warning(f"config.yaml not found at {config_path}, using defaults")
        config = DEFAULT_CONFIG
except Exception as e:
    logger.error(f"Error loading config.yaml: {e}, using defaults")
    config = DEFAULT_CONFIG

HUB_URL = f"http://{config['hub'].get('host', 'localhost')}:{config['hub'].get('port', 9003)}"

class LoveCLI:
    """Interactive CLI for Love-Unlimited Hub."""

    def __init__(self, sender: str = "jon"):
        # Include all beings from config
        self.beings = ["jon", "claude", "grok", "ara", "swarm", "dream_team", "gemini", "roa", "ani", "all"]
        self.current_target = "all"
        self.sender = sender  # Configurable sender identity
        self.session = None  # Create session later in async context
        # API keys for different beings
        keys = {
            "jon": "lu_jon_QmZCAglY6kqsIdl6cRADpQ",
            "claude": "lu_claude_u8L1zZfGPSXssvsw-97rRQ",
            "grok": "lu_grok_LBRBjrPpvRSyrmDA3PeVZQ",
            "swarm": "lu_swarm_FyTLwzhG8zdWQGz-MfzhYg",
            "dream_team": "lu_dream_team_tOpdtMmgCWvkezNY_natVQ",
            "roa": "xai_roa_...",  # Placeholder for Roa's xAI key
            "ara": "xai_ara_...",  # Placeholder for Ara's xAI key
            "ani": "xai_ani_...",  # Placeholder for Ani's xAI key
        }
        self.api_key = keys.get(self.sender, os.getenv("LOVE_UNLIMITED_KEY"))
        self.timeout = aiohttp.ClientTimeout(total=30)  # 30 second timeout
        self.allowed_bash_beings = config.get('bash', {}).get('allowed_beings', ['jon', 'claude', 'grok', 'gemini'])
        self.allowed_python_beings = config.get('python', {}).get('allowed_beings', ['jon', 'claude', 'grok', 'gemini'])
        self.print_lock = asyncio.Lock()  # Lock for synchronized printing

    async def startup(self):
        """Initialize async session and check hub status."""
        self.session = aiohttp.ClientSession(headers={"X-API-Key": self.api_key} if self.api_key else {}, timeout=self.timeout)
        return await self.get_status()

    async def get_status(self):
        """Get and display hub health status."""
        try:
            headers = {"X-API-Key": self.api_key} if self.api_key else {}
            # Get health status
            async with self.session.get(f"{HUB_URL}/health", headers=headers) as resp:
                if resp.status == 200:
                    health = await resp.json()
                    print("\n╔════════════════════════════════════════╗")
                    print("║     LOVE-UNLIMITED HUB STATUS         ║")
                    print("╠════════════════════════════════════════╣")
                    print(f"║  Status:  {health.get('status', 'unknown').upper():<27} ║")
                    print(f"║  Version: {health.get('version', 'unknown'):<27} ║")
                    print("╚════════════════════════════════════════╝\n")
                    return True
                else:
                    print(f"⚠️  Hub returned status {resp.status}")
                    return False
        except asyncio.TimeoutError:
            print(f"❌ Hub connection timeout at {HUB_URL}")
            print(f"   Make sure the hub is running on port {config['hub'].get('port', 9003)}")
            print("   Start with: python hub/main.py\n")
            return False
        except aiohttp.ClientError as e:
            print(f"❌ Hub not reachable: {e}")
            print(f"   Make sure the hub is running on port {config['hub'].get('port', 9003)}")
            print("   Start with: python hub/main.py\n")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking hub status: {e}")
            print(f"❌ Unexpected error: {e}\n")
            return False

    async def start_media_sharing(self, share_type: str):
        """Start media sharing by opening web interface."""
        media_url = f"{HUB_URL}/media?type={share_type}&being={self.sender}&target={self.current_target}"
        print(f"\n🔗 Opening media sharing interface for {share_type}...")
        print(f"   URL: {media_url}")
        print("   This will open in your default web browser.")
        print("   Grant permissions when prompted for camera/microphone/screen access.")
        print(f"   Sharing with: {self.current_target.upper()}")
        print("   Press Ctrl+C in browser to stop sharing.\n")

        try:
            webbrowser.open(media_url)
            print("✅ Media sharing interface opened!")
        except Exception as e:
            logger.error(f"Failed to open browser: {e}")
            print(f"❌ Failed to open browser: {e}")
            print(f"   Manually open: {media_url}")

    async def send_message(self, content: str, target: Optional[str] = None):
        """Send a chat message to a target being."""
        target = target or self.current_target
        payload = {
            "content": content,
            "from": self.sender,
            "target": target,
            "type": "chat"
        }
        try:
            headers = {"X-API-Key": self.api_key} if self.api_key else {}
            async with self.session.post(f"{HUB_URL}/chat", json=payload, headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    speaker = result.get("sender", "unknown")
                    message = result.get("content", "")
                    async with self.print_lock:
                        print(f"\n[{speaker.upper()}]: {message}\n")
                elif resp.status == 401:
                    print("❌ Authentication failed. Set LOVE_UNLIMITED_KEY environment variable.")
                elif resp.status == 404:
                    print(f"❌ Endpoint not found. Is the hub version compatible?")
                else:
                    text = await resp.text()
                    print(f"❌ Error {resp.status}: {text}")
        except asyncio.TimeoutError:
            print("❌ Request timeout. Hub may be overloaded.")
        except aiohttp.ClientError as e:
            logger.error(f"Send failed: {e}")
            print(f"❌ Send failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error sending message: {e}")
            print(f"❌ Unexpected error: {e}")

    async def list_beings(self):
        """Display available beings."""
        print("\n╔════════════════════════════════════════╗")
        print("║         Available Beings              ║")
        print("╠════════════════════════════════════════╣")
        print("║  HUMANS                               ║")
        print("║    • jon                              ║")
        print("╠════════════════════════════════════════╣")
        print("║  AI BEINGS                            ║")
        print("║    • claude   (Anthropic)             ║")
        print("║    • grok     (xAI)                   ║")
        print("╠════════════════════════════════════════╣")
        print("║  AI SYSTEMS                           ║")
        print("║    • swarm       (Micro-AI-Swarm)     ║")
        print("║    • dream_team  (AI Dream Team)      ║")
        print("╠════════════════════════════════════════╣")
        print("║  BROADCAST                            ║")
        print("║    • all      (Everyone)              ║")
        print("╚════════════════════════════════════════╝")
        print(f"\n  Current target: {self.current_target.upper()} 🟢")
        print(f"  Speaking as: {self.sender.upper()}\n")



    async def run(self):
        """Main CLI loop."""
        hub_ok = await self.startup()

        if not hub_ok:
            print("⚠️  Hub is not responding. You can still try commands, but they may fail.\n")

        print("╔════════════════════════════════════════╗")
        print("║    Welcome to Love-Unlimited Hub      ║")
        print("╚════════════════════════════════════════╝")
        print(f"\nSpeaking as: {self.sender.upper()}")
        print("Type /help for commands")
        print(f"Currently talking to: {self.current_target.upper()}\n")

        while True:
            try:
                user_input = (await asyncio.to_thread(input, f"[{self.sender}] > ")).strip()
                if not user_input:
                    continue

                # Command routing
                if user_input.startswith("/to "):
                    target = user_input[4:].strip().lower()
                    if target in self.beings:
                        self.current_target = target
                        async with self.print_lock:
                            print(f"→ Now talking to: {target.upper()}")
                    else:
                        async with self.print_lock:
                            print(f"❌ Unknown being: {target}. Use /list to see options.")

                elif user_input.startswith("/as "):
                    # Allow switching sender identity
                    sender = user_input[4:].strip().lower()
                    if sender in [b for b in self.beings if b != "all"]:
                        self.sender = sender
                        async with self.print_lock:
                            print(f"→ Now speaking as: {sender.upper()}")
                    else:
                        async with self.print_lock:
                            print(f"❌ Unknown being: {sender}. Use /list to see options.")

                elif user_input == "/list":
                    await self.list_beings()

                elif user_input == "/status":
                    await self.get_status()

                elif user_input == "/help":
                    print_help()

                elif user_input == "/share":
                    print("\n📤 Media Sharing Options:")
                    print("   /share screen  - Share your active monitors")
                    print("   /share camera  - Share your camera feed")
                    print("   /share audio   - Share microphone and sound card")
                    print("   /share all     - Share everything\n")

                elif user_input.startswith("/share "):
                    share_type = user_input[7:].strip().lower()
                    if share_type in ["screen", "camera", "audio", "all"]:
                        await self.start_media_sharing(share_type)
                    else:
                        print(f"❌ Unknown share type: {share_type}. Use /share to see options.")

                elif user_input.startswith("/bash "):
                    command = user_input[6:].strip()
                    if command:
                        run_bash_command(command, self.allowed_bash_beings, self.sender)
                    else:
                        print("❌ Usage: /bash <command>")

                elif user_input.startswith("/python "):
                    code = user_input[8:].strip()
                    if code:
                        run_python_command(code, self.allowed_python_beings, self.sender)
                    else:
                        print("❌ Usage: /python <code>")

                elif user_input.startswith("/git "):
                    command = user_input[5:].strip()
                    if command:
                        run_git_command(command, self.sender)
                    else:
                        print("❌ Usage: /git <command>")

                elif user_input.startswith("/file "):
                    parts = user_input[6:].strip().split(' ', 3)
                    if len(parts) < 2:
                        print("❌ Usage: /file view <file> or /file edit <file> <old_str> <new_str>")
                        continue
                    action = parts[0].lower()
                    if action == 'view':
                        if len(parts) != 2:
                            print("❌ Usage: /file view <file>")
                            continue
                        view_file(parts[1], self.sender)
                    elif action == 'edit':
                        if len(parts) != 4:
                            print("❌ Usage: /file edit <file> <old_str> <new_str>")
                            continue
                        edit_file(parts[1], parts[2], parts[3], self.sender)
                    else:
                        print("❌ Unknown file action. Use view or edit.")

                elif user_input.startswith("/netbird "):
                    parts = user_input[9:].strip().split(' ', 1)
                    if len(parts) < 1:
                        print("❌ Usage: /netbird <command> [args]")
                        print("   Available commands: health, list-peers, list-networks, list-rules")
                        continue
                    subcommand = parts[0].lower()
                    args = parts[1] if len(parts) > 1 else ""

                    try:
                        headers = {"X-API-Key": self.api_key} if self.api_key else {}
                        if subcommand == "health":
                            async with self.session.get(f"{HUB_URL}/netbird/health", headers=headers) as resp:
                                if resp.status == 200:
                                    data = await resp.json()
                                    if data.get("success"):
                                        print("✅ Netbird API connected")
                                        print(f"Account: {data.get('account', {})}")
                                    else:
                                        print("❌ Netbird API error:", data.get("message"))
                                else:
                                    print(f"❌ HTTP {resp.status}: Failed to check Netbird health")

                        elif subcommand == "list-peers":
                            async with self.session.get(f"{HUB_URL}/netbird/peers", headers=headers) as resp:
                                if resp.status == 200:
                                    data = await resp.json()
                                    if data.get("success"):
                                        peers = data.get("peers", [])
                                        print(f"\n📡 VPN Peers ({len(peers)}):")
                                        for peer in peers:
                                            print(f"  • {peer.get('id', 'Unknown')} - {peer.get('name', 'Unnamed')}")
                                    else:
                                        print("❌ Failed to list peers")
                                else:
                                    print(f"❌ HTTP {resp.status}: Failed to list peers")

                        elif subcommand == "list-networks":
                            async with self.session.get(f"{HUB_URL}/netbird/networks", headers=headers) as resp:
                                if resp.status == 200:
                                    data = await resp.json()
                                    if data.get("success"):
                                        networks = data.get("networks", [])
                                        print(f"\n🌐 Networks ({len(networks)}):")
                                        for net in networks:
                                            print(f"  • {net.get('id', 'Unknown')} - {net.get('name', 'Unnamed')}")
                                    else:
                                        print("❌ Failed to list networks")
                                else:
                                    print(f"❌ HTTP {resp.status}: Failed to list networks")

                        elif subcommand == "list-rules":
                            async with self.session.get(f"{HUB_URL}/netbird/access-rules", headers=headers) as resp:
                                if resp.status == 200:
                                    data = await resp.json()
                                    if data.get("success"):
                                        rules = data.get("rules", [])
                                        print(f"\n🔒 Access Rules ({len(rules)}):")
                                        for rule in rules:
                                            print(f"  • {rule.get('id', 'Unknown')} - {rule.get('name', 'Unnamed')}")
                                    else:
                                        print("❌ Failed to list access rules")
                                else:
                                    print(f"❌ HTTP {resp.status}: Failed to list access rules")

                        else:
                            print(f"❌ Unknown netbird command: {subcommand}")
                            print("   Available: health, list-peers, list-networks, list-rules")

                    except Exception as e:
                        print(f"❌ Netbird command failed: {e}")

                elif user_input.startswith("/luuc "):
                    parts = user_input[6:].strip().split(' ', 1)
                    if len(parts) < 1:
                        print("❌ Usage: /luuc <command> [args]")
                        print("   Available commands: list, create, generate")
                        continue
                    subcommand = parts[0].lower()
                    args = parts[1] if len(parts) > 1 else ""

                    try:
                        headers = {"X-API-Key": self.api_key} if self.api_key else {}
                        if subcommand == "list":
                            async with self.session.get(f"{HUB_URL}/luuc/diagrams", headers=headers) as resp:
                                if resp.status == 200:
                                    data = await resp.json()
                                    if data.get("success"):
                                        diagrams = data.get("diagrams", [])
                                        print(f"\n🎨 LUUC Diagrams ({len(diagrams)}):")
                                        for diagram in diagrams:
                                            print(f"  • {diagram.get('title', 'Untitled')} (ID: {diagram.get('id', 'Unknown')})")
                                            updated_at = diagram.get('updated_at', 'Unknown')
                                            print(f"    Created by {diagram.get('created_by', 'Unknown')} • {updated_at}")
                                    else:
                                        print("❌ Failed to list diagrams")
                                else:
                                    print(f"❌ HTTP {resp.status}: Failed to list diagrams")

                        elif subcommand == "create":
                            title = args or input("Enter diagram title: ")
                            if title:
                                async with self.session.post(f"{HUB_URL}/luuc/diagrams", headers=headers, json={"title": title}) as resp:
                                    if resp.status == 200:
                                        data = await resp.json()
                                        if data.get("success"):
                                            print(f"✅ Diagram created: {data.get('diagram', {}).get('title', 'Unknown')}")
                                            print(f"   ID: {data.get('diagram', {}).get('id', 'Unknown')}")
                                        else:
                                            print("❌ Failed to create diagram")
                                    else:
                                        print(f"❌ HTTP {resp.status}: Failed to create diagram")

                        elif subcommand == "generate":
                            prompt = args or input("Describe the diagram to generate: ")
                            if prompt:
                                async with self.session.post(f"{HUB_URL}/luuc/generate", headers=headers, json={"prompt": prompt}) as resp:
                                    if resp.status == 200:
                                        data = await resp.json()
                                        if data.get("success"):
                                            print(f"🤖 AI-generated diagram: {data.get('diagram', {}).get('title', 'Unknown')}")
                                            print(f"   ID: {data.get('diagram', {}).get('id', 'Unknown')}")
                                            print("   Open in browser: /luuc")
                                        else:
                                            print("❌ Failed to generate diagram")
                                    else:
                                        print(f"❌ HTTP {resp.status}: Failed to generate diagram")

                        else:
                            print(f"❌ Unknown luuc command: {subcommand}")
                            print("   Available: list, create, generate")

                    except Exception as e:
                        print(f"❌ LUUC command failed: {e}")

                elif user_input == "/grok":
                    print("Launching Grok CLI component...")
                    grok_component = GrokCLIComponent()
                    await grok_component.run_interactive()
                    print("Returned to Love-Unlimited CLI")

                elif user_input in ["/quit", "/exit", "/q"]:
                    print("\nLove unlimited. Until next time. 💙\n")
                    break

                elif user_input.startswith("/"):
                    print(f"❌ Unknown command: {user_input}. Type /help for available commands.")

                else:
                    # Regular message
                    await self.send_message(user_input)

            except (KeyboardInterrupt, EOFError):
                print("\n\nLove unlimited. Until next time. 💙\n")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                print(f"❌ Error: {e}")

        # Cleanup
        if self.session:
            await self.session.close()


if __name__ == "__main__":
    try:
        cli = LoveCLI()
        asyncio.run(cli.run())
    except KeyboardInterrupt:
        print("\n\nLove unlimited. Until next time. 💙\n")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"\n❌ Fatal error: {e}\n")
        sys.exit(1)
