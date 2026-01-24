"""SSH Client for remote server operations."""

import asyncio
import os
from pathlib import Path
from typing import Any

from ..settings import settings


class SSHClient:
    """Client for SSH operations on remote servers."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        user: str | None = None,
        key_path: str | None = None,
    ):
        """Initialize SSH client."""
        self.host = host or settings.ssh_host
        self.port = port or settings.ssh_port
        self.user = user or settings.ssh_user
        self.key_path = Path(key_path or settings.ssh_key_path).expanduser()
        self.timeout = settings.ssh_timeout
        self._connection: Any = None

    async def connect(self) -> None:
        """Establish SSH connection."""
        try:
            import asyncssh
        except ImportError as e:
            raise RuntimeError("asyncssh not installed. Run: pip install asyncssh") from e

        # asyncssh may try to resolve a local username via getpass.getuser(), which can
        # import the Unix-only 'pwd' module if it can't find a username in the
        # environment. Ensure common variables are present on Windows.
        fallback_user = os.environ.get("USERNAME") or "user"
        os.environ.setdefault("LOGNAME", fallback_user)
        os.environ.setdefault("USER", fallback_user)

        try:
            self._connection = await asyncssh.connect(
                self.host,
                port=self.port,
                username=self.user,
                client_keys=[str(self.key_path)],
                known_hosts=None,  # Skip host key verification
                connect_timeout=self.timeout,
            )
        except Exception as e:
            raise RuntimeError(f"SSH connection failed: {e}") from e

    async def disconnect(self) -> None:
        """Close SSH connection."""
        if self._connection:
            self._connection.close()
            await self._connection.wait_closed()
            self._connection = None

    async def run(self, command: str, timeout: int | None = None) -> tuple[str, str, int]:
        """
        Run command on remote server.

        Returns: (stdout, stderr, exit_code)
        """
        if not self._connection:
            await self.connect()

        try:
            result = await asyncio.wait_for(
                self._connection.run(command),
                timeout=timeout or self.timeout,
            )
            return (
                result.stdout or "",
                result.stderr or "",
                result.exit_status or 0,
            )
        except asyncio.TimeoutError:
            return "", f"Command timed out after {timeout or self.timeout}s", -1

    async def run_checked(self, command: str, timeout: int | None = None) -> str:
        """Run command and raise on error."""
        stdout, stderr, exit_code = await self.run(command, timeout)
        if exit_code != 0:
            raise RuntimeError(f"Command failed (exit {exit_code}): {stderr or stdout}")
        return stdout

    async def read_file(self, path: str) -> str:
        """Read file content from remote server."""
        stdout, stderr, exit_code = await self.run(f"cat {path}")
        if exit_code != 0:
            raise FileNotFoundError(f"Cannot read {path}: {stderr}")
        return stdout

    async def write_file(self, path: str, content: str, mode: str = "644") -> None:
        """Write content to file on remote server."""
        # Escape content for shell
        escaped = content.replace("'", "'\"'\"'")
        await self.run_checked(f"echo '{escaped}' > {path}")
        await self.run_checked(f"chmod {mode} {path}")

    async def file_exists(self, path: str) -> bool:
        """Check if file exists on remote server."""
        _, _, exit_code = await self.run(f"test -f {path}")
        return exit_code == 0

    async def dir_exists(self, path: str) -> bool:
        """Check if directory exists on remote server."""
        _, _, exit_code = await self.run(f"test -d {path}")
        return exit_code == 0

    async def ensure_dir(self, path: str) -> None:
        """Ensure directory exists on remote server."""
        await self.run_checked(f"mkdir -p {path}")

    async def __aenter__(self) -> "SSHClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.disconnect()


class SSHClientFactory:
    """Factory for creating SSH clients with different hosts."""

    @staticmethod
    def create(
        host: str,
        port: int = 22,
        user: str = "root",
        key_path: str | None = None,
    ) -> SSHClient:
        """Create SSH client for specific host."""
        return SSHClient(
            host=host,
            port=port,
            user=user,
            key_path=key_path,
        )

    @staticmethod
    def from_server_ip(ip: str) -> SSHClient:
        """Create SSH client from server IP."""
        return SSHClient(host=ip)
