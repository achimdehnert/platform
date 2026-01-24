"""
Core Views
==========

Health checks and utility views.
"""

import sys

from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


@never_cache
@require_GET
def health_check(request):
    """
    Health check endpoint for monitoring.

    Returns JSON with:
    - database: Database connection status
    - cache: Cache connection status
    - status: Overall health status

    Status codes:
    - 200: Healthy
    - 503: Unhealthy

    Usage:
        curl https://yourdomain.com/health/
    """
    checks = {
        "database": False,
        "cache": False,
        "status": "unhealthy",
        "version": "1.0.0",
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    }

    # Check Database Connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            checks["database"] = result[0] == 1
    except Exception as e:
        checks["database_error"] = str(e)

    # Check Cache Connection
    try:
        test_key = "health_check_test"
        test_value = "ok"
        cache.set(test_key, test_value, 10)
        checks["cache"] = cache.get(test_key) == test_value
        cache.delete(test_key)
    except Exception as e:
        checks["cache_error"] = str(e)

    # Overall Status
    checks["status"] = "healthy" if all([checks["database"], checks["cache"]]) else "unhealthy"

    # HTTP Status Code
    status_code = 200 if checks["status"] == "healthy" else 503

    return JsonResponse(checks, status=status_code)


@never_cache
@require_GET
def readiness_check(request):
    """
    Kubernetes-style readiness check.

    Returns 200 if app is ready to serve traffic.
    """
    try:
        # Quick database check
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        return JsonResponse({"ready": True}, status=200)
    except Exception:
        return JsonResponse({"ready": False}, status=503)


@never_cache
@require_GET
def liveness_check(request):
    """
    Kubernetes-style liveness check.

    Returns 200 if app is alive (even if not ready).
    """
    return JsonResponse({"alive": True}, status=200)
