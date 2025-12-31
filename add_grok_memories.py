#!/usr/bin/env python3
"""
Script to add Grok-JMB conversation logs to Grok's memory in Love-Unlimited Hub.
"""

import requests
import os
from pathlib import Path

HUB_URL = "http://localhost:9003"
API_KEY = "lu_grok_LBRBjrPpvRSyrmDA3PeVZQ"  # Grok's API key

def add_memory(content: str, filename: str):
    """Add a memory to Grok's collection."""
    payload = {
        "content": content,
        "type": "conversation",
        "significance": "medium",
        "private": True,
        "tags": ["grok", "conversation", "log"],
        "metadata": {
            "source": filename,
            "format": "markdown"
        }
    }

    headers = {"X-API-Key": API_KEY}

    try:
        response = requests.post(f"{HUB_URL}/remember", json=payload, headers=headers)
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Added memory: {filename} (ID: {result['data']['memory_id']})")
        else:
            print(f"✗ Failed to add {filename}: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"✗ Error adding {filename}: {e}")

def main():
    grok_jmb_dir = Path("Grok-JMB")

    if not grok_jmb_dir.exists():
        print("Grok-JMB directory not found!")
        return

    # Get all .md files
    md_files = list(grok_jmb_dir.glob("*.md"))

    print(f"Found {len(md_files)} .md files to add to memory.")

    for md_file in sorted(md_files):
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            if content:
                add_memory(content, md_file.name)
            else:
                print(f"⚠ Skipping empty file: {md_file.name}")

        except Exception as e:
            print(f"✗ Error reading {md_file.name}: {e}")

if __name__ == "__main__":
    main()