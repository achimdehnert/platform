from django.urls import path

from . import views
from . import views_domain_dashboards

app_name = "hub"

urlpatterns = [
    # Old central dashboard (will be replaced by domain tiles)
    path("old-dashboard/", views.central_dashboard, name="dashboard-old"),
    
    # NEW: Home with all domain tiles
    path("", views_domain_dashboards.home_dashboard, name="home"),
    
    # Generic domain dashboards (/<domain-slug>/)
    path("<slug:domain_slug>/", views_domain_dashboards.generic_domain_dashboard, name="domain-dashboard"),
    
    # Landing page
    path("welcome/", views.landing_page, name="landing"),
]
