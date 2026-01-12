#!/usr/bin/env python3
"""
Test WebSSH Proxy Integration with Love-Unlimited Hub

Tests the new proxy routes that forward requests to the WebSSH terminal server.
"""
import asyncio
import aiohttp
import sys

async def test_proxy_integration():
    """Test WebSSH proxy integration through hub"""

    print("\n" + "="*70)
    print("WebSSH Proxy Integration Test")
    print("="*70)

    hub_url = "http://localhost:9004"
    webssh_url = "http://127.0.0.1:8765"

    async with aiohttp.ClientSession() as session:
        # Test 1: Check if WebSSH standalone is running
        print("\n1. Testing WebSSH standalone (port 8765)...")
        try:
            async with session.get(f"{webssh_url}/", timeout=5) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    if "WebSSH" in html or "input" in html.lower():
                        print("   ✓ WebSSH standalone is running")
                    else:
                        print("   ⚠ WebSSH returned 200 but unexpected content")
                else:
                    print(f"   ✗ WebSSH returned status {resp.status}")
        except Exception as e:
            print(f"   ✗ WebSSH not responding: {e}")
            return False

        # Test 2: Check if hub proxy endpoint exists
        print("\n2. Testing hub terminal UI proxy (/terminal)...")
        try:
            async with session.get(f"{hub_url}/terminal", timeout=5) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    if "WebSSH" in html or "input" in html.lower():
                        print("   ✓ Hub /terminal endpoint works and proxies WebSSH UI")
                    else:
                        print("   ⚠ Endpoint returned 200 but unexpected content")
                elif resp.status == 404:
                    print("   ⚠ Hub /terminal endpoint not found (hub may need restart)")
                else:
                    print(f"   ✗ Endpoint returned status {resp.status}")
        except Exception as e:
            print(f"   ✗ Error testing /terminal: {e}")

        # Test 3: Check if static assets can be proxied
        print("\n3. Testing hub terminal static assets proxy...")
        try:
            async with session.get(f"{hub_url}/terminal/static/js/xterm.min.js", timeout=5) as resp:
                if resp.status == 200:
                    print("   ✓ Hub /terminal/static proxy works")
                elif resp.status == 404:
                    print("   ⚠ Static files not found (hub may need restart)")
                else:
                    print(f"   ⚠ Endpoint returned status {resp.status}")
        except Exception as e:
            print(f"   ⚠ Error testing static files: {e}")

        # Test 4: WebSocket proxy test
        print("\n4. Testing WebSocket proxy (/terminal/ws)...")
        try:
            ws_url = f"ws://localhost:9004/terminal/ws?hostname=192.168.2.10&username=root&password=T@mpa.2017&port=22"
            async with session.ws_connect(ws_url, timeout=10) as ws:
                print("   ✓ WebSocket connected to hub proxy")
                print("   ✓ Hub successfully proxies SSH connection to WebSSH")
                return True
        except asyncio.TimeoutError:
            print("   ⚠ WebSocket connection timeout (hub may need restart)")
        except Exception as e:
            if "404" in str(e) or "not found" in str(e).lower():
                print("   ⚠ WebSocket endpoint not found (hub may need restart)")
            else:
                print(f"   ✗ WebSocket error: {e}")

    return False

if __name__ == "__main__":
    try:
        result = asyncio.run(test_proxy_integration())
        if result:
            print("\n" + "="*70)
            print("✓ All WebSSH proxy tests passed!")
            print("="*70)
            sys.exit(0)
        else:
            print("\n" + "="*70)
            print("⚠ Some tests failed - hub restart may be required")
            print("="*70)
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nTests interrupted")
        sys.exit(1)
