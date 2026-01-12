"""
SSH Client Wrapper for Love-Unlimited Terminal Access
Provides async SSH connections with PTY support for terminal sessions
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
import asyncssh
import yaml

logger = logging.getLogger(__name__)

class SSHClient:
    """Async SSH client wrapper with PTY support"""

    def __init__(self, host: str, port: int = 22, username: str = None,
                 password: str = None, key_path: str = None, use_agent: bool = False):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.key_path = key_path
        self.use_agent = use_agent
        self.connection: Optional[asyncssh.SSHClientConnection] = None
        self.process: Optional[asyncssh.SSHClientProcess] = None
        self.connected = False

    async def connect(self) -> bool:
        """Establish SSH connection"""
        try:
            # Prepare auth methods
            options = {}
            if self.password:
                options['password'] = self.password
            if self.key_path and Path(self.key_path).exists():
                options['client_keys'] = [self.key_path]
            if self.use_agent:
                options['agent_path'] = None  # Use default agent

            # Connect
            self.connection = await asyncssh.connect(
                self.host, port=self.port, username=self.username,
                **options
            )
            self.connected = True
            logger.info(f"Connected to {self.username}@{self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"SSH connection failed: {e}")
            self.connected = False
            return False

    async def disconnect(self):
        """Close SSH connection"""
        if self.process:
            self.process.close()
            await self.process.wait_closed()
        if self.connection:
            self.connection.close()
            await self.connection.wait_closed()
        self.connected = False
        logger.info(f"Disconnected from {self.host}")

    async def execute_command(self, command: str, pty: bool = True,
                            term_type: str = 'xterm', term_size: Tuple[int, int] = (80, 24)) -> asyncssh.SSHClientProcess:
        """Execute command with optional PTY"""
        if not self.connected:
            raise ConnectionError("Not connected to SSH server")

        # Set terminal options
        options = {}
        if pty:
            options['term_type'] = term_type
            options['term_size'] = term_size

        self.process = await self.connection.create_process(command, **options)
        return self.process

    async def start_shell(self, term_type: str = 'xterm', term_size: Tuple[int, int] = (80, 24)) -> asyncssh.SSHClientProcess:
        """Start interactive shell"""
        return await self.execute_command('', pty=True, term_type=term_type, term_size=term_size)

    def is_connected(self) -> bool:
        """Check if connection is active"""
        return self.connected and self.connection and not self.connection._transport.is_closing()

class SSHConnectionPool:
    """Manages SSH connection pooling"""

    def __init__(self, max_connections: int = 5):
        self.max_connections = max_connections
        self.connections: Dict[str, SSHClient] = {}
        self.lock = asyncio.Lock()

    async def get_connection(self, host: str, port: int = 22, username: str = None,
                           password: str = None, key_path: str = None, use_agent: bool = False) -> SSHClient:
        """Get or create SSH connection"""
        key = f"{username}@{host}:{port}"

        async with self.lock:
            if key in self.connections and self.connections[key].is_connected():
                return self.connections[key]

            # Create new connection
            client = SSHClient(host, port, username, password, key_path, use_agent)
            if await client.connect():
                if len(self.connections) >= self.max_connections:
                    # Remove oldest inactive connection
                    oldest_key = None
                    oldest_time = None
                    for k, conn in self.connections.items():
                        if not conn.is_connected():
                            oldest_key = k
                            break
                    if oldest_key:
                        await self.connections[oldest_key].disconnect()
                        del self.connections[oldest_key]

                self.connections[key] = client
                return client

        raise ConnectionError(f"Failed to connect to {key}")

    async def close_all(self):
        """Close all connections"""
        for client in self.connections.values():
            await client.disconnect()
        self.connections.clear()

# Global connection pool
ssh_pool = SSHConnectionPool()

def load_ssh_config(config_path: str = "auth/ssh_config.yaml") -> Dict[str, Any]:
    """Load SSH configuration from YAML"""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.warning(f"SSH config not found: {config_path}")
        return {}
    except Exception as e:
        logger.error(f"Error loading SSH config: {e}")
        return {}