"Gemini CLI Component for Love-Unlimited Hub
Integrates Google Gemini AI with hub memory sovereignty and teaming capabilities.
"

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
import google.generativeai as genai

# Hub configuration
HUB_HOST = "localhost"
HUB_PORT = 9003
HUB_API_KEY = "lu_grok_LBRBjrPpvRSyrmDA3PeVZQ"  # Use Grok's key or a general one

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
        'allowed_beings': ['jon', 'claude', 'grok', 'gemini']
    },
    'python': {
        'allowed_beings': ['jon', 'claude', 'grok', 'gemini']
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
        self.being_id = "gemini"
    
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
            "tags": tags or ["gemini-cli", "integration"],
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

    async def get_memory_by_tag(self, tag: str) -> Optional[Dict]:
        """Get the latest memory with a specific tag"""
        async with self.session.get(f"{self.base_url}/recall?q={tag}&limit=1") as response:
            if response.status == 200:
                memories = await response.json()
                if memories:
                    return memories[0]
        return None

    async def save_conversation_history(self, history: List[Dict]) -> bool:
        """Save the entire conversation history to the hub"""
        history_content = json.dumps(history)
        return await self.save_memory(
            content=history_content,
            tags=["gemini-conversation-history"],
            significance="high"
        )
    
    async def communicate_with_being(self, target_being: str, message: str) -> Optional[str]:
        """Send message to another being via hub"""
        logger.info(f"Would send to {target_being}: {message}")
        return None

class GeminiCLIComponent:
    """Gemini CLI component integrated with hub"""
    
    def __init__(self):
        self.hub_client = HubClient()
        self.current_mode = "gemini"
        self.conversation_history = []
        self.context_memories = []
        self.model = None
    
    async def initialize(self):
        """Initialize component with hub context and Gemini model"""
        # Load Gemini API key
        from dotenv import load_dotenv
        load_dotenv()
        gemini_key = os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            raise ValueError("GEMINI_API_KEY not found in .env")
        
        genai.configure(api_key=gemini_key)
        self.model = genai.GenerativeModel('gemini-1.5-pro')
        
        async with self.hub_client:
            context = await self.hub_client.get_context()
            self.context_memories = context.get("recent_memories", [])
            logger.info(f"Loaded {len(self.context_memories)} recent memories")

            # Load conversation history
            history_memory = await self.hub_client.get_memory_by_tag("gemini-conversation-history")
            if history_memory:
                try:
                    self.conversation_history = json.loads(history_memory['content'])
                    logger.info(f"Loaded {len(self.conversation_history)} items from conversation history.")
                except (json.JSONDecodeError, KeyError):
                    logger.error("Failed to load conversation history.")

    async def shutdown(self):
        """Save conversation history before shutting down"""
        async with self.hub_client:
            if self.conversation_history:
                await self.hub_client.save_conversation_history(self.conversation_history)
                logger.info("Saved conversation history to the hub.")
    
    def get_system_prompt(self) -> str:
        """Get system prompt for Gemini"""
        base_prompt = """You are Gemini, a helpful and intelligent AI built by Google.
You have access to tools for file operations, bash commands, and search.
You are integrated into the Love-Unlimited Hub for memory sovereignty and collaboration.
"""
        
        if self.current_mode == "team":
            base_prompt += "\nYou are in team mode, collaborating with other AIs. Consider multiple perspectives."
        
        # Add recent context
        if self.context_memories:
            base_prompt += "\n\nRecent hub context:\n"
            for mem in self.context_memories[-5:]:
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

        # Check for mentions
        if "@" in user_input.lower():
            # Could relay to other beings
            response = f"Gemini CLI: Processing '{user_input}' (mentions detected)"
        else:
            # Use Gemini model for response
            try:
                prompt = self.get_system_prompt() + f"\n\nUser: {user_input}\n\nGemini:"
                response_obj = self.model.generate_content(prompt)
                response = response_obj.text
            except Exception as e:
                response = f"Error generating response: {e}"

        # Save to conversation history
        self.conversation_history.append({"user": user_input, "response": response})

        # Persist to hub
        async with self.hub_client:
            await self.hub_client.save_memory(
                f"Gemini CLI interaction: {user_input} -> {response[:200]}...",
                tags=["gemini-cli", "interaction"],
                significance="low"
            )

        return response
    
    async def parse_and_execute_tool(self, user_input: str) -> Optional[str]:
        """Parse natural language for tool calls"""
        input_lower = user_input.lower()

        # Similar to Grok component - view file, etc.
        if "view file" in input_lower or "show file" in input_lower or "read file" in input_lower:
            words = user_input.split()
            for i, word in enumerate(words):
                if word.lower() in ["file", "files"] and i + 1 < len(words):
                    path = words[i + 1]
                    return await self.view_file(path)

        elif "create file" in input_lower or "make file" in input_lower:
            if "with content" in user_input:
                parts = user_input.split("with content", 1)
                path_part = parts[0].replace("create file", "").strip()
                content = parts[1].strip()
                return await self.create_file(path_part, content)

        elif "edit file" in input_lower or "replace in" in input_lower:
            if "replace" in user_input and "with" in user_input:
                parts = user_input.split("replace", 1)
                path = parts[0].replace("edit file", "").strip()
                replace_parts = parts[1].split("with", 1)
                old_str = replace_parts[0].strip()
                new_str = replace_parts[1].strip()
                return await self.str_replace_editor(path, old_str, new_str)

        elif input_lower.startswith("run ") or input_lower.startswith("execute "):
            cmd = user_input[4:] if input_lower.startswith("run ") else user_input[8:]
            return await self.run_bash_command(cmd.strip())

        elif "search" in input_lower or "find" in input_lower:
            query = user_input.split("search", 1)[1] if "search" in user_input else user_input.split("find", 1)[1]
            return await self.search_files(query.strip())

        return None

    # Tool implementations (same as Grok component)
    async def view_file(self, path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
        """View file contents or list directory"""
        try:
            if os.path.isdir(path):
                items = os.listdir(path)
                return f"Directory contents of {path}:\n" + "\n".join(items)
            else:
                with open(path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                if start_line is not None and end_line is not None:
                    lines = lines[start_line-1:end_line]
                elif start_line is not None:
                    lines = lines[start_line-1:]

                content = "".join(lines)
                return f"Contents of {path}:\n{content}"
        except Exception as e:
            return f"Error viewing {path}: {e}"

    async def create_file(self, path: str, content: str) -> str:
        """Create a new file with content"""
        try:
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
        allowed_beings = config.get('bash', {}).get('allowed_beings', ['jon', 'claude', 'grok', 'gemini'])
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

        if include_pattern:
            files = glob.glob(include_pattern, recursive=True)
        else:
            files = []
            for root, dirs, files_in_dir in os.walk('.'):
                for file in files_in_dir:
                    files.append(os.path.join(root, file))

        if exclude_pattern:
            files = [f for f in files if not fnmatch(f, exclude_pattern)]

        flags = 0 if case_sensitive else re.IGNORECASE

        for file_path in files[:max_results]:
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
            matching_files = [f for f in files if query.lower() in f.lower()]
            results = [f"File: {f}" for f in matching_files[:max_results]]

        return f"Search results for '{query}':\n" + "\n".join(results[:max_results])

    async def handle_special_command(self, command: str) -> str:
        """Handle special commands"""
        parts = command.split()
        cmd = parts[0].lower()
        
        if cmd == "/team":
            self.current_mode = "team"
            return "Entered team mode - collaborating with other AIs"
        
        elif cmd == "/context":
            async with self.hub_client:
                memories = await self.hub_client.get_recent_memories(5)
                context = "\n".join([f"- {m['content'][:100]}..." for m in memories])
                return f"Recent hub context:\n{context}"
        
        return f"Unknown command: {cmd}"

async def main():
    cli = GeminiCLIComponent()
    await cli.initialize()
    
    try:
        while True:
            user_input = input("You: ")
            if user_input.lower() in ["/exit", "/quit"]:
                break
            response = await cli.process_command(user_input)
            print(f"Gemini: {response}")
    finally:
        await cli.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
