"""Django admin for bfagent-core models."""

from django.contrib import admin
from bfagent_core.models import AuditEvent, OutboxMessage


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    """Admin for audit events (read-only)."""
    
    list_display = [
        "created_at",
        "tenant_id",
        "category",
        "action",
        "entity_type",
        "entity_id",
        "actor_user_id",
    ]
    list_filter = ["category", "action", "entity_type"]
    search_fields = ["entity_id", "tenant_id", "actor_user_id", "request_id"]
    readonly_fields = [
        "id",
        "tenant_id",
        "actor_user_id",
        "category",
        "action",
        "entity_type",
        "entity_id",
        "payload",
        "request_id",
        "created_at",
    ]
    ordering = ["-created_at"]
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(OutboxMessage)
class OutboxMessageAdmin(admin.ModelAdmin):
    """Admin for outbox messages."""
    
    list_display = [
        "created_at",
        "tenant_id",
        "topic",
        "is_published",
        "published_at",
    ]
    list_filter = ["topic", "published_at"]
    search_fields = ["topic", "tenant_id"]
    readonly_fields = [
        "id",
        "tenant_id",
        "topic",
        "payload",
        "created_at",
    ]
    ordering = ["-created_at"]
    
    @admin.display(boolean=True, description="Published")
    def is_published(self, obj):
        return obj.is_published
