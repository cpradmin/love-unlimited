#!/usr/bin/env python3
"""Quick test of Swarm through the hub."""
import requests
import os

API_KEY = os.getenv("LOVE_UNLIMITED_KEY")

print("Testing Swarm through Love-Unlimited Hub...\n")

response = requests.post(
    "http://localhost:9003/chat",
    headers={"X-API-Key": API_KEY},
    json={
        "content": "What is 10 divided by 2? Brief answer.",
        "from": "jon",
        "target": "swarm",
        "type": "chat"
    },
    timeout=120  # Longer timeout for Ollama
)

result = response.json()
sender = result.get('sender', 'unknown')
content = result.get('content', '')

print(f"Q: What is 10 divided by 2?")
print(f"[{sender.upper()}]: {content}\n")

if sender == 'swarm' and '5' in content:
    print("✅ SWARM WORKING THROUGH HUB!")
elif sender == 'swarm':
    print("✅ Swarm responded, but check the answer")
else:
    print(f"⚠ Unexpected sender: {sender}")
