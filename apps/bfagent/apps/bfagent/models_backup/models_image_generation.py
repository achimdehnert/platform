"""Image Generation Models"""

import uuid
from pathlib import Path
from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image as PILImage
from io import BytesIO
from django.core.files.base import ContentFile


class GeneratedImage(models.Model):
    """
    Track generated images with full metadata.
    
    Stores:
    - Generation details (prompt, provider, model)
    - File storage (image + thumbnail)
    - Cost tracking
    - Book/Chapter associations
    - User tracking
    """
    
    PROVIDER_CHOICES = [
        ('openai', 'OpenAI DALL-E'),
        ('stability', 'Stability AI'),
        ('replicate', 'Replicate'),
        ('other', 'Other'),
    ]
    
    QUALITY_CHOICES = [
        ('standard', 'Standard'),
        ('hd', 'HD'),
        ('high', 'High'),
    ]
    
    # === IDENTITY ===
    image_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # === GENERATION DETAILS ===
    prompt = models.TextField(
        help_text="Original prompt used for generation"
    )
    revised_prompt = models.TextField(
        blank=True,
        help_text="AI-revised prompt (if applicable)"
    )
    negative_prompt = models.TextField(
        blank=True,
        help_text="Negative prompt (what to avoid)"
    )
    
    provider = models.CharField(
        max_length=50,
        choices=PROVIDER_CHOICES,
        db_index=True,
        help_text="Provider used to generate image"
    )
    model = models.CharField(
        max_length=100,
        help_text="Model name (e.g., 'dall-e-3', 'sd3')"
    )
    
    # === FILE STORAGE ===
    image_file = models.ImageField(
        upload_to='generated_images/%Y/%m/%d/',
        help_text="Generated image file"
    )
    thumbnail = models.ImageField(
        upload_to='generated_images/thumbnails/%Y/%m/%d/',
        blank=True,
        null=True,
        help_text="Thumbnail (300x300, auto-generated)"
    )
    
    # Original URL from provider (if available)
    original_url = models.URLField(
        max_length=1000,
        blank=True,
        help_text="Original URL from provider"
    )
    
    # === IMAGE METADATA ===
    size = models.CharField(
        max_length=50,
        help_text="Image size (e.g., '1024x1024', '16:9')"
    )
    quality = models.CharField(
        max_length=20,
        choices=QUALITY_CHOICES,
        default='standard'
    )
    style = models.CharField(
        max_length=100,
        blank=True,
        help_text="Style preset (e.g., 'vivid', 'natural')"
    )
    
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    file_size_bytes = models.BigIntegerField(null=True, blank=True)
    
    # === COST & PERFORMANCE ===
    cost_cents = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Generation cost in cents"
    )
    generation_time_seconds = models.FloatField(
        help_text="Time taken to generate image"
    )
    
    # === BOOK/CHAPTER ASSOCIATION ===
    book_id = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Associated book ID (if illustration)"
    )
    chapter_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="Associated chapter ID"
    )
    scene_number = models.IntegerField(
        null=True,
        blank=True,
        help_text="Scene number within chapter"
    )
    scene_description = models.TextField(
        blank=True,
        help_text="Original scene description"
    )
    
    # === HANDLER & USER ===
    handler = models.ForeignKey(
        'Handler',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_images',
        help_text="Handler that generated this image"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_images'
    )
    
    # === STATUS & METADATA ===
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Is image active/visible?"
    )
    is_favorite = models.BooleanField(
        default=False,
        help_text="User marked as favorite"
    )
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Tags: ['illustration', 'book_cover', 'character', etc.]"
    )
    notes = models.TextField(
        blank=True,
        help_text="User notes about this image"
    )
    
    # === GENERATION METADATA ===
    generation_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional generation parameters and metadata"
    )
    
    class Meta:
        db_table = 'generated_images'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['provider', '-created_at']),
            models.Index(fields=['book_id', 'chapter_id', 'scene_number']),
            models.Index(fields=['is_active', '-created_at']),
            models.Index(fields=['-cost_cents']),
        ]
        verbose_name = 'Generated Image'
        verbose_name_plural = 'Generated Images'
    
    def __str__(self):
        if self.book_id:
            return f"Book {self.book_id} - {self.prompt[:50]}"
        return f"{self.provider} - {self.prompt[:50]}"
    
    def save(self, *args, **kwargs):
        # Auto-generate thumbnail on save
        if self.image_file and not self.thumbnail:
            self.create_thumbnail()
        
        # Extract dimensions if not set
        if self.image_file and (not self.width or not self.height):
            self.extract_dimensions()
        
        super().save(*args, **kwargs)
    
    def create_thumbnail(self, size=(300, 300)):
        """
        Create thumbnail from image file.
        
        Args:
            size: Tuple of (width, height) for thumbnail
        """
        if not self.image_file:
            return
        
        try:
            # Open image
            image = PILImage.open(self.image_file)
            
            # Convert RGBA to RGB if necessary
            if image.mode in ('RGBA', 'LA', 'P'):
                background = PILImage.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1])
                image = background
            
            # Create thumbnail
            image.thumbnail(size, PILImage.Resampling.LANCZOS)
            
            # Save to BytesIO
            thumb_io = BytesIO()
            image.save(thumb_io, format='JPEG', quality=85)
            thumb_io.seek(0)
            
            # Generate filename
            filename = f"thumb_{self.image_id}.jpg"
            
            # Save to thumbnail field
            self.thumbnail.save(
                filename,
                ContentFile(thumb_io.read()),
                save=False
            )
        except Exception as e:
            # Log error but don't fail
            print(f"Failed to create thumbnail: {e}")
    
    def extract_dimensions(self):
        """
        Extract width and height from image file.
        """
        if not self.image_file:
            return
        
        try:
            image = PILImage.open(self.image_file)
            self.width, self.height = image.size
            self.file_size_bytes = self.image_file.size
        except Exception as e:
            print(f"Failed to extract dimensions: {e}")
    
    @property
    def cost_usd(self):
        """Return cost in USD"""
        return float(self.cost_cents) / 100
    
    @property
    def aspect_ratio(self):
        """Calculate aspect ratio"""
        if self.width and self.height:
            gcd = self._gcd(self.width, self.height)
            return f"{self.width//gcd}:{self.height//gcd}"
        return self.size
    
    def _gcd(self, a, b):
        """Greatest common divisor"""
        while b:
            a, b = b, a % b
        return a
    
    def get_absolute_url(self):
        """Return detail URL"""
        return reverse('bfagent:image_detail', kwargs={'image_id': self.image_id})
    
    def get_download_url(self):
        """Return download URL"""
        return self.image_file.url if self.image_file else None
    
    def get_thumbnail_url(self):
        """Return thumbnail URL or fallback to original"""
        if self.thumbnail:
            return self.thumbnail.url
        return self.image_file.url if self.image_file else None