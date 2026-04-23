import logging
import time

from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from iil_commons.health.checks import REGISTRY, HealthCheck
from iil_commons.settings import get_setting

logger = logging.getLogger(__name__)

HEALTH_PATHS = frozenset({"/livez/", "/healthz/", "/readyz/", "/health/"})


@csrf_exempt
@require_GET
def liveness(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "alive"})


@csrf_exempt
@require_GET
def readiness(request: HttpRequest) -> JsonResponse:
    enabled_checks: list[str] = get_setting("HEALTH_CHECKS", ["db"])
    results: dict = {}
    all_ok = True

    for name in enabled_checks:
        check_cls = REGISTRY.get(name)
        if check_cls is None:
            continue
        check: HealthCheck = check_cls()
        t0 = time.monotonic()
        ok, detail = check.check()
        latency_ms = round((time.monotonic() - t0) * 1000, 1)
        if ok:
            results[name] = {"status": "ok", "latency_ms": latency_ms}
        else:
            results[name] = {"status": "fail", "error": detail[:200]}
            all_ok = False

    payload = {"status": "ok" if all_ok else "fail", "checks": results}
    return JsonResponse(payload, status=200 if all_ok else 503)
