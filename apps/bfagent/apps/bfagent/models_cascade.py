"""
Cascade Autonomous Work Session Models

Tracks autonomous Cascade work sessions for bug-fixing and feature implementation.
"""

import uuid
from django.db import models
from django.conf import settings


class CascadeWorkSession(models.Model):
    """Tracks autonomous Cascade work sessions"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requirement = models.ForeignKey(
        'bfagent.TestRequirement',
        on_delete=models.CASCADE,
        related_name='cascade_sessions'
    )
    
    # Cross-Domain Support
    domain = models.CharField(
        max_length=50,
        default='core',
        help_text="Domain this session belongs to (e.g., writing_hub, control_center, cad_hub)"
    )
    
    # Session Status
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('stopped', 'Manually Stopped'),
        ('max_iterations', 'Max Iterations Reached'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Iteration Tracking
    current_iteration = models.IntegerField(default=0)
    max_iterations = models.IntegerField(default=10)
    
    # Timestamps
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Context
    initial_context = models.TextField(help_text="Bug context at session start (Markdown)")
    final_summary = models.TextField(blank=True, help_text="Summary when session ends")
    
    # Tracking
    files_changed = models.JSONField(default=list, help_text="List of files modified")
    error_count = models.IntegerField(default=0)
    success_indicators = models.JSONField(default=list, help_text="Success patterns detected")
    
    # User
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='cascade_sessions'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cascade_work_sessions'
        ordering = ['-created_at']
        verbose_name = 'Cascade Work Session'
        verbose_name_plural = 'Cascade Work Sessions'
    
    def __str__(self):
        return f"Session {self.id.hex[:8]} - {self.requirement.name[:30]} ({self.status})"
    
    @property
    def progress_percentage(self):
        """Calculate progress as percentage"""
        if self.max_iterations == 0:
            return 0
        return int((self.current_iteration / self.max_iterations) * 100)
    
    @property
    def is_active(self):
        """Check if session is still running"""
        return self.status in ['pending', 'running']
    
    def start(self):
        """Start the session"""
        from django.utils import timezone
        self.status = 'running'
        self.started_at = timezone.now()
        self.save()
    
    def stop(self, reason='stopped'):
        """Stop the session"""
        from django.utils import timezone
        self.status = reason
        self.completed_at = timezone.now()
        self.save()
    
    def increment_iteration(self):
        """Move to next iteration"""
        self.current_iteration += 1
        if self.current_iteration >= self.max_iterations:
            self.stop('max_iterations')
        self.save()
        return self.current_iteration
    
    def mark_success(self, summary=''):
        """Mark session as successful"""
        from django.utils import timezone
        self.status = 'success'
        self.completed_at = timezone.now()
        self.final_summary = summary
        self.save()
        
        # Update requirement status
        self.requirement.status = 'done'
        self.requirement.save()
    
    def add_log(self, log_type, message, details=None):
        """Add a log entry to this session"""
        return CascadeWorkLog.objects.create(
            session=self,
            log_type=log_type,
            iteration=self.current_iteration,
            message=message,
            details=details or {}
        )


class CascadeWorkLog(models.Model):
    """Individual log entries for a work session"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        CascadeWorkSession,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    
    LOG_TYPES = [
        ('info', 'Info'),
        ('action', 'Action'),
        ('stdout', 'Stdout'),
        ('stderr', 'Stderr'),
        ('success', 'Success'),
        ('error', 'Error'),
        ('warning', 'Warning'),
        ('file_change', 'File Change'),
        ('test_result', 'Test Result'),
    ]
    log_type = models.CharField(max_length=20, choices=LOG_TYPES)
    
    iteration = models.IntegerField(default=0)
    message = models.TextField()
    details = models.JSONField(default=dict, help_text="Extra context (files, line numbers, etc.)")
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'cascade_work_logs'
        ordering = ['timestamp']
        verbose_name = 'Cascade Work Log'
        verbose_name_plural = 'Cascade Work Logs'
    
    def __str__(self):
        return f"[{self.log_type}] Iter {self.iteration}: {self.message[:50]}"
    
    @property
    def icon(self):
        """Get Bootstrap icon for log type"""
        icons = {
            'info': 'bi-info-circle text-info',
            'action': 'bi-lightning text-primary',
            'stdout': 'bi-terminal text-secondary',
            'stderr': 'bi-exclamation-triangle text-danger',
            'success': 'bi-check-circle text-success',
            'error': 'bi-x-circle text-danger',
            'warning': 'bi-exclamation-circle text-warning',
            'file_change': 'bi-file-earmark-code text-primary',
            'test_result': 'bi-clipboard-check text-info',
        }
        return icons.get(self.log_type, 'bi-record-circle')
