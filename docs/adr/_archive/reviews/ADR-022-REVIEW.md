# ADR-022 v2 — Production Review

**Reviewer**: Claude (Platform Architecture Review)
**Date**: 2026-02-10
**Severity Scale**: 🔴 Critical | 🟠 High | 🟡 Medium | 🔵 Low | ✅ OK

---

## Executive Summary

ADR-022 v2 is a significant improvement over v1 — the IST-Analyse is thorough and the
generalization approach (best-of-breed from each repo) is sound. However, the ADR has
**7 critical/high findings** that must be resolved before implementation. The primary
concerns are: missing rollback strategy for the entrypoint migration, a race condition
in the health-endpoint design, contradictions with ADR-009, and unsafe `set -e` (not
`set -euo pipefail`) in the entrypoint standard.

**Verdict**: Approve with mandatory changes (Phase 0-1 can proceed immediately).

---

## 1. Architekturkonformität

### 1.1 🔴 CRITICAL — Entrypoint uses `set -e` instead of `set -euo pipefail`

**Befund**: Section 3.4 defines the standard entrypoint with `set -e`. The Platform
Architecture Master and the stated quality criteria require `set -euo pipefail` for
robust error handling. `set -e` alone does not catch:
- Undefined variables (common in env-driven config)
- Pipe failures (e.g., `command | grep` where command fails)

**Risiko**: Silent failures in production. A misspelled env var like `${GUNICORN_WORKES}`
would silently expand to empty string, and gunicorn would start with 0 workers or its
own default — violating "Fail Loud, Not Silent" (Platform Master §1.5).

**Empfehlung**: Replace entrypoint header and add explicit validation:

```bash
#!/bin/sh
set -euo pipefail

# ------------------------------------------------------------------
# Entrypoint: web | worker | beat
# Validates required env vars and runs the selected service mode.
# ------------------------------------------------------------------

# Validate required environment (fail loud, not silent)
: "${DJANGO_SETTINGS_MODULE:?DJANGO_SETTINGS_MODULE must be set}"

python manage.py migrate --noinput --skip-checks

case "${1:?Usage: entrypoint.sh [web|worker|beat]}" in
  web)
    python manage.py collectstatic --noinput 2>/dev/null || true
    exec gunicorn config.wsgi:application \
      --bind 0.0.0.0:8000 \
      --workers "${GUNICORN_WORKERS:-2}" \
      --timeout "${GUNICORN_TIMEOUT:-120}" \
      --access-logfile - \
      --error-logfile -
    ;;
  worker)
    exec celery -A config worker -l "${CELERY_LOG_LEVEL:-info}" \
      --concurrency="${CELERY_CONCURRENCY:-2}"
    ;;
  beat)
    exec celery -A config beat -l "${CELERY_LOG_LEVEL:-info}" \
      --schedule=/tmp/celerybeat-schedule
    ;;
  *)
    echo "ERROR: Unknown mode '$1'. Usage: entrypoint.sh [web|worker|beat]" >&2
    exit 1
    ;;
esac
```

**Note on `pipefail`**: If targeting pure POSIX `sh`, `pipefail` is not available.
The shebang should then be `#!/bin/bash` or use Alpine's `#!/bin/ash` (which also
doesn't support `pipefail`). For `python:3.12-slim` (Debian), `bash` is available.
Change shebang to `#!/bin/bash` to be explicit.

---

### 1.2 🔴 CRITICAL — `migrate --noinput` at container start is a race condition

**Befund**: The entrypoint runs `python manage.py migrate --noinput --skip-checks`
before starting gunicorn/celery. With multiple replicas or rolling deploys, two
containers can run migrations concurrently, causing:
- Deadlocks on the `django_migrations` table
- Partial migration state if one container crashes mid-migration

This is especially dangerous for bfagent (§2.8: `git pull + compose`) where a deploy
could restart both web and worker simultaneously.

**Risiko**: Data corruption or locked migration table during high-frequency deploys
(ADR-009 states bfagent: ~5x/day, travel-beat: ~10x/day).

**Empfehlung**: Separate migration from container startup. Two options:

**Option A (recommended)**: Dedicated migration job in compose (idempotent, run-once):

```yaml
# docker-compose.prod.yml — migration job
services:
  migrate:
    image: ghcr.io/achimdehnert/${APP_NAME}:${IMAGE_TAG:-latest}
    command: ["python", "manage.py", "migrate", "--noinput"]
    env_file: .env.prod
    depends_on:
      db:
        condition: service_healthy
    restart: "no"  # Run once, exit
    deploy:
      restart_policy:
        condition: none

  web:
    # ...
    depends_on:
      migrate:
        condition: service_completed_successfully
```

**Option B**: Advisory lock in entrypoint (simpler but less clean):

```bash
# Only run migrations if we can acquire advisory lock
python -c "
from django.db import connection
with connection.cursor() as c:
    c.execute('SELECT pg_try_advisory_lock(1)')
    if c.fetchone()[0]:
        import django.core.management
        django.core.management.call_command('migrate', '--noinput')
        c.execute('SELECT pg_advisory_unlock(1)')
    else:
        print('Migration already running, skipping')
"
```

---

### 1.3 🟠 HIGH — ADR-009 inconsistencies

**Befund**: Several contradictions with ADR-009 (Centralized Deployment Architecture):

| Dimension | ADR-009 | ADR-022 | Conflict |
|-----------|---------|---------|----------|
| Dockerfile path | `docker/Dockerfile` | `docker/app/Dockerfile` | Path mismatch |
| Workflow tag | `@main` | `@v1` | Versioning unclear |
| Health URL | `/health/` | `/livez/` + `/healthz/` | Endpoint naming |
| App list | 5 apps + cad-hub | 5 apps + mcp-hub | cad-hub vs pptx-hub |

**Risiko**: Developers won't know which ADR to follow. The `_build-docker.yml`
reusable workflow in ADR-009 specifies `dockerfile: docker/Dockerfile` as input,
but ADR-022 mandates `docker/app/Dockerfile`.

**Empfehlung**:
1. Explicitly state that ADR-022 supersedes the relevant sections of ADR-009
2. Align Dockerfile path — pick ONE. `docker/app/Dockerfile` is better for repos
   that also have `docker/nginx/Dockerfile`, so go with ADR-022's path but update
   ADR-009's `_build-docker.yml` default input
3. Add `cad-hub` to ADR-022's scope or explicitly note its retirement
4. Pin `@v1` tag and document tag-creation process in platform repo

---

### 1.4 🟠 HIGH — Missing rollback strategy

**Befund**: ADR-022 defines 5 migration phases but has zero rollback procedures.
For a platform with 10+ deploys/day, this is a significant gap. Specifically:

- Phase 2 (Dockerfile generalization): If the new multi-stage build fails, what's
  the revert path? Old Dockerfile was deleted/moved.
- Phase 4 (Server cleanup): "Erst neuen Deploy verifizieren, dann alten Source
  archivieren" — but no definition of "verifizieren" or retention period.

**Risiko**: A failed Phase 2 migration on bfagent (highest traffic) could cause
extended downtime if there's no documented rollback.

**Empfehlung**: Add rollback procedures per phase:

```
Phase 2 Rollback:
1. Keep old Dockerfile as docker/app/Dockerfile.legacy for 2 weeks
2. GHCR retains last 5 images per app (old images remain pullable)
3. Compose rollback: IMAGE_TAG=<previous-sha> docker compose up -d
4. Verification: curl -sf http://127.0.0.1:<PORT>/livez/ || rollback

Phase 4 Rollback:
1. Server source archived to /opt/<app>-archive/ (not deleted)
2. Retention: 30 days minimum
3. Emergency: cd /opt/<app>-archive && docker compose up -d
```

---

## 2. Invarianten

### 2.1 🟠 HIGH — Health endpoint has no auth bypass guarantee

**Befund**: The `healthz.py` standard (§3.6) implements `/livez/` and `/healthz/`
but doesn't address Django middleware. If `SubdomainTenantMiddleware` from
`bfagent-core` is active (as mandated for DSGVO compliance), requests to `/livez/`
without a subdomain will return `403 Forbidden` — breaking Docker healthchecks
and load balancer probes.

**Risiko**: Health probes fail → Docker marks container unhealthy → container
restarts in a loop → production outage.

**Empfehlung**: Health endpoints must be excluded from tenant middleware. Add to
the ADR's `healthz.py` standard:

```python
# apps/core/healthz.py
"""
Health endpoints for container orchestration.

These views are exempt from authentication and tenant resolution.
They MUST be registered BEFORE tenant middleware in URL routing,
or explicitly excluded in SubdomainTenantMiddleware.
"""
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def liveness(request):
    """Liveness probe: Is the process alive? No dependency checks."""
    return JsonResponse({"status": "alive"})


@csrf_exempt
def readiness(request):
    """Readiness probe: Can we serve traffic? Checks DB connectivity."""
    checks = {}
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
    return JsonResponse({"status": "healthy", "checks": checks})
```

And mandate this middleware exclusion pattern:

```python
# bfagent_core/middleware.py — required update
HEALTH_PATHS = frozenset({"/livez/", "/healthz/"})

class SubdomainTenantMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Health probes bypass tenant resolution (invariant)
        if request.path in HEALTH_PATHS:
            return None
        # ... existing tenant logic
```

---

### 2.2 🟡 MEDIUM — `env_file: .env.prod` naming is ambiguous on multi-stage servers

**Befund**: The standard mandates `env_file: .env.prod` for all apps. On the shared
Hetzner server, multiple apps run under `/opt/<app>/`. If someone accidentally copies
or symlinks `.env.prod` to the wrong directory, secrets leak between apps.

**Risiko**: Cross-app secret leakage (DSGVO Art. 32 violation for the DSB platform).

**Empfehlung**: Use app-scoped env file names:

```yaml
# Option A (preferred): Scoped filename
env_file: .env.${APP_NAME}.prod  # e.g., .env.risk-hub.prod

# Option B: Keep .env.prod but enforce directory isolation via chmod
# /opt/risk-hub/.env.prod owned by risk-hub:risk-hub, mode 0600
```

Alternatively, document a mandatory `chmod 600 .env.prod` and `chown` step in the
server provisioning script.

---

### 2.3 🟡 MEDIUM — No `CONN_MAX_AGE` in standard, but listed as optimization

**Befund**: §6 lists `CONN_MAX_AGE=600` as optimization O2 with "Keins" (no) risk.
But this should be part of the base standard, not optional. The current default of
`CONN_MAX_AGE=0` creates a new DB connection per request. At 10+ deploys/day with
production traffic, this wastes ~200ms per request on connection setup.

**Risiko**: Unnecessary latency and PostgreSQL connection churn.

**Empfehlung**: Move to §3 (SOLL-Zustand) as a mandatory settings standard:

```python
# config/settings/base.py — mandatory database settings
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        # ...
        "CONN_MAX_AGE": int(os.environ.get("DB_CONN_MAX_AGE", "600")),
        "CONN_HEALTH_CHECKS": True,  # Django 4.1+ — validates before reuse
    }
}
```

---

## 3. Seiteneffekte

### 3.1 🟠 HIGH — Shared DB (bfagent + weltenhub) creates migration coupling

**Befund**: §2.3 shows weltenhub uses `shared (bfagent_db)`. §6 lists "Shared DB
aufbrechen" as optimization O1, but this is critically underrated. With shared DB:

1. Django migrations from bfagent can lock tables weltenhub needs
2. `migrate --noinput` in both entrypoints will race on the same `django_migrations` table
3. A bad migration in one app corrupts the other's schema

This directly violates Platform Master §1.3 (Separation of Concerns).

**Risiko**: Production data corruption. Two Django apps sharing one PostgreSQL
database with their own migration histories is an anti-pattern.

**Empfehlung**: Elevate from "optimization" to **Phase 1 prerequisite**:

```yaml
# docker-compose.prod.yml — weltenhub gets its own DB
services:
  db:
    image: postgres:16-alpine
    volumes:
      - weltenhub_pgdata:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: weltenhub
      POSTGRES_USER: weltenhub
    # ...

volumes:
  weltenhub_pgdata:  # Separate volume, separate lifecycle
```

Migration procedure:
1. `pg_dump -n public bfagent_db > weltenhub_tables.sql` (only weltenhub tables)
2. Create new DB, restore
3. Update weltenhub `.env.prod` with new DB credentials
4. Remove weltenhub tables from bfagent_db after verification period (7 days)

---

### 3.2 🟡 MEDIUM — `collectstatic` in entrypoint creates race with nginx/Caddy

**Befund**: The entrypoint runs `collectstatic --noinput` at web startup. If a new
image deploys while the old container is still serving, static files could be
half-updated (old container serves new CSS but old JS, or vice versa).

**Risiko**: Brief visual glitches during deploys. Low severity but violates
idempotency principle since the result depends on timing.

**Empfehlung**: The ADR correctly moves collectstatic to build-time (§3.3: "collectstatic
bei Build-time mit Dummy-Env"). But the entrypoint (§3.4) still has it at runtime.
This is contradictory. Remove from entrypoint, keep only in Dockerfile:

```dockerfile
# In Dockerfile build stage
RUN DJANGO_SETTINGS_MODULE=config.settings.production \
    SECRET_KEY=build-dummy \
    DATABASE_URL=sqlite:///tmp/build.db \
    python manage.py collectstatic --noinput
```

And in entrypoint, remove the collectstatic line entirely:

```bash
  web)
    # collectstatic is done at build time (Dockerfile)
    exec gunicorn config.wsgi:application \
      --bind 0.0.0.0:8000 \
      # ...
```

---

### 3.3 🔵 LOW — Port registry lacks allocation strategy

**Befund**: §3.7 defines a static port map but no process for allocating ports for
new apps. The MCP-tools mentioned in §9 ("MCP-Tools brauchen konsistente Pfade,
Ports, Endpoints") need a discoverable registry, not a static ADR table.

**Empfehlung**: Define allocation rule: `8080 + (app_index * 10)` or maintain a
`platform/config/port-registry.yml` that MCP tools can parse:

```yaml
# platform/config/port-registry.yml
# Canonical port assignments — consumed by deployment-mcp
apps:
  bfagent:    { port: 8088, proxy: caddy, domain: bfagent.iil.pet }
  weltenhub:  { port: 8081, proxy: direct, domain: weltenforger.com }
  travel-beat: { port: 8089, proxy: caddy, domain: drifttales.app }
  risk-hub:   { port: 8090, proxy: direct, domain: schutztat.de }
  pptx-hub:   { port: 8020, proxy: direct, domain: prezimo.com }
```

---

## 4. Migrationsrisiken

### 4.1 🟠 HIGH — Phase 2 Python 3.11→3.12 for bfagent is under-scoped

**Befund**: §4.1 estimates "30 min" for the bfagent Dockerfile migration including
Python 3.11→3.12 upgrade. bfagent is the largest codebase with the most dependencies.
A Python minor version bump can cause:

- `asyncio` behavior changes (3.12 deprecates several patterns)
- C-extension recompilation failures (e.g., `psycopg2`, `Pillow`, `lxml`)
- `importlib` changes that affect dynamic imports
- Removal of `distutils` (fully removed in 3.12)

**Risiko**: Unpredictable build failures or runtime regressions that are not caught
in a 30-minute window.

**Empfehlung**: Separate Python upgrade from Dockerfile restructuring:

```
Phase 2a: Dockerfile restructuring (keep Python 3.11)
  - Move to docker/app/, multi-stage, non-root
  - Verify: all tests pass, image builds, deploys work
  - Duration: 30 min

Phase 2b: Python 3.11 → 3.12 upgrade (separate PR)
  - Run full test suite with 3.12
  - Check all dependencies for 3.12 compatibility
  - Test in staging for 24h before production
  - Duration: 1-2 hours + 24h soak
```

---

### 4.2 🟡 MEDIUM — Phase 4 server cleanup has no canary period

**Befund**: Phase 4 says "Erst neuen Deploy verifizieren, dann alten Source archivieren"
but defines no minimum canary period. For bfagent (DSB/DSGVO compliance system),
a failure discovered days later with no rollback source would be catastrophic.

**Empfehlung**: Define explicit canary periods:

| App | Canary Period | Verification Criteria |
|-----|--------------|----------------------|
| bfagent | 14 days | No 5xx errors, all scheduled tasks completed |
| risk-hub | 7 days | Health checks green, all API endpoints tested |
| travel-beat | 7 days | Health checks green |
| weltenhub | 7 days | Health checks green |
| pptx-hub | 3 days | Health checks green |

---

### 4.3 🟡 MEDIUM — travel-beat Postgres 15→16 marked "Niedrig" but requires dump/restore

**Befund**: §4.3 lists "Postgres 15 zu 16" with priority "Niedrig" and effort
"DB-Dump". A major Postgres version upgrade requires `pg_dumpall` + restore, since
in-place upgrade is not supported with Docker volumes. Downtime is required.

**Risiko**: Data loss if dump/restore is done incorrectly. Marking as "Niedrig"
may lead to it being done casually.

**Empfehlung**: Elevate to "Mittel" priority and document the procedure:

```bash
#!/bin/bash
set -euo pipefail

# travel-beat-pg-upgrade.sh
# Upgrades PostgreSQL 15 → 16 with full backup and verification

APP="travel-beat"
OLD_CONTAINER="${APP}-db-1"
BACKUP_FILE="/opt/${APP}/backups/pg15-final-$(date +%Y%m%d_%H%M%S).sql.gz"

echo "=== Step 1: Stop application ==="
cd /opt/${APP}
docker compose stop web worker beat 2>/dev/null || true

echo "=== Step 2: Full backup ==="
docker compose exec -T db pg_dumpall -U postgres | gzip > "${BACKUP_FILE}"
echo "Backup: ${BACKUP_FILE} ($(du -h "${BACKUP_FILE}" | cut -f1))"

echo "=== Step 3: Verify backup ==="
gunzip -t "${BACKUP_FILE}" || { echo "ERROR: Backup corrupted"; exit 1; }

echo "=== Step 4: Stop and remove old DB ==="
docker compose down db
docker volume ls | grep "${APP}" | grep pgdata  # Show volume name

echo "=== Step 5: Update compose to pg16, start new DB ==="
# (Manual step: update image tag in docker-compose.prod.yml)
docker compose up -d db
sleep 5  # Wait for PG to initialize

echo "=== Step 6: Restore ==="
gunzip -c "${BACKUP_FILE}" | docker compose exec -T db psql -U postgres

echo "=== Step 7: Verify ==="
docker compose exec -T db psql -U postgres -c "SELECT version();"
docker compose exec -T db psql -U postgres -c "SELECT count(*) FROM pg_tables WHERE schemaname='public';"

echo "=== Step 8: Restart application ==="
docker compose up -d

echo "=== Done. Monitor /livez/ and /healthz/ ==="
```

---

## 5. Additional Findings

### 5.1 🟡 MEDIUM — Compliance checklist missing DSGVO-specific items

**Befund**: §8 has 13 compliance checkpoints, but none address DSGVO requirements
that are central to the platform's purpose:

- No check for RLS (Row-Level Security) enablement
- No check for audit logging (bfagent-core provides `emit_audit_event`)
- No check for TLS between containers (currently all localhost, acceptable)

**Empfehlung**: Add DSGVO-relevant items to the checklist:

```
[ ] Database: Separate DB instance per app (no shared DB)
[ ] Tenancy: SubdomainTenantMiddleware active (if multi-tenant)
[ ] Audit: bfagent-core audit middleware installed
[ ] Backup: Automated daily pg_dump with 30-day retention
```

---

### 5.2 🔵 LOW — Missing `--error-logfile -` in gunicorn config

**Befund**: The entrypoint has `--access-logfile -` but not `--error-logfile -`.
Gunicorn errors would go to stderr by default (which Docker captures), but being
explicit is better practice and aligns with "Fail Loud" principle.

---

### 5.3 🔵 LOW — Healthcheck `python urllib` not fully specified

**Befund**: §3.5 mandates "python urllib auf /livez/ (kein curl)" but doesn't
provide the actual Dockerfile HEALTHCHECK command.

**Empfehlung**: Standardize this one-liner:

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/livez/')" \
  || exit 1
```

---

## 6. Review Summary

| # | Finding | Severity | Section | Action |
|---|---------|----------|---------|--------|
| 1.1 | `set -e` statt `set -euo pipefail` | 🔴 Critical | §3.4 | Fix entrypoint |
| 1.2 | migrate race condition | 🔴 Critical | §3.4 | Separate migration job |
| 1.3 | ADR-009 contradictions | 🟠 High | §3.2 | Align or supersede |
| 1.4 | No rollback strategy | 🟠 High | §7 | Add per-phase rollback |
| 2.1 | Health probe blocked by tenant MW | 🟠 High | §3.6 | MW exemption |
| 3.1 | Shared DB is anti-pattern | 🟠 High | §6/O1 | Elevate to Phase 1 |
| 4.1 | Python 3.11→3.12 under-scoped | 🟠 High | §4.1 | Split into 2a/2b |
| 2.2 | `.env.prod` cross-app risk | 🟡 Medium | §3.5 | Scope or chmod |
| 2.3 | `CONN_MAX_AGE` should be standard | 🟡 Medium | §6/O2 | Move to §3 |
| 3.2 | collectstatic contradiction | 🟡 Medium | §3.3/§3.4 | Remove from entrypoint |
| 4.2 | No canary period defined | 🟡 Medium | §7 | Add table |
| 4.3 | PG 15→16 underestimated | 🟡 Medium | §4.3 | Elevate + script |
| 5.1 | Missing DSGVO checklist items | 🟡 Medium | §8 | Add items |
| 3.3 | No port allocation strategy | 🔵 Low | §3.7 | Registry file |
| 5.2 | Missing gunicorn error-logfile | 🔵 Low | §3.4 | Add flag |
| 5.3 | HEALTHCHECK not fully specified | 🔵 Low | §3.5 | Add Dockerfile line |

**Blocking**: Items 1.1, 1.2, 1.3, 2.1, 3.1 must be resolved before Phase 2 begins.
Phase 0 (security) and Phase 1 (compose hygiene) can proceed as-is.
