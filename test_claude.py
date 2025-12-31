#!/usr/bin/env python3
import requests
import os

print("Testing Claude with real API...\n")

# Test 1: Simple math
response = requests.post(
    "http://localhost:9003/chat",
    headers={"X-API-Key": os.getenv("LOVE_UNLIMITED_KEY")},
    json={
        "content": "What is 12 times 8? Just give me the number.",
        "from": "jon",
        "target": "claude",
        "type": "chat"
    },
    timeout=60
)

result = response.json()
print(f"Q: What is 12 times 8?")
print(f"Claude: {result.get('content')}\n")

if '96' in result.get('content', ''):
    print("✅ Math test PASSED\n")
else:
    print("⚠ Unexpected response\n")

# Test 2: Actual question
response = requests.post(
    "http://localhost:9003/chat",
    headers={"X-API-Key": os.getenv("LOVE_UNLIMITED_KEY")},
    json={
        "content": "What do you think about AI collaboration and memory sovereignty?",
        "from": "jon",
        "target": "claude",
        "type": "chat"
    },
    timeout=60
)

result = response.json()
print(f"Q: What do you think about AI collaboration and memory sovereignty?")
print(f"Claude: {result.get('content')}\n")

content = result.get('content', '').lower()
if any(word in content for word in ['collaboration', 'memory', 'sovereignty', 'ai']):
    print("✅ Claude is responding contextually!")
else:
    print("⚠ Response seems generic")
