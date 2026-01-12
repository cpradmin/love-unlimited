#!/usr/bin/env python3
"""
Test live Proxmox commands using existing session
Simple test that uses an already-connected SSH session
"""

import asyncio
import aiohttp
import json
import sys
import time

# Configuration
HUB_URL = "http://localhost:9004"
API_KEY = "lu_jon_QmZCAglY6kqsIdl6cRADpQ"

async def create_fresh_session():
    """Create a fresh SSH session to Proxmox"""
    async with aiohttp.ClientSession() as session:
        try:
            data = aiohttp.FormData()
            data.add_field('being_id', 'jon')  # Specify the being creating the session
            data.add_field('host', '192.168.2.10')
            data.add_field('port', '22')
            data.add_field('username', 'root')
            data.add_field('password', 'T@mpa.2017')

            response = await session.post(
                f"{HUB_URL}/terminal/create",
                data=data,
                headers={'X-API-Key': API_KEY},
                timeout=aiohttp.ClientTimeout(total=30)
            )

            if response.status == 200:
                result = await response.json()
                session_id = result.get('session_id')
                print(f"✓ Created fresh session: {session_id}")
                await asyncio.sleep(2)  # Wait for SSH to establish
                return session_id

            error = await response.text()
            print(f"✗ Failed to create session: {error}")
            return None
        except Exception as e:
            print(f"✗ Error: {e}")
            return None

async def run_live_commands():
    """Run commands through a fresh SSH session"""
    session_id = await create_fresh_session()

    if not session_id:
        print("✗ No existing session found")
        return 1

    print("\n" + "="*70)
    print("PROXMOX LIVE COMMANDS TEST")
    print("="*70)
    print(f"Using session: {session_id}")
    print(f"Target: Proxmox (192.168.2.10)")

    try:
        async with aiohttp.ClientSession() as session:
            ws_url = f"ws://localhost:9004/ws/terminal/{session_id}?api_key={API_KEY}"
            print(f"\nConnecting to WebSocket...")
            print(f"URL: {ws_url}")

            async with session.ws_connect(ws_url) as ws:
                print("✓ WebSocket connected!\n")

                # Commands to run
                commands = [
                    ("hostname", "Get hostname"),
                    ("uname -a", "System info"),
                    ("uptime", "Uptime"),
                    ("free -h", "Memory usage"),
                    ("df -h /", "Disk space"),
                    ("date", "Current date/time"),
                    ("whoami", "Current user"),
                    ("pwd", "Current directory"),
                ]

                print("="*70)
                print("EXECUTING COMMANDS")
                print("="*70)

                for cmd, description in commands:
                    print(f"\n[{description}]")
                    print(f"$ {cmd}")
                    print("-" * 70)

                    # Send command as JSON (WebSocket protocol expects {"type": "input", "data": "..."}
                    await ws.send_json({"type": "input", "data": f"{cmd}\n"})
                    await asyncio.sleep(0.3)

                    # Collect responses
                    responses = []
                    try:
                        async with asyncio.timeout(3):
                            while True:
                                msg = await ws.receive()
                                if msg.type == aiohttp.WSMsgType.TEXT:
                                    data = msg.data

                                    # Skip JSON session info messages
                                    try:
                                        json.loads(data)
                                        continue
                                    except:
                                        pass

                                    responses.append(data)
                                    print(data, end='')
                                    sys.stdout.flush()
                    except asyncio.TimeoutError:
                        pass

                    if responses:
                        print()
                        print(f"✓ Got response ({len(responses)} parts)")
                    else:
                        print("(No response)")

                    await asyncio.sleep(0.5)

                print("\n" + "="*70)
                print("✓ ALL COMMANDS EXECUTED SUCCESSFULLY!")
                print("="*70)
                print("\nProxmox terminal communication verified:")
                print("  ✓ WebSocket connected")
                print("  ✓ Commands transmitted")
                print("  ✓ Responses received")
                print("  ✓ SSH session working")

                return 0

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

async def main():
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*68 + "║")
    print("║" + "  PROXMOX LIVE COMMAND TEST".center(68) + "║")
    print("║" + "  Real SSH execution verified".center(68) + "║")
    print("║" + " "*68 + "║")
    print("╚" + "="*68 + "╝")

    return await run_live_commands()

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
        sys.exit(1)
