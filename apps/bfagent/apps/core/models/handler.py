"""
Handler System Models - Normalized & Core

Moved from apps.bfagent to apps.core for centralization.

Key Normalizations:
    ✅ Integer PK instead of string-based handler_id
    ✅ FK to HandlerCategory instead of CharField CHOICES
    ✅ Proper indexing for PostgreSQL
    ✅ Backwards compatibility via 'code' field

Migration Path:
    Old: apps.bfagent.models_handlers.Handler
    New: apps.core.models.Handler
"""

from decimal import Decimal

import jsonschema
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class Handler(models.Model):
    """
    Handler Definition - Registered handlers in DB

    Replaces HandlerRegistry with DB-backed system.
    Normalized version with Integer PKs and FK to HandlerCategory.

    Features:
    - Type-safe relations instead of string-based references
    - Version management and deprecation support
    - Dependency tracking
    - Performance metrics
    - Configuration validation via JSON Schema
    """

    # === PRIMARY KEY ===
    # Integer PK for optimal performance
    id = models.BigAutoField(primary_key=True, verbose_name=_("ID"))

    # === IDENTITY ===
    # Code replaces handler_id as the unique identifier
    code = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name=_("Code"),
        help_text=_("Unique identifier (e.g., 'project_fields')"),
    )

    # Backwards compatibility: Keep handler_id as alias to code
    # TODO: Remove in future when all code uses 'code' field
    @property
    def handler_id(self):
        """Backwards compatibility property"""
        return self.code

    name = models.CharField(
        max_length=200,
        verbose_name=_("Name"),
        help_text=_("Human-readable name (e.g., 'Project Fields Loader')"),
    )

    # Legacy field name support
    @property
    def display_name(self):
        """Backwards compatibility property"""
        return self.name

    description = models.TextField(
        blank=True, default="", verbose_name=_("Description"), help_text=_("What this handler does")
    )

    # === CATEGORY ===
    # TODO: Normalize to FK in Phase 2b
    # For now, keep as CharField for backwards compatibility
    CATEGORY_CHOICES = [
        ("input", "Input Handler"),
        ("processing", "Processing Handler"),
        ("output", "Output Handler"),
    ]

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        db_index=True,
        verbose_name=_("Category"),
        help_text=_("Handler type: input, processing, or output"),
    )

    # === CODE REFERENCE ===
    module_path = models.CharField(
        max_length=255,
        verbose_name=_("Module Path"),
        help_text=_("Python module path (e.g., 'apps.bfagent.services.handlers.input_handlers')"),
    )

    class_name = models.CharField(
        max_length=100,
        verbose_name=_("Class Name"),
        help_text=_("Handler class name (e.g., 'ProjectFieldsHandler')"),
    )

    # === CONFIGURATION SCHEMA ===
    config_schema = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Config Schema"),
        help_text=_("JSON Schema for validating handler configuration"),
    )

    input_schema = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Input Schema"),
        help_text=_("JSON Schema describing expected input structure"),
    )

    output_schema = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Output Schema"),
        help_text=_("JSON Schema describing output structure"),
    )

    # === DEPENDENCIES ===
    required_handlers = models.ManyToManyField(
        "self",
        symmetrical=False,
        related_name="dependent_handlers",
        blank=True,
        verbose_name=_("Required Handlers"),
        help_text=_("Handlers that must run before this one"),
    )

    # === VERSIONING ===
    version = models.CharField(
        max_length=20,
        default="1.0.0",
        verbose_name=_("Version"),
        help_text=_("Semantic version (e.g., '1.2.3')"),
    )

    is_deprecated = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=_("Is Deprecated"),
        help_text=_("Is this handler deprecated?"),
    )

    deprecation_reason = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Deprecation Reason"),
        help_text=_("Why this handler is deprecated"),
    )

    replacement_handler = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="replaces",
        verbose_name=_("Replacement Handler"),
        help_text=_("Recommended replacement if deprecated"),
    )

    # === PERFORMANCE & QUALITY ===
    avg_execution_time_ms = models.IntegerField(
        default=0,
        verbose_name=_("Avg Execution Time (ms)"),
        help_text=_("Average execution time in milliseconds"),
    )

    success_rate = models.FloatField(
        default=100.0,
        verbose_name=_("Success Rate"),
        help_text=_("Success rate percentage (0-100)"),
    )

    total_executions = models.IntegerField(
        default=0,
        db_index=True,
        verbose_name=_("Total Executions"),
        help_text=_("Total number of executions"),
    )

    # === STATUS ===
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_("Is Active"),
        help_text=_("Is this handler available for use?"),
    )

    requires_llm = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=_("Requires LLM"),
        help_text=_("Does this handler require LLM API calls?"),
    )

    is_experimental = models.BooleanField(
        default=False,
        verbose_name=_("Is Experimental"),
        help_text=_("Is this handler in experimental/beta phase?"),
    )

    # === METADATA ===
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_handlers",
        verbose_name=_("Created By"),
    )

    # === DOCUMENTATION ===
    documentation_url = models.URLField(
        blank=True,
        default="",
        verbose_name=_("Documentation URL"),
        help_text=_("Link to detailed documentation"),
    )

    example_config = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Example Config"),
        help_text=_("Example configuration for documentation"),
    )

    class Meta:
        app_label = "core"
        db_table = "handlers"
        verbose_name = _("Handler")
        verbose_name_plural = _("Handlers")

        # Indexes optimized for PostgreSQL
        indexes = [
            # Common queries
            models.Index(fields=["category", "is_active"], name="hdlr_cat_active_idx"),
            models.Index(fields=["code"], name="hdlr_code_idx"),
            models.Index(fields=["-total_executions"], name="hdlr_executions_idx"),
            models.Index(fields=["is_active", "is_deprecated"], name="hdlr_status_idx"),
            models.Index(fields=["requires_llm", "is_active"], name="hdlr_llm_active_idx"),
        ]

        # Ordering
        ordering = ["category", "code"]

    def __str__(self):
        status = " (deprecated)" if self.is_deprecated else ""
        return f"{self.name} ({self.code}){status}"

    def get_implementation(self):
        """
        Dynamically load and return handler class

        Returns:
            Handler class (not instance)

        Raises:
            ImportError: If handler class cannot be loaded
        """
        from importlib import import_module

        try:
            module = import_module(self.module_path)
            return getattr(module, self.class_name)
        except (ImportError, AttributeError) as e:
            raise ImportError(
                f"Could not load handler {self.code}: "
                f"module={self.module_path}, class={self.class_name}. "
                f"Error: {e}"
            )

    def validate_config(self, config: dict) -> bool:
        """
        Validate configuration against config_schema

        Args:
            config: Configuration dictionary to validate

        Returns:
            True if valid

        Raises:
            ValidationError: If configuration is invalid
        """
        if not self.config_schema:
            return True

        try:
            jsonschema.validate(instance=config, schema=self.config_schema)
            return True
        except jsonschema.ValidationError as e:
            raise ValidationError(f"Invalid configuration for handler {self.code}: {e.message}")

    def update_metrics(self, execution_time_ms: int, success: bool):
        """
        Update performance metrics based on execution

        Args:
            execution_time_ms: Execution time in milliseconds
            success: Whether execution was successful
        """
        # Update average execution time
        total_time = self.avg_execution_time_ms * self.total_executions
        self.total_executions += 1
        self.avg_execution_time_ms = int((total_time + execution_time_ms) / self.total_executions)

        # Update success rate
        if success:
            successes = int(self.success_rate * (self.total_executions - 1) / 100)
            self.success_rate = ((successes + 1) / self.total_executions) * 100
        else:
            successes = int(self.success_rate * (self.total_executions - 1) / 100)
            self.success_rate = (successes / self.total_executions) * 100

        self.save(
            update_fields=[
                "avg_execution_time_ms",
                "success_rate",
                "total_executions",
                "updated_at",
            ]
        )


# PostgreSQL-specific optimizations (future):
#
# 1. Partial indexes for active handlers:
#    CREATE INDEX handlers_active_idx
#    ON handlers (category_id, code)
#    WHERE is_active = true AND is_deprecated = false;
#
# 2. GIN index for JSON schemas (if needed):
#    CREATE INDEX handlers_config_schema_gin
#    ON handlers USING gin(config_schema);
#
# 3. Full-text search on name + description:
#    CREATE INDEX handlers_search_idx
#    ON handlers USING gin(to_tsvector('english', name || ' ' || description));
