"""
ReadinessView — DB-checking readiness endpoint for Django repos.

OPT-IN: include in a repo's root urls.py:

    from django.urls import include, path
    urlpatterns = [
        ...,
        path("readyz/", include("platform_context.health.urls")),
    ]

Design:
    - Runs ``SELECT 1`` on default DB connection (cheap, forces connection pool).
    - Optionally checks additional callables registered via
      settings.HEALTH_READINESS_CHECKS.
    - Returns 200 if ALL checks pass, 503 otherwise.

References:
    - ADR-167 v1.1 § Readiness Probes
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from django.conf import settings
from django.db import OperationalError, connections
from django.http import HttpRequest, JsonResponse
from django.utils.module_loading import import_string
from django.views import View

logger = logging.getLogger("platform_context.health")

CheckResult = tuple[str, bool, str]
SyncCheck = Callable[[], CheckResult]


def _check_default_db() -> CheckResult:
    """Ping the default database connection with SELECT 1."""
    try:
        conn = connections["default"]
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            row = cursor.fetchone()
        if row == (1,):
            return ("db.default", True, "SELECT 1 OK")
        return ("db.default", False, f"Unexpected row: {row!r}")
    except OperationalError as exc:
        return ("db.default", False, f"OperationalError: {exc}")
    except Exception as exc:  # noqa: BLE001 — deliberately broad for health
        return ("db.default", False, f"{type(exc).__name__}: {exc}")


def _resolve_user_checks() -> list[SyncCheck]:
    """Load settings.HEALTH_READINESS_CHECKS (list of dotted paths to callables)."""
    dotted_paths: list[str] = getattr(settings, "HEALTH_READINESS_CHECKS", [])
    resolved: list[SyncCheck] = []
    for dotted in dotted_paths:
        try:
            resolved.append(import_string(dotted))
        except ImportError as exc:
            logger.error("health.readiness_check.import_failed dotted=%s err=%s", dotted, exc)
            resolved.append(
                lambda dotted=dotted, exc=exc: (  # type: ignore[misc]
                    dotted,
                    False,
                    f"Import failed: {exc}",
                )
            )
    return resolved


class ReadinessView(View):
    """Readiness endpoint. Runs DB check + user-registered checks."""

    http_method_names = ["get", "head"]

    def get(self, request: HttpRequest) -> JsonResponse:
        return self._render(self._run_all_checks())

    @staticmethod
    def _run_all_checks() -> list[CheckResult]:
        results: list[CheckResult] = [_check_default_db()]
        for check in _resolve_user_checks():
            try:
                results.append(check())
            except Exception as exc:  # noqa: BLE001
                results.append((
                    getattr(check, "__name__", "user_check"),
                    False,
                    f"{type(exc).__name__}: {exc}",
                ))
        return results

    @staticmethod
    def _render(results: list[CheckResult]) -> JsonResponse:
        payload: dict[str, Any] = {
            "status": "ok" if all(ok for _, ok, _ in results) else "degraded",
            "checks": [{"name": n, "ok": ok, "detail": d} for n, ok, d in results],
        }
        status_code = 200 if payload["status"] == "ok" else 503
        response = JsonResponse(payload, status=status_code)
        response["Cache-Control"] = "no-store"
        return response
