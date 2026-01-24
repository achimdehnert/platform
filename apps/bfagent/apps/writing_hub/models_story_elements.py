"""
Story Elements Models
Enhanced models for detailed story planning based on story-outline-tool
Using DB-driven lookup tables instead of enums for flexibility
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

# =============================================================================
# Lookup Tables (Master Data)
# =============================================================================


class EmotionalTone(models.Model):
    """
    Emotional tone/mood of a scene
    Master data - populated via management command
    """

    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Technical code (e.g., 'hopeful', 'tense')",
    )
    name_en = models.CharField(max_length=100, help_text="English name")
    name_de = models.CharField(max_length=100, help_text="German name")
    description = models.TextField(blank=True, help_text="Description of this emotional tone")
    color = models.CharField(
        max_length=7,
        default="#3498db",
        help_text="Color for visualization (hex)",
    )
    order = models.IntegerField(default=0, help_text="Display order")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "emotional_tones"
        ordering = ["order", "name_en"]
        verbose_name = _("Emotional Tone")
        verbose_name_plural = _("Emotional Tones")

    def __str__(self):
        return self.name_en


class ConflictLevel(models.Model):
    """
    Conflict intensity level for pacing analysis
    Master data - populated via management command
    """

    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Technical code (e.g., 'none', 'low', 'medium', 'high', 'climax')",
    )
    name_en = models.CharField(max_length=100, help_text="English name")
    name_de = models.CharField(max_length=100, help_text="German name")
    description = models.TextField(blank=True, help_text="Description of this conflict level")
    intensity = models.IntegerField(
        default=0,
        help_text="Numeric intensity (0-10) for analysis",
    )
    color = models.CharField(
        max_length=7,
        default="#95a5a6",
        help_text="Color for visualization (hex)",
    )
    order = models.IntegerField(default=0, help_text="Display order")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "conflict_levels"
        ordering = ["order", "intensity"]
        verbose_name = _("Conflict Level")
        verbose_name_plural = _("Conflict Levels")

    def __str__(self):
        return self.name_en


class BeatType(models.Model):
    """
    Type of story beat (action, dialogue, description, revelation, decision, etc.)
    Master data - populated via management command
    """

    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Technical code (e.g., 'action', 'dialogue', 'revelation')",
    )
    name_en = models.CharField(max_length=100, help_text="English name")
    name_de = models.CharField(max_length=100, help_text="German name")
    description = models.TextField(blank=True, help_text="Description of this beat type")
    icon = models.CharField(max_length=50, blank=True, help_text="Icon class (e.g., 'fa-running')")
    color = models.CharField(
        max_length=7,
        default="#3498db",
        help_text="Color for visualization (hex)",
    )
    order = models.IntegerField(default=0, help_text="Display order")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "beat_types"
        ordering = ["order", "name_en"]
        verbose_name = _("Beat Type")
        verbose_name_plural = _("Beat Types")

    def __str__(self):
        return self.name_en


class SceneConnectionType(models.Model):
    """
    Type of connection between scenes (foreshadowing, callback, parallel, contrast, etc.)
    Master data - populated via management command
    """

    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Technical code (e.g., 'foreshadowing', 'callback', 'parallel')",
    )
    name_en = models.CharField(max_length=100, help_text="English name")
    name_de = models.CharField(max_length=100, help_text="German name")
    description = models.TextField(blank=True, help_text="Description of this connection type")
    icon = models.CharField(max_length=50, blank=True, help_text="Icon class")
    order = models.IntegerField(default=0, help_text="Display order")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "scene_connection_types"
        ordering = ["order", "name_en"]
        verbose_name = _("Scene Connection Type")
        verbose_name_plural = _("Scene Connection Types")

    def __str__(self):
        return self.name_en


# =============================================================================
# Story Elements (Content Data)
# =============================================================================


class Beat(models.Model):
    """
    The smallest unit of story - a single moment or action
    Part of a Scene
    """

    scene = models.ForeignKey(
        "Scene",
        on_delete=models.CASCADE,
        related_name="beats",
        help_text="Scene this beat belongs to",
    )
    beat_type = models.ForeignKey(
        BeatType,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Type of beat (action, dialogue, etc.)",
    )
    description = models.TextField(help_text="What happens in this beat")
    order = models.IntegerField(default=0, help_text="Order within scene")
    notes = models.TextField(blank=True, help_text="Internal notes")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "story_beats"
        ordering = ["scene", "order"]
        verbose_name = _("Beat")
        verbose_name_plural = _("Beats")

    def __str__(self):
        return f"Beat {self.order}: {self.description[:50]}"


class Scene(models.Model):
    """
    A scene - continuous action in one place/time
    The primary working unit for authors
    Enhanced version based on story-outline-tool
    """

    title = models.CharField(max_length=200, help_text="Scene title")
    summary = models.TextField(blank=True, help_text="Brief summary of what happens")

    chapter = models.ForeignKey(
        "bfagent.BookChapters",
        on_delete=models.CASCADE,
        related_name="scenes",
        db_column="chapter_id",
        to_field="id",
        help_text="Chapter this scene belongs to",
    )
    order = models.IntegerField(default=0, help_text="Order within chapter")

    pov_character = models.ForeignKey(
        "bfagent.Characters",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pov_scenes",
        help_text="Whose perspective is this scene from?",
    )
    characters = models.ManyToManyField(
        "bfagent.Characters",
        blank=True,
        related_name="scenes",
        help_text="Characters present in this scene",
    )

    location = models.ForeignKey(
        "Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scenes",
        help_text="Where does this scene take place?",
    )

    story_datetime = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When does this happen in the story timeline?",
    )
    story_date_description = models.CharField(
        max_length=200,
        blank=True,
        help_text="Human-readable time (e.g., 'Three days later', 'Winter 1942')",
    )

    plot_threads = models.ManyToManyField(
        "PlotThread",
        blank=True,
        related_name="scenes",
        help_text="Which plot threads are advanced in this scene?",
    )

    emotional_start = models.ForeignKey(
        EmotionalTone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scenes_starting",
        help_text="Emotional tone at scene start",
    )
    emotional_end = models.ForeignKey(
        EmotionalTone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scenes_ending",
        help_text="Emotional tone at scene end",
    )
    conflict_level = models.ForeignKey(
        ConflictLevel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Conflict intensity for pacing analysis",
    )

    goal = models.TextField(
        blank=True,
        help_text="What should this scene accomplish? (Scene method)",
    )
    disaster = models.TextField(
        blank=True,
        help_text="What goes wrong? How does it fail? (Scene method)",
    )

    word_count_target = models.IntegerField(
        default=2000,
        help_text="Target word count for this scene",
    )
    word_count_actual = models.IntegerField(
        default=0,
        help_text="Actual word count (updated when content written)",
    )

    status = models.ForeignKey(
        "writing_hub.WritingStage",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Current status (idea, outlined, drafted, revised, final)",
    )

    content = models.TextField(
        blank=True,
        help_text="Actual written content of the scene",
    )

    notes = models.TextField(blank=True, help_text="Internal notes and ideas")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "story_scenes"
        ordering = ["chapter", "order"]
        verbose_name = _("Scene")
        verbose_name_plural = _("Scenes")
        indexes = [
            models.Index(fields=["chapter", "order"]),
            models.Index(fields=["pov_character"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.chapter.title} - Scene {self.order}: {self.title}"

    def get_emotional_arc(self):
        return (
            self.emotional_start.name_en if self.emotional_start else None,
            self.emotional_end.name_en if self.emotional_end else None,
        )

    def calculate_word_count(self):
        if self.content:
            self.word_count_actual = len(self.content.split())
            self.save(update_fields=["word_count_actual"])
        return self.word_count_actual


class Location(models.Model):
    """
    A location/setting in the story
    Master data for the project
    """

    project = models.ForeignKey(
        "bfagent.BookProjects",
        on_delete=models.CASCADE,
        related_name="locations",
        db_column="project_id",
        to_field="id",
        help_text="Book project this location belongs to",
    )
    name = models.CharField(max_length=200, help_text="Location name")
    description = models.TextField(blank=True, help_text="Description of this location")
    time_period = models.CharField(
        max_length=200,
        blank=True,
        help_text="Time period (e.g., 'medieval', '2024', 'future')",
    )
    mood = models.CharField(
        max_length=200,
        blank=True,
        help_text="Overall mood/atmosphere of this location",
    )
    notes = models.TextField(blank=True, help_text="Internal notes")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "story_locations"
        ordering = ["project", "name"]
        verbose_name = _("Location")
        verbose_name_plural = _("Locations")

    def __str__(self):
        return f"{self.project.title} - {self.name}"


class PlotThread(models.Model):
    """
    A plot thread/storyline that runs through the narrative
    Tracks parallel storylines
    """

    project = models.ForeignKey(
        "bfagent.BookProjects",
        on_delete=models.CASCADE,
        related_name="plot_threads",
        db_column="project_id",
        to_field="id",
        help_text="Book project this plot thread belongs to",
    )
    name = models.CharField(max_length=200, help_text="Plot thread name")
    description = models.TextField(blank=True, help_text="What is this thread about?")
    thread_type = models.CharField(
        max_length=50,
        choices=[
            ("main", "Main Plot"),
            ("subplot", "Subplot"),
            ("background", "Background"),
        ],
        default="subplot",
        help_text="Type of plot thread",
    )
    color = models.CharField(
        max_length=7,
        default="#e74c3c",
        help_text="Color for visualization (hex)",
    )
    resolution = models.TextField(
        blank=True,
        help_text="How this thread resolves",
    )
    status = models.ForeignKey(
        "writing_hub.WritingStage",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Current status of this thread",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "plot_threads"
        ordering = ["project", "thread_type", "name"]
        verbose_name = _("Plot Thread")
        verbose_name_plural = _("Plot Threads")

    def __str__(self):
        return f"{self.project.title} - {self.name} ({self.get_thread_type_display()})"


class SceneConnection(models.Model):
    """
    A connection between two scenes (foreshadowing, callback, etc.)
    Tracks structural relationships
    """

    from_scene = models.ForeignKey(
        Scene,
        on_delete=models.CASCADE,
        related_name="connections_from",
        help_text="Source scene",
    )
    to_scene = models.ForeignKey(
        Scene,
        on_delete=models.CASCADE,
        related_name="connections_to",
        help_text="Target scene",
    )
    connection_type = models.ForeignKey(
        SceneConnectionType,
        on_delete=models.PROTECT,
        help_text="Type of connection",
    )
    description = models.TextField(
        blank=True,
        help_text="Details about this connection",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "scene_connections"
        ordering = ["from_scene", "to_scene"]
        verbose_name = _("Scene Connection")
        verbose_name_plural = _("Scene Connections")
        unique_together = [["from_scene", "to_scene", "connection_type"]]

    def __str__(self):
        return f"{self.from_scene.title} → {self.to_scene.title} ({self.connection_type})"


class TimelineEvent(models.Model):
    """
    An event on the story timeline
    May or may not be shown in a scene
    """

    project = models.ForeignKey(
        "bfagent.BookProjects",
        on_delete=models.CASCADE,
        related_name="timeline_events",
        db_column="project_id",
        to_field="id",
        help_text="Book project this event belongs to",
    )
    description = models.TextField(help_text="What happens in this event")
    story_datetime = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When does this happen in story time?",
    )
    story_date_description = models.CharField(
        max_length=200,
        blank=True,
        help_text="Human-readable time description",
    )
    scene = models.ForeignKey(
        Scene,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="timeline_events",
        help_text="Scene where this event is shown (if any)",
    )
    is_shown = models.BooleanField(
        default=True,
        help_text="Is this event shown in the narrative or just background?",
    )
    characters = models.ManyToManyField(
        "bfagent.Characters",
        blank=True,
        related_name="timeline_events",
        help_text="Characters involved in this event",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "timeline_events"
        ordering = ["project", "story_datetime"]
        verbose_name = _("Timeline Event")
        verbose_name_plural = _("Timeline Events")

    def __str__(self):
        return f"{self.project.title} - {self.description[:50]}"
