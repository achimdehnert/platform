"""
Job data models.

Pydantic models for representing processing jobs and their status.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict


class JobStatus(str, Enum):
    """Status of a processing job."""
    
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    """Type of processing job."""
    
    EXTRACT = "extract"
    TRANSLATE = "translate"
    ENHANCE = "enhance"
    REPACKAGE = "repackage"
    ANALYZE = "analyze"
    PIPELINE = "pipeline"


class JobResult(BaseModel):
    """Result of a completed job."""
    
    model_config = ConfigDict(frozen=True)
    
    success: bool
    output_path: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    
    # Timing
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int | None = None


class Job(BaseModel):
    """A processing job."""
    
    model_config = ConfigDict(frozen=True)
    
    id: UUID = Field(default_factory=uuid4)
    job_type: JobType
    status: JobStatus = JobStatus.PENDING
    
    # Input
    presentation_id: UUID | None = None
    input_path: str | None = None
    input_snapshot: dict[str, Any] = Field(default_factory=dict)
    
    # Configuration
    options: dict[str, Any] = Field(default_factory=dict)
    priority: int = 5  # 1-10, higher = more important
    
    # Progress
    progress: int = 0  # 0-100
    progress_message: str = ""
    
    # Result
    result: JobResult | None = None
    error_message: str | None = None
    
    # Retry handling
    attempt_count: int = 0
    max_attempts: int = 3
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    
    # Multi-tenancy
    org_id: int | None = None
    created_by_id: int | None = None
    
    @property
    def is_terminal(self) -> bool:
        """Check if job is in a terminal state."""
        return self.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)
    
    @property
    def can_retry(self) -> bool:
        """Check if job can be retried."""
        return self.attempt_count < self.max_attempts and self.status == JobStatus.FAILED
    
    @property
    def duration_ms(self) -> int | None:
        """Calculate job duration in milliseconds."""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return int(delta.total_seconds() * 1000)
        return None
