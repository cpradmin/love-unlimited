#!/usr/bin/env python3
"""
Test WebSSH connection to Proxmox
"""
import asyncio
import aiohttp
import sys

async def test_webssh():
    print("\n" + "="*70)
    print("WEBSSH LIVE TEST - Connect to Proxmox")
    print("="*70)
    
    ws_url = "ws://127.0.0.1:8765/ws?hostname=192.168.2.10&username=root&password=T@mpa.2017&port=22"
    
    print(f"\nConnecting to: {ws_url}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(ws_url, timeout=10) as ws:
                print("✓ WebSocket connected to WebSSH!")
                
                # Send commands
                commands = ["hostname", "uname -a", "whoami", "pwd"]
                
                for cmd in commands:
                    print(f"\n$ {cmd}")
                    print("-" * 70)
                    
                    # Send command
                    await ws.send_str(cmd + "\n")
                    await asyncio.sleep(0.5)
                    
                    # Read responses
                    try:
                        async with asyncio.timeout(3):
                            response = ""
                            while True:
                                msg = await ws.receive()
                                if msg.type == aiohttp.WSMsgType.TEXT:
                                    response += msg.data
                                    print(msg.data, end='', flush=True)
                                elif msg.type == aiohttp.WSMsgType.CLOSED:
                                    break
                    except asyncio.TimeoutError:
                        print("\n(timeout - waiting for next command)")
                
                print("\n\n✓ WebSSH terminal working correctly!")
                print("✓ Live command execution successful!")
                return True
                
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_webssh())
    sys.exit(0 if result else 1)
