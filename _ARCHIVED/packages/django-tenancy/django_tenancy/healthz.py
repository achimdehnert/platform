"""Health check endpoints for container orchestration (ADR-022).

These endpoints are exempt from authentication and tenant resolution.
They MUST be accessible without a subdomain for Docker healthchecks
and load balancer probes to function correctly.

Registration in config/urls.py::

    from django_tenancy.healthz import HEALTH_PATHS, liveness, readiness

    urlpatterns = [
        path("livez/", liveness, name="health-liveness"),
        path("healthz/", readiness, name="health-readiness"),
        path("health/", readiness, name="health-compat"),
    ]

The SubdomainTenantMiddleware MUST exclude HEALTH_PATHS.
"""

from __future__ import annotations

import time

from django.db import connection
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

HEALTH_PATHS = frozenset({"/livez/", "/healthz/", "/health/"})


@csrf_exempt
@require_GET
def liveness(request) -> JsonResponse:
    """Liveness probe: process is running. No dependency checks."""
    return JsonResponse({"status": "alive"})


@csrf_exempt
@require_GET
def readiness(request) -> JsonResponse:
    """Readiness probe: all dependencies healthy, ready to serve.

    Checks database connectivity and optionally Redis.
    Returns 200 if all checks pass, 503 otherwise.
    """
    checks: dict = {}
    healthy = True

    # Database check
    try:
        t0 = time.monotonic()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        latency_ms = round((time.monotonic() - t0) * 1000, 1)
        checks["database"] = {"status": "ok", "latency_ms": latency_ms}
    except Exception as exc:
        checks["database"] = {"status": "fail", "error": str(exc)[:200]}
        healthy = False

    # Redis check (optional — only if django cache is configured)
    try:
        from django.core.cache import cache

        t0 = time.monotonic()
        cache.set("_healthz", "ok", timeout=5)
        val = cache.get("_healthz")
        latency_ms = round((time.monotonic() - t0) * 1000, 1)
        if val == "ok":
            checks["redis"] = {"status": "ok", "latency_ms": latency_ms}
        else:
            checks["redis"] = {"status": "fail", "error": "read mismatch"}
            healthy = False
    except Exception as exc:
        # Redis not configured or unavailable — not a hard failure
        # if cache backend is LocMemCache or similar
        error_str = str(exc)[:200]
        if "LocMemCache" not in error_str and "DummyCache" not in error_str:
            checks["redis"] = {"status": "fail", "error": error_str}
            healthy = False

    payload = {"status": "ok" if healthy else "fail", "checks": checks}
    return JsonResponse(payload, status=200 if healthy else 503)
