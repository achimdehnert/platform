"""
Docker Client
=============

Remote Docker management via SSH.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from deployment_mcp.clients.ssh import CommandResult, get_ssh_manager
from deployment_mcp.settings import settings


class ContainerState(str, Enum):
    """Docker container states."""

    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    RESTARTING = "restarting"
    REMOVING = "removing"
    EXITED = "exited"
    DEAD = "dead"


@dataclass
class Container:
    """Docker container representation."""

    id: str
    name: str
    image: str
    state: ContainerState
    status: str  # Human-readable status like "Up 2 hours"
    ports: list[str]
    created: datetime | None
    labels: dict[str, str]

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "Container":
        """Create from docker inspect JSON."""
        # Handle docker ps --format json output
        state_str = data.get("State", "unknown")
        if isinstance(state_str, dict):
            state_str = state_str.get("Status", "unknown")

        try:
            state = ContainerState(state_str.lower())
        except ValueError:
            state = ContainerState.DEAD

        # Parse ports
        ports_raw = data.get("Ports", "")
        if isinstance(ports_raw, str):
            ports = [p.strip() for p in ports_raw.split(",") if p.strip()]
        elif isinstance(ports_raw, list):
            ports = ports_raw
        else:
            ports = []

        # Parse created time
        created = None
        created_str = data.get("CreatedAt") or data.get("Created")
        if created_str:
            try:
                # Docker format: "2024-01-15 10:30:00 +0100 CET"
                if " " in created_str:
                    created = datetime.fromisoformat(created_str.split(" +")[0])
            except (ValueError, IndexError):
                pass

        # Parse labels
        labels_raw = data.get("Labels", {})
        if isinstance(labels_raw, str):
            labels = {}
            for item in labels_raw.split(","):
                if "=" in item:
                    k, v = item.split("=", 1)
                    labels[k.strip()] = v.strip()
        else:
            labels = labels_raw or {}

        return cls(
            id=data.get("ID", data.get("Id", ""))[:12],
            name=data.get("Names", data.get("Name", "")).strip("/"),
            image=data.get("Image", ""),
            state=state,
            status=data.get("Status", ""),
            ports=ports,
            created=created,
            labels=labels,
        )


@dataclass
class DockerStats:
    """Container resource statistics."""

    container_id: str
    container_name: str
    cpu_percent: float
    memory_usage: str
    memory_percent: float
    network_io: str
    block_io: str


class DockerClient:
    """Docker client for remote container management."""

    def __init__(self, server_name: str) -> None:
        self.server_name = server_name
        self._ssh = get_ssh_manager()

    async def _run(self, cmd: str) -> CommandResult:
        """Run a Docker command on the remote server."""
        return await self._ssh.run_command(self.server_name, cmd)

    async def list_containers(self, all_containers: bool = False) -> list[Container]:
        """List Docker containers."""
        cmd = "docker ps --format json"
        if all_containers:
            cmd += " -a"

        result = await self._run(cmd)
        if not result.success:
            raise RuntimeError(f"Failed to list containers: {result.stderr}")

        containers = []
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                try:
                    data = json.loads(line)
                    containers.append(Container.from_json(data))
                except json.JSONDecodeError:
                    continue

        return containers

    async def get_container(self, name_or_id: str) -> Container | None:
        """Get a specific container by name or ID."""
        result = await self._run(f"docker inspect {name_or_id} --format json")
        if not result.success:
            return None

        try:
            data = json.loads(result.stdout)
            if isinstance(data, list) and data:
                return Container.from_json(data[0])
        except json.JSONDecodeError:
            pass

        return None

    async def get_logs(
        self,
        container: str,
        lines: int = 100,
        since: str | None = None,
        follow: bool = False,
        timestamps: bool = True,
    ) -> str:
        """Get container logs."""
        cmd = f"docker logs {container}"
        if lines:
            cmd += f" --tail {lines}"
        if since:
            cmd += f" --since {since}"
        if timestamps:
            cmd += " --timestamps"

        result = await self._run(cmd)
        # Docker logs go to stderr for some containers
        return result.stdout or result.stderr

    async def start(self, container: str) -> bool:
        """Start a container."""
        result = await self._run(f"docker start {container}")
        return result.success

    async def stop(self, container: str, timeout: int = 10) -> bool:
        """Stop a container."""
        result = await self._run(f"docker stop -t {timeout} {container}")
        return result.success

    async def restart(self, container: str, timeout: int = 10) -> bool:
        """Restart a container."""
        result = await self._run(f"docker restart -t {timeout} {container}")
        return result.success

    async def exec_command(self, container: str, command: str) -> CommandResult:
        """Execute a command inside a container."""
        # Escape the command properly
        escaped_cmd = command.replace('"', '\\"')
        return await self._run(f'docker exec {container} sh -c "{escaped_cmd}"')

    async def get_stats(self, container: str | None = None) -> list[DockerStats]:
        """Get container resource statistics."""
        cmd = "docker stats --no-stream --format json"
        if container:
            cmd += f" {container}"

        result = await self._run(cmd)
        if not result.success:
            return []

        stats = []
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                try:
                    data = json.loads(line)
                    stats.append(
                        DockerStats(
                            container_id=data.get("ID", "")[:12],
                            container_name=data.get("Name", ""),
                            cpu_percent=float(data.get("CPUPerc", "0%").rstrip("%")),
                            memory_usage=data.get("MemUsage", ""),
                            memory_percent=float(data.get("MemPerc", "0%").rstrip("%")),
                            network_io=data.get("NetIO", ""),
                            block_io=data.get("BlockIO", ""),
                        )
                    )
                except (json.JSONDecodeError, ValueError):
                    continue

        return stats

    # === Docker Compose Operations ===

    async def compose_ps(self, project_dir: str) -> list[Container]:
        """List containers for a compose project."""
        cmd = f"cd {project_dir} && {settings.docker_compose_cmd} ps --format json"
        result = await self._run(cmd)

        if not result.success:
            raise RuntimeError(f"Failed to list compose services: {result.stderr}")

        containers = []
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                try:
                    data = json.loads(line)
                    containers.append(Container.from_json(data))
                except json.JSONDecodeError:
                    continue

        return containers

    async def compose_logs(
        self, project_dir: str, service: str | None = None, lines: int = 100
    ) -> str:
        """Get docker compose logs."""
        cmd = f"cd {project_dir} && {settings.docker_compose_cmd} logs --tail {lines}"
        if service:
            cmd += f" {service}"

        result = await self._run(cmd)
        return result.stdout or result.stderr

    async def compose_up(self, project_dir: str, detach: bool = True, build: bool = False) -> bool:
        """Start docker compose services."""
        cmd = f"cd {project_dir} && {settings.docker_compose_cmd} up"
        if detach:
            cmd += " -d"
        if build:
            cmd += " --build"

        result = await self._run(cmd)
        return result.success

    async def compose_down(self, project_dir: str, volumes: bool = False) -> bool:
        """Stop docker compose services."""
        cmd = f"cd {project_dir} && {settings.docker_compose_cmd} down"
        if volumes:
            cmd += " -v"

        result = await self._run(cmd)
        return result.success

    async def compose_restart(self, project_dir: str, service: str | None = None) -> bool:
        """Restart docker compose services."""
        cmd = f"cd {project_dir} && {settings.docker_compose_cmd} restart"
        if service:
            cmd += f" {service}"

        result = await self._run(cmd)
        return result.success
