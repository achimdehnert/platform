"""UI Hub models for guardrail rules and violations."""

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone


class GuardrailCategory(models.Model):
    """Category for organizing guardrail rules."""

    CATEGORY_CHOICES = [
        ("naming", "Naming Conventions"),
        ("separation", "Separation of Concerns"),
        ("htmx", "HTMX Patterns"),
        ("structure", "Project Structure"),
        ("custom", "Custom Rules"),
    ]

    code = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    description = models.TextField()
    display_order = models.IntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "ui_hub"
        db_table = "ui_hub_categories"
        verbose_name = "Guardrail Category"
        verbose_name_plural = "Guardrail Categories"
        ordering = ["display_order", "name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class GuardrailRule(models.Model):
    """Guardrail rule for code quality enforcement."""

    SEVERITY_CHOICES = [
        ("info", "Info"),
        ("warning", "Warning"),
        ("error", "Error"),
    ]

    category = models.ForeignKey(GuardrailCategory, on_delete=models.CASCADE, related_name="rules")
    name = models.CharField(max_length=200, db_index=True)
    description = models.TextField()
    pattern = models.CharField(max_length=500, help_text="Regex pattern to validate against")
    message = models.TextField(help_text="Error message when violated")
    suggestion = models.TextField(blank=True, help_text="Suggested fix for the violation")
    severity = models.CharField(
        max_length=20, choices=SEVERITY_CHOICES, default="warning", db_index=True
    )

    # Metadata
    is_builtin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "ui_hub"
        db_table = "ui_hub_rules"
        verbose_name = "Guardrail Rule"
        verbose_name_plural = "Guardrail Rules"
        ordering = ["category", "name"]
        indexes = [
            models.Index(fields=["category", "is_active"]),
            models.Index(fields=["severity", "is_active"]),
        ]

    def __str__(self):
        return f"{self.category.code}.{self.name}"


class RuleExample(models.Model):
    """Example code for a guardrail rule."""

    rule = models.ForeignKey(GuardrailRule, on_delete=models.CASCADE, related_name="examples")
    code = models.TextField(help_text="Example code")
    is_valid = models.BooleanField(
        help_text="True if this is a valid example, False if anti-pattern"
    )
    explanation = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "ui_hub"
        db_table = "ui_hub_rule_examples"
        verbose_name = "Rule Example"
        verbose_name_plural = "Rule Examples"
        ordering = ["-is_valid", "id"]

    def __str__(self):
        status = "✅ Valid" if self.is_valid else "❌ Invalid"
        return f"{self.rule.name}: {status}"


class CodeTemplate(models.Model):
    """Code template for scaffolding."""

    TEMPLATE_TYPE_CHOICES = [
        ("view", "View Function"),
        ("template", "HTML Template"),
        ("partial", "HTMX Partial"),
        ("url", "URL Pattern"),
        ("service", "Service Function"),
        ("selector", "Selector Function"),
    ]

    name = models.CharField(max_length=200, unique=True, db_index=True)
    template_type = models.CharField(max_length=50, choices=TEMPLATE_TYPE_CHOICES, db_index=True)
    description = models.TextField()
    content = models.TextField(help_text="Jinja2 template content")

    # Template variables schema (JSON)
    variables_schema = models.JSONField(
        default=dict, help_text="JSON schema for required variables"
    )

    is_active = models.BooleanField(default=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "ui_hub"
        db_table = "ui_hub_templates"
        verbose_name = "Code Template"
        verbose_name_plural = "Code Templates"
        ordering = ["template_type", "name"]
        indexes = [
            models.Index(fields=["template_type", "is_active"]),
        ]

    def __str__(self):
        return f"{self.get_template_type_display()}: {self.name}"


class HTMXPattern(models.Model):
    """HTMX pattern template (inline edit, delete, search, etc.)."""

    PATTERN_TYPE_CHOICES = [
        ("inline_edit", "Inline Edit"),
        ("delete_row", "Delete Row"),
        ("search_filter", "Search/Filter"),
        ("modal_form", "Modal Form"),
        ("pagination", "Pagination"),
        ("infinite_scroll", "Infinite Scroll"),
        ("lazy_load", "Lazy Load"),
    ]

    name = models.CharField(max_length=200, unique=True, db_index=True)
    pattern_type = models.CharField(max_length=50, choices=PATTERN_TYPE_CHOICES, db_index=True)
    description = models.TextField()

    # Template content for different parts
    view_template = models.TextField(blank=True, help_text="Django view function template")
    html_template = models.TextField(blank=True, help_text="HTML template with HTMX attributes")
    partial_template = models.TextField(blank=True, help_text="HTMX partial template")

    # Optional JavaScript
    javascript = models.TextField(blank=True, help_text="Optional JavaScript code")

    is_active = models.BooleanField(default=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "ui_hub"
        db_table = "ui_hub_htmx_patterns"
        verbose_name = "HTMX Pattern"
        verbose_name_plural = "HTMX Patterns"
        ordering = ["pattern_type", "name"]

    def __str__(self):
        return f"{self.get_pattern_type_display()}: {self.name}"


class RuleViolation(models.Model):
    """Logged violation of a guardrail rule."""

    rule = models.ForeignKey(GuardrailRule, on_delete=models.CASCADE, related_name="violations")

    file_path = models.CharField(max_length=500, db_index=True)
    line_number = models.IntegerField(null=True, blank=True)
    code_snippet = models.TextField()
    message = models.TextField()

    # Context
    app_name = models.CharField(max_length=100, blank=True, db_index=True)
    severity = models.CharField(max_length=20, db_index=True)

    # Resolution
    is_resolved = models.BooleanField(default=False, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        app_label = "ui_hub"
        db_table = "ui_hub_violations"
        verbose_name = "Rule Violation"
        verbose_name_plural = "Rule Violations"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["file_path", "is_resolved"]),
            models.Index(fields=["severity", "is_resolved"]),
            models.Index(fields=["created_at", "is_resolved"]),
        ]

    def __str__(self):
        return f"{self.rule.name} @ {self.file_path}:{self.line_number}"

    def resolve(self, note=""):
        """Mark violation as resolved."""
        self.is_resolved = True
        self.resolved_at = timezone.now()
        self.resolution_note = note
        self.save()


class ValidationSession(models.Model):
    """Session for batch validation runs."""

    session_id = models.CharField(max_length=100, unique=True, db_index=True)

    # Scope
    target_path = models.CharField(max_length=500)
    app_name = models.CharField(max_length=100, blank=True, db_index=True)

    # Results
    total_files = models.IntegerField(default=0)
    violations_found = models.IntegerField(default=0)
    errors_count = models.IntegerField(default=0)
    warnings_count = models.IntegerField(default=0)
    info_count = models.IntegerField(default=0)

    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ("running", "Running"),
            ("completed", "Completed"),
            ("failed", "Failed"),
        ],
        default="running",
        db_index=True,
    )

    started_at = models.DateTimeField(auto_now_add=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Results summary
    summary = models.JSONField(default=dict)

    class Meta:
        app_label = "ui_hub"
        db_table = "ui_hub_validation_sessions"
        verbose_name = "Validation Session"
        verbose_name_plural = "Validation Sessions"
        ordering = ["-started_at"]

    def __str__(self):
        return f"Validation {self.session_id} - {self.status}"
