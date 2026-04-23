"""Tenant-aware Django Admin base classes (ADR-137).

TenantModelAdmin bypasses the auto-filter from TenantManager so that
staff users can see all tenants in the Django Admin.

Usage::

    from django.contrib import admin
    from django_tenancy.admin import TenantModelAdmin

    @admin.register(MyModel)
    class MyModelAdmin(TenantModelAdmin):
        list_display = ["name", "tenant_id", ...]
"""

from __future__ import annotations

from django.contrib import admin


class TenantModelAdmin(admin.ModelAdmin):
    """Admin base class that bypasses TenantManager auto-filter.

    All admin registrations for TenantModel subclasses should inherit
    from this class to ensure staff users see data across all tenants.
    """

    def get_queryset(self, request):
        """Return unscoped queryset (all tenants visible)."""
        qs = self.model._default_manager
        if hasattr(qs, "unscoped"):
            return qs.unscoped()
        return qs.get_queryset()
