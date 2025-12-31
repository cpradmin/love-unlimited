#!/usr/bin/env python3
"""
Test broadcasting to ALL AIs for diverse coding perspectives.
"""
import requests
import os

API_KEY = os.getenv("LOVE_UNLIMITED_KEY")

print("╔══════════════════════════════════════════════════════════════════╗")
print("║    BROADCAST: Get perspectives from ALL THREE AIs               ║")
print("╚══════════════════════════════════════════════════════════════════╝\n")

question = "How would you optimize a slow database query? Brief answer."

print(f"QUESTION TO ALL AIs: {question}\n")
print("="*70)

response = requests.post(
    "http://localhost:9003/chat",
    headers={"X-API-Key": API_KEY},
    json={
        "content": question,
        "from": "jon",
        "target": "all",  # Broadcast to ALL AIs
        "type": "chat"
    },
    timeout=120
)

result = response.json()
sender = result.get('sender', 'unknown')
content = result.get('content', '')

print(f"[{sender.upper()} responded first]:")
print(content)
print("\n" + "="*70)
print("\nNOTE: With target='all', the hub returns the first AI to respond.")
print("For collaborative input, ask each AI separately and compare answers.")
print("="*70)
