#!/usr/bin/env python3
"""
Test all SSH connections from auth/ssh_config.yaml
"""

import asyncio
import sys
import os
sys.path.append('hub')

from ssh_client import load_ssh_config, SSHClient

async def test_ssh_connection(name, config):
    """Test a single SSH connection"""
    print(f"Testing {name}...")

    # Handle auth method
    if config.get('auth_method') == 'password':
        password = config.get('password')
        if not password and 'key_path' in config:
            # key_path might be password
            password = config.get('key_path')
        key_path = None
    else:
        password = None
        key_path = config.get('key_path')

    client = SSHClient(
        host=config['host'],
        port=config.get('port', 22),
        username=config['username'],
        password=password,
        key_path=key_path
    )

    try:
        success = await client.connect()
        if success:
            print(f"  ✅ {name} ({config['host']}) - connected successfully")
            await client.disconnect()
            return True
        else:
            print(f"  ❌ {name} ({config['host']}) - connection failed")
            return False
    except Exception as e:
        print(f"  ❌ {name} ({config['host']}) - error: {e}")
        return False

async def main():
    """Test all SSH connections"""
    print("Testing all SSH connections from auth/ssh_config.yaml\n")

    config = load_ssh_config()
    if not config or 'credentials' not in config:
        print("No credentials found in config")
        return

    results = {}
    for name, cred in config['credentials'].items():
        # Skip if env var not set for debian
        if name == 'debian_vm' and not os.getenv('PROXMOX_DEBIAN_PASS'):
            print(f"  ⏭️  {name} ({cred['host']}) - skipped due to unset PROXMOX_DEBIAN_PASS environment variable")
            results[name] = 'skipped'
            continue

        success = await test_ssh_connection(name, cred)
        results[name] = 'success' if success else 'failed'

    print("\nSummary:")
    for name, status in results.items():
        print(f"  {name}: {status}")

if __name__ == "__main__":
    asyncio.run(main())