"""Template context processor for tenant context.

Adds ``tenant``, ``tenant_id``, and ``tenant_slug`` to every template
context so templates can access the current tenant without explicit
view logic.

Usage in settings.py::

    TEMPLATES = [{
        "OPTIONS": {
            "context_processors": [
                ...
                "django_tenancy.context_processors.tenant",
            ],
        },
    }]

Then in templates::

    {{ tenant.name }}
    {{ tenant_slug }}
"""

from __future__ import annotations

from django.http import HttpRequest


def tenant(request: HttpRequest) -> dict:
    """Add tenant context to template rendering."""
    return {
        "tenant": getattr(request, "tenant", None),
        "tenant_id": getattr(request, "tenant_id", None),
        "tenant_slug": getattr(request, "tenant_slug", None),
    }
