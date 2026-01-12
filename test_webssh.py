#!/usr/bin/env python3
"""
Test WebSSH connection to Proxmox
"""
import asyncio
import aiohttp
import json

HUB_URL = "http://localhost:8888"
PROXMOX_HOST = "192.168.2.10"
PROXMOX_USER = "root"
PROXMOX_PASS = "T@mpa.2017"

async def test_webssh():
    """Test WebSSH WebSocket connection"""
    print("\n" + "="*70)
    print("WEBSSH TEST - Connect to Proxmox")
    print("="*70)
    
    # WebSSH expects connection parameters as URL parameters or POST data
    # Format: ws://localhost:8888/ws?hostname=192.168.2.10&username=root&password=xxx
    
    ws_url = f"ws://localhost:8888/ws?hostname={PROXMOX_HOST}&username={PROXMOX_USER}&password={PROXMOX_PASS}&port=22"
    
    print(f"\nConnecting to: {ws_url}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(ws_url, timeout=10) as ws:
                print("✓ WebSocket connected!")
                
                # Send first command
                cmd = "hostname\n"
                print(f"\nSending command: {cmd}")
                await ws.send_str(cmd)
                
                # Receive response
                print("\nWaiting for response...")
                try:
                    async with asyncio.timeout(5):
                        while True:
                            msg = await ws.receive()
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                print(f"Response: {msg.data}")
                            elif msg.type == aiohttp.WSMsgType.CLOSED:
                                break
                except asyncio.TimeoutError:
                    print("(Timeout - connection may be waiting for input)")
                
                print("\n✓ WebSSH connection working!")
                return True
                
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_webssh())
    exit(0 if result else 1)
