"""
Weltenhub Character Models
==========================

Character management for story worlds.
Includes character arcs and relationships.

Tables:
    - wh_character: Main character entity
    - wh_character_arc: Character development arc
    - wh_character_relationship: Relationships between characters
"""

from django.db import models

from apps.core.models import TenantAwareModel


class Character(TenantAwareModel):
    """
    A character in a story world.

    Characters belong to a world and can appear in multiple stories.
    """

    world = models.ForeignKey(
        "worlds.World",
        on_delete=models.CASCADE,
        related_name="characters",
        help_text="World this character belongs to"
    )
    role = models.ForeignKey(
        "lookups.CharacterRole",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="characters",
        help_text="Character role (protagonist, antagonist, etc.)"
    )
    name = models.CharField(
        max_length=200,
        help_text="Character's name"
    )
    slug = models.SlugField(
        max_length=200,
        help_text="URL-safe identifier"
    )
    title = models.CharField(
        max_length=100,
        blank=True,
        help_text="Title or honorific (Dr., King, etc.)"
    )
    nickname = models.CharField(
        max_length=100,
        blank=True,
        help_text="Nickname or alias"
    )
    description = models.TextField(
        blank=True,
        help_text="Physical description"
    )
    personality = models.TextField(
        blank=True,
        help_text="Personality traits and behavior"
    )
    backstory = models.TextField(
        blank=True,
        help_text="Character's background and history"
    )
    motivation = models.TextField(
        blank=True,
        help_text="What drives this character?"
    )
    goals = models.TextField(
        blank=True,
        help_text="Character's goals and desires"
    )
    flaws = models.TextField(
        blank=True,
        help_text="Character flaws and weaknesses"
    )
    strengths = models.TextField(
        blank=True,
        help_text="Character strengths and abilities"
    )
    voice = models.TextField(
        blank=True,
        help_text="How the character speaks, verbal patterns"
    )
    age = models.CharField(
        max_length=50,
        blank=True,
        help_text="Age or age range"
    )
    gender = models.CharField(
        max_length=50,
        blank=True,
        help_text="Gender identity"
    )
    home_location = models.ForeignKey(
        "locations.Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="home_characters",
        help_text="Character's home location"
    )
    current_location = models.ForeignKey(
        "locations.Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_characters",
        help_text="Character's current location in story"
    )
    portrait = models.ImageField(
        upload_to="characters/portraits/",
        blank=True,
        null=True,
        help_text="Character portrait image"
    )
    is_protagonist = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Is this a main protagonist?"
    )
    is_public = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Can be used by other tenants"
    )
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Tags for filtering and search"
    )
    notes = models.TextField(
        blank=True,
        help_text="Internal notes (not shown in story)"
    )

    class Meta:
        db_table = "wh_character"
        verbose_name = "Character"
        verbose_name_plural = "Characters"
        ordering = ["-is_protagonist", "name"]
        indexes = [
            models.Index(fields=["tenant", "world"]),
            models.Index(fields=["role"]),
            models.Index(fields=["is_protagonist"]),
            models.Index(fields=["is_public"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "world", "slug"],
                name="unique_character_slug_per_world"
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.world.name})"

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class CharacterArc(TenantAwareModel):
    """
    Character development arc within a story.

    Tracks how a character changes throughout a story.
    """

    character = models.ForeignKey(
        Character,
        on_delete=models.CASCADE,
        related_name="arcs",
        help_text="Character this arc belongs to"
    )
    story = models.ForeignKey(
        "stories.Story",
        on_delete=models.CASCADE,
        related_name="character_arcs",
        help_text="Story this arc is for"
    )
    arc_type = models.CharField(
        max_length=50,
        choices=[
            ("positive", "Positive Change"),
            ("negative", "Negative Change"),
            ("flat", "Flat Arc (no change)"),
            ("fall", "Fall Arc (tragic)"),
            ("corruption", "Corruption Arc"),
            ("redemption", "Redemption Arc"),
        ],
        default="positive",
        help_text="Type of character arc"
    )
    starting_state = models.TextField(
        help_text="Character's state at story beginning"
    )
    ending_state = models.TextField(
        help_text="Character's state at story end"
    )
    key_moments = models.JSONField(
        default=list,
        blank=True,
        help_text="Key moments in the arc: [{scene_id, description}]"
    )
    internal_conflict = models.TextField(
        blank=True,
        help_text="Character's internal struggle"
    )
    external_conflict = models.TextField(
        blank=True,
        help_text="Character's external challenges"
    )
    lesson_learned = models.TextField(
        blank=True,
        help_text="What the character learns"
    )
    notes = models.TextField(
        blank=True,
        help_text="Planning notes"
    )

    class Meta:
        db_table = "wh_character_arc"
        verbose_name = "Character Arc"
        verbose_name_plural = "Character Arcs"
        ordering = ["story", "character"]
        constraints = [
            models.UniqueConstraint(
                fields=["character", "story"],
                name="unique_character_arc_per_story"
            )
        ]

    def __str__(self):
        return f"{self.character.name} arc in {self.story.title}"


class CharacterRelationship(TenantAwareModel):
    """
    Relationship between two characters.

    Bidirectional: if A is B's friend, B is A's friend.
    """

    character_a = models.ForeignKey(
        Character,
        on_delete=models.CASCADE,
        related_name="relationships_as_a",
        help_text="First character"
    )
    character_b = models.ForeignKey(
        Character,
        on_delete=models.CASCADE,
        related_name="relationships_as_b",
        help_text="Second character"
    )
    relationship_type = models.CharField(
        max_length=50,
        choices=[
            ("family", "Family"),
            ("romantic", "Romantic"),
            ("friend", "Friend"),
            ("enemy", "Enemy"),
            ("rival", "Rival"),
            ("mentor", "Mentor/Mentee"),
            ("colleague", "Colleague"),
            ("acquaintance", "Acquaintance"),
        ],
        help_text="Type of relationship"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of the relationship"
    )
    strength = models.IntegerField(
        default=5,
        help_text="Relationship strength 1-10"
    )
    is_mutual = models.BooleanField(
        default=True,
        help_text="Is the relationship mutual?"
    )
    started_at = models.CharField(
        max_length=200,
        blank=True,
        help_text="When relationship started (in story terms)"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional notes"
    )

    class Meta:
        db_table = "wh_character_relationship"
        verbose_name = "Character Relationship"
        verbose_name_plural = "Character Relationships"
        ordering = ["character_a", "character_b"]
        constraints = [
            models.UniqueConstraint(
                fields=["character_a", "character_b", "relationship_type"],
                name="unique_relationship_type"
            )
        ]

    def __str__(self):
        return f"{self.character_a.name} <-> {self.character_b.name} ({self.relationship_type})"
