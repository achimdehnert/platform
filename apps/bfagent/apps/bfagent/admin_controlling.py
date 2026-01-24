# -*- coding: utf-8 -*-
"""
Admin für Agent/LLM Controlling.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count, Avg
from .models_controlling import (
    LLMUsageLog,
    AgentValidationLog,
    ControllingBaseline,
    ControllingAlert,
)


@admin.register(LLMUsageLog)
class LLMUsageLogAdmin(admin.ModelAdmin):
    """Admin für LLM Usage Logs."""
    
    list_display = [
        "timestamp",
        "agent",
        "task",
        "model",
        "tokens_display",
        "cost_display",
        "latency_display",
        "status_display",
    ]
    list_filter = [
        "agent",
        "provider",
        "model",
        "success",
        "cached",
        "fallback_used",
    ]
    search_fields = ["agent", "task", "model", "error_message"]
    date_hierarchy = "timestamp"
    readonly_fields = [
        "timestamp",
        "agent",
        "task",
        "model",
        "provider",
        "tokens_in",
        "tokens_out",
        "cost_usd",
        "latency_ms",
        "cached",
        "fallback_used",
        "success",
        "error_message",
        "request_hash",
    ]
    
    def tokens_display(self, obj):
        return f"{obj.tokens_in} → {obj.tokens_out}"
    tokens_display.short_description = "Tokens (in→out)"
    
    def cost_display(self, obj):
        return f"${obj.cost_usd:.4f}"
    cost_display.short_description = "Kosten"
    
    def latency_display(self, obj):
        if obj.cached:
            return format_html('<span style="color: green;">cached</span>')
        return f"{obj.latency_ms:.0f}ms"
    latency_display.short_description = "Latenz"
    
    def status_display(self, obj):
        if obj.success:
            return format_html('<span style="color: green;">✅</span>')
        return format_html('<span style="color: red;">❌</span>')
    status_display.short_description = "Status"
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(AgentValidationLog)
class AgentValidationLogAdmin(admin.ModelAdmin):
    """Admin für Agent Validation Logs."""
    
    list_display = [
        "timestamp",
        "agent",
        "action",
        "result_display",
        "errors_count",
        "file_path_short",
    ]
    list_filter = [
        "agent",
        "action",
        "passed",
    ]
    search_fields = ["agent", "action", "file_path"]
    date_hierarchy = "timestamp"
    readonly_fields = [
        "timestamp",
        "agent",
        "action",
        "passed",
        "errors_count",
        "warnings_count",
        "errors_prevented",
        "file_path",
        "cascade_session_id",
    ]
    
    def result_display(self, obj):
        if obj.passed:
            return format_html('<span style="color: green;">✅ Passed</span>')
        return format_html(
            '<span style="color: red;">❌ {} Fehler</span>',
            obj.errors_count
        )
    result_display.short_description = "Ergebnis"
    
    def file_path_short(self, obj):
        if obj.file_path:
            return obj.file_path.split("/")[-1]
        return "-"
    file_path_short.short_description = "Datei"
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ControllingBaseline)
class ControllingBaselineAdmin(admin.ModelAdmin):
    """Admin für Controlling Baselines."""
    
    list_display = [
        "created_at",
        "metric_type",
        "period_days",
        "description_short",
    ]
    list_filter = ["metric_type"]
    search_fields = ["metric_type", "description"]
    readonly_fields = ["created_at"]
    
    def description_short(self, obj):
        if obj.description:
            return obj.description[:50] + "..." if len(obj.description) > 50 else obj.description
        return "-"
    description_short.short_description = "Beschreibung"


@admin.register(ControllingAlert)
class ControllingAlertAdmin(admin.ModelAdmin):
    """Admin für Controlling Alerts."""
    
    list_display = [
        "created_at",
        "severity_display",
        "alert_type",
        "message_short",
        "values_display",
        "acknowledged_display",
    ]
    list_filter = [
        "severity",
        "alert_type",
        "acknowledged",
    ]
    search_fields = ["message"]
    date_hierarchy = "created_at"
    actions = ["acknowledge_alerts"]
    
    def severity_display(self, obj):
        colors = {
            "info": "blue",
            "warning": "orange",
            "critical": "red",
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.severity, "black"),
            obj.get_severity_display()
        )
    severity_display.short_description = "Schwere"
    
    def message_short(self, obj):
        return obj.message[:50] + "..." if len(obj.message) > 50 else obj.message
    message_short.short_description = "Nachricht"
    
    def values_display(self, obj):
        if obj.threshold_value and obj.actual_value:
            return f"{obj.actual_value:.1f} / {obj.threshold_value:.1f}"
        return "-"
    values_display.short_description = "Wert / Schwelle"
    
    def acknowledged_display(self, obj):
        if obj.acknowledged:
            return format_html('<span style="color: green;">✅</span>')
        return format_html('<span style="color: gray;">⏳</span>')
    acknowledged_display.short_description = "Bestätigt"
    
    @admin.action(description="Ausgewählte Alerts bestätigen")
    def acknowledge_alerts(self, request, queryset):
        for alert in queryset.filter(acknowledged=False):
            alert.acknowledge(by=request.user.username)
        self.message_user(request, f"{queryset.count()} Alerts bestätigt.")
