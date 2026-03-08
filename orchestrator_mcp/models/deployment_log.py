"""
orchestrator_mcp/models/deployment_log.py

AuditStore for Deployment Agent — per ADR-107 §4.3.

Fixes applied (see REVIEW-ADR-107):
  L-2: _ACTIVE_STATUSES constant — UniqueConstraint synced with Status enum

Platform-standards:
  BigAutoField PK, public_id UUIDField, tenant_id BigIntegerField(db_index=True),
  soft_delete (deleted_at), UniqueConstraint (not unique_together), i18n via _()
"""

from __future__ import annotations

import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class DeploymentLog(models.Model):
    """
    Immutable audit record for every deployment attempt.
    One record per deployment lifecycle (PENDING -> DEPLOYED or ROLLED_BACK).
    """

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        PRE_CHECK = "pre_check", _("Pre-Check")
        MIGRATING = "migrating", _("Migrating")
        DEPLOYING = "deploying", _("Deploying")
        HEALTH_CHECKING = "health_checking", _("Health Checking")
        DEPLOYED = "deployed", _("Deployed")
        ROLLING_BACK = "rolling_back", _("Rolling Back")
        FAILED = "failed", _("Failed")
        ROLLED_BACK = "rolled_back", _("Rolled Back")

    class Trigger(models.TextChoices):
        GIT_PUSH_MAIN = "git_push_main", _("Git Push to main")
        MANUAL = "manual", _("Manual Trigger")
        ROLLBACK = "rollback", _("Rollback Trigger")

    # Fix L-2: Status list as constant — stays in sync with Status enum
    _ACTIVE_STATUSES = [
        Status.PENDING,
        Status.PRE_CHECK,
        Status.MIGRATING,
        Status.DEPLOYING,
        Status.HEALTH_CHECKING,
    ]

    # --- Platform-standard PKs ---
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name=_("Public ID"),
    )

    # --- Multi-tenancy ---
    tenant_id = models.BigIntegerField(
        db_index=True,
        verbose_name=_("Tenant ID"),
    )

    # --- Deployment Identity ---
    repository = models.CharField(
        max_length=255,
        verbose_name=_("Repository"),
        help_text=_("e.g. org/repo-name"),
    )
    service_name = models.CharField(
        max_length=100,
        verbose_name=_("Service Name"),
        help_text=_("Docker Compose service identifier"),
    )
    image_tag = models.CharField(
        max_length=255,
        verbose_name=_("Image Tag"),
        help_text=_("GHCR image tag deployed"),
    )
    previous_image_tag = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name=_("Previous Image Tag"),
        help_text=_("Tag before this deployment — used for rollback"),
    )

    # --- Git Context ---
    git_sha = models.CharField(max_length=40, verbose_name=_("Git SHA"))
    git_branch = models.CharField(
        max_length=255, default="main", verbose_name=_("Git Branch")
    )
    pr_number = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("PR Number"),
        help_text=_("GitHub PR that triggered this deployment"),
    )
    triggered_by = models.CharField(
        max_length=100,
        verbose_name=_("Triggered By"),
        help_text=_("GitHub Actions runner or manual user"),
    )

    # --- Deployment Lifecycle ---
    trigger = models.CharField(
        max_length=20,
        choices=Trigger.choices,
        default=Trigger.GIT_PUSH_MAIN,
        verbose_name=_("Trigger"),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("Status"),
        db_index=True,
    )
    started_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Started At"))
    completed_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Completed At")
    )

    # --- Migration Details ---
    had_pending_migrations = models.BooleanField(
        default=False, verbose_name=_("Had Pending Migrations")
    )
    had_breaking_migrations = models.BooleanField(
        default=False, verbose_name=_("Had Breaking Migrations")
    )
    migration_names = models.JSONField(
        default=list,
        verbose_name=_("Migration Names"),
        help_text=_("List of applied migration identifiers"),
    )

    # --- Health Check ---
    health_check_attempts = models.PositiveSmallIntegerField(
        default=0, verbose_name=_("Health Check Attempts")
    )
    health_check_passed = models.BooleanField(
        null=True, verbose_name=_("Health Check Passed")
    )

    # --- Gate Level ---
    gate_level = models.PositiveSmallIntegerField(
        default=2,
        verbose_name=_("Gate Level"),
        help_text=_("0=Auto, 1=Agent, 2=Human-Approval, 3=Tech-Lead"),
    )
    approved_by = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name=_("Approved By"),
        help_text=_("GitHub username who gave Gate-2 approval"),
    )

    # --- Outcome ---
    error_message = models.TextField(
        blank=True, default="", verbose_name=_("Error Message")
    )
    rollback_reason = models.TextField(
        blank=True, default="", verbose_name=_("Rollback Reason")
    )
    duration_seconds = models.PositiveIntegerField(
        null=True, blank=True, verbose_name=_("Duration (seconds)")
    )

    # --- Platform soft-delete ---
    deleted_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Deleted At"), db_index=True
    )

    # --- Timestamps ---
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name=_("Created At")
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Deployment Log")
        verbose_name_plural = _("Deployment Logs")
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["repository", "git_sha"]),
            models.Index(fields=["tenant_id", "-started_at"]),
        ]
        constraints = [
            # Fix L-2: use _ACTIVE_STATUSES constant
            models.UniqueConstraint(
                fields=["tenant_id", "service_name"],
                condition=models.Q(
                    status__in=[s.value for s in DeploymentLog._ACTIVE_STATUSES]
                ),
                name="unique_active_deployment_per_service",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Deployment {self.public_id} "
            f"[{self.service_name}@{self.image_tag[:12]}] — {self.status}"
        )

    @property
    def is_active(self) -> bool:
        return self.status in {
            self.Status.PENDING,
            self.Status.PRE_CHECK,
            self.Status.MIGRATING,
            self.Status.DEPLOYING,
            self.Status.HEALTH_CHECKING,
        }

    @property
    def is_terminal(self) -> bool:
        return self.status in {
            self.Status.DEPLOYED,
            self.Status.FAILED,
            self.Status.ROLLED_BACK,
        }
