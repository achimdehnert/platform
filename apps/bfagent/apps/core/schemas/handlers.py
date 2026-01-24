"""
Handler Schemas
===============

Pydantic models for handler input/output validation.

Consolidates from:
- apps/bfagent/services/handlers/schemas.py
- apps/genagent/core/schemas.py
"""

from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator

from .base import BaseConfigModel, BaseInput, BaseOutput, ProcessingStatus

# =============================================================================
# Handler Configuration
# =============================================================================


class HandlerConfig(BaseConfigModel):
    """
    Base configuration for all handlers.

    Provides standard settings all handlers might need.
    """

    timeout: int = Field(300, ge=1, le=3600, description="Execution timeout in seconds")
    retry_count: int = Field(3, ge=0, le=10, description="Number of retries on failure")
    retry_delay: float = Field(1.0, ge=0, description="Delay between retries in seconds")
    enable_logging: bool = Field(True, description="Enable detailed logging")
    enable_metrics: bool = Field(True, description="Collect performance metrics")


# =============================================================================
# Handler Input/Output
# =============================================================================


class HandlerInput(BaseInput):
    """
    Standard input for handlers.

    Extends BaseInput with handler-specific fields.
    """

    data: Dict[str, Any] = Field(default_factory=dict, description="Input data for processing")
    config: Optional[HandlerConfig] = Field(None, description="Handler configuration overrides")


class HandlerOutput(BaseOutput):
    """
    Standard output from handlers.

    Extends BaseOutput with handler-specific fields.
    """

    handler_name: Optional[str] = Field(None, description="Name of handler that processed this")
    handler_version: Optional[str] = Field(None, description="Version of handler")
    execution_time_ms: Optional[int] = Field(
        None, ge=0, description="Execution time in milliseconds"
    )
    status: ProcessingStatus = Field(ProcessingStatus.COMPLETED, description="Processing status")


# =============================================================================
# LLM Handler Schemas
# =============================================================================


class LLMProcessorConfig(HandlerConfig):
    """Configuration for LLM processing handlers."""

    model: str = Field("gpt-4", description="LLM model to use")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(4096, ge=1, le=32000, description="Maximum tokens to generate")
    system_prompt: Optional[str] = Field(None, description="System prompt for LLM")


class LLMProcessorInput(HandlerInput):
    """Input for LLM processing."""

    prompt: str = Field(description="User prompt for LLM")
    context: Dict[str, Any] = Field(
        default_factory=dict, description="Additional context for prompt"
    )
    config: Optional[LLMProcessorConfig] = None


class LLMProcessorOutput(HandlerOutput):
    """Output from LLM processing."""

    generated_text: Optional[str] = Field(None, description="LLM generated text")
    tokens_used: Optional[int] = Field(None, ge=0, description="Number of tokens used")
    cost_usd: Optional[float] = Field(None, ge=0, description="Estimated cost in USD")


# =============================================================================
# Template Renderer Schemas
# =============================================================================


class TemplateRendererConfig(HandlerConfig):
    """Configuration for template rendering."""

    template_engine: str = Field("jinja2", description="Template engine to use")
    auto_escape: bool = Field(True, description="Auto-escape HTML")
    strict_undefined: bool = Field(False, description="Raise error on undefined variables")


class TemplateRendererInput(HandlerInput):
    """Input for template rendering."""

    template: str = Field(description="Template content or path")
    context: Dict[str, Any] = Field(default_factory=dict, description="Template context variables")
    config: Optional[TemplateRendererConfig] = None


class TemplateRendererOutput(HandlerOutput):
    """Output from template rendering."""

    rendered: Optional[str] = Field(None, description="Rendered template output")


# =============================================================================
# Data Validation Schemas
# =============================================================================


class ValidationConfig(HandlerConfig):
    """Configuration for validation handlers."""

    strict_mode: bool = Field(True, description="Fail on first error")
    collect_all_errors: bool = Field(True, description="Collect all errors, not just first")


class ValidationInput(HandlerInput):
    """Input for validation."""

    validation_schema: Dict[str, Any] = Field(description="Validation schema")
    config: Optional[ValidationConfig] = None


class ValidationOutput(HandlerOutput):
    """Output from validation."""

    is_valid: bool = Field(description="Whether data is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")


# =============================================================================
# File Processing Schemas
# =============================================================================


class FileProcessorConfig(HandlerConfig):
    """Configuration for file processing."""

    max_file_size_mb: float = Field(100.0, ge=0.1, le=1000.0, description="Maximum file size in MB")
    allowed_extensions: List[str] = Field(
        default_factory=list, description="Allowed file extensions"
    )


class FileProcessorInput(HandlerInput):
    """Input for file processing."""

    file_path: str = Field(description="Path to file to process")
    config: Optional[FileProcessorConfig] = None


class FileProcessorOutput(HandlerOutput):
    """Output from file processing."""

    processed_file_path: Optional[str] = Field(None, description="Path to processed file")
    file_size_bytes: Optional[int] = Field(None, ge=0, description="File size in bytes")


# =============================================================================
# Batch Processing Schemas
# =============================================================================


class BatchProcessorConfig(HandlerConfig):
    """Configuration for batch processing."""

    batch_size: int = Field(100, ge=1, le=10000, description="Number of items per batch")
    parallel: bool = Field(False, description="Process batches in parallel")
    continue_on_error: bool = Field(
        True, description="Continue processing on individual item errors"
    )


class BatchProcessorInput(HandlerInput):
    """Input for batch processing."""

    items: List[Dict[str, Any]] = Field(description="List of items to process")
    config: Optional[BatchProcessorConfig] = None


class BatchProcessorOutput(HandlerOutput):
    """Output from batch processing."""

    total_items: int = Field(ge=0, description="Total number of items")
    processed_items: int = Field(ge=0, description="Successfully processed items")
    failed_items: int = Field(ge=0, description="Failed items")
    results: List[Dict[str, Any]] = Field(default_factory=list, description="Results for each item")


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # Base Handler
    "HandlerConfig",
    "HandlerInput",
    "HandlerOutput",
    # LLM
    "LLMProcessorConfig",
    "LLMProcessorInput",
    "LLMProcessorOutput",
    # Template
    "TemplateRendererConfig",
    "TemplateRendererInput",
    "TemplateRendererOutput",
    # Validation
    "ValidationConfig",
    "ValidationInput",
    "ValidationOutput",
    # File
    "FileProcessorConfig",
    "FileProcessorInput",
    "FileProcessorOutput",
    # Batch
    "BatchProcessorConfig",
    "BatchProcessorInput",
    "BatchProcessorOutput",
]
