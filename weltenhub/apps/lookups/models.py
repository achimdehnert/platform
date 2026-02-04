"""
Weltenhub Lookup Models
=======================

Database-driven lookup tables for all choices.
NO ENUMS - everything from database for flexibility.

Tables:
    - lkp_genre: Story genres
    - lkp_mood: Emotional tones/moods
    - lkp_conflict_level: Conflict intensity levels
    - lkp_location_type: Types of locations
    - lkp_scene_type: Types of scenes
    - lkp_character_role: Character roles in stories
"""

from django.db import models


class BaseLookup(models.Model):
    """
    Abstract base for all lookup tables.

    Provides consistent structure:
    - code: Machine-readable identifier
    - name/name_de: Display names (EN/DE)
    - order: Sort order
    - is_active: Soft enable/disable
    """

    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Machine-readable code (e.g., 'fantasy', 'tense')"
    )
    name = models.CharField(
        max_length=100,
        help_text="English display name"
    )
    name_de = models.CharField(
        max_length=100,
        blank=True,
        help_text="German display name"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of this option"
    )
    order = models.IntegerField(
        default=0,
        db_index=True,
        help_text="Display order (lower = first)"
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this option is available"
    )

    class Meta:
        abstract = True
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Genre(BaseLookup):
    """Story genres (Fantasy, SciFi, Romance, etc.)."""

    color = models.CharField(
        max_length=7,
        default="#3498db",
        help_text="Color for UI (hex)"
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text="Icon class (e.g., 'bi-book')"
    )

    class Meta:
        db_table = "lkp_genre"
        verbose_name = "Genre"
        verbose_name_plural = "Genres"
        ordering = ["order", "name"]


class Mood(BaseLookup):
    """Emotional tones/moods for scenes."""

    color = models.CharField(
        max_length=7,
        default="#95a5a6",
        help_text="Color for visualization (hex)"
    )
    intensity = models.IntegerField(
        default=5,
        help_text="Intensity level 1-10"
    )

    class Meta:
        db_table = "lkp_mood"
        verbose_name = "Mood"
        verbose_name_plural = "Moods"
        ordering = ["order", "name"]


class ConflictLevel(BaseLookup):
    """Conflict intensity levels for pacing analysis."""

    intensity = models.IntegerField(
        default=0,
        help_text="Numeric intensity 0-10"
    )
    color = models.CharField(
        max_length=7,
        default="#95a5a6",
        help_text="Color for visualization (hex)"
    )

    class Meta:
        db_table = "lkp_conflict_level"
        verbose_name = "Conflict Level"
        verbose_name_plural = "Conflict Levels"
        ordering = ["intensity"]


class LocationType(BaseLookup):
    """Types of locations (continent, country, city, building, etc.)."""

    parent_type = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="child_types",
        help_text="Parent location type in hierarchy"
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text="Icon class"
    )

    class Meta:
        db_table = "lkp_location_type"
        verbose_name = "Location Type"
        verbose_name_plural = "Location Types"
        ordering = ["order", "name"]


class SceneType(BaseLookup):
    """Types of scenes (action, dialogue, flashback, etc.)."""

    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text="Icon class"
    )
    color = models.CharField(
        max_length=7,
        default="#3498db",
        help_text="Color for visualization (hex)"
    )
    typical_duration_minutes = models.IntegerField(
        default=5,
        help_text="Typical duration in story time (minutes)"
    )

    class Meta:
        db_table = "lkp_scene_type"
        verbose_name = "Scene Type"
        verbose_name_plural = "Scene Types"
        ordering = ["order", "name"]


class CharacterRole(BaseLookup):
    """Character roles in stories (protagonist, antagonist, etc.)."""

    is_main = models.BooleanField(
        default=False,
        help_text="Is this a main character role?"
    )
    color = models.CharField(
        max_length=7,
        default="#3498db",
        help_text="Color for visualization (hex)"
    )

    class Meta:
        db_table = "lkp_character_role"
        verbose_name = "Character Role"
        verbose_name_plural = "Character Roles"
        ordering = ["order", "name"]


class TransportType(BaseLookup):
    """Types of transport (flight, train, car, ship, etc.)."""

    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text="Icon class (e.g., 'bi-airplane')"
    )
    typical_scene_types = models.ManyToManyField(
        SceneType,
        blank=True,
        related_name="transport_types",
        help_text="Scene types typically associated with this transport"
    )

    class Meta:
        db_table = "lkp_transport_type"
        verbose_name = "Transport Type"
        verbose_name_plural = "Transport Types"
        ordering = ["order", "name"]


class RuleCategory(BaseLookup):
    """Categories for world rules (physics, magic, social, etc.)."""

    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text="Icon class (e.g., 'bi-lightning')"
    )
    color = models.CharField(
        max_length=7,
        default="#6366f1",
        help_text="Color for visualization (hex)"
    )

    class Meta:
        db_table = "lkp_rule_category"
        verbose_name = "Rule Category"
        verbose_name_plural = "Rule Categories"
        ordering = ["order", "name"]


class RuleImportance(BaseLookup):
    """Importance levels for world rules (absolute, strong, guideline)."""

    severity = models.IntegerField(
        default=5,
        help_text="Severity level 1-10 (10 = never break)"
    )
    color = models.CharField(
        max_length=7,
        default="#ef4444",
        help_text="Color for visualization (hex)"
    )

    class Meta:
        db_table = "lkp_rule_importance"
        verbose_name = "Rule Importance"
        verbose_name_plural = "Rule Importance Levels"
        ordering = ["-severity", "name"]


class TenantRole(BaseLookup):
    """Roles for tenant users (owner, admin, editor, viewer)."""

    permission_level = models.IntegerField(
        default=0,
        help_text="Permission level 0-100 (100 = full access)"
    )
    can_manage_users = models.BooleanField(
        default=False,
        help_text="Can this role manage other users?"
    )
    can_manage_settings = models.BooleanField(
        default=False,
        help_text="Can this role manage tenant settings?"
    )

    class Meta:
        db_table = "lkp_tenant_role"
        verbose_name = "Tenant Role"
        verbose_name_plural = "Tenant Roles"
        ordering = ["-permission_level", "name"]
