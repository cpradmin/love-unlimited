"""
Netbird API Client for Love-Unlimited Hub
Manages VPN peers, networks, and access controls via Netbird API
"""

import logging
import asyncio
from typing import Optional, Dict, List, Any
from pathlib import Path
import yaml
import httpx

logger = logging.getLogger(__name__)


class NetbirdClient:
    """Netbird API client wrapper for Love-Unlimited Hub"""

    def __init__(self, config_path: str = "auth/netbird_config.yaml"):
        """
        Initialize Netbird client

        Args:
            config_path: Path to Netbird configuration file
        """
        self.config = self._load_config(config_path)
        self.base_url = self.config.get("base_url", "https://api.netbird.io")
        self.api_token = self.config.get("api_token")
        self.timeout = httpx.Timeout(30.0)
        self._client = None

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load Netbird configuration from YAML file"""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Netbird config not found at {config_path}")

        with open(config_file, "r") as f:
            config = yaml.safe_load(f)

        if not config or "netbird" not in config:
            raise ValueError("Invalid Netbird config: missing 'netbird' section")

        return config["netbird"]

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with auth headers"""
        if self._client is None:
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=self.timeout
            )
        return self._client

    async def close(self):
        """Close the HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _api_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make authenticated API request"""
        client = await self._get_client()
        url = f"{self.base_url}{endpoint}"

        try:
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Netbird API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Netbird API request failed: {e}")
            raise

    async def list_peers(self) -> List[Dict[str, Any]]:
        """List all VPN peers"""
        return await self._api_request("GET", "/api/peers")

    async def get_peer(self, peer_id: str) -> Dict[str, Any]:
        """Get details of a specific peer"""
        return await self._api_request("GET", f"/api/peers/{peer_id}")

    async def add_peer(self, peer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new VPN peer"""
        return await self._api_request("POST", "/api/peers", json=peer_data)

    async def update_peer(self, peer_id: str, peer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing VPN peer"""
        return await self._api_request("PUT", f"/api/peers/{peer_id}", json=peer_data)

    async def remove_peer(self, peer_id: str) -> bool:
        """Remove a VPN peer"""
        await self._api_request("DELETE", f"/api/peers/{peer_id}")
        return True

    async def list_networks(self) -> List[Dict[str, Any]]:
        """List all networks"""
        return await self._api_request("GET", "/api/networks")

    async def get_network(self, network_id: str) -> Dict[str, Any]:
        """Get details of a specific network"""
        return await self._api_request("GET", f"/api/networks/{network_id}")

    async def add_network(self, network_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new network"""
        return await self._api_request("POST", "/api/networks", json=network_data)

    async def update_network(self, network_id: str, network_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing network"""
        return await self._api_request("PUT", f"/api/networks/{network_id}", json=network_data)

    async def remove_network(self, network_id: str) -> bool:
        """Remove a network"""
        await self._api_request("DELETE", f"/api/networks/{network_id}")
        return True

    async def list_access_rules(self) -> List[Dict[str, Any]]:
        """List all access rules"""
        return await self._api_request("GET", "/api/access-rules")

    async def get_access_rule(self, rule_id: str) -> Dict[str, Any]:
        """Get details of a specific access rule"""
        return await self._api_request("GET", f"/api/access-rules/{rule_id}")

    async def add_access_rule(self, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new access rule"""
        return await self._api_request("POST", "/api/access-rules", json=rule_data)

    async def update_access_rule(self, rule_id: str, rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing access rule"""
        return await self._api_request("PUT", f"/api/access-rules/{rule_id}", json=rule_data)

    async def remove_access_rule(self, rule_id: str) -> bool:
        """Remove an access rule"""
        await self._api_request("DELETE", f"/api/access-rules/{rule_id}")
        return True

    async def get_account(self) -> Dict[str, Any]:
        """Get account information"""
        return await self._api_request("GET", "/api/accounts")


# Global client instance
_netbird_client = None


async def get_netbird_client() -> NetbirdClient:
    """Get or create Netbird client singleton"""
    global _netbird_client

    if _netbird_client is None:
        _netbird_client = NetbirdClient()

    return _netbird_client