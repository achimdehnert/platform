# -*- coding: utf-8 -*-
"""
Admin für Usage Tracking Models.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count, Avg
from .models_usage_tracking import (
    DjangoGenerationError,
    ToolUsageLog,
    ErrorFixPattern,
)


@admin.register(DjangoGenerationError)
class DjangoGenerationErrorAdmin(admin.ModelAdmin):
    """Admin für Django Generation Errors."""
    
    list_display = [
        "timestamp",
        "error_type_display",
        "severity_display",
        "error_message_short",
        "file_path_short",
        "occurrence_count",
        "source_display",
        "resolved_display",
    ]
    list_filter = [
        "error_type",
        "severity",
        "source",
        "resolved",
        "auto_fixable",
    ]
    search_fields = ["error_message", "file_path", "error_code"]
    date_hierarchy = "timestamp"
    readonly_fields = [
        "timestamp",
        "error_hash",
        "occurrence_count",
    ]
    actions = ["mark_resolved", "mark_auto_fixable"]
    
    fieldsets = (
        ("Error Info", {
            "fields": ("error_type", "severity", "error_code", "error_message")
        }),
        ("Location", {
            "fields": ("file_path", "line_number", "function_name")
        }),
        ("Code", {
            "fields": ("code_snippet", "stack_trace"),
            "classes": ("collapse",)
        }),
        ("Source & Session", {
            "fields": ("source", "session_id")
        }),
        ("Resolution", {
            "fields": ("resolved", "resolution", "auto_fixable", "fix_suggestion")
        }),
        ("Statistics", {
            "fields": ("error_hash", "occurrence_count"),
            "classes": ("collapse",)
        }),
    )
    
    def error_type_display(self, obj):
        colors = {
            'template': '#17a2b8',
            'view': '#28a745',
            'url': '#ffc107',
            'model': '#dc3545',
            'import': '#6c757d',
            'syntax': '#fd7e14',
        }
        color = colors.get(obj.error_type, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_error_type_display()
        )
    error_type_display.short_description = "Type"
    
    def severity_display(self, obj):
        colors = {
            'info': 'blue',
            'warning': 'orange',
            'error': 'red',
            'critical': 'darkred',
        }
        return format_html(
            '<span style="color: {};">{}</span>',
            colors.get(obj.severity, 'black'),
            obj.get_severity_display()
        )
    severity_display.short_description = "Severity"
    
    def error_message_short(self, obj):
        msg = obj.error_message[:60]
        if len(obj.error_message) > 60:
            msg += "..."
        return msg
    error_message_short.short_description = "Message"
    
    def file_path_short(self, obj):
        if obj.file_path:
            parts = obj.file_path.split("/")
            return "/".join(parts[-2:]) if len(parts) > 1 else parts[-1]
        return "-"
    file_path_short.short_description = "File"
    
    def source_display(self, obj):
        icons = {
            'cascade': '🤖',
            'user': '👤',
            'system': '⚙️',
            'mcp': '🔧',
        }
        return f"{icons.get(obj.source, '?')} {obj.get_source_display()}"
    source_display.short_description = "Source"
    
    def resolved_display(self, obj):
        if obj.resolved:
            return format_html('<span style="color: green;">✅</span>')
        if obj.auto_fixable:
            return format_html('<span style="color: orange;">🔧</span>')
        return format_html('<span style="color: gray;">⏳</span>')
    resolved_display.short_description = "Status"
    
    @admin.action(description="Mark selected as resolved")
    def mark_resolved(self, request, queryset):
        count = queryset.update(resolved=True)
        self.message_user(request, f"{count} errors marked as resolved.")
    
    @admin.action(description="Mark selected as auto-fixable")
    def mark_auto_fixable(self, request, queryset):
        count = queryset.update(auto_fixable=True)
        self.message_user(request, f"{count} errors marked as auto-fixable.")


@admin.register(ToolUsageLog)
class ToolUsageLogAdmin(admin.ModelAdmin):
    """Admin für Tool Usage Logs."""
    
    list_display = [
        "timestamp",
        "tool_name",
        "caller_display",
        "app_label",
        "execution_time_display",
        "status_display",
    ]
    list_filter = [
        "tool_name",
        "caller_type",
        "app_label",
        "success",
    ]
    search_fields = ["tool_name", "caller_id", "result_summary"]
    date_hierarchy = "timestamp"
    readonly_fields = [
        "timestamp",
        "tool_name",
        "tool_version",
        "tool_category",
        "caller_type",
        "caller_id",
        "app_label",
        "request_url",
        "input_params",
        "execution_time_ms",
        "success",
        "result_summary",
        "error_message",
        "session_id",
    ]
    
    def caller_display(self, obj):
        icons = {
            'user': '👤',
            'cascade': '🤖',
            'mcp': '🔧',
            'api': '🌐',
            'scheduled': '⏰',
            'system': '⚙️',
        }
        icon = icons.get(obj.caller_type, '?')
        caller = obj.caller_id[:20] if obj.caller_id else "-"
        return f"{icon} {caller}"
    caller_display.short_description = "Caller"
    
    def execution_time_display(self, obj):
        if obj.execution_time_ms > 1000:
            return format_html(
                '<span style="color: orange;">{:.1f}s</span>',
                obj.execution_time_ms / 1000
            )
        return f"{obj.execution_time_ms:.0f}ms"
    execution_time_display.short_description = "Time"
    
    def status_display(self, obj):
        if obj.success:
            return format_html('<span style="color: green;">✅</span>')
        return format_html('<span style="color: red;">❌</span>')
    status_display.short_description = "Status"
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ErrorFixPattern)
class ErrorFixPatternAdmin(admin.ModelAdmin):
    """Admin für Error Fix Patterns."""
    
    list_display = [
        "name",
        "error_type",
        "fix_type",
        "times_applied",
        "success_rate_display",
        "is_active_display",
    ]
    list_filter = [
        "error_type",
        "fix_type",
        "is_active",
    ]
    search_fields = ["name", "description", "error_pattern"]
    readonly_fields = ["times_applied", "created_at", "updated_at"]
    
    fieldsets = (
        ("Pattern Info", {
            "fields": ("name", "description", "is_active")
        }),
        ("Matching", {
            "fields": ("error_type", "error_pattern", "file_pattern")
        }),
        ("Fix", {
            "fields": ("fix_type", "fix_template")
        }),
        ("Statistics", {
            "fields": ("times_applied", "success_rate", "created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    
    def success_rate_display(self, obj):
        if obj.success_rate >= 90:
            color = "green"
        elif obj.success_rate >= 70:
            color = "orange"
        else:
            color = "red"
        return format_html(
            '<span style="color: {};">{:.0f}%</span>',
            color, obj.success_rate
        )
    success_rate_display.short_description = "Success Rate"
    
    def is_active_display(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">✅ Active</span>')
        return format_html('<span style="color: gray;">❌ Inactive</span>')
    is_active_display.short_description = "Status"
