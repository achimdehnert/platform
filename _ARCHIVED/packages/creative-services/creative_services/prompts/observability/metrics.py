"""
Prometheus metrics for prompt executions.

Metrics are optional - if prometheus_client is not installed,
this module provides no-op implementations.
"""

from contextlib import contextmanager
from typing import Any, Generator

# Try to import prometheus_client, provide no-ops if not available
try:
    from prometheus_client import Counter, Histogram, Gauge

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

    # No-op implementations
    class _NoOpMetric:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def labels(self, *args: Any, **kwargs: Any) -> "_NoOpMetric":
            return self

        def inc(self, amount: float = 1) -> None:
            pass

        def dec(self, amount: float = 1) -> None:
            pass

        def set(self, value: float) -> None:
            pass

        def observe(self, value: float) -> None:
            pass

    Counter = _NoOpMetric  # type: ignore
    Histogram = _NoOpMetric  # type: ignore
    Gauge = _NoOpMetric  # type: ignore


# === Counters ===

PROMPT_EXECUTIONS_TOTAL = Counter(
    "prompt_executions_total",
    "Total number of prompt executions",
    ["template_key", "app_name", "status"],
)

PROMPT_TOKENS_TOTAL = Counter(
    "prompt_tokens_total",
    "Total tokens used in prompt executions",
    ["template_key", "app_name", "token_type"],  # token_type: input, output
)

PROMPT_COST_TOTAL = Counter(
    "prompt_cost_dollars_total",
    "Total cost in dollars for prompt executions",
    ["template_key", "app_name", "llm_provider"],
)

PROMPT_CACHE_HITS = Counter(
    "prompt_cache_hits_total",
    "Total cache hits for prompt executions",
    ["template_key", "app_name"],
)

PROMPT_ERRORS_TOTAL = Counter(
    "prompt_errors_total",
    "Total errors in prompt executions",
    ["template_key", "app_name", "error_type"],
)


# === Histograms ===

PROMPT_EXECUTION_DURATION = Histogram(
    "prompt_execution_duration_seconds",
    "Duration of prompt executions in seconds",
    ["template_key", "app_name"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0),
)


# === Gauges ===

ACTIVE_EXECUTIONS = Gauge(
    "prompt_active_executions",
    "Number of currently active prompt executions",
    ["app_name"],
)


# === Helper Functions ===


def record_execution(
    template_key: str,
    app_name: str,
    status: str,
    duration_seconds: float,
    tokens_input: int = 0,
    tokens_output: int = 0,
    cost_dollars: float = 0.0,
    llm_provider: str = "unknown",
    from_cache: bool = False,
    error_type: str | None = None,
) -> None:
    """
    Record metrics for a completed prompt execution.

    Args:
        template_key: Template that was executed
        app_name: Application name
        status: Execution status (success, failed, cached)
        duration_seconds: Execution duration
        tokens_input: Input tokens used
        tokens_output: Output tokens generated
        cost_dollars: Cost in dollars
        llm_provider: LLM provider used
        from_cache: Whether result was from cache
        error_type: Error type if failed
    """
    # Execution count
    PROMPT_EXECUTIONS_TOTAL.labels(
        template_key=template_key,
        app_name=app_name,
        status=status,
    ).inc()

    # Duration
    PROMPT_EXECUTION_DURATION.labels(
        template_key=template_key,
        app_name=app_name,
    ).observe(duration_seconds)

    # Tokens
    if tokens_input > 0:
        PROMPT_TOKENS_TOTAL.labels(
            template_key=template_key,
            app_name=app_name,
            token_type="input",
        ).inc(tokens_input)

    if tokens_output > 0:
        PROMPT_TOKENS_TOTAL.labels(
            template_key=template_key,
            app_name=app_name,
            token_type="output",
        ).inc(tokens_output)

    # Cost
    if cost_dollars > 0:
        PROMPT_COST_TOTAL.labels(
            template_key=template_key,
            app_name=app_name,
            llm_provider=llm_provider,
        ).inc(cost_dollars)

    # Cache hits
    if from_cache:
        PROMPT_CACHE_HITS.labels(
            template_key=template_key,
            app_name=app_name,
        ).inc()

    # Errors
    if error_type:
        PROMPT_ERRORS_TOTAL.labels(
            template_key=template_key,
            app_name=app_name,
            error_type=error_type,
        ).inc()


@contextmanager
def track_active_execution(app_name: str) -> Generator[None, None, None]:
    """
    Context manager to track active executions.

    Usage:
        with track_active_execution("my_app"):
            # execution code
    """
    ACTIVE_EXECUTIONS.labels(app_name=app_name).inc()
    try:
        yield
    finally:
        ACTIVE_EXECUTIONS.labels(app_name=app_name).dec()


def is_prometheus_available() -> bool:
    """Check if Prometheus client is available."""
    return PROMETHEUS_AVAILABLE
