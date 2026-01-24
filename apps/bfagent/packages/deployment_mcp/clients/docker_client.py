"""Docker Client for container operations via SSH."""

import json
from typing import Any

from ..models import Container, ContainerStatus, ComposeService
from ..settings import settings
from .ssh_client import SSHClient


class DockerClient:
    """Client for Docker operations via SSH."""

    def __init__(self, ssh_client: SSHClient):
        """Initialize Docker client."""
        self.ssh = ssh_client
        self.compose_path = settings.docker_compose_path

    # =========================================================================
    # CONTAINER OPERATIONS
    # =========================================================================

    async def list_containers(self, all_containers: bool = False) -> list[Container]:
        """List Docker containers."""
        flag = "-a" if all_containers else ""
        format_str = '{"id":"{{.ID}}","name":"{{.Names}}","image":"{{.Image}}","status":"{{.State}}","ports":"{{.Ports}}"}'

        stdout, _, exit_code = await self.ssh.run(
            f'docker ps {flag} --format \'{format_str}\''
        )

        if exit_code != 0:
            return []

        containers = []
        for line in stdout.strip().split("\n"):
            if not line:
                continue
            try:
                data = json.loads(line)
                containers.append(
                    Container(
                        id=data["id"],
                        name=data["name"],
                        image=data["image"],
                        status=self._parse_status(data["status"]),
                        ports=data["ports"].split(", ") if data["ports"] else [],
                    )
                )
            except json.JSONDecodeError:
                continue
        return containers

    async def get_container(self, container_id: str) -> Container | None:
        """Get container by ID or name."""
        format_str = '{"id":"{{.ID}}","name":"{{.Names}}","image":"{{.Image}}","status":"{{.State}}","ports":"{{.Ports}}"}'

        stdout, _, exit_code = await self.ssh.run(
            f'docker ps -a --filter "id={container_id}" --filter "name={container_id}" --format \'{format_str}\''
        )

        if exit_code != 0 or not stdout.strip():
            return None

        line = stdout.strip().split("\n")[0]
        data = json.loads(line)
        return Container(
            id=data["id"],
            name=data["name"],
            image=data["image"],
            status=self._parse_status(data["status"]),
            ports=data["ports"].split(", ") if data["ports"] else [],
        )

    async def container_logs(
        self,
        container_id: str,
        lines: int = 100,
        since: str | None = None,
    ) -> str:
        """Get container logs."""
        cmd = f"docker logs --tail {lines}"
        if since:
            cmd += f" --since {since}"
        cmd += f" {container_id}"

        stdout, stderr, _ = await self.ssh.run(cmd)
        return stdout or stderr

    async def restart_container(self, container_id: str) -> bool:
        """Restart a container."""
        _, _, exit_code = await self.ssh.run(f"docker restart {container_id}")
        return exit_code == 0

    async def stop_container(self, container_id: str, timeout: int = 10) -> bool:
        """Stop a container."""
        _, _, exit_code = await self.ssh.run(f"docker stop -t {timeout} {container_id}")
        return exit_code == 0

    async def start_container(self, container_id: str) -> bool:
        """Start a container."""
        _, _, exit_code = await self.ssh.run(f"docker start {container_id}")
        return exit_code == 0

    async def remove_container(self, container_id: str, force: bool = False) -> bool:
        """Remove a container."""
        flag = "-f" if force else ""
        _, _, exit_code = await self.ssh.run(f"docker rm {flag} {container_id}")
        return exit_code == 0

    async def container_stats(self, container_id: str) -> dict[str, Any]:
        """Get container resource stats."""
        format_str = '{"cpu":"{{.CPUPerc}}","mem":"{{.MemUsage}}","mem_perc":"{{.MemPerc}}","net":"{{.NetIO}}","block":"{{.BlockIO}}"}'

        stdout, _, exit_code = await self.ssh.run(
            f'docker stats --no-stream --format \'{format_str}\' {container_id}'
        )

        if exit_code != 0 or not stdout.strip():
            return {}

        return json.loads(stdout.strip())

    # =========================================================================
    # DOCKER COMPOSE OPERATIONS
    # =========================================================================

    async def compose_ps(self, project_path: str | None = None) -> list[ComposeService]:
        """List compose services."""
        path = project_path or self.compose_path
        format_str = '{"name":"{{.Name}}","status":"{{.Status}}","ports":"{{.Ports}}"}'

        stdout, _, exit_code = await self.ssh.run(
            f'cd {path} && docker compose ps --format \'{format_str}\''
        )

        if exit_code != 0:
            return []

        services = []
        for line in stdout.strip().split("\n"):
            if not line:
                continue
            try:
                data = json.loads(line)
                services.append(
                    ComposeService(
                        name=data["name"],
                        status=data["status"],
                        ports=data["ports"].split(", ") if data["ports"] else [],
                    )
                )
            except json.JSONDecodeError:
                continue
        return services

    async def compose_up(
        self,
        project_path: str | None = None,
        detach: bool = True,
        build: bool = False,
        services: list[str] | None = None,
    ) -> tuple[str, int]:
        """Start compose services."""
        path = project_path or self.compose_path
        cmd = f"cd {path} && docker compose up"

        if detach:
            cmd += " -d"
        if build:
            cmd += " --build"
        if services:
            cmd += " " + " ".join(services)

        stdout, stderr, exit_code = await self.ssh.run(cmd, timeout=300)
        return stdout or stderr, exit_code

    async def compose_down(
        self,
        project_path: str | None = None,
        volumes: bool = False,
        remove_orphans: bool = False,
    ) -> tuple[str, int]:
        """Stop compose services."""
        path = project_path or self.compose_path
        cmd = f"cd {path} && docker compose down"

        if volumes:
            cmd += " -v"
        if remove_orphans:
            cmd += " --remove-orphans"

        stdout, stderr, exit_code = await self.ssh.run(cmd, timeout=120)
        return stdout or stderr, exit_code

    async def compose_logs(
        self,
        project_path: str | None = None,
        service: str | None = None,
        lines: int = 100,
    ) -> str:
        """Get compose logs."""
        path = project_path or self.compose_path
        cmd = f"cd {path} && docker compose logs --tail {lines}"

        if service:
            cmd += f" {service}"

        stdout, stderr, _ = await self.ssh.run(cmd)
        return stdout or stderr

    async def compose_pull(
        self,
        project_path: str | None = None,
        services: list[str] | None = None,
    ) -> tuple[str, int]:
        """Pull compose images."""
        path = project_path or self.compose_path
        cmd = f"cd {path} && docker compose pull"

        if services:
            cmd += " " + " ".join(services)

        stdout, stderr, exit_code = await self.ssh.run(cmd, timeout=300)
        return stdout or stderr, exit_code

    async def compose_restart(
        self,
        project_path: str | None = None,
        services: list[str] | None = None,
    ) -> tuple[str, int]:
        """Restart compose services."""
        path = project_path or self.compose_path
        cmd = f"cd {path} && docker compose restart"

        if services:
            cmd += " " + " ".join(services)

        stdout, stderr, exit_code = await self.ssh.run(cmd, timeout=120)
        return stdout or stderr, exit_code

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _parse_status(self, status: str) -> ContainerStatus:
        """Parse container status string."""
        status_lower = status.lower()
        if "running" in status_lower:
            return ContainerStatus.RUNNING
        elif "exited" in status_lower:
            return ContainerStatus.EXITED
        elif "paused" in status_lower:
            return ContainerStatus.PAUSED
        elif "restarting" in status_lower:
            return ContainerStatus.RESTARTING
        elif "created" in status_lower:
            return ContainerStatus.CREATED
        elif "dead" in status_lower:
            return ContainerStatus.DEAD
        elif "removing" in status_lower:
            return ContainerStatus.REMOVING
        return ContainerStatus.EXITED
