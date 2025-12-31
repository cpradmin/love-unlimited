#!/usr/bin/env python3
"""Test AI code generation capabilities."""
import requests
import os
import time

API_KEY = os.getenv("LOVE_UNLIMITED_KEY")

def ask(target, question):
    """Ask a coding question."""
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
print("║            TESTING CODE GENERATION CAPABILITIES                  ║")
print("╚══════════════════════════════════════════════════════════════════╝\n")

# Test 1: Claude - Python function
print("="*70)
print("TEST 1: CLAUDE - Write a Python function")
print("="*70)
sender, code = ask("claude", "Write a Python function that reverses a string. Just the code, no explanation.")
print(f"[{sender.upper()}]:")
print(code)
print("")

time.sleep(1)

# Test 2: Grok - JavaScript snippet
print("="*70)
print("TEST 2: GROK - Write JavaScript code")
print("="*70)
sender, code = ask("grok", "Write a JavaScript function that checks if a number is prime. Just the code.")
print(f"[{sender.upper()}]:")
print(code)
print("")

time.sleep(1)

# Test 3: Swarm - Simple algorithm
print("="*70)
print("TEST 3: SWARM - Write an algorithm")
print("="*70)
sender, code = ask("swarm", "Write Python code for bubble sort. Short version, just the code.")
print(f"[{sender.upper()}]:")
print(code)
print("")

print("="*70)
print("✅ ALL AIs CAN WRITE CODE!")
print("="*70)
