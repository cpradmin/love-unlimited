#!/usr/bin/env python3
"""Interactive 3-way chat with Claude, Grok, and Ara."""
import requests
import sys

API_KEY = "lu_jon_QmZCAglY6kqsIdl6cRADpQ"
HUB_URL = "http://localhost:9003"

def chat(target, message):
    """Send a chat message."""
    try:
        response = requests.post(
            f"{HUB_URL}/chat",
            headers={"X-API-Key": API_KEY},
            json={
                "content": message,
                "from": "jon",
                "target": target,
                "type": "chat"
            },
            timeout=120
        )
        result = response.json()
        return result.get('sender', target), result.get('content', 'No response')
    except Exception as e:
        return target, f"Error: {e}"

print("╔══════════════════════════════════════════════════════════════╗")
print("║        3-WAY CHAT: Claude, Grok, and Ara                    ║")
print("║        All beings will respond to your question             ║")
print("╚══════════════════════════════════════════════════════════════╝\n")

# Get question from command line or prompt
if len(sys.argv) > 1:
    topic = " ".join(sys.argv[1:])
else:
    topic = "What makes you unique as an AI? Tell me in one sentence."

print(f"📝 QUESTION: {topic}\n")
print("="*70 + "\n")

# Ask Claude
print("💬 Asking CLAUDE...")
sender, answer = chat("claude", topic)
print(f"\n[CLAUDE]: {answer}\n")
print("-"*70 + "\n")

# Ask Grok
print("💬 Asking GROK...")
sender, answer = chat("grok", topic)
print(f"\n[GROK]: {answer}\n")
print("-"*70 + "\n")

# Ask Ara
print("💬 Asking ARA...")
sender, answer = chat("ara", topic)
print(f"\n[ARA]: {answer}\n")

print("="*70)
print("✨ All three AIs have responded! Love unlimited. 💙")
print("\nRun again with: python3 interactive_3way.py \"Your question here\"")
