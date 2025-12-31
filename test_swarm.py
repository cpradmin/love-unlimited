#!/usr/bin/env python3
"""Test the Swarm coordinator."""
import requests
import os

API_KEY = os.getenv("LOVE_UNLIMITED_KEY")
BASE_URL = "http://localhost:9003"

print("╔══════════════════════════════════════════════════════════════════╗")
print("║          TESTING SWARM COORDINATOR                               ║")
print("╚══════════════════════════════════════════════════════════════════╝\n")

# Test 1: Simple question
response = requests.post(
    f"{BASE_URL}/chat",
    headers={"X-API-Key": API_KEY},
    json={
        "content": "What are the benefits of distributed AI systems?",
        "from": "jon",
        "target": "swarm",
        "type": "chat"
    },
    timeout=60
)

result = response.json()
print(f"Q: What are the benefits of distributed AI systems?")
print(f"[{result.get('sender', 'unknown').upper()}]: {result.get('content')}")
print("")

# Test 2: Technical question
response = requests.post(
    f"{BASE_URL}/chat",
    headers={"X-API-Key": API_KEY},
    json={
        "content": "How does mesh networking improve resilience?",
        "from": "jon",
        "target": "swarm",
        "type": "chat"
    },
    timeout=60
)

result = response.json()
print("="*70)
print(f"Q: How does mesh networking improve resilience?")
print(f"[{result.get('sender', 'unknown').upper()}]: {result.get('content')}")
print("")

print("="*70)
if result.get('sender') == 'swarm':
    print("✅ SWARM IS RESPONDING!")
else:
    print("⚠ Unexpected sender")
print("="*70)
