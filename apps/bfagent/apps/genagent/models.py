"""
GenAgent Models - General Agent Framework
Clean implementation of Phase/Action workflow system
"""

from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from apps.genagent.handlers import get_handler
import traceback


class Phase(models.Model):
    """
    Workflow Phase - represents a stage in an agent workflow
    
    Example: "Preparation", "Execution", "Validation"
    """
    
    name = models.CharField(
        max_length=100,
        verbose_name="Phase Name",
        help_text="Name of the workflow phase"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description",
        help_text="Detailed description of what happens in this phase"
    )
    order = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Order",
        help_text="Execution order (phases run sequentially)"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Active",
        help_text="Inactive phases are skipped during execution"
    )
    color = models.CharField(
        max_length=7,
        default="#3B82F6",
        verbose_name="Color",
        help_text="UI color in hex format (e.g. #3B82F6)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'name']
        db_table = 'genagent_phases'
        verbose_name = "GenAgent Phase"
        verbose_name_plural = "GenAgent Phases"
        indexes = [
            models.Index(fields=['order', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.order}. {self.name}"

    def execute_actions(self, context=None, test_mode=False):
        """
        Execute all actions in this phase sequentially

        Args:
            context: Dictionary with execution context data
            test_mode: If True, runs in test mode without side effects

        Returns:
            Dictionary with execution summary
        """
        if context is None:
            context = {}

        results = {
            'phase': self.name,
            'phase_id': self.id,
            'started_at': timezone.now().isoformat(),
            'actions_executed': 0,
            'actions_succeeded': 0,
            'actions_failed': 0,
            'actions_skipped': 0,
            'action_results': [],
            'status': 'running'
        }

        actions = self.actions.filter(is_active=True).order_by('order')

        for action in actions:
            try:
                result = action.execute(context=context, test_mode=test_mode)
                results['action_results'].append(result)
                results['actions_executed'] += 1

                if result['status'] == 'success':
                    results['actions_succeeded'] += 1
                elif result['status'] == 'failed':
                    results['actions_failed'] += 1
                    if not action.continue_on_error:
                        results['status'] = 'failed'
                        break
                elif result['status'] == 'skipped':
                    results['actions_skipped'] += 1

            except Exception as e:
                results['actions_failed'] += 1
                results['action_results'].append({
                    'action_id': action.id,
                    'action_name': action.name,
                    'status': 'failed',
                    'error': str(e)
                })
                if not action.continue_on_error:
                    results['status'] = 'failed'
                    break

        results['finished_at'] = timezone.now().isoformat()
        if results['status'] == 'running':
            results['status'] = 'success' if results['actions_failed'] == 0 else 'partial'

        return results


class Action(models.Model):
    """
    Handler Action - represents a specific task executed by a handler
    
    Each action is linked to a phase and executes a specific handler class
    """
    
    phase = models.ForeignKey(
        Phase,
        on_delete=models.CASCADE,
        related_name='actions',
        verbose_name="Phase"
    )
    name = models.CharField(
        max_length=100,
        verbose_name="Action Name",
        help_text="Descriptive name for this action"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description",
        help_text="What this action does"
    )
    handler_class = models.CharField(
        max_length=200,
        verbose_name="Handler Class",
        help_text="Full Python path to handler class (e.g. apps.genagent.handlers.demo_handlers.WelcomeHandler)"
    )
    order = models.IntegerField(
        default=0,
        verbose_name="Order",
        help_text="Execution order within the phase"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Active",
        help_text="Inactive actions are skipped"
    )
    
    # Configuration
    config = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Configuration",
        help_text="JSON configuration passed to handler"
    )
    timeout_seconds = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Timeout (seconds)",
        help_text="Maximum execution time (optional)"
    )
    retry_count = models.IntegerField(
        default=0,
        verbose_name="Retry Count",
        help_text="Number of retries on failure"
    )
    continue_on_error = models.BooleanField(
        default=False,
        verbose_name="Continue on Error",
        help_text="If true, workflow continues even if this action fails"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['phase__order', 'order', 'name']
        db_table = 'genagent_actions'
        verbose_name = "GenAgent Action"
        verbose_name_plural = "GenAgent Actions"
        indexes = [
            models.Index(fields=['phase', 'order', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.phase.name} → {self.name}"

    def execute(self, context=None, test_mode=False):
        """
        Execute this action with its configured handler

        Args:
            context: Dictionary with execution context data
            test_mode: If True, runs in test mode without side effects

        Returns:
            Dictionary with execution result
        """
        if context is None:
            context = {}

        # Create execution log entry
        from apps.genagent.models import ExecutionLog
        log = ExecutionLog.objects.create(
            action=self,
            status='pending',
            input_data=context
        )

        started_at = timezone.now()
        log.started_at = started_at
        log.status = 'running'
        log.save()

        try:
            # Get handler class
            handler_class = get_handler(self.handler_class)
            if not handler_class:
                raise ValueError(f"Handler '{self.handler_class}' not found")

            # Create handler instance with config
            handler = handler_class(config=self.config)

            # Execute handler
            result = handler.execute(context=context, test_mode=test_mode)

            # Update log with success
            finished_at = timezone.now()
            duration = (finished_at - started_at).total_seconds()

            log.status = 'success'
            log.finished_at = finished_at
            log.duration_seconds = duration
            log.output_data = result
            log.save()

            return {
                'action_id': self.id,
                'action_name': self.name,
                'handler': self.handler_class,
                'status': 'success',
                'result': result,
                'duration_seconds': duration,
                'execution_log_id': log.id
            }

        except Exception as e:
            # Update log with failure
            finished_at = timezone.now()
            duration = (finished_at - started_at).total_seconds()

            error_message = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"

            log.status = 'failed'
            log.finished_at = finished_at
            log.duration_seconds = duration
            log.error_message = error_message
            log.save()

            return {
                'action_id': self.id,
                'action_name': self.name,
                'handler': self.handler_class,
                'status': 'failed',
                'error': str(e),
                'error_type': type(e).__name__,
                'duration_seconds': duration,
                'execution_log_id': log.id
            }


class ExecutionLog(models.Model):
    """
    Execution Log - records the execution of an action
    
    Provides audit trail and debugging information
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),
    ]
    
    action = models.ForeignKey(
        Action,
        on_delete=models.CASCADE,
        related_name='executions',
        verbose_name="Action"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Status"
    )
    
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Started At"
    )
    finished_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Finished At"
    )
    duration_seconds = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Duration (seconds)",
        help_text="Execution time in seconds"
    )
    
    input_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Input Data",
        help_text="Context data passed to handler"
    )
    output_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Output Data",
        help_text="Result data returned by handler"
    )
    error_message = models.TextField(
        blank=True,
        default="",
        verbose_name="Error Message",
        help_text="Error details if execution failed"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        db_table = 'genagent_execution_logs'
        verbose_name = "GenAgent Execution Log"
        verbose_name_plural = "GenAgent Execution Logs"
        indexes = [
            models.Index(fields=['action', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.action} - {self.status} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"


class CustomDomain(models.Model):
    """
    Custom Domain - User-created workflow templates (Database-backed)
    
    Allows flexible creation of domains like: novel, essay, movie, research, etc.
    Complements code-based DomainTemplate classes with database customization.
    """
    
    CATEGORY_CHOICES = [
        ('creative_writing', 'Creative Writing'),
        ('technical_writing', 'Technical Writing'),
        ('media_production', 'Media Production'),
        ('research', 'Research & Analysis'),
        ('business', 'Business & Reports'),
        ('other', 'Other'),
    ]
    
    domain_id = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Domain ID",
        help_text="Unique identifier (e.g. 'novel', 'essay', 'movie')"
    )
    name = models.CharField(
        max_length=200,
        verbose_name="Display Name",
        help_text="Human-readable name (e.g. 'Novel Writing Workflow')"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description",
        help_text="Detailed description of this domain template"
    )
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default='other',
        verbose_name="Category",
        help_text="Domain category for organization"
    )
    
    # Visual
    icon = models.CharField(
        max_length=50,
        default='bi-file-text',
        verbose_name="Icon",
        help_text="Bootstrap icon class (e.g. 'bi-file-text')"
    )
    color = models.CharField(
        max_length=7,
        default='#3B82F6',
        verbose_name="Color",
        help_text="UI color in hex format (e.g. #3B82F6)"
    )
    
    # Configuration (JSON)
    phases_config = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Phases Configuration",
        help_text="List of phase definitions with actions"
    )
    required_fields = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Required Fields",
        help_text="List of required configuration fields"
    )
    optional_fields = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Optional Fields",
        help_text="List of optional configuration fields"
    )
    
    # Metadata
    author = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Author",
        help_text="Template creator"
    )
    version = models.CharField(
        max_length=20,
        default='1.0.0',
        verbose_name="Version"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Active",
        help_text="Inactive templates are hidden"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['category', 'name']
        db_table = 'genagent_custom_domains'
        verbose_name = "Custom Domain"
        verbose_name_plural = "Custom Domains"
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['domain_id']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.domain_id})"
    
    def get_statistics(self):
        """Return statistics about this domain template"""
        return {
            'total_phases': len(self.phases_config),
            'total_actions': sum(len(phase.get('actions', [])) for phase in self.phases_config),
            'required_fields_count': len(self.required_fields),
            'optional_fields_count': len(self.optional_fields),
        }
