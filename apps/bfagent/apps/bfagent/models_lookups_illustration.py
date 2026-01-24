"""
Illustration System Lookup Tables
==================================

Database-driven lookup tables for AI-powered illustration system.
Replaces hardcoded TextChoices with flexible, admin-editable models.

Migration from:
- ArtStyle (TextChoices)
- ImageType (TextChoices)
- AIProvider (TextChoices)
- ImageStatus (TextChoices)
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class IllustrationArtStyle(models.Model):
    """
    Art styles for image generation.
    
    Replaces: ArtStyle(TextChoices)
    """
    # Core fields
    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique identifier (e.g., 'realistic', 'watercolor')"
    )
    name = models.CharField(
        max_length=100,
        help_text="Display name (e.g., 'Realistic Photography')"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description of the art style"
    )
    
    # Visual reference
    example_url = models.URLField(
        blank=True,
        help_text="Example image URL showcasing this style"
    )
    thumbnail = models.ImageField(
        upload_to='illustration/style_examples/',
        blank=True,
        null=True,
        help_text="Example thumbnail"
    )
    
    # Metadata for recommendations
    suitable_for = models.JSONField(
        default=list,
        help_text="Suitable image types (e.g., ['cover', 'scene', 'portrait'])"
    )
    complexity = models.IntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Style complexity (1=simple, 10=complex)"
    )
    
    # Prompt suggestions
    prompt_keywords = models.TextField(
        blank=True,
        help_text="Recommended keywords for this style (comma-separated)"
    )
    negative_prompt_defaults = models.TextField(
        blank=True,
        help_text="Default negative prompt for this style"
    )
    
    # Standard fields
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this style is available for selection"
    )
    order = models.IntegerField(
        default=0,
        help_text="Display order"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'bfagent'
        db_table = 'illustration_art_styles'
        ordering = ['order', 'name']
        verbose_name = 'Art Style'
        verbose_name_plural = 'Art Styles'
    
    def __str__(self):
        return self.name


class IllustrationImageType(models.Model):
    """
    Image types for different use cases.
    
    Replaces: ImageType(TextChoices)
    """
    # Core fields
    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique identifier (e.g., 'cover', 'chapter_header')"
    )
    name = models.CharField(
        max_length=100,
        help_text="Display name (e.g., 'Book Cover', 'Chapter Header')"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of when to use this image type"
    )
    
    # Recommended styles
    recommended_styles = models.ManyToManyField(
        IllustrationArtStyle,
        blank=True,
        related_name='suitable_image_types',
        help_text="Art styles that work well for this image type"
    )
    
    # Technical specifications
    default_width = models.IntegerField(
        default=1024,
        help_text="Default image width in pixels"
    )
    default_height = models.IntegerField(
        default=1024,
        help_text="Default image height in pixels"
    )
    aspect_ratio = models.CharField(
        max_length=20,
        blank=True,
        help_text="Aspect ratio (e.g., '16:9', '1:1', '4:3')"
    )
    
    # Usage context
    use_case_examples = models.TextField(
        blank=True,
        help_text="Examples of when to use this type"
    )
    
    # Icon for UI
    icon = models.CharField(
        max_length=50,
        default='bi-image',
        help_text="Bootstrap icon class"
    )
    
    # Standard fields
    is_active = models.BooleanField(
        default=True,
        db_index=True
    )
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'bfagent'
        db_table = 'illustration_image_types'
        ordering = ['order', 'name']
        verbose_name = 'Image Type'
        verbose_name_plural = 'Image Types'
    
    def __str__(self):
        return self.name


class IllustrationAIProvider(models.Model):
    """
    AI providers for image generation.
    
    Replaces: AIProvider(TextChoices)
    """
    # Core fields
    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Provider code (e.g., 'dalle3', 'stability')"
    )
    name = models.CharField(
        max_length=100,
        help_text="Provider name (e.g., 'DALL-E 3 (OpenAI)')"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of the provider and its capabilities"
    )
    
    # Technical details
    api_endpoint = models.URLField(
        blank=True,
        help_text="API endpoint URL"
    )
    api_key_required = models.BooleanField(
        default=True,
        help_text="Whether an API key is required"
    )
    documentation_url = models.URLField(
        blank=True,
        help_text="Link to provider documentation"
    )
    
    # Capabilities
    max_resolution = models.CharField(
        max_length=20,
        blank=True,
        help_text="Maximum resolution (e.g., '1024x1024', '2048x2048')"
    )
    supports_batch = models.BooleanField(
        default=False,
        help_text="Whether batch generation is supported"
    )
    supports_img2img = models.BooleanField(
        default=False,
        help_text="Whether image-to-image transformation is supported"
    )
    supports_inpainting = models.BooleanField(
        default=False,
        help_text="Whether inpainting is supported"
    )
    
    # Pricing
    pricing_per_image = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Cost per image in USD"
    )
    pricing_model = models.CharField(
        max_length=100,
        blank=True,
        help_text="Pricing model description"
    )
    
    # Performance
    avg_generation_time_seconds = models.IntegerField(
        null=True,
        blank=True,
        help_text="Average generation time in seconds"
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        db_index=True
    )
    is_recommended = models.BooleanField(
        default=False,
        help_text="Whether this is a recommended provider"
    )
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'bfagent'
        db_table = 'illustration_ai_providers'
        ordering = ['order', 'name']
        verbose_name = 'AI Provider'
        verbose_name_plural = 'AI Providers'
    
    def __str__(self):
        return self.name


class IllustrationImageStatus(models.Model):
    """
    Status values for generated images.
    
    Replaces: ImageStatus(TextChoices)
    """
    # Core fields
    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Status code (e.g., 'pending', 'generating', 'approved')"
    )
    name = models.CharField(
        max_length=100,
        help_text="Display name (e.g., 'Pending', 'Generating')"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of what this status means"
    )
    
    # UI Styling
    color = models.CharField(
        max_length=20,
        default='secondary',
        help_text="Bootstrap color class (primary, success, warning, danger, etc.)"
    )
    icon = models.CharField(
        max_length=50,
        default='bi-circle',
        help_text="Bootstrap icon class"
    )
    
    # Workflow
    is_terminal_state = models.BooleanField(
        default=False,
        help_text="Whether this is a final state (no further processing)"
    )
    is_error_state = models.BooleanField(
        default=False,
        help_text="Whether this represents an error condition"
    )
    can_retry_from = models.BooleanField(
        default=False,
        help_text="Whether generation can be retried from this state"
    )
    can_edit_from = models.BooleanField(
        default=True,
        help_text="Whether the image can be edited in this state"
    )
    
    # Progress
    progress_percentage = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Progress percentage (0-100) for this status"
    )
    
    # Standard fields
    is_active = models.BooleanField(
        default=True,
        db_index=True
    )
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'bfagent'
        db_table = 'illustration_image_statuses'
        ordering = ['order', 'name']
        verbose_name = 'Image Status'
        verbose_name_plural = 'Image Statuses'
    
    def __str__(self):
        return self.name
