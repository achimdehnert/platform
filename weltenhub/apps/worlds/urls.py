"""
Weltenhub Worlds API URLs
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import WorldViewSet, WorldRuleViewSet

app_name = "worlds"

router = DefaultRouter()
router.register("worlds", WorldViewSet, basename="world")
router.register("rules", WorldRuleViewSet, basename="world-rule")

urlpatterns = [
    path("", include(router.urls)),
]
