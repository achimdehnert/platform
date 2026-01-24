"""
Core Media Base Models
======================

Abstract base classes for media production workflows.
Used by media_hub and can be extended by writing_hub.

Architecture:
- AbstractPreset → StylePreset, FormatPreset, QualityPreset, VoicePreset
- AbstractRenderJob → RenderJob (media_hub), ChapterIllustration (writing_hub)
- AbstractAsset → Asset, AssetFile
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import hashlib
import uuid

User = get_user_model()


# =============================================================================
# PRESET BASE CLASSES
# =============================================================================

class AbstractPreset(models.Model):
    """
    Base class for all preset types (Style, Format, Quality, Voice).
    
    Presets are configuration templates that can be selected by users.
    Only approved presets are available for production use.
    """
    
    key = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        default='',
        help_text="Unique identifier for programmatic access"
    )
    name = models.CharField(
        max_length=200,
        help_text="Display name"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description for users"
    )
    
    # Governance
    is_approved = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Only approved presets are available for production"
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Inactive presets are hidden from selection"
    )
    
    # Audit
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Versioning
    version = models.PositiveIntegerField(default=1)
    
    class Meta:
        abstract = True
        ordering = ['name']
    
    def __str__(self):
        status = "✓" if self.is_approved else "○"
        return f"{status} {self.name} ({self.key})"
    
    def save(self, *args, **kwargs):
        if self.pk:
            # Increment version on update
            self.version += 1
        super().save(*args, **kwargs)


class AbstractStylePreset(AbstractPreset):
    """
    Base class for style presets (visual styles, prompts, etc.)
    """
    
    prompt_style = models.TextField(
        help_text="Positive prompt additions for this style"
    )
    prompt_negative = models.TextField(
        blank=True,
        help_text="Negative prompt (things to avoid)"
    )
    
    # Default sampler settings
    defaults = models.JSONField(
        default=dict,
        help_text="Default settings: steps, cfg, sampler, scheduler"
    )
    
    # Optional reference
    reference_image = models.ImageField(
        upload_to='preset_references/',
        blank=True,
        null=True,
        help_text="Visual reference for this style"
    )
    
    class Meta:
        abstract = True


class AbstractFormatPreset(AbstractPreset):
    """
    Base class for format presets (dimensions, DPI, etc.)
    """
    
    width = models.PositiveIntegerField(
        help_text="Output width in pixels"
    )
    height = models.PositiveIntegerField(
        help_text="Output height in pixels"
    )
    
    meta = models.JSONField(
        default=dict,
        help_text="Additional format metadata: dpi, color_space, etc."
    )
    
    class Meta:
        abstract = True
    
    @property
    def aspect_ratio(self) -> str:
        """Calculate aspect ratio as string."""
        from math import gcd
        g = gcd(self.width, self.height)
        return f"{self.width // g}:{self.height // g}"
    
    @property
    def resolution(self) -> str:
        """Resolution as string."""
        return f"{self.width}x{self.height}"


class AbstractQualityPreset(AbstractPreset):
    """
    Base class for quality presets (draft, final, etc.)
    """
    
    settings = models.JSONField(
        default=dict,
        help_text="Quality settings: steps, upscale, upscale_factor, etc."
    )
    
    # Cost estimation
    estimated_time_seconds = models.PositiveIntegerField(
        default=0,
        help_text="Estimated generation time in seconds"
    )
    estimated_cost = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        default=0,
        help_text="Estimated cost per generation (if using paid API)"
    )
    
    class Meta:
        abstract = True


class AbstractVoicePreset(AbstractPreset):
    """
    Base class for voice presets (TTS voices, speech settings)
    """
    
    class Engine(models.TextChoices):
        XTTS = 'xtts', 'XTTS (Local)'
        ELEVENLABS = 'elevenlabs', 'ElevenLabs'
        AZURE = 'azure', 'Azure TTS'
        OPENAI = 'openai', 'OpenAI TTS'
    
    engine = models.CharField(
        max_length=20,
        choices=Engine.choices,
        default=Engine.XTTS
    )
    voice_id = models.CharField(
        max_length=100,
        help_text="Voice identifier for the selected engine"
    )
    
    defaults = models.JSONField(
        default=dict,
        help_text="Default settings: speed, pitch, etc."
    )
    
    # Sample audio
    sample_audio = models.FileField(
        upload_to='voice_samples/',
        blank=True,
        null=True,
        help_text="Sample audio for preview"
    )
    
    class Meta:
        abstract = True


# =============================================================================
# WORKFLOW BASE CLASSES
# =============================================================================

class AbstractWorkflowDefinition(models.Model):
    """
    Base class for workflow definitions (ComfyUI workflows, etc.)
    
    Workflows are versioned and integrity-checked via SHA256 hash.
    """
    
    key = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Workflow identifier"
    )
    version = models.PositiveIntegerField(default=1)
    
    # Workflow content
    workflow_json = models.JSONField(
        help_text="Full workflow definition (e.g., ComfyUI graph)"
    )
    sha256 = models.CharField(
        max_length=64,
        editable=False,
        help_text="SHA256 hash for integrity verification"
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        db_index=True
    )
    
    # Metadata
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        abstract = True
        unique_together = ['key', 'version']
        ordering = ['key', '-version']
    
    def __str__(self):
        return f"{self.key} v{self.version}"
    
    def save(self, *args, **kwargs):
        # Calculate SHA256 hash
        import json
        content = json.dumps(self.workflow_json, sort_keys=True)
        self.sha256 = hashlib.sha256(content.encode()).hexdigest()
        super().save(*args, **kwargs)


# =============================================================================
# RENDER JOB BASE CLASSES
# =============================================================================

class AbstractRenderJob(models.Model):
    """
    Base class for render jobs.
    
    A render job represents a request to generate media content.
    The input_snapshot captures ALL parameters at submission time for audit.
    """
    
    class JobType(models.TextChoices):
        ILLUSTRATION = 'illustration', 'Illustration'
        COMIC_PANEL = 'comic_panel', 'Comic Panel'
        AUDIO_CHAPTER = 'audio_chapter', 'Audio Chapter'
        COVER = 'cover', 'Cover Art'
        UPSCALE = 'upscale', 'Upscaling'
    
    class Status(models.TextChoices):
        QUEUED = 'queued', 'In Warteschlange'
        RUNNING = 'running', 'Wird verarbeitet'
        SUCCESS = 'success', 'Erfolgreich'
        FAILED = 'failed', 'Fehlgeschlagen'
        CANCELLED = 'cancelled', 'Abgebrochen'
    
    # Job identification
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True
    )
    job_type = models.CharField(
        max_length=20,
        choices=JobType.choices,
        db_index=True
    )
    
    # Reference to source content (polymorphic)
    ref_table = models.CharField(
        max_length=100,
        help_text="Source table name (e.g., 'panel', 'scene', 'chapter')"
    )
    ref_id = models.PositiveIntegerField(
        help_text="Source record ID"
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.QUEUED,
        db_index=True
    )
    priority = models.PositiveSmallIntegerField(
        default=5,
        help_text="1=highest, 10=lowest"
    )
    
    # INPUT SNAPSHOT - The audit core!
    input_snapshot = models.JSONField(
        default=dict,
        help_text="Complete resolved parameters at submission time (immutable)"
    )
    
    # Error tracking
    error_message = models.TextField(
        blank=True,
        default='',
        help_text="Error message if failed"
    )
    
    # Retry handling
    attempt_count = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=3)
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Audit
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_created"
    )
    
    class Meta:
        abstract = True
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['ref_table', 'ref_id']),
        ]
    
    def __str__(self):
        return f"{self.get_job_type_display()} #{self.id} ({self.get_status_display()})"
    
    @property
    def duration_seconds(self) -> int | None:
        """Calculate job duration in seconds."""
        if self.started_at and self.finished_at:
            return int((self.finished_at - self.started_at).total_seconds())
        return None
    
    def mark_running(self):
        """Mark job as running."""
        self.status = self.Status.RUNNING
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])
    
    def mark_success(self, output_summary: dict = None):
        """Mark job as successful."""
        self.status = self.Status.SUCCESS
        self.finished_at = timezone.now()
        if output_summary:
            self.output_summary = output_summary
        self.save(update_fields=['status', 'finished_at', 'output_summary'])
    
    def mark_failed(self, error: str):
        """Mark job as failed."""
        self.status = self.Status.FAILED
        self.finished_at = timezone.now()
        self.error = error
        self.save(update_fields=['status', 'finished_at', 'error'])


class AbstractRenderAttempt(models.Model):
    """
    Base class for render attempts (logs each try).
    
    A job can have multiple attempts (retries).
    """
    
    class Status(models.TextChoices):
        RUNNING = 'running', 'Running'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
    
    attempt_no = models.PositiveSmallIntegerField(default=1)
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.RUNNING
    )
    
    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    
    # Error tracking
    error_message = models.TextField(blank=True, default='')
    error_traceback = models.TextField(blank=True, default='')
    
    # Output
    output_data = models.JSONField(default=dict, blank=True)
    comfy_prompt_id = models.CharField(max_length=100, blank=True, default='')
    
    class Meta:
        abstract = True
        ordering = ['-attempt_no']
    
    def __str__(self):
        return f"Attempt #{self.attempt_no} ({self.get_status_display()})"


# =============================================================================
# ASSET BASE CLASSES
# =============================================================================

class AbstractAsset(models.Model):
    """
    Base class for generated assets.
    
    An asset is a logical grouping of generated files (e.g., image + thumbnail).
    """
    
    class AssetType(models.TextChoices):
        IMAGE = 'image', 'Image'
        AUDIO = 'audio', 'Audio'
        VIDEO = 'video', 'Video'
        DOCUMENT = 'document', 'Document'
    
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True
    )
    asset_type = models.CharField(
        max_length=20,
        choices=AssetType.choices,
        db_index=True
    )
    
    # Metadata
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata (dimensions, duration, etc.)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Audit
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_created"
    )
    
    class Meta:
        abstract = True
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_asset_type_display()} {self.uuid.hex[:8]}"


class AbstractAssetFile(models.Model):
    """
    Base class for asset files.
    
    Each asset can have multiple files (original, thumbnail, variants).
    """
    
    class FileType(models.TextChoices):
        ORIGINAL = 'original', 'Original'
        THUMBNAIL = 'thumbnail', 'Thumbnail'
        PREVIEW = 'preview', 'Preview'
        OPTIMIZED = 'optimized', 'Optimized'
    
    # File info
    file_type = models.CharField(
        max_length=20,
        choices=FileType.choices,
        default=FileType.ORIGINAL
    )
    storage_path = models.CharField(
        max_length=500,
        help_text="Path in storage"
    )
    storage_backend = models.CharField(
        max_length=50,
        default='local',
        help_text="Storage backend: local, s3, etc."
    )
    
    # Technical details
    mime_type = models.CharField(max_length=100, blank=True, default='')
    file_size = models.PositiveBigIntegerField(null=True, blank=True)
    checksum = models.CharField(
        max_length=64,
        blank=True,
        default='',
        help_text="SHA256 checksum"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        abstract = True
    
    def __str__(self):
        return f"{self.storage_path} ({self.get_file_type_display()})"
    
    @property
    def size_human(self) -> str:
        """Human-readable file size."""
        size = self.file_size or 0
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
