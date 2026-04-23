"""
Prometheus metrics for platform_context.

Uses optional import: if prometheus_client is not installed, a no-op
stub is exposed so the middleware still works (ADR-167 v1.1: observability
is non-critical, runtime must not fail because of a missing optional dep).

Usage:
    from platform_context.metrics import HEALTH_PROBE_COUNTER
    HEALTH_PROBE_COUNTER.labels(path="/livez/", mode="sync").inc()
"""
from __future__ import annotations

from typing import Any, Protocol


class _CounterProtocol(Protocol):
    def labels(self, **kwargs: str) -> _CounterProtocol: ...
    def inc(self, amount: float = 1) -> None: ...


class _NoopCounter:
    """Silent fallback when prometheus_client is unavailable."""

    def labels(self, **kwargs: str) -> _NoopCounter:
        return self

    def inc(self, amount: float = 1) -> None:
        return None


HEALTH_PROBE_COUNTER: _CounterProtocol

try:
    from prometheus_client import Counter

    HEALTH_PROBE_COUNTER = Counter(
        "iil_health_probe_total",
        "Count of health-probe requests bypassed by HealthBypassMiddleware.",
        labelnames=("path", "mode"),
    )
except ImportError:
    HEALTH_PROBE_COUNTER = _NoopCounter()
