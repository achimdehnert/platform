"""
User World Models - Layer 3: Personal Customization

Enables:
- Story continuity across multiple trips/stories
- Personal places (favorites, exclusions)
- Recurring characters
- Location memories from past stories
"""

from django.db import models
from django.conf import settings


class UserWorld(models.Model):
    """
    User's personal story universe.
    All stories of a user can share characters and memories.
    """
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='world',
    )
    
    # Universe Name
    name = models.CharField(
        max_length=200,
        default='Mein Story-Universum',
        help_text='Name deines Story-Universums',
    )
    description = models.TextField(
        blank=True,
        help_text='Beschreibung deines Universums',
    )
    
    # Default Preferences
    default_genre = models.CharField(max_length=30, blank=True)
    default_spice_level = models.CharField(max_length=20, default='mild')
    
    # Global Exclusions (topics to always avoid)
    global_triggers_avoid = models.JSONField(
        default=list,
        blank=True,
        help_text='Themen die immer vermieden werden',
    )
    
    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User World'
        verbose_name_plural = 'User Worlds'
    
    def __str__(self):
        return f"{self.user}'s World: {self.name}"
    
    @classmethod
    def get_or_create_for_user(cls, user):
        """Get or create UserWorld for a user."""
        world, created = cls.objects.get_or_create(user=user)
        return world


class Character(models.Model):
    """
    A recurring character in the user's story universe.
    Can appear across multiple stories.
    """
    
    class Role(models.TextChoices):
        PROTAGONIST = 'protagonist', 'Protagonist'
        LOVE_INTEREST = 'love_interest', 'Love Interest'
        ANTAGONIST = 'antagonist', 'Antagonist'
        SIDEKICK = 'sidekick', 'Sidekick'
        MENTOR = 'mentor', 'Mentor'
        FRIEND = 'friend', 'Freund/in'
        FAMILY = 'family', 'Familie'
        OTHER = 'other', 'Andere'
    
    class Gender(models.TextChoices):
        MALE = 'male', 'Männlich'
        FEMALE = 'female', 'Weiblich'
        NON_BINARY = 'non_binary', 'Non-Binary'
        OTHER = 'other', 'Andere'
    
    # Beziehung
    user_world = models.ForeignKey(
        UserWorld,
        on_delete=models.CASCADE,
        related_name='characters',
    )
    
    # Basis-Info
    name = models.CharField(max_length=100)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.PROTAGONIST,
    )
    gender = models.CharField(
        max_length=20,
        choices=Gender.choices,
        default=Gender.FEMALE,
    )
    age = models.PositiveIntegerField(null=True, blank=True)
    
    # Beschreibung
    appearance = models.TextField(blank=True, help_text='Äußeres Erscheinungsbild')
    personality = models.TextField(blank=True, help_text='Persönlichkeit')
    background = models.TextField(blank=True, help_text='Hintergrundgeschichte')
    
    # Beziehungen zu anderen Charakteren
    relationships = models.JSONField(
        default=dict,
        blank=True,
        help_text='{"character_id": "relationship_type"}',
    )
    
    # Story-Tracking
    introduced_in = models.ForeignKey(
        'stories.Story',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='introduced_characters',
    )
    current_status = models.CharField(max_length=200, blank=True)
    
    # Aktiv?
    is_active = models.BooleanField(default=True)
    
    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Charakter'
        verbose_name_plural = 'Charaktere'
        ordering = ['role', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_role_display()})"


class PersonalPlace(models.Model):
    """
    A personal place the user wants to include or exclude.
    Layer 3 overlay on top of BaseLocation/LocationLayer.
    """
    
    class PlaceType(models.TextChoices):
        INCLUDE = 'include', 'In Stories verwenden'
        EXCLUDE = 'exclude', 'NICHT verwenden'
        FAVORITE = 'favorite', 'Favorit (bevorzugt)'
    
    # Beziehung
    user_world = models.ForeignKey(
        UserWorld,
        on_delete=models.CASCADE,
        related_name='personal_places',
    )
    
    # Location
    name = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    
    # Optional: Link to BaseLocation
    base_location = models.ForeignKey(
        'locations.BaseLocation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    
    # Typ
    place_type = models.CharField(
        max_length=20,
        choices=PlaceType.choices,
        default=PlaceType.INCLUDE,
    )
    
    # Details
    description = models.TextField(
        blank=True,
        help_text='Warum ist dieser Ort besonders?',
    )
    personal_memory = models.TextField(
        blank=True,
        help_text='Persönliche Erinnerung (nur für dich sichtbar)',
    )
    
    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Persönlicher Ort'
        verbose_name_plural = 'Persönliche Orte'
        ordering = ['city', 'name']
    
    def __str__(self):
        status = "✅" if self.place_type != 'exclude' else "❌"
        return f"{status} {self.name}, {self.city}"


class LocationMemory(models.Model):
    """
    Memory of what happened at a location in a user's stories.
    Enables story continuity and references to past events.
    """
    
    # Beziehung
    user_world = models.ForeignKey(
        UserWorld,
        on_delete=models.CASCADE,
        related_name='location_memories',
    )
    base_location = models.ForeignKey(
        'locations.BaseLocation',
        on_delete=models.CASCADE,
        related_name='user_memories',
    )
    
    # Story-Kontext
    story = models.ForeignKey(
        'stories.Story',
        on_delete=models.CASCADE,
        related_name='location_memories',
    )
    chapter = models.ForeignKey(
        'stories.Chapter',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    
    # Memory Content
    summary = models.TextField(help_text='Was ist hier passiert?')
    characters_involved = models.ManyToManyField(
        Character,
        blank=True,
        related_name='location_memories',
    )
    emotional_significance = models.CharField(
        max_length=50,
        blank=True,
        help_text='emotional tag: romantic, tragic, funny, etc.',
    )
    
    # Für Referenzen
    can_reference = models.BooleanField(
        default=True,
        help_text='Kann in zukünftigen Stories referenziert werden',
    )
    
    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Location Memory'
        verbose_name_plural = 'Location Memories'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.base_location.name}: {self.summary[:50]}..."
