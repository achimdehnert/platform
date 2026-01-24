"""
Django Admin Configuration for Context Enrichment

Provides UI for managing:
- Context Schemas
- Context Sources (inline)
- Context Enrichment Logs
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
import json

from apps.bfagent.models import (
    ContextSchema,
    ContextSource,
    ContextEnrichmentLog,
)


class ContextSourceInline(admin.TabularInline):
    """Inline editor for context sources"""
    model = ContextSource
    extra = 0
    fields = [
        'order', 'name', 'source_type',
        'is_required_icon', 'is_active_icon', 'edit_link'
    ]
    readonly_fields = ['is_required_icon', 'is_active_icon', 'edit_link']
    ordering = ['order']
    
    classes = ['collapse']
    
    def is_required_icon(self, obj):
        """Display required status"""
        if obj.is_required:
            return format_html('<span style="color: red; font-weight: bold;">⚠️</span>')
        return format_html('<span style="color: gray;">➖</span>')
    is_required_icon.short_description = 'Required'
    
    def is_active_icon(self, obj):
        """Display active status"""
        if obj.is_active:
            return format_html('<span style="color: green;">✅</span>')
        return format_html('<span style="color: red;">❌</span>')
    is_active_icon.short_description = 'Active'
    
    def edit_link(self, obj):
        """Edit link"""
        if obj.pk:
            return format_html(
                '<a href="{}" class="button">✏️ Edit</a>',
                reverse('admin:bfagent_contextsource_change', args=[obj.pk])
            )
        return '-'
    edit_link.short_description = 'Actions'


@admin.register(ContextSchema)
class ContextSchemaAdmin(admin.ModelAdmin):
    """Admin interface for Context Schemas"""

    list_display = [
        'name',
        'display_name',
        'handler_type',
        'version',
        'source_count',
        'is_active_icon',
        'is_system_icon',
    ]
    
    list_display_links = ['name']
    
    list_filter = [
        'is_active',
        'is_system',
        'handler_type',
    ]
    
    search_fields = [
        'name',
        'display_name',
        'description',
        'handler_type',
    ]
    
    # Alle Felder Read-Only in der List View
    list_editable = []
    
    # Read-only fields für Detail View
    readonly_fields = [
        'created_at',
        'updated_at',
        'schema_preview',
    ]
    
    fieldsets = (
        ('Schema Information', {
            'fields': (
                'name',
                'display_name', 
                'description',
                'handler_type',
                'version'
            )
        }),
        ('Status', {
            'fields': ('is_active', 'is_system')
        }),
        ('Schema Preview', {
            'fields': ('schema_preview',),
            'classes': ('wide',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # Keine Inlines für saubere Ansicht
    # inlines = [ContextSourceInline]
    
    actions = [
        'validate_schemas',
        'activate_schemas',
        'deactivate_schemas',
        'view_schema_details',
    ]
    
    # Maximale Items pro Seite
    list_per_page = 50
    
    def get_readonly_fields(self, request, obj=None):
        """System schemas cannot change name or is_system"""
        readonly = list(self.readonly_fields)
        if obj and obj.is_system:
            readonly.extend(['name', 'is_system'])
        return readonly
    
    def is_active_icon(self, obj):
        """Display active status as icon"""
        if obj.is_active:
            return format_html('<span style="color: green; font-size: 18px;">✅</span>')
        return format_html('<span style="color: red; font-size: 18px;">⏸️</span>')
    is_active_icon.short_description = 'Active'
    
    def is_system_icon(self, obj):
        """Display system status as icon"""
        if obj.is_system:
            return format_html('<span style="color: blue; font-size: 18px;">🔒</span>')
        return format_html('<span style="color: gray; font-size: 18px;">📝</span>')
    is_system_icon.short_description = 'System'
    
    def source_count(self, obj):
        """Display active source count"""
        count = obj.sources.filter(is_active=True).count()
        total = obj.sources.count()
        
        if count == total:
            color = 'green'
        elif count == 0:
            color = 'red'
        else:
            color = 'orange'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}/{}</span>',
            color, count, total
        )
    source_count.short_description = 'Sources'
    
    def actions_column(self, obj):
        """Action buttons column"""
        buttons = []
        
        # Test button
        buttons.append(
            f'<a class="button" href="#" onclick="testSchema({obj.pk}); return false;">'
            f'🧪 Test</a>'
        )
        
        # Info button
        buttons.append(
            f'<a class="button" href="#" onclick="showSchemaInfo({obj.pk}); return false;">'
            f'ℹ️ Info</a>'
        )
        
        return mark_safe(' '.join(buttons))
    actions_column.short_description = 'Actions'
    
    def schema_preview(self, obj):
        """Display schema preview with sources"""
        if not obj.pk:
            return '-'
        
        sources = obj.get_active_sources()
        
        html = '<div style="font-family: monospace; background: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 4px solid #007bff;">'
        html += f'<h3 style="margin-top: 0; color: #007bff;">📋 {obj.display_name}</h3>'
        html += f'<p><strong>Handler:</strong> {obj.handler_type}</p>'
        html += f'<p><strong>Version:</strong> {obj.version}</p>'
        html += f'<hr style="border: 0; border-top: 1px solid #dee2e6;">'
        html += f'<h4>🔗 Sources ({sources.count()})</h4>'
        html += '<ol style="line-height: 1.8;">'
        
        for source in sources:
            required_badge = '⚠️ Required' if source.is_required else '➖ Optional'
            active_badge = '✅' if source.is_active else '❌'
            
            html += f'<li>'
            html += f'<strong>{source.name}</strong> '
            html += f'<span style="background: #e9ecef; padding: 2px 8px; border-radius: 3px; font-size: 11px;">{source.source_type}</span> '
            html += f'<span style="font-size: 16px;">{active_badge}</span> '
            html += f'<span style="color: {"#dc3545" if source.is_required else "#6c757d"}; font-size: 11px;">{required_badge}</span>'
            html += f'<br><span style="color: #6c757d; font-size: 12px;">→ {source.context_key or "merged into context"}</span>'
            html += f'</li>'
        
        html += '</ol></div>'
        
        return mark_safe(html)
    schema_preview.short_description = 'Schema Preview'
    
    # Actions
    def validate_schemas(self, request, queryset):
        """Validate selected schemas"""
        from apps.bfagent.services.context_enrichment.validators import SchemaValidator
        validator = SchemaValidator()
        
        for schema in queryset:
            errors = validator.validate(schema)
            if errors:
                self.message_user(
                    request,
                    f"❌ Schema '{schema.name}' has errors: {', '.join(errors)}",
                    level='ERROR'
                )
            else:
                self.message_user(
                    request,
                    f"✅ Schema '{schema.name}' is valid",
                    level='SUCCESS'
                )
    validate_schemas.short_description = '🔍 Validate selected schemas'
    
    def activate_schemas(self, request, queryset):
        """Activate selected schemas"""
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f"✅ Activated {updated} schema(s)",
            level='SUCCESS'
        )
    activate_schemas.short_description = '✅ Activate selected schemas'
    
    def deactivate_schemas(self, request, queryset):
        """Deactivate selected schemas"""
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f"⏸️ Deactivated {updated} schema(s)",
            level='WARNING'
        )
    deactivate_schemas.short_description = '⏸️ Deactivate selected schemas'
    
    def view_schema_details(self, request, queryset):
        """View schema details action"""
        if queryset.count() == 1:
            schema = queryset.first()
            from django.http import HttpResponseRedirect
            from django.urls import reverse
            url = reverse('admin:bfagent_contextschema_change', args=[schema.pk])
            return HttpResponseRedirect(url)
        else:
            self.message_user(
                request,
                "Please select exactly one schema to view details",
                level='WARNING'
            )
    view_schema_details.short_description = '👁️ View Details'


@admin.register(ContextSource)
class ContextSourceAdmin(admin.ModelAdmin):
    """Admin interface for Context Sources"""
    
    list_display = [
        'name',
        'schema',
        'source_type',
        'order',
        'model_name',
        'is_required',
        'is_active',
    ]
    
    list_filter = [
        'source_type',
        'is_required',
        'is_active',
        'schema',
    ]
    
    search_fields = [
        'name',
        'model_name',
        'function_name',
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'config_display',
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('schema', 'name', 'order', 'source_type')
        }),
        ('Model Configuration', {
            'fields': ('model_name', 'filter_config', 'fields', 'field_mappings'),
            'classes': ('collapse',)
        }),
        ('Query Configuration', {
            'fields': ('aggregate_type', 'order_by'),
            'classes': ('collapse',)
        }),
        ('Computed Configuration', {
            'fields': ('function_name', 'function_params'),
            'classes': ('collapse',)
        }),
        ('Output Configuration', {
            'fields': ('context_key',)
        }),
        ('Error Handling', {
            'fields': ('is_required', 'fallback_value', 'default_value', 'timeout_seconds')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'config_display'),
            'classes': ('collapse',)
        }),
    )
    
    def config_display(self, obj):
        """Display configuration as formatted JSON"""
        if not obj.pk:
            return '-'
        
        config = {
            'source_type': obj.source_type,
            'model_name': obj.model_name,
            'filter_config': obj.filter_config,
            'fields': obj.fields,
            'field_mappings': obj.field_mappings,
            'aggregate_type': obj.aggregate_type,
            'context_key': obj.context_key or 'merged',
        }
        
        formatted_json = json.dumps(config, indent=2)
        return format_html(
            '<pre style="background: #f5f5f5; padding: 10px; border-radius: 4px;">{}</pre>',
            formatted_json
        )
    config_display.short_description = 'Configuration (JSON)'


@admin.register(ContextEnrichmentLog)
class ContextEnrichmentLogAdmin(admin.ModelAdmin):
    """Admin interface for Context Enrichment Logs"""
    
    list_display = [
        'id',
        'schema',
        'handler_name',
        'success_icon',
        'execution_time_ms',
        'created_at',
    ]
    
    list_filter = [
        'success',
        'schema',
        'created_at',
    ]
    
    search_fields = [
        'handler_name',
        'error_message',
    ]
    
    readonly_fields = [
        'schema',
        'handler_name',
        'params',
        'enriched_context',
        'execution_time_ms',
        'success',
        'error_message',
        'created_at',
        'params_display',
        'context_display',
    ]
    
    fieldsets = (
        ('Execution Info', {
            'fields': ('schema', 'handler_name', 'execution_time_ms', 'success', 'created_at')
        }),
        ('Parameters', {
            'fields': ('params', 'params_display'),
            'classes': ('collapse',)
        }),
        ('Result', {
            'fields': ('enriched_context', 'context_display'),
            'classes': ('collapse',)
        }),
        ('Errors', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Logs are created automatically"""
        return False
    
    def success_icon(self, obj):
        """Display success/failure icon"""
        if obj.success:
            return format_html(
                '<span style="color: green; font-size: 16px;">✅</span>'
            )
        else:
            return format_html(
                '<span style="color: red; font-size: 16px;">❌</span>'
            )
    success_icon.short_description = 'Status'
    
    def params_display(self, obj):
        """Display parameters as formatted JSON"""
        if not obj.params:
            return '-'
        formatted_json = json.dumps(obj.params, indent=2)
        return format_html(
            '<pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; max-height: 300px; overflow: auto;">{}</pre>',
            formatted_json
        )
    params_display.short_description = 'Parameters (Formatted)'
    
    def context_display(self, obj):
        """Display context as formatted JSON"""
        if not obj.enriched_context:
            return '-'
        formatted_json = json.dumps(obj.enriched_context, indent=2)
        return format_html(
            '<pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; max-height: 300px; overflow: auto;">{}</pre>',
            formatted_json
        )
    context_display.short_description = 'Enriched Context (Formatted)'
