"""
Weltenhub Stories API Views
"""

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Story, Chapter, PlotThread, TimelineEvent
from .serializers import (
    StoryListSerializer,
    StoryDetailSerializer,
    ChapterSerializer,
    PlotThreadSerializer,
    TimelineEventSerializer,
)


class StoryViewSet(viewsets.ModelViewSet):
    """API endpoint for Stories."""

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["world", "genre", "status", "is_public"]
    search_fields = ["title", "premise", "logline"]
    ordering_fields = ["title", "created_at", "actual_word_count"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Story.objects.select_related(
            "world",
            "genre"
        ).prefetch_related("chapters", "plot_threads")

    def get_serializer_class(self):
        if self.action == "list":
            return StoryListSerializer
        return StoryDetailSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=True, methods=["post"])
    def update_word_count(self, request, pk=None):
        """Recalculate word count from scenes."""
        story = self.get_object()
        count = story.update_word_count()
        return Response({"actual_word_count": count})


class ChapterViewSet(viewsets.ModelViewSet):
    """API endpoint for Chapters."""

    serializer_class = ChapterSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["story", "status"]
    ordering_fields = ["number"]
    ordering = ["number"]

    def get_queryset(self):
        return Chapter.objects.select_related("story")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class PlotThreadViewSet(viewsets.ModelViewSet):
    """API endpoint for Plot Threads."""

    serializer_class = PlotThreadSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["story", "thread_type", "status"]

    def get_queryset(self):
        return PlotThread.objects.select_related("story")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class TimelineEventViewSet(viewsets.ModelViewSet):
    """API endpoint for Timeline Events."""

    serializer_class = TimelineEventSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["story", "is_shown", "is_pivotal"]
    ordering_fields = ["story_datetime"]
    ordering = ["story_datetime"]

    def get_queryset(self):
        return TimelineEvent.objects.select_related("story", "scene")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
