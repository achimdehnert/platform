"""
BF Agent MCP Server - Django Models
====================================

Normalisierte Datenbankstruktur für Domain/Handler-Registry.

Design-Prinzipien:
- 3NF Normalisierung (keine redundanten Daten)
- Integer Primary Keys (Performance)
- Explizite ForeignKeys statt JSON-Felder
- Separate Junction Tables für M:N
- Audit Fields (created_at, updated_at, created_by)
- Soft Delete Pattern (is_active statt DELETE)

Tabellen-Hierarchie:
- Tag (unabhängig)
- Domain → Phase (1:N)
- Domain → Handler (1:N)
- Handler ↔ Tag (M:N via HandlerTag)
- Domain ↔ Tag (M:N via DomainTag)
- BestPractice (unabhängig)
- PromptTemplate → Domain (N:1)
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


# =============================================================================
# ABSTRACT BASE MODELS
# =============================================================================

class TimeStampedModel(models.Model):
    """
    Abstract Base Model mit Audit-Feldern.
    
    Jedes Model erbt automatisch:
    - created_at: Erstellungszeitpunkt
    - updated_at: Letzte Änderung
    """
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
        db_index=True
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At")
    )
    
    class Meta:
        abstract = True


class AuditModel(TimeStampedModel):
    """
    Abstract Base Model mit vollem Audit Trail.
    
    Erweitert TimeStampedModel um:
    - created_by: Ersteller
    - updated_by: Letzter Bearbeiter
    """
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_created",
        verbose_name=_("Created By")
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_updated",
        verbose_name=_("Updated By")
    )
    
    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """
    Abstract Base Model mit Soft Delete.
    
    Statt DELETE wird is_active=False gesetzt.
    """
    
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Active"),
        db_index=True,
        help_text=_("Inactive items are hidden but not deleted")
    )
    
    class Meta:
        abstract = True
    
    def soft_delete(self):
        """Soft Delete: Setzt is_active=False."""
        self.is_active = False
        self.save(update_fields=['is_active', 'updated_at'])
    
    def restore(self):
        """Restore: Setzt is_active=True."""
        self.is_active = True
        self.save(update_fields=['is_active', 'updated_at'])


# =============================================================================
# TAG MODEL (Independent)
# =============================================================================

class TagCategory(models.TextChoices):
    """Kategorien für Tags."""
    GENERAL = 'general', _('General')
    TECHNICAL = 'technical', _('Technical')
    DOMAIN = 'domain', _('Domain')
    AI = 'ai', _('AI/ML')
    FORMAT = 'format', _('File Format')


class Tag(TimeStampedModel):
    """
    Tag für Kategorisierung von Domains und Handlern.
    
    Normalisiert: Eigene Tabelle statt JSON-Array in Parent.
    """
    
    name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_("Name"),
        help_text=_("Unique tag name (lowercase)")
    )
    display_name = models.CharField(
        max_length=100,
        verbose_name=_("Display Name")
    )
    category = models.CharField(
        max_length=20,
        choices=TagCategory.choices,
        default=TagCategory.GENERAL,
        verbose_name=_("Category"),
        db_index=True
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description")
    )
    color = models.CharField(
        max_length=7,
        default="#6B7280",
        verbose_name=_("Color"),
        help_text=_("Hex color code")
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("Icon"),
        help_text=_("Icon identifier (e.g., Lucide icon name)")
    )
    
    class Meta:
        verbose_name = _("Tag")
        verbose_name_plural = _("Tags")
        ordering = ['category', 'name']
    
    def __str__(self):
        return self.display_name
    
    def save(self, *args, **kwargs):
        # Ensure name is lowercase
        self.name = self.name.lower().strip()
        if not self.display_name:
            self.display_name = self.name.title()
        super().save(*args, **kwargs)


# =============================================================================
# DOMAIN MODEL
# =============================================================================

class DomainStatus(models.TextChoices):
    """Status einer Domain."""
    PRODUCTION = 'production', _('Production')
    BETA = 'beta', _('Beta')
    DEVELOPMENT = 'development', _('Development')
    PLANNED = 'planned', _('Planned')
    DEPRECATED = 'deprecated', _('Deprecated')


class Domain(AuditModel, SoftDeleteModel):
    """
    Fachdomäne im BF Agent System.
    
    Repräsentiert einen kompletten Workflow-Bereich
    (z.B. Books, CAD, MedTrans).
    """
    
    # Identification
    domain_id = models.SlugField(
        max_length=50,
        unique=True,
        verbose_name=_("Domain ID"),
        help_text=_("Unique slug identifier (e.g., 'books', 'cad')")
    )
    display_name = models.CharField(
        max_length=100,
        verbose_name=_("Display Name")
    )
    description = models.TextField(
        verbose_name=_("Description")
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=DomainStatus.choices,
        default=DomainStatus.DEVELOPMENT,
        verbose_name=_("Status"),
        db_index=True
    )
    
    # Visual
    icon = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("Icon")
    )
    color = models.CharField(
        max_length=7,
        default="#3B82F6",
        verbose_name=_("Color")
    )
    
    # Metadata
    version = models.CharField(
        max_length=20,
        default="1.0.0",
        verbose_name=_("Version")
    )
    
    # Configuration (JSON für flexible Config)
    config = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Configuration"),
        help_text=_("Domain-specific configuration")
    )
    
    # Relations (M:N via Junction Table)
    tags = models.ManyToManyField(
        Tag,
        through='DomainTag',
        related_name='domains',
        blank=True,
        verbose_name=_("Tags")
    )
    
    class Meta:
        verbose_name = _("Domain")
        verbose_name_plural = _("Domains")
        ordering = ['display_name']
        indexes = [
            models.Index(fields=['status', 'is_active']),
            models.Index(fields=['domain_id']),
        ]
    
    def __str__(self):
        return f"{self.display_name} ({self.domain_id})"
    
    @property
    def handler_count(self) -> int:
        """Anzahl aktiver Handler in dieser Domain."""
        return self.handlers.filter(is_active=True).count()
    
    @property
    def phase_list(self) -> list:
        """Liste der Phasen-Namen in Reihenfolge."""
        return list(self.phases.order_by('order').values_list('name', flat=True))


# =============================================================================
# DOMAIN-TAG JUNCTION TABLE
# =============================================================================

class DomainTag(TimeStampedModel):
    """
    Junction Table für Domain ↔ Tag (M:N).
    
    Normalisiert: Eigene Tabelle statt ManyToMany ohne through.
    Ermöglicht zusätzliche Metadaten pro Zuordnung.
    """
    
    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        verbose_name=_("Domain")
    )
    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        verbose_name=_("Tag")
    )
    
    # Optional: Reihenfolge der Tags
    order = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_("Order")
    )
    
    class Meta:
        verbose_name = _("Domain Tag")
        verbose_name_plural = _("Domain Tags")
        unique_together = ['domain', 'tag']
        ordering = ['order']


# =============================================================================
# PHASE MODEL
# =============================================================================

class Phase(TimeStampedModel):
    """
    Workflow-Phase innerhalb einer Domain.
    
    Definiert die Schritte eines Domain-Workflows
    (z.B. Upload → Parsing → Analyse → Report).
    """
    
    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        related_name='phases',
        verbose_name=_("Domain")
    )
    
    # Identification
    name = models.CharField(
        max_length=50,
        verbose_name=_("Name"),
        help_text=_("Internal name (lowercase)")
    )
    display_name = models.CharField(
        max_length=100,
        verbose_name=_("Display Name")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description")
    )
    
    # Ordering
    order = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_("Order"),
        db_index=True
    )
    
    # Visual
    color = models.CharField(
        max_length=7,
        default="#3B82F6",
        verbose_name=_("Color")
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("Icon")
    )
    
    # Timing
    estimated_duration_seconds = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Est. Duration (s)")
    )
    
    # Flags
    is_required = models.BooleanField(
        default=True,
        verbose_name=_("Required"),
        help_text=_("Can this phase be skipped?")
    )
    allows_parallel = models.BooleanField(
        default=False,
        verbose_name=_("Allows Parallel"),
        help_text=_("Can actions in this phase run in parallel?")
    )
    
    class Meta:
        verbose_name = _("Phase")
        verbose_name_plural = _("Phases")
        ordering = ['domain', 'order']
        unique_together = ['domain', 'name']
        indexes = [
            models.Index(fields=['domain', 'order']),
        ]
    
    def __str__(self):
        return f"{self.domain.domain_id}: {self.display_name}"


# =============================================================================
# HANDLER MODEL
# =============================================================================

class HandlerType(models.TextChoices):
    """Typ eines Handlers."""
    AI_POWERED = 'ai_powered', _('AI-Powered')
    RULE_BASED = 'rule_based', _('Rule-Based')
    HYBRID = 'hybrid', _('Hybrid')
    UTILITY = 'utility', _('Utility')


class AIProvider(models.TextChoices):
    """Verfügbare AI Provider."""
    OPENAI = 'openai', _('OpenAI')
    ANTHROPIC = 'anthropic', _('Anthropic')
    OLLAMA = 'ollama', _('Ollama (Local)')
    STABILITY = 'stability', _('Stability AI')
    TESSERACT = 'tesseract', _('Tesseract OCR')
    NONE = 'none', _('None')


class Handler(AuditModel, SoftDeleteModel):
    """
    Handler im BF Agent System.
    
    Repräsentiert eine einzelne Verarbeitungseinheit
    mit definiertem Input/Output Schema.
    """
    
    # Relations
    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        related_name='handlers',
        verbose_name=_("Domain")
    )
    phase = models.ForeignKey(
        Phase,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='handlers',
        verbose_name=_("Phase"),
        help_text=_("Primary phase this handler belongs to")
    )
    
    # Identification
    name = models.CharField(
        max_length=100,
        verbose_name=_("Name"),
        help_text=_("Handler class name (PascalCase)")
    )
    description = models.TextField(
        verbose_name=_("Description")
    )
    
    # Type & Provider
    handler_type = models.CharField(
        max_length=20,
        choices=HandlerType.choices,
        default=HandlerType.RULE_BASED,
        verbose_name=_("Handler Type"),
        db_index=True
    )
    ai_provider = models.CharField(
        max_length=20,
        choices=AIProvider.choices,
        default=AIProvider.NONE,
        verbose_name=_("AI Provider")
    )
    
    # Schemas (JSON für Flexibilität)
    input_schema = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Input Schema"),
        help_text=_("Pydantic schema definition")
    )
    output_schema = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Output Schema")
    )
    
    # Performance
    estimated_duration_seconds = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Est. Duration (s)")
    )
    
    # Versioning
    version = models.CharField(
        max_length=20,
        default="1.0.0",
        verbose_name=_("Version")
    )
    
    # Source (optional: für Code-Anzeige)
    source_path = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Source Path"),
        help_text=_("Path to handler source file")
    )
    
    # Configuration
    config = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Configuration")
    )
    
    # Tags (M:N)
    tags = models.ManyToManyField(
        Tag,
        through='HandlerTag',
        related_name='handlers',
        blank=True,
        verbose_name=_("Tags")
    )
    
    class Meta:
        verbose_name = _("Handler")
        verbose_name_plural = _("Handlers")
        ordering = ['domain', 'name']
        unique_together = ['domain', 'name']
        indexes = [
            models.Index(fields=['domain', 'handler_type']),
            models.Index(fields=['handler_type', 'is_active']),
            models.Index(fields=['ai_provider']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.domain.domain_id})"
    
    @property
    def is_ai_powered(self) -> bool:
        return self.ai_provider != AIProvider.NONE


# =============================================================================
# HANDLER-TAG JUNCTION TABLE
# =============================================================================

class HandlerTag(TimeStampedModel):
    """
    Junction Table für Handler ↔ Tag (M:N).
    """
    
    handler = models.ForeignKey(
        Handler,
        on_delete=models.CASCADE,
        verbose_name=_("Handler")
    )
    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        verbose_name=_("Tag")
    )
    order = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_("Order")
    )
    
    class Meta:
        verbose_name = _("Handler Tag")
        verbose_name_plural = _("Handler Tags")
        unique_together = ['handler', 'tag']
        ordering = ['order']


# =============================================================================
# BEST PRACTICE MODEL
# =============================================================================

class BestPractice(AuditModel):
    """
    Best Practice Dokumentation.
    
    Speichert Best Practices für verschiedene Topics.
    """
    
    topic = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_("Topic"),
        help_text=_("Topic identifier (e.g., 'handlers', 'pydantic')")
    )
    display_name = models.CharField(
        max_length=100,
        verbose_name=_("Display Name")
    )
    content = models.TextField(
        verbose_name=_("Content"),
        help_text=_("Markdown formatted content")
    )
    order = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_("Order")
    )
    
    # Related Topics (Self-referential M:N)
    related_topics = models.ManyToManyField(
        'self',
        blank=True,
        symmetrical=True,
        verbose_name=_("Related Topics")
    )
    
    class Meta:
        verbose_name = _("Best Practice")
        verbose_name_plural = _("Best Practices")
        ordering = ['order', 'topic']
    
    def __str__(self):
        return self.display_name


# =============================================================================
# PROMPT TEMPLATE MODEL
# =============================================================================

class PromptTemplate(AuditModel, SoftDeleteModel):
    """
    Prompt Template für AI-gestützte Code-Generierung.
    
    Zero-Hardcoding: Prompts in DB statt im Code.
    """
    
    # Optional Domain-Zuordnung
    domain = models.ForeignKey(
        Domain,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prompt_templates',
        verbose_name=_("Domain"),
        help_text=_("Domain-specific template, or null for global")
    )
    
    # Identification
    name = models.CharField(
        max_length=100,
        verbose_name=_("Name"),
        help_text=_("Template identifier")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description")
    )
    
    # Template Content
    system_prompt = models.TextField(
        verbose_name=_("System Prompt")
    )
    user_prompt_template = models.TextField(
        verbose_name=_("User Prompt Template"),
        help_text=_("Use {variable} for placeholders")
    )
    
    # Configuration
    ai_provider = models.CharField(
        max_length=20,
        choices=AIProvider.choices,
        default=AIProvider.OPENAI,
        verbose_name=_("AI Provider")
    )
    model_name = models.CharField(
        max_length=50,
        default="gpt-4",
        verbose_name=_("Model Name")
    )
    temperature = models.FloatField(
        default=0.7,
        verbose_name=_("Temperature")
    )
    max_tokens = models.PositiveIntegerField(
        default=4000,
        verbose_name=_("Max Tokens")
    )
    
    # Versioning
    version = models.CharField(
        max_length=20,
        default="1.0.0",
        verbose_name=_("Version")
    )
    
    class Meta:
        verbose_name = _("Prompt Template")
        verbose_name_plural = _("Prompt Templates")
        unique_together = ['domain', 'name', 'version']
        ordering = ['domain', 'name']
    
    def __str__(self):
        domain_prefix = self.domain.domain_id if self.domain else "global"
        return f"{domain_prefix}/{self.name} v{self.version}"


# =============================================================================
# USAGE STATISTICS MODEL
# =============================================================================

class HandlerExecution(TimeStampedModel):
    """
    Statistik über Handler-Ausführungen.
    
    Für Performance-Monitoring und Optimierung.
    """
    
    handler = models.ForeignKey(
        Handler,
        on_delete=models.CASCADE,
        related_name='executions',
        verbose_name=_("Handler")
    )
    
    # Timing
    started_at = models.DateTimeField(
        verbose_name=_("Started At")
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Completed At")
    )
    duration_ms = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Duration (ms)")
    )
    
    # Result
    success = models.BooleanField(
        default=True,
        verbose_name=_("Success"),
        db_index=True
    )
    error_message = models.TextField(
        blank=True,
        verbose_name=_("Error Message")
    )
    
    # Cost (for AI handlers)
    tokens_used = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Tokens Used")
    )
    cost_usd = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        default=0,
        verbose_name=_("Cost (USD)")
    )
    
    class Meta:
        verbose_name = _("Handler Execution")
        verbose_name_plural = _("Handler Executions")
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['handler', 'success']),
            models.Index(fields=['started_at']),
        ]


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Base Models
    "TimeStampedModel",
    "AuditModel",
    "SoftDeleteModel",
    # Tag
    "Tag",
    "TagCategory",
    # Domain
    "Domain",
    "DomainStatus",
    "DomainTag",
    # Phase
    "Phase",
    # Handler
    "Handler",
    "HandlerType",
    "AIProvider",
    "HandlerTag",
    # Best Practice
    "BestPractice",
    # Prompt
    "PromptTemplate",
    # Statistics
    "HandlerExecution",
]
