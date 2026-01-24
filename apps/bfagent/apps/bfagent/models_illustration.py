"""
AI-Powered Illustration System Models
Type-safe Django models for image generation & management
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator


class ArtStyle(models.TextChoices):
    """Kunstrichtungen für Style Profiles"""
    REALISTIC = 'realistic', 'Realistic Photography'
    WATERCOLOR = 'watercolor', 'Watercolor'
    DIGITAL_ART = 'digital_art', 'Digital Art'
    VECTOR = 'vector', 'Vector Art'
    TECHNICAL = 'technical', 'Technical Drawing'
    ILLUSTRATION = 'illustration', 'Illustration'
    PHOTOGRAPHY = 'photography', 'Photography'
    SKETCH = 'sketch', 'Sketch'
    OIL_PAINTING = 'oil_painting', 'Oil Painting'
    ANIME = 'anime', 'Anime'
    COMIC = 'comic', 'Comic Book'


class ImageType(models.TextChoices):
    """Bild-Typen für verschiedene Anwendungsfälle"""
    COVER = 'cover', 'Book Cover'
    CHAPTER_HEADER = 'chapter_header', 'Chapter Header'
    SCENE_ILLUSTRATION = 'scene_illustration', 'Scene Illustration'
    CHARACTER_PORTRAIT = 'character_portrait', 'Character Portrait'
    LOCATION = 'location', 'Location Shot'
    DIAGRAM = 'diagram', 'Diagram'
    INFOGRAPHIC = 'infographic', 'Infographic'
    TECHNICAL_DRAWING = 'technical_drawing', 'Technical Drawing'
    CHART = 'chart', 'Chart'
    ICON = 'icon', 'Icon'
    FULL_PAGE = 'full_page', 'Full Page Illustration'


class AIProvider(models.TextChoices):
    """Unterstützte AI-Provider"""
    DALLE3 = 'dalle3', 'DALL-E 3 (OpenAI)'
    STABILITY = 'stability', 'Stability AI (Direct)'
    STABLE_DIFFUSION = 'stable_diffusion', 'Stable Diffusion (Replicate)'
    MIDJOURNEY = 'midjourney', 'Midjourney'
    LEONARDO = 'leonardo', 'Leonardo AI'
    ADOBE_FIREFLY = 'adobe_firefly', 'Adobe Firefly'


class ImageStatus(models.TextChoices):
    """Status eines generierten Bildes"""
    PENDING = 'pending', 'Pending'
    GENERATING = 'generating', 'Generating'
    GENERATED = 'generated', 'Generated'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'
    ARCHIVED = 'archived', 'Archived'
    ERROR = 'error', 'Error'


class ImageStyleProfile(models.Model):
    """
    Style Profile für konsistente Bildgenerierung
    Definiert visuellen Stil über ein ganzes Projekt hinweg
    """
    # Basic Info
    style_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique style identifier"
    )
    display_name = models.CharField(
        max_length=200,
        help_text="Human-readable name"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed description of the style"
    )

    # Style Settings
    art_style = models.CharField(
        max_length=50,
        choices=ArtStyle.choices,
        default=ArtStyle.DIGITAL_ART
    )
    color_mood = models.CharField(
        max_length=500,
        help_text="Color palette description (e.g., 'pastel', 'vibrant')"
    )
    base_prompt = models.TextField(
        help_text="Base prompt template for this style"
    )
    negative_prompt = models.TextField(
        blank=True,
        null=True,
        help_text="Things to avoid in generation"
    )

    # Technical Settings
    default_resolution = models.CharField(
        max_length=20,
        default="1024x1024",
        help_text="Default image size (e.g., 1024x1024)"
    )
    default_quality = models.CharField(
        max_length=20,
        default="standard",
        choices=[('standard', 'Standard'), ('hd', 'HD')],
        help_text="Quality setting"
    )
    preferred_provider = models.CharField(
        max_length=50,
        choices=AIProvider.choices,
        default=AIProvider.DALLE3
    )

    # Consistency Settings
    consistency_weight = models.FloatField(
        default=0.8,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="How strict style consistency is (0.0-1.0)"
    )
    style_strength = models.FloatField(
        default=0.7,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="How strong the style is applied (0.0-1.0)"
    )
    seed = models.IntegerField(
        blank=True,
        null=True,
        help_text="Fixed seed for reproducibility"
    )

    # Reference Images
    reference_images = models.JSONField(
        default=list,
        blank=True,
        help_text="URLs to reference images"
    )

    # Metadata
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Tags for categorization"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='illustration_styles'
    )
    project = models.ForeignKey(
        'BookProjects',
        on_delete=models.CASCADE,
        related_name='illustration_styles',
        null=True,
        blank=True,
        help_text="Optional: Link to specific project"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.CharField(max_length=20, default="1.0.0")

    # Stats
    usage_count = models.IntegerField(
        default=0,
        help_text="How many times this style was used"
    )
    total_cost_usd = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0,
        help_text="Total cost for images generated with this style"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Image Style Profile"
        verbose_name_plural = "Image Style Profiles"

    def __str__(self):
        return f"{self.display_name} ({self.art_style})"


class IllustrationImage(models.Model):
    """
    Generiertes Bild mit allen Metadaten (Legacy Illustration System)
    """
    # Basic Info
    image_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique image identifier"
    )
    image_type = models.CharField(
        max_length=50,
        choices=ImageType.choices,
        default=ImageType.SCENE_ILLUSTRATION
    )
    status = models.CharField(
        max_length=20,
        choices=ImageStatus.choices,
        default=ImageStatus.PENDING
    )

    # Relations
    style_profile = models.ForeignKey(
        ImageStyleProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_images'
    )
    project = models.ForeignKey(
        'BookProjects',
        on_delete=models.CASCADE,
        related_name='generated_images',
        null=True,
        blank=True,
        help_text="Optional: Project this image belongs to"
    )
    chapter = models.ForeignKey(
        'BookChapters',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='illustrations',
        help_text="Optional: Link to specific chapter"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='illustration_images'
    )

    # Generation Info
    provider_used = models.CharField(
        max_length=50,
        choices=AIProvider.choices,
        help_text="AI Provider used for generation"
    )
    prompt_used = models.TextField(
        help_text="Actual prompt sent to AI"
    )
    negative_prompt_used = models.TextField(
        blank=True,
        null=True,
        help_text="Negative prompt used"
    )

    # Image Data
    image_url = models.TextField(
        help_text="URL to generated image"
    )
    image_file = models.ImageField(
        upload_to='illustrations/%Y/%m/%d/',
        null=True,
        blank=True,
        help_text="Downloaded image file (optional)"
    )
    thumbnail_url = models.TextField(
        blank=True,
        null=True,
        help_text="URL to thumbnail"
    )

    # Technical Details
    resolution = models.CharField(
        max_length=20,
        help_text="Image resolution (e.g., 1024x1024)"
    )
    quality = models.CharField(
        max_length=20,
        help_text="Quality setting used"
    )
    seed = models.IntegerField(
        null=True,
        blank=True,
        help_text="Seed used for generation"
    )

    # Generation Metrics
    generation_time_seconds = models.FloatField(
        null=True,
        blank=True,
        help_text="Time taken to generate"
    )
    cost_usd = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0,
        help_text="Cost of this image"
    )
    retry_count = models.IntegerField(
        default=0,
        help_text="Number of retries needed"
    )

    # Content Context (from ContentContext model)
    content_context = models.JSONField(
        default=dict,
        blank=True,
        help_text="Content context data"
    )

    # Quality Metrics
    quality_score = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="AI-assessed quality score (0.0-1.0)"
    )
    user_rating = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="User rating (1-5 stars)"
    )

    # Approval
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_images'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)

    # Metadata
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Tags for categorization"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata"
    )

    # Error Handling
    error_message = models.TextField(
        blank=True,
        null=True,
        help_text="Error message if generation failed"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bfagent_generatedimage'  # Use existing table
        ordering = ['-created_at']
        verbose_name = "Illustration Image (Legacy)"
        verbose_name_plural = "Illustration Images (Legacy)"
        indexes = [
            models.Index(fields=['project', 'status']),
            models.Index(fields=['image_type', 'status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.get_image_type_display()} - {self.image_id}"

    def approve(self, user):
        """Approve this image"""
        self.status = ImageStatus.APPROVED
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save()

    def reject(self, reason=None):
        """Reject this image"""
        self.status = ImageStatus.REJECTED
        self.rejection_reason = reason
        self.save()

    @property
    def is_approved(self):
        return self.status == ImageStatus.APPROVED

    @property
    def content_summary(self):
        """Get summary from content_context"""
        context = self.content_context
        if not context:
            return "No context"
        parts = []
        if context.get('setting'):
            parts.append(f"Setting: {context['setting']}")
        if context.get('characters'):
            parts.append(f"Characters: {', '.join(context['characters'][:3])}")
        if context.get('mood'):
            parts.append(f"Mood: {context['mood']}")
        return ' | '.join(parts) if parts else "Context available"


class ImageGenerationBatch(models.Model):
    """
    Batch-Generierung von mehreren Bildern
    Für effiziente Massen-Generierung
    """
    batch_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique batch identifier"
    )
    name = models.CharField(
        max_length=200,
        help_text="Batch name"
    )
    description = models.TextField(blank=True, null=True)

    # Relations
    project = models.ForeignKey(
        'BookProjects',
        on_delete=models.CASCADE,
        related_name='image_batches'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='image_batches'
    )

    # Batch Settings
    style_profile = models.ForeignKey(
        ImageStyleProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    image_type = models.CharField(
        max_length=50,
        choices=ImageType.choices
    )
    provider = models.CharField(
        max_length=50,
        choices=AIProvider.choices
    )

    # Progress Tracking
    total_images = models.IntegerField(
        help_text="Total images to generate"
    )
    generated_count = models.IntegerField(
        default=0,
        help_text="Successfully generated"
    )
    failed_count = models.IntegerField(
        default=0,
        help_text="Failed generations"
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('running', 'Running'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
            ('cancelled', 'Cancelled'),
        ],
        default='pending'
    )

    # Cost Tracking
    total_cost_usd = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0
    )
    estimated_cost_usd = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Image Generation Batch"
        verbose_name_plural = "Image Generation Batches"

    def __str__(self):
        return f"{self.name} ({self.generated_count}/{self.total_images})"

    @property
    def progress_percentage(self):
        if self.total_images == 0:
            return 0
        return int((self.generated_count / self.total_images) * 100)
