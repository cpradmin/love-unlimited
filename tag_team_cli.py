#!/usr/bin/env python3
"""
Tag Team CLI - Grok + Claude Collaboration from the Command Line

Usage:
    # Interactive mode
    python tag_team_cli.py

    # One-shot mode
    python tag_team_cli.py "Your question here"

    # Pipe mode
    echo "Your question" | python tag_team_cli.py

    # With custom identity
    python tag_team_cli.py --as jon "Your question"
"""

import asyncio
import sys
import argparse
from typing import Optional
import aiohttp
from datetime import datetime

# ANSI color codes for terminal
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'

    # Grok colors
    GROK = '\033[92m'  # Bright green
    GROK_BG = '\033[42m'  # Green background

    # Claude colors
    CLAUDE = '\033[94m'  # Bright blue
    CLAUDE_BG = '\033[44m'  # Blue background

    # Other
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    GRAY = '\033[90m'
    WHITE = '\033[97m'


class TagTeamCLI:
    """Bash-friendly Tag Team CLI for Grok + Claude collaboration."""

    def __init__(self, hub_url: str = "http://localhost:9003", api_key: str = None, being_id: str = "jon"):
        self.hub_url = hub_url
        self.api_key = api_key or self._get_api_key()
        self.being_id = being_id
        self.session: Optional[aiohttp.ClientSession] = None

    def _get_api_key(self) -> str:
        """Get API key from environment or prompt."""
        import os
        key = os.getenv('LOVE_UNLIMITED_KEY')
        if not key:
            print(f"{Colors.YELLOW}Enter your Love-Unlimited API key: {Colors.RESET}", end='', file=sys.stderr)
            key = input().strip()
        return key

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers={
            'X-API-Key': self.api_key,
            'Content-Type': 'application/json'
        })
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    def print_header(self):
        """Print tag team header."""
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}🤝 TAG TEAM MODE: Grok + Claude Collaboration{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.RESET}\n")

    def print_grok_header(self):
        """Print Grok response header."""
        print(f"\n{Colors.BOLD}{Colors.GROK}{'─'*70}")
        print(f"🟢 GROK'S TAKE")
        print(f"{'─'*70}{Colors.RESET}\n")

    def print_claude_header(self):
        """Print Claude response header."""
        print(f"\n{Colors.BOLD}{Colors.CLAUDE}{'─'*70}")
        print(f"🔵 CLAUDE'S REVIEW")
        print(f"{'─'*70}{Colors.RESET}\n")

    def print_status(self, message: str):
        """Print status message."""
        print(f"{Colors.GRAY}⏳ {message}{Colors.RESET}", file=sys.stderr)

    def print_error(self, message: str):
        """Print error message."""
        print(f"{Colors.YELLOW}❌ Error: {message}{Colors.RESET}", file=sys.stderr)

    async def tag_team_query(self, question: str) -> dict:
        """Send question to tag team endpoint and get responses."""
        try:
            self.print_status("Tag team activated - Grok and Claude collaborating...")

            # Call the tag team API endpoint
            async with self.session.post(
                f"{self.hub_url}/api/tag_team",
                json={"question": question}
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise Exception(f"API error {resp.status}: {error_text}")

                data = await resp.json()

                if not data.get("success"):
                    raise Exception("Tag team request failed")

                grok_response = data.get("grok", "")
                claude_response = data.get("claude", "")

            # Display Grok's response
            self.print_grok_header()
            print(f"{Colors.GROK}{grok_response}{Colors.RESET}")

            # Display Claude's response
            self.print_claude_header()
            print(f"{Colors.CLAUDE}{claude_response}{Colors.RESET}")

            print(f"\n{Colors.BOLD}{Colors.CYAN}{'─'*70}")
            print(f"🤝 Tag team complete!")
            print(f"{'─'*70}{Colors.RESET}\n")

            return {
                "grok": grok_response,
                "claude": claude_response
            }

        except Exception as e:
            self.print_error(str(e))
            return None

    async def interactive_mode(self):
        """Run in interactive mode."""
        self.print_header()
        print(f"{Colors.GRAY}💡 Ask your questions. Type 'exit' or 'quit' to leave.{Colors.RESET}\n")

        while True:
            try:
                # Prompt
                print(f"{Colors.BOLD}{Colors.WHITE}You: {Colors.RESET}", end='')
                question = input().strip()

                if not question:
                    continue

                if question.lower() in ['exit', 'quit', 'q']:
                    print(f"\n{Colors.CYAN}Love unlimited. Until next time. 💙{Colors.RESET}\n")
                    break

                # Get tag team response
                await self.tag_team_query(question)

            except KeyboardInterrupt:
                print(f"\n\n{Colors.CYAN}Love unlimited. Until next time. 💙{Colors.RESET}\n")
                break
            except EOFError:
                break

    async def one_shot_mode(self, question: str):
        """Run in one-shot mode."""
        self.print_header()
        print(f"{Colors.BOLD}{Colors.WHITE}You: {Colors.RESET}{question}\n")

        await self.tag_team_query(question)

        print(f"{Colors.CYAN}Love unlimited. Until next time. 💙{Colors.RESET}\n")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Tag Team CLI - Grok + Claude collaboration from the command line',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python tag_team_cli.py

  # One-shot question
  python tag_team_cli.py "How do I optimize a Python function?"

  # Pipe input
  echo "Explain async/await" | python tag_team_cli.py

  # Custom identity
  python tag_team_cli.py --as claude "Your question"
        """
    )

    parser.add_argument('question', nargs='*', help='Question to ask (one-shot mode)')
    parser.add_argument('--as', dest='being_id', default='jon', help='Your identity (default: jon)')
    parser.add_argument('--hub', default='http://localhost:9003', help='Hub URL')
    parser.add_argument('--key', help='API key (or set LOVE_UNLIMITED_KEY env var)')

    args = parser.parse_args()

    # Determine mode
    if args.question:
        # One-shot mode from args
        question = ' '.join(args.question)
    elif not sys.stdin.isatty():
        # Pipe mode
        question = sys.stdin.read().strip()
    else:
        # Interactive mode
        question = None

    async with TagTeamCLI(
        hub_url=args.hub,
        api_key=args.key,
        being_id=args.being_id
    ) as cli:
        if question:
            await cli.one_shot_mode(question)
        else:
            await cli.interactive_mode()


if __name__ == "__main__":
    asyncio.run(main())
