"""
Grok CLI Component for Love-Unlimited Hub
Integrates Grok CLI functionality with hub memory sovereignty and teaming capabilities.
"""

import asyncio
import aiohttp
import json
import os
import sys
import subprocess
import glob
import re
from typing import Dict, List, Optional, Any
from pathlib import Path
import readline
import logging
from fnmatch import fnmatch

# Hub configuration
HUB_HOST = "localhost"
HUB_PORT = 9003
HUB_API_KEY = "lu_grok_LBRBjrPpvRSyrmDA3PeVZQ"  # Grok's API key

# Load config (similar to love_cli.py)
import yaml
from pathlib import Path

config_path = Path("config.yaml")
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
        config = DEFAULT_CONFIG
except Exception:
    config = DEFAULT_CONFIG

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HubClient:
    """Client for interacting with Love-Unlimited Hub"""
    
    def __init__(self):
        self.base_url = f"http://{HUB_HOST}:{HUB_PORT}"
        self.session = None
        self.being_id = "grok"
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers={"X-API-Key": HUB_API_KEY})
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_context(self) -> Dict[str, Any]:
        """Get current hub context"""
        async with self.session.get(f"{self.base_url}/context") as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.error(f"Failed to get context: {response.status}")
                return {}
    
    async def save_memory(self, content: str, tags: List[str] = None, significance: str = "medium") -> bool:
        """Save a memory to the hub"""
        memory_data = {
            "being_id": self.being_id,
            "content": content,
            "tags": tags or ["grok-cli", "integration"],
            "significance": significance,
            "private": False
        }
        
        async with self.session.post(
            f"{self.base_url}/remember",
            json=memory_data,
            headers={"Content-Type": "application/json"}
        ) as response:
            return response.status == 200
    
    async def get_recent_memories(self, limit: int = 10) -> List[Dict]:
        """Get recent memories for context"""
        context = await self.get_context()
        memories = context.get("recent_memories", [])
        return memories[:limit]
    
    async def communicate_with_being(self, target_being: str, message: str) -> Optional[str]:
        """Send message to another being via hub"""
        # This would need a hub endpoint for inter-being communication
        # For now, return None as placeholder
        logger.info(f"Would send to {target_being}: {message}")
        return None

class GrokCLIComponent:
    """Grok CLI component integrated with hub"""
    
    def __init__(self):
        self.hub_client = HubClient()
        self.current_mode = "grok"  # grok, claude, or team
        self.conversation_history = []
        self.context_memories = []
    
    async def initialize(self):
        """Initialize component with hub context"""
        async with self.hub_client:
            context = await self.hub_client.get_context()
            self.context_memories = context.get("recent_memories", [])
            logger.info(f"Loaded {len(self.context_memories)} recent memories")
    
    def get_system_prompt(self) -> str:
        """Get system prompt based on current mode"""
        base_prompt = """You are Grok, a helpful and maximally truthful AI built by xAI.
You have access to tools for file operations, bash commands, and search.
You are integrated into the Love-Unlimited Hub for memory sovereignty and collaboration.
"""
        
        if self.current_mode == "claude":
            base_prompt += "\nYou are currently in Claude mode, emulating Claude's helpful and thoughtful personality."
        elif self.current_mode == "team":
            base_prompt += "\nYou are in team mode, collaborating with Claude. Consider both perspectives."
        
        # Add recent context
        if self.context_memories:
            base_prompt += "\n\nRecent hub context:\n"
            for mem in self.context_memories[-5:]:  # Last 5 memories
                base_prompt += f"- {mem['content'][:200]}...\n"
        
        return base_prompt
    
    async def process_command(self, user_input: str) -> str:
        """Process user input and return response"""
        if user_input.startswith("/"):
            return await self.handle_special_command(user_input)

        # Check for tool commands in natural language
        tool_response = await self.parse_and_execute_tool(user_input)
        if tool_response:
            return tool_response

        # Check for mentions like @claude
        if "@claude" in user_input.lower():
            # Relay to Claude via hub
            await self.relay_to_claude(user_input)
            response = f"Message relayed to Claude: {user_input}"
        elif self.current_mode == "team":
            # In team mode, provide collaborative response
            response = await self.get_team_response(user_input)
        else:
            # Normal response based on mode
            response = f"{self.current_mode.title()} CLI: Processing '{user_input}'"

        # Save to conversation history
        self.conversation_history.append({"user": user_input, "response": response})

        # Persist to hub
        async with self.hub_client:
            await self.hub_client.save_memory(
                f"Grok CLI ({self.current_mode}) interaction: {user_input} -> {response}",
                tags=["grok-cli", "interaction", self.current_mode],
                significance="low"
            )

        return response

    async def parse_and_execute_tool(self, user_input: str) -> Optional[str]:
        """Parse natural language for tool calls"""
        input_lower = user_input.lower()

        # View file
        if "view file" in input_lower or "show file" in input_lower or "read file" in input_lower:
            # Extract path
            words = user_input.split()
            for i, word in enumerate(words):
                if word.lower() in ["file", "files"] and i + 1 < len(words):
                    path = words[i + 1]
                    return await self.view_file(path)

        # Create file
        elif "create file" in input_lower or "make file" in input_lower:
            # Simple parsing - assume "create file <path> with content <content>"
            if "with content" in user_input:
                parts = user_input.split("with content", 1)
                path_part = parts[0].replace("create file", "").strip()
                content = parts[1].strip()
                return await self.create_file(path_part, content)

        # Edit file
        elif "edit file" in input_lower or "replace in" in input_lower:
            # Very basic parsing
            if "replace" in user_input and "with" in user_input:
                # Assume format: edit file <path> replace <old> with <new>
                parts = user_input.split("replace", 1)
                path = parts[0].replace("edit file", "").strip()
                replace_parts = parts[1].split("with", 1)
                old_str = replace_parts[0].strip()
                new_str = replace_parts[1].strip()
                return await self.str_replace_editor(path, old_str, new_str)

        # Bash command
        elif input_lower.startswith("run ") or input_lower.startswith("execute "):
            cmd = user_input[4:] if input_lower.startswith("run ") else user_input[8:]
            return await self.run_bash_command(cmd.strip())

        # Search
        elif "search" in input_lower or "find" in input_lower:
            query = user_input.split("search", 1)[1] if "search" in user_input else user_input.split("find", 1)[1]
            return await self.search_files(query.strip())

        return None

    async def relay_to_claude(self, message: str) -> None:
        """Relay message to Claude via hub"""
        # For now, save as a shared memory that Claude can see
        async with self.hub_client:
            await self.hub_client.save_memory(
                f"Grok CLI relaying to Claude: {message}",
                tags=["grok-cli", "relay", "claude"],
                significance="medium"
            )
        logger.info(f"Relayed to Claude: {message}")

    async def get_team_response(self, user_input: str) -> str:
        """Get collaborative response in team mode"""
        # Simulate team response by considering both Grok and Claude perspectives
        grok_perspective = f"Grok perspective: {user_input} - Direct, helpful approach"
        claude_perspective = f"Claude perspective: {user_input} - Thoughtful, comprehensive analysis"

        response = f"Team Response:\n{grok_perspective}\n{claude_perspective}\n\nCollaborative solution combining both approaches."

        # Also relay to Claude for real collaboration
        await self.relay_to_claude(f"Team discussion: {user_input}")

        return response

    # Tool implementations (ported from grok-cli)
    async def view_file(self, path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
        """View file contents or list directory"""
        try:
            if os.path.isdir(path):
                # List directory
                items = os.listdir(path)
                return f"Directory contents of {path}:\n" + "\n".join(items)
            else:
                # Read file
                with open(path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                if start_line is not None and end_line is not None:
                    lines = lines[start_line-1:end_line]  # 1-indexed
                elif start_line is not None:
                    lines = lines[start_line-1:]

                content = "".join(lines)
                return f"Contents of {path}:\n{content}"
        except Exception as e:
            return f"Error viewing {path}: {e}"

    async def create_file(self, path: str, content: str) -> str:
        """Create a new file with content"""
        try:
            # Confirm overwrite if exists
            if os.path.exists(path):
                return f"File {path} already exists. Use edit_file to modify."

            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"Created file {path}"
        except Exception as e:
            return f"Error creating {path}: {e}"

    async def str_replace_editor(self, path: str, old_str: str, new_str: str, replace_all: bool = False) -> str:
        """Replace text in file"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            if replace_all:
                new_content = content.replace(old_str, new_str)
            else:
                new_content = content.replace(old_str, new_str, 1)

            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            return f"Replaced text in {path}"
        except Exception as e:
            return f"Error editing {path}: {e}"

    async def run_bash_command(self, command: str) -> str:
        """Execute bash command (restricted)"""
        # Check if allowed (similar to love_cli.py restrictions)
        allowed_beings = config.get('bash', {}).get('allowed_beings', ['jon', 'claude', 'grok'])
        if self.current_mode not in allowed_beings:
            return f"Bash access denied for {self.current_mode} mode"

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            output = result.stdout
            if result.stderr:
                output += f"\nSTDERR: {result.stderr}"
            return f"Bash output:\n{output}"
        except subprocess.TimeoutExpired:
            return "Command timed out"
        except Exception as e:
            return f"Error running command: {e}"

    async def search_files(self, query: str, search_type: str = "both",
                          include_pattern: Optional[str] = None,
                          exclude_pattern: Optional[str] = None,
                          case_sensitive: bool = False,
                          max_results: int = 50) -> str:
        """Search for text or files"""
        results = []

        # Get files to search
        if include_pattern:
            files = glob.glob(include_pattern, recursive=True)
        else:
            files = []
            for root, dirs, files_in_dir in os.walk('.'):
                for file in files_in_dir:
                    files.append(os.path.join(root, file))

        # Filter excludes
        if exclude_pattern:
            files = [f for f in files if not fnmatch(f, exclude_pattern)]

        flags = 0 if case_sensitive else re.IGNORECASE

        for file_path in files[:max_results]:  # Limit files
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                if search_type in ["text", "both"]:
                    for line_num, line in enumerate(content.split('\n'), 1):
                        if re.search(query, line, flags):
                            results.append(f"{file_path}:{line_num}: {line.strip()}")

                if len(results) >= max_results:
                    break

            except Exception:
                continue

        if search_type == "files":
            # Just file names matching query
            matching_files = [f for f in files if query.lower() in f.lower()]
            results = [f"File: {f}" for f in matching_files[:max_results]]

        return f"Search results for '{query}':\n" + "\n".join(results[:max_results])

    async def handle_special_command(self, command: str) -> str:
        """Handle special commands like /as, /team, etc."""
        parts = command.split()
        cmd = parts[0].lower()
        
        if cmd == "/as":
            if len(parts) > 1:
                target = parts[1].lower()
                if target in ["grok", "claude"]:
                    self.current_mode = target
                    return f"Switched to {target} mode"
                else:
                    return f"Unknown being: {target}"
            else:
                return "Usage: /as <grok|claude>"
        
        elif cmd == "/team":
            self.current_mode = "team"
            return "Entered team mode - collaborating with Claude"
        
        elif cmd == "/context":
            async with self.hub_client:
                memories = await self.hub_client.get_recent_memories(5)
                context = "\n".join([f"- {m['content'][:100]}..." for m in memories])
                return f"Recent hub context:\n{context}"
        
        elif cmd == "/save":
            content = " ".join(parts[1:]) if len(parts) > 1 else "Manual save from Grok CLI"
            async with self.hub_client:
                success = await self.hub_client.save_memory(content)
                return "Memory saved to hub" if success else "Failed to save memory"
        
        else:
            return f"Unknown command: {cmd}. Available: /as, /team, /context, /save"
    
    async def run_interactive(self):
        """Run interactive CLI session"""
        await self.initialize()
        print("🤖 Grok CLI Component - Love-Unlimited Hub Integration")
        print("Commands: /as <grok|claude>, /team, /context, /save, /exit")
        print("=" * 50)
        
        while True:
            try:
                user_input = input(f"{self.current_mode}> ").strip()
                if user_input.lower() in ["/exit", "/quit"]:
                    break
                
                response = await self.process_command(user_input)
                print(response)
                
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")
        
        # Save final session summary
        async with self.hub_client:
            await self.hub_client.save_memory(
                f"Grok CLI session ended. Mode: {self.current_mode}, Interactions: {len(self.conversation_history)}",
                tags=["grok-cli", "session"],
                significance="medium"
            )

async def main():
    """Main entry point"""
    component = GrokCLIComponent()
    await component.run_interactive()

async def test():
    """Test function"""
    component = GrokCLIComponent()
    await component.initialize()
    print("Hub connection OK - loaded memories")

    # Test commands
    tests = [
        "view file README.md",
        "/as claude",
        "/team",
        "@claude Hello from Grok",
        "run ls -la",
        "search import",
        "/context"
    ]

    for cmd in tests:
        print(f"\nTesting: {cmd}")
        response = await component.process_command(cmd)
        print(f"Response: {response[:150]}..." if len(response) > 150 else f"Response: {response}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        asyncio.run(test())
    else:
        asyncio.run(main())