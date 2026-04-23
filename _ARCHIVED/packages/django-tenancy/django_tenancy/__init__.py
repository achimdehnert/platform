"""Shared multi-tenancy infrastructure for the IIL platform.

Provides Organization, Membership, TenantManager (auto-filter),
TenantModelAdmin, TenantLifecycleMiddleware,
SubdomainTenantMiddleware, health endpoints, and contextvars-based
tenant context propagation.

Usage:
    # settings.py
    INSTALLED_APPS = [
        ...
        "django_tenancy",
    ]

    # MIDDLEWARE (order matters)
    MIDDLEWARE = [
        ...
        "django_tenancy.middleware.SubdomainTenantMiddleware",
        "django_tenancy.lifecycle.TenantLifecycleMiddleware",  # ADR-137
    ]
"""

__version__ = "0.2.0"
