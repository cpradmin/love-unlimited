"""
Netdata Proxy - Transparent proxy to Netdata monitoring server

Provides HTTP and WebSocket proxying to the Netdata server,
enabling real-time monitoring access through the Love-Unlimited Hub.
"""
from fastapi import Request, WebSocket
from fastapi_proxy_lib.core.websocket import ReverseWebSocketProxy
from fastapi_proxy_lib.core.http import ReverseHttpProxy
from httpx import AsyncClient
import websockets
import asyncio
import logging
from urllib.parse import quote

logger = logging.getLogger(__name__)


class NetdataProxy:
    """Reverse proxy for Netdata monitoring server

    Provides transparent HTTP and WebSocket proxying to the Netdata server
    running on a separate port, enabling integrated monitoring access through
    the main hub.

    Architecture:
        Browser → FastAPI Hub (/netdata/*)
               → HTTP/WS Proxy
               → Netdata Server (port 19999)
    """

    def __init__(self, netdata_host: str = "127.0.0.1", netdata_port: int = 19999):
        """Initialize the Netdata proxy.

        Args:
            netdata_host: Netdata server host (default: localhost)
            netdata_port: Netdata server port (default: 19999)
        """
        self.netdata_host = netdata_host
        self.netdata_port = netdata_port
        self.base_ws_url = f"ws://{netdata_host}:{netdata_port}/"
        self.base_http_url = f"http://{netdata_host}:{netdata_port}/"

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

        logger.info(f"Netdata proxy initialized → {netdata_host}:{netdata_port}")

    async def proxy_websocket(self, websocket: WebSocket, path: str = "/", query_params: dict = None) -> None:
        """Proxy a WebSocket connection to Netdata using websockets library.

        Args:
            websocket: FastAPI WebSocket connection
            path: Request path
            query_params: Query parameters dict
        """
        query_str = "&".join(f"{k}={quote(str(v))}" for k, v in (query_params or {}).items())
        url = f"{self.base_ws_url}{path}"
        if query_str:
            url += f"?{query_str}"

        try:
            async with websockets.connect(url) as ws:
                # Forward messages between client and Netdata
                async def forward_from_client():
                    try:
                        while True:
                            message = await websocket.receive_text()
                            await ws.send(message)
                    except Exception:
                        pass

                async def forward_from_server():
                    try:
                        async for message in ws:
                            await websocket.send_text(message)
                    except Exception:
                        pass

                await asyncio.gather(forward_from_client(), forward_from_server())
        except Exception as e:
            logger.error(f"WebSocket proxy error: {e}")
            await websocket.close(code=1011, reason="Proxy error")

    async def proxy_http(self, request: Request, path: str = None):
        """Proxy an HTTP request to Netdata.

        Args:
            request: FastAPI Request object
            path: Optional path to override the request path

        Returns:
            Response from Netdata server
        """
        if path:
            return await self.http_proxy.proxy(request=request, path=path)
        else:
            return await self.http_proxy.proxy(request=request)

    async def close(self) -> None:
        """Cleanup proxy resources.

        Must be called during hub shutdown to properly close connections
        """
        await self.http_client.aclose()
        logger.info("Netdata proxy closed")