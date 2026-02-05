"""
URL configuration for PPTX-Hub Django app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from pptx_hub.django.api import views

router = DefaultRouter()
router.register("presentations", views.PresentationViewSet, basename="presentation")
router.register("jobs", views.JobViewSet, basename="job")

app_name = "pptx_hub"

urlpatterns = [
    # REST API
    path("", include(router.urls)),
    
    # OpenAPI Schema (if drf-spectacular is installed)
    # path("schema/", SpectacularAPIView.as_view(), name="schema"),
    # path("docs/", SpectacularSwaggerView.as_view(), name="swagger"),
]
