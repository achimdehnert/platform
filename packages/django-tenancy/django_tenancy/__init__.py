"""Shared multi-tenancy infrastructure for the BF Agent platform.

Provides Organization, Membership, TenantAwareManager,
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
    ]
"""

__version__ = "0.1.0"
