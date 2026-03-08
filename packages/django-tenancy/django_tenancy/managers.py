"""
django_tenancy/managers.py

TenantManager and TenantQuerySet for all TenantModel subclasses.
Provides for_tenant() and active() convenience methods.
"""
from __future__ import annotations

from django.db import models


class TenantQuerySet(models.QuerySet):
    def for_tenant(self, tenant_id: int) -> "TenantQuerySet":
        """Filter to rows belonging to the given tenant."""
        return self.filter(tenant_id=tenant_id)

    def active(self) -> "TenantQuerySet":
        """Exclude soft-deleted rows."""
        return self.filter(deleted_at__isnull=True)


class TenantManager(models.Manager):
    def get_queryset(self) -> TenantQuerySet:
        return TenantQuerySet(self.model, using=self._db)

    def for_tenant(self, tenant_id: int) -> TenantQuerySet:
        return self.get_queryset().for_tenant(tenant_id)

    def active(self) -> TenantQuerySet:
        return self.get_queryset().active()
