"""
Proxmox API Client for Love-Unlimited Hub
Manages VMs, containers, and infrastructure monitoring
"""

import logging
import asyncio
from typing import Optional, Dict, List, Any
from pathlib import Path
import yaml

try:
    from proxmoxer import ProxmoxAPI, ResourceException
    PROXMOXER_AVAILABLE = True
except ImportError:
    PROXMOXER_AVAILABLE = False
    ProxmoxAPI = None
    ResourceException = Exception

logger = logging.getLogger(__name__)


class ProxmoxClient:
    """Proxmox VE API client wrapper for Love-Unlimited Hub"""

    def __init__(self, config_path: str = "auth/proxmox_config.yaml"):
        """
        Initialize Proxmox client

        Args:
            config_path: Path to Proxmox configuration file
        """
        if not PROXMOXER_AVAILABLE:
            raise ImportError("proxmoxer is not installed. Run: pip install proxmoxer")

        self.config = self._load_config(config_path)
        self._client = None
        self._connected = False
        self._cache = {}

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load Proxmox configuration from YAML file"""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Proxmox config not found at {config_path}")

        with open(config_file, "r") as f:
            config = yaml.safe_load(f)

        if not config or "proxmox" not in config:
            raise ValueError("Invalid Proxmox configuration file")

        return config["proxmox"]

    def connect(self) -> bool:
        """
        Connect to Proxmox VE cluster

        Returns:
            True if connection successful, False otherwise
        """
        try:
            auth = self.config["auth"]
            # Parse token_id format: user@realm!token_name
            token_id = auth["token_id"]
            if "!" in token_id:
                user_realm, token_name = token_id.split("!", 1)
            else:
                user_realm = token_id
                token_name = None

            self._client = ProxmoxAPI(
                self.config["host"],
                user=user_realm,
                token_name=token_name,
                token_value=auth["token_secret"],
                verify_ssl=self.config.get("verify_ssl", False),
                timeout=self.config.get("timeout", 30),
            )

            # Test connection
            self._client.nodes.get()
            self._connected = True
            logger.info(f"Connected to Proxmox at {self.config['host']}")
            return True
        except ResourceException as e:
            logger.error(f"Failed to connect to Proxmox: {str(e)}")
            self._connected = False
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to Proxmox: {str(e)}")
            self._connected = False
            return False

    def is_connected(self) -> bool:
        """Check if connected to Proxmox"""
        return self._connected

    # ============================================================================
    # Node Management
    # ============================================================================

    def get_nodes(self) -> List[Dict[str, Any]]:
        """Get all cluster nodes"""
        if not self._connected:
            raise RuntimeError("Not connected to Proxmox")

        try:
            nodes = self._client.nodes.get()
            return [
                {
                    "node": node["node"],
                    "status": node["status"],
                    "uptime": node.get("uptime", 0),
                    "cpu": node.get("cpu", 0),
                    "maxcpu": node.get("maxcpu", 0),
                    "memory": node.get("memory", 0),
                    "maxmemory": node.get("maxmemory", 0),
                    "disk": node.get("disk", 0),
                    "maxdisk": node.get("maxdisk", 0),
                }
                for node in nodes
            ]
        except ResourceException as e:
            logger.error(f"Failed to get nodes: {str(e)}")
            return []

    def get_node_status(self, node: str) -> Dict[str, Any]:
        """Get detailed status of a specific node"""
        if not self._connected:
            raise RuntimeError("Not connected to Proxmox")

        try:
            status = self._client.nodes(node).status.get()
            return {
                "node": node,
                "status": status.get("status", "unknown"),
                "uptime": status.get("uptime", 0),
                "cpu": status.get("cpu", 0),
                "maxcpu": status.get("maxcpu", 0),
                "memory": status.get("memory", 0),
                "maxmemory": status.get("maxmemory", 0),
                "disk": status.get("disk", 0),
                "maxdisk": status.get("maxdisk", 0),
                "ksm": status.get("ksm", {}),
                "loadavg": status.get("loadavg", []),
            }
        except ResourceException as e:
            logger.error(f"Failed to get node status for {node}: {str(e)}")
            return {}

    # ============================================================================
    # VM Management
    # ============================================================================

    def list_vms(self, node: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all VMs, optionally filtered by node

        Args:
            node: Optional node name to filter by

        Returns:
            List of VM information dictionaries
        """
        if not self._connected:
            raise RuntimeError("Not connected to Proxmox")

        vms = []
        try:
            nodes = [node] if node else [n["node"] for n in self.get_nodes()]

            for node_name in nodes:
                try:
                    node_vms = self._client.nodes(node_name).qemu.get()
                    for vm in node_vms:
                        vms.append({
                            "vmid": vm["vmid"],
                            "name": vm.get("name", ""),
                            "node": node_name,
                            "status": vm.get("status", "unknown"),
                            "uptime": vm.get("uptime", 0),
                            "cpu": vm.get("cpu", 0),
                            "maxcpu": vm.get("maxcpu", 0),
                            "memory": vm.get("memory", 0),
                            "maxmemory": vm.get("maxmemory", 0),
                            "disk": vm.get("disk", 0),
                            "maxdisk": vm.get("maxdisk", 0),
                            "type": "qemu",
                        })
                except ResourceException:
                    logger.warning(f"Failed to get VMs for node {node_name}")

            return vms
        except Exception as e:
            logger.error(f"Failed to list VMs: {str(e)}")
            return []

    def get_vm_status(self, node: str, vmid: int) -> Dict[str, Any]:
        """Get detailed status of a specific VM"""
        if not self._connected:
            raise RuntimeError("Not connected to Proxmox")

        try:
            status = self._client.nodes(node).qemu(vmid).status.current.get()
            return {
                "vmid": vmid,
                "node": node,
                "status": status.get("status", "unknown"),
                "uptime": status.get("uptime", 0),
                "cpu": status.get("cpu", 0),
                "maxcpu": status.get("maxcpu", 0),
                "memory": status.get("memory", 0),
                "maxmemory": status.get("maxmemory", 0),
                "disk": status.get("disk", 0),
                "maxdisk": status.get("maxdisk", 0),
                "pid": status.get("pid"),
            }
        except ResourceException as e:
            logger.error(f"Failed to get VM status for {vmid} on {node}: {str(e)}")
            return {}

    def start_vm(self, node: str, vmid: int) -> bool:
        """Start a VM"""
        if not self._connected:
            raise RuntimeError("Not connected to Proxmox")

        try:
            self._client.nodes(node).qemu(vmid).status.start.create()
            logger.info(f"Started VM {vmid} on {node}")
            return True
        except ResourceException as e:
            logger.error(f"Failed to start VM {vmid}: {str(e)}")
            return False

    def stop_vm(self, node: str, vmid: int, force: bool = False) -> bool:
        """Stop a VM"""
        if not self._connected:
            raise RuntimeError("Not connected to Proxmox")

        try:
            if force:
                self._client.nodes(node).qemu(vmid).status.stop.create()
            else:
                self._client.nodes(node).qemu(vmid).status.shutdown.create()
            logger.info(f"Stopped VM {vmid} on {node}")
            return True
        except ResourceException as e:
            logger.error(f"Failed to stop VM {vmid}: {str(e)}")
            return False

    def reboot_vm(self, node: str, vmid: int) -> bool:
        """Reboot a VM"""
        if not self._connected:
            raise RuntimeError("Not connected to Proxmox")

        try:
            self._client.nodes(node).qemu(vmid).status.reboot.create()
            logger.info(f"Rebooted VM {vmid} on {node}")
            return True
        except ResourceException as e:
            logger.error(f"Failed to reboot VM {vmid}: {str(e)}")
            return False

    # ============================================================================
    # Container Management (LXC)
    # ============================================================================

    def list_containers(self, node: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all containers, optionally filtered by node

        Args:
            node: Optional node name to filter by

        Returns:
            List of container information dictionaries
        """
        if not self._connected:
            raise RuntimeError("Not connected to Proxmox")

        containers = []
        try:
            nodes = [node] if node else [n["node"] for n in self.get_nodes()]

            for node_name in nodes:
                try:
                    node_containers = self._client.nodes(node_name).lxc.get()
                    for container in node_containers:
                        containers.append({
                            "vmid": container["vmid"],
                            "name": container.get("hostname", ""),
                            "node": node_name,
                            "status": container.get("status", "unknown"),
                            "uptime": container.get("uptime", 0),
                            "cpu": container.get("cpu", 0),
                            "maxcpu": container.get("maxcpu", 0),
                            "memory": container.get("memory", 0),
                            "maxmemory": container.get("maxmemory", 0),
                            "disk": container.get("disk", 0),
                            "maxdisk": container.get("maxdisk", 0),
                            "type": "lxc",
                        })
                except ResourceException:
                    logger.warning(f"Failed to get containers for node {node_name}")

            return containers
        except Exception as e:
            logger.error(f"Failed to list containers: {str(e)}")
            return []

    def start_container(self, node: str, vmid: int) -> bool:
        """Start a container"""
        if not self._connected:
            raise RuntimeError("Not connected to Proxmox")

        try:
            self._client.nodes(node).lxc(vmid).status.start.create()
            logger.info(f"Started container {vmid} on {node}")
            return True
        except ResourceException as e:
            logger.error(f"Failed to start container {vmid}: {str(e)}")
            return False

    def stop_container(self, node: str, vmid: int, force: bool = False) -> bool:
        """Stop a container"""
        if not self._connected:
            raise RuntimeError("Not connected to Proxmox")

        try:
            if force:
                self._client.nodes(node).lxc(vmid).status.stop.create()
            else:
                self._client.nodes(node).lxc(vmid).status.shutdown.create()
            logger.info(f"Stopped container {vmid} on {node}")
            return True
        except ResourceException as e:
            logger.error(f"Failed to stop container {vmid}: {str(e)}")
            return False

    # ============================================================================
    # Snapshots
    # ============================================================================

    def list_snapshots(self, node: str, vmid: int) -> List[Dict[str, Any]]:
        """List all snapshots for a VM or container"""
        if not self._connected:
            raise RuntimeError("Not connected to Proxmox")

        try:
            snapshots = self._client.nodes(node).qemu(vmid).snapshot.get()
            return [
                {
                    "name": snap.get("name", ""),
                    "description": snap.get("description", ""),
                    "snaptime": snap.get("snaptime", 0),
                    "vmstate": snap.get("vmstate", 0),
                }
                for snap in snapshots
            ]
        except ResourceException as e:
            logger.error(f"Failed to list snapshots for {vmid}: {str(e)}")
            return []

    def create_snapshot(self, node: str, vmid: int, name: str, description: str = "") -> bool:
        """Create a snapshot"""
        if not self._connected:
            raise RuntimeError("Not connected to Proxmox")

        try:
            self._client.nodes(node).qemu(vmid).snapshot.create(
                snapname=name,
                description=description
            )
            logger.info(f"Created snapshot {name} for VM {vmid}")
            return True
        except ResourceException as e:
            logger.error(f"Failed to create snapshot: {str(e)}")
            return False

    def restore_snapshot(self, node: str, vmid: int, name: str, force: bool = False) -> bool:
        """Restore a snapshot"""
        if not self._connected:
            raise RuntimeError("Not connected to Proxmox")

        try:
            self._client.nodes(node).qemu(vmid).snapshot(name).rollback.create(force=force)
            logger.info(f"Restored snapshot {name} for VM {vmid}")
            return True
        except ResourceException as e:
            logger.error(f"Failed to restore snapshot: {str(e)}")
            return False

    # ============================================================================
    # Utility Methods
    # ============================================================================

    def get_cluster_resources(self) -> Dict[str, Any]:
        """Get cluster-wide resource summary"""
        if not self._connected:
            raise RuntimeError("Not connected to Proxmox")

        try:
            vms = self.list_vms()
            containers = self.list_containers()
            nodes = self.get_nodes()

            return {
                "nodes": len(nodes),
                "nodes_running": sum(1 for n in nodes if n["status"] == "online"),
                "vms_total": len(vms),
                "vms_running": sum(1 for vm in vms if vm["status"] == "running"),
                "containers_total": len(containers),
                "containers_running": sum(1 for c in containers if c["status"] == "running"),
                "total_cpu": sum(n["maxcpu"] for n in nodes),
                "total_memory": sum(n["maxmemory"] for n in nodes),
                "total_disk": sum(n["maxdisk"] for n in nodes),
            }
        except Exception as e:
            logger.error(f"Failed to get cluster resources: {str(e)}")
            return {}

    def disconnect(self):
        """Disconnect from Proxmox"""
        self._client = None
        self._connected = False
        logger.info("Disconnected from Proxmox")


# Singleton instance
_proxmox_client: Optional[ProxmoxClient] = None


def get_proxmox_client() -> ProxmoxClient:
    """Get or create Proxmox client singleton"""
    global _proxmox_client

    if _proxmox_client is None:
        _proxmox_client = ProxmoxClient()
        _proxmox_client.connect()

    return _proxmox_client
