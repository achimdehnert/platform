"""Module subscription and membership models.

Extends the base tenancy with per-module access control:

- ``ModuleSubscription``: which modules a tenant has licensed/activated.
- ``ModuleMembership``: which users have access to a specific module
  within a tenant, and with which role.

Design principles:
- ``module`` is a plain CharField (no FK) so apps can define their own
  module codes without touching this package.
- ``ModuleMembership.role`` is independent of ``Membership.role`` —
  a tenant admin can grant module-specific roles without changing the
  overall org membership.
- Both models carry a denormalized ``tenant_id`` for fast filtering
  (same pattern as ``Membership``).
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models

from .managers import TenantAwareManager


class ModuleSubscription(models.Model):
    """Records which modules a tenant has subscribed to.

    Attributes:
        organization: The owning organization.
        tenant_id: Denormalized from organization for query efficiency.
        module: Module code (e.g. ``"risk"``, ``"dsb"``, ``"worlds"``).
        status: Lifecycle state of the subscription.
        plan_code: Billing plan identifier (e.g. ``"free"``, ``"pro"``).
        trial_ends_at: When the trial period ends (None = no trial).
        activated_at: When the subscription became active.
        expires_at: Hard expiry date (None = no expiry).
    """

    class Status(models.TextChoices):
        TRIAL = "trial", "Trial"
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    organization = models.ForeignKey(
        "django_tenancy.Organization",
        on_delete=models.CASCADE,
        related_name="module_subscriptions",
    )
    tenant_id = models.UUIDField(db_index=True)
    module = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Module code, e.g. 'risk', 'dsb', 'worlds'.",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TRIAL,
    )
    plan_code = models.CharField(max_length=50, default="free")
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantAwareManager()

    class Meta:
        db_table = "tenancy_module_subscription"
        verbose_name = "Module Subscription"
        verbose_name_plural = "Module Subscriptions"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "module"],
                name="uq_module_subscription_tenant_module",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=["trial", "active", "suspended"],
                ),
                name="ck_module_subscription_status",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="idx_module_sub_tenant_status",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.organization} / {self.module} ({self.status})"

    @property
    def is_accessible(self) -> bool:
        """Whether this subscription currently grants access."""
        return self.status in (self.Status.TRIAL, self.Status.ACTIVE)


class ModuleMembership(models.Model):
    """Maps a user to a module within a tenant, with a module-specific role.

    A user must have a ``Membership`` in the organization AND a
    ``ModuleMembership`` for the specific module to access it.

    Attributes:
        tenant_id: Denormalized for query efficiency.
        user: The user being granted access.
        module: Module code (must match a ``ModuleSubscription.module``).
        role: The user's role within this module.
        granted_by: Who granted this membership (audit trail).
        granted_at: When the membership was created.
        expires_at: Optional expiry (None = permanent).
    """

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        MANAGER = "manager", "Manager"
        MEMBER = "member", "Member"
        VIEWER = "viewer", "Viewer"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="module_memberships",
    )
    module = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Module code, e.g. 'risk', 'dsb', 'worlds'.",
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.VIEWER,
    )
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    granted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    objects = TenantAwareManager()

    class Meta:
        db_table = "tenancy_module_membership"
        verbose_name = "Module Membership"
        verbose_name_plural = "Module Memberships"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "user", "module"],
                name="uq_module_membership_tenant_user_module",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    role__in=["admin", "manager", "member", "viewer"],
                ),
                name="ck_module_membership_role",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "module"],
                name="idx_module_mem_tenant_module",
            ),
            models.Index(
                fields=["tenant_id", "user"],
                name="idx_module_mem_tenant_user",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user} → {self.module} ({self.role}) @ {self.tenant_id}"
