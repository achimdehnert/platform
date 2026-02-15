"""Tenant-aware model manager.

Provides explicit tenant filtering via ``for_tenant(tenant_id)``.

Design decision (ADR-035): NO auto-filter on ``get_queryset()``.
Thread-local / contextvars auto-filtering is implicit and breaks in
Celery tasks, management commands, and Django admin. Explicit is safer.

Usage::

    class MyModel(models.Model):
        tenant_id = models.UUIDField(db_index=True)
        objects = TenantAwareManager()

    # In views / services:
    MyModel.objects.for_tenant(request.tenant_id)
"""

from __future__ import annotations

from uuid import UUID

from django.db import models


class TenantAwareManager(models.Manager):
    """Manager with explicit tenant-scoped queryset method."""

    def for_tenant(self, tenant_id: UUID) -> models.QuerySet:
        """Filter queryset by tenant_id.

        Args:
            tenant_id: The tenant UUID to filter by.

        Returns:
            QuerySet filtered to the given tenant.
        """
        return self.get_queryset().filter(tenant_id=tenant_id)
