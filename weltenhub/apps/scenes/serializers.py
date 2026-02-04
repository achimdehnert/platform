"""
Weltenhub Scenes Serializers
"""

from rest_framework import serializers
from .models import SceneTemplate, Scene, SceneBeat, SceneConnection


class SceneTemplateSerializer(serializers.ModelSerializer):
    """Scene template serializer."""

    class Meta:
        model = SceneTemplate
        fields = [
            "id",
            "name",
            "slug",
            "scene_type",
            "description",
            "purpose",
            "structure",
            "typical_beats",
            "mood_guidance",
            "pov_suggestions",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "slug", "created_at"]


class SceneBeatSerializer(serializers.ModelSerializer):
    """Scene beat serializer."""

    class Meta:
        model = SceneBeat
        fields = [
            "id",
            "scene",
            "beat_type",
            "description",
            "order",
            "emotional_shift",
            "tension_level",
            "word_count_target",
            "notes",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class SceneConnectionSerializer(serializers.ModelSerializer):
    """Scene connection serializer."""

    from_scene_title = serializers.CharField(
        source="from_scene.title",
        read_only=True
    )
    to_scene_title = serializers.CharField(
        source="to_scene.title",
        read_only=True
    )

    class Meta:
        model = SceneConnection
        fields = [
            "id",
            "from_scene",
            "from_scene_title",
            "to_scene",
            "to_scene_title",
            "connection_type",
            "description",
            "is_optional",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class SceneListSerializer(serializers.ModelSerializer):
    """Scene list view."""

    scene_type_name = serializers.CharField(
        source="scene_type.name",
        read_only=True,
        allow_null=True
    )
    location_name = serializers.CharField(
        source="location.name",
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = Scene
        fields = [
            "id",
            "title",
            "slug",
            "story",
            "chapter",
            "scene_type",
            "scene_type_name",
            "location",
            "location_name",
            "order",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "slug", "created_at"]


class SceneDetailSerializer(serializers.ModelSerializer):
    """Scene detail view."""

    scene_type_name = serializers.CharField(
        source="scene_type.name",
        read_only=True,
        allow_null=True
    )
    beats = SceneBeatSerializer(many=True, read_only=True)

    class Meta:
        model = Scene
        fields = [
            "id",
            "tenant",
            "story",
            "chapter",
            "template",
            "title",
            "slug",
            "scene_type",
            "scene_type_name",
            "location",
            "summary",
            "goal",
            "conflict",
            "outcome",
            "pov_character",
            "mood",
            "conflict_level",
            "order",
            "word_count_target",
            "word_count_actual",
            "status",
            "notes",
            "beats",
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
