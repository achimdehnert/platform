"""
Weltenhub Scenes API Views
"""

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import SceneTemplate, Scene, SceneBeat, SceneConnection
from .serializers import (
    SceneTemplateSerializer,
    SceneListSerializer,
    SceneDetailSerializer,
    SceneBeatSerializer,
    SceneConnectionSerializer,
)


class SceneTemplateViewSet(viewsets.ModelViewSet):
    """API endpoint for Scene Templates."""

    queryset = SceneTemplate.objects.all()
    serializer_class = SceneTemplateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["scene_type", "is_active"]
    search_fields = ["name", "description"]


class SceneViewSet(viewsets.ModelViewSet):
    """API endpoint for Scenes."""

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["story", "chapter", "scene_type", "status"]
    search_fields = ["title", "summary"]
    ordering_fields = ["order", "created_at"]
    ordering = ["chapter", "order"]

    def get_queryset(self):
        return Scene.objects.select_related(
            "story",
            "chapter",
            "scene_type",
            "location"
        ).prefetch_related("beats")

    def get_serializer_class(self):
        if self.action == "list":
            return SceneListSerializer
        return SceneDetailSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class SceneBeatViewSet(viewsets.ModelViewSet):
    """API endpoint for Scene Beats."""

    serializer_class = SceneBeatSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["scene", "beat_type"]

    def get_queryset(self):
        return SceneBeat.objects.select_related("scene")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class SceneConnectionViewSet(viewsets.ModelViewSet):
    """API endpoint for Scene Connections."""

    serializer_class = SceneConnectionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["from_scene", "to_scene", "connection_type"]

    def get_queryset(self):
        return SceneConnection.objects.select_related(
            "from_scene",
            "to_scene"
        )

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
