"""
django_tenancy/models.py

Organization (Tenant entity), Membership, and TenantModel (abstract base).

Platform standards (ADR-109):
  - BigAutoField PK
  - public_id UUIDField
  - tenant_id = BigIntegerField (NOT FK — ADR-109 Fix B-1)
  - deleted_at soft-delete
  - TenantManager with for_tenant() + active()
"""
from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from .managers import TenantManager


class Organization(models.Model):
    """
    Tenant entity. One Organization = one tenant.

    Subdomain routing: <slug>.hub.domain.tld
    Language: overrides platform default per tenant (ADR-110).
    """

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name=_("Public ID"),
    )
    name = models.CharField(max_length=200, verbose_name=_("Name"))
    slug = models.SlugField(
        max_length=100,
        unique=True,
        verbose_name=_("Slug"),
        help_text=_("Used as subdomain identifier"),
    )
    subdomain = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Subdomain override"),
        help_text=_("Leave blank to use slug"),
    )
    language = models.CharField(
        max_length=8,
        default="de",
        verbose_name=_("Language"),
        help_text=_("Tenant-default language (ADR-110)"),
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    deleted_at = models.DateTimeField(
        null=True, blank=True, db_index=True, verbose_name=_("Deleted At")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    objects = TenantManager()

    class Meta:
        app_label = "django_tenancy"
        verbose_name = _("Organization")
        verbose_name_plural = _("Organizations")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["slug"],
                condition=models.Q(deleted_at__isnull=True),
                name="unique_active_org_slug",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def effective_subdomain(self) -> str:
        return self.subdomain or self.slug


class Membership(models.Model):
    """
    Links a User to an Organization with a role.

    One user can have at most one Membership per Organization.
    """

    class Role(models.TextChoices):
        ADMIN = "admin", _("Admin")
        MANAGER = "manager", _("Manager")
        MEMBER = "member", _("Member")
        VIEWER = "viewer", _("Viewer")

    id = models.BigAutoField(primary_key=True)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name=_("Organization"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name=_("User"),
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
        verbose_name=_("Role"),
    )
    tenant_id = models.BigIntegerField(
        db_index=True,
        verbose_name=_("Tenant ID"),
        help_text=_("Denormalized from organization.id for fast filtering"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        app_label = "django_tenancy"
        verbose_name = _("Membership")
        verbose_name_plural = _("Memberships")
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user"],
                name="unique_membership_org_user",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant_id", "user"], name="idx_membership_tenant_user"),
        ]

    def __str__(self) -> str:
        return f"{self.user} @ {self.organization} ({self.role})"


class TenantModel(models.Model):
    """
    Abstract base class for all tenant-scoped models.

    Fix B-1 (ADR-109): tenant_id is BigIntegerField, NOT ForeignKey.
    Rationale: FK would enforce ON DELETE CASCADE/RESTRICT, breaking
    Celery tasks and cross-DB scenarios.
    """

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name=_("Public ID"),
    )
    # NOT a FK — intentional (ADR-109 B-1)
    tenant_id = models.BigIntegerField(
        db_index=True,
        verbose_name=_("Tenant ID"),
    )
    deleted_at = models.DateTimeField(
        null=True, blank=True, db_index=True, verbose_name=_("Deleted At")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    objects = TenantManager()

    class Meta:
        abstract = True
