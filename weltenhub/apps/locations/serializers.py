"""
Weltenhub Locations Serializers
"""

from rest_framework import serializers
from .models import Location


class LocationListSerializer(serializers.ModelSerializer):
    """Location list view (minimal)."""

    location_type_name = serializers.CharField(
        source="location_type.name",
        read_only=True,
        allow_null=True
    )
    parent_name = serializers.CharField(
        source="parent.name",
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = Location
        fields = [
            "id",
            "name",
            "slug",
            "world",
            "parent",
            "parent_name",
            "location_type",
            "location_type_name",
            "created_at",
        ]
        read_only_fields = ["id", "slug", "created_at"]


class LocationDetailSerializer(serializers.ModelSerializer):
    """Location detail view (all fields)."""

    location_type_name = serializers.CharField(
        source="location_type.name",
        read_only=True,
        allow_null=True
    )
    full_path = serializers.SerializerMethodField()
    depth = serializers.SerializerMethodField()

    class Meta:
        model = Location
        fields = [
            "id",
            "tenant",
            "world",
            "parent",
            "name",
            "slug",
            "location_type",
            "location_type_name",
            "description",
            "atmosphere",
            "significance",
            "latitude",
            "longitude",
            "image",
            "metadata",
            "full_path",
            "depth",
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

    def get_full_path(self, obj) -> str:
        return obj.full_path

    def get_depth(self, obj) -> int:
        return obj.depth
