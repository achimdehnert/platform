"""
BF Agent MCP Server - Extended Models
======================================

Zusätzliche Models für "Self-Dogfooding":
MCP folgt den eigenen BF Agent Regeln - alles DB-getrieben!

Diese Datei enthält:
- CodingConvention: Coding-Regeln und Standards
- ProjectStructure: Projekt-Struktur-Konventionen
- MCPContext: Kontext-Templates für verschiedene Aufgaben
"""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

# Import base classes from main models
try:
    from .models import AuditModel, SoftDeleteModel, Domain
except ImportError:
    # Standalone mode - define minimal bases
    class AuditModel(models.Model):
        created_at = models.DateTimeField(auto_now_add=True)
        updated_at = models.DateTimeField(auto_now=True)
        class Meta:
            abstract = True
    
    class SoftDeleteModel(models.Model):
        is_active = models.BooleanField(default=True)
        class Meta:
            abstract = True
    
    Domain = None


# =============================================================================
# CODING CONVENTION MODEL
# =============================================================================

class ConventionCategory(models.TextChoices):
    """Kategorien für Coding Conventions."""
    NAMING = 'naming', _('Naming Conventions')
    STRUCTURE = 'structure', _('Code Structure')
    PATTERNS = 'patterns', _('Design Patterns')
    VALIDATION = 'validation', _('Input/Output Validation')
    ERROR_HANDLING = 'error_handling', _('Error Handling')
    TESTING = 'testing', _('Testing Standards')
    DOCUMENTATION = 'documentation', _('Documentation')
    PERFORMANCE = 'performance', _('Performance')
    SECURITY = 'security', _('Security')


class ConventionSeverity(models.TextChoices):
    """Schweregrad bei Verletzung der Convention."""
    ERROR = 'error', _('Error - Must Fix')
    WARNING = 'warning', _('Warning - Should Fix')
    INFO = 'info', _('Info - Consider')
    HINT = 'hint', _('Hint - Optional')


class CodingConvention(AuditModel, SoftDeleteModel):
    """
    Coding Conventions für BF Agent.
    
    DB-getrieben statt hardcoded!
    Wird von MCP gelesen und an Windsurf weitergegeben.
    """
    
    # Identification
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("Name"),
        help_text=_("Unique identifier (snake_case)")
    )
    display_name = models.CharField(
        max_length=200,
        verbose_name=_("Display Name")
    )
    
    # Categorization
    category = models.CharField(
        max_length=30,
        choices=ConventionCategory.choices,
        default=ConventionCategory.PATTERNS,
        verbose_name=_("Category"),
        db_index=True
    )
    severity = models.CharField(
        max_length=20,
        choices=ConventionSeverity.choices,
        default=ConventionSeverity.WARNING,
        verbose_name=_("Severity"),
        db_index=True
    )
    
    # Rule Definition
    rule = models.TextField(
        verbose_name=_("Rule"),
        help_text=_("The convention rule in clear language")
    )
    rationale = models.TextField(
        blank=True,
        verbose_name=_("Rationale"),
        help_text=_("Why this rule exists")
    )
    
    # Examples
    example_good = models.TextField(
        blank=True,
        verbose_name=_("Good Example"),
        help_text=_("Code that follows this convention")
    )
    example_bad = models.TextField(
        blank=True,
        verbose_name=_("Bad Example"),
        help_text=_("Code that violates this convention")
    )
    
    # Applicability
    applies_to = models.JSONField(
        default=list,
        verbose_name=_("Applies To"),
        help_text=_("Component types: ['handler', 'service', 'model', 'test']")
    )
    
    # Optional: Regex pattern for automated checking
    check_pattern = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_("Check Pattern"),
        help_text=_("Regex pattern for automated validation")
    )
    
    # Ordering
    order = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_("Order")
    )
    
    class Meta:
        verbose_name = _("Coding Convention")
        verbose_name_plural = _("Coding Conventions")
        ordering = ['category', 'order', 'name']
        indexes = [
            models.Index(fields=['category', 'severity']),
            models.Index(fields=['is_active', 'category']),
        ]
    
    def __str__(self):
        return f"[{self.severity}] {self.display_name}"


# =============================================================================
# PROJECT STRUCTURE MODEL
# =============================================================================

class ComponentType(models.TextChoices):
    """Typen von Projekt-Komponenten."""
    HANDLER = 'handler', _('Handler')
    SERVICE = 'service', _('Service')
    MODEL = 'model', _('Model')
    SCHEMA = 'schema', _('Schema')
    TEST = 'test', _('Test')
    ADMIN = 'admin', _('Admin')
    VIEW = 'view', _('View')
    URL = 'url', _('URL Config')
    TEMPLATE = 'template', _('Template')
    MANAGEMENT_COMMAND = 'management_command', _('Management Command')
    MIGRATION = 'migration', _('Migration')
    FIXTURE = 'fixture', _('Fixture')


class ProjectStructure(AuditModel, SoftDeleteModel):
    """
    Projekt-Struktur Konventionen.
    
    Definiert wo verschiedene Komponenten-Typen liegen
    und wie sie benannt werden sollen.
    """
    
    # Component Definition
    component_type = models.CharField(
        max_length=30,
        choices=ComponentType.choices,
        unique=True,
        verbose_name=_("Component Type")
    )
    
    # Path Conventions
    path_pattern = models.CharField(
        max_length=200,
        verbose_name=_("Path Pattern"),
        help_text=_("Pattern with placeholders: apps/{domain}/handlers/")
    )
    
    # Naming Conventions
    file_naming_pattern = models.CharField(
        max_length=100,
        verbose_name=_("File Naming Pattern"),
        help_text=_("Pattern: {name}_handler.py")
    )
    class_naming_pattern = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Class Naming Pattern"),
        help_text=_("Pattern: {Name}Handler (PascalCase)")
    )
    
    # Description
    description = models.TextField(
        verbose_name=_("Description"),
        help_text=_("Purpose and usage of this component type")
    )
    
    # Template
    boilerplate_template = models.TextField(
        blank=True,
        verbose_name=_("Boilerplate Template"),
        help_text=_("Template code for new components")
    )
    
    # Related Conventions
    related_conventions = models.ManyToManyField(
        CodingConvention,
        blank=True,
        related_name='structures',
        verbose_name=_("Related Conventions")
    )
    
    class Meta:
        verbose_name = _("Project Structure")
        verbose_name_plural = _("Project Structures")
        ordering = ['component_type']
    
    def __str__(self):
        return f"{self.get_component_type_display()}: {self.path_pattern}"


# =============================================================================
# MCP CONTEXT MODEL
# =============================================================================

class ContextType(models.TextChoices):
    """Typen von MCP-Kontext."""
    CREATE_HANDLER = 'create_handler', _('Create Handler')
    CREATE_SERVICE = 'create_service', _('Create Service')
    CREATE_MODEL = 'create_model', _('Create Model')
    CREATE_TEST = 'create_test', _('Create Test')
    FIX_BUG = 'fix_bug', _('Fix Bug')
    ADD_FEATURE = 'add_feature', _('Add Feature')
    REFACTOR = 'refactor', _('Refactor')
    REVIEW = 'review', _('Code Review')
    EXPLAIN = 'explain', _('Explain Code')


class MCPContext(AuditModel, SoftDeleteModel):
    """
    Kontext-Templates für MCP-Aufgaben.
    
    Gibt Windsurf strukturierten Kontext für verschiedene Aufgaben.
    """
    
    # Identification
    context_type = models.CharField(
        max_length=30,
        choices=ContextType.choices,
        unique=True,
        verbose_name=_("Context Type")
    )
    display_name = models.CharField(
        max_length=100,
        verbose_name=_("Display Name")
    )
    
    # Context Template (Markdown with placeholders)
    context_template = models.TextField(
        verbose_name=_("Context Template"),
        help_text=_("Markdown template with {placeholders}")
    )
    
    # Related Info
    required_info = models.JSONField(
        default=list,
        verbose_name=_("Required Info"),
        help_text=_("What info to gather: ['domain', 'name', 'description']")
    )
    
    # What to include
    include_conventions = models.BooleanField(
        default=True,
        verbose_name=_("Include Conventions")
    )
    include_best_practices = models.BooleanField(
        default=True,
        verbose_name=_("Include Best Practices")
    )
    include_similar_code = models.BooleanField(
        default=True,
        verbose_name=_("Include Similar Code")
    )
    include_structure = models.BooleanField(
        default=True,
        verbose_name=_("Include Project Structure")
    )
    
    # Best practices topics to include
    best_practice_topics = models.JSONField(
        default=list,
        verbose_name=_("Best Practice Topics"),
        help_text=_("Topics to include: ['handlers', 'pydantic']")
    )
    
    # Convention categories to include
    convention_categories = models.JSONField(
        default=list,
        verbose_name=_("Convention Categories"),
        help_text=_("Categories to include: ['patterns', 'naming']")
    )
    
    class Meta:
        verbose_name = _("MCP Context")
        verbose_name_plural = _("MCP Contexts")
        ordering = ['context_type']
    
    def __str__(self):
        return self.display_name


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Choices
    "ConventionCategory",
    "ConventionSeverity",
    "ComponentType",
    "ContextType",
    # Models
    "CodingConvention",
    "ProjectStructure",
    "MCPContext",
]
