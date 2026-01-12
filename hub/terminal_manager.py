"""
Terminal Session Manager for Love-Unlimited
Manages SSH terminal sessions with sharing capabilities
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, asdict
import redis
import json
import asyncssh

from hub.ssh_client import SSHClient, ssh_pool

logger = logging.getLogger(__name__)

@dataclass
class TerminalSession:
    """Represents an active terminal session"""
    session_id: str
    being_id: str  # Owner/creator
    host: str
    port: int
    username: str
    created_at: datetime
    last_activity: datetime
    status: str  # connecting, connected, disconnected, error
    controller: Optional[str] = None  # being_id with input control
    viewers: Set[str] = None  # being_ids viewing the session
    error_message: Optional[str] = None
    ssh_client: Optional[SSHClient] = None
    streamer_task: Optional[asyncio.Task] = None  # Task for streaming output

    def __post_init__(self):
        if self.viewers is None:
            self.viewers = set()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for Redis storage (exclude non-serializable objects)"""
        return {
            'session_id': self.session_id,
            'being_id': self.being_id,
            'host': self.host,
            'port': self.port,
            'username': self.username,
            'created_at': self.created_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'status': self.status,
            'controller': self.controller,
            'viewers': list(self.viewers) if self.viewers else [],
            'error_message': self.error_message,
            'streamer_task': None,  # Don't serialize tasks
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TerminalSession':
        """Create from dict (Redis data)"""
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['last_activity'] = datetime.fromisoformat(data['last_activity'])
        data['viewers'] = set(data.get('viewers', []))
        data['ssh_client'] = None  # Will be restored on demand
        return cls(**data)

class TerminalSessionManager:
    """Manages terminal sessions with sharing and persistence"""

    def __init__(self, redis_client: redis.Redis, websocket_manager=None):
        self.redis = redis_client
        self.websocket_manager = websocket_manager
        self.sessions: Dict[str, TerminalSession] = {}
        self.session_timeout = timedelta(minutes=30)
        self.cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def start(self):
        """Start the manager"""
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        await self._restore_sessions()

    async def stop(self):
        """Stop the manager and cleanup"""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass

        # Close all sessions
        for session in self.sessions.values():
            if session.ssh_client:
                await session.ssh_client.disconnect()

    async def create_session(self, being_id: str, host: str, port: int = 22,
                           username: str = None, password: str = None,
                           key_path: str = None, use_agent: bool = False) -> str:
        """Create a new terminal session"""
        session_id = str(uuid.uuid4())

        session = TerminalSession(
            session_id=session_id,
            being_id=being_id,
            host=host,
            port=port,
            username=username,
            created_at=datetime.now(),
            last_activity=datetime.now(),
            status='connecting',
            controller=being_id,  # Creator is initial controller
            viewers={being_id}  # Creator is initial viewer
        )

        async with self._lock:
            self.sessions[session_id] = session
            await self._save_session(session)

        # Start connection in background
        asyncio.create_task(self._connect_session(session, password, key_path, use_agent))

        logger.info(f"Created terminal session {session_id} for {being_id} to {username}@{host}:{port}")
        return session_id

    async def _connect_session(self, session: TerminalSession, password: str,
                             key_path: str, use_agent: bool):
        """Connect SSH session in background"""
        try:
            session.status = 'connecting'
            await self._save_session(session)

            # Get SSH client from pool
            ssh_client = await ssh_pool.get_connection(
                session.host, session.port, session.username,
                password, key_path, use_agent
            )

            session.ssh_client = ssh_client
            session.status = 'connected'
            session.controller = session.being_id  # Creator gets control initially

            # Start interactive shell and output streaming
            try:
                shell_process = await session.ssh_client.start_shell()
                session.streamer_task = asyncio.create_task(self._stream_output(session, shell_process))
            except Exception as e:
                session.status = 'error'
                session.error_message = str(e)
                logger.error(f"Failed to start shell: {e}")

            logger.info(f"Terminal session {session.session_id} connected")

        except Exception as e:
            session.status = 'error'
            session.error_message = str(e)
            logger.error(f"Terminal session {session.session_id} connection failed: {e}")

        await self._save_session(session)

    async def _stream_output(self, session: TerminalSession, process: asyncssh.SSHClientProcess):
        """Stream terminal output to all viewers"""
        try:
            while True:
                # Read stdout
                try:
                    stdout_data = await asyncio.wait_for(process.stdout.read(1024), timeout=1.0)
                    if stdout_data and self.websocket_manager:
                        for viewer in session.viewers.copy():
                            try:
                                await self.websocket_manager.send_personal_message({
                                    "type": "terminal_output",
                                    "session_id": session.session_id,
                                    "data": stdout_data.decode('utf-8', errors='replace')
                                }, viewer)
                            except Exception as e:
                                logger.error(f"Failed to send output to {viewer}: {e}")
                except asyncio.TimeoutError:
                    pass

                # Read stderr
                try:
                    stderr_data = await asyncio.wait_for(process.stderr.read(1024), timeout=1.0)
                    if stderr_data and self.websocket_manager:
                        for viewer in session.viewers.copy():
                            try:
                                await self.websocket_manager.send_personal_message({
                                    "type": "terminal_output",
                                    "session_id": session.session_id,
                                    "data": stderr_data.decode('utf-8', errors='replace')
                                }, viewer)
                            except Exception as e:
                                logger.error(f"Failed to send stderr to {viewer}: {e}")
                except asyncio.TimeoutError:
                    pass

                # Check if process ended
                if process.returncode is not None:
                    break

                await asyncio.sleep(0.1)  # Small delay to prevent busy loop

        except Exception as e:
            logger.error(f"Output streaming error for session {session.session_id}: {e}")
        finally:
            # Notify viewers of session end
            if self.websocket_manager:
                for viewer in session.viewers.copy():
                    try:
                        await self.websocket_manager.send_personal_message({
                            "type": "terminal_closed",
                            "session_id": session.session_id
                        }, viewer)
                    except Exception as e:
                        logger.error(f"Failed to send close to {viewer}: {e}")

    async def attach_viewer(self, session_id: str, being_id: str) -> bool:
        """Attach a being as viewer to session"""
        async with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return False

            session.viewers.add(being_id)
            session.last_activity = datetime.now()
            await self._save_session(session)
            return True

    async def detach_viewer(self, session_id: str, being_id: str):
        """Detach a being from session"""
        async with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return

            session.viewers.discard(being_id)
            if session.controller == being_id:
                session.controller = None

            session.last_activity = datetime.now()
            await self._save_session(session)

            # Close session if no viewers
            if not session.viewers:
                await self.close_session(session_id)

    async def set_controller(self, session_id: str, being_id: str) -> bool:
        """Set which being has input control"""
        async with self._lock:
            session = self.sessions.get(session_id)
            if not session or being_id not in session.viewers:
                return False

            session.controller = being_id
            session.last_activity = datetime.now()
            await self._save_session(session)
            return True

    async def get_session(self, session_id: str) -> Optional[TerminalSession]:
        """Get session by ID"""
        async with self._lock:
            return self.sessions.get(session_id)

    async def list_sessions(self, being_id: str = None) -> List[TerminalSession]:
        """List all sessions or sessions for specific being"""
        async with self._lock:
            sessions = list(self.sessions.values())
            if being_id:
                sessions = [s for s in sessions if being_id in s.viewers]
            return sessions

    async def close_session(self, session_id: str):
        """Close and cleanup session"""
        async with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return

            # Cancel streamer task
            if session.streamer_task and not session.streamer_task.done():
                session.streamer_task.cancel()
                try:
                    await session.streamer_task
                except asyncio.CancelledError:
                    pass

            if session.ssh_client:
                await session.ssh_client.disconnect()

            del self.sessions[session_id]
            await self._delete_session(session_id)

            logger.info(f"Closed terminal session {session_id}")

    async def _save_session(self, session: TerminalSession):
        """Save session to Redis"""
        key = f"terminal_session:{session.session_id}"
        data = session.to_dict()
        self.redis.setex(key, int(self.session_timeout.total_seconds()), json.dumps(data))

    async def _delete_session(self, session_id: str):
        """Delete session from Redis"""
        key = f"terminal_session:{session_id}"
        self.redis.delete(key)

    async def _restore_sessions(self):
        """Restore active sessions from Redis on startup"""
        pattern = "terminal_session:*"
        keys = self.redis.keys(pattern)

        for key in keys:
            try:
                data = self.redis.get(key)
                if data:
                    session_data = json.loads(data)
                    session = TerminalSession.from_dict(session_data)
                    self.sessions[session.session_id] = session
                    logger.info(f"Restored terminal session {session.session_id}")
            except Exception as e:
                logger.error(f"Error restoring session {key}: {e}")

    async def _cleanup_loop(self):
        """Periodic cleanup of inactive sessions"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                now = datetime.now()

                async with self._lock:
                    to_close = []
                    for session_id, session in self.sessions.items():
                        if now - session.last_activity > self.session_timeout:
                            to_close.append(session_id)

                    for session_id in to_close:
                        logger.info(f"Auto-closing inactive terminal session {session_id}")
                        await self.close_session(session_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

# Global manager instance
terminal_manager: Optional[TerminalSessionManager] = None

async def get_terminal_manager(websocket_manager=None) -> TerminalSessionManager:
    """Get global terminal manager instance"""
    global terminal_manager
    if terminal_manager is None:
        # Get redis client from main.py or create new
        redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        terminal_manager = TerminalSessionManager(redis_client, websocket_manager)
        await terminal_manager.start()
    return terminal_manager