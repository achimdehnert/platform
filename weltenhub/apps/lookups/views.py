"""
Weltenhub Lookups API Views
===========================

Read-only ViewSets for all lookup models.
Lookups are public and don't require tenant filtering.
"""

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    Genre,
    Mood,
    ConflictLevel,
    LocationType,
    SceneType,
    CharacterRole,
    TransportType,
)
from .serializers import (
    GenreSerializer,
    MoodSerializer,
    ConflictLevelSerializer,
    LocationTypeSerializer,
    SceneTypeSerializer,
    CharacterRoleSerializer,
    TransportTypeSerializer,
)


class BaseLookupViewSet(viewsets.ReadOnlyModelViewSet):
    """Base ViewSet for lookup tables (read-only)."""

    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["is_active"]

    def get_queryset(self):
        """Filter to active items by default."""
        qs = super().get_queryset()
        if self.request.query_params.get("include_inactive") != "true":
            qs = qs.filter(is_active=True)
        return qs


class GenreViewSet(BaseLookupViewSet):
    """API endpoint for genres."""

    queryset = Genre.objects.all()
    serializer_class = GenreSerializer


class MoodViewSet(BaseLookupViewSet):
    """API endpoint for moods."""

    queryset = Mood.objects.all()
    serializer_class = MoodSerializer


class ConflictLevelViewSet(BaseLookupViewSet):
    """API endpoint for conflict levels."""

    queryset = ConflictLevel.objects.all()
    serializer_class = ConflictLevelSerializer


class LocationTypeViewSet(BaseLookupViewSet):
    """API endpoint for location types."""

    queryset = LocationType.objects.all()
    serializer_class = LocationTypeSerializer


class SceneTypeViewSet(BaseLookupViewSet):
    """API endpoint for scene types."""

    queryset = SceneType.objects.all()
    serializer_class = SceneTypeSerializer


class CharacterRoleViewSet(BaseLookupViewSet):
    """API endpoint for character roles."""

    queryset = CharacterRole.objects.all()
    serializer_class = CharacterRoleSerializer


class TransportTypeViewSet(BaseLookupViewSet):
    """API endpoint for transport types."""

    queryset = TransportType.objects.all()
    serializer_class = TransportTypeSerializer
