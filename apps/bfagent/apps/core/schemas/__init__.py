"""
Core Schemas Package
====================

Unified Pydantic schemas for the entire project.

Quick Start:
    from apps.core.schemas import BaseInput, BaseOutput
    from apps.core.schemas import validate_email, validate_url
    from apps.core.schemas import HandlerInput, HandlerOutput

    # Use base models
    class MyInput(BaseInput):
        name: str
        email: str

    # Use validators
    result = validate_email("user@example.com")
    if not result.is_valid:
        print(result.errors)

Package Structure:
    - base.py: Base models, mixins, enums
    - validators.py: Validation utilities
    - handlers.py: Handler-specific schemas
    - api.py: API request/response schemas (future)
"""

# Base Models
from .base import (
    BaseConfigModel,
    BaseInput,
    BaseOutput,
    IdentifiableMixin,
    PaginatedOutput,
    Priority,
    ProcessingStatus,
    StrictConfigModel,
    TimestampMixin,
    ValidationResult,
)

# Handler Schemas
from .handlers import (
    BatchProcessorConfig,
    BatchProcessorInput,
    BatchProcessorOutput,
    FileProcessorConfig,
    FileProcessorInput,
    FileProcessorOutput,
    HandlerConfig,
    HandlerInput,
    HandlerOutput,
    LLMProcessorConfig,
    LLMProcessorInput,
    LLMProcessorOutput,
    TemplateRendererConfig,
    TemplateRendererInput,
    TemplateRendererOutput,
    ValidationConfig,
    ValidationInput,
    ValidationOutput,
)

# Validators
from .validators import (
    ALLOWED_EXTENSIONS,
    validate_all,
    validate_email,
    validate_file_extension,
    validate_file_size,
    validate_json_string,
    validate_list_length,
    validate_range,
    validate_slug,
    validate_unique_items,
    validate_url,
)

__all__ = [
    # Base Models
    "BaseConfigModel",
    "StrictConfigModel",
    "BaseInput",
    "BaseOutput",
    "PaginatedOutput",
    "TimestampMixin",
    "IdentifiableMixin",
    "ProcessingStatus",
    "Priority",
    "ValidationResult",
    # Validators
    "validate_email",
    "validate_url",
    "validate_file_extension",
    "validate_file_size",
    "validate_slug",
    "validate_json_string",
    "validate_range",
    "validate_list_length",
    "validate_unique_items",
    "validate_all",
    "ALLOWED_EXTENSIONS",
    # Handler Schemas
    "HandlerConfig",
    "HandlerInput",
    "HandlerOutput",
    "LLMProcessorConfig",
    "LLMProcessorInput",
    "LLMProcessorOutput",
    "TemplateRendererConfig",
    "TemplateRendererInput",
    "TemplateRendererOutput",
    "ValidationConfig",
    "ValidationInput",
    "ValidationOutput",
    "FileProcessorConfig",
    "FileProcessorInput",
    "FileProcessorOutput",
    "BatchProcessorConfig",
    "BatchProcessorInput",
    "BatchProcessorOutput",
]

__version__ = "1.0.0"
