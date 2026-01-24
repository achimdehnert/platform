"""
Writing Hub - World Building Models
====================================

Projektunabhängige Weltenbau-Models.

Created: 2026-01-09
Purpose: Welten können in mehreren Projekten wiederverwendet werden.
"""

import uuid
from django.db import models
from django.conf import settings


class World(models.Model):
    """
    Projektunabhängige Weltdefinition.
    
    Eine Welt gehört einem User und kann in beliebig vielen Projekten
    verwendet werden über die ProjectWorld M2M-Beziehung.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='worlds'
    )
    
    # Basis
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, blank=True)
    world_type = models.ForeignKey(
        'writing_hub.WorldType',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='worlds'
    )
    description = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to='worlds/', blank=True, null=True)
    
    # Weltenbau-Details
    setting_era = models.CharField(max_length=200, blank=True, help_text="Zeitepoche")
    geography = models.TextField(blank=True, help_text="Landschaften, Klima, Orte")
    climate = models.TextField(blank=True, help_text="Klimazonen, Wetter")
    inhabitants = models.TextField(blank=True, help_text="Völker, Rassen, Bewohner")
    culture = models.TextField(blank=True, help_text="Traditionen, Religion, Werte")
    religion = models.TextField(blank=True, help_text="Glaubenssysteme")
    technology_level = models.CharField(max_length=200, blank=True, help_text="Technologiestufe")
    magic_system = models.TextField(blank=True, help_text="Magiesystem falls vorhanden")
    politics = models.TextField(blank=True, help_text="Machtverhältnisse, Regierungsformen")
    economy = models.TextField(blank=True, help_text="Wirtschaftssystem")
    history = models.TextField(blank=True, help_text="Wichtige historische Ereignisse")
    
    # Sprache
    class Language(models.TextChoices):
        DE = 'de', '🇩🇪 Deutsch'
        EN = 'en', '🇬🇧 English'
        ES = 'es', '🇪🇸 Español'
        FR = 'fr', '🇫🇷 Français'
        IT = 'it', '🇮🇹 Italiano'
        PT = 'pt', '🇵🇹 Português'
    
    language = models.CharField(
        max_length=5,
        choices=Language.choices,
        default=Language.DE,
        help_text="Sprache der Welt-Inhalte"
    )
    
    # Metadaten
    is_public = models.BooleanField(
        default=False,
        help_text="Kann von anderen Usern adoptiert werden"
    )
    is_template = models.BooleanField(
        default=False,
        help_text="Vorlage für neue Welten"
    )
    version = models.PositiveIntegerField(default=1)
    tags = models.JSONField(
        blank=True,
        default=list,
        help_text="Tags für Suche und Filterung (Liste von Strings)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'writing_hub'
        db_table = 'writing_worlds'
        ordering = ['name']
        verbose_name = 'World'
        verbose_name_plural = 'Worlds'
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            base_slug = slugify(self.name)
            self.slug = f"{base_slug}-{str(self.id)[:8]}" if self.id else base_slug
        super().save(*args, **kwargs)
    
    @property
    def project_count(self):
        """Anzahl der Projekte, die diese Welt verwenden."""
        return self.project_links.count()


class ProjectWorld(models.Model):
    """
    M2M-Verknüpfung zwischen Projekt und Welt.
    
    Erlaubt projekt-spezifische Anpassungen ohne die Original-Welt zu ändern.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    project = models.ForeignKey(
        'bfagent.BookProjects',
        on_delete=models.CASCADE,
        related_name='world_links'
    )
    world = models.ForeignKey(
        'World',
        on_delete=models.CASCADE,
        related_name='project_links'
    )
    
    # Rolle der Welt im Projekt
    ROLE_CHOICES = [
        ('primary', 'Hauptwelt'),
        ('secondary', 'Nebenwelt'),
        ('mentioned', 'Erwähnt'),
        ('flashback', 'Rückblende'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='primary')
    
    # Projekt-spezifische Anpassungen
    custom_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Anderer Name im Projekt (optional)"
    )
    project_notes = models.TextField(
        blank=True,
        help_text="Projekt-spezifische Notizen"
    )
    timeline_offset = models.IntegerField(
        default=0,
        help_text="Jahre vor/nach Welt-Timeline"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'writing_hub'
        db_table = 'writing_project_worlds'
        unique_together = ['project', 'world']
        ordering = ['role', 'world__name']
        verbose_name = 'Project World'
        verbose_name_plural = 'Project Worlds'
    
    def __str__(self):
        name = self.custom_name or self.world.name
        return f"{name} ({self.get_role_display()}) - {self.project.title}"
    
    @property
    def display_name(self):
        """Name der Welt im Projektkontext."""
        return self.custom_name or self.world.name


class WorldLocation(models.Model):
    """
    Orte innerhalb einer Welt.
    
    Hierarchisch strukturiert (Kontinent → Land → Stadt → Gebäude).
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    world = models.ForeignKey(
        'World',
        on_delete=models.CASCADE,
        related_name='locations'
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children'
    )
    
    name = models.CharField(max_length=200)
    
    LOCATION_TYPES = [
        ('continent', 'Kontinent'),
        ('country', 'Land'),
        ('region', 'Region'),
        ('city', 'Stadt'),
        ('district', 'Stadtteil'),
        ('building', 'Gebäude'),
        ('landmark', 'Wahrzeichen'),
        ('natural', 'Naturmerkmal'),
    ]
    location_type = models.CharField(max_length=20, choices=LOCATION_TYPES, default='city')
    
    description = models.TextField(blank=True)
    significance = models.TextField(blank=True, help_text="Bedeutung für die Story")
    
    # Optionale Koordinaten für Karten
    coordinates = models.JSONField(blank=True, null=True, help_text="{'x': 0, 'y': 0} für Karten")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'writing_hub'
        db_table = 'writing_world_locations'
        ordering = ['location_type', 'name']
        verbose_name = 'World Location'
        verbose_name_plural = 'World Locations'
    
    def __str__(self):
        return f"{self.name} ({self.get_location_type_display()})"
    
    @property
    def full_path(self):
        """Vollständiger Pfad: Kontinent > Land > Stadt."""
        parts = [self.name]
        parent = self.parent
        while parent:
            parts.insert(0, parent.name)
            parent = parent.parent
        return " > ".join(parts)


class WorldRule(models.Model):
    """
    Regeln und Constraints einer Welt.
    
    Formalisiert die "Gesetze" der Welt für Konsistenz.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    world = models.ForeignKey(
        'World',
        on_delete=models.CASCADE,
        related_name='rules'
    )
    
    CATEGORY_CHOICES = [
        ('physics', 'Physik'),
        ('magic', 'Magie'),
        ('social', 'Gesellschaft'),
        ('technology', 'Technologie'),
        ('biology', 'Biologie'),
        ('economy', 'Wirtschaft'),
    ]
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='physics')
    
    rule = models.CharField(max_length=500, help_text="Die Regel selbst")
    explanation = models.TextField(blank=True, help_text="Erklärung/Begründung")
    
    IMPORTANCE_CHOICES = [
        ('absolute', 'Absolut - Nie brechen'),
        ('strong', 'Stark - Nur mit gutem Grund'),
        ('guideline', 'Richtlinie - Flexibel'),
    ]
    importance = models.CharField(max_length=20, choices=IMPORTANCE_CHOICES, default='strong')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'writing_hub'
        db_table = 'writing_world_rules'
        ordering = ['category', '-importance', 'rule']
        verbose_name = 'World Rule'
        verbose_name_plural = 'World Rules'
    
    def __str__(self):
        return f"[{self.get_category_display()}] {self.rule[:50]}..."
