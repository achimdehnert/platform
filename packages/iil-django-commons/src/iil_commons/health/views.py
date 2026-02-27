import json
import logging

from django.http import HttpRequest, HttpResponse

from iil_commons.health.checks import REGISTRY, HealthCheck
from iil_commons.settings import get_setting

logger = logging.getLogger(__name__)


def liveness(request: HttpRequest) -> HttpResponse:
    return HttpResponse(
        json.dumps({"status": "ok"}),
        content_type="application/json",
        status=200,
    )


def readiness(request: HttpRequest) -> HttpResponse:
    enabled_checks: list[str] = get_setting("HEALTH_CHECKS", ["db"])
    results: dict[str, str] = {}
    all_ok = True

    for name in enabled_checks:
        check_cls = REGISTRY.get(name)
        if check_cls is None:
            continue
        check: HealthCheck = check_cls()
        ok, detail = check.check()
        results[name] = detail if ok else f"ERROR: {detail}"
        if not ok:
            all_ok = False

    payload = {"status": "ok" if all_ok else "degraded", "checks": results}
    status_code = 200 if all_ok else 503
    return HttpResponse(
        json.dumps(payload),
        content_type="application/json",
        status=status_code,
    )
