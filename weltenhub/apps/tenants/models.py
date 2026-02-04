"""
Weltenhub Tenant Models
=======================

Multi-tenant support for Weltenhub.
Each tenant has isolated data and user permissions.

Tables:
    - wh_tenant: Tenant (organization/customer)
    - wh_tenant_user: User-Tenant membership with roles
    - wh_permission: Available permissions
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Tenant(models.Model):
    """
    A tenant (organization/customer) in Weltenhub.

    All data is isolated per tenant using row-level filtering.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    name = models.CharField(
        max_length=200,
        help_text="Display name of the tenant"
    )
    slug = models.SlugField(
        max_length=200,
        unique=True,
        help_text="URL-safe identifier"
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this tenant is active"
    )
    settings = models.JSONField(
        default=dict,
        blank=True,
        help_text="Tenant-specific settings as JSON"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "wh_tenant"
        verbose_name = "Tenant"
        verbose_name_plural = "Tenants"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Permission(models.Model):
    """
    Available permissions in Weltenhub.

    Database-driven permissions instead of hardcoded strings.
    """

    code = models.CharField(
        max_length=100,
        unique=True,
        help_text="Permission code (e.g., 'world.create')"
    )
    name = models.CharField(
        max_length=200,
        help_text="Human-readable name"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of what this permission allows"
    )
    category = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Permission category (e.g., 'world', 'scene')"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "wh_permission"
        verbose_name = "Permission"
        verbose_name_plural = "Permissions"
        ordering = ["category", "code"]

    def __str__(self):
        return f"{self.category}.{self.code}"


class TenantUser(models.Model):
    """
    User membership in a tenant with role and permissions.

    A user can belong to multiple tenants with different roles.
    Uses database-driven lookup for roles (Database-First principle).
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="users"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tenant_memberships"
    )
    role = models.ForeignKey(
        "lookups.TenantRole",
        on_delete=models.PROTECT,
        related_name="tenant_users",
        help_text="User's role in this tenant (from lookup table)"
    )
    permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name="tenant_users",
        help_text="Additional permissions beyond role"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this membership is active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "wh_tenant_user"
        verbose_name = "Tenant User"
        verbose_name_plural = "Tenant Users"
        unique_together = [["tenant", "user"]]
        ordering = ["tenant", "role", "user"]

    def __str__(self):
        return f"{self.user} @ {self.tenant} ({self.role.name})"

    def has_permission(self, permission_code: str) -> bool:
        """Check if user has a specific permission."""
        # High permission levels (owner/admin) have all permissions
        if self.role.permission_level >= 80:  # Owner/Admin level
            return True
        if self.role.can_manage_users or self.role.can_manage_settings:
            return True
        return self.permissions.filter(code=permission_code).exists()
