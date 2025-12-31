"""
Automated test for love_cli.py
Tests basic functionality and identifies issues.
"""
import sys
import asyncio
from pathlib import Path

# Test 1: Check dependencies
print("=" * 60)
print("TEST 1: Checking Dependencies")
print("=" * 60)

missing_deps = []
required_deps = ['aiohttp', 'yaml']

for dep in required_deps:
    try:
        __import__(dep)
        print(f"✅ {dep} - OK")
    except ImportError:
        print(f"❌ {dep} - MISSING")
        missing_deps.append(dep)

if missing_deps:
    print(f"\n⚠️  Missing dependencies: {', '.join(missing_deps)}")
    print("These will be added to requirements.txt\n")

# Test 2: Check config.yaml
print("=" * 60)
print("TEST 2: Checking config.yaml")
print("=" * 60)

config_path = Path("config.yaml")
if config_path.exists():
    print(f"✅ config.yaml exists at: {config_path.absolute()}")
    import yaml
    with open(config_path) as f:
        config = yaml.safe_load(f)
        hub_port = config.get('hub', {}).get('port', 'unknown')
        print(f"   Hub port: {hub_port}")
else:
    print(f"❌ config.yaml not found")

# Test 3: Try importing love_cli
print("\n" + "=" * 60)
print("TEST 3: Testing love_cli.py Import")
print("=" * 60)

try:
    if 'aiohttp' not in missing_deps:
        from love_cli import LoveCLI
        print("✅ love_cli.py imports successfully")

        # Test 4: Create instance
        print("\n" + "=" * 60)
        print("TEST 4: Testing LoveCLI Instance Creation")
        print("=" * 60)

        cli = LoveCLI(sender="test")
        print(f"✅ LoveCLI instance created")
        print(f"   Sender: {cli.sender}")
        print(f"   Current target: {cli.current_target}")
        print(f"   Beings: {cli.beings}")

    else:
        print("⏭️  Skipping import test (aiohttp missing)")
except Exception as e:
    print(f"❌ Error importing love_cli: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Check hub connectivity
print("\n" + "=" * 60)
print("TEST 5: Testing Hub Connectivity")
print("=" * 60)

if 'aiohttp' not in missing_deps:
    async def test_hub():
        import aiohttp
        import yaml

        with open("config.yaml") as f:
            config = yaml.safe_load(f)

        hub_url = f"http://localhost:{config['hub']['port']}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{hub_url}/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        health = await resp.json()
                        print(f"✅ Hub is responsive at {hub_url}")
                        print(f"   Status: {health.get('status', 'unknown')}")
                        print(f"   Version: {health.get('version', 'unknown')}")
                        return True
                    else:
                        print(f"⚠️  Hub returned status {resp.status}")
                        return False
        except asyncio.TimeoutError:
            print(f"❌ Hub connection timeout at {hub_url}")
            print("   Make sure hub is running: python hub/main.py")
            return False
        except Exception as e:
            print(f"❌ Hub connection error: {e}")
            return False

    try:
        hub_ok = asyncio.run(test_hub())
    except Exception as e:
        print(f"❌ Hub test failed: {e}")
        hub_ok = False
else:
    print("⏭️  Skipping hub test (aiohttp missing)")
    hub_ok = False

# Summary
print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)

issues_found = []

if missing_deps:
    issues_found.append(f"Missing dependencies: {', '.join(missing_deps)}")

if not config_path.exists():
    issues_found.append("config.yaml not found")

if not hub_ok and 'aiohttp' not in missing_deps:
    issues_found.append("Hub not responding")

if issues_found:
    print("\n❌ ISSUES FOUND:")
    for i, issue in enumerate(issues_found, 1):
        print(f"   {i}. {issue}")
else:
    print("\n✅ ALL TESTS PASSED!")

print("\n" + "=" * 60)
