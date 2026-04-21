---
status: Accepted
date: 2026-04-21
decision-makers: Achim Dehnert, Cascade AI
consulted: []
informed: []
implementation_status: partial
implementation_evidence:
  - "platform_context v0.6.0: HealthBypassMiddleware + SubdomainTenantMiddleware health bypass (22 tests)"
  - "Phase 1 rollout: 9/19 repos committed + pushed (risk-hub, bfagent, billing-hub, coach-hub, tax-hub, wedding-hub, writing-hub, pptx-hub, trading-hub)"
  - "tax-hub + trading-hub: local HealthCheckMiddleware replaced with central one"
---

<!-- Drift-Detector-Felder
staleness_months: 12
drift_check_paths:
  - packages/platform-context/src/platform_context/middleware.py
  - packages/platform-context/tests/test_middleware.py
supersedes_check: null
-->

# ADR-167: Adopt 3-Tier Middleware Standard for Health Probes and Tenant Resolution

## Context and Problem Statement

19 Django repositories have divergent middleware stacks. Health-check bypasses
were implemented individually in travel-beat (`HealthBypassTenantMiddleware`),
research-hub (`EXEMPT_PATH_PREFIXES`), and bfagent (`.env.prod` hack).
`ALLOWED_HOSTS` fixes had to be applied across 20 files in 19 repos.

There is no standard that defines which middleware a repository must include
and in what order, leading to inconsistent behavior for health probes,
tenant resolution, and request context.

## Decision Drivers

- **Consistency**: Health probes (`/livez/`, `/healthz/`) must work identically in all 19 repos
- **Defense in Depth**: Docker/LB health checks must bypass all downstream middleware (auth, CSRF, tenant)
- **DRY**: Per-repo health bypass hacks (3 different implementations) violate single-source-of-truth
- **Onboarding**: New repos should get health probes by adding one middleware line
- **Tenant Compatibility**: Multi-tenant repos (Tier 2/3) must not reject health probes for missing subdomain

## Considered Options

### Option A: Per-repo health views (status quo)

Each repo defines its own `/livez/` and `/healthz/` views in `urls.py`.
Tenant middleware must be individually patched to exempt health paths.

- Good: No shared dependency required
- Bad: 19 different implementations, 3 different bypass hacks
- Bad: Every new repo must rediscover the health probe pattern
- Bad: Tenant middleware changes require per-repo fixes

### Option B: Central `HealthBypassMiddleware` in `platform_context` (chosen)

A single middleware class in `platform_context.middleware` short-circuits
health probe paths before any downstream middleware runs.

- Good: Single source of truth — one middleware class, 22 tests
- Good: Works with all tenant tiers (bypass happens before tenant resolution)
- Good: Configurable via `settings.HEALTH_PROBE_PATHS`
- Good: Repos can still define custom DB-checking health views on different paths
- Bad: Requires `iil-platform-context >= 0.6.0` as dependency
- Bad: Middleware intercepts all configured health paths — repos that need DB readiness checks must use a separate path (e.g., `/readyz-db/`)

### Option C: Nginx-level health bypass

Configure Nginx to return 200 for health paths without proxying to Django.

- Good: Zero Django changes
- Bad: Health probe doesn't verify Django is running (defeats the purpose)
- Bad: Nginx config is not in repo — drift risk
- Bad: No readiness check (DB connectivity) possible

## Decision Outcome

**Chosen option: B — Central `HealthBypassMiddleware`**, because it provides
a single source of truth that works across all tenant tiers while keeping
health probes fast (no DB, no auth) and configurable.

### Implementation

Introduce a **3-Tier Middleware Standard** implemented in `platform_context`
(package `iil-platform-context >= 0.6.0`).

#### Tier 1: Platform Base (all repos)

Every Django repository MUST include `HealthBypassMiddleware` as the **first**
middleware. This ensures `/livez/`, `/healthz/`, `/readyz/`, `/health/` always
return HTTP 200 without touching the database, auth, or tenant resolution.

```python
MIDDLEWARE = [
    "platform_context.middleware.HealthBypassMiddleware",  # FIRST — ADR-167
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
```

#### Tier 2: Tenant-Aware (subdomain-based RLS, no schema isolation)

Repos that need subdomain → `tenant_id` resolution via RLS (Row-Level Security)
add `SubdomainTenantMiddleware` after `HealthBypassMiddleware`.
Health paths are automatically bypassed (built-in since v0.6.0).

Tier 2 is chosen over Tier 3 when the app uses a **single shared schema**
with RLS policies (e.g., `SET app.tenant_id`) rather than per-tenant
PostgreSQL schemas.

```python
MIDDLEWARE = [
    "platform_context.middleware.HealthBypassMiddleware",       # Tier 1
    "platform_context.middleware.SubdomainTenantMiddleware",    # Tier 2
    "django.middleware.security.SecurityMiddleware",
    ...
]
```

#### Tier 3: Schema Isolation (django-tenants)

Repos using `django-tenants` for per-tenant PostgreSQL schemas use
`TenantMainMiddleware`. `HealthBypassMiddleware` (first) ensures health
probes bypass schema resolution.

Tier 3 is chosen when the app requires **full schema isolation** per tenant
(separate tables, migrations, data) — typically for apps with complex
multi-tenant data models or regulatory isolation requirements.

```python
MIDDLEWARE = [
    "platform_context.middleware.HealthBypassMiddleware",                 # Tier 1
    "django_tenants.middleware.main.TenantMainMiddleware",               # Tier 3
    "platform_context.tenant_utils.middleware.TenantPropagationMiddleware",
    ...
]
```

### Tier Assignment

| Tier | Repos | Rationale |
|------|-------|-----------|
| 1 | pptx-hub, illustration-hub, billing-hub, writing-hub, wedding-hub, recruiting-hub, dms-hub, coach-hub, dev-hub, learn-hub, trading-hub | Single-purpose or no multi-tenant data model |
| 2 | risk-hub, bfagent, ausschreibungs-hub | Subdomain-based tenancy with RLS (ADR-161), single shared schema |
| 3 | travel-beat, tax-hub, cad-hub, weltenhub, research-hub | Full `django-tenants` schema isolation (ADR-072) |

### `HealthBypassMiddleware` Details

- Short-circuits requests to `HEALTH_PROBE_PATHS` with `{"status": "ok"}`
- Default paths: `/livez/`, `/healthz/`, `/readyz/`, `/health/`
- Configurable via `settings.HEALTH_PROBE_PATHS` (frozenset)
- No database access, no auth, no tenant resolution
- 22 unit tests in `platform-context/tests/test_middleware.py`

### Readiness Probes with DB Checks

Because `HealthBypassMiddleware` intercepts all configured health paths
**before** the Django URL resolver, per-repo DB-checking readiness views
(e.g., `/healthz/` that runs `SELECT 1`) will be bypassed.

**Workaround**: Repos that need a DB readiness check should:
1. Remove `/healthz/` from `HEALTH_PROBE_PATHS` in their settings, OR
2. Use a separate endpoint (e.g., `/readyz-db/`) not in the middleware's path set

The default middleware `/healthz/` response is sufficient for Docker/LB
liveness probes. DB readiness is better checked by the Docker `healthcheck`
command in `docker-compose.prod.yml`.

### Defense in Depth: `ALLOWED_HOSTS`

The `ALLOWED_HOSTS` defensive snippet (ADR-021) remains in all repos as backup:

```python
# ADR-021: Internal hosts for Docker/LB health probes — always present
ALLOWED_HOSTS.extend(h for h in ("localhost", "127.0.0.1") if h not in ALLOWED_HOSTS)
```

This ensures `Host: localhost` is always accepted, even if `HealthBypassMiddleware`
is misconfigured or not yet deployed.

## Consequences

### Good

- **Consistent behavior**: Health probes work identically across all 19 repos
- **Single source of truth**: Middleware logic lives in `platform_context`, not per-repo
- **Onboarding**: New repos get health probes by adding one middleware line
- **Eliminates hacks**: travel-beat's custom `HealthBypassTenantMiddleware`,
  research-hub's `EXEMPT_PATH_PREFIXES`, bfagent's `.env.prod` edit all become obsolete
- **Tenant-safe**: Both `SubdomainTenantMiddleware` and `TenantMainMiddleware`
  are bypassed for health paths

### Bad

- Repos must depend on `iil-platform-context >= 0.6.0` (10 repos need Dockerfile changes)
- Custom health views in repos are bypassed — need separate path or config override
- Phase 2 rollout requires Dockerfile changes for repos without `platform_context`

### Confirmation

Compliance is verified by:

1. **Automated**: `curl -s -o /dev/null -w "%{http_code}" -H "Host: localhost" http://127.0.0.1:<port>/livez/` returns `200` for all deployed repos
2. **CI**: `grep -q "HealthBypassMiddleware" <settings_file>` in repo CI or Drift-Detector
3. **Manual**: `MIDDLEWARE[0]` in each repo's settings must be `"platform_context.middleware.HealthBypassMiddleware"`

## Migration Tracking

| Phase | Repo | Status | Date |
|-------|------|--------|------|
| 1 | risk-hub | ✅ Done | 2026-04-21 |
| 1 | bfagent | ✅ Done | 2026-04-21 |
| 1 | billing-hub | ✅ Done | 2026-04-21 |
| 1 | coach-hub | ✅ Done | 2026-04-21 |
| 1 | tax-hub | ✅ Done (replaced local) | 2026-04-21 |
| 1 | wedding-hub | ✅ Done | 2026-04-21 |
| 1 | writing-hub | ✅ Done | 2026-04-21 |
| 1 | pptx-hub | ✅ Done | 2026-04-21 |
| 1 | trading-hub | ✅ Done (replaced local) | 2026-04-21 |
| 2 | ausschreibungs-hub | ⬜ Pending | — |
| 2 | cad-hub | ⬜ Pending | — |
| 2 | dev-hub | ⬜ Pending | — |
| 2 | dms-hub | ⬜ Pending | — |
| 2 | illustration-hub | ⬜ Pending | — |
| 2 | learn-hub | ⬜ Pending | — |
| 2 | recruiting-hub | ⬜ Pending | — |
| 2 | research-hub | ⬜ Pending | — |
| 2 | travel-beat | ⬜ Pending | — |
| 2 | weltenhub | ⬜ Pending | — |

## Open Questions

1. **PyPI Publish**: When to publish `iil-platform-context` to GitHub Packages PyPI?
   This would eliminate the git-clone-from-monorepo pattern in Dockerfiles.
   Deferred — tracked as Phase 3 in a future ADR.
2. **Readiness Probe Standardization**: Should all repos use `/readyz-db/` for DB checks
   or should we make `HEALTH_PROBE_PATHS` configurable per-repo? Current decision:
   per-repo `HEALTH_PROBE_PATHS` override via settings is sufficient.

## More Information

- **ADR-021**: Health Probes — defines `/livez/` + `/healthz/` convention
- **ADR-056**: Multi-Tenancy — `TenantPropagationMiddleware` for service-to-service calls
- **ADR-072**: Schema Isolation — `django-tenants` for Tier 3 repos
- **ADR-146**: Platform Packages — `iil-platform-context` as shared package
- **ADR-161**: RLS Policies — Row-Level Security for Tier 2 repos
- **Implementation**: `platform/packages/platform-context/src/platform_context/middleware.py`
- **Tests**: `platform/packages/platform-context/tests/test_middleware.py` (22 tests)
