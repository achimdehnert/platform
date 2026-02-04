"""
Weltenhub URL Configuration
===========================

Main URL routing for all apps and API endpoints.
"""

from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)


def health_check(request):
    """Simple health check endpoint for Docker/Traefik."""
    from django.http import JsonResponse
    return JsonResponse({"status": "healthy"})


urlpatterns = [
    # Health check (no auth required)
    path("health/", health_check, name="health-check"),

    # Public pages (Landing, Impressum, Datenschutz)
    path("", include("apps.public.urls")),

    # Admin
    path("admin/", admin.site.urls),

    # API Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui"
    ),

    # Governance (DDL Web UI)
    path("governance/", include("apps.governance.urls")),

    # API v1
    path("api/v1/tenants/", include("apps.tenants.urls")),
    path("api/v1/lookups/", include("apps.lookups.urls")),
    path("api/v1/worlds/", include("apps.worlds.urls")),
    path("api/v1/locations/", include("apps.locations.urls")),
    path("api/v1/characters/", include("apps.characters.urls")),
    path("api/v1/scenes/", include("apps.scenes.urls")),
    path("api/v1/stories/", include("apps.stories.urls")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
