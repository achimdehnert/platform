"""Pydantic models for Deployment MCP Server."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# =============================================================================
# ENUMS
# =============================================================================


class ServerStatus(str, Enum):
    """Hetzner server status."""

    RUNNING = "running"
    STARTING = "starting"
    STOPPING = "stopping"
    OFF = "off"
    DELETING = "deleting"
    MIGRATING = "migrating"
    REBUILDING = "rebuilding"
    UNKNOWN = "unknown"


class PowerAction(str, Enum):
    """Server power actions."""

    ON = "poweron"
    OFF = "poweroff"
    REBOOT = "reboot"
    RESET = "reset"
    SHUTDOWN = "shutdown"


class ContainerStatus(str, Enum):
    """Docker container status."""

    RUNNING = "running"
    EXITED = "exited"
    PAUSED = "paused"
    RESTARTING = "restarting"
    CREATED = "created"
    DEAD = "dead"
    REMOVING = "removing"


class FirewallDirection(str, Enum):
    """Firewall rule direction."""

    IN = "in"
    OUT = "out"


class FirewallProtocol(str, Enum):
    """Firewall rule protocol."""

    TCP = "tcp"
    UDP = "udp"
    ICMP = "icmp"
    GRE = "gre"
    ESP = "esp"


# =============================================================================
# HETZNER SERVER MODELS
# =============================================================================


class ServerType(BaseModel):
    """Hetzner server type."""

    id: int
    name: str
    description: str
    cores: int
    memory: float  # GB
    disk: int  # GB
    prices: list[dict[str, Any]] = Field(default_factory=list)


class ServerImage(BaseModel):
    """Hetzner server image."""

    id: int
    name: str
    description: str | None = None
    type: str  # system, snapshot, backup, app
    os_flavor: str | None = None
    os_version: str | None = None


class ServerLocation(BaseModel):
    """Hetzner datacenter location."""

    id: int
    name: str
    description: str
    country: str
    city: str
    network_zone: str


class ServerPublicNet(BaseModel):
    """Server public network info."""

    ipv4: str | None = None
    ipv6: str | None = None


class Server(BaseModel):
    """Hetzner Cloud Server."""

    id: int
    name: str
    status: ServerStatus
    public_net: ServerPublicNet
    server_type: str
    datacenter: str
    image: str | None = None
    created: datetime | None = None
    labels: dict[str, str] = Field(default_factory=dict)


class ServerCreateRequest(BaseModel):
    """Request to create a new server."""

    name: str = Field(description="Server name")
    server_type: str = Field(default="cx22", description="Server type (cx22, cx32, etc.)")
    image: str = Field(default="ubuntu-24.04", description="OS image")
    location: str = Field(default="fsn1", description="Datacenter location")
    ssh_keys: list[str] = Field(default_factory=list, description="SSH key names or IDs")
    labels: dict[str, str] = Field(default_factory=dict, description="Labels for the server")
    user_data: str | None = Field(default=None, description="Cloud-init user data")
    automount: bool = Field(default=False, description="Auto-mount volumes")
    start_after_create: bool = Field(default=True, description="Start server after creation")


class ServerCreateResponse(BaseModel):
    """Response from server creation."""

    server: Server
    root_password: str | None = None
    action_id: int


# =============================================================================
# FIREWALL MODELS
# =============================================================================


class FirewallRule(BaseModel):
    """Firewall rule."""

    direction: FirewallDirection
    protocol: FirewallProtocol
    port: str | None = None  # e.g., "80", "8000-9000"
    source_ips: list[str] = Field(default_factory=list)  # For inbound
    destination_ips: list[str] = Field(default_factory=list)  # For outbound
    description: str | None = None


class Firewall(BaseModel):
    """Hetzner Cloud Firewall."""

    id: int
    name: str
    rules: list[FirewallRule] = Field(default_factory=list)
    applied_to: list[dict[str, Any]] = Field(default_factory=list)
    labels: dict[str, str] = Field(default_factory=dict)
    created: datetime | None = None


class FirewallCreateRequest(BaseModel):
    """Request to create a firewall."""

    name: str = Field(description="Firewall name")
    rules: list[FirewallRule] = Field(default_factory=list)
    labels: dict[str, str] = Field(default_factory=dict)


class FirewallApplyRequest(BaseModel):
    """Request to apply firewall to servers."""

    firewall_id: int
    server_ids: list[int] = Field(default_factory=list)


# =============================================================================
# SSH KEY MODELS
# =============================================================================


class SSHKey(BaseModel):
    """Hetzner SSH Key."""

    id: int
    name: str
    fingerprint: str
    public_key: str
    labels: dict[str, str] = Field(default_factory=dict)
    created: datetime | None = None


class SSHKeyCreateRequest(BaseModel):
    """Request to create an SSH key."""

    name: str = Field(description="SSH key name")
    public_key: str = Field(description="SSH public key content")
    labels: dict[str, str] = Field(default_factory=dict)


# =============================================================================
# DOCKER MODELS
# =============================================================================


class Container(BaseModel):
    """Docker container info."""

    id: str
    name: str
    image: str
    status: ContainerStatus
    ports: list[str] = Field(default_factory=list)
    created: datetime | None = None


class ComposeService(BaseModel):
    """Docker Compose service status."""

    name: str
    status: str
    replicas: str | None = None
    ports: list[str] = Field(default_factory=list)


# =============================================================================
# DATABASE MODELS
# =============================================================================


class Database(BaseModel):
    """PostgreSQL database info."""

    name: str
    owner: str
    size: str | None = None
    encoding: str = "UTF8"


class DatabaseBackup(BaseModel):
    """Database backup info."""

    filename: str
    database: str
    size: int
    created: datetime


# =============================================================================
# ENVIRONMENT MODELS
# =============================================================================


class EnvVariable(BaseModel):
    """Environment variable."""

    key: str
    value: str
    masked: bool = False


class Secret(BaseModel):
    """Secret (masked environment variable)."""

    key: str
    exists: bool = True
    masked_value: str = "********"


# =============================================================================
# ACTION MODELS
# =============================================================================


class HetznerAction(BaseModel):
    """Hetzner API action."""

    id: int
    command: str
    status: str  # running, success, error
    progress: int
    started: datetime | None = None
    finished: datetime | None = None
    error: dict[str, Any] | None = None


# =============================================================================
# RESPONSE MODELS
# =============================================================================


class OperationResult(BaseModel):
    """Generic operation result."""

    success: bool
    message: str
    data: dict[str, Any] | None = None
    error: str | None = None
