"""
Context Enrichment Models
Database-driven schemas for dynamic context enrichment in handlers.

Purpose:
    - Define reusable context enrichment schemas
    - Configure data sources without code changes
    - Enable UI-based schema management
    - Support pre-loaded default schemas
"""

from django.db import models
from django.core.exceptions import ValidationError
import json


class ContextSchema(models.Model):
    """
    Defines a complete context enrichment schema for handlers.
    
    Examples:
        - chapter_generation: Context for chapter outline generation
        - character_enrichment: Context for character development
        - world_building: Context for world/setting enrichment
    """
    
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique identifier for the schema (e.g., 'chapter_generation')"
    )
    display_name = models.CharField(
        max_length=200,
        help_text="Human-readable name for UI display"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description of what this schema does"
    )
    handler_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="Handler this schema is designed for (e.g., 'ChapterGenerateHandler')"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this schema is currently active"
    )
    is_system = models.BooleanField(
        default=False,
        help_text="System schemas are pre-loaded and cannot be deleted"
    )
    
    version = models.CharField(
        max_length=20,
        default="1.0.0",
        help_text="Schema version for tracking changes"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Context Schema"
        verbose_name_plural = "Context Schemas"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.display_name} ({self.name})"
    
    def get_active_sources(self):
        """Get all active sources for this schema ordered by priority"""
        return self.sources.filter(is_active=True).order_by('order')
    
    def validate_schema(self):
        """Validate schema configuration"""
        sources = self.get_active_sources()
        if not sources.exists():
            raise ValidationError("Schema must have at least one active source")
        return True


class ContextSource(models.Model):
    """
    Individual data source for context enrichment.
    
    Source Types:
        - model: Fetch data from a Django model (primary key)
        - related_query: Query related data with filters
        - computed: Calculate values using custom functions
        - aggregation: Aggregate data from multiple records
        - external_api: Call external APIs (future)
        - custom: Custom Python function
    """
    
    SOURCE_TYPES = [
        ('model', 'Django Model (PK)'),
        ('related_query', 'Related Query (Filter)'),
        ('computed', 'Computed Value'),
        ('aggregation', 'Aggregation (Count/Sum/etc)'),
        ('beat_sheet', 'Beat Sheet Mapping'),
        ('custom', 'Custom Function'),
    ]
    
    AGGREGATE_TYPES = [
        ('first', 'First Result'),
        ('last', 'Last Result'),
        ('all', 'All Results (QuerySet)'),
        ('list', 'List of Dicts'),
        ('count', 'Count'),
        ('exists', 'Boolean Exists'),
    ]
    
    schema = models.ForeignKey(
        ContextSchema,
        on_delete=models.CASCADE,
        related_name='sources'
    )
    
    name = models.CharField(
        max_length=100,
        help_text="Descriptive name for this source"
    )
    source_type = models.CharField(
        max_length=20,
        choices=SOURCE_TYPES,
        help_text="Type of data source"
    )
    order = models.IntegerField(
        default=0,
        help_text="Execution order (lower runs first)"
    )
    
    # Model Configuration
    model_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Django model name (e.g., 'BookProjects', 'Characters')"
    )
    
    # Query Configuration (JSON)
    filter_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Filter parameters for queries (supports {param} placeholders)"
    )
    
    # Field Selection (JSON)
    fields = models.JSONField(
        default=list,
        blank=True,
        help_text="Fields to extract from model instances"
    )
    
    # Field Mapping (JSON)
    field_mappings = models.JSONField(
        default=dict,
        blank=True,
        help_text="Map source fields to context keys (source_field: context_key)"
    )
    
    # Aggregation
    aggregate_type = models.CharField(
        max_length=20,
        choices=AGGREGATE_TYPES,
        default='first',
        help_text="How to aggregate multiple results"
    )
    
    # Output Configuration
    context_key = models.CharField(
        max_length=100,
        blank=True,
        help_text="Key to use in context dict (if not merging fields)"
    )
    
    # Computed Function
    function_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Name of computation function (for computed type)"
    )
    function_params = models.JSONField(
        default=dict,
        blank=True,
        help_text="Parameters for computation function"
    )
    
    # Ordering
    order_by = models.CharField(
        max_length=100,
        blank=True,
        help_text="Field to order results by (use '-field' for descending)"
    )
    
    # Defaults & Fallbacks
    default_value = models.JSONField(
        null=True,
        blank=True,
        help_text="Default value if source returns nothing"
    )
    
    is_required = models.BooleanField(
        default=False,
        help_text="If True, enrichment fails if this source fails"
    )
    
    fallback_value = models.JSONField(
        null=True,
        blank=True,
        help_text="Fallback value if source fails (when not required)"
    )
    
    timeout_seconds = models.IntegerField(
        default=5,
        help_text="Maximum time to wait for this source (in seconds)"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this source is active"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Context Source"
        verbose_name_plural = "Context Sources"
        ordering = ['schema', 'order', 'name']
        unique_together = [['schema', 'order']]
    
    def __str__(self):
        return f"{self.schema.name} → {self.name} ({self.source_type})"
    
    def get_config_display(self):
        """Get readable config for admin display"""
        config = {
            'type': self.source_type,
            'model': self.model_name,
            'context_key': self.context_key or 'merged',
        }
        if self.filter_config:
            config['filter'] = self.filter_config
        return json.dumps(config, indent=2)


class ContextEnrichmentLog(models.Model):
    """
    Log of context enrichment executions for debugging and monitoring.
    """
    
    schema = models.ForeignKey(
        ContextSchema,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    
    handler_name = models.CharField(max_length=100)
    params = models.JSONField(default=dict)
    enriched_context = models.JSONField(default=dict)
    
    execution_time_ms = models.FloatField(
        help_text="Execution time in milliseconds"
    )
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Context Enrichment Log"
        verbose_name_plural = "Context Enrichment Logs"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['schema', '-created_at']),
        ]
    
    def __str__(self):
        status = "✓" if self.success else "✗"
        return f"{status} {self.schema.name} @ {self.created_at.strftime('%Y-%m-%d %H:%M')}"
