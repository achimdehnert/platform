"""
orchestrator_mcp/models/cost_log.py

CostLog Django model per ADR-108.
Tracks token usage and budget per agent task.
"""
from __future__ import annotations

import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class CostLog(models.Model):
    """
    Token usage audit record for cost dashboards and budget enforcement.

    Platform-standards (ADR-109/platform-context):
      - BigAutoField PK
      - public_id UUIDField
      - tenant_id BigIntegerField (0 = platform-internal)
    """

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
    model = models.CharField(max_length=100, blank=True, verbose_name=_("Model"))
    complexity = models.CharField(max_length=20, default="moderate", verbose_name=_("Complexity"))
    agent_role = models.CharField(max_length=50, blank=True, verbose_name=_("Agent Role"))

    # Budget tracking
    tokens_used = models.IntegerField(default=0, verbose_name=_("Tokens Used"))
    token_budget = models.IntegerField(default=60000, verbose_name=_("Token Budget"))
    over_budget = models.BooleanField(default=False, db_index=True, verbose_name=_("Over Budget"))
    utilization = models.FloatField(
        default=0.0,
        verbose_name=_("Utilization"),
        help_text=_("tokens_used / token_budget"),
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        app_label = "orchestrator_mcp"
        verbose_name = _("Cost Log")
        verbose_name_plural = _("Cost Logs")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["task_id"], name="costlog_task_id_idx"),
            models.Index(fields=["over_budget"], name="costlog_overbudget_idx"),
            models.Index(fields=["created_at"], name="costlog_created_idx"),
        ]

    def __str__(self) -> str:
        return f"CostLog({self.task_id} used={self.tokens_used} budget={self.token_budget} over={self.over_budget})"
