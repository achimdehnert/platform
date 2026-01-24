"""
Component Registry Models
Universal registry for all system components (handlers, views, models, etc.)
Extends the existing HandlerRegistry concept.
"""
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.db.models import Q, Avg, Count, F
from typing import Dict, List, Optional
import json


class ComponentType(models.TextChoices):
    """All trackable component types in the system"""
    HANDLER = 'handler', 'Handler'
    VIEW = 'view', 'View/URL'
    MODEL = 'model', 'Django Model'
    FORM = 'form', 'Django Form'
    SERIALIZER = 'serializer', 'DRF Serializer'
    API_ENDPOINT = 'api', 'API Endpoint'
    GRAPHQL_TYPE = 'graphql', 'GraphQL Type'
    GRAPHQL_MUTATION = 'graphql_mutation', 'GraphQL Mutation'
    GRAPHQL_QUERY = 'graphql_query', 'GraphQL Query'
    TEMPLATE = 'template', 'Template'
    WORKFLOW = 'workflow', 'Workflow'
    SERVICE = 'service', 'Service Class'
    UTILITY = 'utility', 'Utility Function'
    MIDDLEWARE = 'middleware', 'Middleware'
    COMMAND = 'command', 'Management Command'


class ComponentStatus(models.TextChoices):
    """Component lifecycle status"""
    PROPOSED = 'proposed', '💡 Proposed'
    PLANNED = 'planned', '📋 Planned'
    IN_PROGRESS = 'in_progress', '🚧 In Progress'
    IN_REVIEW = 'in_review', '👀 In Review'
    TESTING = 'testing', '🧪 Testing'
    ACTIVE = 'active', '✅ Active'
    BETA = 'beta', 'Beta'
    EXPERIMENTAL = 'experimental', 'Experimental'
    DEPRECATED = 'deprecated', '⚠️ Deprecated'
    DISABLED = 'disabled', 'Disabled'
    REJECTED = 'rejected', '❌ Rejected'


class ComponentRegistry(models.Model):
    """
    Universal registry for all system components
    
    Tracks handlers, views, models, forms, templates, workflows, etc.
    Provides searchability, dependency tracking, and usage metrics.
    """
    
    # === IDENTITY ===
    identifier = models.CharField(
        max_length=300,
        unique=True,
        db_index=True,
        help_text="Unique identifier (e.g., 'apps.bfagent.handlers.CharacterHandler')"
    )
    
    name = models.CharField(
        max_length=200,
        db_index=True,
        help_text="Human-readable name"
    )
    
    component_type = models.CharField(
        max_length=50,
        choices=ComponentType.choices,
        db_index=True,
        help_text="Type of component"
    )
    
    # === LOCATION ===
    module_path = models.CharField(
        max_length=500,
        help_text="Python module path (e.g., 'apps.bfagent.domains.book_writing.handlers')"
    )
    
    file_path = models.CharField(
        max_length=500,
        help_text="Relative file path from project root"
    )
    
    class_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Class name if applicable"
    )
    
    function_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Function name if applicable"
    )
    
    # === DOMAIN & ORGANIZATION ===
    domain = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text="Domain (e.g., 'book', 'explosion', 'shared')"
    )
    
    category = models.CharField(
        max_length=100,
        blank=True,
        help_text="Category within domain"
    )
    
    # === DOCUMENTATION ===
    description = models.TextField(
        blank=True,
        help_text="Brief description of what this component does"
    )
    
    docstring = models.TextField(
        blank=True,
        help_text="Full docstring from code"
    )
    
    usage_examples = models.JSONField(
        default=list,
        blank=True,
        help_text="List of usage examples"
    )
    
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Searchable tags (e.g., ['character', 'generation', 'llm'])"
    )
    
    # === METADATA (polymorphic) ===
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Type-specific metadata (schema varies by component_type)"
    )
    
    # === DEPENDENCIES ===
    depends_on = models.JSONField(
        default=list,
        blank=True,
        help_text="List of component identifiers this depends on"
    )
    
    required_by = models.JSONField(
        default=list,
        blank=True,
        help_text="List of component identifiers that depend on this"
    )
    
    # === STATUS & VERSION ===
    status = models.CharField(
        max_length=20,
        choices=ComponentStatus.choices,
        default=ComponentStatus.ACTIVE,
        db_index=True
    )
    
    version = models.CharField(
        max_length=50,
        blank=True,
        help_text="Component version"
    )
    
    deprecated_reason = models.TextField(
        blank=True,
        help_text="Why this was deprecated"
    )
    
    replacement_identifier = models.CharField(
        max_length=300,
        blank=True,
        help_text="Identifier of replacement component"
    )
    
    # === USAGE METRICS ===
    usage_count = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Total number of times used"
    )
    
    success_count = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    failure_count = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    avg_execution_time_ms = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Average execution time in milliseconds"
    )
    
    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this component was last used"
    )
    
    # === TIMESTAMPS ===
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    discovered_at = models.DateTimeField(
        default=timezone.now,
        help_text="When this component was discovered/registered"
    )
    
    # === FEATURE PLANNING FIELDS ===
    owner = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_components',
        help_text="Primary developer/owner"
    )
    
    priority = models.CharField(
        max_length=20,
        choices=[
            ('critical', '🔥 Critical'),
            ('high', '🔴 High'),
            ('medium', '🟡 Medium'),
            ('low', '🔵 Low'),
            ('backlog', '📦 Backlog'),
        ],
        default='backlog',
        blank=True,
        help_text="Priority level"
    )
    
    proposed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this component was proposed"
    )
    
    planned_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this component was planned"
    )
    
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When development started"
    )
    
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When development completed"
    )
    
    class Meta:
        db_table = 'bfagent_component_registry'
        verbose_name = 'Component'
        verbose_name_plural = 'Component Registry'
        ordering = ['component_type', 'name']
        indexes = [
            models.Index(fields=['component_type', 'domain']),
            models.Index(fields=['status', 'component_type']),
            models.Index(fields=['-usage_count']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.component_type})"
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        total = self.success_count + self.failure_count
        if total == 0:
            return 100.0
        return (self.success_count / total) * 100
    
    @property
    def health_score(self) -> int:
        """Calculate health score 0-100"""
        if self.status == ComponentStatus.DISABLED:
            return 0
        
        score = 100
        
        # Penalize low success rate
        if self.usage_count > 10:
            score -= max(0, (100 - self.success_rate) * 0.5)
        
        # Penalize deprecated
        if self.status == ComponentStatus.DEPRECATED:
            score -= 30
        
        # Penalize unused
        if self.usage_count == 0:
            score -= 20
        
        return max(0, min(100, int(score)))
    
    def record_usage(self, success: bool = True, execution_time_ms: int = 0):
        """Record a usage event"""
        self.usage_count = F('usage_count') + 1
        self.last_used_at = timezone.now()
        
        if success:
            self.success_count = F('success_count') + 1
        else:
            self.failure_count = F('failure_count') + 1
        
        # Update rolling average
        if execution_time_ms > 0:
            total_time = self.avg_execution_time_ms * (self.usage_count - 1)
            self.avg_execution_time_ms = int((total_time + execution_time_ms) / self.usage_count)
        
        self.save(update_fields=['usage_count', 'success_count', 'failure_count', 
                                 'avg_execution_time_ms', 'last_used_at'])
    
    @classmethod
    def find_similar(cls, search_term: str, component_type: Optional[str] = None) -> List['ComponentRegistry']:
        """Find components similar to search term"""
        query = Q(name__icontains=search_term) | Q(description__icontains=search_term)
        
        # Search in tags
        components = cls.objects.filter(query)
        
        if component_type:
            components = components.filter(component_type=component_type)
        
        return list(components.filter(status=ComponentStatus.ACTIVE).order_by('-usage_count')[:10])


class ComponentUsageLog(models.Model):
    """Detailed log of component usage"""
    
    component = models.ForeignKey(
        ComponentRegistry,
        on_delete=models.CASCADE,
        related_name='usage_logs'
    )
    
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    success = models.BooleanField(default=True)
    
    execution_time_ms = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)]
    )
    
    context = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional context about this usage"
    )
    
    error_message = models.TextField(
        blank=True,
        help_text="Error message if failed"
    )
    
    class Meta:
        db_table = 'bfagent_component_usage_log'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['component', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]
    
    def __str__(self):
        status = "✓" if self.success else "✗"
        return f"{status} {self.component.name} @ {self.timestamp}"


class ComponentChangeLog(models.Model):
    """Track changes to components over time"""
    
    component = models.ForeignKey(
        ComponentRegistry,
        on_delete=models.CASCADE,
        related_name='change_logs'
    )
    
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    change_type = models.CharField(
        max_length=50,
        choices=[
            ('created', 'Created'),
            ('updated', 'Updated'),
            ('deprecated', 'Deprecated'),
            ('reactivated', 'Reactivated'),
            ('deleted', 'Deleted'),
        ]
    )
    
    changes = models.JSONField(
        default=dict,
        help_text="Dict of changed fields: {field: {old: x, new: y}}"
    )
    
    reason = models.TextField(blank=True)
    
    class Meta:
        db_table = 'bfagent_component_change_log'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.change_type}: {self.component.name} @ {self.timestamp}"


# ============================================================================
# MIGRATION REGISTRY MODELS
# ============================================================================

class MigrationRegistry(models.Model):
    """
    Central registry for all Django migrations
    
    Tracks migration metadata, dependencies, schema changes,
    rollback safety, and impact on existing data.
    """
    
    # === IDENTITY ===
    app_label = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Django app name"
    )
    
    migration_name = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Migration filename (e.g., 0001_initial)"
    )
    
    migration_number = models.IntegerField(
        help_text="Extracted migration number"
    )
    
    # === FILE INFORMATION ===
    file_path = models.CharField(
        max_length=500,
        help_text="Relative path to migration file"
    )
    
    file_hash = models.CharField(
        max_length=64,
        help_text="SHA256 hash of migration file content"
    )
    
    # === MIGRATION METADATA ===
    description = models.TextField(
        blank=True,
        help_text="Auto-extracted description from migration"
    )
    
    migration_type = models.CharField(
        max_length=20,
        choices=[
            ('schema', 'Schema Migration'),
            ('data', 'Data Migration'),
            ('mixed', 'Schema + Data'),
            ('empty', 'Empty Migration'),
        ],
        default='schema',
        db_index=True
    )
    
    # === COMPLEXITY & RISK ===
    complexity_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Complexity score 0-100"
    )
    
    is_reversible = models.BooleanField(
        default=True,
        help_text="Can this migration be rolled back?"
    )
    
    requires_downtime = models.BooleanField(
        default=False,
        help_text="Requires downtime to apply?"
    )
    
    # === SCHEMA CHANGES ===
    models_created = models.JSONField(
        default=list,
        blank=True,
        help_text="List of models created"
    )
    
    models_deleted = models.JSONField(
        default=list,
        blank=True,
        help_text="List of models deleted"
    )
    
    fields_added = models.JSONField(
        default=dict,
        blank=True,
        help_text="Dict of fields added per model"
    )
    
    fields_removed = models.JSONField(
        default=dict,
        blank=True,
        help_text="Dict of fields removed per model"
    )
    
    fields_modified = models.JSONField(
        default=dict,
        blank=True,
        help_text="Dict of fields modified per model"
    )
    
    # === DEPENDENCIES ===
    depends_on = models.JSONField(
        default=list,
        blank=True,
        help_text="List of migration dependencies"
    )
    
    # === IMPACT ESTIMATION ===
    estimated_affected_rows = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Estimated number of rows affected"
    )
    
    estimated_duration_seconds = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Estimated duration in seconds"
    )
    
    # === WARNINGS & RISKS ===
    warnings = models.JSONField(
        default=list,
        blank=True,
        help_text="List of warnings"
    )
    
    rollback_risks = models.JSONField(
        default=list,
        blank=True,
        help_text="List of rollback risks"
    )
    
    # === STATUS ===
    is_applied = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Has this migration been applied?"
    )
    
    applied_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When was this migration applied?"
    )
    
    # === TIMESTAMPS ===
    discovered_at = models.DateTimeField(
        default=timezone.now,
        help_text="When was this migration discovered?"
    )
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'bfagent_migration_registry'
        unique_together = [['app_label', 'migration_name']]
        ordering = ['app_label', 'migration_number']
        indexes = [
            models.Index(fields=['app_label', 'migration_number']),
            models.Index(fields=['applied_at']),
            models.Index(fields=['is_applied', 'app_label']),
            models.Index(fields=['complexity_score']),
        ]
    
    def __str__(self):
        status = "✓" if self.is_applied else "⏳"
        return f"{status} {self.app_label}.{self.migration_name}"
    
    @property
    def full_name(self):
        """Full migration identifier"""
        return f"{self.app_label}.{self.migration_name}"
    
    @property
    def risk_level(self):
        """Calculate risk level based on complexity"""
        if self.complexity_score >= 71:
            return 'critical'
        elif self.complexity_score >= 51:
            return 'risky'
        elif self.complexity_score >= 31:
            return 'careful'
        return 'safe'


class MigrationConflict(models.Model):
    """Track migration conflicts and dependency issues"""
    
    migration1 = models.ForeignKey(
        MigrationRegistry,
        on_delete=models.CASCADE,
        related_name='conflicts_as_migration1'
    )
    
    migration2 = models.ForeignKey(
        MigrationRegistry,
        on_delete=models.CASCADE,
        related_name='conflicts_as_migration2'
    )
    
    conflict_type = models.CharField(
        max_length=50,
        choices=[
            ('circular', 'Circular Dependency'),
            ('missing', 'Missing Dependency'),
            ('order', 'Order Conflict'),
        ]
    )
    
    description = models.TextField()
    
    detected_at = models.DateTimeField(auto_now_add=True)
    
    resolved = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'bfagent_migration_conflict'
        ordering = ['-detected_at']
    
    def __str__(self):
        return f"{self.conflict_type}: {self.migration1.full_name} ↔ {self.migration2.full_name}"
