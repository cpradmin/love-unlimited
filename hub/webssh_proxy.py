"""
WebSSH Proxy - Transparent proxy to WebSSH terminal server

Provides HTTP and WebSocket proxying to the standalone WebSSH server,
enabling secure terminal access through the Love-Unlimited Hub.
"""
from fastapi import Request, WebSocket
from fastapi_proxy_lib.core.websocket import ReverseWebSocketProxy
from fastapi_proxy_lib.core.http import ReverseHttpProxy
from httpx import AsyncClient
import logging

logger = logging.getLogger(__name__)


class WebSSHProxy:
    """Reverse proxy for WebSSH terminal server

    Provides transparent HTTP and WebSocket proxying to the WebSSH server
    running on a separate port, enabling integrated terminal access through
    the main hub without custom WebSocket/SSH code.

    Architecture:
        Browser → FastAPI Hub (/terminal/*)
               → HTTP/WS Proxy
               → WebSSH Server (port 8765)
               → Paramiko SSH client
               → Remote SSH Server (Proxmox)
    """

    def __init__(self, webssh_host: str = "127.0.0.1", webssh_port: int = 8765):
        """Initialize the WebSSH proxy.

        Args:
            webssh_host: WebSSH server host (default: localhost)
            webssh_port: WebSSH server port (default: 8765)
        """
        self.webssh_host = webssh_host
        self.webssh_port = webssh_port
        self.base_ws_url = f"ws://{webssh_host}:{webssh_port}"
        self.base_http_url = f"http://{webssh_host}:{webssh_port}"

        # Initialize HTTP client and proxy handlers
        self.http_client = AsyncClient(timeout=30.0)
        self.ws_proxy = ReverseWebSocketProxy(
            client=self.http_client,
            base_url=self.base_ws_url
        )
        self.http_proxy = ReverseHttpProxy(
            client=self.http_client,
            base_url=self.base_http_url
        )

        logger.info(f"WebSSH proxy initialized → {webssh_host}:{webssh_port}")

    async def proxy_websocket(self, websocket: WebSocket, path: str) -> None:
        """Proxy a WebSocket connection to WebSSH.

        Args:
            websocket: FastAPI WebSocket connection
            path: Request path including query parameters
        """
        await self.ws_proxy.proxy(websocket=websocket, path=path)

    async def proxy_http(self, request: Request, path: str):
        """Proxy an HTTP request to WebSSH.

        Args:
            request: FastAPI Request object
            path: Request path

        Returns:
            Response from WebSSH server
        """
        return await self.http_proxy.proxy(request=request, path=path)

    async def close(self) -> None:
        """Cleanup proxy resources.

        Must be called during hub shutdown to properly close connections
        and release resources.
        """
        try:
            await self.ws_proxy.aclose()
            await self.http_proxy.aclose()
            await self.http_client.aclose()
            logger.info("WebSSH proxy closed")
        except Exception as e:
            logger.error(f"Error closing WebSSH proxy: {e}")
