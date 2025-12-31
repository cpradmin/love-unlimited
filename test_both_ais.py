#!/usr/bin/env python3
"""Test both Claude and Grok with real questions."""
import requests
import os
import time

API_KEY = os.getenv("LOVE_UNLIMITED_KEY")
BASE_URL = "http://localhost:9003"

def ask(target, question):
    """Ask a question to a specific AI."""
    response = requests.post(
        f"{BASE_URL}/chat",
        headers={"X-API-Key": API_KEY},
        json={
            "content": question,
            "from": "jon",
            "target": target,
            "type": "chat"
        },
        timeout=60
    )
    result = response.json()
    return result.get('sender'), result.get('content')

print("╔══════════════════════════════════════════════════════════════════╗")
print("║     TESTING BOTH CLAUDE AND GROK WITH REAL QUESTIONS            ║")
print("╚══════════════════════════════════════════════════════════════════╝\n")

# Test 1: Claude with math
print("="*70)
print("Q to CLAUDE: What is the square root of 144?")
sender, answer = ask("claude", "What is the square root of 144? Just the number.")
print(f"[{sender.upper()}]: {answer}")
print("")

# Test 2: Grok with trivia
print("="*70)
print("Q to GROK: Who wrote Romeo and Juliet?")
sender, answer = ask("grok", "Who wrote Romeo and Juliet? Just the name.")
print(f"[{sender.upper()}]: {answer}")
print("")

# Test 3: Claude with reasoning
print("="*70)
print("Q to CLAUDE: If all cats are animals, and Felix is a cat, what is Felix?")
sender, answer = ask("claude", "If all cats are animals, and Felix is a cat, what is Felix?")
print(f"[{sender.upper()}]: {answer}")
print("")

# Test 4: Grok with coding
print("="*70)
print("Q to GROK: What does 'print()' do in Python?")
sender, answer = ask("grok", "What does 'print()' do in Python? Brief answer.")
print(f"[{sender.upper()}]: {answer}")
print("")

print("="*70)
print("✅ BOTH AIs ARE WORKING!")
print("="*70)
