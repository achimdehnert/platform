"""
Core Base Schemas
=================

Unified base Pydantic models for consistent validation across the project.

Consolidates patterns from:
- apps/genagent/core/schemas.py
- apps/bfagent/services/handlers/schemas.py
- Various handler input/output schemas
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

# =============================================================================
# Base Configuration Models
# =============================================================================


class BaseConfigModel(BaseModel):
    """
    Base for all configuration models.

    Features:
    - Allows extra fields for extensibility
    - Validates on assignment
    - Uses JSON schema generation
    """

    model_config = ConfigDict(
        extra="allow", validate_assignment=True, json_schema_extra={"type": "object"}
    )


class StrictConfigModel(BaseModel):
    """
    Strict configuration model - no extra fields allowed.

    Use for:
    - API contracts
    - Database schemas
    - Critical validation
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True, frozen=False)


# =============================================================================
# Base Input/Output Models
# =============================================================================


class BaseInput(BaseConfigModel):
    """
    Base model for all handler inputs.

    Provides common metadata fields that all inputs should have.
    """

    request_id: Optional[str] = Field(None, description="Unique request identifier for tracking")
    user_id: Optional[int] = Field(None, description="User making the request")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {"request_id": "req_123abc", "user_id": 1, "metadata": {"source": "web"}}
        }


class BaseOutput(BaseConfigModel):
    """
    Base model for all handler outputs.

    Standardizes response format across all handlers.
    """

    success: bool = Field(description="Whether the operation succeeded")
    message: Optional[str] = Field(None, description="Human-readable message")
    errors: List[str] = Field(default_factory=list, description="List of error messages if any")
    warnings: List[str] = Field(default_factory=list, description="List of warning messages")
    data: Optional[Dict[str, Any]] = Field(None, description="Result data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Response metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Operation completed",
                "data": {"result": "value"},
                "metadata": {"duration_ms": 150},
            }
        }


class PaginatedOutput(BaseOutput):
    """
    Base model for paginated responses.

    Adds pagination metadata to standard output.
    """

    page: int = Field(1, ge=1, description="Current page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")
    total_items: int = Field(0, ge=0, description="Total number of items")
    total_pages: int = Field(0, ge=0, description="Total number of pages")
    has_next: bool = Field(False, description="Whether there's a next page")
    has_previous: bool = Field(False, description="Whether there's a previous page")


# =============================================================================
# Status Enums
# =============================================================================


class ProcessingStatus(str, Enum):
    """Standard processing status values."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class Priority(str, Enum):
    """Standard priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# =============================================================================
# Common Field Models
# =============================================================================


class TimestampMixin(BaseModel):
    """Mixin for models that need timestamps."""

    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    def touch(self):
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now()


class IdentifiableMixin(BaseModel):
    """Mixin for models that need unique identification."""

    id: Optional[Union[int, str]] = Field(None, description="Unique identifier")
    slug: Optional[str] = Field(None, description="URL-friendly identifier")


# =============================================================================
# Validation Result Model
# =============================================================================


class ValidationResult(BaseModel):
    """
    Standardized validation result.

    Used across validators to provide consistent error reporting.
    """

    is_valid: bool = Field(description="Whether validation passed")
    errors: List[str] = Field(default_factory=list, description="Validation error messages")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    field_errors: Dict[str, List[str]] = Field(
        default_factory=dict, description="Field-specific errors"
    )

    @property
    def error_count(self) -> int:
        """Total number of errors."""
        return len(self.errors) + sum(len(e) for e in self.field_errors.values())

    def add_error(self, error: str, field: Optional[str] = None):
        """Add an error message."""
        if field:
            if field not in self.field_errors:
                self.field_errors[field] = []
            self.field_errors[field].append(error)
        else:
            self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str):
        """Add a warning message."""
        self.warnings.append(warning)


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # Base Models
    "BaseConfigModel",
    "StrictConfigModel",
    "BaseInput",
    "BaseOutput",
    "PaginatedOutput",
    # Mixins
    "TimestampMixin",
    "IdentifiableMixin",
    # Enums
    "ProcessingStatus",
    "Priority",
    # Validation
    "ValidationResult",
]
