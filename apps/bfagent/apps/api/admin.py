"""
Django Admin for MCP Orchestration
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import MCPToolExecution, WorkflowContext


@admin.register(WorkflowContext)
class WorkflowContextAdmin(admin.ModelAdmin):
    """Admin interface for WorkflowContext"""

    list_display = ["context_id", "workflow_name", "created_at", "expires_at", "status_badge"]
    list_filter = ["created_at", "expires_at"]
    search_fields = ["context_id", "workflow_name"]
    readonly_fields = ["context_id", "created_at", "updated_at", "expires_at", "execution_count"]

    fieldsets = [
        ("Identification", {"fields": ["context_id", "workflow_name"]}),
        ("Data", {"fields": ["data"], "classes": ["collapse"]}),
        ("Metadata", {"fields": ["created_at", "updated_at", "expires_at", "execution_count"]}),
    ]

    def status_badge(self, obj):
        """Show status badge"""
        from django.utils import timezone

        if obj.expires_at < timezone.now():
            return format_html('<span style="color: red;">⏰ Expired</span>')
        else:
            return format_html('<span style="color: green;">✅ Active</span>')

    status_badge.short_description = "Status"

    def execution_count(self, obj):
        """Count of executions"""
        return obj.executions.count()

    execution_count.short_description = "Executions"

    actions = ["cleanup_expired"]

    def cleanup_expired(self, request, queryset):
        """Admin action to cleanup expired contexts"""
        count = WorkflowContext.cleanup_expired()
        self.message_user(request, f"Cleaned up {count} expired contexts")

    cleanup_expired.short_description = "Cleanup expired contexts"


@admin.register(MCPToolExecution)
class MCPToolExecutionAdmin(admin.ModelAdmin):
    """Admin interface for MCPToolExecution"""

    list_display = ["id", "status_icon", "server", "tool", "execution_time_display", "created_at"]
    list_filter = ["success", "server", "created_at"]
    search_fields = ["tool", "server", "error_message"]
    readonly_fields = [
        "context",
        "server",
        "tool",
        "params",
        "result",
        "success",
        "error_message",
        "execution_time_ms",
        "created_at",
    ]

    fieldsets = [
        ("Execution", {"fields": ["context", "server", "tool", "success", "execution_time_ms"]}),
        ("Input", {"fields": ["params"], "classes": ["collapse"]}),
        ("Output", {"fields": ["result", "error_message"], "classes": ["collapse"]}),
        ("Metadata", {"fields": ["created_at"]}),
    ]

    def status_icon(self, obj):
        """Show status icon"""
        if obj.success:
            return format_html('<span style="color: green; font-size: 16px;">✅</span>')
        else:
            return format_html('<span style="color: red; font-size: 16px;">❌</span>')

    status_icon.short_description = ""

    def execution_time_display(self, obj):
        """Format execution time"""
        if obj.execution_time_ms:
            return f"{obj.execution_time_ms:.2f}ms"
        return "-"

    execution_time_display.short_description = "Duration"

    def has_add_permission(self, request):
        """Disable manual adding (created via API only)"""
        return False
