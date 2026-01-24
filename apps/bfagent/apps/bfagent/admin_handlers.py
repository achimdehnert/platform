"""
Django Admin für Handler-Verwaltung

Zentrales Admin-Interface für:
- Handler (DB-registrierte Handler)
- ActionHandler (Workflow Actions)
- HandlerExecution (Execution Tracking)
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models_handlers import Handler, ActionHandler, HandlerExecution


@admin.register(Handler)
class HandlerAdmin(admin.ModelAdmin):
    """
    Handler Management - Zentrale Verwaltung aller registrierten Handler
    
    Organisiert nach Domains:
    - bookwriting.*  (Book Writing Studio)
    - medtrans.*    (Medical Translation)
    - genagent.*    (Generic Agents)
    """
    
    list_display = [
        'handler_id',
        'display_name',
        'category',
        'domain_badge',
        'version',
        'status_badge',
        'performance_badge',
        'total_executions',
        'created_at',
    ]
    
    list_filter = [
        'category',
        'is_active',
        'is_deprecated',
        'is_experimental',
        'requires_llm',
        'created_at',
    ]
    
    search_fields = [
        'handler_id',
        'display_name',
        'description',
        'module_path',
        'class_name',
    ]
    
    readonly_fields = [
        'handler_id',
        'created_at',
        'updated_at',
        'total_executions',
        'avg_execution_time_ms',
        'success_rate',
        'performance_chart',
        'dependency_graph',
        'schema_preview',
    ]
    
    fieldsets = (
        ('Identification', {
            'fields': ('handler_id', 'display_name', 'description', 'category')
        }),
        ('Code Reference', {
            'fields': ('module_path', 'class_name', 'version')
        }),
        ('Configuration', {
            'fields': ('config_schema', 'input_schema', 'output_schema', 'schema_preview'),
            'classes': ('collapse',)
        }),
        ('Dependencies', {
            'fields': ('required_handlers', 'dependency_graph'),
            'classes': ('collapse',)
        }),
        ('Status & Flags', {
            'fields': (
                'is_active',
                'is_deprecated',
                'deprecation_reason',
                'replacement_handler_id',
                'is_experimental',
                'requires_llm',
            )
        }),
        ('Performance Metrics', {
            'fields': (
                'total_executions',
                'avg_execution_time_ms',
                'success_rate',
                'performance_chart',
            )
        }),
        ('Documentation', {
            'fields': ('documentation_url', 'example_config'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def domain_badge(self, obj):
        """Extract and display domain from handler_id"""
        domain = obj.handler_id.split('.')[0] if '.' in obj.handler_id else 'unknown'
        colors = {
            'bookwriting': '#8B5CF6',  # Purple
            'medtrans': '#10B981',     # Green
            'genagent': '#3B82F6',     # Blue
            'core': '#6B7280',         # Gray
        }
        color = colors.get(domain, '#9CA3AF')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            domain.upper()
        )
    domain_badge.short_description = 'Domain'
    
    def status_badge(self, obj):
        """Display handler status with color coding"""
        if obj.is_deprecated:
            return format_html(
                '<span style="background-color: #EF4444; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px;">DEPRECATED</span>'
            )
        elif not obj.is_active:
            return format_html(
                '<span style="background-color: #9CA3AF; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px;">INACTIVE</span>'
            )
        elif obj.is_experimental:
            return format_html(
                '<span style="background-color: #F59E0B; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px;">EXPERIMENTAL</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #10B981; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px;">ACTIVE</span>'
            )
    status_badge.short_description = 'Status'
    
    def performance_badge(self, obj):
        """Display performance metrics badge"""
        if obj.success_rate >= 95:
            color = '#10B981'  # Green
            label = 'EXCELLENT'
        elif obj.success_rate >= 80:
            color = '#F59E0B'  # Orange
            label = 'GOOD'
        else:
            color = '#EF4444'  # Red
            label = 'NEEDS ATTENTION'
        
        return format_html(
            '<div style="text-align: center;">'
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px; display: block; margin-bottom: 2px;">{}</span>'
            '<small style="color: #6B7280;">{:.1f}% success</small>'
            '</div>',
            color,
            label,
            obj.success_rate
        )
    performance_badge.short_description = 'Performance'
    
    def performance_chart(self, obj):
        """Display performance metrics visualization"""
        return format_html(
            '<div style="padding: 10px; background: #F9FAFB; border-radius: 5px;">'
            '<h4 style="margin: 0 0 10px 0;">Performance Metrics</h4>'
            '<div style="margin-bottom: 8px;">'
            '<strong>Success Rate:</strong> '
            '<div style="width: 200px; background-color: #E5E7EB; border-radius: 3px; display: inline-block; margin-left: 10px;">'
            '<div style="width: {}%; background-color: #10B981; height: 20px; border-radius: 3px; text-align: center; color: white; font-size: 12px; line-height: 20px;">'
            '{:.1f}%</div></div></div>'
            '<div><strong>Avg Response:</strong> {} ms</div>'
            '<div><strong>Total Runs:</strong> {:,}</div>'
            '</div>',
            obj.success_rate,
            obj.success_rate,
            obj.avg_execution_time_ms,
            obj.total_executions
        )
    performance_chart.short_description = 'Performance Details'
    
    def dependency_graph(self, obj):
        """Display handler dependencies"""
        if not obj.required_handlers.exists():
            return mark_safe('<em style="color: #9CA3AF;">No dependencies</em>')
        
        deps = obj.required_handlers.all()
        html = '<div style="padding: 10px; background: #F9FAFB; border-radius: 5px;">'
        html += '<h4 style="margin: 0 0 10px 0;">Required Handlers</h4>'
        html += '<ul style="margin: 0; padding-left: 20px;">'
        for dep in deps:
            html += f'<li><code>{dep.handler_id}</code> - {dep.display_name}</li>'
        html += '</ul></div>'
        return mark_safe(html)
    dependency_graph.short_description = 'Dependencies'
    
    def schema_preview(self, obj):
        """Display schema preview"""
        import json
        html = '<div style="font-family: monospace; font-size: 12px; background: #1F2937; color: #D1D5DB; padding: 10px; border-radius: 5px; overflow-x: auto;">'
        
        if obj.input_schema:
            html += '<h4 style="color: #10B981; margin: 0 0 5px 0;">Input Schema:</h4>'
            html += f'<pre style="margin: 0 0 15px 0;">{json.dumps(obj.input_schema, indent=2)}</pre>'
        
        if obj.output_schema:
            html += '<h4 style="color: #3B82F6; margin: 0 0 5px 0;">Output Schema:</h4>'
            html += f'<pre style="margin: 0;">{json.dumps(obj.output_schema, indent=2)}</pre>'
        
        html += '</div>'
        return mark_safe(html)
    schema_preview.short_description = 'Schema Preview'


@admin.register(ActionHandler)
class ActionHandlerAdmin(admin.ModelAdmin):
    """
    Action Handler Management - Workflow Actions
    
    Verknüpft Handler mit Workflow-Phasen für automatische Ausführung
    """
    
    list_display = [
        'name',
        'handler_link',
        'action_link',
        'phase_link',
        'is_active',
        'execution_count',
        'success_rate_display',
        'avg_duration',
    ]
    
    list_filter = [
        'is_active',
        'created_at',
    ]
    
    search_fields = [
        'name',
        'description',
        'handler__handler_id',
        'handler__display_name',
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'execution_history',
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Handler Configuration', {
            'fields': ('handler', 'default_config')
        }),
        ('Workflow Integration', {
            'fields': ('action', 'phase'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
        ('Execution History', {
            'fields': ('execution_history',),
            'classes': ('collapse',)
        }),
    )
    
    def handler_link(self, obj):
        if obj.handler:
            url = reverse('admin:bfagent_handler_change', args=[obj.handler.pk])
            return format_html('<a href="{}">{}</a>', url, obj.handler.handler_id)
        return '-'
    handler_link.short_description = 'Handler'
    
    def action_link(self, obj):
        if obj.action:
            url = reverse('admin:bfagent_agentaction_change', args=[obj.action.pk])
            return format_html('<a href="{}">{}</a>', url, obj.action.name)
        return '-'
    action_link.short_description = 'Action'
    
    def phase_link(self, obj):
        if obj.phase:
            url = reverse('admin:bfagent_workflowphase_change', args=[obj.phase.pk])
            return format_html('<a href="{}">{}</a>', url, obj.phase.name)
        return '-'
    phase_link.short_description = 'Phase'
    
    def execution_count(self, obj):
        return obj.handler_executions.count() if obj.handler else 0
    execution_count.short_description = 'Executions'
    
    def success_rate_display(self, obj):
        if not obj.handler:
            return '-'
        executions = obj.handler_executions.all()
        if not executions:
            return 'N/A'
        success = executions.filter(success=True).count()
        total = executions.count()
        rate = (success / total * 100) if total > 0 else 0
        return f'{rate:.1f}%'
    success_rate_display.short_description = 'Success Rate'
    
    def avg_duration(self, obj):
        if not obj.handler:
            return '-'
        executions = obj.handler_executions.all()
        if not executions:
            return 'N/A'
        from django.db.models import Avg
        avg = executions.aggregate(Avg('execution_time_ms'))['execution_time_ms__avg']
        return f'{avg:.0f} ms' if avg else 'N/A'
    avg_duration.short_description = 'Avg Duration'
    
    def execution_history(self, obj):
        """Display recent execution history"""
        executions = obj.handler_executions.order_by('-started_at')[:10]
        if not executions:
            return mark_safe('<em style="color: #9CA3AF;">No executions yet</em>')
        
        html = '<table style="width: 100%; border-collapse: collapse;">'
        html += '<tr style="background: #F9FAFB; font-weight: bold;"><th>Started</th><th>Success</th><th>Duration</th><th>Error</th></tr>'
        for ex in executions:
            status_color = '#10B981' if ex.success else '#EF4444'
            html += f'<tr style="border-bottom: 1px solid #E5E7EB;">'
            html += f'<td>{ex.started_at.strftime("%Y-%m-%d %H:%M:%S")}</td>'
            html += f'<td><span style="color: {status_color};">{"✓" if ex.success else "✗"}</span></td>'
            html += f'<td>{ex.execution_time_ms:.0f} ms</td>'
            html += f'<td>{ex.error_message[:50] if ex.error_message else "-"}</td>'
            html += '</tr>'
        html += '</table>'
        return mark_safe(html)
    execution_history.short_description = 'Recent Executions'


@admin.register(HandlerExecution)
class HandlerExecutionAdmin(admin.ModelAdmin):
    """
    Handler Execution Tracking - Ausführungshistorie
    
    Trackt alle Handler-Ausführungen für Performance-Analyse und Debugging
    """
    
    list_display = [
        'id',
        'handler_link',
        'action_handler_link',
        'success_badge',
        'execution_time_ms',
        'started_at',
        'user',
    ]
    
    list_filter = [
        'success',
        'started_at',
    ]
    
    search_fields = [
        'handler__handler_id',
        'action_handler__name',
        'error_message',
    ]
    
    readonly_fields = [
        'handler',
        'action_handler',
        'context_data',
        'result_data',
        'started_at',
        'completed_at',
        'execution_time_ms',
        'success',
        'error_message',
        'user',
    ]
    
    fieldsets = (
        ('Execution Details', {
            'fields': ('handler', 'action_handler', 'user', 'success', 'execution_time_ms')
        }),
        ('Timing', {
            'fields': ('started_at', 'completed_at')
        }),
        ('Data', {
            'fields': ('context_data', 'result_data'),
            'classes': ('collapse',)
        }),
        ('Error Details', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def handler_link(self, obj):
        if obj.handler:
            url = reverse('admin:bfagent_handler_change', args=[obj.handler.pk])
            return format_html('<a href="{}">{}</a>', url, obj.handler.handler_id)
        return '-'
    handler_link.short_description = 'Handler'
    
    def action_handler_link(self, obj):
        if obj.action_handler:
            url = reverse('admin:bfagent_actionhandler_change', args=[obj.action_handler.pk])
            return format_html('<a href="{}">{}</a>', url, obj.action_handler.name)
        return '-'
    action_handler_link.short_description = 'Action Handler'
    
    def success_badge(self, obj):
        if obj.success:
            return format_html(
                '<span style="background-color: #10B981; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px;">SUCCESS</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #EF4444; color: white; padding: 3px 8px; '
                'border-radius: 3px; font-size: 11px;">FAILED</span>'
            )
    success_badge.short_description = 'Status'
