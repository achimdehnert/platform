"""
Docker Container - Consolidated Tool
=====================================

VORHER (7 separate Tools):
    container_list, container_logs, container_start, container_stop,
    container_restart, container_stats, container_exec

NACHHER (1 konsolidiertes Tool):
    container_manage(action="list|logs|start|stop|restart|stats|exec", ...)

Nutzt SSH-Client um Docker-Befehle auf Remote-Servern auszuführen.

Author: BF Agent Team
"""

from __future__ import annotations

import logging
from typing import ClassVar, Optional

from .base import ConsolidatedTool, action

logger = logging.getLogger(__name__)


class DockerContainerTool(ConsolidatedTool):
    """Manage Docker containers on remote servers via SSH."""

    category: ClassVar[str] = "container"
    description: ClassVar[str] = (
        "Manage Docker containers on Hetzner servers via SSH. "
        "List, inspect logs, start/stop, get stats, and execute commands."
    )

    def __init__(self, ssh_client=None):
        """Initialize with optional SSH client (DI).
        
        Args:
            ssh_client: SSHClient/DockerClient instance for remote execution.
                       If None, runs in demo mode.
        """
        super().__init__()
        self._ssh = ssh_client

    # ─── READ-ONLY Actions ───────────────────────────────────────────────

    @action("list", "List all containers with status, image, ports", read_only=True)
    async def list_containers(
        self,
        server_name: str = "",
        all_containers: bool = False,
        filter_name: Optional[str] = None,
    ) -> str:
        """List Docker containers on a server.
        
        Args:
            server_name: Target server (uses default if empty)
            all_containers: Include stopped containers (default: only running)
            filter_name: Filter by container name pattern
        """
        if self._ssh:
            cmd = "docker ps --format '{{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Image}}\t{{.Ports}}'"
            if all_containers:
                cmd = cmd.replace("docker ps", "docker ps -a")
            if filter_name:
                cmd += f" --filter name={filter_name}"
            result = await self._ssh.execute(server_name, cmd)
            return self._format_container_list(result)
        return self._demo_container_list(all_containers, filter_name)

    @action("logs", "View container logs (tail)", read_only=True)
    async def container_logs(
        self,
        container: str,
        server_name: str = "",
        lines: int = 50,
        follow: bool = False,
        since: Optional[str] = None,
    ) -> str:
        """View logs from a container.
        
        Args:
            container: Container name or ID
            server_name: Target server
            lines: Number of tail lines (default: 50)
            follow: Stream logs (not recommended for MCP)
            since: Show logs since timestamp (e.g. '2h', '30m', '2024-01-01')
        """
        if self._ssh:
            cmd = f"docker logs --tail {lines}"
            if since:
                cmd += f" --since {since}"
            cmd += f" {container}"
            result = await self._ssh.execute(server_name, cmd)
            return result
        return f"📋 [Demo] Logs for {container} (last {lines} lines):\n[2025-01-01 10:00:00] Container started\n[2025-01-01 10:00:01] Listening on :8080"

    @action("stats", "Get container resource usage (CPU, memory, network)", read_only=True)
    async def container_stats(
        self,
        container: Optional[str] = None,
        server_name: str = "",
    ) -> str:
        """Get container resource statistics.
        
        Args:
            container: Specific container (all if empty)
            server_name: Target server
        """
        if self._ssh:
            cmd = "docker stats --no-stream --format '{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}'"
            if container:
                cmd += f" {container}"
            result = await self._ssh.execute(server_name, cmd)
            return self._format_stats(result)
        return self._demo_stats(container)

    @action("inspect", "Get detailed container configuration", read_only=True)
    async def inspect_container(
        self,
        container: str,
        server_name: str = "",
    ) -> str:
        """Inspect a container's configuration and state.
        
        Args:
            container: Container name or ID
            server_name: Target server
        """
        if self._ssh:
            cmd = (
                f"docker inspect --format '"
                f"Name: {{{{.Name}}}}\n"
                f"Image: {{{{.Config.Image}}}}\n"
                f"State: {{{{.State.Status}}}}\n"
                f"Started: {{{{.State.StartedAt}}}}\n"
                f"Restart: {{{{.RestartCount}}}}\n"
                f"IP: {{{{.NetworkSettings.IPAddress}}}}'"
                f" {container}"
            )
            result = await self._ssh.execute(server_name, cmd)
            return f"🔍 Container: {container}\n\n{result}"
        return f"🔍 [Demo] {container}: running, image=nginx:latest, IP=172.17.0.2"

    # ─── MUTATING Actions ────────────────────────────────────────────────

    @action("start", "Start a stopped container")
    async def start_container(
        self,
        container: str,
        server_name: str = "",
    ) -> str:
        """Start a stopped container.
        
        Args:
            container: Container name or ID
            server_name: Target server
        """
        if self._ssh:
            await self._ssh.execute(server_name, f"docker start {container}")
            return f"▶️ Started: {container}"
        return f"▶️ [Demo] Would start: {container}"

    @action("stop", "Stop a running container")
    async def stop_container(
        self,
        container: str,
        server_name: str = "",
        timeout: int = 10,
    ) -> str:
        """Stop a running container.
        
        Args:
            container: Container name or ID
            server_name: Target server
            timeout: Seconds to wait before killing (default: 10)
        """
        if self._ssh:
            await self._ssh.execute(server_name, f"docker stop -t {timeout} {container}")
            return f"⏹️ Stopped: {container}"
        return f"⏹️ [Demo] Would stop: {container} (timeout={timeout}s)"

    @action("restart", "Restart a container")
    async def restart_container(
        self,
        container: str,
        server_name: str = "",
        timeout: int = 10,
    ) -> str:
        """Restart a container.
        
        Args:
            container: Container name or ID
            server_name: Target server
            timeout: Seconds to wait before killing (default: 10)
        """
        if self._ssh:
            await self._ssh.execute(server_name, f"docker restart -t {timeout} {container}")
            return f"🔄 Restarted: {container}"
        return f"🔄 [Demo] Would restart: {container}"

    @action("exec", "Execute a command inside a container")
    async def exec_in_container(
        self,
        container: str,
        command: str,
        server_name: str = "",
        workdir: Optional[str] = None,
        user: Optional[str] = None,
    ) -> str:
        """Execute a command inside a running container.
        
        Args:
            container: Container name or ID
            command: Command to execute
            server_name: Target server
            workdir: Working directory inside container
            user: User to run as (e.g. 'root', 'www-data')
        """
        if self._ssh:
            cmd = "docker exec"
            if workdir:
                cmd += f" -w {workdir}"
            if user:
                cmd += f" -u {user}"
            cmd += f" {container} {command}"
            result = await self._ssh.execute(server_name, cmd)
            return f"💻 exec {container}> {command}\n\n{result}"
        return f"💻 [Demo] Would exec in {container}: {command}"

    # ─── DESTRUCTIVE Actions ─────────────────────────────────────────────

    @action("remove", "Remove a stopped container", destructive=True)
    async def remove_container(
        self,
        container: str,
        server_name: str = "",
        force: bool = False,
    ) -> str:
        """Remove a container. Must be stopped unless force=True.
        
        Args:
            container: Container name or ID
            server_name: Target server
            force: Force remove even if running
        """
        if self._ssh:
            cmd = f"docker rm {'--force ' if force else ''}{container}"
            await self._ssh.execute(server_name, cmd)
            return f"🗑️ Removed: {container}"
        return f"🗑️ [Demo] Would remove: {container} (force={force})"

    # ─── Demo Formatters (private) ───────────────────────────────────────

    def _demo_container_list(self, all_containers: bool, filter_name: Optional[str]) -> str:
        containers = [
            ("abc123", "nginx-proxy", "Up 3 days", "nginx:latest", "80->80, 443->443"),
            ("def456", "app-backend", "Up 3 days", "myapp:v2.1", "8080->8080"),
            ("ghi789", "postgres-14", "Up 3 days", "postgres:14", "5432->5432"),
        ]
        if all_containers:
            containers.append(("jkl012", "old-worker", "Exited (0) 2d ago", "worker:v1", ""))

        if filter_name:
            containers = [c for c in containers if filter_name.lower() in c[1].lower()]

        return self._format_table(containers)

    def _format_table(self, containers) -> str:
        lines = [
            "# 🐳 Docker Containers\n",
            "| ID | Name | Status | Image | Ports |",
            "|----|------|--------|-------|-------|",
        ]
        for cid, name, status, image, ports in containers:
            icon = "🟢" if "Up" in status else "🔴"
            lines.append(f"| `{cid}` | {name} | {icon} {status} | {image} | {ports} |")
        lines.append(f"\n**Total:** {len(containers)} container(s)")
        return "\n".join(lines)

    def _format_container_list(self, raw_output: str) -> str:
        """Parse docker ps output to markdown table."""
        lines_in = raw_output.strip().split("\n")
        containers = []
        for line in lines_in:
            parts = line.split("\t")
            if len(parts) >= 4:
                containers.append(tuple(parts[:5]))
        if containers:
            return self._format_table(containers)
        return "No containers found."

    def _demo_stats(self, container: Optional[str]) -> str:
        lines = [
            "# 📊 Container Stats\n",
            "| Container | CPU | Memory | Net I/O |",
            "|-----------|-----|--------|---------|",
            "| nginx-proxy | 0.5% | 32MiB / 256MiB | 1.2GB / 800MB |",
            "| app-backend | 12.3% | 512MiB / 2GiB | 5.6GB / 3.2GB |",
            "| postgres-14 | 3.1% | 256MiB / 1GiB | 2.1GB / 1.8GB |",
        ]
        return "\n".join(lines)

    def _format_stats(self, raw_output: str) -> str:
        """Parse docker stats output to markdown table."""
        lines = [
            "# 📊 Container Stats\n",
            "| Container | CPU | Memory | Net I/O |",
            "|-----------|-----|--------|---------|",
        ]
        for line in raw_output.strip().split("\n"):
            parts = line.split("\t")
            if len(parts) >= 4:
                lines.append(f"| {parts[0]} | {parts[1]} | {parts[2]} | {parts[3]} |")
        return "\n".join(lines)
