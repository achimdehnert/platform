"""Concrete tenancy models: Organization and Membership.

Based on risk-hub's production-proven implementation (ADR-003).
Apps install ``django_tenancy`` in INSTALLED_APPS and get these
tables via ``manage.py migrate django_tenancy``.

CRITICAL (Global Rules §3.3):
    Organization.id != Organization.tenant_id
    Always use org.tenant_id for data isolation, never org.id.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class Organization(models.Model):
    """Tenant organization with lifecycle management.

    Attributes:
        id: Internal primary key (UUID). Do NOT use for tenant filtering.
        tenant_id: Public tenant identifier. Use THIS for data isolation.
        slug: Subdomain slug (e.g. ``acme`` for ``acme.example.com``).
        status: Lifecycle state (trial → active → suspended → deleted).
        plan_code: Billing plan identifier.
    """

    class Status(models.TextChoices):
        TRIAL = "trial", "Trial"
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        DELETED = "deleted", "Deleted"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(
        unique=True, default=uuid.uuid4, editable=False, db_index=True,
    )
    slug = models.SlugField(max_length=63, unique=True)
    name = models.CharField(max_length=200)

    # Lifecycle
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TRIAL,
    )
    plan_code = models.CharField(max_length=50, default="free")
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    suspended_at = models.DateTimeField(null=True, blank=True)
    suspended_reason = models.TextField(blank=True, default="")
    deleted_at = models.DateTimeField(null=True, blank=True)

    # Tenant-specific configuration (not for structured data)
    settings = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tenancy_organization"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    status__in=["trial", "active", "suspended", "deleted"],
                ),
                name="org_status_chk",
            ),
        ]
        indexes = [
            models.Index(fields=["status"], name="idx_org_status"),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def is_active(self) -> bool:
        """Whether the organization can serve requests."""
        return self.status in (self.Status.TRIAL, self.Status.ACTIVE)


class Membership(models.Model):
    """Maps a user to an organization with a role.

    Attributes:
        tenant_id: Denormalized from organization for query efficiency.
        role: Permission level within the organization.
    """

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"
        VIEWER = "viewer", "Viewer"
        EXTERNAL = "external", "External"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.MEMBER,
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    invited_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tenancy_membership"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "user"],
                name="membership_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    role__in=["owner", "admin", "member", "viewer", "external"],
                ),
                name="membership_role_chk",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "role"],
                name="idx_membership_tenant_role",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user} -> {self.organization} ({self.role})"
