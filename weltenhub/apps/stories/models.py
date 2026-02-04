"""
Weltenhub Story Models
======================

Story and chapter management for narrative content.

Tables:
    - wh_story: Main story entity
    - wh_chapter: Chapters within a story
    - wh_plot_thread: Plot threads/storylines
    - wh_timeline_event: Events on the story timeline
"""

from django.db import models

from apps.core.models import TenantAwareModel


class Story(TenantAwareModel):
    """
    A story within a world.

    Stories contain chapters, scenes, and track narrative elements.
    """

    world = models.ForeignKey(
        "worlds.World",
        on_delete=models.CASCADE,
        related_name="stories",
        help_text="World this story takes place in"
    )
    title = models.CharField(
        max_length=300,
        help_text="Story title"
    )
    slug = models.SlugField(
        max_length=300,
        help_text="URL-safe identifier"
    )
    genre = models.ForeignKey(
        "lookups.Genre",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stories",
        help_text="Primary genre"
    )
    premise = models.TextField(
        blank=True,
        help_text="Story premise (1-2 paragraphs)"
    )
    logline = models.CharField(
        max_length=500,
        blank=True,
        help_text="One-sentence summary"
    )
    synopsis = models.TextField(
        blank=True,
        help_text="Full story synopsis"
    )
    themes = models.JSONField(
        default=list,
        blank=True,
        help_text="Central themes: ['redemption', 'love', 'sacrifice']"
    )
    target_audience = models.CharField(
        max_length=100,
        blank=True,
        help_text="Target audience (e.g., 'Adult', 'Young Adult')"
    )
    spice_level = models.IntegerField(
        default=0,
        help_text="Romantic/adult content level 0-5"
    )
    target_word_count = models.IntegerField(
        default=80000,
        help_text="Target total word count"
    )
    actual_word_count = models.IntegerField(
        default=0,
        help_text="Current word count"
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("planning", "Planning"),
            ("outlining", "Outlining"),
            ("drafting", "Drafting"),
            ("revising", "Revising"),
            ("editing", "Editing"),
            ("completed", "Completed"),
            ("published", "Published"),
        ],
        default="planning",
        help_text="Current writing status"
    )
    cover_image = models.ImageField(
        upload_to="stories/covers/",
        blank=True,
        null=True,
        help_text="Cover image"
    )
    is_public = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Publicly visible"
    )
    source_trip = models.JSONField(
        default=dict,
        blank=True,
        help_text="Reference to source trip (travel-beat integration)"
    )
    notes = models.TextField(
        blank=True,
        help_text="Internal planning notes"
    )

    class Meta:
        db_table = "wh_story"
        verbose_name = "Story"
        verbose_name_plural = "Stories"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "world"]),
            models.Index(fields=["genre"]),
            models.Index(fields=["status"]),
            models.Index(fields=["is_public"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "slug"],
                name="unique_story_slug"
            )
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def update_word_count(self) -> int:
        """Calculate total word count from all scenes."""
        total = sum(
            scene.word_count_actual
            for scene in self.scenes.all()
        )
        self.actual_word_count = total
        self.save(update_fields=["actual_word_count"])
        return total


class Chapter(TenantAwareModel):
    """
    A chapter within a story.

    Chapters organize scenes into logical groups.
    """

    story = models.ForeignKey(
        Story,
        on_delete=models.CASCADE,
        related_name="chapters",
        help_text="Story this chapter belongs to"
    )
    title = models.CharField(
        max_length=200,
        help_text="Chapter title"
    )
    number = models.IntegerField(
        help_text="Chapter number"
    )
    summary = models.TextField(
        blank=True,
        help_text="Chapter summary"
    )
    notes = models.TextField(
        blank=True,
        help_text="Planning notes"
    )
    target_word_count = models.IntegerField(
        default=5000,
        help_text="Target word count"
    )
    actual_word_count = models.IntegerField(
        default=0,
        help_text="Current word count"
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("planned", "Planned"),
            ("outlined", "Outlined"),
            ("drafted", "Drafted"),
            ("revised", "Revised"),
            ("final", "Final"),
        ],
        default="planned",
        help_text="Writing status"
    )

    class Meta:
        db_table = "wh_chapter"
        verbose_name = "Chapter"
        verbose_name_plural = "Chapters"
        ordering = ["story", "number"]
        constraints = [
            models.UniqueConstraint(
                fields=["story", "number"],
                name="unique_chapter_number"
            )
        ]

    def __str__(self):
        return f"Chapter {self.number}: {self.title}"

    def update_word_count(self) -> int:
        """Calculate word count from scenes."""
        total = sum(
            scene.word_count_actual
            for scene in self.scenes.all()
        )
        self.actual_word_count = total
        self.save(update_fields=["actual_word_count"])
        return total


class PlotThread(TenantAwareModel):
    """
    A plot thread/storyline running through a story.

    Tracks parallel storylines and their resolution.
    """

    story = models.ForeignKey(
        Story,
        on_delete=models.CASCADE,
        related_name="plot_threads",
        help_text="Story this thread belongs to"
    )
    name = models.CharField(
        max_length=200,
        help_text="Plot thread name"
    )
    thread_type = models.CharField(
        max_length=20,
        choices=[
            ("main", "Main Plot"),
            ("subplot", "Subplot"),
            ("background", "Background"),
        ],
        default="subplot",
        help_text="Thread type"
    )
    description = models.TextField(
        blank=True,
        help_text="What is this thread about?"
    )
    resolution = models.TextField(
        blank=True,
        help_text="How this thread resolves"
    )
    color = models.CharField(
        max_length=7,
        default="#e74c3c",
        help_text="Color for visualization (hex)"
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("active", "Active"),
            ("resolved", "Resolved"),
            ("dropped", "Dropped"),
        ],
        default="active",
        help_text="Thread status"
    )

    class Meta:
        db_table = "wh_plot_thread"
        verbose_name = "Plot Thread"
        verbose_name_plural = "Plot Threads"
        ordering = ["story", "thread_type", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_thread_type_display()})"


class TimelineEvent(TenantAwareModel):
    """
    An event on the story timeline.

    May or may not be shown in a scene.
    """

    story = models.ForeignKey(
        Story,
        on_delete=models.CASCADE,
        related_name="timeline_events",
        help_text="Story this event belongs to"
    )
    scene = models.ForeignKey(
        "scenes.Scene",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="timeline_events",
        help_text="Scene where this is shown (if any)"
    )
    description = models.TextField(
        help_text="What happens"
    )
    story_datetime = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When in story time"
    )
    story_date_description = models.CharField(
        max_length=200,
        blank=True,
        help_text="Human-readable time"
    )
    is_shown = models.BooleanField(
        default=True,
        help_text="Is this shown in narrative?"
    )
    is_pivotal = models.BooleanField(
        default=False,
        help_text="Is this a pivotal story event?"
    )
    characters = models.ManyToManyField(
        "characters.Character",
        blank=True,
        related_name="timeline_events",
        help_text="Characters involved"
    )
    location = models.ForeignKey(
        "locations.Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="timeline_events",
        help_text="Where this happens"
    )

    class Meta:
        db_table = "wh_timeline_event"
        verbose_name = "Timeline Event"
        verbose_name_plural = "Timeline Events"
        ordering = ["story", "story_datetime"]

    def __str__(self):
        return f"{self.story.title}: {self.description[:50]}"
