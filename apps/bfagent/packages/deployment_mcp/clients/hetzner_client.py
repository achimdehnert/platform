"""Hetzner Cloud API Client."""

import httpx
from typing import Any

from ..models import (
    Server,
    ServerStatus,
    ServerPublicNet,
    ServerCreateRequest,
    ServerCreateResponse,
    ServerType,
    ServerImage,
    ServerLocation,
    Firewall,
    FirewallRule,
    FirewallDirection,
    FirewallProtocol,
    FirewallCreateRequest,
    SSHKey,
    SSHKeyCreateRequest,
    HetznerAction,
    PowerAction,
)
from ..settings import settings


class HetznerClient:
    """Client for Hetzner Cloud API."""

    def __init__(self, api_token: str | None = None):
        """Initialize Hetzner client."""
        self.api_token = api_token or settings.hetzner_api_token.get_secret_value()
        self.base_url = settings.hetzner_api_url
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_token}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    # =========================================================================
    # SERVER OPERATIONS
    # =========================================================================

    async def list_servers(self, label_selector: str | None = None) -> list[Server]:
        """List all servers."""
        client = await self._get_client()
        params = {}
        if label_selector:
            params["label_selector"] = label_selector

        response = await client.get("/servers", params=params)
        response.raise_for_status()
        data = response.json()

        servers = []
        for srv in data.get("servers", []):
            servers.append(self._parse_server(srv))
        return servers

    async def get_server(self, server_id: int) -> Server:
        """Get server by ID."""
        client = await self._get_client()
        response = await client.get(f"/servers/{server_id}")
        response.raise_for_status()
        return self._parse_server(response.json()["server"])

    async def get_server_by_name(self, name: str) -> Server | None:
        """Get server by name."""
        servers = await self.list_servers()
        for server in servers:
            if server.name == name:
                return server
        return None

    async def create_server(self, request: ServerCreateRequest) -> ServerCreateResponse:
        """Create a new server."""
        client = await self._get_client()

        payload: dict[str, Any] = {
            "name": request.name,
            "server_type": request.server_type,
            "image": request.image,
            "location": request.location,
            "start_after_create": request.start_after_create,
        }

        if request.ssh_keys:
            payload["ssh_keys"] = request.ssh_keys
        if request.labels:
            payload["labels"] = request.labels
        if request.user_data:
            payload["user_data"] = request.user_data
        if request.automount:
            payload["automount"] = request.automount

        response = await client.post("/servers", json=payload)
        response.raise_for_status()
        data = response.json()

        return ServerCreateResponse(
            server=self._parse_server(data["server"]),
            root_password=data.get("root_password"),
            action_id=data["action"]["id"],
        )

    async def delete_server(self, server_id: int) -> HetznerAction:
        """Delete a server."""
        client = await self._get_client()
        response = await client.delete(f"/servers/{server_id}")
        response.raise_for_status()
        data = response.json()
        return self._parse_action(data["action"])

    async def server_action(self, server_id: int, action: PowerAction) -> HetznerAction:
        """Execute power action on server."""
        client = await self._get_client()
        response = await client.post(f"/servers/{server_id}/actions/{action.value}")
        response.raise_for_status()
        return self._parse_action(response.json()["action"])

    async def rebuild_server(self, server_id: int, image: str) -> HetznerAction:
        """Rebuild server with new image."""
        client = await self._get_client()
        response = await client.post(
            f"/servers/{server_id}/actions/rebuild",
            json={"image": image},
        )
        response.raise_for_status()
        return self._parse_action(response.json()["action"])

    # =========================================================================
    # SERVER TYPES & IMAGES
    # =========================================================================

    async def list_server_types(self) -> list[ServerType]:
        """List available server types."""
        client = await self._get_client()
        response = await client.get("/server_types")
        response.raise_for_status()
        data = response.json()

        return [
            ServerType(
                id=st["id"],
                name=st["name"],
                description=st["description"],
                cores=st["cores"],
                memory=st["memory"],
                disk=st["disk"],
                prices=st.get("prices", []),
            )
            for st in data.get("server_types", [])
        ]

    async def list_images(self, type_filter: str | None = None) -> list[ServerImage]:
        """List available images."""
        client = await self._get_client()
        params = {}
        if type_filter:
            params["type"] = type_filter

        response = await client.get("/images", params=params)
        response.raise_for_status()
        data = response.json()

        return [
            ServerImage(
                id=img["id"],
                name=img["name"],
                description=img.get("description"),
                type=img["type"],
                os_flavor=img.get("os_flavor"),
                os_version=img.get("os_version"),
            )
            for img in data.get("images", [])
        ]

    async def list_locations(self) -> list[ServerLocation]:
        """List available datacenter locations."""
        client = await self._get_client()
        response = await client.get("/locations")
        response.raise_for_status()
        data = response.json()

        return [
            ServerLocation(
                id=loc["id"],
                name=loc["name"],
                description=loc["description"],
                country=loc["country"],
                city=loc["city"],
                network_zone=loc["network_zone"],
            )
            for loc in data.get("locations", [])
        ]

    # =========================================================================
    # FIREWALL OPERATIONS
    # =========================================================================

    async def list_firewalls(self, label_selector: str | None = None) -> list[Firewall]:
        """List all firewalls."""
        client = await self._get_client()
        params = {}
        if label_selector:
            params["label_selector"] = label_selector

        response = await client.get("/firewalls", params=params)
        response.raise_for_status()
        data = response.json()

        return [self._parse_firewall(fw) for fw in data.get("firewalls", [])]

    async def get_firewall(self, firewall_id: int) -> Firewall:
        """Get firewall by ID."""
        client = await self._get_client()
        response = await client.get(f"/firewalls/{firewall_id}")
        response.raise_for_status()
        return self._parse_firewall(response.json()["firewall"])

    async def create_firewall(self, request: FirewallCreateRequest) -> Firewall:
        """Create a new firewall."""
        client = await self._get_client()

        rules_payload = []
        for rule in request.rules:
            rule_dict: dict[str, Any] = {
                "direction": rule.direction.value,
                "protocol": rule.protocol.value,
            }
            if rule.port:
                rule_dict["port"] = rule.port
            if rule.source_ips:
                rule_dict["source_ips"] = rule.source_ips
            if rule.destination_ips:
                rule_dict["destination_ips"] = rule.destination_ips
            if rule.description:
                rule_dict["description"] = rule.description
            rules_payload.append(rule_dict)

        payload = {
            "name": request.name,
            "rules": rules_payload,
        }
        if request.labels:
            payload["labels"] = request.labels

        response = await client.post("/firewalls", json=payload)
        response.raise_for_status()
        return self._parse_firewall(response.json()["firewall"])

    async def delete_firewall(self, firewall_id: int) -> bool:
        """Delete a firewall."""
        client = await self._get_client()
        response = await client.delete(f"/firewalls/{firewall_id}")
        response.raise_for_status()
        return True

    async def set_firewall_rules(
        self, firewall_id: int, rules: list[FirewallRule]
    ) -> list[HetznerAction]:
        """Set firewall rules (replaces all existing rules)."""
        client = await self._get_client()

        rules_payload = []
        for rule in rules:
            rule_dict: dict[str, Any] = {
                "direction": rule.direction.value,
                "protocol": rule.protocol.value,
            }
            if rule.port:
                rule_dict["port"] = rule.port
            if rule.source_ips:
                rule_dict["source_ips"] = rule.source_ips
            if rule.destination_ips:
                rule_dict["destination_ips"] = rule.destination_ips
            if rule.description:
                rule_dict["description"] = rule.description
            rules_payload.append(rule_dict)

        response = await client.post(
            f"/firewalls/{firewall_id}/actions/set_rules",
            json={"rules": rules_payload},
        )
        response.raise_for_status()
        data = response.json()
        return [self._parse_action(a) for a in data.get("actions", [])]

    async def apply_firewall_to_servers(
        self, firewall_id: int, server_ids: list[int]
    ) -> list[HetznerAction]:
        """Apply firewall to servers."""
        client = await self._get_client()

        apply_to = [{"type": "server", "server": {"id": sid}} for sid in server_ids]

        response = await client.post(
            f"/firewalls/{firewall_id}/actions/apply_to_resources",
            json={"apply_to": apply_to},
        )
        response.raise_for_status()
        data = response.json()
        return [self._parse_action(a) for a in data.get("actions", [])]

    async def remove_firewall_from_servers(
        self, firewall_id: int, server_ids: list[int]
    ) -> list[HetznerAction]:
        """Remove firewall from servers."""
        client = await self._get_client()

        remove_from = [{"type": "server", "server": {"id": sid}} for sid in server_ids]

        response = await client.post(
            f"/firewalls/{firewall_id}/actions/remove_from_resources",
            json={"remove_from": remove_from},
        )
        response.raise_for_status()
        data = response.json()
        return [self._parse_action(a) for a in data.get("actions", [])]

    # =========================================================================
    # SSH KEY OPERATIONS
    # =========================================================================

    async def list_ssh_keys(self, label_selector: str | None = None) -> list[SSHKey]:
        """List all SSH keys."""
        client = await self._get_client()
        params = {}
        if label_selector:
            params["label_selector"] = label_selector

        response = await client.get("/ssh_keys", params=params)
        response.raise_for_status()
        data = response.json()

        return [self._parse_ssh_key(key) for key in data.get("ssh_keys", [])]

    async def get_ssh_key(self, key_id: int) -> SSHKey:
        """Get SSH key by ID."""
        client = await self._get_client()
        response = await client.get(f"/ssh_keys/{key_id}")
        response.raise_for_status()
        return self._parse_ssh_key(response.json()["ssh_key"])

    async def create_ssh_key(self, request: SSHKeyCreateRequest) -> SSHKey:
        """Create a new SSH key."""
        client = await self._get_client()

        payload: dict[str, Any] = {
            "name": request.name,
            "public_key": request.public_key,
        }
        if request.labels:
            payload["labels"] = request.labels

        response = await client.post("/ssh_keys", json=payload)
        response.raise_for_status()
        return self._parse_ssh_key(response.json()["ssh_key"])

    async def delete_ssh_key(self, key_id: int) -> bool:
        """Delete an SSH key."""
        client = await self._get_client()
        response = await client.delete(f"/ssh_keys/{key_id}")
        response.raise_for_status()
        return True

    # =========================================================================
    # ACTION OPERATIONS
    # =========================================================================

    async def get_action(self, action_id: int) -> HetznerAction:
        """Get action status."""
        client = await self._get_client()
        response = await client.get(f"/actions/{action_id}")
        response.raise_for_status()
        return self._parse_action(response.json()["action"])

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _parse_server(self, data: dict[str, Any]) -> Server:
        """Parse server from API response."""
        public_net = data.get("public_net", {})
        ipv4 = public_net.get("ipv4", {}).get("ip") if public_net.get("ipv4") else None
        ipv6 = public_net.get("ipv6", {}).get("ip") if public_net.get("ipv6") else None

        return Server(
            id=data["id"],
            name=data["name"],
            status=ServerStatus(data.get("status", "unknown")),
            public_net=ServerPublicNet(ipv4=ipv4, ipv6=ipv6),
            server_type=data.get("server_type", {}).get("name", "unknown"),
            datacenter=data.get("datacenter", {}).get("name", "unknown"),
            image=data.get("image", {}).get("name") if data.get("image") else None,
            created=data.get("created"),
            labels=data.get("labels", {}),
        )

    def _parse_firewall(self, data: dict[str, Any]) -> Firewall:
        """Parse firewall from API response."""
        rules = []
        for rule_data in data.get("rules", []):
            rules.append(
                FirewallRule(
                    direction=FirewallDirection(rule_data["direction"]),
                    protocol=FirewallProtocol(rule_data["protocol"]),
                    port=rule_data.get("port"),
                    source_ips=rule_data.get("source_ips", []),
                    destination_ips=rule_data.get("destination_ips", []),
                    description=rule_data.get("description"),
                )
            )

        return Firewall(
            id=data["id"],
            name=data["name"],
            rules=rules,
            applied_to=data.get("applied_to", []),
            labels=data.get("labels", {}),
            created=data.get("created"),
        )

    def _parse_ssh_key(self, data: dict[str, Any]) -> SSHKey:
        """Parse SSH key from API response."""
        return SSHKey(
            id=data["id"],
            name=data["name"],
            fingerprint=data["fingerprint"],
            public_key=data["public_key"],
            labels=data.get("labels", {}),
            created=data.get("created"),
        )

    def _parse_action(self, data: dict[str, Any]) -> HetznerAction:
        """Parse action from API response."""
        return HetznerAction(
            id=data["id"],
            command=data["command"],
            status=data["status"],
            progress=data["progress"],
            started=data.get("started"),
            finished=data.get("finished"),
            error=data.get("error"),
        )
