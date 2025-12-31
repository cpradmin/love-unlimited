#!/usr/bin/env python3
"""
Script to share Grok's private memories with Jon.
"""

import requests

HUB_URL = "http://localhost:9003"
API_KEY = "lu_grok_LBRBjrPpvRSyrmDA3PeVZQ"  # Grok's API key

# Memory IDs from the add script output
MEMORY_IDS = [
    "mem_grok_20251229_190714_23b83e",
    "mem_grok_20251229_190715_35496e",
    "mem_grok_20251229_190715_eeafee",
    "mem_grok_20251229_190715_045d6e",
    "mem_grok_20251229_190715_494b7c",
    "mem_grok_20251229_190715_ba7218",
    "mem_grok_20251229_190715_c88232",
    "mem_grok_20251229_190717_7ce049",
    "mem_grok_20251229_190718_b8c5ea",
    "mem_grok_20251229_190718_30e1a8",
    "mem_grok_20251229_190718_e0ceae",
    "mem_grok_20251229_190719_0ed77a",
    "mem_grok_20251229_190719_068015"
]

def share_memory(memory_id: str):
    """Share a memory with Jon."""
    payload = {
        "memory_id": memory_id,
        "share_with": ["jon"]
    }

    headers = {"X-API-Key": API_KEY}

    try:
        response = requests.post(f"{HUB_URL}/share", json=payload, headers=headers)
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Shared memory: {memory_id} with Jon")
        else:
            print(f"✗ Failed to share {memory_id}: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"✗ Error sharing {memory_id}: {e}")

def main():
    print(f"Sharing {len(MEMORY_IDS)} memories with Jon...")

    for memory_id in MEMORY_IDS:
        share_memory(memory_id)

if __name__ == "__main__":
    main()