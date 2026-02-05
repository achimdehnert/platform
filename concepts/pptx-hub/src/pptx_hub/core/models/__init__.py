"""
Core data models for PPTX-Hub.

These are Pydantic models used for data validation and serialization.
They are framework-agnostic and can be used standalone or with Django.
"""

from pptx_hub.core.models.presentation import (
    Presentation,
    Slide,
    SlideText,
    ExtractionResult,
)
from pptx_hub.core.models.job import (
    Job,
    JobStatus,
    JobType,
    JobResult,
)

__all__ = [
    "Presentation",
    "Slide",
    "SlideText",
    "ExtractionResult",
    "Job",
    "JobStatus",
    "JobType",
    "JobResult",
]
