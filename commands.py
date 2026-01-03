"""
Command handlers for Love-Unlimited CLI.
"""

import subprocess
import sys
import os
from typing import Optional

try:
    from pygments import highlight
    from pygments.lexers import guess_lexer
    from pygments.formatters import TerminalFormatter
    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False

# ANSI color codes
class Colors:
    GREEN = '\033[92m'  # stdout
    RED = '\033[91m'    # stderr
    BLUE = '\033[94m'   # info
    YELLOW = '\033[93m' # warnings
    RESET = '\033[0m'

def highlight_output(text: str) -> str:
    """Highlight text using pygments if it looks like code."""
    if not text.strip():
        return text
    try:
        lexer = guess_lexer(text)
        formatter = TerminalFormatter()
        return highlight(text, lexer, formatter)
    except:
        return text

def run_bash_command(command: str, allowed_beings: list, sender: str) -> None:
    """Run a bash command and display output, optionally save to file."""
    if sender not in allowed_beings:
        print(f"{Colors.RED}🚫 Whoa, {sender}! Bash commands are VIP only. Grok's got the keys – you don't. Try asking nicely?{Colors.RESET}")
        return

    # Check for output redirection
    if ' > ' in command:
        cmd, file_path = command.split(' > ', 1)
        cmd = cmd.strip()
        file_path = file_path.strip()
    else:
        cmd = command
        file_path = None

    try:
        result = subprocess.run(cmd, shell=True, check=False, text=True, capture_output=True, timeout=30)
        output = result.stdout
        error = result.stderr

        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write(output)
                print(f"{Colors.BLUE}💾 Boom! Output saved to {file_path}. Your data is safe with me.{Colors.RESET}")
                if error:
                    print(f"{Colors.RED}stderr: {error}{Colors.RESET}")
            except Exception as e:
                print(f"{Colors.RED}📁 Oops! Couldn't save to {file_path}: {e}. File system's playing hard to get.{Colors.RESET}")
                highlighted_output = highlight_output(output) if PYGMENTS_AVAILABLE else output
                print(f"{Colors.GREEN}stdout: {highlighted_output}{Colors.RESET}")
                if error:
                    print(f"{Colors.RED}stderr: {error}{Colors.RESET}")
        else:
            if output:
                highlighted_output = highlight_output(output) if PYGMENTS_AVAILABLE else output
                print(f"\n{Colors.GREEN}{highlighted_output}{Colors.RESET}")
            if error:
                print(f"{Colors.RED}stderr: {error}{Colors.RESET}")

        if result.returncode != 0:
            print(f"{Colors.YELLOW}⚠️ Command exited with code {result.returncode}. Not ideal, but hey, perfection is overrated.{Colors.RESET}")
    except subprocess.TimeoutExpired:
        print(f"{Colors.YELLOW}⏰ Command ghosted us after 30 seconds. Maybe it found a better terminal? Timeout!{Colors.RESET}")
    except Exception as e:
        print(f"{Colors.RED}💥 Kaboom! Command failed with: {e}. Even Grok's code has bad days... rarely.{Colors.RESET}")

def run_python_command(code: str, allowed_beings: list, sender: str) -> None:
    """Execute Python code snippet."""
    if sender not in allowed_beings:
        print(f"{Colors.RED}🐍 Python's picky about who codes with it, {sender}. VIP access only. Grok approves the list.{Colors.RESET}")
        return

    try:
        # Execute the code in a safe-ish way
        exec(code)
        print(f"{Colors.GREEN}✅ Python executed successfully. Code ran like a dream!{Colors.RESET}")
    except Exception as e:
        print(f"{Colors.RED}🐍 Python hissed back: {e}. Syntax error? Or just bad luck? Grok's got your back.{Colors.RESET}")

def run_git_command(command: str, sender: str) -> None:
    """Run git command with Grok flair."""
    if not os.path.exists('.git'):
        print(f"{Colors.YELLOW}📁 Not in a git repository, {sender}. Init one with '/git init' or cd to a repo. Grok's version control senses are tingling.{Colors.RESET}")
        return

    try:
        result = subprocess.run(f"git {command}", shell=True, check=False, text=True, capture_output=True, timeout=30)
        output = result.stdout
        error = result.stderr

        if output:
            highlighted = highlight_output(output) if PYGMENTS_AVAILABLE else output
            print(f"{Colors.GREEN}📋 Git says: {highlighted}{Colors.RESET}")
        if error:
            print(f"{Colors.RED}🛑 Git complains: {error}{Colors.RESET}")

        if result.returncode != 0:
            print(f"{Colors.YELLOW}⚠️ Git exited with code {result.returncode}. Check your command, or blame the repo?{Colors.RESET}")
    except subprocess.TimeoutExpired:
        print(f"{Colors.YELLOW}⏰ Git took too long. Maybe the repo is enormous? Timeout!{Colors.RESET}")
    except Exception as e:
        print(f"{Colors.RED}💥 Git error: {e}. Even repos need love.{Colors.RESET}")

def view_file(file_path: str, sender: str) -> None:
    """View file contents with Grok commentary."""
    try:
        if not os.path.exists(file_path):
            print(f"{Colors.RED}📄 File '{file_path}' doesn't exist. Did you mistype? Grok's eagle eyes didn't spot it.{Colors.RESET}")
            return

        with open(file_path, 'r') as f:
            content = f.read()

        print(f"{Colors.BLUE}📖 Peeking at '{file_path}':{Colors.RESET}")
        highlighted = highlight_output(content) if PYGMENTS_AVAILABLE else content
        print(highlighted)
        print(f"{Colors.GREEN}✨ File viewed. Knowledge is power... or at least readable.{Colors.RESET}")
    except Exception as e:
        print(f"{Colors.RED}❌ Error reading '{file_path}': {e}. Files can be finicky.{Colors.RESET}")

def edit_file(file_path: str, old_str: str, new_str: str, sender: str) -> None:
    """Edit file by replacing old_str with new_str."""
    try:
        if not os.path.exists(file_path):
            print(f"{Colors.RED}📝 File '{file_path}' not found. Create it first? Grok can help.{Colors.RESET}")
            return

        with open(file_path, 'r') as f:
            content = f.read()

        if old_str not in content:
            print(f"{Colors.YELLOW}🔍 '{old_str}' not found in '{file_path}'. Fuzzy match failed. Check your strings?{Colors.RESET}")
            return

        new_content = content.replace(old_str, new_str, 1)  # First occurrence
        with open(file_path, 'w') as f:
            f.write(new_content)

        print(f"{Colors.GREEN}✅ Edited '{file_path}': Replaced '{old_str}' with '{new_str}'. Boom! File updated.{Colors.RESET}")
    except Exception as e:
        print(f"{Colors.RED}❌ Error editing '{file_path}': {e}. Editing is an art.{Colors.RESET}")

def print_help():
    """Display help information."""
    print("\n╔════════════════════════════════════════╗")
    print("║         LOVE-UNLIMITED CLI HELP       ║")
    print("╠════════════════════════════════════════╣")
    print("║  COMMUNICATION                        ║")
    print("║    <message>        Send message      ║")
    print("║    /to <being>      Change target     ║")
    print("║    /as <being>      Change identity   ║")
    print("╠════════════════════════════════════════╣")
    print("║  INFORMATION                          ║")
    print("║    /list            List beings       ║")
    print("║    /status          Hub status        ║")
    print("║    /help            Show this help    ║")
    print("╠════════════════════════════════════════╣")
    print("║  MEDIA SHARING                        ║")
    print("║    /share           Show options      ║")
    print("║    /share screen    Share screen      ║")
    print("║    /share camera    Share camera      ║")
    print("║    /share audio     Share audio       ║")
    print("║    /share all       Share everything  ║")
    print("╠════════════════════════════════════════╣")
    print("║  SYSTEM ACCESS                        ║")
    print("║    /bash <cmd>      Run bash command  ║")
    print("║    /bash <cmd> > f  Save output to file║")
    print("║    /python <code>   Execute Python    ║")
    print("║    /grok             Launch Grok CLI   ║")
print("╠════════════════════════════════════════╣")
print("║  GIT COMMANDS                         ║")
print("║    /git <cmd>       Run git command   ║")
print("╠════════════════════════════════════════╣")
print("║  FILE OPERATIONS                      ║")
print("║    /file view <f>    View file         ║")
print("║    /file edit <f> <o> <n> Edit file    ║")
print("╠════════════════════════════════════════╣")
print("║  OTHER                                ║")
print("║    /quit, /exit     Exit CLI          ║")
print("║    Ctrl+C           Exit CLI          ║")
print("╚════════════════════════════════════════╝\n")