"""
django_tenancy/models.py

Fixes:
  B-1: tenant_id = BigIntegerField (kein FK)
  H-1: BigAutoField PK + public_id UUID + deleted_at Soft-Delete
  C-5: gettext_lazy für alle Feld-Labels (ADR-110 Compliance)
  M-1: UniqueConstraint für subdomain (kein unique_together)
  ADR-110 Tenant-Integration: Organization.language Feld
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class OrganizationManager(models.Manager["Organization"]):
    """Excludes soft-deleted organizations by default."""

    def get_queryset(self) -> models.QuerySet["Organization"]:
        return super().get_queryset().filter(deleted_at__isnull=True)

    def including_deleted(self) -> models.QuerySet["Organization"]:
        return super().get_queryset()


class Organization(models.Model):
    """
    Tenant entity for all iil-Platform UI Hubs.

    Platform standards (ADR-109):
      ✅ BigAutoField PK
      ✅ public_id UUIDField
      ✅ Soft-Delete via deleted_at
      ✅ UniqueConstraint (not deprecated unique_together)
      ✅ gettext_lazy on all verbose_name fields (ADR-110)
      ✅ tenant_id on related models is BigIntegerField — NOT FK to this model
    """

    # Platform-standard PKs
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name=_("Public ID"),
    )

    # Identity
    name = models.CharField(
        max_length=200,
        verbose_name=_("Name"),
    )
    slug = models.SlugField(
        max_length=100,
        verbose_name=_("Slug"),
        help_text=_("URL-freundlicher Bezeichner, z.B. 'acme-corp'"),
    )
    subdomain = models.CharField(
        max_length=63,  # DNS label max length
        verbose_name=_("Subdomain"),
        help_text=_("z.B. 'acme' → acme.hub.domain.tld"),
        blank=True,
        default="",
    )

    # ADR-110: Tenant-Sprache
    language = models.CharField(
        max_length=8,
        choices=settings.LANGUAGES,
        default="de",
        verbose_name=_("Sprache"),
        help_text=_("Standardsprache für diese Organisation"),
    )

    # Status
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Aktiv"),
    )
    plan = models.CharField(
        max_length=50,
        default="free",
        verbose_name=_("Plan"),
    )

    # Soft-Delete (Platform-Standard)
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_("Gelöscht am"),
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Erstellt am"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Aktualisiert am"))

    objects = OrganizationManager()
    all_objects = models.Manager()  # Including soft-deleted

    class Meta:
        verbose_name = _("Organisation")
        verbose_name_plural = _("Organisationen")
        ordering = ["name"]
        constraints = [
            # Fix M-1: UniqueConstraint statt deprecated unique_together
            models.UniqueConstraint(
                fields=["slug"],
                condition=models.Q(deleted_at__isnull=True),
                name="unique_active_org_slug",
            ),
            models.UniqueConstraint(
                fields=["subdomain"],
                condition=models.Q(
                    deleted_at__isnull=True,
                    subdomain__gt="",  # exclude empty strings
                ),
                name="unique_active_org_subdomain",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Soft-delete this organization. Does NOT cascade — caller is responsible."""
        from django.utils import timezone
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at", "updated_at"])


# ---------------------------------------------------------------------------
# TenantManager Mixin — für alle User-Data-Models
# Fix C-1: Queryset-Filter im Manager, nicht in Views
# ---------------------------------------------------------------------------


class TenantQuerySet(models.QuerySet["_TenantModel"]):
    def for_tenant(self, tenant_id: int) -> "TenantQuerySet[_TenantModel]":
        return self.filter(tenant_id=tenant_id)

    def active(self) -> "TenantQuerySet[_TenantModel]":
        """Excludes soft-deleted records."""
        return self.filter(deleted_at__isnull=True)

    def for_tenant_active(self, tenant_id: int) -> "TenantQuerySet[_TenantModel]":
        return self.for_tenant(tenant_id).active()


class TenantManager(models.Manager["_TenantModel"]):
    def get_queryset(self) -> TenantQuerySet:
        return TenantQuerySet(self.model, using=self._db)

    def for_tenant(self, tenant_id: int) -> TenantQuerySet:
        return self.get_queryset().for_tenant(tenant_id)

    def for_tenant_active(self, tenant_id: int) -> TenantQuerySet:
        return self.get_queryset().for_tenant_active(tenant_id)


# Type variable for type-checking only
import typing
_TenantModel = typing.TypeVar("_TenantModel", bound=models.Model)


# ---------------------------------------------------------------------------
# TenantModel — Abstract Base für alle User-Data-Models in Hub-Repos
# ---------------------------------------------------------------------------


class TenantModel(models.Model):
    """
    Abstract base model for all user-data models in iil-Platform Hubs.

    Provides:
      - tenant_id = BigIntegerField(db_index=True)  [Platform-Standard: no FK]
      - public_id = UUIDField                        [Platform-Standard]
      - deleted_at = DateTimeField                   [Soft-Delete]
      - TenantManager with for_tenant() queryset

    Usage:
        class MyModel(TenantModel):
            name = models.CharField(max_length=200)
            # tenant_id, public_id, deleted_at automatically provided
    """

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name=_("Public ID"),
    )

    # Platform-Standard: BigIntegerField, NO ForeignKey to Organization
    # Rationale: schema-based isolation, cross-DB compatibility, iil-testkit compatibility
    tenant_id = models.BigIntegerField(
        db_index=True,
        verbose_name=_("Tenant ID"),
    )

    # Soft-Delete
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_("Gelöscht am"),
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Erstellt am"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Aktualisiert am"))

    objects = TenantManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def soft_delete(self) -> None:
        from django.utils import timezone
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at", "updated_at"])
