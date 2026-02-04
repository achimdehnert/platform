"""
Weltenhub Characters API URLs
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CharacterViewSet,
    CharacterArcViewSet,
    CharacterRelationshipViewSet,
)

app_name = "characters"

router = DefaultRouter()
router.register("characters", CharacterViewSet, basename="character")
router.register("arcs", CharacterArcViewSet, basename="character-arc")
router.register(
    "relationships",
    CharacterRelationshipViewSet,
    basename="character-relationship"
)

urlpatterns = [
    path("", include(router.urls)),
]
