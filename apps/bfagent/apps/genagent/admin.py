"""
GenAgent Admin Interface
"""

from django.contrib import admin
from .models import Phase, Action, ExecutionLog


class ActionInline(admin.TabularInline):
    """Inline admin for Actions within Phase"""
    model = Action
    extra = 1
    fields = ['name', 'handler_class', 'order', 'is_active', 'retry_count']
    ordering = ['order']


@admin.register(Phase)
class PhaseAdmin(admin.ModelAdmin):
    """Admin for Phase model"""
    
    list_display = ['order', 'name', 'is_active', 'action_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['order', 'name']
    inlines = [ActionInline]
    
    fieldsets = [
        ('Basic Information', {
            'fields': ['name', 'description', 'is_active']
        }),
        ('Display', {
            'fields': ['order', 'color']
        }),
    ]
    
    def action_count(self, obj):
        """Count of actions in this phase"""
        return obj.actions.count()
    action_count.short_description = 'Actions'


@admin.register(Action)
class ActionAdmin(admin.ModelAdmin):
    """Admin for Action model"""
    
    list_display = ['name', 'phase', 'handler_class', 'order', 'is_active', 'retry_count']
    list_filter = ['is_active', 'phase', 'continue_on_error']
    search_fields = ['name', 'description', 'handler_class']
    ordering = ['phase__order', 'order']
    
    fieldsets = [
        ('Basic Information', {
            'fields': ['phase', 'name', 'description', 'is_active']
        }),
        ('Handler Configuration', {
            'fields': ['handler_class', 'config', 'order']
        }),
        ('Execution Settings', {
            'fields': ['timeout_seconds', 'retry_count', 'continue_on_error']
        }),
    ]


@admin.register(ExecutionLog)
class ExecutionLogAdmin(admin.ModelAdmin):
    """Admin for ExecutionLog model"""
    
    list_display = ['action', 'status', 'duration_seconds', 'started_at', 'finished_at']
    list_filter = ['status', 'created_at']
    search_fields = ['action__name', 'error_message']
    ordering = ['-created_at']
    readonly_fields = ['action', 'status', 'started_at', 'finished_at', 
                       'duration_seconds', 'input_data', 'output_data', 
                       'error_message', 'created_at']
    
    fieldsets = [
        ('Execution Info', {
            'fields': ['action', 'status', 'started_at', 'finished_at', 'duration_seconds']
        }),
        ('Data', {
            'fields': ['input_data', 'output_data'],
            'classes': ['collapse']
        }),
        ('Error Details', {
            'fields': ['error_message'],
            'classes': ['collapse']
        }),
    ]
    
    def has_add_permission(self, request):
        """Execution logs are created automatically, not manually"""
        return False
