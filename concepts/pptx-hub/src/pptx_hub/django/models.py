"""
Django models for PPTX-Hub.

Database models for presentations, jobs, and file management.
"""

from __future__ import annotations

import uuid
from typing import Any

from django.conf import settings
from django.db import models


class Organization(models.Model):
    """
    Tenant model for multi-tenancy.
    
    All presentations and jobs belong to an organization.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    
    # Settings
    settings = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "pptx_hub_organization"
        ordering = ["name"]
    
    def __str__(self) -> str:
        return self.name


class Membership(models.Model):
    """User membership in an organization."""
    
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"
        VIEWER = "viewer", "Viewer"
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pptx_hub_memberships",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "pptx_hub_membership"
        unique_together = ["user", "organization"]
    
    def __str__(self) -> str:
        return f"{self.user} - {self.organization} ({self.role})"


class TenantAwareManager(models.Manager):
    """Manager that filters by organization."""
    
    def for_org(self, org_id: uuid.UUID):
        """Filter queryset by organization."""
        return self.filter(org_id=org_id)


class TenantAwareModel(models.Model):
    """
    Abstract base model for tenant-aware models.
    
    All models that need organization isolation should inherit from this.
    """
    
    org = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)ss",
    )
    
    objects = TenantAwareManager()
    
    class Meta:
        abstract = True


class Presentation(TenantAwareModel):
    """
    A PowerPoint presentation.
    
    Represents a PPTX file with metadata, version history,
    and associated processing jobs.
    """
    
    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready"
        ERROR = "error", "Error"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic info
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UPLOADED,
    )
    
    # Language
    source_language = models.CharField(max_length=10, blank=True)
    target_language = models.CharField(max_length=10, blank=True)
    
    # Statistics
    slide_count = models.PositiveIntegerField(default=0)
    word_count = models.PositiveIntegerField(default=0)
    
    # Metadata
    original_filename = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Audit
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="pptx_presentations_created",
    )
    
    class Meta:
        db_table = "pptx_hub_presentation"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["org", "status"]),
            models.Index(fields=["org", "created_at"]),
        ]
    
    def __str__(self) -> str:
        return self.title or self.original_filename


class PresentationFile(models.Model):
    """
    A file associated with a presentation.
    
    Tracks different versions and types of files (original, processed, etc.)
    """
    
    class FileType(models.TextChoices):
        ORIGINAL = "original", "Original"
        PROCESSED = "processed", "Processed"
        THUMBNAIL = "thumbnail", "Thumbnail"
        EXPORT = "export", "Export"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    presentation = models.ForeignKey(
        Presentation,
        on_delete=models.CASCADE,
        related_name="files",
    )
    
    file_type = models.CharField(max_length=20, choices=FileType.choices)
    version = models.PositiveSmallIntegerField(default=1)
    is_current = models.BooleanField(default=True)
    
    # Storage
    storage_backend = models.CharField(max_length=20, default="local")
    storage_path = models.CharField(max_length=500)
    
    # File info
    original_filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=100, default="application/octet-stream")
    file_size = models.PositiveBigIntegerField(null=True, blank=True)
    checksum_sha256 = models.CharField(max_length=64, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "pptx_hub_presentation_file"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["presentation", "file_type", "is_current"]),
        ]
    
    def __str__(self) -> str:
        return f"{self.presentation_id}/{self.file_type}/v{self.version}"


class ProcessingJob(TenantAwareModel):
    """
    An async processing job.
    
    Tracks the status and progress of presentation processing tasks.
    """
    
    class JobType(models.TextChoices):
        EXTRACT = "extract", "Text Extraction"
        TRANSLATE = "translate", "Translation"
        ENHANCE = "enhance", "Enhancement"
        REPACKAGE = "repackage", "Repackage"
        ANALYZE = "analyze", "Analysis"
        PIPELINE = "pipeline", "Full Pipeline"
    
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Job definition
    job_type = models.CharField(max_length=20, choices=JobType.choices)
    presentation = models.ForeignKey(
        Presentation,
        on_delete=models.CASCADE,
        related_name="jobs",
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    priority = models.PositiveSmallIntegerField(default=5)
    
    # Progress
    progress = models.PositiveSmallIntegerField(default=0)
    progress_message = models.CharField(max_length=255, blank=True)
    
    # Input/Output
    input_snapshot = models.JSONField(default=dict, blank=True)
    options = models.JSONField(default=dict, blank=True)
    result_data = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    
    # Retry
    attempt_count = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=3)
    
    # Task queue integration
    task_id = models.CharField(max_length=100, blank=True, db_index=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Audit
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="pptx_jobs_created",
    )
    
    class Meta:
        db_table = "pptx_hub_processing_job"
        ordering = ["-priority", "created_at"]
        indexes = [
            models.Index(fields=["org", "status"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["presentation", "job_type"]),
        ]
    
    def __str__(self) -> str:
        return f"{self.job_type} - {self.presentation_id} ({self.status})"
    
    @property
    def is_terminal(self) -> bool:
        """Check if job is in a terminal state."""
        return self.status in (
            self.Status.COMPLETED,
            self.Status.FAILED,
            self.Status.CANCELLED,
        )
    
    @property
    def can_retry(self) -> bool:
        """Check if job can be retried."""
        return (
            self.attempt_count < self.max_attempts
            and self.status == self.Status.FAILED
        )


class JobAttempt(models.Model):
    """
    A single execution attempt of a job.
    
    Tracks each retry with timing and error details.
    """
    
    job = models.ForeignKey(
        ProcessingJob,
        on_delete=models.CASCADE,
        related_name="attempts",
    )
    attempt_number = models.PositiveSmallIntegerField()
    
    status = models.CharField(
        max_length=20,
        choices=[
            ("running", "Running"),
            ("completed", "Completed"),
            ("failed", "Failed"),
        ],
    )
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    
    # Result
    result_data = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    error_traceback = models.TextField(blank=True)
    
    class Meta:
        db_table = "pptx_hub_job_attempt"
        ordering = ["job", "attempt_number"]
        unique_together = ["job", "attempt_number"]
    
    def __str__(self) -> str:
        return f"Job {self.job_id} - Attempt {self.attempt_number}"
