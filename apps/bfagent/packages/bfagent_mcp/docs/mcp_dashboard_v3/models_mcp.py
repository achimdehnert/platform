"""
MCP Dashboard Models
====================

Django Models für das MCP Dashboard.

Models:
- MCPRiskLevel: Risikostufen für Domains
- MCPProtectionLevel: Schutzstufen für Pfade  
- MCPPathCategory: Kategorien für Protected Paths
- MCPComponentType: Typen von Komponenten (Handler, Service, etc.)
- MCPDomainConfig: Konfiguration pro Domain
- MCPDomainComponent: Komponenten einer Domain
- MCPProtectedPath: Geschützte Pfade
- MCPRefactorSession: Refactoring-Sessions
- MCPSessionFileChange: Dateiänderungen in Sessions
- MCPRefactoringRule: Custom Refactoring Rules

Author: BF Agent Team
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


# =============================================================================
# ABSTRACT BASE MODELS
# =============================================================================

class AuditModel(models.Model):
    """Abstract base model with audit fields."""
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class ActivatableModel(AuditModel):
    """Abstract model with is_active flag."""
    
    is_active = models.BooleanField(default=True, db_index=True)
    
    class Meta:
        abstract = True


# =============================================================================
# LOOKUP MODELS
# =============================================================================

class MCPRiskLevel(ActivatableModel):
    """
    Risikostufen für Domain-Konfigurationen.
    
    Beispiele:
    - LOW: Sicher für Refactoring
    - MEDIUM: Backup erforderlich
    - HIGH: Genehmigung + Backup erforderlich
    - CRITICAL: Kein Refactoring erlaubt
    """
    
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    severity_score = models.IntegerField(
        default=50,
        help_text=_("0-100, higher = more severe")
    )
    requires_approval = models.BooleanField(default=False)
    requires_backup = models.BooleanField(default=True)
    color = models.CharField(
        max_length=20,
        default='secondary',
        help_text=_("Bootstrap color class")
    )
    icon = models.CharField(max_length=10, default='🟡')
    description = models.TextField(blank=True)
    
    class Meta:
        db_table = 'mcp_risk_level'
        ordering = ['-severity_score']
        verbose_name = _("Risk Level")
        verbose_name_plural = _("Risk Levels")
    
    def __str__(self):
        return f"{self.icon} {self.display_name}"


class MCPProtectionLevel(ActivatableModel):
    """
    Schutzstufen für Protected Paths.
    
    Beispiele:
    - ABSOLUTE: Niemals modifizieren
    - REVIEW: Nur mit Review
    - WARN: Warnung anzeigen
    - NONE: Keine Einschränkung
    """
    
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    severity_score = models.IntegerField(default=50)
    color = models.CharField(max_length=20, default='secondary')
    icon = models.CharField(max_length=10, default='🔒')
    description = models.TextField(blank=True)
    
    class Meta:
        db_table = 'mcp_protection_level'
        ordering = ['-severity_score']
        verbose_name = _("Protection Level")
        verbose_name_plural = _("Protection Levels")
    
    def __str__(self):
        return f"{self.icon} {self.display_name}"


class MCPPathCategory(ActivatableModel):
    """
    Kategorien für Protected Paths.
    
    Beispiele:
    - MCP: MCP Package selbst
    - Config: Konfigurationsdateien
    - Security: Sicherheitskritische Dateien
    - Infrastructure: Deployment, Docker, etc.
    """
    
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    icon = models.CharField(max_length=10, default='📁')
    order = models.IntegerField(default=0)
    description = models.TextField(blank=True)
    
    class Meta:
        db_table = 'mcp_path_category'
        ordering = ['order', 'name']
        verbose_name = _("Path Category")
        verbose_name_plural = _("Path Categories")
    
    def __str__(self):
        return f"{self.icon} {self.display_name}"


class MCPComponentType(ActivatableModel):
    """
    Typen von Komponenten.
    
    Beispiele:
    - handler: *_handler.py
    - service: *_service.py
    - repository: *_repository.py
    - model: models.py
    - view: views*.py
    """
    
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    file_pattern = models.CharField(
        max_length=100,
        help_text=_("Glob pattern, e.g. '*_handler.py'")
    )
    class_suffix = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Expected class suffix, e.g. 'Handler'")
    )
    icon = models.CharField(max_length=10, default='📦')
    is_refactorable = models.BooleanField(
        default=True,
        help_text=_("Can this component type be refactored?")
    )
    order = models.IntegerField(default=0)
    description = models.TextField(blank=True)
    
    class Meta:
        db_table = 'mcp_component_type'
        ordering = ['order', 'name']
        verbose_name = _("Component Type")
        verbose_name_plural = _("Component Types")
    
    def __str__(self):
        return f"{self.icon} {self.display_name}"


# =============================================================================
# DOMAIN CONFIGURATION
# =============================================================================

class MCPDomainConfig(ActivatableModel):
    """
    MCP Konfiguration für eine Domain.
    
    Verknüpft eine Domain mit:
    - Risikostufe
    - Base Path
    - Refactoring-Einstellungen
    - Abhängigkeiten
    """
    
    # Verknüpfung zur Domain (aus dem Hauptsystem)
    domain = models.OneToOneField(
        'bfagent_mcp.Domain',  # Adjust to your actual Domain model
        on_delete=models.CASCADE,
        related_name='mcp_config'
    )
    
    # Configuration
    base_path = models.CharField(
        max_length=255,
        help_text=_("Relative path from project root, e.g. 'apps/books'")
    )
    risk_level = models.ForeignKey(
        MCPRiskLevel,
        on_delete=models.PROTECT,
        related_name='domain_configs'
    )
    
    # Refactoring settings
    allows_refactoring = models.BooleanField(
        default=True,
        help_text=_("Can this domain be refactored?")
    )
    is_protected = models.BooleanField(
        default=False,
        help_text=_("Completely protected from any changes?")
    )
    is_refactor_ready = models.BooleanField(
        default=False,
        help_text=_("Has been reviewed and is ready for refactoring?")
    )
    refactor_order = models.IntegerField(
        default=0,
        help_text=_("Order in refactoring queue (lower = earlier)")
    )
    
    # Dependencies
    depends_on = models.ManyToManyField(
        'bfagent_mcp.Domain',
        blank=True,
        related_name='dependents',
        help_text=_("Domains this one depends on")
    )
    
    # Notes
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'mcp_domain_config'
        ordering = ['refactor_order', 'domain__name']
        verbose_name = _("Domain Config")
        verbose_name_plural = _("Domain Configs")
    
    def __str__(self):
        return f"{self.domain.display_name} ({self.risk_level.name})"
    
    @property
    def component_count(self) -> int:
        """Get count of active components."""
        return self.components.filter(is_active=True).count()


class MCPDomainComponent(ActivatableModel):
    """
    Komponente einer Domain.
    
    Repräsentiert eine einzelne Datei/Klasse wie:
    - ChapterHandler
    - BookService
    - UserRepository
    """
    
    domain_config = models.ForeignKey(
        MCPDomainConfig,
        on_delete=models.CASCADE,
        related_name='components'
    )
    component_type = models.ForeignKey(
        MCPComponentType,
        on_delete=models.PROTECT,
        related_name='components'
    )
    
    name = models.CharField(max_length=100)
    file_path = models.CharField(max_length=255)
    class_name = models.CharField(max_length=100, blank=True)
    
    is_refactorable = models.BooleanField(default=True)
    last_refactored = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'mcp_domain_component'
        ordering = ['domain_config', 'component_type', 'name']
        unique_together = ['domain_config', 'component_type', 'name']
        verbose_name = _("Domain Component")
        verbose_name_plural = _("Domain Components")
    
    def __str__(self):
        return f"{self.name} ({self.component_type.name})"


# =============================================================================
# PROTECTED PATHS
# =============================================================================

class MCPProtectedPath(ActivatableModel):
    """
    Geschützter Pfad.
    
    Pfade die vor Refactoring geschützt sind:
    - Glob Patterns: packages/bfagent_mcp/**
    - Regex Patterns: .*_test\.py$
    """
    
    path_pattern = models.CharField(
        max_length=255,
        unique=True,
        help_text=_("Glob or regex pattern")
    )
    protection_level = models.ForeignKey(
        MCPProtectionLevel,
        on_delete=models.PROTECT,
        related_name='protected_paths'
    )
    category = models.ForeignKey(
        MCPPathCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paths'
    )
    
    is_regex = models.BooleanField(
        default=False,
        help_text=_("Is this a regex pattern?")
    )
    reason = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'mcp_protected_path'
        ordering = ['category__order', 'path_pattern']
        verbose_name = _("Protected Path")
        verbose_name_plural = _("Protected Paths")
    
    def __str__(self):
        return self.path_pattern


# =============================================================================
# REFACTORING SESSIONS
# =============================================================================

class MCPRefactorSession(AuditModel):
    """
    Refactoring Session.
    
    Trackt eine komplette Refactoring-Operation:
    - Start/Ende Zeitpunkt
    - Geänderte Dateien
    - Statistiken
    - Status
    """
    
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('in_progress', _('In Progress')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
        ('cancelled', _('Cancelled')),
    ]
    
    domain_config = models.ForeignKey(
        MCPDomainConfig,
        on_delete=models.CASCADE,
        related_name='refactor_sessions'
    )
    
    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    error_message = models.TextField(blank=True)
    
    # Stats
    files_changed = models.IntegerField(default=0)
    lines_added = models.IntegerField(default=0)
    lines_removed = models.IntegerField(default=0)
    
    # Triggering
    triggered_by = models.CharField(
        max_length=50,
        default='manual',
        help_text=_("How was this session triggered?")
    )
    triggered_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mcp_sessions'
    )
    
    # Configuration
    components_selected = models.JSONField(
        default=list,
        help_text=_("List of component types selected for refactoring")
    )
    
    # Celery
    celery_task_id = models.CharField(max_length=255, blank=True)
    
    # Backup
    backup_path = models.CharField(max_length=500, blank=True)
    
    class Meta:
        db_table = 'mcp_refactor_session'
        ordering = ['-started_at']
        verbose_name = _("Refactor Session")
        verbose_name_plural = _("Refactor Sessions")
    
    def __str__(self):
        return f"Session #{self.id} - {self.domain_config.domain.display_name} ({self.status})"
    
    @property
    def duration(self):
        """Get session duration."""
        if self.started_at and self.ended_at:
            return self.ended_at - self.started_at
        return None


class MCPSessionFileChange(AuditModel):
    """
    Dateiänderung in einer Session.
    
    Trackt jede einzelne Datei die geändert wurde:
    - Pfad
    - Änderungstyp
    - Diff
    - Statistiken
    """
    
    CHANGE_TYPE_CHOICES = [
        ('added', _('Added')),
        ('modified', _('Modified')),
        ('deleted', _('Deleted')),
    ]
    
    session = models.ForeignKey(
        MCPRefactorSession,
        on_delete=models.CASCADE,
        related_name='file_changes'
    )
    
    file_path = models.CharField(max_length=500)
    change_type = models.CharField(
        max_length=20,
        choices=CHANGE_TYPE_CHOICES,
        default='modified'
    )
    
    lines_added = models.IntegerField(default=0)
    lines_removed = models.IntegerField(default=0)
    
    diff_content = models.TextField(
        blank=True,
        help_text=_("Unified diff of changes")
    )
    
    class Meta:
        db_table = 'mcp_session_file_change'
        ordering = ['session', 'file_path']
        verbose_name = _("File Change")
        verbose_name_plural = _("File Changes")
    
    def __str__(self):
        return f"{self.change_type}: {self.file_path}"


# =============================================================================
# CUSTOM REFACTORING RULES
# =============================================================================

class MCPRefactoringRule(ActivatableModel):
    """
    Custom Refactoring Rule.
    
    Erlaubt das Hinzufügen von Refactoring-Regeln über Admin.
    """
    
    name = models.CharField(max_length=100, unique=True)
    component_type = models.CharField(
        max_length=50,
        help_text=_("Component type this rule applies to")
    )
    
    pattern = models.TextField(
        help_text=_("Regex pattern to match")
    )
    replacement = models.TextField(
        help_text=_("Replacement string (supports regex groups)")
    )
    
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    
    # Conditions
    condition_code = models.TextField(
        blank=True,
        help_text=_("Python code that returns True/False for condition check")
    )
    
    class Meta:
        db_table = 'mcp_refactoring_rule'
        ordering = ['component_type', 'order', 'name']
        verbose_name = _("Refactoring Rule")
        verbose_name_plural = _("Refactoring Rules")
    
    def __str__(self):
        return f"{self.name} ({self.component_type})"


# =============================================================================
# NAMING CONVENTIONS (referenced by sync service)
# =============================================================================

class TableNamingConvention(ActivatableModel):
    """
    Naming Convention für Komponenten.
    
    Definiert wie Dateien und Klassen benannt werden sollen.
    """
    
    app_label = models.CharField(
        max_length=100,
        help_text=_("App label or '*' for all apps")
    )
    component_type = models.CharField(
        max_length=50,
        help_text=_("Component type: handler, service, etc.")
    )
    
    file_pattern = models.CharField(
        max_length=100,
        help_text=_("File naming pattern, e.g. '{model}_handler.py'")
    )
    class_pattern = models.CharField(
        max_length=100,
        help_text=_("Class naming pattern, e.g. '{Model}Handler'")
    )
    
    prefix = models.CharField(max_length=50, blank=True)
    suffix = models.CharField(max_length=50, blank=True)
    
    enforce_convention = models.BooleanField(
        default=False,
        help_text=_("Strictly enforce this convention?")
    )
    
    description = models.TextField(blank=True)
    example = models.CharField(max_length=200, blank=True)
    
    class Meta:
        db_table = 'mcp_naming_convention'
        ordering = ['app_label', 'component_type']
        unique_together = ['app_label', 'component_type']
        verbose_name = _("Naming Convention")
        verbose_name_plural = _("Naming Conventions")
    
    def __str__(self):
        return f"{self.app_label}/{self.component_type}"


# =============================================================================
# DOMAIN MODEL (Base model referenced by MCP configs)
# =============================================================================

class Domain(ActivatableModel):
    """
    Base Domain Model.
    
    Repräsentiert eine Domain im System.
    Wird von MCPDomainConfig referenziert.
    """
    
    domain_id = models.CharField(
        max_length=50,
        unique=True,
        help_text=_("Unique identifier, e.g. 'books', 'medtrans'")
    )
    name = models.CharField(max_length=100)
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    class Meta:
        db_table = 'mcp_domain'
        ordering = ['name']
        verbose_name = _("Domain")
        verbose_name_plural = _("Domains")
    
    def __str__(self):
        return self.display_name
