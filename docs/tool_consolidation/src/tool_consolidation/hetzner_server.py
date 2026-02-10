"""
Hetzner Server - Consolidated Tool
===================================

VORHER (8 separate Tools):
    server_list, server_status, server_power, server_create,
    server_delete, server_resize, server_rebuild, server_rename

NACHHER (1 konsolidiertes Tool):
    server_manage(action="list|status|power|create|delete|resize|rebuild|rename", ...)

Windsurf sieht nur 1 Tool statt 8!

Author: BF Agent Team
"""

from __future__ import annotations

import logging
from typing import ClassVar, Optional

from .base import ConsolidatedTool, action

logger = logging.getLogger(__name__)


class HetznerServerTool(ConsolidatedTool):
    """Manage Hetzner Cloud servers - all operations via one tool."""

    category: ClassVar[str] = "server"
    description: ClassVar[str] = (
        "Manage Hetzner Cloud servers. "
        "List, create, delete, power control, resize, and more."
    )

    def __init__(self, hetzner_client=None):
        """Initialize with optional Hetzner client (DI)."""
        super().__init__()
        self._client = hetzner_client  # Wird in echtem Server injected

    # ─── READ-ONLY Actions ───────────────────────────────────────────────

    @action("list", "List all servers with status, IP, type", read_only=True)
    async def list_servers(
        self,
        label_selector: Optional[str] = None,
        status_filter: Optional[str] = None,
    ) -> str:
        """List all Hetzner Cloud servers.
        
        Args:
            label_selector: Filter by labels (e.g. 'env=production')
            status_filter: Filter by status (running, off, initializing)
        """
        if self._client:
            servers = await self._client.list_servers(
                label_selector=label_selector,
                status=status_filter,
            )
            return self._format_server_list(servers)
        return "🖥️ [Demo] 2 servers: web-prod-1 (running), db-primary (running)"

    @action("status", "Get detailed server status with metrics", read_only=True)
    async def get_status(
        self,
        server_name: Optional[str] = None,
        server_id: Optional[int] = None,
    ) -> str:
        """Get detailed status of a specific server.
        
        Args:
            server_name: Server name (e.g. 'web-prod-1')
            server_id: Alternative: Server ID
        """
        if self._client:
            server = await self._client.get_server(
                name=server_name, server_id=server_id
            )
            return self._format_server_detail(server)
        return f"🖥️ [Demo] {server_name or server_id}: running, 2 cores, 4GB RAM"

    # ─── MUTATING Actions ────────────────────────────────────────────────

    @action("power", "Power actions: on, off, shutdown, reboot, reset")
    async def power_action(
        self,
        server_name: str,
        power_action: str = "status",
    ) -> str:
        """Execute power action on a server.
        
        Args:
            server_name: Target server name
            power_action: One of: on, off, shutdown, reboot, reset
        """
        valid_actions = {"on", "off", "shutdown", "reboot", "reset", "status"}
        if power_action not in valid_actions:
            return f"❌ Invalid power_action: '{power_action}'. Use: {', '.join(sorted(valid_actions))}"

        if self._client:
            result = await self._client.server_power(server_name, power_action)
            return f"⚡ {server_name}: {power_action} → {result}"
        return f"⚡ [Demo] {server_name}: {power_action} executed"

    @action("create", "Create a new server")
    async def create_server(
        self,
        server_name: str,
        server_type: str = "cx22",
        image: str = "ubuntu-24.04",
        location: str = "nbg1",
        labels: Optional[str] = None,
    ) -> str:
        """Create a new Hetzner Cloud server.
        
        Args:
            server_name: Name for the new server
            server_type: Server type (cx22, cx32, cx42, ...)
            image: OS image (ubuntu-24.04, debian-12, ...)
            location: Datacenter (nbg1, fsn1, hel1)
            labels: Labels as 'key=value,key2=value2'
        """
        if self._client:
            result = await self._client.create_server(
                name=server_name,
                server_type=server_type,
                image=image,
                location=location,
                labels=_parse_labels(labels) if labels else None,
            )
            return f"✅ Server created: {server_name} ({server_type} in {location})"
        return f"✅ [Demo] Would create: {server_name} ({server_type}, {image}, {location})"

    @action("resize", "Resize server (change type)")
    async def resize_server(
        self,
        server_name: str,
        server_type: str,
    ) -> str:
        """Resize a server to a different type. Server must be off.
        
        Args:
            server_name: Target server
            server_type: New type (cx22, cx32, ...)
        """
        if self._client:
            result = await self._client.resize_server(server_name, server_type)
            return f"🔄 {server_name}: resized to {server_type}"
        return f"🔄 [Demo] Would resize {server_name} → {server_type}"

    @action("rename", "Rename a server")
    async def rename_server(
        self,
        server_name: str,
        new_name: str,
    ) -> str:
        """Rename a server.
        
        Args:
            server_name: Current server name
            new_name: New name
        """
        if self._client:
            await self._client.rename_server(server_name, new_name)
            return f"✏️ Renamed: {server_name} → {new_name}"
        return f"✏️ [Demo] Would rename {server_name} → {new_name}"

    # ─── DESTRUCTIVE Actions ─────────────────────────────────────────────

    @action("delete", "Delete a server permanently", destructive=True)
    async def delete_server(
        self,
        server_name: str,
    ) -> str:
        """Delete a server. This is irreversible!
        
        Args:
            server_name: Server to delete
        """
        if self._client:
            await self._client.delete_server(server_name)
            return f"🗑️ Server deleted: {server_name}"
        return f"🗑️ [Demo] Would delete: {server_name}"

    @action("rebuild", "Rebuild server with new image", destructive=True)
    async def rebuild_server(
        self,
        server_name: str,
        image: str = "ubuntu-24.04",
    ) -> str:
        """Rebuild a server with a new OS image. All data will be lost!
        
        Args:
            server_name: Server to rebuild
            image: New OS image
        """
        if self._client:
            await self._client.rebuild_server(server_name, image)
            return f"🔨 Server rebuilt: {server_name} with {image}"
        return f"🔨 [Demo] Would rebuild {server_name} with {image}"

    # ─── Formatters (private) ────────────────────────────────────────────

    def _format_server_list(self, servers) -> str:
        """Format server list as markdown table."""
        if not servers:
            return "No servers found."

        lines = [
            "# 🖥️ Hetzner Servers\n",
            "| Name | Status | IP | Type | DC |",
            "|------|--------|-----|------|-----|",
        ]
        for s in servers:
            status_icon = "🟢" if s.status == "running" else "🔴"
            lines.append(
                f"| {s.name} | {status_icon} {s.status} | `{s.public_ip}` | {s.server_type} | {s.datacenter} |"
            )
        lines.append(f"\n**Total:** {len(servers)} server(s)")
        return "\n".join(lines)

    def _format_server_detail(self, server) -> str:
        """Format detailed server info."""
        return f"""# 🖥️ {server.name}

| Property | Value |
|----------|-------|
| Status | {server.status} |
| IP | {server.public_ip} |
| Type | {server.server_type} |
| Datacenter | {server.datacenter} |
| Cores | {server.cores} |
| RAM | {server.memory_gb} GB |
| Disk | {server.disk_gb} GB |
"""


# =============================================================================
# Helpers
# =============================================================================


def _parse_labels(labels_str: str) -> dict[str, str]:
    """Parse 'key=val,key2=val2' to dict."""
    result = {}
    for pair in labels_str.split(","):
        if "=" in pair:
            k, v = pair.split("=", 1)
            result[k.strip()] = v.strip()
    return result
