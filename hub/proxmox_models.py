"""
Proxmox API models for Love-Unlimited Hub
Pydantic models for request/response validation
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


# ============================================================================
# Node Models
# ============================================================================

class NodeStatus(BaseModel):
    """Node status information"""
    node: str
    status: str
    uptime: int = 0
    cpu: float = 0
    maxcpu: int = 0
    memory: int = 0
    maxmemory: int = 0
    disk: int = 0
    maxdisk: int = 0
    loadavg: Optional[List[float]] = None


class NodesListResponse(BaseModel):
    """Response from listing all nodes"""
    success: bool
    nodes: List[NodeStatus]


# ============================================================================
# VM Models
# ============================================================================

class VMInfo(BaseModel):
    """Virtual Machine information"""
    vmid: int
    name: str
    node: str
    status: str
    uptime: int = 0
    cpu: float = 0
    maxcpu: int = 0
    memory: int = 0
    maxmemory: int = 0
    disk: int = 0
    maxdisk: int = 0
    type: str = "qemu"


class VMsListResponse(BaseModel):
    """Response from listing VMs"""
    success: bool
    count: int = 0
    vms: List[VMInfo]


class VMStatusResponse(BaseModel):
    """Response from getting VM status"""
    success: bool
    data: Dict[str, Any]


class VMActionRequest(BaseModel):
    """Request to perform an action on a VM"""
    node: str
    vmid: int
    force: bool = False


class VMActionResponse(BaseModel):
    """Response from VM action"""
    success: bool
    message: str
    vmid: int
    node: str


# ============================================================================
# Container Models
# ============================================================================

class ContainerInfo(BaseModel):
    """LXC Container information"""
    vmid: int
    name: str
    node: str
    status: str
    uptime: int = 0
    cpu: float = 0
    maxcpu: int = 0
    memory: int = 0
    maxmemory: int = 0
    disk: int = 0
    maxdisk: int = 0
    type: str = "lxc"


class ContainersListResponse(BaseModel):
    """Response from listing containers"""
    success: bool
    count: int = 0
    containers: List[ContainerInfo]


# ============================================================================
# Snapshot Models
# ============================================================================

class SnapshotInfo(BaseModel):
    """Snapshot information"""
    name: str
    description: str = ""
    snaptime: int = 0
    vmstate: int = 0


class SnapshotsListResponse(BaseModel):
    """Response from listing snapshots"""
    success: bool
    vmid: int
    node: str
    snapshots: List[SnapshotInfo]


class CreateSnapshotRequest(BaseModel):
    """Request to create a snapshot"""
    node: str
    vmid: int
    name: str
    description: str = ""


class RestoreSnapshotRequest(BaseModel):
    """Request to restore a snapshot"""
    node: str
    vmid: int
    name: str
    force: bool = False


# ============================================================================
# Cluster Models
# ============================================================================

class ClusterResourcesResponse(BaseModel):
    """Response from getting cluster resources"""
    success: bool
    nodes: int
    nodes_running: int
    vms_total: int
    vms_running: int
    containers_total: int
    containers_running: int
    total_cpu: int
    total_memory: int
    total_disk: int


class ProxmoxHealthResponse(BaseModel):
    """Proxmox health check response"""
    success: bool
    connected: bool
    message: str
    host: str = ""
    resources: Optional[Dict[str, Any]] = None
