"""
Feature Documentation System - Link Features to Documentation Files

Allows features to have associated documentation:
- MD files from docs/ folder
- Design documents
- Implementation guides
- Architecture diagrams
- Meeting notes
"""

from django.db import models
from django.core.validators import FileExtensionValidator
from .models_registry import ComponentRegistry


class FeatureDocument(models.Model):
    """
    Documentation file associated with a feature
    
    Can be auto-discovered from docs/ folder or manually uploaded.
    """
    
    # === RELATIONSHIPS ===
    feature = models.ForeignKey(
        ComponentRegistry,
        on_delete=models.CASCADE,
        related_name='documents',
        help_text="Feature this document belongs to"
    )
    
    # === FILE INFORMATION ===
    title = models.CharField(
        max_length=200,
        help_text="Document title (e.g., 'Architecture Overview')"
    )
    
    file_path = models.CharField(
        max_length=500,
        blank=True,
        help_text="Relative path to file in repository (e.g., docs/HANDLER_SYSTEM.md)"
    )
    
    uploaded_file = models.FileField(
        upload_to='feature_docs/%Y/%m/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['md', 'pdf', 'txt', 'docx', 'png', 'jpg', 'svg'])],
        help_text="Uploaded document file (optional if file_path is set)"
    )
    
    # === DOCUMENT METADATA ===
    document_type = models.CharField(
        max_length=20,
        choices=[
            ('design', 'Design Document'),
            ('architecture', 'Architecture Document'),
            ('guide', 'Implementation Guide'),
            ('reference', 'Reference Documentation'),
            ('spec', 'Technical Specification'),
            ('notes', 'Meeting Notes'),
            ('diagram', 'Diagram/Visualization'),
            ('other', 'Other'),
        ],
        default='other',
        help_text="Type of document"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Brief description of what this document contains"
    )
    
    # === DISCOVERY ===
    is_auto_discovered = models.BooleanField(
        default=False,
        help_text="Was this document auto-discovered from docs/ folder?"
    )
    
    discovered_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When was this document linked to the feature?"
    )
    
    # === CONTENT METADATA ===
    file_size = models.IntegerField(
        default=0,
        help_text="File size in bytes"
    )
    
    word_count = models.IntegerField(
        default=0,
        help_text="Approximate word count (for text documents)"
    )
    
    last_modified = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last modification time of the file"
    )
    
    # === ORDERING ===
    order = models.IntegerField(
        default=0,
        help_text="Display order (lower = first)"
    )
    
    class Meta:
        db_table = 'bfagent_feature_document'
        ordering = ['order', '-discovered_at']
        unique_together = [['feature', 'file_path']]
        indexes = [
            models.Index(fields=['feature', 'document_type']),
            models.Index(fields=['is_auto_discovered']),
        ]
    
    def __str__(self):
        return f"{self.feature.name}: {self.title}"
    
    @property
    def file_extension(self):
        """Get file extension"""
        if self.file_path:
            return self.file_path.split('.')[-1].lower()
        elif self.uploaded_file:
            return self.uploaded_file.name.split('.')[-1].lower()
        return ''
    
    @property
    def is_markdown(self):
        """Check if this is a markdown file"""
        return self.file_extension == 'md'
    
    @property
    def is_image(self):
        """Check if this is an image file"""
        return self.file_extension in ['png', 'jpg', 'jpeg', 'svg', 'gif']
    
    @property
    def display_icon(self):
        """Get Bootstrap icon for file type"""
        icons = {
            'md': 'file-text',
            'pdf': 'file-pdf',
            'txt': 'file-text',
            'docx': 'file-word',
            'png': 'file-image',
            'jpg': 'file-image',
            'jpeg': 'file-image',
            'svg': 'file-image',
        }
        return icons.get(self.file_extension, 'file-earmark')


class FeatureDocumentKeyword(models.Model):
    """
    Keywords for document discovery
    
    Maps keywords to features for automatic document association.
    Example: "handler" keyword → HandlerSystemRefactoring feature
    """
    
    feature = models.ForeignKey(
        ComponentRegistry,
        on_delete=models.CASCADE,
        related_name='discovery_keywords',
        help_text="Feature to associate with"
    )
    
    keyword = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Keyword to search for in filenames and content"
    )
    
    keyword_type = models.CharField(
        max_length=20,
        choices=[
            ('filename', 'In Filename'),
            ('content', 'In Content'),
            ('both', 'In Both'),
        ],
        default='both',
        help_text="Where to search for this keyword"
    )
    
    weight = models.IntegerField(
        default=1,
        help_text="Weight for relevance scoring (higher = more relevant)"
    )
    
    class Meta:
        db_table = 'bfagent_feature_document_keyword'
        unique_together = [['feature', 'keyword']]
        indexes = [
            models.Index(fields=['keyword', 'keyword_type']),
        ]
    
    def __str__(self):
        return f"{self.feature.name}: {self.keyword}"
