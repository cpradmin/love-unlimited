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
                        success = await component.hub_client.save_memory(content, tags=["grok-cli", "memory-write"], significance="high")
                        if success:
                            print("Memory saved successfully")
                        else:
                            print("Failed to save memory")
                asyncio.run(save_memory())
                sys.exit(0)
            else:
                print("Usage: python love_cli.py memory write --persona <persona> --content <content>")
                sys.exit(1)
    else:
        print("Unknown command")
        sys.exit(1)

# Setup logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
        self.beings = ["jon", "claude", "grok", "ara", "swarm", "dream_team", "all"]
        self.current_target = "all"
        self.sender = sender  # Configurable sender identity
        self.session = None  # Create session later in async context
        self.api_key = os.getenv("LOVE_UNLIMITED_KEY")
        self.timeout = aiohttp.ClientTimeout(total=30)  # 30 second timeout
        self.allowed_bash_beings = config.get('bash', {}).get('allowed_beings', ['jon'])
        self.allowed_python_beings = config.get('python', {}).get('allowed_beings', ['jon'])

    async def startup(self):
        """Initialize async session and check hub status."""
        self.session = aiohttp.ClientSession(headers={"X-API-Key": "lu_jon_QmZCAglY6kqsIdl6cRADpQ"}, timeout=self.timeout)
        await self.get_status()

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
                        print(f"→ Now talking to: {target.upper()}")
                    else:
                        print(f"❌ Unknown being: {target}. Use /list to see options.")

                elif user_input.startswith("/as "):
                    # Allow switching sender identity
                    sender = user_input[4:].strip().lower()
                    if sender in [b for b in self.beings if b != "all"]:
                        self.sender = sender
                        print(f"→ Now speaking as: {sender.upper()}")
                    else:
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
