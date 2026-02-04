"""
Weltenhub Lookups API URLs
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    GenreViewSet,
    MoodViewSet,
    ConflictLevelViewSet,
    LocationTypeViewSet,
    SceneTypeViewSet,
    CharacterRoleViewSet,
    TransportTypeViewSet,
)

app_name = "lookups"

router = DefaultRouter()
router.register("genres", GenreViewSet, basename="genre")
router.register("moods", MoodViewSet, basename="mood")
router.register("conflict-levels", ConflictLevelViewSet, basename="conflict-level")
router.register("location-types", LocationTypeViewSet, basename="location-type")
router.register("scene-types", SceneTypeViewSet, basename="scene-type")
router.register("character-roles", CharacterRoleViewSet, basename="character-role")
router.register("transport-types", TransportTypeViewSet, basename="transport-type")

urlpatterns = [
    path("", include(router.urls)),
]
