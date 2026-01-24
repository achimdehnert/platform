"""
SSH Client
==========

Async SSH client for remote command execution using asyncssh.
"""

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import asyncssh

from deployment_mcp.settings import settings


@dataclass
class CommandResult:
    """Result of a remote command execution."""

    stdout: str
    stderr: str
    exit_code: int
    success: bool

    @property
    def output(self) -> str:
        """Combined output (stdout preferred, stderr if empty)."""
        return self.stdout if self.stdout else self.stderr


class SSHClient:
    """Async SSH client for remote server management."""

    def __init__(
        self,
        host: str,
        user: str | None = None,
        port: int | None = None,
        key_path: Path | None = None,
    ) -> None:
        self.host = host
        self.user = user or settings.ssh_user
        self.port = port or settings.ssh_port
        self.key_path = key_path or settings.ssh_key_path
        self._conn: asyncssh.SSHClientConnection | None = None

    async def connect(self) -> None:
        """Establish SSH connection."""
        if self._conn is not None:
            return

        # Build connection options
        options: dict[str, Any] = {
            "host": self.host,
            "port": self.port,
            "username": self.user,
            "client_keys": [str(self.key_path)],
            "connect_timeout": settings.ssh_timeout,
        }

        # Known hosts handling
        if settings.ssh_known_hosts:
            options["known_hosts"] = str(settings.ssh_known_hosts)
        else:
            # Accept any host key (development mode)
            options["known_hosts"] = None

        self._conn = await asyncssh.connect(**options)

    async def disconnect(self) -> None:
        """Close SSH connection."""
        if self._conn:
            self._conn.close()
            await self._conn.wait_closed()
            self._conn = None

    async def run(self, command: str, timeout: int | None = None) -> CommandResult:
        """Execute a command on the remote server."""
        await self.connect()
        assert self._conn is not None

        try:
            result = await asyncio.wait_for(
                self._conn.run(command, check=False),
                timeout=timeout or settings.ssh_timeout,
            )
            return CommandResult(
                stdout=result.stdout or "",
                stderr=result.stderr or "",
                exit_code=result.exit_status or 0,
                success=result.exit_status == 0,
            )
        except asyncio.TimeoutError:
            return CommandResult(
                stdout="",
                stderr=f"Command timed out after {timeout or settings.ssh_timeout}s",
                exit_code=-1,
                success=False,
            )

    async def __aenter__(self) -> "SSHClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.disconnect()


class SSHManager:
    """Manager for multiple SSH connections."""

    def __init__(self) -> None:
        self._connections: dict[str, SSHClient] = {}

    def _resolve_host(self, server_name: str) -> str:
        """Resolve server name to IP/hostname."""
        # Check aliases first
        if server_name in settings.server_aliases:
            return settings.server_aliases[server_name]
        # Assume it's already an IP or hostname
        return server_name

    async def get_client(self, server_name: str) -> SSHClient:
        """Get or create an SSH client for a server."""
        host = self._resolve_host(server_name)

        if host not in self._connections:
            self._connections[host] = SSHClient(host)

        client = self._connections[host]
        await client.connect()
        return client

    async def run_command(self, server_name: str, command: str) -> CommandResult:
        """Run a command on a server."""
        client = await self.get_client(server_name)
        return await client.run(command)

    async def close_all(self) -> None:
        """Close all SSH connections."""
        for client in self._connections.values():
            await client.disconnect()
        self._connections.clear()


# Singleton instance
_manager: SSHManager | None = None


def get_ssh_manager() -> SSHManager:
    """Get the singleton SSH manager."""
    global _manager
    if _manager is None:
        _manager = SSHManager()
    return _manager
