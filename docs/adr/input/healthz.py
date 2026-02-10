"""
Health endpoints for container orchestration (ADR-022).

These endpoints are exempt from authentication and tenant resolution.
They MUST be accessible without a subdomain for Docker healthchecks
and load balancer probes to function correctly.

Registration in config/urls.py:
    urlpatterns = [
        path("livez/", liveness, name="health-liveness"),
        path("healthz/", readiness, name="health-readiness"),
        # ... other patterns
    ]

The SubdomainTenantMiddleware in bfagent-core MUST exclude these paths.
See HEALTH_PATHS constant below.
"""

from django.db import connection
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

# Paths that must bypass tenant middleware (import in middleware)
HEALTH_PATHS = frozenset({"/livez/", "/healthz/"})


@csrf_exempt
@require_GET
def liveness(request):
    """
    Liveness probe: Is the process alive?

    No dependency checks — only confirms the Python process is running
    and can handle HTTP requests. Used by Docker HEALTHCHECK and
    Kubernetes liveness probes.

    Returns:
        200 {"status": "alive"}  — always, if reachable
    """
    return JsonResponse({"status": "alive"})


@csrf_exempt
@require_GET
def readiness(request):
    """
    Readiness probe: Can we serve traffic?

    Checks database connectivity. Used by load balancers and
    orchestrators to decide if traffic should be routed here.

    Returns:
        200 {"status": "healthy", "checks": {...}}  — all checks pass
        503 {"status": "unhealthy", "checks": {...}} — any check failed
    """
    checks = {}

    # --- Database connectivity ---
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = str(e)
        return JsonResponse(
            {"status": "unhealthy", "checks": checks},
            status=503,
        )

    # --- Extensible: add Redis, S3, etc. checks here ---
    # try:
    #     from django.core.cache import cache
    #     cache.set("_healthz", "1", timeout=5)
    #     checks["cache"] = "ok"
    # except Exception as e:
    #     checks["cache"] = str(e)
    #     return JsonResponse(
    #         {"status": "unhealthy", "checks": checks},
    #         status=503,
    #     )

    return JsonResponse({"status": "healthy", "checks": checks})
