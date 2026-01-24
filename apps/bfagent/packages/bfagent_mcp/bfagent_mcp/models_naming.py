"""
BF Agent MCP Server - Naming Convention System
================================================

DB-getriebene Naming Conventions für Tabellen und Klassen.

Jede Domain/App hat definierte Prefixes:
- table_prefix: für db_table (z.B. "mcp_")
- class_prefix: für Klassennamen (z.B. "MCP")

Dies ermöglicht:
- Sofortige Erkennung welche Tabelle zu welcher Domain gehört
- Konsistente Benennung über das gesamte Projekt
- Validierung neuer Models gegen Conventions
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

# Import base classes
try:
    from .models import AuditModel, SoftDeleteModel, Domain
except ImportError:
    # Fallback for standalone testing
    from django.db import models as dj_models
    
    class AuditModel(dj_models.Model):
        created_at = dj_models.DateTimeField(auto_now_add=True)
        updated_at = dj_models.DateTimeField(auto_now=True)
        class Meta:
            abstract = True
    
    class SoftDeleteModel(dj_models.Model):
        is_active = dj_models.BooleanField(default=True)
        class Meta:
            abstract = True
    
    Domain = None


# =============================================================================
# TABLE NAMING CONVENTION
# =============================================================================

class TableNamingConvention(AuditModel, SoftDeleteModel):
    """
    Naming Convention für Tabellen/Models pro Domain/App.
    
    DB-getrieben - MCP folgt seinen eigenen Regeln!
    
    Beispiel:
        app_label="bfagent_mcp", table_prefix="mcp_", class_prefix="MCP"
        → Tabelle: mcp_refactor_config
        → Klasse: MCPRefactorConfig
    """
    
    # Identification
    app_label = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_("App Label"),
        help_text=_("Django App Label: 'bfagent_mcp', 'books', 'core'")
    )
    
    # Optional: Link to Domain (if domain-specific)
    domain = models.OneToOneField(
        'bfagent_mcp.Domain',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='naming_convention',
        verbose_name=_("Domain"),
        help_text=_("Optional: Associated domain")
    )
    
    # Display
    display_name = models.CharField(
        max_length=100,
        verbose_name=_("Display Name"),
        help_text=_("Human readable: 'MCP Server', 'Book Writing'")
    )
    
    # Prefixes
    table_prefix = models.CharField(
        max_length=20,
        verbose_name=_("Table Prefix"),
        help_text=_("Prefix for db_table: 'mcp_', 'books_', 'core_'")
    )
    class_prefix = models.CharField(
        max_length=20,
        verbose_name=_("Class Prefix"),
        help_text=_("Prefix for class names: 'MCP', 'Books', 'Core'")
    )
    
    # Patterns (with placeholders)
    table_pattern = models.CharField(
        max_length=100,
        default="{prefix}{name}",
        verbose_name=_("Table Pattern"),
        help_text=_("Pattern for table names: {prefix}{name} → mcp_component_type")
    )
    class_pattern = models.CharField(
        max_length=100,
        default="{Prefix}{Name}",
        verbose_name=_("Class Pattern"),
        help_text=_("Pattern for class names: {Prefix}{Name} → MCPComponentType")
    )
    
    # File Patterns
    file_pattern = models.CharField(
        max_length=100,
        default="{prefix}_{name}.py",
        verbose_name=_("File Pattern"),
        help_text=_("Pattern for file names: {prefix}_{name}.py → mcp_models.py")
    )
    
    # Validation
    enforce_convention = models.BooleanField(
        default=True,
        verbose_name=_("Enforce Convention"),
        help_text=_("Raise error if new models don't follow convention")
    )
    
    # Description
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Notes about this convention")
    )
    
    # Examples (for documentation)
    example_tables = models.JSONField(
        default=list,
        verbose_name=_("Example Tables"),
        help_text=_("Examples: ['mcp_component_type', 'mcp_refactor_config']")
    )
    example_classes = models.JSONField(
        default=list,
        verbose_name=_("Example Classes"),
        help_text=_("Examples: ['MCPComponentType', 'MCPRefactorConfig']")
    )
    
    class Meta:
        db_table = 'core_naming_convention'
        verbose_name = _("Naming Convention")
        verbose_name_plural = _("Naming Conventions")
        ordering = ['app_label']
    
    def __str__(self):
        return f"{self.app_label}: {self.table_prefix}* / {self.class_prefix}*"
    
    def clean(self):
        """Validate convention rules."""
        super().clean()
        
        # Table prefix must end with underscore
        if self.table_prefix and not self.table_prefix.endswith('_'):
            raise ValidationError({
                'table_prefix': _("Table prefix must end with underscore (e.g., 'mcp_')")
            })
        
        # Table prefix must be lowercase
        if self.table_prefix != self.table_prefix.lower():
            raise ValidationError({
                'table_prefix': _("Table prefix must be lowercase")
            })
        
        # Class prefix should be PascalCase (start with uppercase)
        if self.class_prefix and not self.class_prefix[0].isupper():
            raise ValidationError({
                'class_prefix': _("Class prefix must start with uppercase (e.g., 'MCP')")
            })
    
    def get_table_name(self, name: str) -> str:
        """
        Generate table name from model name.
        
        Args:
            name: Model name in snake_case (e.g., "component_type")
            
        Returns:
            Full table name (e.g., "mcp_component_type")
        """
        return self.table_pattern.format(
            prefix=self.table_prefix,
            name=name.lower()
        )
    
    def get_class_name(self, name: str) -> str:
        """
        Generate class name from base name.
        
        Args:
            name: Base name in PascalCase (e.g., "ComponentType")
            
        Returns:
            Full class name (e.g., "MCPComponentType")
        """
        return self.class_pattern.format(
            Prefix=self.class_prefix,
            Name=name
        )
    
    def validate_table_name(self, table_name: str) -> bool:
        """Check if table name follows convention."""
        return table_name.startswith(self.table_prefix)
    
    def validate_class_name(self, class_name: str) -> bool:
        """Check if class name follows convention."""
        return class_name.startswith(self.class_prefix)


# =============================================================================
# MODEL REGISTRY (Optional - für Auto-Validierung)
# =============================================================================

class ModelRegistry(AuditModel):
    """
    Registry aller Models im System.
    
    Ermöglicht:
    - Übersicht aller Tabellen
    - Validierung gegen Naming Conventions
    - Dokumentation
    """
    
    # Identification
    app_label = models.CharField(
        max_length=50,
        verbose_name=_("App Label")
    )
    model_name = models.CharField(
        max_length=100,
        verbose_name=_("Model Name"),
        help_text=_("Python class name")
    )
    
    # Convention Link
    convention = models.ForeignKey(
        TableNamingConvention,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registered_models',
        verbose_name=_("Convention")
    )
    
    # Table Info
    db_table = models.CharField(
        max_length=100,
        verbose_name=_("DB Table")
    )
    
    # Validation Status
    follows_convention = models.BooleanField(
        default=True,
        verbose_name=_("Follows Convention")
    )
    convention_violations = models.JSONField(
        default=list,
        verbose_name=_("Violations"),
        help_text=_("List of convention violations")
    )
    
    # Metadata
    field_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Field Count")
    )
    has_audit_fields = models.BooleanField(
        default=False,
        verbose_name=_("Has Audit Fields")
    )
    
    # Documentation
    docstring = models.TextField(
        blank=True,
        verbose_name=_("Docstring")
    )
    
    class Meta:
        db_table = 'core_model_registry'
        verbose_name = _("Model Registry")
        verbose_name_plural = _("Model Registry")
        unique_together = ['app_label', 'model_name']
        ordering = ['app_label', 'model_name']
    
    def __str__(self):
        status = "✓" if self.follows_convention else "✗"
        return f"{status} {self.app_label}.{self.model_name}"
    
    def validate_against_convention(self) -> list[str]:
        """
        Validate this model against its naming convention.
        
        Returns:
            List of violation messages
        """
        violations = []
        
        if not self.convention:
            return violations
        
        # Check table name
        if not self.convention.validate_table_name(self.db_table):
            violations.append(
                f"Table '{self.db_table}' should start with '{self.convention.table_prefix}'"
            )
        
        # Check class name
        if not self.convention.validate_class_name(self.model_name):
            violations.append(
                f"Class '{self.model_name}' should start with '{self.convention.class_prefix}'"
            )
        
        return violations
    
    def save(self, *args, **kwargs):
        # Auto-validate
        self.convention_violations = self.validate_against_convention()
        self.follows_convention = len(self.convention_violations) == 0
        super().save(*args, **kwargs)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_convention_for_app(app_label: str) -> TableNamingConvention | None:
    """
    Get naming convention for an app.
    
    Args:
        app_label: Django app label
        
    Returns:
        Convention or None
    """
    try:
        return TableNamingConvention.objects.get(app_label=app_label, is_active=True)
    except TableNamingConvention.DoesNotExist:
        return None


def validate_model_naming(app_label: str, class_name: str, table_name: str) -> list[str]:
    """
    Validate model naming against convention.
    
    Args:
        app_label: Django app label
        class_name: Model class name
        table_name: Database table name
        
    Returns:
        List of violations (empty if valid)
    """
    convention = get_convention_for_app(app_label)
    if not convention or not convention.enforce_convention:
        return []
    
    violations = []
    
    if not convention.validate_table_name(table_name):
        violations.append(
            f"Table '{table_name}' must start with '{convention.table_prefix}'"
        )
    
    if not convention.validate_class_name(class_name):
        violations.append(
            f"Class '{class_name}' must start with '{convention.class_prefix}'"
        )
    
    return violations


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "TableNamingConvention",
    "ModelRegistry",
    "get_convention_for_app",
    "validate_model_naming",
]
