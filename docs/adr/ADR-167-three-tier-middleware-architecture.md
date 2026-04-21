# ADR-167: 3-Tier Middleware Architecture

- **Status:** Accepted
- **Date:** 2026-04-21
- **Deciders:** Achim Dehnert, Cascade AI
- **Relates to:** ADR-021 (Health Probes), ADR-056 (Multi-Tenancy), ADR-146 (Platform Packages)

## Context and Problem Statement

19 Django repositories have divergent middleware stacks. Health-check bypasses
were implemented individually in travel-beat (`HealthBypassTenantMiddleware`),
research-hub (`EXEMPT_PATH_PREFIXES`), and bfagent (`.env.prod` hack).
`ALLOWED_HOSTS` fixes had to be applied across 20 files in 19 repos.

There is no standard that defines which middleware a repository must include
and in what order, leading to inconsistent behavior for health probes,
tenant resolution, and request context.

## Decision

Introduce a **3-Tier Middleware Standard** implemented in `platform_context`
(package `iil-platform-context >= 0.6.0`).

### Tier 1: Platform Base (all repos)

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

### Tier 2: Tenant-Aware (subdomain-based RLS, no schema isolation)

Repos that need subdomain → `tenant_id` resolution via RLS (Row-Level Security)
add `SubdomainTenantMiddleware` after `HealthBypassMiddleware`.
Health paths are automatically bypassed.

```python
MIDDLEWARE = [
    "platform_context.middleware.HealthBypassMiddleware",       # Tier 1
    "platform_context.middleware.SubdomainTenantMiddleware",    # Tier 2
    "django.middleware.security.SecurityMiddleware",
    ...
]
```

### Tier 3: Schema Isolation (django-tenants)

Repos using `django-tenants` for per-tenant PostgreSQL schemas replace
`SubdomainTenantMiddleware` with `TenantMainMiddleware` (or a custom
subclass). Health paths must still be bypassed — either via
`HealthBypassMiddleware` (first) or the custom tenant middleware's
built-in health bypass.

```python
MIDDLEWARE = [
    "platform_context.middleware.HealthBypassMiddleware",                 # Tier 1
    "django_tenants.middleware.main.TenantMainMiddleware",               # Tier 3
    "platform_context.tenant_utils.middleware.TenantPropagationMiddleware",
    ...
]
```

## Tier Assignment

| Tier | Repos |
|------|-------|
| 1 | pptx-hub, illustration-hub, billing-hub, writing-hub, wedding-hub, recruiting-hub, dms-hub, coach-hub, dev-hub, learn-hub, trading-hub |
| 2 | risk-hub, bfagent, ausschreibungs-hub |
| 3 | travel-beat, tax-hub, cad-hub, weltenhub, research-hub |

## Implementation

### `HealthBypassMiddleware` (platform_context.middleware)

- Short-circuits requests to `HEALTH_PROBE_PATHS` with `{"status": "ok"}`
- Default paths: `/livez/`, `/healthz/`, `/readyz/`, `/health/`
- Configurable via `settings.HEALTH_PROBE_PATHS` (frozenset)
- No database access, no auth, no tenant resolution
- 22 unit tests

### `SubdomainTenantMiddleware` (platform_context.middleware)

- Now includes built-in health path bypass (skips tenant resolution)
- Resolves subdomain → tenant model → sets `request.tenant` + RLS

### Defense in Depth: `ALLOWED_HOSTS`

The `ALLOWED_HOSTS` defensive snippet (ADR-021) remains in all repos as backup:

```python
# ADR-021: Internal hosts for Docker/LB health probes — always present
ALLOWED_HOSTS.extend(h for h in ("localhost", "127.0.0.1") if h not in ALLOWED_HOSTS)
```

This ensures `Host: localhost` is always accepted, even if `HealthBypassMiddleware`
is misconfigured or not yet deployed.

## Consequences

### Positive

- **Consistent behavior**: Health probes work identically across all 19 repos
- **Single source of truth**: Middleware logic lives in `platform_context`, not per-repo
- **Onboarding**: New repos get health probes by adding one middleware line
- **Eliminates hacks**: travel-beat's custom `HealthBypassTenantMiddleware`,
  research-hub's `EXEMPT_PATH_PREFIXES`, bfagent's `.env.prod` edit all become obsolete

### Negative

- Repos must depend on `iil-platform-context >= 0.6.0`
- Custom health views in repos (e.g., DB-checking `/healthz/`) are bypassed —
  use `/healthz/` in the repo's own URL conf if detailed checks are needed
  alongside the middleware's fast `/livez/`

### Neutral

- The `ALLOWED_HOSTS` defensive snippet stays as defense-in-depth
- Per-repo health views can coexist (middleware only intercepts configured paths)

## Migration Path

1. Add `HealthBypassMiddleware` as first middleware in each repo
2. Remove per-repo health bypass hacks (travel-beat, research-hub)
3. Verify with `curl -H "Host: localhost" http://127.0.0.1:<port>/livez/`
4. Future: Publish `iil-platform-context` to GitHub Packages PyPI registry
   to eliminate git-clone-from-monorepo pattern in Dockerfiles
