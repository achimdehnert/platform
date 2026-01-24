from django.contrib import admin
from django.utils.html import format_html
from .models import MCPServerType, MCPServer, MCPTool, MCPServerLog, MCPConfigSync


@admin.register(MCPServerType)
class MCPServerTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'icon', 'server_count']
    search_fields = ['name']
    
    def server_count(self, obj):
        return obj.servers.count()
    server_count.short_description = 'Servers'


@admin.register(MCPServer)
class MCPServerAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_name', 'status_badge', 'command', 'tool_count', 'is_enabled', 'updated_at']
    list_filter = ['status', 'is_enabled', 'server_type', 'command']
    search_fields = ['name', 'display_name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'last_health_check']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'display_name', 'server_type', 'description')
        }),
        ('Ausführung', {
            'fields': ('command', 'args', 'env')
        }),
        ('Status', {
            'fields': ('status', 'is_enabled', 'disabled_tools')
        }),
        ('Pfade', {
            'fields': ('source_path', 'config_path', 'repo_url', 'version'),
            'classes': ('collapse',)
        }),
        ('Sync', {
            'fields': ('imported_from_config', 'config_key'),
            'classes': ('collapse',)
        }),
        ('Metadaten', {
            'fields': ('created_at', 'updated_at', 'last_health_check'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'active': '#28a745',
            'disabled': '#6c757d',
            'error': '#dc3545',
            'unknown': '#ffc107',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'


@admin.register(MCPTool)
class MCPToolAdmin(admin.ModelAdmin):
    list_display = ['name', 'server', 'category', 'is_enabled', 'usage_count', 'last_used_at']
    list_filter = ['server', 'is_enabled', 'category']
    search_fields = ['name', 'display_name', 'description']
    readonly_fields = ['usage_count', 'last_used_at', 'created_at', 'updated_at']


@admin.register(MCPServerLog)
class MCPServerLogAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'server', 'level_badge', 'message_short']
    list_filter = ['level', 'server']
    search_fields = ['message']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    def level_badge(self, obj):
        colors = {
            'debug': '#6c757d',
            'info': '#17a2b8',
            'warning': '#ffc107',
            'error': '#dc3545',
        }
        color = colors.get(obj.level, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; border-radius: 3px;">{}</span>',
            color, obj.level.upper()
        )
    level_badge.short_description = 'Level'
    
    def message_short(self, obj):
        return obj.message[:80] + '...' if len(obj.message) > 80 else obj.message
    message_short.short_description = 'Message'


@admin.register(MCPConfigSync)
class MCPConfigSyncAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'sync_status', 'servers_added', 'servers_updated', 'config_path']
    list_filter = ['sync_status']
    readonly_fields = ['created_at']
