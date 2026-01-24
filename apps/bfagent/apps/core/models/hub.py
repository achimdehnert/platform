"""
Hub Model - Database-driven Hub Management

Stores hub manifests in database for dynamic configuration.
Supports the Zero-Hardcoding philosophy of BF Agent.

Links to NavigationSection for automatic sidebar management.
"""

from django.db import models
from django.core.validators import RegexValidator


class HubStatus(models.TextChoices):
    """Status eines Hubs."""
    PRODUCTION = "production", "Production"
    BETA = "beta", "Beta"
    DEVELOPMENT = "development", "Development"
    DEPRECATED = "deprecated", "Deprecated"
    DISABLED = "disabled", "Disabled"


class HubCategory(models.TextChoices):
    """Kategorie eines Hubs."""
    CONTENT = "content", "Content"
    ENGINEERING = "engineering", "Engineering"
    SYSTEM = "system", "System"
    RESEARCH = "research", "Research"
    OTHER = "other", "Other"


class Hub(models.Model):
    """
    Hub-Manifest in der Datenbank.
    
    Ermöglicht dynamische Hub-Konfiguration ohne Code-Änderungen.
    Verknüpft mit NavigationSection für automatische Sidebar-Verwaltung.
    """
    # Identifikation
    hub_id = models.CharField(
        max_length=50,
        unique=True,
        validators=[RegexValidator(r'^[a-z][a-z0-9_]*$', 'Lowercase letters, numbers, underscores')],
        help_text="Eindeutige Hub-ID (z.B. 'writing_hub')"
    )
    name = models.CharField(max_length=100, help_text="Anzeigename des Hubs")
    
    # Metadaten
    version = models.CharField(max_length=20, default="1.0.0")
    description = models.TextField(blank=True, default="")
    author = models.CharField(max_length=100, default="BF Agent Team")
    
    # Klassifizierung
    status = models.CharField(
        max_length=20,
        choices=HubStatus.choices,
        default=HubStatus.PRODUCTION
    )
    category = models.CharField(
        max_length=20,
        choices=HubCategory.choices,
        default=HubCategory.OTHER
    )
    icon = models.CharField(max_length=50, default="bi-puzzle", help_text="Bootstrap Icon class")
    
    # Navigation Link - Verknüpfung mit Sidebar
    navigation_section = models.OneToOneField(
        'control_center.NavigationSection',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hub',
        help_text="Verknüpfte NavigationSection für Sidebar"
    )
    
    # Technische Konfiguration
    entry_point = models.CharField(
        max_length=100,
        blank=True,
        help_text="Python module path (z.B. 'apps.writing_hub')"
    )
    dependencies = models.JSONField(
        default=list,
        blank=True,
        help_text="Liste der Hub-IDs von denen dieser Hub abhängt"
    )
    provides = models.JSONField(
        default=list,
        blank=True,
        help_text="Was der Hub bereitstellt: views, models, handlers, api"
    )
    
    # Hub-spezifische Einstellungen
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Hub-spezifische Konfiguration als JSON"
    )
    config_schema = models.JSONField(
        default=dict,
        blank=True,
        help_text="JSON Schema für config Validierung"
    )
    
    # Status
    is_active = models.BooleanField(default=True, help_text="Hub ist aktiviert")
    is_installed = models.BooleanField(default=True, help_text="Hub-Code ist vorhanden")
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "core_hubs"
        verbose_name = "Hub"
        verbose_name_plural = "Hubs"
        ordering = ["category", "name"]
    
    def __str__(self):
        return f"{self.name} ({self.hub_id})"
    
    def save(self, *args, **kwargs):
        # Auto-generate entry_point if not set
        if not self.entry_point:
            self.entry_point = f"apps.{self.hub_id}"
        
        # Default provides
        if not self.provides:
            self.provides = ["views", "models"]
        
        # Sync navigation section active state
        if self.navigation_section:
            if self.navigation_section.is_active != self.is_active:
                self.navigation_section.is_active = self.is_active
                self.navigation_section.save(update_fields=['is_active'])
        
        super().save(*args, **kwargs)
    
    def get_navigation_items(self):
        """Get all navigation items for this hub."""
        if self.navigation_section:
            return self.navigation_section.items.filter(is_active=True)
        return []
    
    def to_manifest_dict(self) -> dict:
        """Convert to dictionary format for HubRegistry compatibility."""
        return {
            "id": self.hub_id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "status": self.status,
            "category": self.category,
            "icon": self.icon,
            "entry_point": self.entry_point,
            "dependencies": self.dependencies or [],
            "provides": self.provides or [],
            "config": self.config or {},
            "config_schema": self.config_schema or {},
            "is_active": self.is_active,
            "navigation_section_id": self.navigation_section_id,
        }
    
    @classmethod
    def get_active_hubs(cls):
        """Get all active hubs."""
        return cls.objects.filter(is_active=True, is_installed=True)
    
    @classmethod
    def get_by_category(cls, category: str):
        """Get hubs by category."""
        return cls.objects.filter(category=category, is_active=True)
