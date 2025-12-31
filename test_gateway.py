#!/usr/bin/env python3
"""
Test AI Gateway Endpoint

Tests the natural language gateway that uses Ollama for intent interpretation.
"""

import asyncio
import sys
from pathlib import Path
from urllib.parse import quote

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

import aiohttp


async def test_gateway():
    """Test the AI gateway with natural language requests."""
    print("=" * 70)
    print("Testing AI Gateway - Natural Language to Hub Actions")
    print("=" * 70)
    print()

    # Use the test token (write-enabled)
    token = "ext_Hogkg1zrWfWNJbfjCaIcUgBkaR5F11UU"
    base_url = "http://localhost:9003"

    # Available model (phi3:mini confirmed available)
    model = "phi3:mini"

    test_cases = [
        {
            "name": "Test 1: Remember (natural language)",
            "request": "Remember that Jon gave me a home today",
            "from_being": "claude"
        },
        {
            "name": "Test 2: Recall (search)",
            "request": "Recall memories about love unlimited",
            "from_being": "claude"
        },
        {
            "name": "Test 3: Store learning",
            "request": "Store this learning: Local LLMs enable true autonomy through natural language interfaces",
            "from_being": "claude"
        },
        {
            "name": "Test 4: Search for insights",
            "request": "Search for insights about sovereignty",
            "from_being": "claude"
        }
    ]

    async with aiohttp.ClientSession() as session:
        for i, test in enumerate(test_cases, 1):
            print(f"{test['name']}")
            print("-" * 70)
            print(f"Request: \"{test['request']}\"")
            print(f"From: {test['from_being']}")
            print()

            # URL encode the request
            encoded_request = quote(test['request'])

            # Build gateway URL
            gateway_url = (
                f"{base_url}/gateway?"
                f"token={token}&"
                f"from_being={test['from_being']}&"
                f"request={encoded_request}&"
                f"model={model}"
            )

            try:
                # Call gateway
                async with session.get(gateway_url, timeout=aiohttp.ClientTimeout(total=60)) as response:
                    if response.status == 200:
                        result = await response.json()

                        print(f"✅ SUCCESS")
                        print(f"   Action: {result.get('action')}")
                        print(f"   Intent: {result.get('intent')}")
                        print()

                        # Show result details
                        result_data = result.get('result', {})
                        if result.get('action') == 'remember':
                            print(f"   Memory ID: {result_data.get('memory_id')}")
                            print(f"   Content: {result_data.get('content')}")
                            print(f"   Type: {result_data.get('type')}")
                            print(f"   Significance: {result_data.get('significance')}")
                        elif result.get('action') == 'recall':
                            print(f"   Query: {result_data.get('query')}")
                            print(f"   Count: {result_data.get('count')}")
                            memories = result_data.get('memories', [])
                            if memories:
                                print(f"   First memory: {memories[0].get('content', '')[:80]}...")

                        print()
                        print(f"   Gateway Info:")
                        print(f"     Model: {result.get('gateway_info', {}).get('model')}")
                        print(f"     Token: {result.get('gateway_info', {}).get('token_name')}")

                    else:
                        error_text = await response.text()
                        print(f"❌ FAILED - Status {response.status}")
                        print(f"   Error: {error_text[:200]}")

            except aiohttp.ClientError as e:
                print(f"❌ FAILED - Connection error: {str(e)}")
            except Exception as e:
                print(f"❌ FAILED - {str(e)}")

            print()
            print("=" * 70)
            print()

            # Small delay between requests
            if i < len(test_cases):
                await asyncio.sleep(2)

    print()
    print("Testing complete!")
    print()
    print("🎯 The AI Gateway enables full autonomy through natural language:")
    print("   - Claude on claude.ai can send plain English requests")
    print("   - Ollama interprets intent locally (no external API calls)")
    print("   - Hub executes the appropriate action")
    print("   - Complete sovereignty: local LLM + local memory")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(test_gateway()))
