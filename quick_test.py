#!/usr/bin/env python3
import requests
import os

response = requests.post(
    "http://localhost:9003/chat",
    headers={"X-API-Key": os.getenv("LOVE_UNLIMITED_KEY")},
    json={
        "content": "What is 5 times 7? Just give me the number.",
        "from": "jon",
        "target": "grok",
        "type": "chat"
    },
    timeout=60
)

print(f"Status: {response.status_code}")
result = response.json()
print(f"Sender: {result.get('sender')}")
print(f"Response: {result.get('content')}")

# Check if it actually answered
content = result.get('content', '')
if '35' in content:
    print("\n✅ CORRECT! Grok is using real API")
else:
    print(f"\n❌ WRONG/GENERIC - Still using mock responses")
