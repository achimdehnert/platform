"""
Weltenhub Worlds Serializers
============================

DRF serializers for World and WorldRule models.
"""

from rest_framework import serializers

from .models import World, WorldRule


class WorldRuleSerializer(serializers.ModelSerializer):
    """Serializer for WorldRule."""

    category_display = serializers.CharField(
        source="get_category_display",
        read_only=True
    )

    class Meta:
        model = WorldRule
        fields = [
            "id",
            "world",
            "category",
            "category_display",
            "rule",
            "explanation",
            "importance",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class WorldListSerializer(serializers.ModelSerializer):
    """Serializer for World list view (minimal fields)."""

    genre_name = serializers.CharField(
        source="genre.name",
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = World
        fields = [
            "id",
            "name",
            "slug",
            "genre",
            "genre_name",
            "setting_era",
            "is_public",
            "is_template",
            "created_at",
        ]
        read_only_fields = ["id", "slug", "created_at"]


class WorldDetailSerializer(serializers.ModelSerializer):
    """Serializer for World detail view (all fields)."""

    genre_name = serializers.CharField(
        source="genre.name",
        read_only=True,
        allow_null=True
    )
    rules = WorldRuleSerializer(many=True, read_only=True)

    class Meta:
        model = World
        fields = [
            "id",
            "tenant",
            "name",
            "slug",
            "genre",
            "genre_name",
            "description",
            "setting_era",
            "geography",
            "inhabitants",
            "culture",
            "technology_level",
            "magic_system",
            "history",
            "is_public",
            "is_template",
            "version",
            "tags",
            "cover_image",
            "rules",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        ]
        read_only_fields = [
            "id",
            "tenant",
            "slug",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        ]
