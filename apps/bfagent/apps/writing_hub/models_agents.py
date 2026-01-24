"""
Universal Agent Architecture Models
Defines agent roles, LLM tiers, and pipeline configurations.
"""

from django.db import models
from django.utils import timezone


class AgentRole(models.Model):
    """
    Universal agent roles that work across all content types.
    
    Core roles: Researcher, Writer, Reviewer, Critic, Quality Manager
    Specialized: Character Writer, POV Writer, Dialog Writer, etc.
    """
    
    ROLE_CATEGORY_CHOICES = [
        ('core', 'Core Role'),
        ('writer_specialized', 'Specialized Writer'),
        ('domain_specific', 'Domain Specific'),
    ]
    
    code = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    name_de = models.CharField(max_length=100)
    category = models.CharField(max_length=30, choices=ROLE_CATEGORY_CHOICES, default='core')
    description = models.TextField()
    description_de = models.TextField(blank=True)
    
    # Base configuration
    base_system_prompt = models.TextField(help_text="Base system prompt, can be overridden per content type")
    
    # UI
    icon = models.CharField(max_length=50, default='bi-robot')
    color = models.CharField(max_length=20, default='#6366f1')
    
    # Parent role for specializations (e.g., CharacterWriter -> Writer)
    parent_role = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='specializations'
    )
    
    # Ordering and status
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'writing_hub_agent_roles'
        ordering = ['sort_order', 'name']
        verbose_name = 'Agent Role'
        verbose_name_plural = 'Agent Roles'
    
    def __str__(self):
        if self.parent_role:
            return f"{self.name} ({self.parent_role.name})"
        return self.name


class LlmTier(models.Model):
    """
    LLM tier configuration for cost/quality management.
    
    Tiers: Bulk (cheap/free), Standard (balanced), Premium (best quality)
    """
    
    code = models.CharField(max_length=20, unique=True)  # bulk, standard, premium
    name = models.CharField(max_length=50)
    name_de = models.CharField(max_length=50)
    description = models.TextField()
    
    # Default LLM for this tier
    default_llm = models.ForeignKey(
        'bfagent.Llms',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tier_default'
    )
    
    # Cost and priority
    cost_factor = models.FloatField(default=1.0, help_text="Relative cost multiplier")
    priority = models.IntegerField(default=0, help_text="Higher = better quality")
    
    # Default parameters for this tier
    default_temperature = models.FloatField(default=0.7)
    default_max_tokens = models.IntegerField(default=2000)
    
    # UI
    icon = models.CharField(max_length=50, default='bi-cpu')
    color = models.CharField(max_length=20, default='#6b7280')
    badge_class = models.CharField(max_length=50, default='bg-secondary')
    
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'writing_hub_llm_tiers'
        ordering = ['sort_order']
        verbose_name = 'LLM Tier'
        verbose_name_plural = 'LLM Tiers'
    
    def __str__(self):
        return f"{self.name} (x{self.cost_factor})"


class AgentRoleContentConfig(models.Model):
    """
    Content-type specific configuration for agent roles.
    Allows different prompts/settings per content type (novel, essay, scientific).
    """
    
    agent_role = models.ForeignKey(AgentRole, on_delete=models.CASCADE, related_name='content_configs')
    content_type = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Content type code: novel, essay, scientific"
    )
    
    # Override system prompt for this content type
    system_prompt_override = models.TextField(blank=True, help_text="If empty, uses base_system_prompt")
    
    # Default tier for this role+content combination
    default_tier = models.ForeignKey(LlmTier, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Generation parameters override
    temperature_override = models.FloatField(null=True, blank=True)
    max_tokens_override = models.IntegerField(null=True, blank=True)
    
    # Is this role applicable for this content type?
    is_applicable = models.BooleanField(default=True)
    is_required = models.BooleanField(default=False, help_text="Must be used in pipeline")
    
    class Meta:
        db_table = 'writing_hub_agent_role_content_configs'
        unique_together = ['agent_role', 'content_type']
        verbose_name = 'Agent Role Content Config'
        verbose_name_plural = 'Agent Role Content Configs'
    
    def __str__(self):
        return f"{self.agent_role.name} → {self.content_type.name}"
    
    def get_system_prompt(self):
        """Get effective system prompt"""
        return self.system_prompt_override or self.agent_role.base_system_prompt
    
    def get_temperature(self):
        """Get effective temperature"""
        if self.temperature_override is not None:
            return self.temperature_override
        if self.default_tier:
            return self.default_tier.default_temperature
        return 0.7
    
    def get_max_tokens(self):
        """Get effective max tokens"""
        if self.max_tokens_override is not None:
            return self.max_tokens_override
        if self.default_tier:
            return self.default_tier.default_max_tokens
        return 2000


class ProjectAgentConfig(models.Model):
    """
    Project-specific agent configuration overrides.
    Allows users to customize which agents/LLMs are used per project.
    """
    
    project = models.ForeignKey(
        'bfagent.BookProjects',
        on_delete=models.CASCADE,
        related_name='agent_configs'
    )
    agent_role = models.ForeignKey(AgentRole, on_delete=models.CASCADE)
    
    # Override LLM for this project+role
    llm_override = models.ForeignKey(
        'bfagent.Llms',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Override default LLM for this role"
    )
    
    # Override tier
    tier_override = models.ForeignKey(
        LlmTier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Override default tier for this role"
    )
    
    # Custom system prompt addition (appended to base)
    custom_instructions = models.TextField(blank=True, help_text="Additional instructions for this project")
    
    # Enable/disable this agent for the project
    is_enabled = models.BooleanField(default=True)
    
    # Usage tracking
    total_calls = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)
    total_cost = models.FloatField(default=0.0)
    last_used_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'writing_hub_project_agent_configs'
        unique_together = ['project', 'agent_role']
        verbose_name = 'Project Agent Config'
        verbose_name_plural = 'Project Agent Configs'
    
    def __str__(self):
        return f"{self.project.title} - {self.agent_role.name}"


class AgentPipelineTemplate(models.Model):
    """
    Predefined pipeline templates for different tasks.
    E.g., "Write Chapter", "Review Document", "Generate Outline"
    """
    
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    name_de = models.CharField(max_length=100)
    description = models.TextField()
    
    # Which content types this pipeline applies to (JSON list)
    content_types = models.JSONField(
        default=list,
        blank=True,
        help_text="List of content type codes: ['novel', 'essay', 'scientific']"
    )
    
    # Pipeline configuration (JSON)
    # Format: [{"agent_role": "researcher", "tier": "bulk", "order": 1}, ...]
    pipeline_config = models.JSONField(default=list)
    
    # Estimated metrics
    estimated_duration_seconds = models.IntegerField(default=60)
    estimated_cost_factor = models.FloatField(default=1.0)
    
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'writing_hub_agent_pipeline_templates'
        ordering = ['sort_order', 'name']
        verbose_name = 'Agent Pipeline Template'
        verbose_name_plural = 'Agent Pipeline Templates'
    
    def __str__(self):
        return self.name


class AgentPipelineExecution(models.Model):
    """
    Tracks execution of agent pipelines.
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    project = models.ForeignKey(
        'bfagent.BookProjects',
        on_delete=models.CASCADE,
        related_name='pipeline_executions'
    )
    pipeline_template = models.ForeignKey(
        AgentPipelineTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # What triggered this pipeline
    trigger_type = models.CharField(max_length=50)  # manual, auto, scheduled
    trigger_context = models.JSONField(default=dict)  # chapter_id, etc.
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    current_step = models.IntegerField(default=0)
    total_steps = models.IntegerField(default=0)
    
    # Results
    output = models.JSONField(default=dict)
    error_message = models.TextField(blank=True)
    
    # Metrics
    total_tokens_used = models.IntegerField(default=0)
    total_cost = models.FloatField(default=0.0)
    duration_seconds = models.FloatField(default=0.0)
    
    # Timestamps
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'writing_hub_agent_pipeline_executions'
        ordering = ['-created_at']
        verbose_name = 'Pipeline Execution'
        verbose_name_plural = 'Pipeline Executions'
    
    def __str__(self):
        return f"{self.project.title} - {self.pipeline_template.name if self.pipeline_template else 'Custom'} ({self.status})"


class AgentPipelineStep(models.Model):
    """
    Individual steps within a pipeline execution.
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),
    ]
    
    execution = models.ForeignKey(
        AgentPipelineExecution,
        on_delete=models.CASCADE,
        related_name='steps'
    )
    agent_role = models.ForeignKey(AgentRole, on_delete=models.CASCADE)
    llm_used = models.ForeignKey(
        'bfagent.Llms',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    tier_used = models.ForeignKey(LlmTier, on_delete=models.SET_NULL, null=True, blank=True)
    
    step_order = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Input/Output
    input_data = models.JSONField(default=dict)
    output_data = models.JSONField(default=dict)
    system_prompt_used = models.TextField(blank=True)
    user_prompt_used = models.TextField(blank=True)
    
    # Metrics
    tokens_used = models.IntegerField(default=0)
    cost = models.FloatField(default=0.0)
    duration_seconds = models.FloatField(default=0.0)
    
    # Error handling
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    
    # Timestamps
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'writing_hub_agent_pipeline_steps'
        ordering = ['execution', 'step_order']
        verbose_name = 'Pipeline Step'
        verbose_name_plural = 'Pipeline Steps'
    
    def __str__(self):
        return f"Step {self.step_order}: {self.agent_role.name} ({self.status})"
