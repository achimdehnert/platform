"""
URL configuration for Workflow System
"""

from django.urls import path
from django.views.generic import TemplateView

app_name = "workflow_system"

urlpatterns = [
    path(
        "", TemplateView.as_view(template_name="workflow_system/dashboard.html"), name="dashboard"
    ),
]
