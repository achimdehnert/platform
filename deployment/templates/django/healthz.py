"""
Health check views for Django SaaS apps on Docker/Hetzner.

Provides two endpoints:
  /livez/   — Liveness probe  (is the process alive?)
  /healthz/ — Readiness probe (can it serve traffic?)

Usage in urls.py:
    from deployment.healthz import liveness, readiness

    urlpatterns = [
        path("livez/",   liveness,  name="liveness"),
        path("healthz/", readiness, name="healthz"),
    ]

The readiness probe checks DB, Redis, disk, and pending migrations.
Returns HTTP 200 when healthy, HTTP 503 when not.
"""

import time

from django.conf import settings
from django.db import connection
from django.http import JsonResponse


def liveness(request):
    """Liveness probe: process is running. No dependency checks."""
    return JsonResponse({"status": "alive"}, status=200)


def readiness(request):
    """Readiness probe: all dependencies healthy, ready to serve."""
    checks = {}
    healthy = True

    # ── Database ─────────────────────────────────────────────────
    try:
        t0 = time.monotonic()
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
        latency = round((time.monotonic() - t0) * 1000, 1)
        checks["database"] = {"status": "ok", "latency_ms": latency}
    except Exception as exc:
        checks["database"] = {"status": "fail", "error": str(exc)[:200]}
        healthy = False

    # ── Redis (optional) ─────────────────────────────────────────
    redis_url = getattr(settings, "REDIS_URL", None) or getattr(
        settings, "CACHES", {}
    ).get("default", {}).get("LOCATION", "")
    if redis_url and redis_url.startswith("redis"):
        try:
            import redis as redis_lib

            t0 = time.monotonic()
            r = redis_lib.from_url(redis_url, socket_timeout=2)
            r.ping()
            latency = round((time.monotonic() - t0) * 1000, 1)
            checks["redis"] = {"status": "ok", "latency_ms": latency}
        except Exception as exc:
            checks["redis"] = {"status": "fail", "error": str(exc)[:200]}
            healthy = False

    # ── Disk ─────────────────────────────────────────────────────
    try:
        import shutil

        total, _used, free = shutil.disk_usage("/")
        pct_free = round(free / total * 100, 1)
        if pct_free > 5:
            disk_status = "ok"
        elif pct_free > 2:
            disk_status = "warn"
        else:
            disk_status = "fail"
        checks["disk"] = {"status": disk_status, "free_pct": pct_free}
        if disk_status == "fail":
            healthy = False
    except Exception:
        pass

    # ── Pending migrations ───────────────────────────────────────
    try:
        from django.core.management import call_command
        from io import StringIO

        out = StringIO()
        call_command("showmigrations", "--plan", stdout=out, no_color=True)
        pending = out.getvalue().count("[ ]")
        checks["migrations"] = {
            "status": "ok" if pending == 0 else "warn",
            "pending": pending,
        }
    except Exception:
        pass

    # ── Build info ───────────────────────────────────────────────
    version = getattr(settings, "VERSION", "unknown")
    git_sha = getattr(settings, "GIT_SHA", "unknown")

    payload = {
        "status": "ok" if healthy else "fail",
        "version": version,
        "git_sha": git_sha,
        "checks": checks,
    }
    return JsonResponse(payload, status=200 if healthy else 503)
