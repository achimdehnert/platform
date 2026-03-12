"""
Zwei-Endpoint Health-Check Pattern nach ADR-106 FIX-D.

Einbinden in config/urls.py:
    from .health import livez_view, readyz_view
    path("livez/", livez_view, name="livez"),
    path("readyz/", readyz_view, name="readyz"),

/livez/  → Liveness  (immer schnell, keine externen Calls)
/readyz/ → Readiness (DB, Redis, Migrations, Celery)
"""

from __future__ import annotations

import json
import logging
import time

from django.db import OperationalError, connection
from django.db.migrations.executor import MigrationExecutor
from django.http import HttpRequest, JsonResponse

logger = logging.getLogger(__name__)


def livez_view(request: HttpRequest) -> JsonResponse:
    """
    Liveness Probe — antwortet immer 200 wenn Django läuft.
    Kein DB-Call, kein Redis — niemals blockierend.
    """
    return JsonResponse({"status": "ok"}, status=200)


def readyz_view(request: HttpRequest) -> JsonResponse:
    """
    Readiness Probe — prüft alle externen Abhängigkeiten.
    200 = bereit für Traffic
    503 = nicht bereit, kein Traffic routen
    """
    checks: dict = {}
    all_ok = True
    start = time.monotonic()

    db_ok, db_detail = _check_database()
    checks["database"] = {"ok": db_ok, "detail": db_detail}
    if not db_ok:
        all_ok = False

    if db_ok:
        mig_ok, mig_detail = _check_migrations()
        checks["migrations"] = {"ok": mig_ok, "detail": mig_detail}
        if not mig_ok:
            all_ok = False

    redis_ok, redis_detail = _check_redis()
    if redis_ok is not None:
        checks["redis"] = {"ok": redis_ok, "detail": redis_detail}
        if not redis_ok:
            all_ok = False

    celery_ok, celery_detail = _check_celery()
    if celery_ok is not None:
        checks["celery"] = {"ok": celery_ok, "detail": celery_detail}
        if not celery_ok:
            all_ok = False

    elapsed_ms = round((time.monotonic() - start) * 1000, 1)
    payload = {
        "status": "ok" if all_ok else "degraded",
        "checks": checks,
        "elapsed_ms": elapsed_ms,
    }

    if not all_ok:
        logger.warning("Readiness check failed: %s", json.dumps(checks))

    return JsonResponse(payload, status=200 if all_ok else 503)


def _check_database() -> tuple[bool, str]:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return True, "connected"
    except OperationalError as e:
        return False, str(e)[:200]


def _check_migrations() -> tuple[bool, str]:
    try:
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        if plan:
            pending = [str(m) for m, _ in plan[:5]]
            return False, f"Pending: {pending}"
        return True, "up-to-date"
    except Exception as e:
        return False, str(e)[:200]


def _check_redis() -> tuple[bool | None, str]:
    """Gibt (None, '') zurück wenn Redis nicht konfiguriert."""
    from django.conf import settings as django_settings

    redis_url = getattr(django_settings, "REDIS_URL", None) or getattr(
        django_settings, "CELERY_BROKER_URL", None
    )
    if not redis_url:
        return None, "not configured"
    try:
        import redis

        r = redis.from_url(
            redis_url, socket_connect_timeout=2, socket_timeout=2
        )
        r.ping()
        return True, "connected"
    except Exception as e:
        return False, str(e)[:200]


def _check_celery() -> tuple[bool | None, str]:
    """Gibt (None, '') zurück wenn Celery nicht konfiguriert."""
    try:
        from config.celery import app as celery_app

        inspect = celery_app.control.inspect(timeout=2.0)
        active = inspect.ping()
        if active:
            return True, f"{len(active)} worker(s) active"
        return False, "no workers responding"
    except ImportError:
        return None, "celery not configured"
    except Exception as e:
        return False, str(e)[:200]
