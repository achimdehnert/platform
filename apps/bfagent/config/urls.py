"""
URL configuration for BF Agent Django project
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.generic import RedirectView

from apps.bfagent.views.auth_views import custom_logout, register
from apps.core.views import health_check, liveness_check, readiness_check

urlpatterns = [
    path("admin/", admin.site.urls),
    # Authentication URLs
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path("logout/", custom_logout, name="logout"),
    path("register/", register, name="register"),
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(template_name="registration/password_reset.html"),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "password-reset-confirm/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    path(
        "password-reset-complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    # Health Check Endpoints (MUST be before catch-all patterns)
    path("health/", health_check, name="health_check"),
    path("readiness/", readiness_check, name="readiness"),
    path("liveness/", liveness_check, name="liveness"),
    # URL Redirects (old -> new structure)
    path("projects/", RedirectView.as_view(url="/bookwriting/books/", permanent=True)),
    path("chapters/", RedirectView.as_view(url="/bookwriting/chapters/", permanent=True)),
    path("characters/", RedirectView.as_view(url="/bookwriting/characters/", permanent=True)),
    # App URLs - SPECIFIC PATHS FIRST (before catch-all patterns)
    # UI Hub - HTMX Guardrails (MUST be before hub catch-all)
    path("ui-hub/", include("apps.ui_hub.urls")),  # UI Hub
    path("monitoring/", include("apps.bfagent.urls_monitoring")),  # Monitoring Dashboard
    path("bookwriting/", include("apps.bfagent.urls")),  # Book Writing Studio
    path("api/workflow/", include("apps.bfagent.api.urls")),  # Workflow Builder API
    path("api/mcp/", include("apps.api.urls_mcp")),  # MCP Orchestration API
    path("api/domains/", include("apps.api.urls_domains")),  # Domains API
    path("control-center/", include("apps.control_center.urls")),
    path("expert-hub/", include(("apps.expert_hub.urls", "expert_hub"))),  # Expert Hub
    path("writing-hub/", include(("apps.writing_hub.urls", "writing_hub"))),  # Writing Hub
    path("research/", include(("apps.research.urls", "research"))),  # Research Hub
    path("cad-hub/", include(("apps.cad_hub.urls", "cad_hub"))),  # CAD Hub (IFC Dashboard)
    path("dlm-hub/", include(("apps.dlm_hub.urls", "dlm_hub"))),  # DLM Hub
    path("media-hub/", include(("apps.media_hub.urls", "media_hub"))),  # Media Hub
    path("workflow/", include(("apps.workflow_system.urls", "workflow_system"))),  # Workflow System
    path(
        "checklist/", include(("apps.checklist_system.urls", "checklist_system"))
    ),  # Checklist System
    path("genagent/", include("apps.genagent.urls")),  # Book Writing Studio 2.0 (Beta)
    path("graph/", include(("apps.graph_core.urls", "graph_core"))),  # Graph Core - Workflow Orchestration
    path("medtrans/", include("apps.medtrans.urls")),  # Medical Translation
    path("sphinx-export/", include(("apps.sphinx_export.urls", "sphinx_export"))),  # Sphinx Export
    path(
        "pptx-studio/", include(("apps.presentation_studio.urls", "presentation_studio"))
    ),  # PPTX Studio
    path("reader/", include("apps.bfagent.urls_book_reader")),  # Book Reader
    path("mcp-hub/", include(("apps.mcp_hub.urls", "mcp_hub"))),  # MCP Hub - Server Management
    # Feature Planning (accessible from all domains)
    path("features/", include("apps.control_center.urls_features")),
    # Dynamic Hub (MUST be last: contains catch-all patterns like /<domain-slug>/)
    path("", include("apps.hub.urls")),
]

# Serve static files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # Django Debug Toolbar URLs
    import importlib.util

    if importlib.util.find_spec("debug_toolbar"):
        urlpatterns = [
            path("__debug__/", include("debug_toolbar.urls")),
        ] + urlpatterns
