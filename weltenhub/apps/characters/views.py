"""
Weltenhub Characters API Views
"""

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Character, CharacterArc, CharacterRelationship
from .serializers import (
    CharacterListSerializer,
    CharacterDetailSerializer,
    CharacterArcSerializer,
    CharacterRelationshipSerializer,
)


class CharacterViewSet(viewsets.ModelViewSet):
    """API endpoint for Characters."""

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["world", "role", "is_active"]
    search_fields = ["name", "full_name", "nickname", "occupation"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        return Character.objects.select_related("world", "role")

    def get_serializer_class(self):
        if self.action == "list":
            return CharacterListSerializer
        return CharacterDetailSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=True, methods=["get"])
    def arcs(self, request, pk=None):
        """Get character arcs."""
        character = self.get_object()
        arcs = character.arcs.all()
        serializer = CharacterArcSerializer(arcs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def relationships(self, request, pk=None):
        """Get character relationships."""
        character = self.get_object()
        rels = CharacterRelationship.objects.filter(
            from_character=character
        ) | CharacterRelationship.objects.filter(
            to_character=character
        )
        serializer = CharacterRelationshipSerializer(rels, many=True)
        return Response(serializer.data)


class CharacterArcViewSet(viewsets.ModelViewSet):
    """API endpoint for Character Arcs."""

    serializer_class = CharacterArcSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["character", "arc_type"]

    def get_queryset(self):
        return CharacterArc.objects.select_related("character")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class CharacterRelationshipViewSet(viewsets.ModelViewSet):
    """API endpoint for Character Relationships."""

    serializer_class = CharacterRelationshipSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["from_character", "to_character", "relationship_type"]

    def get_queryset(self):
        return CharacterRelationship.objects.select_related(
            "from_character",
            "to_character"
        )

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
