"""
Structured event logging for prompt executions.

Events provide detailed, structured logs for debugging and auditing.
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Types of prompt events."""

    # Lifecycle events
    EXECUTION_STARTED = "execution.started"
    EXECUTION_COMPLETED = "execution.completed"
    EXECUTION_FAILED = "execution.failed"

    # Cache events
    CACHE_HIT = "cache.hit"
    CACHE_MISS = "cache.miss"
    CACHE_SET = "cache.set"

    # Security events
    INJECTION_DETECTED = "security.injection_detected"
    INPUT_SANITIZED = "security.input_sanitized"

    # Template events
    TEMPLATE_LOADED = "template.loaded"
    TEMPLATE_NOT_FOUND = "template.not_found"
    TEMPLATE_VALIDATION_FAILED = "template.validation_failed"

    # LLM events
    LLM_REQUEST_STARTED = "llm.request_started"
    LLM_REQUEST_COMPLETED = "llm.request_completed"
    LLM_REQUEST_FAILED = "llm.request_failed"
    LLM_RETRY = "llm.retry"

    # Render events
    RENDER_STARTED = "render.started"
    RENDER_COMPLETED = "render.completed"
    RENDER_FAILED = "render.failed"


class PromptEvent(BaseModel):
    """
    Structured event for prompt operations.

    All events follow a consistent schema for easy parsing and analysis.
    """

    # Event identity
    event_type: EventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Context
    execution_id: UUID | None = None
    template_key: str | None = None
    app_name: str = "unknown"
    user_id: str | None = None

    # Event data
    data: dict[str, Any] = Field(default_factory=dict)

    # Performance
    duration_ms: float | None = None

    # Error info (for failed events)
    error_type: str | None = None
    error_message: str | None = None

    def to_log_dict(self) -> dict[str, Any]:
        """Convert to dictionary for structured logging."""
        result = {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "app_name": self.app_name,
        }

        if self.execution_id:
            result["execution_id"] = str(self.execution_id)
        if self.template_key:
            result["template_key"] = self.template_key
        if self.user_id:
            result["user_id"] = self.user_id
        if self.duration_ms is not None:
            result["duration_ms"] = self.duration_ms
        if self.error_type:
            result["error_type"] = self.error_type
            result["error_message"] = self.error_message
        if self.data:
            result["data"] = self.data

        return result

    model_config = {"frozen": True}


# Module-level logger
_logger: logging.Logger | None = None


def get_event_logger() -> logging.Logger:
    """Get or create the prompt event logger."""
    global _logger
    if _logger is None:
        _logger = logging.getLogger("creative_services.prompts.events")
    return _logger


def emit_event(event: PromptEvent, logger: logging.Logger | None = None) -> None:
    """
    Emit a prompt event to the logger.

    Args:
        event: Event to emit
        logger: Optional custom logger (uses default if not provided)
    """
    if logger is None:
        logger = get_event_logger()

    log_data = event.to_log_dict()

    # Determine log level based on event type
    if event.event_type.value.endswith("_failed"):
        logger.error("Prompt event: %s", event.event_type.value, extra=log_data)
    elif event.event_type == EventType.INJECTION_DETECTED:
        logger.warning("Prompt event: %s", event.event_type.value, extra=log_data)
    else:
        logger.info("Prompt event: %s", event.event_type.value, extra=log_data)


# Convenience functions for common events


def emit_execution_started(
    execution_id: UUID,
    template_key: str,
    app_name: str = "unknown",
    user_id: str | None = None,
    variables: dict | None = None,
) -> PromptEvent:
    """Emit execution started event."""
    event = PromptEvent(
        event_type=EventType.EXECUTION_STARTED,
        execution_id=execution_id,
        template_key=template_key,
        app_name=app_name,
        user_id=user_id,
        data={"variables_count": len(variables) if variables else 0},
    )
    emit_event(event)
    return event


def emit_execution_completed(
    execution_id: UUID,
    template_key: str,
    duration_ms: float,
    tokens_total: int,
    cost_dollars: float,
    from_cache: bool = False,
    app_name: str = "unknown",
) -> PromptEvent:
    """Emit execution completed event."""
    event = PromptEvent(
        event_type=EventType.EXECUTION_COMPLETED,
        execution_id=execution_id,
        template_key=template_key,
        app_name=app_name,
        duration_ms=duration_ms,
        data={
            "tokens_total": tokens_total,
            "cost_dollars": cost_dollars,
            "from_cache": from_cache,
        },
    )
    emit_event(event)
    return event


def emit_execution_failed(
    execution_id: UUID,
    template_key: str,
    error_type: str,
    error_message: str,
    duration_ms: float,
    app_name: str = "unknown",
) -> PromptEvent:
    """Emit execution failed event."""
    event = PromptEvent(
        event_type=EventType.EXECUTION_FAILED,
        execution_id=execution_id,
        template_key=template_key,
        app_name=app_name,
        duration_ms=duration_ms,
        error_type=error_type,
        error_message=error_message,
    )
    emit_event(event)
    return event


def emit_injection_detected(
    template_key: str,
    variable_name: str,
    pattern_matched: str,
    app_name: str = "unknown",
    user_id: str | None = None,
) -> PromptEvent:
    """Emit security event for injection detection."""
    event = PromptEvent(
        event_type=EventType.INJECTION_DETECTED,
        template_key=template_key,
        app_name=app_name,
        user_id=user_id,
        data={
            "variable_name": variable_name,
            "pattern_matched": pattern_matched,
        },
    )
    emit_event(event)
    return event
