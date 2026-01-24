"""UI Hub URL patterns."""

from django.urls import path

from . import views

app_name = "ui_hub"

urlpatterns = [
    # Dashboard
    path("", views.dashboard_view, name="dashboard"),
    # Rules
    path("rules/", views.rules_list_view, name="rules_list"),
    # Violations
    path("violations/", views.violations_list_view, name="violations_list"),
    path("violations/<int:pk>/resolve/", views.violation_resolve_api, name="violation_resolve"),
    # Patterns
    path("patterns/", views.patterns_list_view, name="patterns_list"),
    path("patterns/<int:pk>/", views.pattern_detail_view, name="pattern_detail"),
    # API Endpoints
    path("api/validate-name/", views.validate_name_api, name="api_validate_name"),
    path("api/suggest-name/", views.suggest_name_api, name="api_suggest_name"),
    path("api/scaffold-view/", views.scaffold_view_api, name="api_scaffold_view"),
]
