"""Tenant-aware model managers.

Provides two managers:

1. ``TenantManager`` (ADR-137): Default manager with context-based auto-filter.
   In request context (middleware set tenant_id) → automatic filtering.
   Without context (Celery, shell, tests) → no filter (safe fallback).
   Explicit bypass via ``.unscoped()`` for admin/reports.

2. ``TenantAwareManager`` (ADR-035, legacy): Explicit-only filtering via
   ``for_tenant()``. Kept for backward compatibility.

Usage::

    class MyModel(TenantModel):
        # TenantManager is set automatically via TenantModel
        pass

    # In request context (auto-filtered):
    MyModel.objects.all()              # → filtered by current tenant
    MyModel.objects.filter(active=True) # → also filtered

    # Explicit (Celery, management commands):
    MyModel.objects.for_tenant(tid)

    # Admin / cross-tenant reports:
    MyModel.objects.unscoped()
"""

from __future__ import annotations

import logging
from typing import Union
from uuid import UUID

from django.db import models

logger = logging.getLogger(__name__)


class TenantQuerySet(models.QuerySet):
    """QuerySet with tenant-specific convenience methods."""

    def for_tenant(self, tenant_id: Union[UUID, int]) -> "TenantQuerySet":
        """Explicit tenant filter (Celery, management commands).

        Args:
            tenant_id: The tenant UUID or BigInt to filter by.

        Returns:
            QuerySet filtered to the given tenant.
        """
        return self.filter(tenant_id=tenant_id)

    def unscoped(self) -> "TenantQuerySet":
        """Return a new queryset without the auto-filter.

        Use for admin views, cross-tenant reports, migrations.
        This creates a fresh queryset from the model to bypass any
        auto-filtering that was applied in get_queryset().
        """
        return self.model._default_manager._unscoped_queryset()


class TenantManager(models.Manager):
    """Default manager with context-based auto-filter (ADR-137).

    In request context (middleware has set tenant_id):
        MyModel.objects.all()  → automatically filtered
    Without context (Celery, shell, tests):
        MyModel.objects.all()  → unfiltered (safe fallback)
        MyModel.objects.for_tenant(uuid)  → explicit filter
    Admin / reports:
        MyModel.objects.unscoped()  → explicitly unfiltered
    """

    def get_queryset(self) -> TenantQuerySet:
        """Return queryset, auto-filtered if tenant context is set."""
        qs = TenantQuerySet(self.model, using=self._db)
        from .context import get_context

        ctx = get_context()
        if ctx.tenant_id is not None:
            return qs.filter(tenant_id=ctx.tenant_id)
        return qs

    def for_tenant(self, tenant_id: Union[UUID, int]) -> TenantQuerySet:
        """Explicit tenant filter, bypasses auto-filter."""
        return self._unscoped_queryset().filter(tenant_id=tenant_id)

    def unscoped(self) -> TenantQuerySet:
        """Bypass auto-filter — for admin, migrations, cross-tenant reports."""
        return self._unscoped_queryset()

    def _unscoped_queryset(self) -> TenantQuerySet:
        """Create a raw TenantQuerySet without any auto-filtering."""
        return TenantQuerySet(self.model, using=self._db)


class TenantAwareManager(models.Manager):
    """Legacy manager with explicit tenant-scoped queryset method (ADR-035).

    Kept for backward compatibility. New code should use ``TenantManager``.
    """

    def for_tenant(self, tenant_id: Union[UUID, int]) -> models.QuerySet:
        """Filter queryset by tenant_id.

        Args:
            tenant_id: The tenant UUID or BigInt to filter by.

        Returns:
            QuerySet filtered to the given tenant.
        """
        return self.get_queryset().filter(tenant_id=tenant_id)
