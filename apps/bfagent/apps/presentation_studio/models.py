"""
Presentation Studio Models
Manage PowerPoint presentations and their enhancements
"""

from django.db import models
from django.contrib.auth.models import User
import uuid


class Presentation(models.Model):
    """
    Uploaded PowerPoint presentations
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # File & Metadata
    title = models.CharField(max_length=200, help_text="Presentation title")
    description = models.TextField(blank=True, help_text="Optional description")
    original_file = models.FileField(
        upload_to='presentations/originals/%Y/%m/',
        help_text="Original PPTX file"
    )
    enhanced_file = models.FileField(
        upload_to='presentations/enhanced/%Y/%m/',
        null=True,
        blank=True,
        help_text="Enhanced PPTX file"
    )
    
    # User tracking
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='presentations'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Enhancement tracking
    enhancement_status = models.CharField(
        max_length=20,
        choices=[
            ('uploaded', 'Uploaded'),
            ('analyzing', 'Analyzing'),
            ('ready', 'Ready to Enhance'),
            ('enhancing', 'Enhancing'),
            ('completed', 'Enhanced'),
            ('failed', 'Enhancement Failed')
        ],
        default='uploaded',
        db_index=True
    )
    
    # Stats
    slide_count_original = models.IntegerField(default=0)
    slide_count_enhanced = models.IntegerField(default=0)
    
    # Enhancement history (JSON)
    concepts_added = models.JSONField(
        default=list,
        blank=True,
        help_text="List of concepts added during enhancements"
    )
    
    enhancement_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional enhancement metadata"
    )
    
    # Template Management
    template_collection = models.ForeignKey(
        'TemplateCollection',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='presentations',
        help_text="Template collection used for this presentation"
    )
    
    slide_templates = models.JSONField(
        default=dict,
        blank=True,
        help_text="Analyzed slide templates from this PPTX (legacy/fallback)"
    )
    
    class Meta:
        db_table = 'presentation_studio_presentation'
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['uploaded_by', '-uploaded_at']),
            models.Index(fields=['enhancement_status']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.uploaded_by.username})"
    
    @property
    def is_enhanced(self):
        return self.enhancement_status == 'completed' and bool(self.enhanced_file)
    
    @property
    def slides_added(self):
        if self.slide_count_enhanced > 0:
            return self.slide_count_enhanced - self.slide_count_original
        return 0


class Enhancement(models.Model):
    """
    Enhancement history for presentations
    Tracks each enhancement operation
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    presentation = models.ForeignKey(
        Presentation,
        on_delete=models.CASCADE,
        related_name='enhancements'
    )
    
    # Enhancement details
    enhancement_type = models.CharField(
        max_length=50,
        choices=[
            ('medical', 'Medical Case'),
            ('business', 'Business Strategy'),
            ('scientific', 'Scientific Research'),
            ('technical', 'Technical Documentation'),
            ('custom', 'Custom')
        ],
        help_text="Type of enhancement template used"
    )
    
    enhancement_mode = models.CharField(
        max_length=20,
        choices=[
            ('append', 'Append at End'),
            ('smart', 'Smart Positioning'),
        ],
        default='append'
    )
    
    # Concepts & configuration
    concepts = models.JSONField(
        help_text="List of concepts/slides to add"
    )
    
    configuration = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional configuration options"
    )
    
    # Results
    slides_before = models.IntegerField()
    slides_after = models.IntegerField()
    
    success = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    
    result_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Detailed result data"
    )
    
    # Execution tracking
    executed_at = models.DateTimeField(auto_now_add=True)
    executed_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='presentation_enhancements'
    )
    
    duration_seconds = models.FloatField(
        null=True,
        blank=True,
        help_text="Enhancement execution time"
    )
    
    class Meta:
        db_table = 'presentation_studio_enhancement'
        ordering = ['-executed_at']
        indexes = [
            models.Index(fields=['presentation', '-executed_at']),
            models.Index(fields=['enhancement_type']),
        ]
    
    def __str__(self):
        return f"{self.enhancement_type} on {self.presentation.title} ({self.executed_at})"
    
    @property
    def slides_added_count(self):
        return self.slides_after - self.slides_before


class PreviewSlide(models.Model):
    """
    Preview slide before PPTX conversion
    Allows editing and review before adding to presentation
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    presentation = models.ForeignKey(
        Presentation,
        on_delete=models.CASCADE,
        related_name='preview_slides'
    )
    
    # Ordering
    preview_order = models.IntegerField(
        help_text="Display order in preview list"
    )
    
    # Slide Content
    title = models.CharField(
        max_length=500,
        help_text="Slide title"
    )
    
    content_data = models.JSONField(
        help_text="Full slide content structure (SlideContent format)"
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=[
            ('preview', 'Preview - Not Converted'),
            ('converted', 'Converted to PPTX'),
            ('skipped', 'Skipped'),
        ],
        default='preview',
        db_index=True
    )
    
    # Source tracking
    source_type = models.CharField(
        max_length=50,
        choices=[
            ('markdown', 'Markdown File'),
            ('json', 'JSON File'),
            ('pdf', 'PDF Extract'),
            ('manual', 'Manual Entry'),
        ],
        help_text="Where this preview came from"
    )
    
    source_file_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Original source file name"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    converted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When converted to PPTX"
    )
    
    # Position in PPTX (after conversion)
    pptx_slide_number = models.IntegerField(
        null=True,
        blank=True,
        help_text="Slide number in final PPTX"
    )
    
    class Meta:
        db_table = 'presentation_studio_preview_slide'
        ordering = ['presentation', 'preview_order']
        indexes = [
            models.Index(fields=['presentation', 'status']),
            models.Index(fields=['presentation', 'preview_order']),
        ]
    
    def __str__(self):
        return f"Preview {self.preview_order}: {self.title} ({self.status})"
    
    @property
    def is_converted(self):
        return self.status == 'converted'
    
    @property
    def can_convert(self):
        return self.status == 'preview'


class DesignProfile(models.Model):
    """
    Design/Styling profile for presentations
    Separates visual design from content
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    profile_name = models.CharField(
        max_length=100,
        help_text="e.g. 'Corporate Blue', 'Academic Style'"
    )
    
    # Source
    source_type = models.CharField(
        max_length=50,
        choices=[
            ('extracted', 'Extracted from Upload'),
            ('template', 'System Template'),
            ('custom', 'Custom Created'),
        ]
    )
    
    presentation = models.ForeignKey(
        Presentation,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='design_profiles',
        help_text="Source presentation if extracted"
    )
    
    # Design Data
    colors = models.JSONField(
        default=dict,
        help_text="Color scheme: primary, secondary, accents, text, background"
    )
    
    fonts = models.JSONField(
        default=dict,
        help_text="Font definitions: heading, body, caption"
    )
    
    # Status
    is_system_template = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    class Meta:
        db_table = 'presentation_studio_design_profile'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['source_type']),
            models.Index(fields=['is_system_template']),
        ]
    
    def __str__(self):
        return f"{self.profile_name} ({self.source_type})"
    
    @classmethod
    def get_system_templates(cls):
        """Get all system templates"""
        return cls.objects.filter(is_system_template=True, is_active=True)


class TemplateCollection(models.Model):
    """
    Reusable template collection for consistent branding across presentations
    Allows sharing of slide templates between multiple presentations
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Metadata
    name = models.CharField(
        max_length=200,
        help_text="Template collection name"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of this template collection"
    )
    
    # Organization
    client = models.CharField(
        max_length=200,
        blank=True,
        help_text="Client/Company name"
    )
    project = models.CharField(
        max_length=200,
        blank=True,
        help_text="Project name"
    )
    industry = models.CharField(
        max_length=100,
        blank=True,
        choices=[
            ('tech', 'Technology'),
            ('healthcare', 'Healthcare'),
            ('finance', 'Finance'),
            ('education', 'Education'),
            ('consulting', 'Consulting'),
            ('legal', 'Legal'),
            ('retail', 'Retail'),
            ('manufacturing', 'Manufacturing'),
            ('other', 'Other'),
        ],
        help_text="Industry/sector for this template"
    )
    
    # Template Configuration
    templates = models.JSONField(
        default=dict,
        help_text="Template slide configurations: {template_type: {layout_name, slide_index, ...}}"
    )
    # Format:
    # {
    #     'title_slide': {
    #         'layout_name': 'Title Slide',
    #         'slide_index': 0,
    #         'shape_count': 2,
    #         'has_title': True,
    #         'thumbnail': 'path/to/thumb.png'
    #     },
    #     'content_slide': {...},
    #     'bullet_slide': {...},
    #     'quote_slide': {...}
    # }
    
    # Source PPTX (master template file)
    master_pptx = models.FileField(
        upload_to='template_collections/%Y/%m/',
        help_text="Master PPTX file containing all template slides"
    )
    
    # Metadata
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='template_collections'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Settings
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this collection is available for use"
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Use as default for new presentations"
    )
    is_system = models.BooleanField(
        default=False,
        help_text="System-provided template (cannot be deleted)"
    )
    
    # Usage stats
    usage_count = models.IntegerField(
        default=0,
        help_text="Number of presentations using this collection"
    )
    
    class Meta:
        db_table = 'presentation_studio_template_collection'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['client']),
            models.Index(fields=['industry']),
            models.Index(fields=['is_active', 'is_default']),
        ]
        verbose_name = "Template Collection"
        verbose_name_plural = "Template Collections"
    
    def __str__(self):
        if self.client:
            return f"{self.name} ({self.client})"
        return self.name
    
    @property
    def template_count(self):
        """Number of templates in this collection"""
        return len(self.templates)
    
    @property
    def presentation_count(self):
        """Number of presentations using this collection"""
        return self.presentations.count()
    
    @classmethod
    def get_default(cls):
        """Get the default template collection"""
        return cls.objects.filter(is_default=True, is_active=True).first()
    
    @classmethod
    def get_for_client(cls, client_name):
        """Get template collections for a specific client"""
        return cls.objects.filter(client__iexact=client_name, is_active=True)
    
    def increment_usage(self):
        """Increment usage counter"""
        self.usage_count += 1
        self.save(update_fields=['usage_count'])
