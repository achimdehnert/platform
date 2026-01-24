# -*- coding: utf-8 -*-
"""
Orchestration Models für Cascade Router Architecture.

Trackt:
- Parallele Reasoning-Pfade (A/B Test)
- Delegierte Code-Generierungen
- Worker-LLM Aufrufe
"""
import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone


class ReasoningComparison(models.Model):
    """Trackt parallele Reasoning-Pfade für A/B Tests zwischen Cascade und Thinking-Models."""
    
    TASK_CATEGORY_CHOICES = [
        ('coding', 'Coding Task'),
        ('analysis', 'Analysis'),
        ('planning', 'Planning'),
        ('debugging', 'Debugging'),
        ('refactoring', 'Refactoring'),
        ('documentation', 'Documentation'),
        ('other', 'Other'),
    ]
    
    COMPLEXITY_CHOICES = [
        ('simple', 'Simple'),
        ('medium', 'Medium'),
        ('complex', 'Complex'),
    ]
    
    PATH_CHOICES = [
        ('A', 'Cascade Direct'),
        ('B', 'Thinking Model'),
        ('hybrid', 'Hybrid'),
    ]
    
    WINNER_CHOICES = [
        ('A', 'Cascade Won'),
        ('B', 'Thinking Won'),
        ('tie', 'Tie'),
        ('na', 'Not Applicable'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Input
    user_input = models.TextField(help_text="Original User Request")
    task_category = models.CharField(max_length=50, choices=TASK_CATEGORY_CHOICES, default='other')
    complexity_estimate = models.CharField(max_length=20, choices=COMPLEXITY_CHOICES, default='medium')
    
    # Path A: Cascade
    cascade_response = models.TextField(blank=True, null=True)
    cascade_plan = models.JSONField(default=list, help_text="Strukturierter Plan von Cascade")
    cascade_duration_ms = models.IntegerField(null=True, blank=True)
    cascade_tokens = models.IntegerField(default=0)
    
    # Path B: Thinking Model
    thinking_model = models.CharField(max_length=50, blank=True, help_text="o1, gemini-thinking, deepseek-r1")
    thinking_response = models.TextField(blank=True, null=True)
    thinking_plan = models.JSONField(default=list, help_text="Strukturierter Plan vom Thinking Model")
    thinking_duration_ms = models.IntegerField(null=True, blank=True)
    thinking_tokens = models.IntegerField(default=0)
    thinking_reasoning_trace = models.TextField(blank=True, null=True, help_text="Chain-of-Thought Output")
    
    # Comparison
    plans_identical = models.BooleanField(null=True, blank=True)
    similarity_score = models.FloatField(null=True, blank=True, help_text="0-1 Ähnlichkeit der Pläne")
    key_differences = models.JSONField(default=list, help_text="Liste der Hauptunterschiede")
    
    # Selection
    selected_path = models.CharField(max_length=10, choices=PATH_CHOICES, default='A')
    selection_reason = models.TextField(blank=True, null=True)
    
    # Execution Result
    execution_success = models.BooleanField(null=True, blank=True)
    user_satisfaction = models.IntegerField(null=True, blank=True, help_text="1-5 Rating")
    required_iterations = models.IntegerField(default=1)
    
    # Learning
    winner = models.CharField(max_length=10, choices=WINNER_CHOICES, null=True, blank=True)
    learning_notes = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'bfagent_reasoning_comparisons'
        ordering = ['-created_at']
        verbose_name = 'Reasoning Comparison'
        verbose_name_plural = 'Reasoning Comparisons'
    
    def __str__(self):
        return f"[{self.task_category}] {self.user_input[:50]}..."
    
    @property
    def total_duration_ms(self):
        """Gesamtdauer beider Pfade."""
        cascade = self.cascade_duration_ms or 0
        thinking = self.thinking_duration_ms or 0
        return max(cascade, thinking)  # Parallel, also max
    
    @property
    def total_tokens(self):
        return self.cascade_tokens + self.thinking_tokens


class CodeGenerationLog(models.Model):
    """Trackt alle delegierten Code-Generierungen an Worker-LLMs."""
    
    TASK_TYPE_CHOICES = [
        ('template', 'Django Template'),
        ('urls', 'URL Configuration'),
        ('view', 'View'),
        ('model', 'Model'),
        ('form', 'Form'),
        ('serializer', 'Serializer'),
        ('test', 'Test'),
        ('migration', 'Migration'),
        ('admin', 'Admin'),
        ('service', 'Service'),
        ('handler', 'Handler'),
        ('other', 'Other'),
    ]
    
    METHOD_CHOICES = [
        ('pattern', 'Pattern Library'),
        ('llm', 'Worker LLM'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Verknüpfung zu Reasoning (optional)
    reasoning_comparison = models.ForeignKey(
        ReasoningComparison,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='code_generations'
    )
    
    # Task-Info
    task_type = models.CharField(max_length=50, choices=TASK_TYPE_CHOICES)
    component_name = models.CharField(max_length=200)
    output_path = models.CharField(max_length=500)
    
    # Spezifikation
    specification = models.JSONField(default=dict)
    context_provided = models.JSONField(default=dict)
    
    # Execution
    method_used = models.CharField(max_length=20, choices=METHOD_CHOICES)
    worker_model = models.CharField(max_length=50, blank=True, null=True, help_text="grok, codestral, deepseek")
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.IntegerField(null=True, blank=True)
    
    # Result
    success = models.BooleanField(default=False)
    generated_code = models.TextField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    
    # Validation
    syntax_valid = models.BooleanField(null=True, blank=True)
    validation_errors = models.JSONField(default=list)
    
    # Kosten
    tokens_used = models.IntegerField(default=0)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=6, default=Decimal('0'))
    
    # Cascade Feedback
    cascade_accepted = models.BooleanField(null=True, blank=True)
    cascade_modified = models.BooleanField(null=True, blank=True)
    cascade_notes = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'bfagent_code_generation_logs'
        ordering = ['-started_at']
        verbose_name = 'Code Generation Log'
        verbose_name_plural = 'Code Generation Logs'
        indexes = [
            models.Index(fields=['task_type', 'success']),
            models.Index(fields=['method_used']),
            models.Index(fields=['worker_model']),
        ]
    
    def __str__(self):
        return f"[{self.task_type}] {self.component_name}"


class WorkerLLMConfig(models.Model):
    """Konfiguration für Worker-LLMs."""
    
    name = models.CharField(max_length=50, unique=True, help_text="grok, codestral, deepseek")
    display_name = models.CharField(max_length=100)
    
    # API Config
    api_url = models.URLField()
    model_id = models.CharField(max_length=100)
    api_key_env_var = models.CharField(max_length=100, help_text="Name der Environment Variable")
    
    # Limits
    max_tokens = models.IntegerField(default=4000)
    temperature = models.FloatField(default=0.1)
    
    # Kosten
    cost_per_1k_input_tokens = models.DecimalField(max_digits=10, decimal_places=6, default=Decimal('0.001'))
    cost_per_1k_output_tokens = models.DecimalField(max_digits=10, decimal_places=6, default=Decimal('0.002'))
    
    # Capabilities
    supports_streaming = models.BooleanField(default=True)
    best_for = models.JSONField(default=list, help_text="Task-Types wo dieses Model gut ist")
    
    # Status
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=10, help_text="Niedrigere Zahl = höhere Priorität")
    
    # Stats (aggregiert)
    total_calls = models.IntegerField(default=0)
    successful_calls = models.IntegerField(default=0)
    total_tokens_used = models.BigIntegerField(default=0)
    total_cost = models.DecimalField(max_digits=12, decimal_places=6, default=Decimal('0'))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'bfagent_worker_llm_configs'
        ordering = ['priority', 'name']
        verbose_name = 'Worker LLM Config'
        verbose_name_plural = 'Worker LLM Configs'
    
    def __str__(self):
        return f"{self.display_name} ({self.name})"
    
    @property
    def success_rate(self):
        if self.total_calls == 0:
            return 0
        return (self.successful_calls / self.total_calls) * 100
    
    def increment_stats(self, success: bool, tokens: int, cost: Decimal):
        """Aktualisiert Statistiken nach einem Aufruf."""
        self.total_calls += 1
        if success:
            self.successful_calls += 1
        self.total_tokens_used += tokens
        self.total_cost += cost
        self.save(update_fields=['total_calls', 'successful_calls', 'total_tokens_used', 'total_cost'])


class ThinkingModelConfig(models.Model):
    """Konfiguration für Thinking-Models (o1, Gemini Thinking, etc.)."""
    
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    provider = models.CharField(max_length=50)  # openai, google, deepseek
    
    # API Config
    api_url = models.URLField()
    model_id = models.CharField(max_length=100)
    api_key_env_var = models.CharField(max_length=100)
    
    # Limits
    max_tokens = models.IntegerField(default=8000)
    
    # Kosten (Thinking-Models sind teurer)
    cost_per_1k_input_tokens = models.DecimalField(max_digits=10, decimal_places=6, default=Decimal('0.015'))
    cost_per_1k_output_tokens = models.DecimalField(max_digits=10, decimal_places=6, default=Decimal('0.060'))
    
    # Capabilities
    supports_reasoning_trace = models.BooleanField(default=True)
    best_for = models.JSONField(default=list)
    
    # Status
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=10)
    
    # Stats
    total_calls = models.IntegerField(default=0)
    wins_vs_cascade = models.IntegerField(default=0)
    ties_with_cascade = models.IntegerField(default=0)
    losses_vs_cascade = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'bfagent_thinking_model_configs'
        ordering = ['priority', 'name']
        verbose_name = 'Thinking Model Config'
        verbose_name_plural = 'Thinking Model Configs'
    
    def __str__(self):
        return f"{self.display_name} ({self.provider})"
    
    @property
    def win_rate(self):
        total = self.wins_vs_cascade + self.ties_with_cascade + self.losses_vs_cascade
        if total == 0:
            return 0
        return (self.wins_vs_cascade / total) * 100
