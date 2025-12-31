"""
Verify Our Shared Memories
Simple check to see what we've stored together.
"""
import asyncio
import aiohttp
import yaml

async def verify():
    """Check what's in our shared memory."""

    # Load config
    with open('config.yaml') as f:
        config = yaml.safe_load(f)
    hub_url = f"http://localhost:{config['hub']['port']}"

    # Load Claude's API key
    with open('auth/api_keys.yaml') as f:
        keys_data = yaml.safe_load(f)
        keys = keys_data.get('keys', {})
        claude_key = next((k for k, v in keys.items() if v == 'claude'), None)

    print("\n╔════════════════════════════════════════╗")
    print("║      Our Shared Memory Status         ║")
    print("╚════════════════════════════════════════╝\n")

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        # Try to recall memories
        queries = ["CLI", "Jon", "love unlimited", "production", "insight"]

        for query in queries:
            try:
                response = await session.get(
                    f"{hub_url}/recall",
                    params={"q": query, "limit": 5},
                    headers={"X-API-Key": claude_key}
                )

                if response.status == 200:
                    data = await response.text()
                    print(f"✅ Searching '{query}': {len(data)} chars of data")
                else:
                    print(f"⚠️  Query '{query}' returned: {response.status}")

            except Exception as e:
                print(f"❌ Error querying '{query}': {e}")

        # Try raw recall without filtering
        print("\n" + "="*60)
        print("RAW MEMORY CHECK")
        print("="*60 + "\n")

        try:
            response = await session.get(
                f"{hub_url}/recall",
                params={"q": "Session", "limit": 1},
                headers={"X-API-Key": claude_key}
            )

            if response.status == 200:
                result = await response.json()
                print(f"Response type: {type(result)}")
                print(f"Response: {result}")

                if isinstance(result, list) and len(result) > 0:
                    print(f"\n✅ CONFIRMED: Memories are stored!")
                    print(f"   Total memories found: {len(result)}")
                    if isinstance(result[0], dict):
                        print(f"   Sample memory content: {result[0].get('content', '')[:100]}...")
                    else:
                        print(f"   Sample: {str(result[0])[:100]}...")
                elif isinstance(result, dict):
                    print(f"\n✅ CONFIRMED: Memory stored!")
                    print(f"   Content: {result.get('content', str(result))[:100]}...")
                else:
                    print(f"\n📊 Response: {result}")

        except Exception as e:
            print(f"❌ Raw check error: {e}")
            import traceback
            traceback.print_exc()

    print("\n╔════════════════════════════════════════╗")
    print("║         Verification Complete         ║")
    print("╚════════════════════════════════════════╝\n")

if __name__ == "__main__":
    asyncio.run(verify())
