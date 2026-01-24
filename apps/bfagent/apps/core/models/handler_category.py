"""
Handler Category Model - Database over Enum

Purpose:
    Replaces hardcoded CATEGORY_CHOICES enum with database-backed categories.
    Allows adding new categories without code changes.

Benefits:
    - Dynamic categories (add via admin, not code)
    - Integer FK instead of string comparison
    - Proper foreign key constraints
    - Audit trail for category changes

PostgreSQL Migration Ready:
    - Integer PK (optimal for Postgres)
    - Proper indexing
    - Can be converted to Postgres ENUM if needed
    - Check constraints for business rules
"""

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


class HandlerCategory(models.Model):
    """
    Handler category - Database-backed instead of enum

    Old (BAD):
        CATEGORY_CHOICES = [
            ('input', 'Input Handler'),
            ('processing', 'Processing Handler'),
            ('output', 'Output Handler'),
        ]

    New (GOOD):
        category = ForeignKey('HandlerCategory')

    Allows:
        - Adding new categories without code deploy
        - Category metadata (description, config)
        - Audit trail (created_at, updated_at)
        - Soft delete (is_active flag)
    """

    # === PRIMARY KEY ===
    id = models.BigAutoField(primary_key=True, verbose_name=_("ID"))

    # === IDENTITY ===
    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name=_("Code"),
        help_text=_('Unique code (e.g., "input", "processing", "output")'),
    )

    name = models.CharField(
        max_length=200,
        verbose_name=_("Name"),
        help_text=_('Human-readable name (e.g., "Input Handler")'),
    )

    # === METADATA ===
    description = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Description"),
        help_text=_("Detailed description of this category"),
    )

    # Display settings
    icon = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name=_("Icon"),
        help_text=_('Icon class (e.g., "bi-arrow-down-circle" for input)'),
    )

    color = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name=_("Color"),
        help_text=_('Display color (e.g., "primary", "success", "info")'),
    )

    # Sort order
    display_order = models.IntegerField(
        default=0,
        db_index=True,
        verbose_name=_("Display Order"),
        help_text=_("Order for display in UI (lower = first)"),
    )

    # === CONFIGURATION ===
    # JSONField for category-specific config
    config = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Configuration"),
        help_text=_("Category-specific configuration options"),
    )

    # === STATUS ===
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_("Is Active"),
        help_text=_("Whether this category is currently active"),
    )

    is_system = models.BooleanField(
        default=False,
        verbose_name=_("Is System Category"),
        help_text=_("System categories cannot be deleted"),
    )

    # === AUDIT ===
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        db_table = "handler_categories"
        verbose_name = _("Handler Category")
        verbose_name_plural = _("Handler Categories")

        # Indexes
        indexes = [
            models.Index(fields=["is_active", "display_order"], name="hndlcat_active_order_idx"),
        ]

        # Ordering
        ordering = ["display_order", "name"]

        # Permissions
        permissions = [
            ("manage_system_categories", "Can manage system categories"),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        """
        Model validation

        Ensures:
            - code is lowercase and alphanumeric
            - system categories cannot be deactivated
        """
        super().clean()

        # Validate code format
        if self.code:
            if not self.code.replace("_", "").isalnum():
                raise ValidationError(
                    {"code": _("Code must be alphanumeric (underscores allowed)")}
                )

            # Normalize code to lowercase
            self.code = self.code.lower()

        # Prevent deactivating system categories
        if self.is_system and not self.is_active:
            raise ValidationError({"is_active": _("System categories cannot be deactivated")})

    def save(self, *args, **kwargs):
        """Override save to run validation"""
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        Override delete to prevent deletion of system categories
        """
        if self.is_system:
            raise ValidationError(
                _("System categories cannot be deleted. Set is_active=False instead.")
            )
        super().delete(*args, **kwargs)

    @property
    def handler_count(self):
        """Count of handlers in this category"""
        return self.handlers.filter(is_active=True).count()

    @classmethod
    def get_default_categories(cls):
        """
        Returns default handler categories for initial data

        Returns:
            list: List of category data dicts
        """
        return [
            {
                "code": "input",
                "name": "Input Handler",
                "description": "Handlers that load and prepare input data",
                "icon": "bi-arrow-down-circle",
                "color": "primary",
                "display_order": 1,
                "is_system": True,
            },
            {
                "code": "processing",
                "name": "Processing Handler",
                "description": "Handlers that process and transform data",
                "icon": "bi-gear-fill",
                "color": "info",
                "display_order": 2,
                "is_system": True,
            },
            {
                "code": "output",
                "name": "Output Handler",
                "description": "Handlers that save and export results",
                "icon": "bi-arrow-up-circle",
                "color": "success",
                "display_order": 3,
                "is_system": True,
            },
        ]


# PostgreSQL-specific optimizations (future):
#
# When migrating to Postgres, we can add:
#
# 1. Convert to Postgres ENUM type (optional):
#    CREATE TYPE handler_category_type AS ENUM ('input', 'processing', 'output');
#    ALTER TABLE handlers ADD COLUMN category_type handler_category_type;
#
# 2. Check constraint for code format:
#    ALTER TABLE handler_categories
#    ADD CONSTRAINT code_format
#    CHECK (code ~ '^[a-z0-9_]+$');
#
# 3. Partial index for active categories:
#    CREATE INDEX handler_categories_active_idx
#    ON handler_categories (display_order)
#    WHERE is_active = true;
#
# 4. Trigger to prevent system category deletion:
#    CREATE OR REPLACE FUNCTION prevent_system_category_delete()
#    RETURNS TRIGGER AS $$
#    BEGIN
#        IF OLD.is_system THEN
#            RAISE EXCEPTION 'Cannot delete system category';
#        END IF;
#        RETURN OLD;
#    END;
#    $$ LANGUAGE plpgsql;
