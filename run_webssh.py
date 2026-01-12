#!/usr/bin/env python3
import sys
sys.argv = ['webssh', '--port=8765', '--address=127.0.0.1']

print("\n" + "="*70)
print("WebSSH Server - Port 8765")
print("="*70)
print("\nBrowser: http://127.0.0.1:8765")
print("WebSocket: ws://127.0.0.1:8765/ws?hostname=192.168.2.10&username=root&password=T@mpa.2017&port=22")
print("="*70 + "\n")

from webssh.main import main
main()
