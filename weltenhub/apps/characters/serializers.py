"""
Weltenhub Characters Serializers
"""

from rest_framework import serializers
from .models import Character, CharacterArc, CharacterRelationship


class CharacterListSerializer(serializers.ModelSerializer):
    """Character list view."""

    role_name = serializers.CharField(
        source="role.name",
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = Character
        fields = [
            "id",
            "name",
            "slug",
            "world",
            "role",
            "role_name",
            "age",
            "gender",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "slug", "created_at"]


class CharacterDetailSerializer(serializers.ModelSerializer):
    """Character detail view."""

    role_name = serializers.CharField(
        source="role.name",
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = Character
        fields = [
            "id",
            "tenant",
            "world",
            "name",
            "slug",
            "role",
            "role_name",
            "full_name",
            "nickname",
            "age",
            "gender",
            "occupation",
            "physical_description",
            "personality",
            "backstory",
            "motivations",
            "fears",
            "strengths",
            "weaknesses",
            "speech_pattern",
            "home_location",
            "current_location",
            "portrait_image",
            "is_active",
            "tags",
            "metadata",
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


class CharacterArcSerializer(serializers.ModelSerializer):
    """Character arc serializer."""

    class Meta:
        model = CharacterArc
        fields = [
            "id",
            "character",
            "arc_type",
            "starting_state",
            "catalyst",
            "midpoint_state",
            "climax_event",
            "ending_state",
            "lessons_learned",
            "order",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class CharacterRelationshipSerializer(serializers.ModelSerializer):
    """Character relationship serializer."""

    from_character_name = serializers.CharField(
        source="from_character.name",
        read_only=True
    )
    to_character_name = serializers.CharField(
        source="to_character.name",
        read_only=True
    )

    class Meta:
        model = CharacterRelationship
        fields = [
            "id",
            "from_character",
            "from_character_name",
            "to_character",
            "to_character_name",
            "relationship_type",
            "description",
            "strength",
            "is_mutual",
            "start_context",
            "evolution_notes",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
