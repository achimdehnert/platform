"""
URL Pattern Model - Normalized URL Storage

Purpose:
    Replaces hardcoded url_name strings throughout the application
    with proper FK references to a central URL registry.

Benefits:
    - Integer PKs instead of string comparisons
    - Centralized URL management
    - Foreign key constraints prevent orphaned references
    - Easy to rename/refactor URLs in one place

PostgreSQL Migration Ready:
    - Uses Integer PK (optimal for Postgres)
    - JSONField for future metadata (native in Postgres)
    - Proper indexing strategy
    - Composite UNIQUE constraint (efficient in Postgres)
"""

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


class URLPattern(models.Model):
    """
    Normalized URL pattern storage

    Replaces hardcoded url_name strings like 'expert_hub:customer_dashboard'
    with proper database records and integer foreign keys.

    Example:
        Old: NavigationItem.url_name = 'expert_hub:customer_dashboard'
        New: NavigationItem.url_pattern_id = 42
    """

    # === PRIMARY KEY ===
    # Integer PK for optimal performance in Postgres
    id = models.BigAutoField(primary_key=True, verbose_name=_("ID"))

    # === IDENTITY ===
    code = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name=_("Code"),
        help_text=_('Unique identifier code (e.g., "expert_hub:customer_dashboard")'),
    )

    # URL components (normalized)
    namespace = models.CharField(
        max_length=50,
        blank=True,
        default="",
        db_index=True,
        verbose_name=_("Namespace"),
        help_text=_('URL namespace (e.g., "expert_hub", "control_center")'),
    )

    pattern_name = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name=_("Pattern Name"),
        help_text=_('URL pattern name (e.g., "customer_dashboard", "dashboard")'),
    )

    # === METADATA ===
    app_label = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name=_("App Label"),
        help_text=_('Django app this URL belongs to (e.g., "expert_hub", "control_center")'),
    )

    description = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Description"),
        help_text=_("Human-readable description of what this URL does"),
    )

    # URL path (for reference/documentation)
    url_path = models.CharField(
        max_length=500,
        blank=True,
        default="",
        verbose_name=_("URL Path"),
        help_text=_('Example URL path (e.g., "/expert-hub/customers/")'),
    )

    # === CONFIGURATION ===
    # JSONField for future metadata (native in Postgres, polyfill in SQLite)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Metadata"),
        help_text=_("Additional configuration data"),
    )

    # === STATUS ===
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_("Is Active"),
        help_text=_("Whether this URL pattern is currently active"),
    )

    # === AUDIT ===
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        db_table = "url_patterns"
        verbose_name = _("URL Pattern")
        verbose_name_plural = _("URL Patterns")

        # Composite unique constraint (efficient in Postgres)
        unique_together = [("namespace", "pattern_name")]

        # Indexes for common queries
        indexes = [
            models.Index(fields=["app_label", "is_active"], name="urlpat_app_active_idx"),
            models.Index(fields=["namespace", "is_active"], name="urlpat_ns_active_idx"),
        ]

        # Ordering
        ordering = ["namespace", "pattern_name"]

    def __str__(self):
        return self.url_name

    @property
    def url_name(self):
        """
        Computed property that returns the full URL name

        Returns:
            str: Full URL name (e.g., 'expert_hub:customer_dashboard')
        """
        if self.namespace:
            return f"{self.namespace}:{self.pattern_name}"
        return self.pattern_name

    def clean(self):
        """
        Model validation

        Ensures:
            - code matches computed url_name
            - pattern_name is not empty
        """
        super().clean()

        # Validate pattern_name
        if not self.pattern_name or not self.pattern_name.strip():
            raise ValidationError({"pattern_name": _("Pattern name cannot be empty")})

        # Auto-generate code if not provided
        if not self.code:
            self.code = self.url_name

        # Validate code matches url_name
        if self.code != self.url_name:
            raise ValidationError(
                {"code": _(f"Code must match URL name. Expected: {self.url_name}")}
            )

    def save(self, *args, **kwargs):
        """Override save to run validation"""
        self.full_clean()
        super().save(*args, **kwargs)

    @classmethod
    def get_or_create_from_string(cls, url_name_string: str):
        """
        Helper method to get or create URLPattern from string

        Args:
            url_name_string: URL name string (e.g., 'expert_hub:customer_dashboard')

        Returns:
            tuple: (URLPattern instance, created boolean)
        """
        if ":" in url_name_string:
            namespace, pattern_name = url_name_string.split(":", 1)
        else:
            namespace, pattern_name = "", url_name_string

        return cls.objects.get_or_create(
            code=url_name_string,
            defaults={
                "namespace": namespace,
                "pattern_name": pattern_name,
                "app_label": namespace or "unknown",
            },
        )


# PostgreSQL-specific optimizations (future):
#
# When migrating to Postgres, we can add:
#
# 1. Full-text search index on description:
#    CREATE INDEX url_patterns_description_fts
#    ON url_patterns USING gin(to_tsvector('english', description));
#
# 2. Partial indexes for active patterns:
#    CREATE INDEX url_patterns_active_idx
#    ON url_patterns (namespace, pattern_name)
#    WHERE is_active = true;
#
# 3. Postgres ENUM type for common namespaces (if desired):
#    CREATE TYPE url_namespace AS ENUM ('expert_hub', 'control_center', ...);
#
# 4. Check constraints:
#    ALTER TABLE url_patterns
#    ADD CONSTRAINT pattern_name_not_empty
#    CHECK (pattern_name != '');
