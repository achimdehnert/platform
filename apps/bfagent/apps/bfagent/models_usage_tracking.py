# -*- coding: utf-8 -*-
"""
Usage Tracking Models for Agents and Tools.

Tracks:
- Django generation errors (template, view, url, model)
- Tool usage by user, agent, and application
- Error patterns for automated fixes
"""
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
from typing import Dict, List, Optional
import json


class DjangoGenerationError(models.Model):
    """
    Logs Django code generation errors.
    
    Captures errors in templates, views, urls, models, forms, etc.
    Used to identify common patterns and create automated fixes.
    """
    ERROR_TYPES = [
        ('template', 'Template Error'),
        ('view', 'View Error'),
        ('url', 'URL Configuration Error'),
        ('model', 'Model Error'),
        ('form', 'Form Error'),
        ('import', 'Import Error'),
        ('syntax', 'Syntax Error'),
        ('migration', 'Migration Error'),
        ('admin', 'Admin Error'),
        ('serializer', 'Serializer Error'),
        ('handler', 'Handler Error'),
        ('other', 'Other Error'),
    ]
    
    SEVERITY_CHOICES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ]
    
    SOURCE_CHOICES = [
        ('cascade', 'Cascade/AI Agent'),
        ('user', 'User Manual'),
        ('system', 'System/Automated'),
        ('mcp', 'MCP Tool'),
    ]
    
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Error classification
    error_type = models.CharField(
        max_length=20,
        choices=ERROR_TYPES,
        db_index=True,
        help_text="Type of Django error"
    )
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default='error'
    )
    
    # Error details
    error_message = models.TextField(
        help_text="Full error message"
    )
    error_code = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_index=True,
        help_text="Error code/rule (e.g., E001, W001)"
    )
    
    # Location
    file_path = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text="File where error occurred"
    )
    line_number = models.IntegerField(
        null=True,
        blank=True,
        help_text="Line number of error"
    )
    function_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Function/class where error occurred"
    )
    
    # Context
    code_snippet = models.TextField(
        null=True,
        blank=True,
        help_text="Relevant code snippet"
    )
    stack_trace = models.TextField(
        null=True,
        blank=True,
        help_text="Full stack trace"
    )
    
    # Source tracking
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default='cascade',
        db_index=True
    )
    session_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Cascade session ID"
    )
    
    # Resolution
    resolved = models.BooleanField(default=False)
    resolution = models.TextField(
        null=True,
        blank=True,
        help_text="How the error was resolved"
    )
    auto_fixable = models.BooleanField(
        default=False,
        help_text="Can this error be automatically fixed?"
    )
    fix_suggestion = models.TextField(
        null=True,
        blank=True,
        help_text="Suggested fix for this error"
    )
    
    # Pattern matching
    error_hash = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        db_index=True,
        help_text="Hash for deduplication/pattern matching"
    )
    occurrence_count = models.IntegerField(
        default=1,
        help_text="Number of times this error occurred"
    )
    
    class Meta:
        verbose_name = "Django Generation Error"
        verbose_name_plural = "Django Generation Errors"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["timestamp", "error_type"]),
            models.Index(fields=["error_type", "error_code"]),
            models.Index(fields=["source", "timestamp"]),
        ]
    
    def __str__(self):
        return f"{self.get_error_type_display()}: {self.error_message[:50]}"
    
    @classmethod
    def log_error(
        cls,
        error_type: str,
        error_message: str,
        file_path: str = None,
        line_number: int = None,
        code_snippet: str = None,
        source: str = 'cascade',
        session_id: str = None,
        auto_fixable: bool = False,
        fix_suggestion: str = None,
        **kwargs
    ) -> "DjangoGenerationError":
        """Log a Django generation error."""
        import hashlib
        
        # Create error hash for pattern matching
        hash_content = f"{error_type}:{error_message}:{file_path or ''}"
        error_hash = hashlib.sha256(hash_content.encode()).hexdigest()[:32]
        
        # Check if similar error exists
        existing = cls.objects.filter(error_hash=error_hash).first()
        if existing:
            existing.occurrence_count += 1
            existing.save(update_fields=['occurrence_count'])
            return existing
        
        return cls.objects.create(
            error_type=error_type,
            error_message=error_message,
            file_path=file_path,
            line_number=line_number,
            code_snippet=code_snippet,
            source=source,
            session_id=session_id,
            error_hash=error_hash,
            auto_fixable=auto_fixable,
            fix_suggestion=fix_suggestion,
            **kwargs
        )
    
    @classmethod
    def get_common_errors(cls, days: int = 30, limit: int = 20) -> List[Dict]:
        """Get most common errors for the period."""
        since = timezone.now() - timedelta(days=days)
        
        from django.db.models import Sum, Count
        
        return list(
            cls.objects.filter(timestamp__gte=since)
            .values('error_type', 'error_code', 'error_message')
            .annotate(
                total_occurrences=Sum('occurrence_count'),
                unique_files=Count('file_path', distinct=True)
            )
            .order_by('-total_occurrences')[:limit]
        )
    
    @classmethod
    def get_fixable_errors(cls) -> List["DjangoGenerationError"]:
        """Get errors that can be auto-fixed."""
        return list(
            cls.objects.filter(
                auto_fixable=True,
                resolved=False
            ).order_by('-occurrence_count')
        )


class ToolUsageLog(models.Model):
    """
    Tracks MCP tool and agent usage.
    
    Records who/what used which tool and when for controlling purposes.
    """
    CALLER_TYPES = [
        ('user', 'User (Manual)'),
        ('cascade', 'Cascade/AI'),
        ('mcp', 'MCP Client'),
        ('api', 'API Call'),
        ('scheduled', 'Scheduled Task'),
        ('system', 'System'),
    ]
    
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Tool identification
    tool_name = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Name of the tool/agent"
    )
    tool_version = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="Tool version"
    )
    tool_category = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_index=True,
        help_text="Tool category (e.g., 'code_quality', 'generation')"
    )
    
    # Caller identification
    caller_type = models.CharField(
        max_length=20,
        choices=CALLER_TYPES,
        default='cascade',
        db_index=True
    )
    caller_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
        help_text="User ID, session ID, or system identifier"
    )
    
    # Application context
    app_label = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
        help_text="Django app label if applicable"
    )
    request_url = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text="URL that triggered the tool call"
    )
    
    # Execution details
    input_params = models.JSONField(
        null=True,
        blank=True,
        help_text="Input parameters (sanitized)"
    )
    execution_time_ms = models.FloatField(
        default=0.0,
        help_text="Execution time in milliseconds"
    )
    
    # Result
    success = models.BooleanField(default=True)
    result_summary = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text="Brief summary of result"
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text="Error message if failed"
    )
    
    # Session tracking
    session_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
        help_text="Session ID for grouping"
    )
    
    class Meta:
        verbose_name = "Tool Usage Log"
        verbose_name_plural = "Tool Usage Logs"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["timestamp", "tool_name"]),
            models.Index(fields=["caller_type", "timestamp"]),
            models.Index(fields=["tool_name", "caller_type"]),
            models.Index(fields=["app_label", "timestamp"]),
        ]
    
    def __str__(self):
        return f"{self.tool_name} by {self.get_caller_type_display()} ({self.timestamp:%Y-%m-%d %H:%M})"
    
    @classmethod
    def log_usage(
        cls,
        tool_name: str,
        caller_type: str = 'cascade',
        caller_id: str = None,
        app_label: str = None,
        input_params: dict = None,
        execution_time_ms: float = 0.0,
        success: bool = True,
        result_summary: str = None,
        error_message: str = None,
        **kwargs
    ) -> "ToolUsageLog":
        """Log a tool usage."""
        # Sanitize input params (remove sensitive data)
        sanitized_params = None
        if input_params:
            sanitized_params = {
                k: v for k, v in input_params.items()
                if k not in ['password', 'api_key', 'token', 'secret']
            }
        
        return cls.objects.create(
            tool_name=tool_name,
            caller_type=caller_type,
            caller_id=caller_id,
            app_label=app_label,
            input_params=sanitized_params,
            execution_time_ms=execution_time_ms,
            success=success,
            result_summary=result_summary,
            error_message=error_message,
            **kwargs
        )
    
    @classmethod
    def get_usage_stats(cls, days: int = 30) -> Dict:
        """Get usage statistics for the period."""
        since = timezone.now() - timedelta(days=days)
        logs = cls.objects.filter(timestamp__gte=since)
        
        from django.db.models import Count, Avg, Sum
        
        # Overall stats
        overall = logs.aggregate(
            total_calls=Count('id'),
            successful_calls=Count('id', filter=models.Q(success=True)),
            failed_calls=Count('id', filter=models.Q(success=False)),
            avg_execution_time=Avg('execution_time_ms'),
        )
        
        # By caller type
        by_caller = list(
            logs.values('caller_type')
            .annotate(
                calls=Count('id'),
                success_rate=Count('id', filter=models.Q(success=True)) * 100.0 / Count('id')
            )
            .order_by('-calls')
        )
        
        # By tool
        by_tool = list(
            logs.values('tool_name')
            .annotate(
                calls=Count('id'),
                avg_time=Avg('execution_time_ms'),
                success_rate=Count('id', filter=models.Q(success=True)) * 100.0 / Count('id')
            )
            .order_by('-calls')[:20]
        )
        
        # By app
        by_app = list(
            logs.filter(app_label__isnull=False)
            .values('app_label')
            .annotate(calls=Count('id'))
            .order_by('-calls')
        )
        
        return {
            "period_days": days,
            "overall": overall,
            "by_caller": by_caller,
            "by_tool": by_tool,
            "by_app": by_app,
        }
    
    @classmethod
    def get_user_stats(cls, caller_id: str, days: int = 30) -> Dict:
        """Get usage stats for a specific user/caller."""
        since = timezone.now() - timedelta(days=days)
        logs = cls.objects.filter(
            timestamp__gte=since,
            caller_id=caller_id
        )
        
        from django.db.models import Count, Avg
        
        return {
            "caller_id": caller_id,
            "period_days": days,
            "total_calls": logs.count(),
            "tools_used": list(
                logs.values('tool_name')
                .annotate(calls=Count('id'))
                .order_by('-calls')[:10]
            ),
        }


class ErrorFixPattern(models.Model):
    """
    Stores patterns for automatic error fixes.
    
    Used to create MCP tools that can fix common errors.
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Pattern name/identifier"
    )
    description = models.TextField(
        help_text="Description of what this pattern fixes"
    )
    
    # Matching
    error_type = models.CharField(
        max_length=20,
        choices=DjangoGenerationError.ERROR_TYPES,
        db_index=True
    )
    error_pattern = models.TextField(
        help_text="Regex pattern to match error message"
    )
    file_pattern = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="Glob pattern for file matching"
    )
    
    # Fix
    fix_type = models.CharField(
        max_length=20,
        choices=[
            ('replace', 'Find and Replace'),
            ('insert', 'Insert Code'),
            ('delete', 'Delete Code'),
            ('refactor', 'Refactor'),
            ('command', 'Run Command'),
        ],
        default='replace'
    )
    fix_template = models.TextField(
        help_text="Template for the fix (supports placeholders)"
    )
    
    # Metadata
    times_applied = models.IntegerField(default=0)
    success_rate = models.FloatField(default=100.0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Error Fix Pattern"
        verbose_name_plural = "Error Fix Patterns"
        ordering = ["-times_applied"]
    
    def __str__(self):
        return f"{self.name} ({self.get_error_type_display()})"
    
    def apply_fix(self, error: DjangoGenerationError) -> Dict:
        """Apply this fix pattern to an error."""
        import re
        
        result = {
            "pattern": self.name,
            "applied": False,
            "message": "",
        }
        
        # Check if pattern matches
        if not re.search(self.error_pattern, error.error_message):
            result["message"] = "Pattern does not match"
            return result
        
        # Apply fix based on type
        if self.fix_type == 'replace':
            result["fix_code"] = self.fix_template
            result["applied"] = True
            result["message"] = "Replace fix generated"
        elif self.fix_type == 'insert':
            result["fix_code"] = self.fix_template
            result["applied"] = True
            result["message"] = "Insert fix generated"
        
        # Update statistics
        self.times_applied += 1
        self.save(update_fields=['times_applied'])
        
        return result
    
    @classmethod
    def find_matching_pattern(cls, error: DjangoGenerationError) -> Optional["ErrorFixPattern"]:
        """Find a pattern that matches the given error."""
        import re
        
        patterns = cls.objects.filter(
            error_type=error.error_type,
            is_active=True
        )
        
        for pattern in patterns:
            if re.search(pattern.error_pattern, error.error_message):
                return pattern
        
        return None
