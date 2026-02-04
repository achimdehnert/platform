"""
Weltenhub Stories Serializers
"""

from rest_framework import serializers
from .models import Story, Chapter, PlotThread, TimelineEvent


class ChapterSerializer(serializers.ModelSerializer):
    """Chapter serializer."""

    class Meta:
        model = Chapter
        fields = [
            "id",
            "story",
            "title",
            "number",
            "summary",
            "notes",
            "target_word_count",
            "actual_word_count",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class PlotThreadSerializer(serializers.ModelSerializer):
    """Plot thread serializer."""

    class Meta:
        model = PlotThread
        fields = [
            "id",
            "story",
            "name",
            "thread_type",
            "description",
            "resolution",
            "color",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class TimelineEventSerializer(serializers.ModelSerializer):
    """Timeline event serializer."""

    class Meta:
        model = TimelineEvent
        fields = [
            "id",
            "story",
            "scene",
            "description",
            "story_datetime",
            "story_date_description",
            "is_shown",
            "is_pivotal",
            "location",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class StoryListSerializer(serializers.ModelSerializer):
    """Story list view."""

    genre_name = serializers.CharField(
        source="genre.name",
        read_only=True,
        allow_null=True
    )
    chapter_count = serializers.SerializerMethodField()

    class Meta:
        model = Story
        fields = [
            "id",
            "title",
            "slug",
            "world",
            "genre",
            "genre_name",
            "status",
            "is_public",
            "actual_word_count",
            "chapter_count",
            "created_at",
        ]
        read_only_fields = ["id", "slug", "created_at"]

    def get_chapter_count(self, obj) -> int:
        return obj.chapters.count()


class StoryDetailSerializer(serializers.ModelSerializer):
    """Story detail view."""

    genre_name = serializers.CharField(
        source="genre.name",
        read_only=True,
        allow_null=True
    )
    chapters = ChapterSerializer(many=True, read_only=True)
    plot_threads = PlotThreadSerializer(many=True, read_only=True)

    class Meta:
        model = Story
        fields = [
            "id",
            "tenant",
            "world",
            "title",
            "slug",
            "genre",
            "genre_name",
            "premise",
            "logline",
            "synopsis",
            "themes",
            "target_audience",
            "spice_level",
            "target_word_count",
            "actual_word_count",
            "status",
            "cover_image",
            "is_public",
            "source_trip",
            "notes",
            "chapters",
            "plot_threads",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "tenant",
            "slug",
            "created_at",
            "updated_at",
        ]
