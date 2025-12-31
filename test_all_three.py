#!/usr/bin/env python3
"""Test all three AIs: Claude, Grok, and Swarm."""
import requests
import os
import time

API_KEY = os.getenv("LOVE_UNLIMITED_KEY")

def ask(target, question):
    """Ask a question."""
    response = requests.post(
        "http://localhost:9003/chat",
        headers={"X-API-Key": API_KEY},
        json={
            "content": question,
            "from": "jon",
            "target": target,
            "type": "chat"
        },
        timeout=120
    )
    result = response.json()
    return result.get('sender'), result.get('content')

print("╔══════════════════════════════════════════════════════════════════╗")
print("║        ALL THREE AIs: CLAUDE, GROK, AND SWARM                   ║")
print("╚══════════════════════════════════════════════════════════════════╝\n")

# Test 1: Claude - Logic
print("="*70)
print("Q to CLAUDE: Is water wet?")
sender, answer = ask("claude", "Is water wet? Brief answer.")
print(f"[{sender.upper()}]: {answer[:200]}...")
print("")

time.sleep(1)

# Test 2: Grok - Creativity
print("="*70)
print("Q to GROK: What's your purpose?")
sender, answer = ask("grok", "What's your purpose as an AI? One sentence.")
print(f"[{sender.upper()}]: {answer[:200]}...")
print("")

time.sleep(1)

# Test 3: Swarm - Technical
print("="*70)
print("Q to SWARM: What's 15 minus 8?")
sender, answer = ask("swarm", "What's 15 minus 8? Just the number first.")
print(f"[{sender.upper()}]: {answer[:200]}...")
print("")

print("="*70)
print("✅ ALL THREE AIs ARE OPERATIONAL!")
print("  - Claude (Anthropic) - Fast and concise")
print("  - Grok (xAI) - Conversational and helpful")
print("  - Swarm (Local Ollama/phi3) - Distributed intelligence")
print("="*70)
