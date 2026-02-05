"""
REST API views for PPTX-Hub.
"""

from __future__ import annotations

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from pptx_hub.django.models import Presentation, ProcessingJob
from pptx_hub.django.api.serializers import (
    PresentationSerializer,
    PresentationCreateSerializer,
    JobSerializer,
)


class TenantFilterMixin:
    """Mixin to filter querysets by user's organizations."""
    
    def get_queryset(self):
        """Filter by user's organizations."""
        qs = super().get_queryset()
        user = self.request.user
        
        if user.is_authenticated:
            org_ids = user.pptx_hub_memberships.filter(
                is_active=True
            ).values_list("organization_id", flat=True)
            qs = qs.filter(org_id__in=org_ids)
        else:
            qs = qs.none()
        
        return qs


class PresentationViewSet(TenantFilterMixin, viewsets.ModelViewSet):
    """
    API endpoint for presentations.
    
    list: List all presentations
    create: Upload a new presentation
    retrieve: Get presentation details
    update: Update presentation metadata
    destroy: Delete a presentation
    """
    
    queryset = Presentation.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == "create":
            return PresentationCreateSerializer
        return PresentationSerializer
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=["post"])
    def translate(self, request, pk=None):
        """Start a translation job for this presentation."""
        presentation = self.get_object()
        
        target_language = request.data.get("target_language")
        if not target_language:
            return Response(
                {"error": "target_language is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        # Create job
        job = ProcessingJob.objects.create(
            org=presentation.org,
            presentation=presentation,
            job_type=ProcessingJob.JobType.TRANSLATE,
            options={"target_language": target_language},
            created_by=request.user,
        )
        
        # TODO: Dispatch to task queue
        
        return Response(
            JobSerializer(job).data,
            status=status.HTTP_202_ACCEPTED,
        )
    
    @action(detail=True, methods=["get"])
    def jobs(self, request, pk=None):
        """List jobs for this presentation."""
        presentation = self.get_object()
        jobs = presentation.jobs.order_by("-created_at")
        serializer = JobSerializer(jobs, many=True)
        return Response(serializer.data)


class JobViewSet(TenantFilterMixin, viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for processing jobs.
    
    list: List all jobs
    retrieve: Get job details
    """
    
    queryset = ProcessingJob.objects.all()
    serializer_class = JobSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel a pending or running job."""
        job = self.get_object()
        
        if job.is_terminal:
            return Response(
                {"error": "Job is already in terminal state"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        job.status = ProcessingJob.Status.CANCELLED
        job.save(update_fields=["status", "updated_at"])
        
        return Response(JobSerializer(job).data)
    
    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        """Retry a failed job."""
        job = self.get_object()
        
        if not job.can_retry:
            return Response(
                {"error": "Job cannot be retried"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        job.status = ProcessingJob.Status.PENDING
        job.save(update_fields=["status", "updated_at"])
        
        # TODO: Dispatch to task queue
        
        return Response(JobSerializer(job).data)
