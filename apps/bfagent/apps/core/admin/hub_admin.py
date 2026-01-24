"""
Admin configuration for Hub model.
"""

from django.contrib import admin
from apps.core.models.hub import Hub, HubStatus, HubCategory


@admin.register(Hub)
class HubAdmin(admin.ModelAdmin):
    """Admin for Hub management."""
    
    list_display = [
        "name", "hub_id", "version", "category", "status", 
        "is_active", "is_installed", "updated_at"
    ]
    list_filter = ["status", "category", "is_active", "is_installed"]
    search_fields = ["hub_id", "name", "description"]
    readonly_fields = ["created_at", "updated_at"]
    
    fieldsets = [
        ("Identifikation", {
            "fields": ["hub_id", "name", "description"]
        }),
        ("Klassifizierung", {
            "fields": ["category", "status", "icon", "version", "author"]
        }),
        ("Technisch", {
            "fields": ["entry_point", "dependencies", "provides"],
            "classes": ["collapse"]
        }),
        ("Konfiguration", {
            "fields": ["config", "config_schema"],
            "classes": ["collapse"]
        }),
        ("Status", {
            "fields": ["is_active", "is_installed"]
        }),
        ("Audit", {
            "fields": ["created_at", "updated_at"],
            "classes": ["collapse"]
        }),
    ]
    
    actions = ["activate_hubs", "deactivate_hubs"]
    
    @admin.action(description="Ausgewählte Hubs aktivieren")
    def activate_hubs(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} Hub(s) aktiviert.")
    
    @admin.action(description="Ausgewählte Hubs deaktivieren")
    def deactivate_hubs(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} Hub(s) deaktiviert.")
