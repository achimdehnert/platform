"""
Models for API app - MCP Orchestration
"""

from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils import timezone


class WorkflowContext(models.Model):
    """
    Stores context data for n8n workflows

    Enables sharing data between MCP tool calls within a workflow.
    Automatically cleaned up after 24 hours.
    """

    context_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Unique identifier for this workflow context (e.g., workflow_{workflow_id}_{execution_id})",
    )

    workflow_name = models.CharField(
        max_length=255, blank=True, help_text="Optional workflow name for debugging"
    )

    data = models.JSONField(default=dict, help_text="Context data stored as JSON")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    updated_at = models.DateTimeField(auto_now=True)

    expires_at = models.DateTimeField(db_index=True, help_text="Automatic cleanup after this time")

    class Meta:
        db_table = "api_workflow_contexts"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["context_id"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        return f"WorkflowContext({self.context_id})"

    def save(self, *args, **kwargs):
        # Auto-set expires_at to 24 hours from now
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(hours=24)
        super().save(*args, **kwargs)

    @classmethod
    def cleanup_expired(cls):
        """Delete expired contexts"""
        expired_count = cls.objects.filter(expires_at__lt=timezone.now()).delete()[0]
        return expired_count


class MCPToolExecution(models.Model):
    """
    Logs MCP tool executions for debugging and analytics
    """

    context = models.ForeignKey(
        WorkflowContext, on_delete=models.SET_NULL, null=True, blank=True, related_name="executions"
    )

    server = models.CharField(
        max_length=100, db_index=True, help_text="MCP server name (e.g., book-writing-mcp)"
    )

    tool = models.CharField(
        max_length=100, db_index=True, help_text="Tool name (e.g., book_create_project)"
    )

    params = models.JSONField(default=dict, help_text="Input parameters")

    result = models.JSONField(null=True, blank=True, help_text="Execution result")

    success = models.BooleanField(default=True, db_index=True)

    error_message = models.TextField(blank=True, help_text="Error message if failed")

    execution_time_ms = models.FloatField(
        null=True, blank=True, help_text="Execution time in milliseconds"
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "api_mcp_tool_executions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["server", "tool"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["success"]),
        ]

    def __str__(self):
        status = "✅" if self.success else "❌"
        return f"{status} {self.server}.{self.tool}"
