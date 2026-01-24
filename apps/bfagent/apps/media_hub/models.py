"""
Media Hub Models
================

Concrete implementations of media production models.
Inherits from abstract base classes in apps.core.models.media_base.

Tables:
- media_hub_style_preset
- media_hub_format_preset
- media_hub_quality_preset
- media_hub_voice_preset
- media_hub_workflow_definition
- media_hub_workflow_binding
- media_hub_render_job
- media_hub_render_attempt
- media_hub_asset
- media_hub_asset_file
"""

from django.db import models
from django.contrib.auth import get_user_model

from apps.core.models.media_base import (
    AbstractStylePreset,
    AbstractFormatPreset,
    AbstractQualityPreset,
    AbstractVoicePreset,
    AbstractWorkflowDefinition,
    AbstractRenderJob,
    AbstractRenderAttempt,
    AbstractAsset,
    AbstractAssetFile,
)

User = get_user_model()


# =============================================================================
# PRESET MODELS
# =============================================================================

class StylePreset(AbstractStylePreset):
    """
    Visual style presets for image generation.
    
    Examples: cinematic, comic_realistic, watercolor, manga
    """
    
    class Category(models.TextChoices):
        ILLUSTRATION = 'illustration', 'Illustration'
        COMIC = 'comic', 'Comic'
        COVER = 'cover', 'Cover Art'
        FOOD = 'food', 'Food Photography'
        PORTRAIT = 'portrait', 'Portrait'
        LANDSCAPE = 'landscape', 'Landscape'
    
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.ILLUSTRATION,
        db_index=True
    )
    
    # Color palette suggestion
    color_palette = models.JSONField(
        default=list,
        blank=True,
        help_text="Suggested hex colors for this style"
    )
    
    class Meta:
        app_label = 'media_hub'
        db_table = 'media_hub_style_preset'
        verbose_name = 'Style Preset'
        verbose_name_plural = 'Style Presets'


class FormatPreset(AbstractFormatPreset):
    """
    Output format presets (dimensions, aspect ratios).
    
    Examples: square_1_1, comic_panel_landscape, audiobook_cover
    """
    
    class UseCase(models.TextChoices):
        GENERAL = 'general', 'General'
        COMIC_PANEL = 'comic_panel', 'Comic Panel'
        BOOK_COVER = 'book_cover', 'Book Cover'
        AUDIOBOOK = 'audiobook', 'Audiobook Cover'
        SOCIAL = 'social', 'Social Media'
        PRINT = 'print', 'Print'
    
    use_case = models.CharField(
        max_length=20,
        choices=UseCase.choices,
        default=UseCase.GENERAL,
        db_index=True
    )
    
    class Meta:
        app_label = 'media_hub'
        db_table = 'media_hub_format_preset'
        verbose_name = 'Format Preset'
        verbose_name_plural = 'Format Presets'


class QualityPreset(AbstractQualityPreset):
    """
    Quality presets (draft, standard, final).
    
    Controls steps, upscaling, and other quality parameters.
    """
    
    class Meta:
        app_label = 'media_hub'
        db_table = 'media_hub_quality_preset'
        verbose_name = 'Quality Preset'
        verbose_name_plural = 'Quality Presets'


class VoicePreset(AbstractVoicePreset):
    """
    Voice presets for audio generation (TTS).
    """
    
    class Language(models.TextChoices):
        DE = 'de', 'Deutsch'
        EN = 'en', 'English'
        FR = 'fr', 'Français'
        ES = 'es', 'Español'
    
    language = models.CharField(
        max_length=5,
        choices=Language.choices,
        default=Language.DE,
        db_index=True
    )
    
    class Gender(models.TextChoices):
        MALE = 'male', 'Male'
        FEMALE = 'female', 'Female'
        NEUTRAL = 'neutral', 'Neutral'
    
    gender = models.CharField(
        max_length=10,
        choices=Gender.choices,
        default=Gender.NEUTRAL
    )
    
    class Meta:
        app_label = 'media_hub'
        db_table = 'media_hub_voice_preset'
        verbose_name = 'Voice Preset'
        verbose_name_plural = 'Voice Presets'


# =============================================================================
# WORKFLOW MODELS
# =============================================================================

class WorkflowDefinition(AbstractWorkflowDefinition):
    """
    ComfyUI workflow definitions.
    
    Stores the full workflow JSON graph with versioning.
    """
    
    class Engine(models.TextChoices):
        COMFYUI = 'comfyui', 'ComfyUI'
        XTTS = 'xtts', 'XTTS (TTS)'
        CUSTOM = 'custom', 'Custom'
    
    engine = models.CharField(
        max_length=20,
        choices=Engine.choices,
        default=Engine.COMFYUI
    )
    
    # Required models/checkpoints
    required_models = models.JSONField(
        default=list,
        help_text="List of required model files"
    )
    
    class Meta:
        app_label = 'media_hub'
        db_table = 'media_hub_workflow_definition'
        verbose_name = 'Workflow Definition'
        verbose_name_plural = 'Workflow Definitions'
        unique_together = ['key', 'version']


class WorkflowBinding(models.Model):
    """
    Maps job types to workflow definitions.
    
    Determines which workflow to use for each job type.
    """
    
    job_type = models.CharField(
        max_length=20,
        choices=AbstractRenderJob.JobType.choices,
        unique=True,
        db_index=True
    )
    workflow = models.ForeignKey(
        WorkflowDefinition,
        on_delete=models.PROTECT,
        related_name='bindings'
    )
    
    # Override defaults
    default_style_preset = models.ForeignKey(
        StylePreset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    default_format_preset = models.ForeignKey(
        FormatPreset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    default_quality_preset = models.ForeignKey(
        QualityPreset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'media_hub'
        db_table = 'media_hub_workflow_binding'
        verbose_name = 'Workflow Binding'
        verbose_name_plural = 'Workflow Bindings'
    
    def __str__(self):
        return f"{self.get_job_type_display()} → {self.workflow}"


# =============================================================================
# RENDER JOB MODELS
# =============================================================================

class RenderJob(AbstractRenderJob):
    """
    A render job in the media production pipeline.
    
    References content via ref_table/ref_id (polymorphic).
    Input snapshot captures all parameters for audit/reproducibility.
    """
    
    # Organization (for multi-tenancy - placeholder for future)
    org_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Organization ID (for future multi-tenancy)"
    )
    
    # Project reference
    project = models.ForeignKey(
        'bfagent.BookProjects',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='media_render_jobs'
    )
    
    # Preset references (for UI display, actual values in input_snapshot)
    style_preset = models.ForeignKey(
        StylePreset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    format_preset = models.ForeignKey(
        FormatPreset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    quality_preset = models.ForeignKey(
        QualityPreset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    voice_preset = models.ForeignKey(
        VoicePreset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Workflow used
    workflow = models.ForeignKey(
        WorkflowDefinition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    class Meta:
        app_label = 'media_hub'
        db_table = 'media_hub_render_job'
        verbose_name = 'Render Job'
        verbose_name_plural = 'Render Jobs'
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['project', 'job_type']),
            models.Index(fields=['org_id', 'status']),
        ]
    
    def build_input_snapshot(self) -> dict:
        """
        Build the complete input snapshot from referenced content and presets.
        
        This is called before job execution to capture all parameters.
        """
        snapshot = {
            'job_id': self.id,
            'job_type': self.job_type,
            'ref_table': self.ref_table,
            'ref_id': self.ref_id,
            'workflow': {
                'key': self.workflow.key if self.workflow else None,
                'version': self.workflow.version if self.workflow else None,
                'sha256': self.workflow.sha256 if self.workflow else None,
            },
            'prompt': {},
            'render': {},
            'sampler': {},
            'output': {},
        }
        
        # Add style preset
        if self.style_preset:
            snapshot['prompt']['style'] = self.style_preset.prompt_style
            snapshot['prompt']['negative'] = self.style_preset.prompt_negative
            snapshot['sampler'].update(self.style_preset.defaults)
        
        # Add format preset
        if self.format_preset:
            snapshot['render']['width'] = self.format_preset.width
            snapshot['render']['height'] = self.format_preset.height
            snapshot['render'].update(self.format_preset.meta)
        
        # Add quality preset
        if self.quality_preset:
            snapshot['sampler'].update(self.quality_preset.settings)
        
        # Add voice preset (for audio jobs)
        if self.voice_preset:
            snapshot['tts'] = {
                'engine': self.voice_preset.engine,
                'voice_id': self.voice_preset.voice_id,
                **self.voice_preset.defaults
            }
        
        return snapshot


class RenderAttempt(AbstractRenderAttempt):
    """
    Log of each render attempt for a job.
    
    Supports retries with full audit trail.
    """
    
    job = models.ForeignKey(
        RenderJob,
        on_delete=models.CASCADE,
        related_name='attempts'
    )
    
    # ComfyUI specific
    comfy_prompt_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="ComfyUI prompt_id for tracking"
    )
    
    class Meta:
        app_label = 'media_hub'
        db_table = 'media_hub_render_attempt'
        verbose_name = 'Render Attempt'
        verbose_name_plural = 'Render Attempts'
        unique_together = ['job', 'attempt_no']


# =============================================================================
# ASSET MODELS
# =============================================================================

class Asset(AbstractAsset):
    """
    A generated asset (image, audio, etc.)
    
    Links back to the render job that created it.
    """
    
    # Source
    job = models.ForeignKey(
        RenderJob,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assets'
    )
    
    # Organization (placeholder for future multi-tenancy)
    org_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Organization ID (for future multi-tenancy)"
    )
    
    # Project
    project = models.ForeignKey(
        'bfagent.BookProjects',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='media_assets'
    )
    
    # Content reference (polymorphic)
    content_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="Content type: scene, panel, chapter, etc."
    )
    content_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Content record ID"
    )
    
    # Status
    is_approved = models.BooleanField(
        default=False,
        help_text="Approved for use/publication"
    )
    is_featured = models.BooleanField(
        default=False,
        help_text="Featured/highlighted asset"
    )
    
    class Meta:
        app_label = 'media_hub'
        db_table = 'media_hub_asset'
        verbose_name = 'Asset'
        verbose_name_plural = 'Assets'
        indexes = [
            models.Index(fields=['project', 'asset_type']),
            models.Index(fields=['content_type', 'content_id']),
        ]


class AssetFile(AbstractAssetFile):
    """
    Individual files belonging to an asset.
    
    Each asset can have multiple files (original, thumbnail, etc.)
    """
    
    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name='files'
    )
    
    class Meta:
        app_label = 'media_hub'
        db_table = 'media_hub_asset_file'
        verbose_name = 'Asset File'
        verbose_name_plural = 'Asset Files'


# =============================================================================
# PARAMETER MAPPING (für dynamische Prompt-Generierung)
# =============================================================================

class ParameterMapping(models.Model):
    """
    Maps source fields to target workflow parameters.
    
    Enables dynamic prompt generation based on content type.
    """
    
    class Transform(models.TextChoices):
        PASSTHROUGH = 'passthrough', 'Passthrough (as-is)'
        TEMPLATE = 'template', 'Template (Jinja2)'
        INT = 'int', 'Integer'
        FLOAT = 'float', 'Float'
        BOOL = 'bool', 'Boolean'
        JSON = 'json', 'JSON'
    
    job_type = models.CharField(
        max_length=20,
        choices=AbstractRenderJob.JobType.choices,
        db_index=True
    )
    
    source_field = models.CharField(
        max_length=200,
        help_text="Source field path (e.g., 'scene.location', 'panel.description')"
    )
    target_field = models.CharField(
        max_length=200,
        help_text="Target field path (e.g., 'prompt.positive', 'sampler.steps')"
    )
    transform = models.CharField(
        max_length=20,
        choices=Transform.choices,
        default=Transform.PASSTHROUGH
    )
    template = models.TextField(
        blank=True,
        help_text="Jinja2 template for TEMPLATE transform"
    )
    default_value = models.TextField(
        blank=True,
        help_text="Default value if source is empty"
    )
    
    is_required = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)
    
    class Meta:
        app_label = 'media_hub'
        db_table = 'media_hub_parameter_mapping'
        verbose_name = 'Parameter Mapping'
        verbose_name_plural = 'Parameter Mappings'
        ordering = ['job_type', 'order']
        unique_together = ['job_type', 'source_field', 'target_field']
    
    def __str__(self):
        return f"{self.source_field} → {self.target_field}"
