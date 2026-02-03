"""
TenantMembership model for user-tenant relationships.

Features:
- Role-based access (owner, admin, member, viewer)
- Invitation workflow with expiration
- Permission version for cache invalidation
"""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import TYPE_CHECKING

from django.db import models
from django.utils import timezone

if TYPE_CHECKING:
    from django.db.models import QuerySet


class TenantRole(models.TextChoices):
    """
    Role hierarchy.
    
    | Role   | Level | Description                    |
    |--------|-------|--------------------------------|
    | owner  | 100   | Full access, can delete tenant |
    | admin  | 75    | Almost all, except tenant delete|
    | member | 50    | Work (CRUD), no delete         |
    | viewer | 25    | Read-only                      |
    """
    OWNER = "owner", "Owner"
    ADMIN = "admin", "Admin"
    MEMBER = "member", "Member"
    VIEWER = "viewer", "Viewer"


class MembershipStatus(models.TextChoices):
    """Membership status for invitation workflow."""
    PENDING = "pending", "Pending"
    ACTIVE = "active", "Active"
    DEACTIVATED = "deactivated", "Deactivated"


class TenantMembershipQuerySet(models.QuerySet["TenantMembership"]):
    """Custom QuerySet for membership queries."""
    
    def active(self) -> QuerySet[TenantMembership]:
        """Only active memberships."""
        return self.filter(status=MembershipStatus.ACTIVE)
    
    def for_tenant(self, tenant_id: uuid.UUID) -> QuerySet[TenantMembership]:
        """Memberships for a specific tenant."""
        return self.filter(tenant_id=tenant_id)
    
    def for_user(self, user_id: uuid.UUID) -> QuerySet[TenantMembership]:
        """Memberships for a specific user."""
        return self.filter(user_id=user_id)
    
    def pending_expired(self) -> QuerySet[TenantMembership]:
        """Pending invitations that have expired."""
        return self.filter(
            status=MembershipStatus.PENDING,
            invitation_expires_at__lt=timezone.now(),
        )


class TenantMembershipManager(models.Manager["TenantMembership"]):
    """Custom manager with QuerySet methods."""
    
    def get_queryset(self) -> TenantMembershipQuerySet:
        return TenantMembershipQuerySet(self.model, using=self._db)
    
    def active(self) -> QuerySet[TenantMembership]:
        return self.get_queryset().active()
    
    def get_membership(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> TenantMembership | None:
        """Get active membership for tenant+user."""
        return self.active().filter(
            tenant_id=tenant_id,
            user_id=user_id,
        ).first()
    
    def user_has_access(self, tenant_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Check if user has any active membership."""
        return self.active().filter(
            tenant_id=tenant_id,
            user_id=user_id,
        ).exists()


class TenantMembership(models.Model):
    """
    User-Tenant relationship with role.
    
    Features:
    - One role per user per tenant
    - Invitation workflow
    - Permission version for cache invalidation
    
    Example:
        membership = TenantMembership.objects.create(
            tenant=tenant,
            user=user,
            role=TenantRole.MEMBER,
        )
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    
    # ══════════════════════════════════════════════════════════════════════════
    # RELATIONSHIPS
    # ══════════════════════════════════════════════════════════════════════════
    
    tenant = models.ForeignKey(
        "bfagent_core.Tenant",
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    
    user = models.ForeignKey(
        "bfagent_core.CoreUser",
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    
    # ══════════════════════════════════════════════════════════════════════════
    # ROLE & STATUS
    # ══════════════════════════════════════════════════════════════════════════
    
    role = models.CharField(
        max_length=20,
        choices=TenantRole.choices,
        default=TenantRole.MEMBER,
        db_index=True,
    )
    
    status = models.CharField(
        max_length=20,
        choices=MembershipStatus.choices,
        default=MembershipStatus.ACTIVE,
        db_index=True,
    )
    
    # ══════════════════════════════════════════════════════════════════════════
    # INVITATION
    # ══════════════════════════════════════════════════════════════════════════
    
    invited_by = models.ForeignKey(
        "bfagent_core.CoreUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invitations_sent",
    )
    
    invited_at = models.DateTimeField(null=True, blank=True)
    invitation_expires_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    
    # ══════════════════════════════════════════════════════════════════════════
    # CACHE INVALIDATION
    # ══════════════════════════════════════════════════════════════════════════
    
    permission_version = models.IntegerField(
        default=1,
        help_text="Incremented on role/permission changes for cache invalidation",
    )
    
    # ══════════════════════════════════════════════════════════════════════════
    # METADATA
    # ══════════════════════════════════════════════════════════════════════════
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = TenantMembershipManager()
    
    class Meta:
        db_table = "core_tenant_membership"
        verbose_name = "Tenant Membership"
        verbose_name_plural = "Tenant Memberships"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "user"],
                name="membership_unique",
            ),
            models.CheckConstraint(
                check=models.Q(role__in=["owner", "admin", "member", "viewer"]),
                name="membership_role_chk",
            ),
            models.CheckConstraint(
                check=models.Q(status__in=["pending", "active", "deactivated"]),
                name="membership_status_chk",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "user"]),
            models.Index(fields=["user", "status"]),
            models.Index(
                fields=["invitation_expires_at"],
                condition=models.Q(status="pending"),
                name="membership_pending_idx",
            ),
        ]
    
    def __str__(self) -> str:
        return f"{self.user} @ {self.tenant} ({self.role})"
    
    # ══════════════════════════════════════════════════════════════════════════
    # PROPERTIES
    # ══════════════════════════════════════════════════════════════════════════
    
    @property
    def is_owner(self) -> bool:
        return self.role == TenantRole.OWNER
    
    @property
    def is_admin(self) -> bool:
        return self.role in (TenantRole.OWNER, TenantRole.ADMIN)
    
    @property
    def is_pending(self) -> bool:
        return self.status == MembershipStatus.PENDING
    
    @property
    def is_invitation_expired(self) -> bool:
        if not self.is_pending or not self.invitation_expires_at:
            return False
        return timezone.now() > self.invitation_expires_at
    
    # ══════════════════════════════════════════════════════════════════════════
    # METHODS
    # ══════════════════════════════════════════════════════════════════════════
    
    def accept_invitation(self) -> None:
        """Accept pending invitation."""
        if self.status != MembershipStatus.PENDING:
            raise ValueError("Can only accept pending invitations")
        
        if self.is_invitation_expired:
            raise ValueError("Invitation has expired")
        
        self.status = MembershipStatus.ACTIVE
        self.accepted_at = timezone.now()
        self.save(update_fields=["status", "accepted_at", "updated_at"])
    
    def deactivate(self) -> None:
        """Deactivate membership (soft removal)."""
        self.status = MembershipStatus.DEACTIVATED
        self.save(update_fields=["status", "updated_at"])
    
    def change_role(self, new_role: str) -> None:
        """Change role and increment permission_version."""
        if new_role not in TenantRole.values:
            raise ValueError(f"Invalid role: {new_role}")
        
        self.role = new_role
        self.permission_version += 1
        self.save(update_fields=["role", "permission_version", "updated_at"])
    
    def increment_permission_version(self) -> None:
        """Manually increment version (e.g., after override change)."""
        self.permission_version += 1
        self.save(update_fields=["permission_version", "updated_at"])
    
    @classmethod
    def create_invitation(
        cls,
        tenant,
        user,
        role: str,
        invited_by,
        expires_in_days: int = 7,
    ) -> "TenantMembership":
        """Create a pending invitation."""
        return cls.objects.create(
            tenant=tenant,
            user=user,
            role=role,
            status=MembershipStatus.PENDING,
            invited_by=invited_by,
            invited_at=timezone.now(),
            invitation_expires_at=timezone.now() + timedelta(days=expires_in_days),
        )
