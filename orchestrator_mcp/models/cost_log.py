"""
orchestrator_mcp/models/cost_log.py

CostLog — Token-Budget Tracking per ADR-108 §3.4.

Platform-standards:
  BigAutoField PK, public_id UUID, tenant_id BigIntegerField(db_index),
  soft_delete (deleted_at), i18n via _()
"""

from __future__ import annotations

import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class CostLog(models.Model):
    """
    One record per agent task token usage.
    Used for cost dashboards and budget enforcement.
    """

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

    # --- Token Usage ---
    tokens_used = models.PositiveIntegerField(default=0, verbose_name=_("Tokens Used"))
    tokens_budget = models.PositiveIntegerField(default=0, verbose_name=_("Tokens Budget"))
    overrun = models.BooleanField(default=False, db_index=True, verbose_name=_("Budget Overrun"))

    # --- Timestamps ---
    logged_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Logged At"))
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name=_("Deleted At"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Cost Log")
        verbose_name_plural = _("Cost Logs")
        ordering = ["-logged_at"]
        indexes = [
            models.Index(fields=["tenant_id", "overrun"]),
            models.Index(fields=["agent_role", "-logged_at"]),
            models.Index(fields=["repository", "-logged_at"]),
            models.Index(fields=["model_tier", "-logged_at"]),
        ]

    def __str__(self) -> str:
        overrun_flag = " [OVERRUN]" if self.overrun else ""
        return (
            f"Cost {self.task_id} {self.tokens_used}/{self.tokens_budget} "
            f"({self.model_tier}){overrun_flag}"
        )

    @property
    def utilization_pct(self) -> float | None:
        if not self.tokens_budget:
            return None
        return round(self.tokens_used / self.tokens_budget * 100, 1)
