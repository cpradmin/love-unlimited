#!/usr/bin/env python3
"""
Generate External Access Tokens for Love-Unlimited Hub

This script generates secure read-only access tokens for external integrations.
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from hub.auth import get_external_token_manager


def main():
    """Interactive token generation."""
    print("=" * 60)
    print("Love-Unlimited Hub - External Token Generator")
    print("=" * 60)
    print()

    # Get token manager
    token_manager = get_external_token_manager()

    # Get token details
    print("Create a new read-only external access token\n")

    name = input("Token name (e.g., 'Cloudflare Worker', 'Webhook Service'): ").strip()
    if not name:
        print("Error: Token name is required")
        return 1

    description = input("Description (optional): ").strip()

    # Being access
    print("\nWhich beings can this token access?")
    print("  1. All beings (claude, jon, grok)")
    print("  2. Specific beings (custom selection)")
    choice = input("Choice [1]: ").strip() or "1"

    if choice == "2":
        beings_input = input("Enter being IDs separated by commas (e.g., claude,jon): ").strip()
        allowed_beings = [b.strip() for b in beings_input.split(",") if b.strip()]
        if not allowed_beings:
            print("Error: At least one being must be specified")
            return 1
    else:
        allowed_beings = ["claude", "jon", "grok"]

    # Rate limit
    rate_limit_input = input("Rate limit (requests per hour) [100]: ").strip()
    try:
        rate_limit = int(rate_limit_input) if rate_limit_input else 100
    except ValueError:
        print("Error: Rate limit must be a number")
        return 1

    # Confirm
    print("\n" + "=" * 60)
    print("Token Configuration:")
    print("=" * 60)
    print(f"Name:            {name}")
    print(f"Description:     {description or '(none)'}")
    print(f"Allowed Beings:  {', '.join(allowed_beings)}")
    print(f"Rate Limit:      {rate_limit} requests/hour")
    print(f"Permissions:     recall (read-only)")
    print("=" * 60)
    print()

    confirm = input("Generate this token? [y/N]: ").strip().lower()
    if confirm != 'y':
        print("Token generation cancelled")
        return 0

    # Generate token
    try:
        token = token_manager.generate_token(
            name=name,
            description=description,
            allowed_beings=allowed_beings,
            rate_limit=rate_limit
        )

        print("\n" + "=" * 60)
        print("✅ Token Generated Successfully!")
        print("=" * 60)
        print()
        print("🔑 Your External Access Token:")
        print()
        print(f"  {token}")
        print()
        print("=" * 60)
        print()
        print("⚠️  IMPORTANT:")
        print("  - Store this token securely")
        print("  - This token provides READ-ONLY access to memories")
        print("  - Do not share publicly or commit to version control")
        print("  - Use HTTPS when transmitting this token")
        print()
        print("📖 Usage Example:")
        print()
        print(f"  curl 'http://localhost:9003/external/recall?q=love+unlimited&token={token}&being_id=claude&limit=5'")
        print()
        print("=" * 60)
        print()
        print(f"Token saved to: {token_manager.tokens_file}")
        print()

        return 0

    except Exception as e:
        print(f"\n❌ Error generating token: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
