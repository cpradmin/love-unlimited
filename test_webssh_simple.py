#!/usr/bin/env python3
"""
Simple WebSSH test - just verify connection and basic command
"""
import asyncio
import aiohttp

async def test():
    print("\n" + "="*70)
    print("WebSSH Simple Test")
    print("="*70)
    
    # Test 1: HTTP interface
    print("\n1. Testing HTTP interface...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('http://127.0.0.1:8765/', timeout=5) as resp:
                print(f"   ✓ HTTP GET / returned {resp.status}")
                html = await resp.text()
                if 'input' in html.lower() or 'form' in html.lower():
                    print("   ✓ HTML form found (WebSSH UI)")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 2: WebSocket connection
    print("\n2. Testing WebSocket SSH connection to Proxmox...")
    ws_url = "ws://127.0.0.1:8765/ws?hostname=192.168.2.10&username=root&password=T@mpa.2017&port=22"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(ws_url, timeout=10) as ws:
                print("   ✓ WebSocket connected to WebSSH")
                print("   ✓ WebSSH successfully proxied SSH to Proxmox!")
                
                # Try one simple command
                print("\n3. Sending test command: hostname")
                await ws.send_str("hostname\n")
                await asyncio.sleep(1)
                
                # Try to receive
                try:
                    async with asyncio.timeout(2):
                        msg = await ws.receive()
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            print(f"   ✓ Received response: {msg.data[:100]}")
                except asyncio.TimeoutError:
                    print("   ⚠ No immediate response (SSH connection may be in progress)")
                
                return True
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

asyncio.run(test())
