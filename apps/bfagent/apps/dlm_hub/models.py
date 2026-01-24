"""DLM Hub Models for Documentation Lifecycle Management."""

import uuid

from django.conf import settings
from django.db import models


class AnalysisRun(models.Model):
    """Einzelner Analyse-Durchlauf."""
    
    SCAN_TYPE_CHOICES = [
        ("redundancy", "Redundancy Analysis"),
        ("freshness", "Freshness Check"),
        ("coverage", "Coverage Analysis"),
        ("full", "Full Analysis"),
    ]
    
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    scan_path = models.CharField(max_length=500)
    scan_type = models.CharField(max_length=50, choices=SCAN_TYPE_CHOICES)
    model_used = models.CharField(max_length=100, default="llama3:8b")
    
    files_scanned = models.IntegerField(default=0)
    files_total = models.IntegerField(default=0)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    result_json = models.JSONField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dlm_analysis_runs"
    )
    
    class Meta:
        db_table = "dlm_analysis_runs"
        ordering = ["-created_at"]
        verbose_name = "Analysis Run"
        verbose_name_plural = "Analysis Runs"
    
    def __str__(self):
        return f"{self.scan_type} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def duration_seconds(self):
        if self.completed_at and self.created_at:
            return (self.completed_at - self.created_at).total_seconds()
        return None
    
    @property
    def issue_count(self):
        return self.issues.count()


class AnalysisIssue(models.Model):
    """Einzelnes gefundenes Problem."""
    
    ISSUE_TYPE_CHOICES = [
        ("redundancy", "Redundancy"),
        ("outdated", "Outdated"),
        ("structure", "Structure Issue"),
        ("orphan", "Orphan File"),
        ("broken_link", "Broken Link"),
    ]
    
    SEVERITY_CHOICES = [
        ("high", "High"),
        ("medium", "Medium"),
        ("low", "Low"),
    ]
    
    SUGGESTION_CHOICES = [
        ("archive", "Archive"),
        ("review", "Review"),
        ("merge", "Merge"),
        ("delete", "Delete"),
        ("update", "Update"),
        ("ignore", "Ignore"),
    ]
    
    STATUS_CHOICES = [
        ("open", "Open"),
        ("in_progress", "In Progress"),
        ("resolved", "Resolved"),
        ("ignored", "Ignored"),
    ]
    
    analysis_run = models.ForeignKey(
        AnalysisRun,
        on_delete=models.CASCADE,
        related_name="issues"
    )
    
    issue_type = models.CharField(max_length=50, choices=ISSUE_TYPE_CHOICES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default="medium")
    
    file_path = models.CharField(max_length=500)
    group_name = models.CharField(max_length=200, null=True, blank=True)
    related_files = models.JSONField(default=list, blank=True)
    
    reason = models.TextField()
    suggestion = models.CharField(max_length=50, choices=SUGGESTION_CHOICES)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dlm_resolved_issues"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "dlm_analysis_issues"
        ordering = ["-analysis_run__created_at", "severity", "issue_type"]
        verbose_name = "Analysis Issue"
        verbose_name_plural = "Analysis Issues"
    
    def __str__(self):
        return f"{self.issue_type}: {self.file_path}"
    
    @property
    def severity_color(self):
        return {
            "high": "danger",
            "medium": "warning",
            "low": "info",
        }.get(self.severity, "secondary")


class ActionLog(models.Model):
    """Audit-Log für ausgeführte Aktionen."""
    
    ACTION_TYPE_CHOICES = [
        ("archive", "Archived"),
        ("delete", "Deleted"),
        ("merge", "Merged"),
        ("ignore", "Ignored"),
        ("restore", "Restored"),
    ]
    
    issue = models.ForeignKey(
        AnalysisIssue,
        on_delete=models.CASCADE,
        related_name="action_logs"
    )
    
    action_type = models.CharField(max_length=50, choices=ACTION_TYPE_CHOICES)
    executed_at = models.DateTimeField(auto_now_add=True)
    executed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="dlm_action_logs"
    )
    
    details = models.JSONField(default=dict, blank=True)
    success = models.BooleanField(default=True)
    error_message = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = "dlm_action_logs"
        ordering = ["-executed_at"]
        verbose_name = "Action Log"
        verbose_name_plural = "Action Logs"
    
    def __str__(self):
        return f"{self.action_type} on {self.issue.file_path}"
