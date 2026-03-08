"""
orchestrator_mcp/models/qa_log.py

QALog Django model per ADR-108.
Stores detailed quality evaluation results for each agent task.
"""
from __future__ import annotations

import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class QALog(models.Model):
    """
    Audit record for a completed agent task quality evaluation.

    Platform-standards (ADR-109/platform-context):
      - BigAutoField PK
      - public_id UUIDField
      - tenant_id BigIntegerField (0 = platform-internal)
      - deleted_at soft-delete
    """

    # Platform-standard PKs
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name=_("Public ID"),
    )
    tenant_id = models.BigIntegerField(
        default=0,
        db_index=True,
        verbose_name=_("Tenant ID"),
    )

    # Task identity
    task_id = models.CharField(max_length=200, db_index=True, verbose_name=_("Task ID"))
    task_type = models.CharField(max_length=50, blank=True, verbose_name=_("Task Type"))
    repo = models.CharField(max_length=100, blank=True, verbose_name=_("Repo"))
    branch = models.CharField(max_length=200, blank=True, verbose_name=_("Branch"))
    agent_role = models.CharField(max_length=50, blank=True, verbose_name=_("Agent Role"))
    complexity = models.CharField(max_length=20, default="moderate", verbose_name=_("Complexity"))

    # Quality scores
    composite_score = models.FloatField(default=0.0, verbose_name=_("Composite Score"))
    completion_score = models.FloatField(default=0.0, verbose_name=_("Completion Score"))
    guardian_score = models.FloatField(default=0.0, verbose_name=_("Guardian Score"))
    adr_compliance_score = models.FloatField(default=0.0, verbose_name=_("ADR Compliance Score"))
    iteration_score = models.FloatField(default=1.0, verbose_name=_("Iteration Score"))
    token_score = models.FloatField(default=1.0, verbose_name=_("Token Score"))

    # Rollback decision
    rollback_level = models.CharField(
        max_length=20,
        default="none",
        db_index=True,
        verbose_name=_("Rollback Level"),
    )

    # Completion details
    is_complete = models.BooleanField(default=False, verbose_name=_("Is Complete"))
    blocking_open = models.JSONField(default=list, verbose_name=_("Blocking Open Criteria"))

    # Token usage
    iterations_used = models.IntegerField(default=0, verbose_name=_("Iterations Used"))
    tokens_used = models.IntegerField(default=0, verbose_name=_("Tokens Used"))
    token_budget = models.IntegerField(default=60000, verbose_name=_("Token Budget"))

    # Soft-delete
    deleted_at = models.DateTimeField(
        null=True, blank=True, db_index=True, verbose_name=_("Deleted At")
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        app_label = "orchestrator_mcp"
        verbose_name = _("QA Log")
        verbose_name_plural = _("QA Logs")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["task_id"], name="qalog_task_id_idx"),
            models.Index(fields=["rollback_level"], name="qalog_rollback_idx"),
            models.Index(fields=["created_at"], name="qalog_created_idx"),
        ]

    def __str__(self) -> str:
        return f"QALog({self.task_id} score={self.composite_score:.2f} rollback={self.rollback_level})"
