"""
REST API serializers for PPTX-Hub.
"""

from __future__ import annotations

from rest_framework import serializers

from pptx_hub.django.models import (
    Organization,
    Presentation,
    PresentationFile,
    ProcessingJob,
)


class OrganizationSerializer(serializers.ModelSerializer):
    """Serializer for organizations."""
    
    class Meta:
        model = Organization
        fields = ["id", "name", "slug", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class PresentationFileSerializer(serializers.ModelSerializer):
    """Serializer for presentation files."""
    
    class Meta:
        model = PresentationFile
        fields = [
            "id", "file_type", "version", "is_current",
            "original_filename", "mime_type", "file_size",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class PresentationSerializer(serializers.ModelSerializer):
    """Serializer for presentations."""
    
    files = PresentationFileSerializer(many=True, read_only=True)
    job_count = serializers.SerializerMethodField()
    latest_job_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Presentation
        fields = [
            "id", "title", "description", "status",
            "source_language", "target_language",
            "slide_count", "word_count",
            "original_filename", "metadata",
            "created_at", "updated_at",
            "files", "job_count", "latest_job_status",
        ]
        read_only_fields = [
            "id", "status", "slide_count", "word_count",
            "created_at", "updated_at",
        ]
    
    def get_job_count(self, obj) -> int:
        return obj.jobs.count()
    
    def get_latest_job_status(self, obj) -> str | None:
        latest = obj.jobs.order_by("-created_at").first()
        return latest.status if latest else None


class PresentationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating presentations."""
    
    file = serializers.FileField(write_only=True)
    org_id = serializers.UUIDField()
    
    class Meta:
        model = Presentation
        fields = ["title", "description", "file", "org_id"]
    
    def validate_file(self, value):
        """Validate uploaded file."""
        if not value.name.lower().endswith((".pptx", ".ppt")):
            raise serializers.ValidationError(
                "Only PowerPoint files (.pptx, .ppt) are allowed."
            )
        
        # 100MB limit
        if value.size > 100 * 1024 * 1024:
            raise serializers.ValidationError(
                "File size must be less than 100MB."
            )
        
        return value
    
    def create(self, validated_data):
        """Create presentation from uploaded file."""
        file = validated_data.pop("file")
        org_id = validated_data.pop("org_id")
        
        # Get organization
        try:
            org = Organization.objects.get(id=org_id)
        except Organization.DoesNotExist:
            raise serializers.ValidationError({"org_id": "Organization not found"})
        
        # Create presentation
        presentation = Presentation.objects.create(
            org=org,
            original_filename=file.name,
            **validated_data,
        )
        
        # TODO: Save file to storage and create PresentationFile record
        # TODO: Start extraction job
        
        return presentation


class JobSerializer(serializers.ModelSerializer):
    """Serializer for processing jobs."""
    
    presentation_title = serializers.CharField(
        source="presentation.title",
        read_only=True,
    )
    duration_ms = serializers.SerializerMethodField()
    
    class Meta:
        model = ProcessingJob
        fields = [
            "id", "job_type", "status", "priority",
            "progress", "progress_message",
            "options", "result_data", "error_message",
            "attempt_count", "max_attempts",
            "created_at", "started_at", "completed_at",
            "presentation_title", "duration_ms",
        ]
        read_only_fields = [
            "id", "status", "progress", "progress_message",
            "result_data", "error_message", "attempt_count",
            "created_at", "started_at", "completed_at",
        ]
    
    def get_duration_ms(self, obj) -> int | None:
        if obj.started_at and obj.completed_at:
            delta = obj.completed_at - obj.started_at
            return int(delta.total_seconds() * 1000)
        return None
