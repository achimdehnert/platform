"""
django_tenancy/context_processors.py

Makes request.tenant available in all templates.

Add to TEMPLATES[0]["OPTIONS"]["context_processors"]:
    "django_tenancy.context_processors.tenant"
"""
from __future__ import annotations

from django.http import HttpRequest


def tenant(request: HttpRequest) -> dict:
    """Expose request.tenant to template context."""
    return {
        "tenant": getattr(request, "tenant", None),
        "tenant_id": getattr(request, "tenant_id", 0),
    }
