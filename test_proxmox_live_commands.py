#!/usr/bin/env python3
"""
Test live Proxmox commands through Love-Unlimited terminal
Real commands executed on Proxmox and responses captured
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

class ProxmoxTerminalTester:
    def __init__(self):
        self.session_id = None
        self.ws = None
        self.responses = []

    async def create_session(self):
        """Create SSH session to Proxmox"""
        print("\n" + "="*70)
        print("CREATING SSH SESSION TO PROXMOX")
        print("="*70)

        async with aiohttp.ClientSession() as session:
            try:
                data = aiohttp.FormData()
                data.add_field('host', PROXMOX_HOST)
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
                    self.session_id = result.get('session_id')
                    print(f"✓ Session created: {self.session_id}")
                    print(f"  Host: {PROXMOX_HOST}")
                    print(f"  User: root")
                    await asyncio.sleep(2)  # Wait for SSH to establish
                    return True
                else:
                    print(f"✗ Failed: {response.status}")
                    return False

            except Exception as e:
                print(f"✗ Error: {e}")
                return False

    async def connect_websocket(self):
        """Connect to terminal WebSocket"""
        print("\n" + "="*70)
        print("CONNECTING TO TERMINAL WEBSOCKET")
        print("="*70)

        if not self.session_id:
            print("✗ No session ID")
            return False

        try:
            ws_url = f"ws://localhost:9004/ws/terminal/{self.session_id}?api_key={API_KEY}"
            async with aiohttp.ClientSession() as session:
                self.ws = await session.ws_connect(ws_url, timeout=10)
                print(f"✓ WebSocket connected")

                # Wait for initial messages
                try:
                    async with asyncio.timeout(2):
                        msg = await self.ws.receive()
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            print(f"  Initial message: {msg.data[:80]}...")
                except asyncio.TimeoutError:
                    pass

                return True

        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False

    async def send_command(self, command, timeout=5, wait_for_prompt=False):
        """Send command and capture response"""
        if not self.ws or self.ws.closed:
            print(f"✗ WebSocket not connected")
            return None

        try:
            print(f"\n$ {command}")
            print("-" * 70)

            # Send command as JSON (WebSocket protocol expects {"type": "input", "data": "..."})
            await self.ws.send_json({"type": "input", "data": f"{command}\n"})
            await asyncio.sleep(0.5)

            # Collect responses
            responses = []
            start_time = time.time()

            try:
                async with asyncio.timeout(timeout):
                    while True:
                        msg = await self.ws.receive()
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = msg.data
                            responses.append(data)

                            # Print live output
                            if data:
                                # Parse JSON if it's session info
                                try:
                                    json_data = json.loads(data)
                                    if json_data.get('type') == 'session_info':
                                        continue  # Skip session info messages
                                except:
                                    pass

                                print(data, end='')
                                sys.stdout.flush()

                            # Look for prompt to indicate command completion
                            if wait_for_prompt and ('root@' in data or '#' in data):
                                break

                        elif msg.type == aiohttp.WSMsgType.CLOSED:
                            break

            except asyncio.TimeoutError:
                pass

            elapsed = time.time() - start_time

            if responses:
                full_response = ''.join(responses)
                print(f"\n✓ Got response ({elapsed:.2f}s, {len(full_response)} bytes)")
                self.responses.append({
                    'command': command,
                    'output': full_response,
                    'elapsed': elapsed
                })
                return full_response
            else:
                print(f"(No response in {elapsed:.2f}s)")
                return None

        except Exception as e:
            print(f"✗ Error: {e}")
            return None

    async def run_tests(self):
        """Run series of Proxmox commands"""
        print("\n" + "="*70)
        print("EXECUTING LIVE PROXMOX COMMANDS")
        print("="*70)

        commands = [
            ("hostname", "Get Proxmox hostname", 3),
            ("uname -a", "Get system info", 3),
            ("uptime", "Check uptime", 3),
            ("free -h", "Check memory usage", 3),
            ("df -h /", "Check disk space", 3),
            ("ps aux | head -10", "List processes", 5),
            ("ip addr show", "Show network config", 5),
            ("date", "Get current date/time", 3),
            ("cat /etc/os-release | grep PRETTY_NAME", "Get OS version", 3),
            ("systemctl status pveproxy | head -5", "Check Proxmox status", 5),
        ]

        results = []
        for cmd, description, timeout in commands:
            print(f"\n🔹 {description}")
            response = await self.send_command(cmd, timeout=timeout)
            results.append({
                'cmd': cmd,
                'desc': description,
                'success': response is not None and len(response) > 0
            })
            await asyncio.sleep(0.5)

        return results

    async def test_proxmox_api(self):
        """Test Proxmox-specific commands"""
        print("\n" + "="*70)
        print("PROXMOX-SPECIFIC COMMANDS")
        print("="*70)

        proxmox_commands = [
            ("pvesh get /nodes", "List Proxmox nodes", 5),
            ("pvesh get /nodes/proxmox/status", "Get node status", 5),
            ("pveversion", "Get Proxmox version", 3),
            ("corosync-quorumtool -s 2>&1 | head -5", "Check cluster status", 5),
        ]

        results = []
        for cmd, description, timeout in proxmox_commands:
            print(f"\n🔹 {description}")
            response = await self.send_command(cmd, timeout=timeout)
            results.append({
                'cmd': cmd,
                'desc': description,
                'success': response is not None and len(response) > 0
            })
            await asyncio.sleep(0.5)

        return results

    async def close(self):
        """Close WebSocket"""
        if self.ws and not self.ws.closed:
            await self.ws.close()
            print("\n✓ WebSocket closed")

async def main():
    """Run all live command tests"""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*68 + "║")
    print("║" + "  PROXMOX LIVE COMMAND TEST".center(68) + "║")
    print("║" + "  Real SSH commands executed and output captured".center(68) + "║")
    print("║" + " "*68 + "║")
    print("╚" + "="*68 + "╝")

    tester = ProxmoxTerminalTester()

    try:
        # Create session
        if not await tester.create_session():
            print("✗ Failed to create session")
            return 1

        # Connect WebSocket
        if not await tester.connect_websocket():
            print("✗ Failed to connect WebSocket")
            return 1

        # Run standard Linux commands
        print("\n" + "="*70)
        print("PHASE 1: LINUX SYSTEM COMMANDS")
        print("="*70)
        results1 = await tester.run_tests()

        # Run Proxmox-specific commands
        print("\n" + "="*70)
        print("PHASE 2: PROXMOX COMMANDS")
        print("="*70)
        results2 = await tester.test_proxmox_api()

        # Summary
        all_results = results1 + results2
        passed = sum(1 for r in all_results if r['success'])
        total = len(all_results)

        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)

        print(f"\nSuccessful commands: {passed}/{total}")

        if passed > 0:
            print("\n✓ SUCCESSFUL COMMANDS:")
            for r in all_results:
                if r['success']:
                    print(f"  ✓ {r['desc']}: {r['cmd']}")

        if passed < total:
            print(f"\n✗ FAILED COMMANDS:")
            for r in all_results:
                if not r['success']:
                    print(f"  ✗ {r['desc']}: {r['cmd']}")

        print("\n" + "="*70)
        if passed >= 8:
            print("✓ PROXMOX LIVE COMMANDS TEST PASSED!")
            print("  Real SSH execution verified")
            print("  Terminal communication working")
            exit_code = 0
        else:
            print(f"⚠ {total - passed} command(s) had issues")
            exit_code = 1

        print("="*70)

        await tester.close()
        return exit_code

    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        await tester.close()
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
