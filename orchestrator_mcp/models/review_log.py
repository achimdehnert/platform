"""
orchestrator_mcp/models/review_log.py

AuditStore for Review Agent — Fix M-3 (override audit trail).

Platform-standards:
  BigAutoField PK, public_id UUIDField, tenant_id BigIntegerField(db_index=True),
  soft_delete (deleted_at), UniqueConstraint (not unique_together), i18n via _()
"""

from __future__ import annotations

import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class ReviewLog(models.Model):
    """
    Audit record for every Review Agent run.
    One record per PR review lifecycle. Override events are logged here.
    """

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        RUNNING = "running", _("Running")
        PASSED = "passed", _("Passed")
        FAILED = "failed", _("Failed")
        OVERRIDDEN = "overridden", _("Overridden")

    _ACTIVE_STATUSES = [
        Status.PENDING,
        Status.RUNNING,
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
        db_index=True, verbose_name=_("Tenant ID")
    )

    # --- PR Identity ---
    repository = models.CharField(
        max_length=255, verbose_name=_("Repository")
    )
    pr_number = models.PositiveIntegerField(verbose_name=_("PR Number"))
    pr_author = models.CharField(
        max_length=100, verbose_name=_("PR Author")
    )
    git_sha = models.CharField(max_length=40, verbose_name=_("Git SHA"))

    # --- Review State ---
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        verbose_name=_("Status"),
    )
    blocking_issues = models.JSONField(
        default=list, verbose_name=_("Blocking Issues")
    )
    warning_issues = models.JSONField(
        default=list, verbose_name=_("Warning Issues")
    )
    check_results = models.JSONField(
        default=dict, verbose_name=_("Check Results")
    )

    # --- Override Audit Trail (Fix M-3) ---
    override_by = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name=_("Override By"),
        help_text=_("GitHub username who invoked /override-review"),
    )
    override_reason = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Override Reason"),
    )
    override_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Override At"),
    )

    # --- Timestamps ---
    started_at = models.DateTimeField(
        auto_now_add=True, verbose_name=_("Started At")
    )
    completed_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Completed At")
    )
    deleted_at = models.DateTimeField(
        null=True, blank=True, db_index=True, verbose_name=_("Deleted At")
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name=_("Created At")
    )
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name=_("Updated At")
    )

    class Meta:
        verbose_name = _("Review Log")
        verbose_name_plural = _("Review Logs")
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["repository", "pr_number"]),
            models.Index(fields=["tenant_id", "-started_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "repository", "pr_number"],
                condition=models.Q(
                    status__in=["pending", "in_review"]
                ),
                name="unique_active_review_per_pr",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Review {self.public_id} "
            f"[PR#{self.pr_number} in {self.repository}] — {self.status}"
        )

    @property
    def is_overridden(self) -> bool:
        return self.status == self.Status.OVERRIDDEN

    @property
    def is_active(self) -> bool:
        return self.status in {self.Status.PENDING, self.Status.RUNNING}
