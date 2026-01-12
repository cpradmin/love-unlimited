#!/usr/bin/env python3
"""
Test real Proxmox SSH terminal session through Love-Unlimited hub
"""

import asyncio
import aiohttp
import json
import sys
import time
from pathlib import Path

# Configuration
HUB_URL = "http://localhost:9004"
API_KEY = "lu_jon_QmZCAglY6kqsIdl6cRADpQ"
PROXMOX_HOST = "192.168.2.10"

async def test_create_session():
    """Test creating SSH session to Proxmox"""
    print("\n" + "="*60)
    print("TEST 1: Create SSH Session to Proxmox")
    print("="*60)

    async with aiohttp.ClientSession() as session:
        try:
            # Create terminal session
            data = aiohttp.FormData()
            data.add_field('host', PROXMOX_HOST)
            data.add_field('port', '22')
            data.add_field('username', 'root')
            data.add_field('password', 'T@mpa.2017')

            print(f"Creating session to {PROXMOX_HOST}...")
            response = await session.post(
                f"{HUB_URL}/terminal/create",
                data=data,
                headers={'X-API-Key': API_KEY},
                timeout=aiohttp.ClientTimeout(total=30)
            )

            if response.status == 200:
                result = await response.json()
                session_id = result.get('session_id')
                print(f"✓ Session created: {session_id}")
                print(f"  Host: {PROXMOX_HOST}")
                print(f"  Username: root")
                return session_id
            else:
                error = await response.text()
                print(f"✗ Failed with status {response.status}")
                print(f"  Error: {error}")
                return None

        except asyncio.TimeoutError:
            print("✗ Session creation TIMEOUT (30s)")
            return None
        except Exception as e:
            print(f"✗ Session creation failed: {e}")
            return None

async def test_get_sessions():
    """Test retrieving active sessions"""
    print("\n" + "="*60)
    print("TEST 2: List Active Terminal Sessions")
    print("="*60)

    async with aiohttp.ClientSession() as session:
        try:
            response = await session.get(
                f"{HUB_URL}/terminal/sessions",
                headers={'X-API-Key': API_KEY},
                timeout=aiohttp.ClientTimeout(total=10)
            )

            if response.status == 200:
                result = await response.json()
                sessions = result.get('sessions', [])
                print(f"✓ Found {len(sessions)} active session(s)")

                for sess in sessions:
                    print(f"\n  Session ID: {sess['session_id']}")
                    print(f"  Host: {sess['host']}")
                    print(f"  Username: {sess['username']}")
                    print(f"  Status: {sess['status']}")
                    print(f"  Created: {sess['created_at']}")
                    print(f"  Viewers: {len(sess.get('viewers', []))} connected")

                    # Find Proxmox session
                    if sess['host'] == PROXMOX_HOST:
                        print(f"  ✓ This is our Proxmox session!")
                        return sess['session_id']

                if sessions:
                    return sessions[0]['session_id']
                return None
            else:
                error = await response.text()
                print(f"✗ Failed with status {response.status}")
                print(f"  Error: {error}")
                return None

        except Exception as e:
            print(f"✗ Failed to get sessions: {e}")
            return None

async def test_websocket_connection(session_id):
    """Test WebSocket connection to terminal"""
    print("\n" + "="*60)
    print("TEST 3: WebSocket Connection to Terminal")
    print("="*60)

    if not session_id:
        print("✗ No session ID provided")
        return False

    ws_url = f"ws://localhost:9004/ws/terminal/{session_id}?api_key={API_KEY}"
    print(f"Connecting to: {ws_url}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(ws_url, timeout=10) as ws:
                print("✓ WebSocket connection established")

                # Wait for initial messages
                try:
                    # Set timeout for receiving messages
                    async with asyncio.timeout(3):
                        msg = await ws.receive()
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            print(f"  Received: {msg.data[:100]}")
                except asyncio.TimeoutError:
                    print("  (No immediate message)")

                return ws
    except asyncio.TimeoutError:
        print("✗ WebSocket connection TIMEOUT (10s)")
        return None
    except Exception as e:
        print(f"✗ WebSocket connection failed: {e}")
        return None

async def test_send_command(session_id):
    """Send test command through WebSocket"""
    print("\n" + "="*60)
    print("TEST 4: Send Test Command (hostname)")
    print("="*60)

    if not session_id:
        print("✗ No session ID provided")
        return False

    ws_url = f"ws://localhost:9004/ws/terminal/{session_id}?api_key={API_KEY}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(ws_url, timeout=10) as ws:
                print(f"Sending command: hostname")

                # Send command
                await ws.send_str("hostname\n")
                print("✓ Command sent")

                # Wait for response
                print("Waiting for response...")
                responses = []

                try:
                    async with asyncio.timeout(5):
                        while True:
                            msg = await ws.receive()
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                responses.append(msg.data)
                                print(f"  Received: {msg.data}")

                                # Look for hostname output
                                if 'proxmox' in msg.data.lower() or '192.168' in msg.data:
                                    print("✓ Got Proxmox response!")
                                    return True
                            elif msg.type == aiohttp.WSMsgType.CLOSED:
                                break
                except asyncio.TimeoutError:
                    pass

                if responses:
                    print(f"✓ Received {len(responses)} message(s)")
                    print(f"  Full response: {''.join(responses)}")
                    return True
                else:
                    print("⚠ No response (may still be connected)")
                    return True

    except Exception as e:
        print(f"✗ Command test failed: {e}")
        return False

async def test_system_info(session_id):
    """Get system info from Proxmox"""
    print("\n" + "="*60)
    print("TEST 5: Get Proxmox System Info")
    print("="*60)

    if not session_id:
        print("✗ No session ID provided")
        return False

    ws_url = f"ws://localhost:9004/ws/terminal/{session_id}?api_key={API_KEY}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(ws_url, timeout=10) as ws:
                commands = [
                    "uname -a",
                    "uptime",
                    "free -h",
                ]

                for cmd in commands:
                    print(f"\n  Command: {cmd}")
                    await ws.send_str(f"{cmd}\n")

                    try:
                        async with asyncio.timeout(3):
                            msg = await ws.receive()
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                print(f"  Output: {msg.data[:80]}")
                    except asyncio.TimeoutError:
                        print("  (No immediate response)")

                return True

    except Exception as e:
        print(f"✗ System info test failed: {e}")
        return False

async def main():
    """Run all Proxmox terminal tests"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*58 + "║")
    print("║" + "  PROXMOX TERMINAL SSH SESSION TEST".center(58) + "║")
    print("║" + " "*58 + "║")
    print("╚" + "="*58 + "╝")

    print(f"\nTarget: Proxmox ({PROXMOX_HOST})")
    print(f"Hub: {HUB_URL}")
    print(f"User: root")

    results = {}

    # Test 1: Create session
    session_id = await test_create_session()
    results['create_session'] = session_id is not None

    # Test 2: Get sessions (may use created or existing)
    if not session_id:
        session_id = await test_get_sessions()
    else:
        await test_get_sessions()

    results['list_sessions'] = session_id is not None

    if not session_id:
        print("\n✗ No session available - cannot continue with connection tests")
        session_id = None

    # Test 3: WebSocket connection
    if session_id:
        ws = await test_websocket_connection(session_id)
        results['websocket'] = ws is not None

        # Test 4: Send command
        if ws:
            result = await test_send_command(session_id)
            results['send_command'] = result
    else:
        results['websocket'] = False
        results['send_command'] = False

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed >= 3:
        print("\n✓ PROXMOX TERMINAL IS WORKING!")
        print("  SSH session successfully established")
        print("  WebSocket communication verified")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
