"""
Handler System - Lookup Tables
================================

DB-driven Lookups für Handler System statt hardcoded choices.

Created: 2024-12-06
Purpose: Phase 2 - Handler System Refactoring
"""

from django.db import models

# DEPRECATED: HandlerCategory moved to core.models
# For backwards compatibility, import from core
from apps.core.models import HandlerCategory  # noqa: F401


class HandlerPhase(models.Model):
    """
    Handler Phase Lookup (input, processing, output)

    Ersetzt hardcoded PHASE_CHOICES in ActionHandler Model
    """

    code = models.CharField(
        max_length=20, unique=True, help_text="Phase code (input, processing, output)"
    )
    name = models.CharField(max_length=100, help_text="Display name")
    description = models.TextField(blank=True, help_text="Phase description")

    # Execution order
    execution_order = models.IntegerField(
        default=0, help_text="Order of execution (lower = earlier)"
    )

    # Visual
    color = models.CharField(max_length=20, default="info", help_text="Bootstrap color class")
    icon = models.CharField(
        max_length=50, default="bi-arrow-right", help_text="Bootstrap icon class"
    )

    # Standard fields
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "writing_hub"
        db_table = "handler_phases"
        ordering = ["execution_order", "sort_order"]
        verbose_name = "Handler Phase"
        verbose_name_plural = "Handler Phases"

    def __str__(self):
        return self.name


class ErrorStrategy(models.Model):
    """
    Error Strategy Lookup (stop, skip, retry, fallback)

    Ersetzt hardcoded ERROR_STRATEGY_CHOICES in ActionHandler Model
    """

    code = models.CharField(
        max_length=20, unique=True, help_text="Strategy code (stop, skip, retry, fallback)"
    )
    name = models.CharField(max_length=100, help_text="Display name")
    description = models.TextField(blank=True, help_text="Strategy description")

    # Behavior
    stops_execution = models.BooleanField(
        default=False, help_text="Does this strategy stop the workflow?"
    )
    allows_retry = models.BooleanField(default=False, help_text="Does this strategy allow retries?")
    max_retries = models.IntegerField(default=0, help_text="Maximum retry attempts (0 = unlimited)")

    # Visual
    color = models.CharField(max_length=20, default="warning", help_text="Bootstrap color class")
    icon = models.CharField(
        max_length=50, default="bi-exclamation-triangle", help_text="Bootstrap icon class"
    )

    # Standard fields
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "writing_hub"
        db_table = "error_strategies"
        ordering = ["sort_order"]
        verbose_name = "Error Strategy"
        verbose_name_plural = "Error Strategies"

    def __str__(self):
        return self.name
