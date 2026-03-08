"""
orchestrator_mcp/models/qa_log.py

QALog — AuditStore for Quality Evaluator per ADR-108.

Platform-standards:
  BigAutoField PK, public_id UUID, tenant_id BigIntegerField(db_index),
  soft_delete (deleted_at), UniqueConstraint, i18n via _()
"""

from __future__ import annotations

import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class QALog(models.Model):
    """
    One record per agent task quality evaluation.
    Upserted by task_id after task completion.
    """

    class RollbackLevel(models.IntegerChoices):
        NONE = 0, _("None")
        L1_RE_ENGINEER = 1, _("L1 Re-Engineer")
        L2_TECH_LEAD = 2, _("L2 Tech Lead")
        L3_USER_NOTIFY = 3, _("L3 User Notify")
        L4_ABORT = 4, _("L4 Abort")

    # --- Platform PKs ---
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(
        default=uuid.uuid4, unique=True, editable=False, verbose_name=_("Public ID")
    )

    # --- Multi-tenancy ---
    tenant_id = models.BigIntegerField(db_index=True, default=1, verbose_name=_("Tenant ID"))

    # --- Task Identity ---
    task_id = models.CharField(
        max_length=255, unique=True, db_index=True, verbose_name=_("Task ID")
    )
    task_type = models.CharField(max_length=50, verbose_name=_("Task Type"))
    agent_role = models.CharField(max_length=50, verbose_name=_("Agent Role"))
    model_tier = models.CharField(max_length=50, verbose_name=_("Model Tier"))
    repository = models.CharField(max_length=255, blank=True, default="", verbose_name=_("Repository"))

    # --- Quality Metrics ---
    completion_score = models.FloatField(default=0.0, verbose_name=_("Completion Score"))
    guardian_passed = models.BooleanField(default=False, verbose_name=_("Guardian Passed"))
    coverage_delta = models.FloatField(default=0.0, verbose_name=_("Coverage Delta"))
    adr_compliance = models.BooleanField(default=True, verbose_name=_("ADR Compliance"))
    iteration_count = models.PositiveSmallIntegerField(default=1, verbose_name=_("Iteration Count"))
    composite_score = models.FloatField(default=0.0, verbose_name=_("Composite Score"), db_index=True)
    rollback_level = models.PositiveSmallIntegerField(
        choices=RollbackLevel.choices, default=RollbackLevel.NONE, verbose_name=_("Rollback Level")
    )
    passed = models.BooleanField(default=False, db_index=True, verbose_name=_("Passed"))

    # --- Cost ---
    tokens_used = models.PositiveIntegerField(default=0, verbose_name=_("Tokens Used"))
    tokens_budget = models.PositiveIntegerField(default=0, verbose_name=_("Tokens Budget"))

    # --- Details ---
    details = models.JSONField(default=dict, verbose_name=_("Details"))

    # --- Timestamps ---
    evaluated_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Evaluated At"))
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name=_("Deleted At"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("QA Log")
        verbose_name_plural = _("QA Logs")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "passed"]),
            models.Index(fields=["agent_role", "composite_score"]),
            models.Index(fields=["repository", "-created_at"]),
        ]

    def __str__(self) -> str:
        status = "PASS" if self.passed else f"ROLLBACK-L{self.rollback_level}"
        return f"QA {self.task_id} [{status}] composite={self.composite_score:.2f}"
