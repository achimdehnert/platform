"""
hub_template/config/urls.py

Fix C-6: prefix_default_language=False mit expliziter Redirect-Strategie.
Fix B-4: i18n/ URL für set_language view.

ACHTUNG: prefix_default_language=False ist ein Breaking Change bei bestehenden Hubs.
Migrations-Strategie:
  1. Erst `prefix_default_language=True` deployen (alle Sprachen bekommen Prefix)
  2. 301 Redirects von alten URLs auf neue mit /de/ Prefix
  3. Nach Ablauf der Cache-TTL: prefix_default_language=False aktivieren

Für neue Hubs: direkt prefix_default_language=False verwenden.
"""

from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    # i18n: set_language view (POST → ändert Sprachcookie)
    # Form action in language_switcher.html: {% url 'set_language' %}
    path("i18n/", include("django.conf.urls.i18n")),

    # Admin (außerhalb i18n_patterns — Admin hat eigene i18n)
    path("admin/", admin.site.urls),

    # Health check (außerhalb i18n — Deployment Agent braucht /health/)
    path("health/", include("django_tenancy.urls.health")),

    # Onboarding (außerhalb i18n — kein Tenant nötig)
    path("onboarding/", include("apps.onboarding.urls")),
] + i18n_patterns(
    path("", include("apps.core.urls")),
    # Alle Hub-App-URLs hier
    # path("dashboard/", include("apps.dashboard.urls")),

    # Fix C-6: prefix_default_language=False
    # - /de/dashboard/ und /dashboard/ sind identisch (default language = de)
    # - /en/dashboard/ für Englisch
    # Für bestehende Hubs: erst True, dann nach Redirect-Wartezeit auf False wechseln
    prefix_default_language=False,
)

if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
