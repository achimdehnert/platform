"""
CAD-Hub Django URL Configuration
ADR-009: Database-driven, clean URL structure
"""

from django.urls import path

from cad_services.django.views.calculations import (
    DIN277CalculateView,
    DIN277ExportView,
    DIN277View,
)
from cad_services.django.views.dashboard import DashboardView
from cad_services.django.views.fire_safety import (
    EscapeRouteListView,
    FireCompartmentListView,
    FireRatedElementListView,
    FireSafetyDashboardView,
    fire_safety_stats_api,
)
from cad_services.django.views.models import (
    ModelDetailView,
    ModelListView,
    ModelUploadView,
)
from cad_services.django.views.projects import (
    ProjectCreateView,
    ProjectDeleteView,
    ProjectDetailView,
    ProjectEditView,
    ProjectListView,
)
from cad_services.django.views.rooms import (
    RoomDetailView,
    RoomEditView,
    RoomListView,
)
from cad_services.django.views.viewer import (
    floorplan_embed,
    floorplan_svg,
    floorplan_viewer,
)


app_name = "cadhub"

urlpatterns = [
    # Dashboard
    path("", DashboardView.as_view(), name="dashboard"),
    path("dashboard/stats/", DashboardView.as_view(), name="dashboard-stats"),
    # Projects
    path("projects/", ProjectListView.as_view(), name="project-list"),
    path("projects/create/", ProjectCreateView.as_view(), name="project-create"),
    path("projects/<int:pk>/", ProjectDetailView.as_view(), name="project-detail"),
    path("projects/<int:pk>/edit/", ProjectEditView.as_view(), name="project-edit"),
    path("projects/<int:pk>/delete/", ProjectDeleteView.as_view(), name="project-delete"),
    # Models
    path(
        "projects/<int:project_id>/models/",
        ModelListView.as_view(),
        name="model-list",
    ),
    path(
        "projects/<int:project_id>/models/upload/",
        ModelUploadView.as_view(),
        name="model-upload",
    ),
    path("models/<int:pk>/", ModelDetailView.as_view(), name="model-detail"),
    # Rooms (HTMX)
    path("rooms/", RoomListView.as_view(), name="room-list"),
    path("rooms/<int:pk>/", RoomDetailView.as_view(), name="room-detail"),
    path("rooms/<int:pk>/edit/", RoomEditView.as_view(), name="room-edit"),
    # DIN 277 Calculations (HTMX)
    path("calculations/din277/", DIN277View.as_view(), name="din277"),
    path("calculations/din277/calculate/", DIN277CalculateView.as_view(), name="din277-calculate"),
    path(
        "calculations/din277/export/<int:model_id>/",
        DIN277ExportView.as_view(),
        name="din277-export",
    ),
    # 2D Viewer (iframe-based)
    path("viewer/<int:model_id>/", floorplan_viewer, name="floorplan-viewer"),
    path("viewer/<int:model_id>/svg/", floorplan_svg, name="floorplan-svg"),
    path(
        "viewer/<int:model_id>/embed/",
        floorplan_embed,
        name="floorplan-embed",
    ),
    # Fire Safety
    path(
        "fire-safety/<int:model_id>/",
        FireSafetyDashboardView.as_view(),
        name="fire-safety",
    ),
    path(
        "fire-safety/<int:model_id>/compartments/",
        FireCompartmentListView.as_view(),
        name="fire-compartment-list",
    ),
    path(
        "fire-safety/<int:model_id>/elements/",
        FireRatedElementListView.as_view(),
        name="fire-element-list",
    ),
    path(
        "fire-safety/<int:model_id>/routes/",
        EscapeRouteListView.as_view(),
        name="escape-route-list",
    ),
    path(
        "api/fire-safety/<int:model_id>/",
        fire_safety_stats_api,
        name="fire-safety-api",
    ),
]
