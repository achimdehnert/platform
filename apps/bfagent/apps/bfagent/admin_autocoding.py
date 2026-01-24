"""
Admin Interface für Autocoding System
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse

from .models_autocoding import AutocodingRun, ToolCall, Artifact


class ToolCallInline(admin.TabularInline):
    model = ToolCall
    extra = 0
    readonly_fields = ['tool_name', 'started_at', 'duration_ms', 'ok', 'exit_code']
    fields = ['tool_name', 'started_at', 'duration_ms', 'ok', 'exit_code']
    can_delete = False
    max_num = 0
    
    def has_add_permission(self, request, obj=None):
        return False


class ArtifactInline(admin.TabularInline):
    model = Artifact
    extra = 0
    readonly_fields = ['kind', 'file_path', 'size_bytes', 'sha256_short', 'created_at']
    fields = ['kind', 'file_path', 'size_bytes', 'sha256_short', 'created_at']
    can_delete = False
    max_num = 0
    
    def sha256_short(self, obj):
        return obj.sha256[:12] + '...' if obj.sha256 else '-'
    sha256_short.short_description = 'SHA256'
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(AutocodingRun)
class AutocodingRunAdmin(admin.ModelAdmin):
    list_display = [
        'id_short', 'requirement_link', 'status_badge', 
        'complexity', 'llm_name', 'tokens_display', 'created_at'
    ]
    list_filter = ['status', 'complexity', 'risk', 'llm']
    search_fields = ['id', 'requirement__name', 'task_text']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'started_at', 'completed_at',
        'total_tokens_input', 'total_tokens_output', 'total_cost',
        'duration_display', 'analysis_result_preview'
    ]
    raw_id_fields = ['requirement', 'llm', 'created_by']
    inlines = [ToolCallInline, ArtifactInline]
    
    fieldsets = (
        ('Identifikation', {
            'fields': ('id', 'requirement', 'created_by')
        }),
        ('Aufgabe', {
            'fields': ('task_text', 'repo_url', 'base_branch', 'workspace_path')
        }),
        ('Klassifikation & Routing', {
            'fields': ('complexity', 'risk', 'llm', 'routing_reason')
        }),
        ('Status', {
            'fields': ('status', 'current_iteration', 'max_iterations', 'error_message')
        }),
        ('Ergebnisse', {
            'fields': ('analysis_result_preview', 'tasks_extracted'),
            'classes': ('collapse',)
        }),
        ('Metriken', {
            'fields': (
                'total_tokens_input', 'total_tokens_output', 'total_cost',
                'duration_display'
            )
        }),
        ('Zeitstempel', {
            'fields': ('created_at', 'updated_at', 'started_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def id_short(self, obj):
        return str(obj.id)[:8]
    id_short.short_description = 'ID'
    
    def requirement_link(self, obj):
        url = reverse('admin:bfagent_testrequirement_change', args=[obj.requirement.id])
        return format_html('<a href="{}">{}</a>', url, obj.requirement.name[:40])
    requirement_link.short_description = 'Requirement'
    
    def status_badge(self, obj):
        colors = {
            'created': '#6c757d',
            'analyzing': '#17a2b8',
            'planning': '#007bff',
            'executing': '#ffc107',
            'reviewing': '#fd7e14',
            'completed': '#28a745',
            'failed': '#dc3545',
            'cancelled': '#6c757d',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background:{}; color:white; padding:3px 8px; border-radius:4px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def llm_name(self, obj):
        return obj.llm.name if obj.llm else '-'
    llm_name.short_description = 'LLM'
    
    def tokens_display(self, obj):
        return f"{obj.total_tokens:,}"
    tokens_display.short_description = 'Tokens'
    
    def duration_display(self, obj):
        if obj.duration_seconds:
            return f"{obj.duration_seconds:.1f}s"
        return '-'
    duration_display.short_description = 'Dauer'
    
    def analysis_result_preview(self, obj):
        if obj.analysis_result:
            response = obj.analysis_result.get('response', '')
            preview = response[:500] + '...' if len(response) > 500 else response
            return format_html('<pre style="white-space:pre-wrap;">{}</pre>', preview)
        return '-'
    analysis_result_preview.short_description = 'Analyse (Vorschau)'


@admin.register(ToolCall)
class ToolCallAdmin(admin.ModelAdmin):
    list_display = ['id_short', 'run_link', 'tool_name', 'ok_badge', 'duration_ms', 'started_at']
    list_filter = ['tool_name', 'ok']
    search_fields = ['tool_name', 'run__id']
    readonly_fields = [
        'id', 'run', 'started_at', 'ended_at', 'duration_ms',
        'stdout_sha256', 'stderr_sha256', 'args_sha256'
    ]
    raw_id_fields = ['run']
    
    def id_short(self, obj):
        return str(obj.id)[:8]
    id_short.short_description = 'ID'
    
    def run_link(self, obj):
        url = reverse('admin:bfagent_autocodingrun_change', args=[obj.run.id])
        return format_html('<a href="{}">{}</a>', url, str(obj.run.id)[:8])
    run_link.short_description = 'Run'
    
    def ok_badge(self, obj):
        if obj.ok:
            return format_html('<span style="color:green;">✓</span>')
        return format_html('<span style="color:red;">✗</span>')
    ok_badge.short_description = 'OK'


@admin.register(Artifact)
class ArtifactAdmin(admin.ModelAdmin):
    list_display = ['id_short', 'run_link', 'kind', 'file_path', 'size_display', 'created_at']
    list_filter = ['kind']
    search_fields = ['file_path', 'run__id']
    readonly_fields = ['id', 'run', 'tool_call', 'sha256', 'size_bytes', 'created_at']
    raw_id_fields = ['run', 'tool_call', 'refactor_session']
    
    def id_short(self, obj):
        return str(obj.id)[:8]
    id_short.short_description = 'ID'
    
    def run_link(self, obj):
        url = reverse('admin:bfagent_autocodingrun_change', args=[obj.run.id])
        return format_html('<a href="{}">{}</a>', url, str(obj.run.id)[:8])
    run_link.short_description = 'Run'
    
    def size_display(self, obj):
        if obj.size_bytes < 1024:
            return f"{obj.size_bytes} B"
        elif obj.size_bytes < 1024 * 1024:
            return f"{obj.size_bytes / 1024:.1f} KB"
        return f"{obj.size_bytes / (1024*1024):.1f} MB"
    size_display.short_description = 'Größe'
