#!/usr/bin/env python3
"""
Execute commands on remote SSH server
"""

import asyncio
import sys
sys.path.append('hub')

from ssh_client import SSHClient

async def execute_remote_command(host, username, password, command):
    """Execute command on remote server"""
    client = SSHClient(host=host, username=username, password=password)

    try:
        await client.connect()
        process = await client.execute_command(command)
        stdout, stderr = await process.communicate()
        await client.disconnect()

        # Handle bytes or str
        if isinstance(stdout, bytes):
            stdout = stdout.decode()
        if isinstance(stderr, bytes):
            stderr = stderr.decode()

        return stdout, stderr, process.returncode
    except Exception as e:
        return '', str(e), -1

async def main():
    if len(sys.argv) < 5:
        print("Usage: python remote_exec.py <host> <username> <password> <command>")
        sys.exit(1)

    host = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    command = ' '.join(sys.argv[4:])

    stdout, stderr, code = await execute_remote_command(host, username, password, command)

    if stdout:
        print(stdout, end='')
    if stderr:
        print(stderr, end='', file=sys.stderr)
    sys.exit(code)

if __name__ == "__main__":
    asyncio.run(main())