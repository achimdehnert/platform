"""
Weltenhub Lookups Serializers
=============================

DRF serializers for all lookup models.
"""

from rest_framework import serializers

from .models import (
    Genre,
    Mood,
    ConflictLevel,
    LocationType,
    SceneType,
    CharacterRole,
    TransportType,
)


class GenreSerializer(serializers.ModelSerializer):
    """Serializer for Genre lookup."""

    class Meta:
        model = Genre
        fields = [
            "id",
            "code",
            "name",
            "name_de",
            "description",
            "color",
            "icon",
            "order",
            "is_active",
        ]
        read_only_fields = ["id"]


class MoodSerializer(serializers.ModelSerializer):
    """Serializer for Mood lookup."""

    class Meta:
        model = Mood
        fields = [
            "id",
            "code",
            "name",
            "name_de",
            "description",
            "color",
            "intensity",
            "order",
            "is_active",
        ]
        read_only_fields = ["id"]


class ConflictLevelSerializer(serializers.ModelSerializer):
    """Serializer for ConflictLevel lookup."""

    class Meta:
        model = ConflictLevel
        fields = [
            "id",
            "code",
            "name",
            "name_de",
            "description",
            "intensity",
            "color",
            "order",
            "is_active",
        ]
        read_only_fields = ["id"]


class LocationTypeSerializer(serializers.ModelSerializer):
    """Serializer for LocationType lookup."""

    class Meta:
        model = LocationType
        fields = [
            "id",
            "code",
            "name",
            "name_de",
            "description",
            "parent_type",
            "icon",
            "order",
            "is_active",
        ]
        read_only_fields = ["id"]


class SceneTypeSerializer(serializers.ModelSerializer):
    """Serializer for SceneType lookup."""

    class Meta:
        model = SceneType
        fields = [
            "id",
            "code",
            "name",
            "name_de",
            "description",
            "icon",
            "color",
            "typical_duration_minutes",
            "order",
            "is_active",
        ]
        read_only_fields = ["id"]


class CharacterRoleSerializer(serializers.ModelSerializer):
    """Serializer for CharacterRole lookup."""

    class Meta:
        model = CharacterRole
        fields = [
            "id",
            "code",
            "name",
            "name_de",
            "description",
            "is_main",
            "color",
            "order",
            "is_active",
        ]
        read_only_fields = ["id"]


class TransportTypeSerializer(serializers.ModelSerializer):
    """Serializer for TransportType lookup."""

    class Meta:
        model = TransportType
        fields = [
            "id",
            "code",
            "name",
            "name_de",
            "description",
            "icon",
            "order",
            "is_active",
        ]
        read_only_fields = ["id"]
