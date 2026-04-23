import logging
import time
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)

_metrics_available = False
_request_count = None
_request_latency = None
_requests_in_progress = None

try:
    from prometheus_client import Counter, Gauge, Histogram

    _request_count = Counter(
        "http_requests_total",
        "Total HTTP requests",
        ["method", "path", "status"],
    )
    _request_latency = Histogram(
        "http_request_duration_seconds",
        "HTTP request latency",
        ["method", "path"],
    )
    _requests_in_progress = Gauge(
        "http_requests_in_progress",
        "HTTP requests currently in progress",
        ["method"],
    )
    _metrics_available = True
except ImportError:
    pass


def _normalize_path(path: str) -> str:
    """Collapse numeric path segments to reduce cardinality."""
    import re

    return re.sub(r"/\d+", "/{id}", path)


class PrometheusMiddleware:
    """Records Prometheus metrics for every HTTP request.

    Metrics:
      http_requests_total{method, path, status}
      http_request_duration_seconds{method, path}
      http_requests_in_progress{method}

    Exposes /metrics/ endpoint automatically if prometheus_client is installed.
    Add to urls.py:
        from django.urls import path
        from iil_commons.monitoring.views import metrics_view
        urlpatterns += [path("metrics/", metrics_view)]

    No-op if prometheus_client is not installed.
    """

    def __init__(self, get_response: Callable) -> None:
        self.get_response = get_response
        if not _metrics_available:
            logger.warning(
                "PrometheusMiddleware loaded but prometheus_client is not installed. "
                "Install with: pip install 'iil-django-commons[monitoring]'"
            )

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if not _metrics_available:
            return self.get_response(request)

        method = request.method or "GET"
        path = _normalize_path(request.path)

        _requests_in_progress.labels(method=method).inc()
        start = time.monotonic()
        try:
            response = self.get_response(request)
            status = str(response.status_code)
        except Exception:
            status = "500"
            raise
        finally:
            duration = time.monotonic() - start
            _requests_in_progress.labels(method=method).dec()
            _request_count.labels(method=method, path=path, status=status).inc()
            _request_latency.labels(method=method, path=path).observe(duration)

        return response
