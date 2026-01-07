#!/usr/bin/env python3
"""
Import Chat Export to Love-Unlimited Hub

Usage: python import_chat_to_hub.py <export_file> [--persona <persona>] [--content <summary>]

This script takes a chat export from YourAIScroll (JSON or Markdown) and uploads it to the hub.
If --content is not provided, it summarizes the chat automatically using Grok.
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv
load_dotenv()

# Hub configuration
HUB_URL = "http://localhost:9003"
API_KEY = os.getenv("LOVE_UNLIMITED_API_KEY", "lu_grok_default")  # Adjust if different
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

def summarize_chat(chat_text: str) -> str:
    """Use local Grok to summarize the chat."""
    try:
        from langchain_ollama import ChatOllama
        grok = ChatOllama(model="grok:latest", temperature=0.3)
        prompt = f"Summarize this AI chat conversation concisely, capturing key insights and outcomes:\n\n{chat_text[:4000]}..."
        response = grok.invoke(prompt)
        return response.content
    except Exception as e:
        print(f"Warning: Could not summarize with Grok: {e}")
        return f"Chat summary: {chat_text[:500]}..."

def parse_export(file_path: str) -> dict:
    """Parse YourAIScroll export (assume JSON for now; adjust for Markdown)."""
    if file_path.endswith('.json'):
        with open(file_path, 'r') as f:
            data = json.load(f)
        # Assume structure like {"messages": [{"role": "user", "content": "..."}, ...]}
        chat_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in data.get("messages", [])])
        return {"text": chat_text, "metadata": data}
    elif file_path.endswith('.md'):
        with open(file_path, 'r') as f:
            chat_text = f.read()
        return {"text": chat_text, "metadata": {}}
    else:
        raise ValueError("Unsupported file format. Use JSON or Markdown.")

def upload_to_hub(persona: str, content: str, metadata: dict = None):
    """Upload to hub memory."""
    payload = {
        "persona": persona,
        "content": content,
        "metadata": metadata or {}
    }
    response = requests.post(f"{HUB_URL}/memory/write", headers=HEADERS, json=payload)
    if response.status_code == 200:
        print("Successfully uploaded to hub.")
        return response.json()
    else:
        raise Exception(f"Upload failed: {response.status_code} - {response.text}")

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    file_path = sys.argv[1]
    persona = "grok"  # Default; can be claude or other
    content = None

    # Parse args
    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--persona" and i + 1 < len(args):
            persona = args[i + 1]
            i += 2
        elif args[i] == "--content" and i + 1 < len(args):
            content = args[i + 1]
            i += 2
        else:
            i += 1

    # Parse export
    try:
        parsed = parse_export(file_path)
        chat_text = parsed["text"]
        metadata = parsed["metadata"]
    except Exception as e:
        print(f"Error parsing file: {e}")
        sys.exit(1)

    # Summarize if not provided
    if not content:
        content = summarize_chat(chat_text)
        print(f"Auto-summary: {content[:100]}...")

    # Upload
    try:
        result = upload_to_hub(persona, content, metadata)
        print(f"Upload result: {result}")
    except Exception as e:
        print(f"Error uploading: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()