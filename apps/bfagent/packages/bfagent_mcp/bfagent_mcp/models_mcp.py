"""
BF Agent MCP Server - Refactoring Models v3
=============================================

Voll normalisiertes Schema mit korrekter Naming Convention.

NAMING CONVENTION:
- Table Prefix: mcp_
- Class Prefix: MCP
- Beispiel: MCPComponentType → mcp_component_type

Alle Models folgen dem Pattern:
- Klasse: MCP{Name}
- Tabelle: mcp_{name}
- verbose_name: "MCP: {Name}"

Dies ermöglicht sofortige Erkennung welche Tabellen zum MCP gehören.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

# Import base classes from main models
try:
    from .models import AuditModel, SoftDeleteModel, TimeStampedModel, Domain
except ImportError:
    # Fallback for standalone testing
    from django.db import models as dj_models
    
    class TimeStampedModel(dj_models.Model):
        created_at = dj_models.DateTimeField(auto_now_add=True)
        updated_at = dj_models.DateTimeField(auto_now=True)
        class Meta:
            abstract = True
    
    class AuditModel(TimeStampedModel):
        class Meta:
            abstract = True
    
    class SoftDeleteModel(dj_models.Model):
        is_active = dj_models.BooleanField(default=True)
        class Meta:
            abstract = True
    
    Domain = None


# =============================================================================
# MCP COMPONENT TYPE
# =============================================================================

class MCPComponentType(AuditModel, SoftDeleteModel):
    """
    MCP: Definition eines Komponenten-Typs.
    
    DB-getrieben statt TextChoices!
    Neue Typen können ohne Migration hinzugefügt werden.
    
    Beispiele: handler, service, model, schema, test, admin, view
    """
    
    # Identification
    name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_("Name"),
        help_text=_("Unique identifier (snake_case): handler, service, model")
    )
    display_name = models.CharField(
        max_length=100,
        verbose_name=_("Display Name"),
        help_text=_("Human readable: Handler, Service, Model")
    )
    
    # Path Conventions (Templates mit Placeholders)
    default_path_pattern = models.CharField(
        max_length=200,
        verbose_name=_("Default Path Pattern"),
        help_text=_("Template: apps/{domain}/handlers/ - {domain} wird ersetzt")
    )
    default_file_pattern = models.CharField(
        max_length=100,
        verbose_name=_("Default File Pattern"),
        help_text=_("Template: {name}_handler.py - {name} wird ersetzt")
    )
    default_class_pattern = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Default Class Pattern"),
        help_text=_("Template: {Name}Handler - {Name} ist PascalCase")
    )
    
    # Appearance
    icon = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_("Icon"),
        help_text=_("Emoji oder kurzer Text: 🔧, H, etc.")
    )
    color = models.CharField(
        max_length=7,
        default="#6b7280",
        verbose_name=_("Color"),
        help_text=_("Hex color: #3b82f6")
    )
    
    # Behavior
    is_directory = models.BooleanField(
        default=True,
        verbose_name=_("Is Directory"),
        help_text=_("True = handlers/, False = models.py")
    )
    supports_refactoring = models.BooleanField(
        default=True,
        verbose_name=_("Supports Refactoring"),
        help_text=_("Can this component type be refactored?")
    )
    
    # Ordering
    order = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_("Order"),
        help_text=_("Display order in UI")
    )
    
    # Description & Template
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("What is this component type for?")
    )
    boilerplate_template = models.TextField(
        blank=True,
        verbose_name=_("Boilerplate Template"),
        help_text=_("Template code for new components of this type")
    )
    
    class Meta:
        db_table = 'mcp_component_type'
        verbose_name = _("MCP: Component Type")
        verbose_name_plural = _("MCP: Component Types")
        ordering = ['order', 'name']
    
    def __str__(self):
        icon = f"{self.icon} " if self.icon else ""
        return f"{icon}{self.display_name}"
    
    def get_path_for_domain(self, domain_id: str) -> str:
        """Generiert Pfad für eine Domain."""
        return self.default_path_pattern.replace("{domain}", domain_id)
    
    def get_file_name(self, name: str) -> str:
        """Generiert Dateinamen."""
        return self.default_file_pattern.replace("{name}", name.lower())
    
    def get_class_name(self, name: str) -> str:
        """Generiert Klassennamen (PascalCase)."""
        if not self.default_class_pattern:
            return ""
        pascal_name = "".join(word.capitalize() for word in name.split("_"))
        return self.default_class_pattern.replace("{Name}", pascal_name)


# =============================================================================
# MCP RISK LEVEL
# =============================================================================

class MCPRiskLevel(AuditModel, SoftDeleteModel):
    """
    MCP: Risk Level Definition.
    
    Ermöglicht custom Risk Levels ohne Code-Änderung.
    """
    
    name = models.CharField(
        max_length=30,
        unique=True,
        verbose_name=_("Name"),
        help_text=_("Identifier: critical, high, medium, low, minimal")
    )
    display_name = models.CharField(
        max_length=50,
        verbose_name=_("Display Name")
    )
    
    # Severity (für Sortierung und Logik)
    severity_score = models.PositiveSmallIntegerField(
        default=50,
        verbose_name=_("Severity Score"),
        help_text=_("0-100, höher = riskanter. Critical=100, Minimal=0")
    )
    
    # Appearance
    color = models.CharField(
        max_length=7,
        default="#6b7280",
        verbose_name=_("Color"),
        help_text=_("Hex color for UI")
    )
    icon = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_("Icon")
    )
    
    # Behavior
    requires_approval = models.BooleanField(
        default=False,
        verbose_name=_("Requires Approval"),
        help_text=_("Must be manually approved before refactoring")
    )
    requires_backup = models.BooleanField(
        default=True,
        verbose_name=_("Requires Backup"),
        help_text=_("Git commit required before refactoring")
    )
    
    # Description
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("When to use this risk level")
    )
    
    class Meta:
        db_table = 'mcp_risk_level'
        verbose_name = _("MCP: Risk Level")
        verbose_name_plural = _("MCP: Risk Levels")
        ordering = ['-severity_score']
    
    def __str__(self):
        icon = f"{self.icon} " if self.icon else ""
        return f"{icon}{self.display_name}"


# =============================================================================
# MCP PROTECTION LEVEL
# =============================================================================

class MCPProtectionLevel(AuditModel, SoftDeleteModel):
    """
    MCP: Protection Level Definition.
    """
    
    name = models.CharField(
        max_length=30,
        unique=True,
        verbose_name=_("Name"),
        help_text=_("Identifier: absolute, warn, review")
    )
    display_name = models.CharField(
        max_length=50,
        verbose_name=_("Display Name")
    )
    
    # Severity
    severity_score = models.PositiveSmallIntegerField(
        default=50,
        verbose_name=_("Severity Score"),
        help_text=_("0-100, höher = strikter. Absolute=100")
    )
    
    # Behavior
    blocks_refactoring = models.BooleanField(
        default=True,
        verbose_name=_("Blocks Refactoring"),
        help_text=_("True = cannot refactor at all")
    )
    requires_confirmation = models.BooleanField(
        default=False,
        verbose_name=_("Requires Confirmation"),
        help_text=_("User must confirm before proceeding")
    )
    
    # Appearance
    color = models.CharField(max_length=7, default="#6b7280")
    icon = models.CharField(max_length=10, blank=True)
    
    description = models.TextField(blank=True)
    
    class Meta:
        db_table = 'mcp_protection_level'
        verbose_name = _("MCP: Protection Level")
        verbose_name_plural = _("MCP: Protection Levels")
        ordering = ['-severity_score']
    
    def __str__(self):
        return f"{self.icon} {self.display_name}" if self.icon else self.display_name


# =============================================================================
# MCP PATH CATEGORY
# =============================================================================

class MCPPathCategory(AuditModel, SoftDeleteModel):
    """
    MCP: Kategorien für Protected Paths.
    """
    
    name = models.CharField(max_length=30, unique=True)
    display_name = models.CharField(max_length=50)
    icon = models.CharField(max_length=10, blank=True)
    color = models.CharField(max_length=7, default="#6b7280")
    description = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    
    class Meta:
        db_table = 'mcp_path_category'
        verbose_name = _("MCP: Path Category")
        verbose_name_plural = _("MCP: Path Categories")
        ordering = ['order', 'name']
    
    def __str__(self):
        return f"{self.icon} {self.display_name}" if self.icon else self.display_name


# =============================================================================
# MCP PROTECTED PATH
# =============================================================================

class MCPProtectedPath(AuditModel, SoftDeleteModel):
    """
    MCP: Geschützte Pfade die NICHT refactored werden dürfen.
    """
    
    path_pattern = models.CharField(
        max_length=200,
        unique=True,
        verbose_name=_("Path Pattern"),
        help_text=_("Glob pattern: packages/bfagent_mcp/** or exact: manage.py")
    )
    
    reason = models.TextField(
        verbose_name=_("Reason"),
        help_text=_("Why is this path protected?")
    )
    
    # Relations (FK statt TextChoices!)
    protection_level = models.ForeignKey(
        MCPProtectionLevel,
        on_delete=models.PROTECT,
        related_name='protected_paths',
        verbose_name=_("Protection Level")
    )
    category = models.ForeignKey(
        MCPPathCategory,
        on_delete=models.PROTECT,
        related_name='protected_paths',
        verbose_name=_("Category")
    )
    
    class Meta:
        db_table = 'mcp_protected_path'
        verbose_name = _("MCP: Protected Path")
        verbose_name_plural = _("MCP: Protected Paths")
        ordering = ['category__order', 'path_pattern']
    
    def __str__(self):
        return f"🔒 {self.path_pattern}"


# =============================================================================
# MCP DOMAIN REFACTOR CONFIG
# =============================================================================

class MCPDomainConfig(AuditModel, SoftDeleteModel):
    """
    MCP: Refactoring-Konfiguration pro Domain.
    
    VERBESSERTES DESIGN:
    - Komponenten über M:N Relation (MCPDomainComponent)
    - Risk Level als FK statt TextChoices
    - Zirkuläre-Abhängigkeiten-Validierung
    """
    
    # Link to Domain
    domain = models.OneToOneField(
        'bfagent_mcp.Domain',
        on_delete=models.CASCADE,
        related_name='mcp_refactor_config',
        verbose_name=_("Domain")
    )
    
    # Path Configuration
    base_path = models.CharField(
        max_length=200,
        verbose_name=_("Base Path"),
        help_text=_("e.g., apps/books/ - auto-generated if empty")
    )
    
    # Risk Level (FK statt TextChoices!)
    risk_level = models.ForeignKey(
        MCPRiskLevel,
        on_delete=models.PROTECT,
        related_name='domain_configs',
        verbose_name=_("Risk Level")
    )
    risk_notes = models.TextField(
        blank=True,
        verbose_name=_("Risk Notes"),
        help_text=_("Why this risk level? What to watch out for?")
    )
    
    # Status Flags
    is_refactor_ready = models.BooleanField(
        default=False,
        verbose_name=_("Refactor Ready"),
        help_text=_("Has been reviewed and approved for refactoring")
    )
    is_protected = models.BooleanField(
        default=False,
        verbose_name=_("Protected"),
        help_text=_("Cannot be refactored (e.g., MCP package)")
    )
    
    # Dependencies (M:N with self-referential through Domain)
    depends_on = models.ManyToManyField(
        'bfagent_mcp.Domain',
        blank=True,
        related_name='mcp_required_by',
        verbose_name=_("Dependencies"),
        help_text=_("These domains must be refactored first")
    )
    
    # Ordering
    refactor_order = models.PositiveSmallIntegerField(
        default=100,
        verbose_name=_("Refactor Order"),
        help_text=_("Lower = refactor earlier. Core=1, Main domains=10-50")
    )
    
    # Tracking
    last_refactored_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Last Refactored")
    )
    refactor_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Refactor Count")
    )
    last_refactor_notes = models.TextField(
        blank=True,
        verbose_name=_("Last Refactor Notes")
    )
    
    class Meta:
        db_table = 'mcp_domain_config'
        verbose_name = _("MCP: Domain Config")
        verbose_name_plural = _("MCP: Domain Configs")
        ordering = ['refactor_order', 'domain__domain_id']
    
    def __str__(self):
        status = "🔒" if self.is_protected else ("✓" if self.is_refactor_ready else "○")
        return f"{status} {self.domain.domain_id}"
    
    def clean(self):
        """Validiert das Model - inkl. Zirkuläre-Abhängigkeiten-Check."""
        super().clean()
        
        if self.pk and self.depends_on.exists():
            if self._has_circular_dependency():
                raise ValidationError({
                    'depends_on': _("Circular dependency detected! Check the dependency chain.")
                })
    
    def _has_circular_dependency(self) -> bool:
        """Prüft auf zirkuläre Abhängigkeiten mit DFS."""
        visited = set()
        path = set()
        
        def dfs(domain_id: int) -> bool:
            if domain_id in path:
                return True
            if domain_id in visited:
                return False
            
            visited.add(domain_id)
            path.add(domain_id)
            
            try:
                config = MCPDomainConfig.objects.get(domain_id=domain_id)
                for dep in config.depends_on.all():
                    if dfs(dep.id):
                        return True
            except MCPDomainConfig.DoesNotExist:
                pass
            
            path.remove(domain_id)
            return False
        
        for dep in self.depends_on.all():
            if dfs(dep.id):
                return True
        
        return False
    
    def get_dependency_chain(self) -> list[str]:
        """Gibt die komplette Dependency-Chain zurück."""
        result = []
        visited = set()
        
        def collect(config: MCPDomainConfig):
            if config.domain_id in visited:
                return
            visited.add(config.domain_id)
            
            for dep in config.depends_on.all():
                try:
                    dep_config = dep.mcp_refactor_config
                    collect(dep_config)
                except MCPDomainConfig.DoesNotExist:
                    pass
            
            result.append(config.domain.domain_id)
        
        collect(self)
        return result
    
    def get_components(self) -> list[MCPComponentType]:
        """Gibt alle Komponenten-Typen dieser Domain zurück."""
        return [
            dc.component_type 
            for dc in self.components.filter(is_active=True)
        ]
    
    def get_component_paths(self) -> dict[str, str]:
        """Gibt Dict von Komponenten-Name zu Pfad zurück."""
        result = {}
        for dc in self.components.filter(is_active=True):
            path = dc.path_override or dc.component_type.get_path_for_domain(
                self.domain.domain_id
            )
            result[dc.component_type.name] = path
        return result
    
    def save(self, *args, **kwargs):
        if not self.base_path and hasattr(self, 'domain') and self.domain:
            self.base_path = f"apps/{self.domain.domain_id}/"
        super().save(*args, **kwargs)


# =============================================================================
# MCP DOMAIN COMPONENT (M:N Relation)
# =============================================================================

class MCPDomainComponent(AuditModel, SoftDeleteModel):
    """
    MCP: Verknüpfung Domain ↔ Component Type.
    
    Ermöglicht flexible Zuordnung von Komponenten zu Domains.
    """
    
    # Relations
    domain_config = models.ForeignKey(
        MCPDomainConfig,
        on_delete=models.CASCADE,
        related_name='components',
        verbose_name=_("Domain Config")
    )
    component_type = models.ForeignKey(
        MCPComponentType,
        on_delete=models.PROTECT,
        related_name='domain_assignments',
        verbose_name=_("Component Type")
    )
    
    # Optional Overrides
    path_override = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_("Path Override"),
        help_text=_("Custom path, falls anders als Default")
    )
    
    # Status
    is_refactorable = models.BooleanField(
        default=True,
        verbose_name=_("Is Refactorable"),
        help_text=_("Can this component be refactored in this domain?")
    )
    
    # Notes
    notes = models.TextField(
        blank=True,
        verbose_name=_("Notes"),
        help_text=_("Besonderheiten dieser Komponente in dieser Domain")
    )
    
    class Meta:
        db_table = 'mcp_domain_component'
        verbose_name = _("MCP: Domain Component")
        verbose_name_plural = _("MCP: Domain Components")
        unique_together = ['domain_config', 'component_type']
        ordering = ['domain_config', 'component_type__order']
    
    def __str__(self):
        return f"{self.domain_config.domain.domain_id}/{self.component_type.name}"
    
    def get_effective_path(self) -> str:
        """Gibt den effektiven Pfad zurück (Override oder Default)."""
        if self.path_override:
            return self.path_override
        return self.component_type.get_path_for_domain(
            self.domain_config.domain.domain_id
        )


# =============================================================================
# MCP REFACTOR SESSION
# =============================================================================

class MCPRefactorSession(AuditModel):
    """
    MCP: Tracking einer Refactoring-Session.
    """
    
    # What was refactored
    domain_config = models.ForeignKey(
        MCPDomainConfig,
        on_delete=models.CASCADE,
        related_name='refactor_sessions',
        verbose_name=_("Domain Config")
    )
    
    # Which components (M:N to MCPComponentType)
    components = models.ManyToManyField(
        MCPComponentType,
        related_name='refactor_sessions',
        verbose_name=_("Components Refactored")
    )
    
    # Timing
    started_at = models.DateTimeField(verbose_name=_("Started At"))
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Ended At"))
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Completed At"))  # Alias for ended_at
    
    # Result Status
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('in_progress', _('In Progress')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
        ('rolled_back', _('Rolled Back')),
        ('cancelled', _('Cancelled')),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name=_("Status"),
        db_index=True
    )
    
    # Summary Stats
    total_files_changed = models.PositiveIntegerField(default=0, verbose_name=_("Files Changed"))
    files_changed = models.PositiveIntegerField(default=0, verbose_name=_("Files Changed"))  # Alias
    total_lines_added = models.PositiveIntegerField(default=0, verbose_name=_("Lines Added"))
    lines_added = models.PositiveIntegerField(default=0, verbose_name=_("Lines Added"))  # Alias
    total_lines_removed = models.PositiveIntegerField(default=0, verbose_name=_("Lines Removed"))
    lines_removed = models.PositiveIntegerField(default=0, verbose_name=_("Lines Removed"))  # Alias
    
    # Celery & Backup
    celery_task_id = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Celery Task ID"))
    backup_path = models.CharField(max_length=500, blank=True, verbose_name=_("Backup Path"))
    components_selected = models.JSONField(default=list, verbose_name=_("Selected Components"))
    
    # Notes
    summary = models.TextField(blank=True, verbose_name=_("Summary"))
    error_message = models.TextField(blank=True, verbose_name=_("Error Message"))
    
    # Git Reference
    git_commit_before = models.CharField(max_length=40, blank=True)
    git_commit_after = models.CharField(max_length=40, blank=True)
    git_branch = models.CharField(max_length=100, blank=True)
    
    # Trigger Info
    triggered_by = models.CharField(
        max_length=50,
        choices=[
            ('manual', _('Manual')),
            ('mcp', _('MCP Server')),
            ('windsurf', _('Windsurf IDE')),
            ('web_dashboard', _('Web Dashboard')),
            ('ci', _('CI/CD Pipeline')),
            ('api', _('API Call')),
        ],
        default='manual',
        verbose_name=_("Triggered By")
    )
    triggered_by_user = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mcp_sessions',
        verbose_name=_("Triggered By User")
    )
    
    class Meta:
        db_table = 'mcp_refactor_session'
        verbose_name = _("MCP: Refactor Session")
        verbose_name_plural = _("MCP: Refactor Sessions")
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['status', 'started_at']),
            models.Index(fields=['domain_config', 'status']),
        ]
    
    def __str__(self):
        return f"{self.domain_config.domain.domain_id} - {self.started_at:%Y-%m-%d %H:%M}"
    
    @property
    def duration_seconds(self) -> float | None:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def update_stats_from_files(self):
        """Aktualisiert Summary-Stats aus FileChanges."""
        from django.db.models import Sum, Count
        
        stats = self.file_changes.aggregate(
            total_files=Count('id'),
            total_added=Sum('lines_added'),
            total_removed=Sum('lines_removed'),
        )
        
        self.total_files_changed = stats['total_files'] or 0
        self.total_lines_added = stats['total_added'] or 0
        self.total_lines_removed = stats['total_removed'] or 0
        self.save(update_fields=['total_files_changed', 'total_lines_added', 'total_lines_removed'])


# =============================================================================
# MCP FILE CHANGE
# =============================================================================

class MCPFileChange(TimeStampedModel):
    """
    MCP: Detail welche Datei wie geändert wurde.
    """
    
    session = models.ForeignKey(
        MCPRefactorSession,
        on_delete=models.CASCADE,
        related_name='file_changes',
        verbose_name=_("Session")
    )
    
    file_path = models.CharField(max_length=500, verbose_name=_("File Path"))
    
    change_type = models.CharField(
        max_length=20,
        choices=[
            ('created', _('Created')),
            ('modified', _('Modified')),
            ('deleted', _('Deleted')),
            ('renamed', _('Renamed')),
            ('moved', _('Moved')),
        ],
        verbose_name=_("Change Type"),
        db_index=True
    )
    
    old_path = models.CharField(max_length=500, blank=True, verbose_name=_("Old Path"))
    lines_added = models.PositiveIntegerField(default=0)
    lines_removed = models.PositiveIntegerField(default=0)
    diff_preview = models.TextField(blank=True, verbose_name=_("Diff Preview"))
    diff_content = models.TextField(blank=True, verbose_name=_("Diff Content"))  # Alias for diff_preview
    
    component_type = models.ForeignKey(
        MCPComponentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='file_changes',
        verbose_name=_("Component Type")
    )
    
    class Meta:
        db_table = 'mcp_file_change'
        verbose_name = _("MCP: File Change")
        verbose_name_plural = _("MCP: File Changes")
        ordering = ['session', 'file_path']
        indexes = [
            models.Index(fields=['session', 'change_type']),
            models.Index(fields=['file_path']),
        ]
    
    def __str__(self):
        return f"{self.get_change_type_display()}: {self.file_path}"


# =============================================================================
# MCP CONFIG HISTORY
# =============================================================================

class MCPConfigHistory(TimeStampedModel):
    """
    MCP: History aller Config-Änderungen.
    """
    
    config = models.ForeignKey(
        MCPDomainConfig,
        on_delete=models.CASCADE,
        related_name='history',
        verbose_name=_("Config")
    )
    
    field_name = models.CharField(max_length=100, verbose_name=_("Field Name"))
    old_value = models.TextField(blank=True, verbose_name=_("Old Value"))
    new_value = models.TextField(blank=True, verbose_name=_("New Value"))
    
    changed_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Changed By")
    )
    change_reason = models.TextField(blank=True, verbose_name=_("Change Reason"))
    
    class Meta:
        db_table = 'mcp_config_history'
        verbose_name = _("MCP: Config History")
        verbose_name_plural = _("MCP: Config History")
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.config.domain.domain_id}.{self.field_name} changed"


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Reference Tables
    "MCPComponentType",
    "MCPRiskLevel",
    "MCPProtectionLevel",
    "MCPPathCategory",
    # Main Models
    "MCPDomainConfig",
    "MCPDomainComponent",
    "MCPProtectedPath",
    # Tracking
    "MCPRefactorSession",
    "MCPFileChange",
    "MCPConfigHistory",
]
