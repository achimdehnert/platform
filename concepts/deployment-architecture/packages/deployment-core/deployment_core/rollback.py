"""
Smart rollback strategies for deployments.

This module provides:
- RollbackManager: Manage deployment history and rollbacks
- RollbackStrategy: Different rollback approaches

Example:
    manager = RollbackManager(deploy_path="/opt/myapp")
    
    # Record deployment
    deployment_id = await manager.record_deployment(
        image_tag="abc123",
        previous_tag="def456"
    )
    
    # Rollback on failure
    if deployment_failed:
        result = await manager.rollback(deployment_id)
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class RollbackStrategy(Enum):
    """Rollback strategies."""

    IMMEDIATE = "immediate"  # Rollback to previous version immediately
    GRADUAL = "gradual"  # Gradually shift traffic back
    CANARY = "canary"  # Roll back canary first, then full
    BLUE_GREEN = "blue_green"  # Switch back to previous environment


@dataclass
class Deployment:
    """Deployment record."""

    id: str
    app: str
    image_tag: str
    previous_tag: str | None
    started_at: datetime
    completed_at: datetime | None = None
    status: str = "in_progress"  # in_progress, success, failed, rolled_back
    triggered_by: str = "unknown"
    workflow_run: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "app": self.app,
            "image_tag": self.image_tag,
            "previous_tag": self.previous_tag,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status,
            "triggered_by": self.triggered_by,
            "workflow_run": self.workflow_run,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Deployment":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            app=data["app"],
            image_tag=data["image_tag"],
            previous_tag=data.get("previous_tag"),
            started_at=datetime.fromisoformat(data["started_at"]),
            completed_at=(
                datetime.fromisoformat(data["completed_at"])
                if data.get("completed_at")
                else None
            ),
            status=data.get("status", "unknown"),
            triggered_by=data.get("triggered_by", "unknown"),
            workflow_run=data.get("workflow_run"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class RollbackResult:
    """Result of a rollback operation."""

    success: bool
    deployment_id: str
    rolled_back_to: str | None
    message: str
    commands_executed: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "deployment_id": self.deployment_id,
            "rolled_back_to": self.rolled_back_to,
            "message": self.message,
            "commands_executed": self.commands_executed,
            "duration_seconds": self.duration_seconds,
            "error": self.error,
        }


class RollbackManager:
    """
    Manage deployment history and rollbacks.

    Example:
        manager = RollbackManager(
            deploy_path="/opt/travel-beat",
            app_name="travel-beat",
            compose_file="docker-compose.prod.yml",
            env_file=".env.prod"
        )

        # Record new deployment
        deployment_id = await manager.record_deployment(
            image_tag="abc123",
            previous_tag="def456",
            triggered_by="github-actions"
        )

        # Mark as failed and rollback
        await manager.mark_failed(deployment_id)
        result = await manager.rollback(deployment_id)
    """

    def __init__(
        self,
        deploy_path: str,
        app_name: str,
        compose_file: str = "docker-compose.prod.yml",
        env_file: str = ".env.prod",
        deployments_dir: str = "deployments",
        max_history: int = 100,
    ):
        self.deploy_path = Path(deploy_path)
        self.app_name = app_name
        self.compose_file = compose_file
        self.env_file = env_file
        self.deployments_dir = self.deploy_path / deployments_dir
        self.max_history = max_history

        # Ensure deployments directory exists
        self.deployments_dir.mkdir(parents=True, exist_ok=True)

    def _generate_deployment_id(self) -> str:
        """Generate unique deployment ID."""
        return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

    def _get_image_tag_var(self) -> str:
        """Get the environment variable name for image tag."""
        # Convert app-name to APP_NAME_IMAGE_TAG
        var_name = self.app_name.upper().replace("-", "_")
        return f"{var_name}_IMAGE_TAG"

    async def record_deployment(
        self,
        image_tag: str,
        previous_tag: str | None = None,
        triggered_by: str = "unknown",
        workflow_run: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Record a new deployment.

        Returns the deployment ID.
        """
        deployment_id = self._generate_deployment_id()

        # If previous_tag not provided, try to get from env file
        if previous_tag is None:
            previous_tag = await self._get_current_tag()

        deployment = Deployment(
            id=deployment_id,
            app=self.app_name,
            image_tag=image_tag,
            previous_tag=previous_tag,
            started_at=datetime.now(timezone.utc),
            status="in_progress",
            triggered_by=triggered_by,
            workflow_run=workflow_run,
            metadata=metadata or {},
        )

        # Save deployment record
        deployment_file = self.deployments_dir / f"{deployment_id}.json"
        deployment_file.write_text(json.dumps(deployment.to_dict(), indent=2))

        logger.info(
            "deployment_recorded",
            deployment_id=deployment_id,
            image_tag=image_tag,
            previous_tag=previous_tag,
        )

        # Cleanup old deployments
        await self._cleanup_old_deployments()

        return deployment_id

    async def mark_success(self, deployment_id: str) -> None:
        """Mark deployment as successful."""
        await self._update_status(deployment_id, "success")

    async def mark_failed(self, deployment_id: str) -> None:
        """Mark deployment as failed."""
        await self._update_status(deployment_id, "failed")

    async def _update_status(self, deployment_id: str, status: str) -> None:
        """Update deployment status."""
        deployment_file = self.deployments_dir / f"{deployment_id}.json"

        if not deployment_file.exists():
            logger.warning("deployment_not_found", deployment_id=deployment_id)
            return

        deployment = Deployment.from_dict(json.loads(deployment_file.read_text()))
        deployment.status = status
        deployment.completed_at = datetime.now(timezone.utc)

        deployment_file.write_text(json.dumps(deployment.to_dict(), indent=2))
        logger.info("deployment_status_updated", deployment_id=deployment_id, status=status)

    async def rollback(
        self,
        deployment_id: str | None = None,
        strategy: RollbackStrategy = RollbackStrategy.IMMEDIATE,
    ) -> RollbackResult:
        """
        Rollback to previous deployment.

        Args:
            deployment_id: Specific deployment to rollback (None = latest)
            strategy: Rollback strategy to use

        Returns:
            RollbackResult with success status and details
        """
        start_time = asyncio.get_event_loop().time()

        try:
            # Get deployment to rollback
            if deployment_id:
                deployment = await self._get_deployment(deployment_id)
            else:
                deployment = await self._get_latest_deployment()

            if not deployment:
                return RollbackResult(
                    success=False,
                    deployment_id=deployment_id or "unknown",
                    rolled_back_to=None,
                    message="No deployment found to rollback",
                )

            previous_tag = deployment.previous_tag
            if not previous_tag:
                return RollbackResult(
                    success=False,
                    deployment_id=deployment.id,
                    rolled_back_to=None,
                    message="No previous tag found for rollback",
                )

            logger.info(
                "starting_rollback",
                deployment_id=deployment.id,
                from_tag=deployment.image_tag,
                to_tag=previous_tag,
                strategy=strategy.value,
            )

            # Execute rollback based on strategy
            if strategy == RollbackStrategy.IMMEDIATE:
                result = await self._immediate_rollback(deployment, previous_tag)
            else:
                # For other strategies, fall back to immediate for now
                result = await self._immediate_rollback(deployment, previous_tag)

            # Update deployment status
            deployment.status = "rolled_back"
            deployment.completed_at = datetime.now(timezone.utc)
            deployment_file = self.deployments_dir / f"{deployment.id}.json"
            deployment_file.write_text(json.dumps(deployment.to_dict(), indent=2))

            # Record rollback as new deployment
            rollback_id = f"rollback_{self._generate_deployment_id()}"
            rollback_record = Deployment(
                id=rollback_id,
                app=self.app_name,
                image_tag=previous_tag,
                previous_tag=deployment.image_tag,
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                status="success" if result.success else "failed",
                triggered_by="auto_rollback",
                metadata={"rolled_back_from": deployment.id},
            )
            rollback_file = self.deployments_dir / f"{rollback_id}.json"
            rollback_file.write_text(json.dumps(rollback_record.to_dict(), indent=2))

            result.duration_seconds = asyncio.get_event_loop().time() - start_time
            return result

        except Exception as e:
            logger.error("rollback_failed", error=str(e))
            return RollbackResult(
                success=False,
                deployment_id=deployment_id or "unknown",
                rolled_back_to=None,
                message="Rollback failed with error",
                error=str(e),
                duration_seconds=asyncio.get_event_loop().time() - start_time,
            )

    async def _immediate_rollback(
        self, deployment: Deployment, target_tag: str
    ) -> RollbackResult:
        """Execute immediate rollback."""
        commands_executed = []

        try:
            # Update env file with previous tag
            env_file_path = self.deploy_path / self.env_file
            image_tag_var = self._get_image_tag_var()

            if env_file_path.exists():
                content = env_file_path.read_text()
                import re

                pattern = f"^{image_tag_var}=.*$"
                replacement = f"{image_tag_var}={target_tag}"

                if re.search(pattern, content, re.MULTILINE):
                    new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
                else:
                    new_content = content + f"\n{replacement}"

                env_file_path.write_text(new_content)
                commands_executed.append(f"Updated {self.env_file}: {image_tag_var}={target_tag}")

            # Execute docker compose up
            compose_cmd = (
                f"cd {self.deploy_path} && "
                f"docker compose -f {self.compose_file} --env-file {self.env_file} "
                f"up -d --force-recreate"
            )

            proc = await asyncio.create_subprocess_shell(
                compose_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)

            commands_executed.append(compose_cmd)

            if proc.returncode != 0:
                return RollbackResult(
                    success=False,
                    deployment_id=deployment.id,
                    rolled_back_to=target_tag,
                    message="Docker compose failed during rollback",
                    commands_executed=commands_executed,
                    error=stderr.decode() if stderr else None,
                )

            return RollbackResult(
                success=True,
                deployment_id=deployment.id,
                rolled_back_to=target_tag,
                message=f"Successfully rolled back to {target_tag}",
                commands_executed=commands_executed,
            )

        except asyncio.TimeoutError:
            return RollbackResult(
                success=False,
                deployment_id=deployment.id,
                rolled_back_to=target_tag,
                message="Rollback timed out",
                commands_executed=commands_executed,
                error="TimeoutError: Docker compose took too long",
            )

    async def _get_deployment(self, deployment_id: str) -> Deployment | None:
        """Get deployment by ID."""
        deployment_file = self.deployments_dir / f"{deployment_id}.json"
        if deployment_file.exists():
            return Deployment.from_dict(json.loads(deployment_file.read_text()))
        return None

    async def _get_latest_deployment(self) -> Deployment | None:
        """Get the most recent deployment."""
        deployment_files = sorted(self.deployments_dir.glob("*.json"), reverse=True)

        # Skip rollback records
        for f in deployment_files:
            if f.stem.startswith("rollback_"):
                continue
            return Deployment.from_dict(json.loads(f.read_text()))

        return None

    async def _get_current_tag(self) -> str | None:
        """Get current image tag from env file."""
        env_file_path = self.deploy_path / self.env_file
        image_tag_var = self._get_image_tag_var()

        if env_file_path.exists():
            import re

            content = env_file_path.read_text()
            match = re.search(f"^{image_tag_var}=(.+)$", content, re.MULTILINE)
            if match:
                return match.group(1).strip()

        return None

    async def _cleanup_old_deployments(self) -> None:
        """Remove old deployment records beyond max_history."""
        deployment_files = sorted(self.deployments_dir.glob("*.json"), reverse=True)

        if len(deployment_files) > self.max_history:
            for f in deployment_files[self.max_history :]:
                f.unlink()
                logger.debug("cleaned_up_deployment", file=f.name)

    async def get_history(self, limit: int = 10) -> list[Deployment]:
        """Get deployment history."""
        deployment_files = sorted(self.deployments_dir.glob("*.json"), reverse=True)

        deployments = []
        for f in deployment_files[:limit]:
            deployments.append(Deployment.from_dict(json.loads(f.read_text())))

        return deployments
