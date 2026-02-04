"""
Weltenhub Locations API Views
"""

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Location
from .serializers import LocationListSerializer, LocationDetailSerializer


class LocationViewSet(viewsets.ModelViewSet):
    """API endpoint for Locations."""

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["world", "parent", "location_type"]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        return Location.objects.select_related(
            "world",
            "parent",
            "location_type"
        )

    def get_serializer_class(self):
        if self.action == "list":
            return LocationListSerializer
        return LocationDetailSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=True, methods=["get"])
    def children(self, request, pk=None):
        """Get direct children of this location."""
        location = self.get_object()
        children = location.children.all()
        serializer = LocationListSerializer(children, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def ancestors(self, request, pk=None):
        """Get all ancestors (path to root)."""
        location = self.get_object()
        ancestors = location.get_ancestors()
        serializer = LocationListSerializer(ancestors, many=True)
        return Response(serializer.data)
