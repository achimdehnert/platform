"""
URL configuration for Monitoring Dashboard.
"""

from django.urls import path

from apps.bfagent.views import monitoring_views

app_name = "monitoring"

urlpatterns = [
    # Main dashboard
    path("", monitoring_views.monitoring_dashboard, name="dashboard"),
    # API endpoints
    path("api/stats/", monitoring_views.monitoring_stats, name="stats_api"),
    # Alerts
    path("alerts/", monitoring_views.monitoring_alerts, name="alerts"),
    # App details
    path("app/<str:app_label>/", monitoring_views.monitoring_app_detail, name="app_detail"),
    # Healing events
    path("healing/", monitoring_views.monitoring_healing_events, name="healing_events"),
]
