"""
Weltenhub Scene Models
======================

Scene management with templates for story generation.
Scenes are the building blocks of stories.

Tables:
    - wh_scene_template: Reusable scene templates
    - wh_scene: Individual scenes in stories
    - wh_scene_beat: Beats within a scene
    - wh_scene_connection: Connections between scenes
"""

from django.db import models

from apps.core.models import TenantAwareModel


class SceneTemplate(TenantAwareModel):
    """
    Reusable scene template for story generation.

    Templates provide structure for common scene types
    (e.g., "Airport Departure", "Train Journey", "City Arrival").
    """

    name = models.CharField(
        max_length=200,
        help_text="Template name"
    )
    slug = models.SlugField(
        max_length=200,
        help_text="URL-safe identifier"
    )
    scene_type = models.ForeignKey(
        "lookups.SceneType",
        on_delete=models.PROTECT,
        related_name="templates",
        help_text="Type of scene (action, dialogue, travel, etc.)"
    )
    genre = models.ForeignKey(
        "lookups.Genre",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scene_templates",
        help_text="Genre this template is suited for"
    )
    transport_type = models.ForeignKey(
        "lookups.TransportType",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scene_templates",
        help_text="Transport type (for travel scenes)"
    )
    description = models.TextField(
        help_text="Template description and usage"
    )
    prompt_template = models.TextField(
        blank=True,
        help_text="LLM prompt template with {placeholders}"
    )
    description_variant_1 = models.TextField(
        blank=True,
        help_text="Scene description variant 1 (short)"
    )
    description_variant_2 = models.TextField(
        blank=True,
        help_text="Scene description variant 2 (medium)"
    )
    description_variant_3 = models.TextField(
        blank=True,
        help_text="Scene description variant 3 (detailed)"
    )
    description_variant_4 = models.TextField(
        blank=True,
        help_text="Scene description variant 4 (dramatic)"
    )
    description_variant_5 = models.TextField(
        blank=True,
        help_text="Scene description variant 5 (romantic)"
    )
    mood_tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Applicable moods: ['tense', 'romantic', 'mysterious']"
    )
    typical_duration_minutes = models.IntegerField(
        default=10,
        help_text="Typical scene duration in story time"
    )
    typical_word_count = models.IntegerField(
        default=1500,
        help_text="Typical word count for this scene type"
    )
    required_elements = models.JSONField(
        default=list,
        blank=True,
        help_text="Required story elements: ['protagonist', 'conflict']"
    )
    is_public = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Available to all tenants"
    )
    is_system = models.BooleanField(
        default=False,
        help_text="System-provided template (not editable)"
    )
    order = models.IntegerField(
        default=0,
        help_text="Display order"
    )

    class Meta:
        db_table = "wh_scene_template"
        verbose_name = "Scene Template"
        verbose_name_plural = "Scene Templates"
        ordering = ["scene_type", "order", "name"]
        indexes = [
            models.Index(fields=["scene_type"]),
            models.Index(fields=["genre"]),
            models.Index(fields=["transport_type"]),
            models.Index(fields=["is_public"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "slug"],
                name="unique_scene_template_slug"
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.scene_type})"

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_description_for_mood(self, mood_code: str) -> str:
        """Return appropriate description variant for mood."""
        mood_mapping = {
            "tense": self.description_variant_4,
            "romantic": self.description_variant_5,
            "mysterious": self.description_variant_3,
            "hopeful": self.description_variant_2,
        }
        return mood_mapping.get(mood_code, self.description_variant_1) or self.description


class Scene(TenantAwareModel):
    """
    A scene in a story.

    Scenes are the building blocks of chapters and stories.
    """

    story = models.ForeignKey(
        "stories.Story",
        on_delete=models.CASCADE,
        related_name="scenes",
        help_text="Story this scene belongs to"
    )
    chapter = models.ForeignKey(
        "stories.Chapter",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="scenes",
        help_text="Chapter this scene is in"
    )
    template = models.ForeignKey(
        SceneTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scenes",
        help_text="Template used to generate this scene"
    )
    title = models.CharField(
        max_length=200,
        help_text="Scene title"
    )
    summary = models.TextField(
        blank=True,
        help_text="Brief summary of what happens"
    )
    content = models.TextField(
        blank=True,
        help_text="Full written content of the scene"
    )
    from_location = models.ForeignKey(
        "locations.Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scenes_from",
        help_text="Starting location (for travel scenes)"
    )
    to_location = models.ForeignKey(
        "locations.Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scenes_to",
        help_text="Ending location"
    )
    location = models.ForeignKey(
        "locations.Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scenes",
        help_text="Primary scene location"
    )
    pov_character = models.ForeignKey(
        "characters.Character",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pov_scenes",
        help_text="Point of view character"
    )
    characters = models.ManyToManyField(
        "characters.Character",
        blank=True,
        related_name="scenes",
        help_text="Characters present in this scene"
    )
    mood = models.ForeignKey(
        "lookups.Mood",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scenes",
        help_text="Emotional mood of the scene"
    )
    conflict_level = models.ForeignKey(
        "lookups.ConflictLevel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scenes",
        help_text="Conflict intensity"
    )
    story_datetime = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this happens in story time"
    )
    story_date_description = models.CharField(
        max_length=200,
        blank=True,
        help_text="Human-readable time (e.g., 'Three days later')"
    )
    goal = models.TextField(
        blank=True,
        help_text="What should this scene accomplish?"
    )
    disaster = models.TextField(
        blank=True,
        help_text="What goes wrong? (Scene method)"
    )
    order = models.IntegerField(
        default=0,
        help_text="Order within chapter"
    )
    word_count_target = models.IntegerField(
        default=1500,
        help_text="Target word count"
    )
    word_count_actual = models.IntegerField(
        default=0,
        help_text="Actual word count"
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("idea", "Idea"),
            ("outlined", "Outlined"),
            ("drafted", "Drafted"),
            ("revised", "Revised"),
            ("final", "Final"),
        ],
        default="idea",
        help_text="Writing status"
    )
    is_auto_generated = models.BooleanField(
        default=False,
        help_text="Was this scene auto-generated?"
    )
    generation_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="LLM generation metadata"
    )
    notes = models.TextField(
        blank=True,
        help_text="Internal notes"
    )

    class Meta:
        db_table = "wh_scene"
        verbose_name = "Scene"
        verbose_name_plural = "Scenes"
        ordering = ["story", "chapter", "order"]
        indexes = [
            models.Index(fields=["story", "chapter", "order"]),
            models.Index(fields=["pov_character"]),
            models.Index(fields=["status"]),
            models.Index(fields=["is_auto_generated"]),
        ]

    def __str__(self):
        return f"{self.story.title} - {self.title}"

    def calculate_word_count(self) -> int:
        """Calculate and update actual word count."""
        if self.content:
            self.word_count_actual = len(self.content.split())
            self.save(update_fields=["word_count_actual"])
        return self.word_count_actual


class SceneBeat(TenantAwareModel):
    """
    A beat within a scene.

    Beats are the smallest unit of story - a single moment or action.
    """

    scene = models.ForeignKey(
        Scene,
        on_delete=models.CASCADE,
        related_name="beats",
        help_text="Scene this beat belongs to"
    )
    beat_type = models.CharField(
        max_length=50,
        choices=[
            ("action", "Action"),
            ("dialogue", "Dialogue"),
            ("description", "Description"),
            ("revelation", "Revelation"),
            ("decision", "Decision"),
            ("reaction", "Reaction"),
            ("transition", "Transition"),
        ],
        default="action",
        help_text="Type of beat"
    )
    description = models.TextField(
        help_text="What happens in this beat"
    )
    order = models.IntegerField(
        default=0,
        help_text="Order within scene"
    )
    notes = models.TextField(
        blank=True,
        help_text="Internal notes"
    )

    class Meta:
        db_table = "wh_scene_beat"
        verbose_name = "Scene Beat"
        verbose_name_plural = "Scene Beats"
        ordering = ["scene", "order"]

    def __str__(self):
        return f"Beat {self.order}: {self.description[:50]}"


class SceneConnection(TenantAwareModel):
    """
    Connection between two scenes.

    Tracks narrative connections (foreshadowing, callback, etc.).
    """

    from_scene = models.ForeignKey(
        Scene,
        on_delete=models.CASCADE,
        related_name="connections_from",
        help_text="Source scene"
    )
    to_scene = models.ForeignKey(
        Scene,
        on_delete=models.CASCADE,
        related_name="connections_to",
        help_text="Target scene"
    )
    connection_type = models.CharField(
        max_length=50,
        choices=[
            ("foreshadowing", "Foreshadowing"),
            ("callback", "Callback"),
            ("parallel", "Parallel"),
            ("contrast", "Contrast"),
            ("continuation", "Continuation"),
            ("flashback", "Flashback"),
            ("flashforward", "Flash Forward"),
        ],
        help_text="Type of connection"
    )
    description = models.TextField(
        blank=True,
        help_text="Details about this connection"
    )

    class Meta:
        db_table = "wh_scene_connection"
        verbose_name = "Scene Connection"
        verbose_name_plural = "Scene Connections"
        ordering = ["from_scene", "to_scene"]
        constraints = [
            models.UniqueConstraint(
                fields=["from_scene", "to_scene", "connection_type"],
                name="unique_scene_connection"
            )
        ]

    def __str__(self):
        return f"{self.from_scene.title} -> {self.to_scene.title}"
