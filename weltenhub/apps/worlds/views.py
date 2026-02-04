"""
Weltenhub Worlds API Views
==========================

ViewSets for World and WorldRule models.
All data is tenant-filtered automatically.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import World, WorldRule
from .serializers import (
    WorldListSerializer,
    WorldDetailSerializer,
    WorldRuleSerializer,
)


class WorldViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Worlds.

    list: Get all worlds for current tenant
    create: Create a new world
    retrieve: Get world details
    update: Update a world
    destroy: Soft-delete a world
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["genre", "is_public", "is_template"]
    search_fields = ["name", "description", "setting_era"]
    ordering_fields = ["name", "created_at", "updated_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        """Return worlds for current tenant."""
        return World.objects.select_related("genre").prefetch_related("rules")

    def get_serializer_class(self):
        """Use different serializers for list vs detail."""
        if self.action == "list":
            return WorldListSerializer
        return WorldDetailSerializer

    def perform_create(self, serializer):
        """Set created_by on create."""
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        """Set updated_by on update."""
        serializer.save(updated_by=self.request.user)

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        """Create a copy of this world."""
        world = self.get_object()
        new_world = World.objects.create(
            tenant=world.tenant,
            name=f"{world.name} (Copy)",
            genre=world.genre,
            description=world.description,
            setting_era=world.setting_era,
            geography=world.geography,
            inhabitants=world.inhabitants,
            culture=world.culture,
            technology_level=world.technology_level,
            magic_system=world.magic_system,
            history=world.history,
            is_public=False,
            is_template=False,
            tags=world.tags,
            created_by=request.user,
        )
        serializer = WorldDetailSerializer(new_world)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class WorldRuleViewSet(viewsets.ModelViewSet):
    """API endpoint for World Rules."""

    serializer_class = WorldRuleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["world", "category", "importance"]

    def get_queryset(self):
        """Return rules for current tenant's worlds."""
        return WorldRule.objects.select_related("world")

    def perform_create(self, serializer):
        """Set created_by on create."""
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        """Set updated_by on update."""
        serializer.save(updated_by=self.request.user)
