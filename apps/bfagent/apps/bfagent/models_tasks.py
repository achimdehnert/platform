"""
Task Management Models for LLM Job Delegation
==============================================

Models for tracking delegated tasks that can be executed by
local LLMs (Ollama/vLLM) instead of Cascade.

Integrates with:
- TestRequirement.complexity field
- LLMRouter for automatic LLM selection
- Celery for background execution (future)
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model()


class DelegatedTask(models.Model):
    """
    A task delegated to a local LLM based on complexity.
    
    Workflow:
    1. Cascade receives task request
    2. Checks complexity (from TestRequirement or auto-estimated)
    3. If LOW/MEDIUM → creates DelegatedTask
    4. LLMRouter selects appropriate LLM
    5. Task executes (sync now, async with Celery later)
    6. Result stored, Cascade gets notification
    """
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        QUEUED = 'queued', 'Queued'
        RUNNING = 'running', 'Running'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        CANCELLED = 'cancelled', 'Cancelled'
    
    class TaskType(models.TextChoices):
        CODING = 'coding', 'Coding'
        WRITING = 'writing', 'Writing'
        ANALYSIS = 'analysis', 'Analysis'
        TRANSLATION = 'translation', 'Translation'
        ILLUSTRATION = 'illustration', 'Illustration'
        OTHER = 'other', 'Other'
    
    class Complexity(models.TextChoices):
        AUTO = 'auto', 'Auto (Heuristik)'
        LOW = 'low', 'Low - Einfach'
        MEDIUM = 'medium', 'Medium - Moderat'
        HIGH = 'high', 'High - Komplex'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Task Definition
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    task_type = models.CharField(
        max_length=20,
        choices=TaskType.choices,
        default=TaskType.CODING
    )
    
    # Complexity & Routing
    complexity = models.CharField(
        max_length=20,
        choices=Complexity.choices,
        default=Complexity.AUTO
    )
    complexity_estimated = models.CharField(
        max_length=20,
        blank=True,
        help_text="Auto-estimated complexity (if complexity=auto)"
    )
    
    # LLM Selection
    llm_selected = models.ForeignKey(
        'bfagent.Llms',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='delegated_tasks'
    )
    routing_reason = models.CharField(max_length=200, blank=True)
    requires_cascade = models.BooleanField(
        default=False,
        help_text="True if task was too complex for local LLMs"
    )
    
    # Link to Requirement (optional)
    requirement = models.ForeignKey(
        'bfagent.TestRequirement',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='delegated_tasks'
    )
    
    # Execution Details
    prompt = models.TextField(help_text="The prompt sent to LLM")
    system_prompt = models.TextField(blank=True)
    
    # Status & Timing
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Result
    result_text = models.TextField(blank=True)
    result_data = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    
    # Metrics
    tokens_used = models.IntegerField(default=0)
    latency_ms = models.IntegerField(default=0)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    
    # Celery Task ID (for future background execution)
    celery_task_id = models.CharField(max_length=255, blank=True)
    
    # Audit
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='delegated_tasks_created'
    )
    
    class Meta:
        db_table = 'bfagent_delegated_tasks'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['task_type', 'complexity']),
            models.Index(fields=['requirement']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.status})"
    
    @property
    def duration_seconds(self) -> float:
        """Calculate task duration"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0
    
    def mark_started(self):
        """Mark task as started"""
        self.status = self.Status.RUNNING
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])
    
    def mark_completed(self, result_text: str, tokens: int = 0, latency: int = 0):
        """Mark task as completed with result"""
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.result_text = result_text
        self.tokens_used = tokens
        self.latency_ms = latency
        self.save(update_fields=[
            'status', 'completed_at', 'result_text', 
            'tokens_used', 'latency_ms'
        ])
    
    def mark_failed(self, error: str):
        """Mark task as failed with error"""
        self.status = self.Status.FAILED
        self.completed_at = timezone.now()
        self.error_message = error
        self.save(update_fields=['status', 'completed_at', 'error_message'])


class TaskExecutionLog(models.Model):
    """
    Log of task execution attempts.
    Useful for debugging and analytics.
    """
    
    task = models.ForeignKey(
        DelegatedTask,
        on_delete=models.CASCADE,
        related_name='execution_logs'
    )
    
    timestamp = models.DateTimeField(auto_now_add=True)
    event = models.CharField(max_length=50)  # 'started', 'completed', 'failed', 'retried'
    details = models.JSONField(default=dict)
    
    class Meta:
        db_table = 'bfagent_task_execution_logs'
        ordering = ['-timestamp']


class TaskFeedback(models.Model):
    """
    Feedback on task routing decisions.
    Used to evaluate and improve the Auto-Router.
    """
    
    class Rating(models.TextChoices):
        EXCELLENT = 'excellent', '⭐⭐⭐ Excellent'
        GOOD = 'good', '⭐⭐ Good'
        ACCEPTABLE = 'acceptable', '⭐ Acceptable'
        POOR = 'poor', '👎 Poor'
        WRONG_ROUTING = 'wrong_routing', '❌ Wrong Routing'
    
    task = models.OneToOneField(
        DelegatedTask,
        on_delete=models.CASCADE,
        related_name='feedback'
    )
    
    # Quality Rating
    result_quality = models.CharField(
        max_length=20,
        choices=Rating.choices,
        help_text="Quality of the LLM result"
    )
    
    # Routing Evaluation
    routing_correct = models.BooleanField(
        default=True,
        help_text="Was the complexity estimation correct?"
    )
    should_have_been = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Should have been LOW'),
            ('medium', 'Should have been MEDIUM'),
            ('high', 'Should have been HIGH (Cascade)'),
            ('correct', 'Routing was correct'),
        ],
        default='correct'
    )
    
    # Details
    comment = models.TextField(blank=True, help_text="Optional feedback comment")
    result_used = models.BooleanField(
        default=True,
        help_text="Was the result actually used?"
    )
    manual_correction_needed = models.BooleanField(
        default=False,
        help_text="Did Cascade need to fix the result?"
    )
    
    # Metrics
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'bfagent_task_feedback'
        verbose_name = 'Task Feedback'
        verbose_name_plural = 'Task Feedbacks'
    
    def __str__(self):
        return f"Feedback for {self.task.name}: {self.result_quality}"


class RoutingAnalytics(models.Model):
    """
    Aggregated analytics for routing decisions.
    Updated periodically or on-demand.
    """
    
    date = models.DateField(unique=True)
    
    # Task Counts
    total_tasks = models.IntegerField(default=0)
    low_complexity_tasks = models.IntegerField(default=0)
    medium_complexity_tasks = models.IntegerField(default=0)
    high_complexity_tasks = models.IntegerField(default=0)
    cascade_required_tasks = models.IntegerField(default=0)
    
    # Success Metrics
    successful_delegations = models.IntegerField(default=0)
    failed_delegations = models.IntegerField(default=0)
    
    # Quality Metrics (from feedback)
    excellent_ratings = models.IntegerField(default=0)
    good_ratings = models.IntegerField(default=0)
    acceptable_ratings = models.IntegerField(default=0)
    poor_ratings = models.IntegerField(default=0)
    wrong_routing_count = models.IntegerField(default=0)
    
    # Cost Savings
    estimated_tokens_saved = models.IntegerField(default=0)
    estimated_cost_saved_usd = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    
    # Performance
    avg_latency_ms = models.IntegerField(default=0)
    total_tokens_used = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'bfagent_routing_analytics'
        ordering = ['-date']
    
    def __str__(self):
        return f"Analytics {self.date}: {self.total_tasks} tasks"
    
    @property
    def success_rate(self) -> float:
        total = self.successful_delegations + self.failed_delegations
        if total == 0:
            return 0.0
        return (self.successful_delegations / total) * 100
    
    @property
    def routing_accuracy(self) -> float:
        total_with_feedback = (
            self.excellent_ratings + self.good_ratings + 
            self.acceptable_ratings + self.poor_ratings + 
            self.wrong_routing_count
        )
        if total_with_feedback == 0:
            return 0.0
        correct = total_with_feedback - self.wrong_routing_count
        return (correct / total_with_feedback) * 100
