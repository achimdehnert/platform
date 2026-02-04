"""
Weltenhub Scenes API URLs
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    SceneTemplateViewSet,
    SceneViewSet,
    SceneBeatViewSet,
    SceneConnectionViewSet,
)

app_name = "scenes"

router = DefaultRouter()
router.register("templates", SceneTemplateViewSet, basename="scene-template")
router.register("scenes", SceneViewSet, basename="scene")
router.register("beats", SceneBeatViewSet, basename="scene-beat")
router.register("connections", SceneConnectionViewSet, basename="connection")

urlpatterns = [
    path("", include(router.urls)),
]
