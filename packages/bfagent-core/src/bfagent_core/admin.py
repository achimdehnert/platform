"""Django admin for bfagent-core models."""

from django.contrib import admin
from bfagent_core.models import (
    AuditEvent,
    OutboxMessage,
    Plan,
    CoreUser,
    Tenant,
    TenantMembership,
    CorePermission,
    CoreRolePermission,
    MembershipPermissionOverride,
    PermissionAudit,
)


# ═══════════════════════════════════════════════════════════════════════════════
# PLAN ADMIN
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    """Admin for subscription plans."""
    
    list_display = ["code", "name", "is_public", "sort_order", "monthly_price", "yearly_price"]
    list_filter = ["is_public"]
    search_fields = ["code", "name"]
    ordering = ["sort_order", "code"]
    
    @admin.display(description="Monthly")
    def monthly_price(self, obj):
        return f"€{obj.monthly_price:.2f}" if obj.monthly_price else "-"
    
    @admin.display(description="Yearly")
    def yearly_price(self, obj):
        return f"€{obj.yearly_price:.2f}" if obj.yearly_price else "-"


# ═══════════════════════════════════════════════════════════════════════════════
# CORE USER ADMIN
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(CoreUser)
class CoreUserAdmin(admin.ModelAdmin):
    """Admin for core users (SSO bridge)."""
    
    list_display = ["id", "email", "display_name", "provider", "legacy_user_id", "created_at"]
    list_filter = ["provider"]
    search_fields = ["email", "display_name", "external_id"]
    readonly_fields = ["id", "created_at", "updated_at", "last_login_at"]
    ordering = ["-created_at"]


# ═══════════════════════════════════════════════════════════════════════════════
# TENANT ADMIN
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    """Admin for tenants."""
    
    list_display = ["slug", "name", "status", "plan", "created_at"]
    list_filter = ["status", "plan"]
    search_fields = ["slug", "name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    ordering = ["name"]
    
    fieldsets = (
        (None, {
            "fields": ("id", "slug", "name", "status", "plan")
        }),
        ("Lifecycle", {
            "fields": ("trial_ends_at", "suspended_at", "suspended_reason", "deleted_at"),
            "classes": ("collapse",),
        }),
        ("Settings", {
            "fields": ("settings", "stripe_customer_id"),
            "classes": ("collapse",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# MEMBERSHIP ADMIN
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(TenantMembership)
class TenantMembershipAdmin(admin.ModelAdmin):
    """Admin for tenant memberships."""
    
    list_display = ["user", "tenant", "role", "status", "permission_version", "created_at"]
    list_filter = ["role", "status"]
    search_fields = ["user__email", "tenant__slug", "tenant__name"]
    readonly_fields = ["id", "permission_version", "created_at", "updated_at"]
    raw_id_fields = ["user", "tenant", "invited_by"]
    ordering = ["-created_at"]


# ═══════════════════════════════════════════════════════════════════════════════
# PERMISSION ADMIN
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(CorePermission)
class CorePermissionAdmin(admin.ModelAdmin):
    """Admin for permissions (read-only, managed via code)."""
    
    list_display = ["code", "category", "description"]
    list_filter = ["category"]
    search_fields = ["code", "description"]
    ordering = ["category", "code"]
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CoreRolePermission)
class CoreRolePermissionAdmin(admin.ModelAdmin):
    """Admin for role-permission mappings (read-only)."""
    
    list_display = ["role", "permission"]
    list_filter = ["role"]
    search_fields = ["permission__code"]
    ordering = ["role", "permission"]
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(MembershipPermissionOverride)
class MembershipPermissionOverrideAdmin(admin.ModelAdmin):
    """Admin for permission overrides."""
    
    list_display = ["membership", "permission", "allowed", "expires_at", "created_at"]
    list_filter = ["allowed"]
    search_fields = ["membership__user__email", "permission__code"]
    raw_id_fields = ["membership", "granted_by"]
    ordering = ["-created_at"]


@admin.register(PermissionAudit)
class PermissionAuditAdmin(admin.ModelAdmin):
    """Admin for permission audit trail (read-only)."""
    
    list_display = ["performed_at", "tenant_id", "action", "permission_code", "user_id"]
    list_filter = ["action"]
    search_fields = ["permission_code", "tenant_id", "user_id"]
    readonly_fields = [
        "id", "tenant_id", "membership_id", "user_id", "permission_code",
        "action", "performed_by_id", "performed_at", "previous_value",
        "new_value", "reason", "request_id",
    ]
    ordering = ["-performed_at"]
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# LEGACY MODELS
# ═══════════════════════════════════════════════════════════════════════════════

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
