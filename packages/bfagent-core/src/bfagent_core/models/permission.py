"""
Permission models for RBAC system.

Fully normalized:
- CorePermission: Permission registry
- CoreRolePermission: Role → Permission mapping
- MembershipPermissionOverride: Per-membership overrides
"""

import uuid
from django.db import models


class CorePermission(models.Model):
    """
    Permission registry.
    
    All valid permission codes are stored here for referential integrity.
    Synced from Python Enum via sync_permissions_to_db().
    """
    
    code = models.CharField(
        primary_key=True,
        max_length=100,
        help_text="Permission code (e.g., 'stories.create')",
    )
    
    description = models.TextField(
        blank=True,
        default="",
        help_text="Human-readable description",
    )
    
    category = models.CharField(
        max_length=50,
        default="general",
        db_index=True,
        help_text="Permission category for grouping",
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "core_permission"
        ordering = ["category", "code"]
    
    def __str__(self) -> str:
        return self.code


class CoreRolePermission(models.Model):
    """
    Role → Permission mapping.
    
    Static mapping that defines base permissions for each role.
    """
    
    role = models.CharField(
        max_length=20,
        db_index=True,
        help_text="Role name (owner, admin, member, viewer)",
    )
    
    permission = models.ForeignKey(
        CorePermission,
        on_delete=models.CASCADE,
        related_name="role_assignments",
    )
    
    class Meta:
        db_table = "core_role_permission"
        constraints = [
            models.UniqueConstraint(
                fields=["role", "permission"],
                name="role_permission_unique",
            ),
            models.CheckConstraint(
                check=models.Q(role__in=["owner", "admin", "member", "viewer"]),
                name="role_permission_role_chk",
            ),
        ]
        indexes = [
            models.Index(fields=["role"]),
        ]
    
    def __str__(self) -> str:
        return f"{self.role} → {self.permission_id}"


class MembershipPermissionOverride(models.Model):
    """
    Per-membership permission override.
    
    Allows granting or revoking specific permissions for a user,
    overriding the role-based defaults.
    
    Features:
    - expires_at: Temporary permissions
    - reason: Audit trail
    """
    
    membership = models.ForeignKey(
        "bfagent_core.TenantMembership",
        on_delete=models.CASCADE,
        related_name="permission_overrides",
    )
    
    permission = models.ForeignKey(
        CorePermission,
        on_delete=models.CASCADE,
        related_name="membership_overrides",
    )
    
    allowed = models.BooleanField(
        help_text="True = grant, False = deny",
    )
    
    # Expiration (optional)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Override expires at this time (NULL = permanent)",
    )
    
    # Audit
    reason = models.TextField(
        blank=True,
        default="",
        help_text="Reason for override",
    )
    
    granted_by = models.ForeignKey(
        "bfagent_core.CoreUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="permission_grants",
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "core_membership_permission_override"
        constraints = [
            models.UniqueConstraint(
                fields=["membership", "permission"],
                name="override_membership_perm_unique",
            ),
        ]
        indexes = [
            models.Index(fields=["membership"]),
            models.Index(
                fields=["expires_at"],
                condition=models.Q(expires_at__isnull=False),
                name="override_expires_idx",
            ),
        ]
    
    def __str__(self) -> str:
        action = "GRANT" if self.allowed else "DENY"
        return f"{action} {self.permission_id} for {self.membership_id}"
    
    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        from django.utils import timezone
        return timezone.now() > self.expires_at


class PermissionAudit(models.Model):
    """
    Audit trail for permission changes.
    
    Denormalized for fast queries.
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    
    # Denormalized for queries
    tenant_id = models.UUIDField(db_index=True)
    membership_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)
    
    permission_code = models.CharField(max_length=100)
    
    action = models.CharField(
        max_length=20,
        help_text="grant, revoke, clear, role_change",
    )
    
    performed_by_id = models.UUIDField(null=True, blank=True)
    performed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # State
    previous_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    
    # Context
    reason = models.TextField(blank=True, default="")
    request_id = models.CharField(max_length=64, blank=True, default="")
    
    class Meta:
        db_table = "core_permission_audit"
        ordering = ["-performed_at"]
        indexes = [
            models.Index(fields=["tenant_id", "performed_at"]),
            models.Index(fields=["membership_id"]),
        ]
    
    def __str__(self) -> str:
        return f"{self.action} {self.permission_code} @ {self.performed_at}"
