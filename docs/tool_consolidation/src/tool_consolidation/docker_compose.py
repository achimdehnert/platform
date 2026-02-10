"""
Docker Compose - Consolidated Tool
====================================

VORHER (9 separate Tools):
    compose_up, compose_down, compose_status, compose_logs,
    compose_restart, compose_build, compose_pull, compose_exec, deploy_stack

NACHHER (1 konsolidiertes Tool):
    compose_manage(action="up|down|status|logs|restart|build|pull|exec|deploy", ...)

Author: BF Agent Team
"""

from __future__ import annotations

import logging
from typing import ClassVar, Optional

from .base import ConsolidatedTool, action

logger = logging.getLogger(__name__)


class DockerComposeTool(ConsolidatedTool):
    """Manage Docker Compose stacks on remote servers via SSH."""

    category: ClassVar[str] = "compose"
    description: ClassVar[str] = (
        "Manage Docker Compose stacks. "
        "Deploy, start/stop, view status/logs, build, and execute commands in services."
    )

    def __init__(self, ssh_client=None, compose_cmd: str = "docker compose"):
        """Initialize with optional SSH client.
        
        Args:
            ssh_client: SSH client for remote execution
            compose_cmd: docker compose command (or 'docker-compose' for v1)
        """
        super().__init__()
        self._ssh = ssh_client
        self._compose_cmd = compose_cmd

    # ─── Helpers ─────────────────────────────────────────────────────────

    async def _run_compose(
        self, server_name: str, project_dir: str, subcmd: str
    ) -> str:
        """Execute a docker compose command."""
        cmd = f"cd {project_dir} && {self._compose_cmd} {subcmd}"
        if self._ssh:
            return await self._ssh.execute(server_name, cmd)
        return f"[Demo] Would run: {cmd}"

    # ─── READ-ONLY Actions ───────────────────────────────────────────────

    @action("status", "Show status of all services in a compose stack", read_only=True)
    async def compose_status(
        self,
        project_dir: str,
        server_name: str = "",
    ) -> str:
        """Show status of docker compose services.
        
        Args:
            project_dir: Path to docker-compose.yml directory
            server_name: Target server
        """
        if self._ssh:
            result = await self._run_compose(server_name, project_dir, "ps")
            return f"# 📦 Compose Stack: {project_dir}\n\n```\n{result}\n```"
        return self._demo_compose_status(project_dir)

    @action("logs", "View compose service logs", read_only=True)
    async def compose_logs(
        self,
        project_dir: str,
        server_name: str = "",
        service: Optional[str] = None,
        lines: int = 50,
    ) -> str:
        """View logs from compose services.
        
        Args:
            project_dir: Path to docker-compose.yml directory
            server_name: Target server
            service: Specific service (all if empty)
            lines: Number of tail lines
        """
        subcmd = f"logs --tail {lines}"
        if service:
            subcmd += f" {service}"
        if self._ssh:
            result = await self._run_compose(server_name, project_dir, subcmd)
            return f"📋 Compose Logs ({service or 'all'}):\n\n{result}"
        return f"📋 [Demo] Compose logs for {project_dir} ({service or 'all'}, last {lines} lines)"

    # ─── MUTATING Actions ────────────────────────────────────────────────

    @action("up", "Start compose stack (detached)")
    async def compose_up(
        self,
        project_dir: str,
        server_name: str = "",
        build: bool = False,
        service: Optional[str] = None,
    ) -> str:
        """Start docker compose services.
        
        Args:
            project_dir: Path to docker-compose.yml directory
            server_name: Target server
            build: Rebuild images before starting
            service: Start only specific service
        """
        subcmd = "up -d"
        if build:
            subcmd += " --build"
        if service:
            subcmd += f" {service}"
        if self._ssh:
            await self._run_compose(server_name, project_dir, subcmd)
            return f"▶️ Stack started: {project_dir}" + (f" (service: {service})" if service else "")
        return f"▶️ [Demo] Would start: {project_dir}" + (" --build" if build else "")

    @action("restart", "Restart compose services")
    async def compose_restart(
        self,
        project_dir: str,
        server_name: str = "",
        service: Optional[str] = None,
    ) -> str:
        """Restart docker compose services.
        
        Args:
            project_dir: Path to docker-compose.yml directory
            server_name: Target server
            service: Restart only specific service
        """
        subcmd = "restart"
        if service:
            subcmd += f" {service}"
        if self._ssh:
            await self._run_compose(server_name, project_dir, subcmd)
            return f"🔄 Restarted: {project_dir}" + (f" ({service})" if service else "")
        return f"🔄 [Demo] Would restart: {project_dir}"

    @action("build", "Build or rebuild compose images")
    async def compose_build(
        self,
        project_dir: str,
        server_name: str = "",
        service: Optional[str] = None,
        no_cache: bool = False,
    ) -> str:
        """Build docker compose images.
        
        Args:
            project_dir: Path to docker-compose.yml directory
            server_name: Target server
            service: Build only specific service
            no_cache: Build without cache
        """
        subcmd = "build"
        if no_cache:
            subcmd += " --no-cache"
        if service:
            subcmd += f" {service}"
        if self._ssh:
            result = await self._run_compose(server_name, project_dir, subcmd)
            return f"🔨 Build complete: {project_dir}\n\n{result}"
        return f"🔨 [Demo] Would build: {project_dir}" + (" --no-cache" if no_cache else "")

    @action("pull", "Pull latest images for compose services")
    async def compose_pull(
        self,
        project_dir: str,
        server_name: str = "",
        service: Optional[str] = None,
    ) -> str:
        """Pull latest images for compose services.
        
        Args:
            project_dir: Path to docker-compose.yml directory
            server_name: Target server
            service: Pull only specific service
        """
        subcmd = "pull"
        if service:
            subcmd += f" {service}"
        if self._ssh:
            result = await self._run_compose(server_name, project_dir, subcmd)
            return f"⬇️ Pull complete: {project_dir}\n\n{result}"
        return f"⬇️ [Demo] Would pull: {project_dir}"

    @action("exec", "Execute command in a compose service")
    async def compose_exec(
        self,
        project_dir: str,
        service: str,
        command: str,
        server_name: str = "",
        user: Optional[str] = None,
    ) -> str:
        """Execute a command in a running compose service.
        
        Args:
            project_dir: Path to docker-compose.yml directory
            service: Service name
            command: Command to execute
            server_name: Target server
            user: User to run as
        """
        subcmd = "exec"
        if user:
            subcmd += f" -u {user}"
        subcmd += f" {service} {command}"
        if self._ssh:
            result = await self._run_compose(server_name, project_dir, subcmd)
            return f"💻 exec {service}> {command}\n\n{result}"
        return f"💻 [Demo] Would exec in {service}: {command}"

    @action(
        "deploy",
        "Full deployment: pull → build → up (rolling update)",
    )
    async def deploy_stack(
        self,
        project_dir: str,
        server_name: str = "",
        build: bool = True,
        service: Optional[str] = None,
    ) -> str:
        """Full deployment: pull latest images, build, and start.
        
        Executes in order: pull → build → up -d
        
        Args:
            project_dir: Path to docker-compose.yml directory
            server_name: Target server
            build: Include build step
            service: Deploy only specific service
        """
        steps = []

        # Step 1: Pull
        pull_subcmd = "pull"
        if service:
            pull_subcmd += f" {service}"
        if self._ssh:
            await self._run_compose(server_name, project_dir, pull_subcmd)
        steps.append("✅ Pull complete")

        # Step 2: Build (optional)
        if build:
            build_subcmd = "build"
            if service:
                build_subcmd += f" {service}"
            if self._ssh:
                await self._run_compose(server_name, project_dir, build_subcmd)
            steps.append("✅ Build complete")

        # Step 3: Up
        up_subcmd = "up -d"
        if service:
            up_subcmd += f" {service}"
        if self._ssh:
            await self._run_compose(server_name, project_dir, up_subcmd)
        steps.append("✅ Services started")

        report = [
            f"# 🚀 Deployment: {project_dir}",
            "",
            *[f"  {s}" for s in steps],
            "",
            f"**Stack deployed successfully!**",
        ]
        return "\n".join(report)

    # ─── DESTRUCTIVE Actions ─────────────────────────────────────────────

    @action("down", "Stop and remove compose stack", destructive=True)
    async def compose_down(
        self,
        project_dir: str,
        server_name: str = "",
        volumes: bool = False,
        remove_orphans: bool = False,
    ) -> str:
        """Stop and remove compose services.
        
        Args:
            project_dir: Path to docker-compose.yml directory
            server_name: Target server
            volumes: Also remove volumes (DATA LOSS!)
            remove_orphans: Remove orphaned containers
        """
        subcmd = "down"
        if volumes:
            subcmd += " -v"
        if remove_orphans:
            subcmd += " --remove-orphans"
        if self._ssh:
            await self._run_compose(server_name, project_dir, subcmd)
            return f"⏹️ Stack stopped: {project_dir}" + (" (volumes removed!)" if volumes else "")
        return f"⏹️ [Demo] Would stop: {project_dir}" + (" -v" if volumes else "")

    # ─── Demo Formatters ─────────────────────────────────────────────────

    def _demo_compose_status(self, project_dir: str) -> str:
        return f"""# 📦 Compose Stack: {project_dir}

| Service | Status | Ports |
|---------|--------|-------|
| web | 🟢 Up (3 days) | 80→8080 |
| api | 🟢 Up (3 days) | 3000→3000 |
| db | 🟢 Up (3 days) | 5432→5432 |
| redis | 🟢 Up (3 days) | 6379→6379 |

**4 services running**"""
