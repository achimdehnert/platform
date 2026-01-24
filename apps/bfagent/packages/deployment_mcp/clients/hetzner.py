"""
Hetzner Cloud API Client
========================

Async client for Hetzner Cloud API operations.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import httpx

from deployment_mcp.settings import settings


class ServerStatus(str, Enum):
    """Hetzner server status values."""

    RUNNING = "running"
    INITIALIZING = "initializing"
    STARTING = "starting"
    STOPPING = "stopping"
    OFF = "off"
    DELETING = "deleting"
    MIGRATING = "migrating"
    REBUILDING = "rebuilding"
    UNKNOWN = "unknown"


class PowerAction(str, Enum):
    """Available power actions."""

    POWERON = "poweron"
    POWEROFF = "poweroff"
    REBOOT = "reboot"
    SHUTDOWN = "shutdown"  # Graceful
    RESET = "reset"  # Hard reset


@dataclass
class HetznerServer:
    """Hetzner server representation."""

    id: int
    name: str
    status: ServerStatus
    public_ipv4: str | None
    public_ipv6: str | None
    server_type: str
    datacenter: str
    created: datetime
    labels: dict[str, str]

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "HetznerServer":
        """Create from API response."""
        public_net = data.get("public_net", {})
        ipv4_data = public_net.get("ipv4", {})
        ipv6_data = public_net.get("ipv6", {})

        return cls(
            id=data["id"],
            name=data["name"],
            status=ServerStatus(data.get("status", "unknown")),
            public_ipv4=ipv4_data.get("ip") if ipv4_data else None,
            public_ipv6=ipv6_data.get("ip") if ipv6_data else None,
            server_type=data.get("server_type", {}).get("name", "unknown"),
            datacenter=data.get("datacenter", {}).get("name", "unknown"),
            created=datetime.fromisoformat(data["created"].replace("Z", "+00:00")),
            labels=data.get("labels", {}),
        )


class HetznerClient:
    """Async Hetzner Cloud API client."""

    def __init__(self) -> None:
        self.base_url = settings.hetzner_api_url
        self._client: httpx.AsyncClient | None = None

    @property
    def headers(self) -> dict[str, str]:
        """Get authorization headers."""
        return {
            "Authorization": f"Bearer {settings.hetzner_api_token.get_secret_value()}",
            "Content-Type": "application/json",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self.headers,
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def list_servers(self) -> list[HetznerServer]:
        """List all servers in the account."""
        client = await self._get_client()
        response = await client.get("/servers")
        response.raise_for_status()
        data = response.json()
        return [HetznerServer.from_api(s) for s in data.get("servers", [])]

    async def get_server(self, server_id: int) -> HetznerServer | None:
        """Get a specific server by ID."""
        client = await self._get_client()
        try:
            response = await client.get(f"/servers/{server_id}")
            response.raise_for_status()
            data = response.json()
            return HetznerServer.from_api(data["server"])
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    async def get_server_by_name(self, name: str) -> HetznerServer | None:
        """Get a server by name."""
        servers = await self.list_servers()
        for server in servers:
            if server.name == name:
                return server
        return None

    async def power_action(self, server_id: int, action: PowerAction) -> dict[str, Any]:
        """Execute a power action on a server."""
        client = await self._get_client()
        response = await client.post(f"/servers/{server_id}/actions/{action.value}")
        response.raise_for_status()
        return response.json()

    async def get_server_metrics(
        self, server_id: int, metric_type: str = "cpu", start: str | None = None, end: str | None = None
    ) -> dict[str, Any]:
        """Get server metrics."""
        client = await self._get_client()
        params = {"type": metric_type}
        if start:
            params["start"] = start
        if end:
            params["end"] = end

        response = await client.get(f"/servers/{server_id}/metrics", params=params)
        response.raise_for_status()
        return response.json()


# Singleton instance
_client: HetznerClient | None = None


def get_hetzner_client() -> HetznerClient:
    """Get the singleton Hetzner client."""
    global _client
    if _client is None:
        _client = HetznerClient()
    return _client
