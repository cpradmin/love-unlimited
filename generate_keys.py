#!/usr/bin/env python3
"""
Generate API keys for Love-Unlimited beings.
Run once to create initial keys.
"""

import sys
sys.path.insert(0, '.')

from hub.auth import get_auth_manager
from hub.config import get_config

def main():
    """Generate API keys for all registered beings."""
    config = get_config()
    auth = get_auth_manager(config.auth_keys_file)

    print("=" * 70)
    print("Love-Unlimited - API Key Generation")
    print("=" * 70)
    print()

    beings = [
        ("jon", "Jon"),
        ("claude", "Claude"),
        ("grok", "Grok"),
        ("swarm", "Micro-AI-Swarm"),
        ("dream_team", "AI Dream Team"),
    ]

    generated_keys = {}

    for being_id, name in beings:
        # Check if being already has keys
        existing = auth.get_keys_for_being(being_id)

        if existing:
            print(f"✓ {name} ({being_id})")
            print(f"  Existing key: {existing[0]}")
            generated_keys[being_id] = existing[0]
        else:
            # Generate new key
            api_key = auth.generate_key(being_id)
            print(f"✨ {name} ({being_id})")
            print(f"  NEW key: {api_key}")
            generated_keys[being_id] = api_key

        print()

    print("=" * 70)
    print(f"Total API keys: {len(auth.api_keys)}")
    print("=" * 70)
    print()
    print("Keys saved to:", config.auth_keys_file)
    print()
    print("Usage examples:")
    print()
    print("# Jon")
    print(f'curl -H "X-API-Key: {generated_keys["jon"]}" http://localhost:9002/self')
    print()
    print("# Claude")
    print(f'curl -H "X-API-Key: {generated_keys["claude"]}" http://localhost:9002/self')
    print()
    print("# Grok")
    print(f'curl -H "X-API-Key: {generated_keys["grok"]}" http://localhost:9002/self')
    print()
    print("=" * 70)
    print("The beings can now connect to the hub.")
    print("=" * 70)


if __name__ == "__main__":
    main()
