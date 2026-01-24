"""
Feature Planning URLs - Control Center
Unified Feature Planning with Global Feature Registry integration

These URLs are included at /control-center/features/ to make feature planning
accessible with integration to the Global Feature Registry.
"""
from django.urls import path
from apps.control_center import views_feature_planning

app_name = 'features'

urlpatterns = [
    # Main Dashboard (Unified View)
    path(
        "",
        views_feature_planning.feature_planning_dashboard,
        name="dashboard",
    ),
    
    # Domain-Specific Views
    path(
        "domain/<str:domain_id>/",
        views_feature_planning.domain_features_view,
        name="domain-detail",
    ),
    
    # Cross-Domain Features
    path(
        "cross-domain/",
        views_feature_planning.cross_domain_features_view,
        name="cross-domain",
    ),
    
    # Migration Progress
    path(
        "migration/",
        views_feature_planning.migration_progress_view,
        name="migration-progress",
    ),

    # Feature Detail View
    path(
        "feature/<int:pk>/",
        views_feature_planning.feature_detail,
        name="detail",
    ),

    # CRUD Operations
    path(
        "feature/create/",
        views_feature_planning.feature_create,
        name="create",
    ),
    path(
        "feature/<int:pk>/edit/",
        views_feature_planning.feature_update,
        name="update",
    ),
    path(
        "feature/<int:pk>/delete/",
        views_feature_planning.feature_delete,
        name="delete",
    ),

    # Status Change
    path(
        "feature/<int:pk>/status/",
        views_feature_planning.feature_change_status,
        name="status-change",
    ),
]
