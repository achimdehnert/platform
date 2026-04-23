"""
URL patterns for opt-in readiness endpoint.

Include in repo's root urls.py:

    path("readyz/", include("platform_context.health.urls")),

Serves:
    GET  /readyz/   → 200 if DB + all checks pass, 503 otherwise
    HEAD /readyz/   → same status, no body
"""
from __future__ import annotations

from django.urls import path

from platform_context.health.views import ReadinessView

app_name = "platform_context_health"

urlpatterns = [
    path("", ReadinessView.as_view(), name="readyz"),
]
