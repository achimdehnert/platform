"""
Handler System Models - Backwards Compatibility

MIGRATION STATUS:
    ✅ Handler → Moved to core.models.Handler
    ⏳ ActionHandler → Still here (TODO: Move to core in Phase 2c)
    ⏳ HandlerExecution → Still here (TODO: Move to core in Phase 2c)

Usage:
    # Preferred (new):
    from apps.core.models import Handler

    # Backwards compatible (old):
    from apps.bfagent.models_handlers import Handler  # This still works!
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

# Import Handler from core for backwards compatibility
from apps.core.models import Handler  # noqa: F401

User = get_user_model()


# ============================================================================
# ACTION HANDLER - M2M Through Table
# ============================================================================


class ActionHandler(models.Model):
    """
    M2M Through Table: Which handlers are used in which action

    TODO: Move to core.models in Phase 2c
    """

    PHASE_CHOICES = [
        ("input", "Input Phase"),
        ("processing", "Processing Phase"),
        ("output", "Output Phase"),
    ]

    ERROR_STRATEGY_CHOICES = [
        ("stop", "Stop Execution"),
        ("skip", "Skip Handler & Continue"),
        ("retry", "Retry Handler"),
        ("fallback", "Use Fallback Handler"),
    ]

    # === RELATIONS ===
    action = models.ForeignKey(
        "AgentAction", on_delete=models.CASCADE, related_name="action_handlers"
    )
    handler = models.ForeignKey(
        "core.Handler",  # Now points to core!
        on_delete=models.PROTECT,
        related_name="used_in_actions",
    )

    # === EXECUTION ORDER ===
    order = models.IntegerField(
        default=0, help_text="Execution order within phase (0, 10, 20, ...)"
    )
    phase = models.CharField(
        max_length=20,
        choices=PHASE_CHOICES,
        help_text="Execution phase: input, processing, or output",
    )

    # === CONFIGURATION ===
    config = models.JSONField(default=dict, blank=True, help_text="Handler-specific configuration")

    # === CONDITIONAL EXECUTION ===
    is_optional = models.BooleanField(default=False, help_text="Can this handler be skipped?")
    condition = models.JSONField(null=True, blank=True, help_text="Condition for running")

    # === ERROR HANDLING ===
    on_error = models.CharField(
        max_length=20,
        default="stop",
        choices=ERROR_STRATEGY_CHOICES,
        help_text="What to do if this handler fails",
    )
    fallback_handler = models.ForeignKey(
        "core.Handler",  # Now points to core!
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="fallback_for",
        help_text="Handler to use if this one fails",
    )
    retry_count = models.IntegerField(default=3, help_text="Number of retries if on_error='retry'")
    retry_delay_ms = models.IntegerField(
        default=1000, help_text="Delay between retries in milliseconds"
    )

    # === METADATA ===
    description_override = models.TextField(blank=True, help_text="Override handler description")
    is_active = models.BooleanField(
        default=True, help_text="Is this handler active in this action?"
    )

    # === A/B TESTING ===
    variant = models.CharField(
        max_length=20, blank=True, default="", help_text="A/B test variant identifier"
    )
    traffic_weight = models.IntegerField(
        default=100, help_text="Traffic weight for variant selection"
    )

    # === TIMESTAMPS ===
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "bfagent"
        db_table = "action_handlers"
        ordering = ["action", "phase", "order"]
        unique_together = [["action", "handler", "phase", "variant"]]
        verbose_name = "Action Handler"
        verbose_name_plural = "Action Handlers"
        indexes = [
            models.Index(fields=["action", "phase", "order"]),
            models.Index(fields=["handler"]),
        ]

    def __str__(self):
        variant_str = f" [{self.variant}]" if self.variant else ""
        return (
            f"{self.action.display_name} → {self.handler.name} (order: {self.order}){variant_str}"
        )

    def clean(self):
        """Validate configuration and relationships"""
        super().clean()

        # Validate config against handler schema
        if self.handler_id:
            try:
                self.handler.validate_config(self.config)
            except ValidationError as e:
                raise ValidationError({"config": str(e)})

        # Validate fallback_handler is set if on_error is 'fallback'
        if self.on_error == "fallback" and not self.fallback_handler:
            raise ValidationError(
                {"fallback_handler": 'Fallback handler must be set when on_error is "fallback"'}
            )

        # Validate fallback_handler has same category
        if self.fallback_handler and self.fallback_handler.category != self.handler.category:
            raise ValidationError(
                {
                    "fallback_handler": f"Fallback handler must be same category as primary handler ({self.handler.category})"
                }
            )

    def should_execute(self, context: dict) -> bool:
        """Check if handler should execute based on condition"""
        if not self.condition:
            return True

        field = self.condition.get("field")
        operator = self.condition.get("operator", "==")
        expected_value = self.condition.get("value")

        if field not in context:
            return False

        actual_value = context[field]

        # Simple operator evaluation
        operators = {
            "==": lambda a, e: a == e,
            "!=": lambda a, e: a != e,
            "in": lambda a, e: a in e,
            "not_in": lambda a, e: a not in e,
            ">": lambda a, e: a > e,
            "<": lambda a, e: a < e,
        }

        return operators.get(operator, lambda a, e: True)(actual_value, expected_value)


# ============================================================================
# HANDLER EXECUTION - Tracking
# ============================================================================


class HandlerExecution(models.Model):
    """
    Track individual handler executions

    TODO: Move to core.models in Phase 2c
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("skipped", "Skipped"),
        ("retrying", "Retrying"),
    ]

    # === RELATIONS ===
    action_handler = models.ForeignKey(
        ActionHandler, on_delete=models.CASCADE, related_name="executions"
    )
    project = models.ForeignKey(
        "BookProjects", on_delete=models.CASCADE, related_name="handler_executions"
    )

    # === EXECUTION DETAILS ===
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending", db_index=True
    )

    # === I/O DATA ===
    input_data = models.JSONField(default=dict, help_text="Input context passed to handler")
    output_data = models.JSONField(
        null=True, blank=True, help_text="Output data returned by handler"
    )

    # === ERROR TRACKING ===
    error_message = models.TextField(
        null=True, blank=True, help_text="Error message if execution failed"
    )
    error_traceback = models.TextField(
        null=True, blank=True, help_text="Full error traceback for debugging"
    )
    retry_attempt = models.IntegerField(default=0, help_text="Current retry attempt number")

    # === PERFORMANCE ===
    execution_time_ms = models.IntegerField(
        null=True, blank=True, help_text="Execution time in milliseconds"
    )

    # === COST TRACKING ===
    tokens_used = models.IntegerField(default=0, help_text="Total tokens consumed")
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=Decimal("0.0000"),
        help_text="Execution cost in USD",
    )
    llm_used = models.ForeignKey(
        "Llms",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="handler_executions",
        help_text="LLM used (if applicable)",
    )

    # === METADATA ===
    executed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="executed_handlers"
    )
    execution_context = models.JSONField(
        default=dict, blank=True, help_text="Additional execution context"
    )

    class Meta:
        app_label = "bfagent"
        db_table = "handler_executions"
        ordering = ["-started_at"]
        verbose_name = "Handler Execution"
        verbose_name_plural = "Handler Executions"
        indexes = [
            models.Index(fields=["action_handler", "-started_at"]),
            models.Index(fields=["status", "-started_at"]),
            models.Index(fields=["project", "-started_at"]),
        ]

    def __str__(self):
        duration = f" ({self.duration}ms)" if self.duration else ""
        return f"{self.action_handler.handler.name} - {self.status}{duration}"

    @property
    def duration(self):
        """Calculate execution duration"""
        if self.execution_time_ms:
            return self.execution_time_ms
        if self.completed_at and self.started_at:
            delta = self.completed_at - self.started_at
            return int(delta.total_seconds() * 1000)
        return None

    def mark_success(self, output_data: dict):
        """Mark execution as successful"""
        self.status = "success"
        self.completed_at = timezone.now()
        self.output_data = output_data
        self.execution_time_ms = self.duration
        self.save()

        # Update handler metrics
        self.action_handler.handler.update_metrics(
            execution_time_ms=self.execution_time_ms, success=True
        )

    def mark_failed(self, error_message: str, error_traceback: str = None):
        """Mark execution as failed"""
        self.status = "failed"
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.error_traceback = error_traceback
        self.execution_time_ms = self.duration
        self.save()

        # Update handler metrics
        if self.execution_time_ms:
            self.action_handler.handler.update_metrics(
                execution_time_ms=self.execution_time_ms, success=False
            )

    def mark_skipped(self, reason: str):
        """Mark execution as skipped"""
        self.status = "skipped"
        self.completed_at = timezone.now()
        self.error_message = f"Skipped: {reason}"
        self.save()
