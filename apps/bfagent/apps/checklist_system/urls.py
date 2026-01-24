"""
URL configuration for Checklist System
"""

from django.urls import path
from django.views.generic import TemplateView

app_name = "checklist_system"

urlpatterns = [
    path(
        "", TemplateView.as_view(template_name="checklist_system/dashboard.html"), name="dashboard"
    ),
]
