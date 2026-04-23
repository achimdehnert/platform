"""
Observability module for the Prompt Template System.

Provides structured events and Prometheus metrics for monitoring.
"""

from .events import (
    PromptEvent,
    EventType,
    emit_event,
    get_event_logger,
)

from .metrics import (
    PROMPT_EXECUTIONS_TOTAL,
    PROMPT_EXECUTION_DURATION,
    PROMPT_TOKENS_TOTAL,
    PROMPT_COST_TOTAL,
    PROMPT_CACHE_HITS,
    PROMPT_ERRORS_TOTAL,
    ACTIVE_EXECUTIONS,
    record_execution,
    is_prometheus_available,
)

__all__ = [
    # Events
    "PromptEvent",
    "EventType",
    "emit_event",
    "get_event_logger",
    # Metrics
    "PROMPT_EXECUTIONS_TOTAL",
    "PROMPT_EXECUTION_DURATION",
    "PROMPT_TOKENS_TOTAL",
    "PROMPT_COST_TOTAL",
    "PROMPT_CACHE_HITS",
    "PROMPT_ERRORS_TOTAL",
    "ACTIVE_EXECUTIONS",
    "record_execution",
    "is_prometheus_available",
]
