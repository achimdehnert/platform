"""
Location Models - 3-Layer Architecture

Layer 1: BaseLocation - Shared factual data (coordinates, language, climate)
Layer 2: LocationLayer - Genre-specific overlays (romance spots, thriller locations)
Layer 3: UserWorld - Personal places and exclusions (see worlds app)
"""

from django.db import models
from django.contrib.postgres.fields import ArrayField


class BaseLocation(models.Model):
    """
    Layer 1: Shared Base Location Data
    
    Einmal generiert, für alle User nutzbar.
    Faktische Informationen über einen Ort.
    """
    
    class LocationType(models.TextChoices):
        CITY = 'city', 'Stadt'
        REGION = 'region', 'Region'
        COUNTRY = 'country', 'Land'
        LANDMARK = 'landmark', 'Sehenswürdigkeit'
    
    # Identifikation
    name = models.CharField(max_length=200)
    name_local = models.CharField(max_length=200, blank=True)
    location_type = models.CharField(
        max_length=20,
        choices=LocationType.choices,
        default=LocationType.CITY,
    )
    
    # Geografie
    country = models.CharField(max_length=100)
    country_code = models.CharField(max_length=3)
    region = models.CharField(max_length=100, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Kultur & Sprache
    primary_language = models.CharField(max_length=50)
    languages = ArrayField(
        models.CharField(max_length=50),
        default=list,
        blank=True,
    )
    currency = models.CharField(max_length=10, blank=True)
    
    # Beschreibung (generiert)
    description = models.TextField(blank=True)
    notable_features = ArrayField(
        models.CharField(max_length=200),
        default=list,
        blank=True,
    )
    
    # Viertel/Bezirke
    districts = models.JSONField(default=list, blank=True)
    
    # Klima
    climate_type = models.CharField(max_length=50, blank=True)
    best_seasons = ArrayField(
        models.CharField(max_length=20),
        default=list,
        blank=True,
    )
    
    # Meta
    generated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    generation_model = models.CharField(max_length=50, blank=True)
    
    class Meta:
        verbose_name = 'Base Location'
        verbose_name_plural = 'Base Locations'
        unique_together = ['name', 'country']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['country']),
        ]
    
    def __str__(self):
        return f"{self.name}, {self.country}"


class LocationLayer(models.Model):
    """
    Layer 2: Genre-Specific Location Data
    
    Erweitert BaseLocation um genre-spezifische Details.
    Shared für alle User mit gleichem Genre.
    """
    
    class Genre(models.TextChoices):
        ROMANCE = 'romance', 'Romance'
        THRILLER = 'thriller', 'Thriller'
        MYSTERY = 'mystery', 'Mystery'
        ROMANTIC_SUSPENSE = 'romantic_suspense', 'Romantic Suspense'
        COZY_MYSTERY = 'cozy_mystery', 'Cozy Mystery'
        FANTASY = 'fantasy', 'Fantasy'
        FOODIE = 'foodie', 'Foodie/Culinary'
        ADVENTURE = 'adventure', 'Adventure'
    
    # Beziehung
    base_location = models.ForeignKey(
        BaseLocation,
        on_delete=models.CASCADE,
        related_name='layers',
    )
    genre = models.CharField(
        max_length=30,
        choices=Genre.choices,
    )
    
    # Atmosphäre
    atmosphere = models.TextField(
        blank=True,
        help_text='Genre-spezifische Atmosphärenbeschreibung',
    )
    mood_keywords = ArrayField(
        models.CharField(max_length=50),
        default=list,
        blank=True,
    )
    
    # Sensorische Details
    sensory_details = models.JSONField(
        default=dict,
        blank=True,
        help_text='{"sight": [...], "sound": [...], "smell": [...], "taste": [...]}',
    )
    
    # Orte für dieses Genre
    key_locations = models.JSONField(
        default=list,
        blank=True,
        help_text='Liste von Orten ideal für dieses Genre',
    )
    
    # Story-Hooks
    story_hooks = ArrayField(
        models.TextField(),
        default=list,
        blank=True,
        help_text='Potentielle Plot-Elemente',
    )
    
    # Charaktertypen
    typical_characters = models.JSONField(
        default=list,
        blank=True,
        help_text='Typische Charaktere für dieses Genre an diesem Ort',
    )
    
    # Konfliktpotential
    conflict_opportunities = ArrayField(
        models.TextField(),
        default=list,
        blank=True,
    )
    
    # Meta
    generated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Location Layer'
        verbose_name_plural = 'Location Layers'
        unique_together = ['base_location', 'genre']
    
    def __str__(self):
        return f"{self.base_location.name} ({self.get_genre_display()})"


class ResearchCache(models.Model):
    """
    Cache für LLM-generierte Rohdaten.
    TTL-basiert, wird nach 30 Tagen invalidiert.
    """
    
    cache_key = models.CharField(max_length=255, unique=True)
    data = models.JSONField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    # Tracking
    hit_count = models.PositiveIntegerField(default=0)
    last_hit = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Research Cache'
        verbose_name_plural = 'Research Cache'
        indexes = [
            models.Index(fields=['cache_key']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return self.cache_key
    
    @property
    def is_valid(self) -> bool:
        from django.utils import timezone
        return self.expires_at > timezone.now()
