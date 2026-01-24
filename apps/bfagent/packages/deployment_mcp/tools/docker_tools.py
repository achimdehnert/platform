"""Docker Container Tools for MCP."""

from typing import Any

from ..clients.docker_client import DockerClient
from ..clients.ssh_client import SSHClient
from ..settings import settings


def _get_docker_client(host: str | None = None) -> tuple[SSHClient, DockerClient]:
    """Get SSH and Docker clients."""
    ssh = SSHClient(host=host or settings.ssh_host)
    docker = DockerClient(ssh)
    return ssh, docker


# =============================================================================
# CONTAINER TOOLS
# =============================================================================


async def container_list(
    host: str | None = None,
    all_containers: bool = False,
) -> dict[str, Any]:
    """List Docker containers."""
    ssh, docker = _get_docker_client(host)
    try:
        await ssh.connect()
        containers = await docker.list_containers(all_containers)
        return {
            "success": True,
            "count": len(containers),
            "containers": [
                {
                    "id": c.id,
                    "name": c.name,
                    "image": c.image,
                    "status": c.status.value,
                    "ports": c.ports,
                }
                for c in containers
            ],
        }
    finally:
        await ssh.disconnect()


async def container_status(
    container_id: str,
    host: str | None = None,
) -> dict[str, Any]:
    """Get container status."""
    ssh, docker = _get_docker_client(host)
    try:
        await ssh.connect()
        container = await docker.get_container(container_id)

        if not container:
            return {"success": False, "error": f"Container '{container_id}' not found"}

        stats = await docker.container_stats(container_id)

        return {
            "success": True,
            "container": {
                "id": container.id,
                "name": container.name,
                "image": container.image,
                "status": container.status.value,
                "ports": container.ports,
            },
            "stats": stats,
        }
    finally:
        await ssh.disconnect()


async def container_logs(
    container_id: str,
    host: str | None = None,
    lines: int = 100,
    since: str | None = None,
) -> dict[str, Any]:
    """Get container logs."""
    ssh, docker = _get_docker_client(host)
    try:
        await ssh.connect()
        logs = await docker.container_logs(container_id, lines, since)
        return {
            "success": True,
            "container_id": container_id,
            "lines": lines,
            "logs": logs,
        }
    finally:
        await ssh.disconnect()


async def container_restart(
    container_id: str,
    host: str | None = None,
) -> dict[str, Any]:
    """Restart a container."""
    ssh, docker = _get_docker_client(host)
    try:
        await ssh.connect()
        success = await docker.restart_container(container_id)
        return {
            "success": success,
            "message": f"Container '{container_id}' restarted" if success else "Restart failed",
        }
    finally:
        await ssh.disconnect()


async def container_stop(
    container_id: str,
    host: str | None = None,
    timeout: int = 10,
) -> dict[str, Any]:
    """Stop a container."""
    ssh, docker = _get_docker_client(host)
    try:
        await ssh.connect()
        success = await docker.stop_container(container_id, timeout)
        return {
            "success": success,
            "message": f"Container '{container_id}' stopped" if success else "Stop failed",
        }
    finally:
        await ssh.disconnect()


async def container_start(
    container_id: str,
    host: str | None = None,
) -> dict[str, Any]:
    """Start a container."""
    ssh, docker = _get_docker_client(host)
    try:
        await ssh.connect()
        success = await docker.start_container(container_id)
        return {
            "success": success,
            "message": f"Container '{container_id}' started" if success else "Start failed",
        }
    finally:
        await ssh.disconnect()


# =============================================================================
# DOCKER COMPOSE TOOLS
# =============================================================================


async def compose_ps(
    host: str | None = None,
    project_path: str | None = None,
) -> dict[str, Any]:
    """List compose services."""
    ssh, docker = _get_docker_client(host)
    try:
        await ssh.connect()
        services = await docker.compose_ps(project_path)
        return {
            "success": True,
            "count": len(services),
            "services": [
                {
                    "name": s.name,
                    "status": s.status,
                    "ports": s.ports,
                }
                for s in services
            ],
        }
    finally:
        await ssh.disconnect()


async def compose_up(
    host: str | None = None,
    project_path: str | None = None,
    build: bool = False,
    services: list[str] | None = None,
) -> dict[str, Any]:
    """Start compose services."""
    ssh, docker = _get_docker_client(host)
    try:
        await ssh.connect()
        output, exit_code = await docker.compose_up(
            project_path, detach=True, build=build, services=services
        )
        return {
            "success": exit_code == 0,
            "exit_code": exit_code,
            "output": output,
        }
    finally:
        await ssh.disconnect()


async def compose_down(
    host: str | None = None,
    project_path: str | None = None,
    volumes: bool = False,
    remove_orphans: bool = False,
    confirm: bool = False,
) -> dict[str, Any]:
    """Stop compose services."""
    if volumes and settings.require_confirmation and not confirm:
        return {
            "success": False,
            "error": "Confirmation required when removing volumes. Set confirm=True.",
        }

    ssh, docker = _get_docker_client(host)
    try:
        await ssh.connect()
        output, exit_code = await docker.compose_down(project_path, volumes, remove_orphans)
        return {
            "success": exit_code == 0,
            "exit_code": exit_code,
            "output": output,
        }
    finally:
        await ssh.disconnect()


async def compose_logs(
    host: str | None = None,
    project_path: str | None = None,
    service: str | None = None,
    lines: int = 100,
) -> dict[str, Any]:
    """Get compose logs."""
    ssh, docker = _get_docker_client(host)
    try:
        await ssh.connect()
        logs = await docker.compose_logs(project_path, service, lines)
        return {
            "success": True,
            "service": service or "all",
            "lines": lines,
            "logs": logs,
        }
    finally:
        await ssh.disconnect()


async def compose_pull(
    host: str | None = None,
    project_path: str | None = None,
    services: list[str] | None = None,
) -> dict[str, Any]:
    """Pull compose images."""
    ssh, docker = _get_docker_client(host)
    try:
        await ssh.connect()
        output, exit_code = await docker.compose_pull(project_path, services)
        return {
            "success": exit_code == 0,
            "exit_code": exit_code,
            "output": output,
        }
    finally:
        await ssh.disconnect()


async def compose_restart(
    host: str | None = None,
    project_path: str | None = None,
    services: list[str] | None = None,
) -> dict[str, Any]:
    """Restart compose services."""
    ssh, docker = _get_docker_client(host)
    try:
        await ssh.connect()
        output, exit_code = await docker.compose_restart(project_path, services)
        return {
            "success": exit_code == 0,
            "exit_code": exit_code,
            "output": output,
        }
    finally:
        await ssh.disconnect()
