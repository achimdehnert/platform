"""
Story Models - Generated Stories and Chapters
"""

from django.db import models
from django.conf import settings


class Story(models.Model):
    """Eine generierte Geschichte"""
    
    class Genre(models.TextChoices):
        ROMANCE = 'romance', 'Romance'
        THRILLER = 'thriller', 'Thriller'
        MYSTERY = 'mystery', 'Mystery'
        ROMANTIC_SUSPENSE = 'romantic_suspense', 'Romantic Suspense'
        COZY_MYSTERY = 'cozy_mystery', 'Cozy Mystery'
        FANTASY = 'fantasy', 'Fantasy'
        ADVENTURE = 'adventure', 'Adventure'
    
    class SpiceLevel(models.TextChoices):
        NONE = 'none', 'Keine expliziten Szenen'
        MILD = 'mild', 'Angedeutete Intimität'
        MODERATE = 'moderate', 'Sinnliche Szenen'
        SPICY = 'spicy', 'Explizite Szenen'
    
    class EndingType(models.TextChoices):
        HAPPY = 'happy', 'Happy End'
        SAD = 'sad', 'Trauriges Ende'
        OPEN = 'open', 'Offenes Ende'
        SURPRISE = 'surprise', 'Überraschung'
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Wartend'
        GENERATING = 'generating', 'Wird generiert'
        COMPLETED = 'completed', 'Fertig'
        FAILED = 'failed', 'Fehlgeschlagen'
    
    # Beziehungen
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='stories',
    )
    trip = models.OneToOneField(
        'trips.Trip',
        on_delete=models.CASCADE,
        related_name='story',
    )
    user_world = models.ForeignKey(
        'worlds.UserWorld',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stories',
    )
    
    # Story-Metadaten
    title = models.CharField(max_length=300)
    genre = models.CharField(
        max_length=30,
        choices=Genre.choices,
        default=Genre.ROMANTIC_SUSPENSE,
    )
    
    # Einstellungen
    spice_level = models.CharField(
        max_length=20,
        choices=SpiceLevel.choices,
        default=SpiceLevel.MILD,
    )
    ending_type = models.CharField(
        max_length=20,
        choices=EndingType.choices,
        default=EndingType.HAPPY,
    )
    triggers_avoid = models.JSONField(
        default=list,
        blank=True,
        help_text='Themen die vermieden werden sollen',
    )
    
    # Generierung
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    generation_started = models.DateTimeField(null=True, blank=True)
    generation_completed = models.DateTimeField(null=True, blank=True)
    generation_error = models.TextField(blank=True)
    
    # Statistiken
    total_chapters = models.PositiveIntegerField(default=0)
    total_words = models.PositiveIntegerField(default=0)
    
    # Kosten-Tracking
    tokens_used = models.PositiveIntegerField(default=0)
    generation_cost_usd = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        default=0,
    )
    
    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Story'
        verbose_name_plural = 'Stories'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    @property
    def is_complete(self) -> bool:
        return self.status == self.Status.COMPLETED
    
    @property
    def progress_percent(self) -> int:
        if self.status == self.Status.COMPLETED:
            return 100
        if self.total_chapters == 0:
            return 0
        completed = self.chapters.filter(status=Chapter.Status.COMPLETED).count()
        return int((completed / self.total_chapters) * 100)


class Chapter(models.Model):
    """Ein Kapitel einer Story"""
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Wartend'
        GENERATING = 'generating', 'Wird generiert'
        COMPLETED = 'completed', 'Fertig'
        FAILED = 'failed', 'Fehlgeschlagen'
    
    class PacingType(models.TextChoices):
        ACTION = 'action', 'Action'
        EMOTIONAL = 'emotional', 'Emotional'
        REFLECTIVE = 'reflective', 'Reflektiv'
        ATMOSPHERIC = 'atmospheric', 'Atmosphärisch'
        ROMANTIC = 'romantic', 'Romantisch'
        MYSTERIOUS = 'mysterious', 'Mysteriös'
    
    # Beziehungen
    story = models.ForeignKey(
        Story,
        on_delete=models.CASCADE,
        related_name='chapters',
    )
    
    # Kapitel-Info
    number = models.PositiveIntegerField()
    title = models.CharField(max_length=200, blank=True)
    
    # Story-Struktur
    act = models.CharField(max_length=20, blank=True)  # act_1, act_2a, act_2b, act_3
    beat = models.CharField(max_length=50, blank=True)  # hook, setup, midpoint, etc.
    pacing = models.CharField(
        max_length=20,
        choices=PacingType.choices,
        default=PacingType.ATMOSPHERIC,
    )
    
    # Location-Sync
    story_location = models.CharField(max_length=200, blank=True)
    reader_location = models.CharField(max_length=200, blank=True)
    reading_date = models.DateField(null=True, blank=True)
    
    # Content
    content = models.TextField(blank=True)
    word_count = models.PositiveIntegerField(default=0)
    target_words = models.PositiveIntegerField(default=3000)
    
    # Generierung
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    generation_prompt = models.TextField(blank=True)
    tokens_used = models.PositiveIntegerField(default=0)
    
    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Kapitel'
        verbose_name_plural = 'Kapitel'
        ordering = ['number']
        unique_together = ['story', 'number']
    
    def __str__(self):
        return f"Kapitel {self.number}: {self.title or 'Ohne Titel'}"


class ReadingProgress(models.Model):
    """Lesefortschritt eines Users"""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reading_progress',
    )
    story = models.ForeignKey(
        Story,
        on_delete=models.CASCADE,
        related_name='reading_progress',
    )
    
    # Fortschritt
    current_chapter = models.ForeignKey(
        Chapter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    chapters_completed = models.PositiveIntegerField(default=0)
    words_read = models.PositiveIntegerField(default=0)
    
    # Lesezeit
    total_reading_minutes = models.PositiveIntegerField(default=0)
    last_read_at = models.DateTimeField(null=True, blank=True)
    
    # Lesezeichen
    bookmarks = models.JSONField(default=list, blank=True)
    
    class Meta:
        verbose_name = 'Lesefortschritt'
        verbose_name_plural = 'Lesefortschritte'
        unique_together = ['user', 'story']
    
    def __str__(self):
        return f"{self.user} - {self.story.title}"
    
    @property
    def progress_percent(self) -> int:
        if self.story.total_chapters == 0:
            return 0
        return int((self.chapters_completed / self.story.total_chapters) * 100)
