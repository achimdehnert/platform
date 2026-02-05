"""
Governance App URLs
===================
Web UI for DDL Business Cases, Use Cases, and ADRs.
"""

from django.urls import path
from . import views

app_name = "governance"

urlpatterns = [
    # Dashboard
    path("", views.DashboardView.as_view(), name="dashboard"),
    
    # Business Cases
    path("business-cases/", views.BusinessCaseListView.as_view(), name="bc-list"),
    path("business-cases/create/", views.BusinessCaseCreateView.as_view(), name="bc-create"),
    path("business-cases/<str:code>/", views.BusinessCaseDetailView.as_view(), name="bc-detail"),
    
    # Use Cases
    path("use-cases/", views.UseCaseListView.as_view(), name="uc-list"),
    path("use-cases/<str:code>/", views.UseCaseDetailView.as_view(), name="uc-detail"),
    
    # HTMX Partials
    path("partials/bc-list/", views.bc_list_partial, name="bc-list-partial"),
    path("partials/bc-stats/", views.bc_stats_partial, name="bc-stats-partial"),
    path("partials/bc/<str:code>/status/", views.bc_status_partial, name="bc-status-partial"),
]
