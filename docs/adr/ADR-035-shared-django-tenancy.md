---
status: accepted
date: 2026-02-21
decision-makers: Achim Dehnert
implementation_status: implemented
implementation_evidence:
  - "iil-testkit: shared tenancy fixtures"
---

# ADR-035: Shared Django Tenancy Package

| Metadata    | Value |
| ----------- | ----- |
| **Status**  | Accepted |
| **Date**    | 2026-02-15 |
| **Author**  | Achim Dehnert |
| **Scope**   | platform, cad-hub, weltenhub, risk-hub, travel-beat, bfagent |
| **Follows** | ADR-003 (risk-hub Tenancy), ADR-022 (Platform Consistency), ADR-029 (cad-hub Extraction) |

---

## 1. Problem Statement

Multi-tenancy infrastructure is **copy-pasted across 3+ repos** with diverging implementations:

| Component | cad-hub | risk-hub | weltenhub |
|-----------|---------|----------|-----------|
| Organization model | 79 lines, minimal | 157 lines, Status lifecycle, constraints, indexes | FK to `tenants.Tenant` (different pattern) |
| Membership model | Basic (3 roles) | Full (5 roles, invited_by, constraints) | None (via Tenant FK) |
| TenantAwareManager | `for_tenant(uuid)` 13 lines | ViewSet-based `get_tenant_id()` with 3-tier resolution | Thread-local auto-filter `get_queryset()` |
| Middleware | Subdomain → org lookup, 51 lines | Subdomain + header + RLS `SET app.tenant_id`, contextvars | Thread-local `set_current_tenant()` |
| healthz.py | DB-only, 50 lines | DB, separate file | DB + Redis + latency, 75 lines |
| Context propagation | None | `contextvars` + `set_db_tenant()` for RLS | Thread-local storage |

**Problems:**

- **Drift**: Each repo evolves independently; bug fixes don't propagate
- **Inconsistency**: weltenhub uses FK-based tenancy, others use UUID `tenant_id`
- **Missing features**: cad-hub has no RLS, no lifecycle, no context propagation
- **Global Rules violation**: Rules mandate `tenant_id = UUIDField(db_index=True)` — weltenhub violates this
- **Onboarding tax**: Every new app copy-pastes ~300 lines of boilerplate

## 2. Decision

Extract tenancy infrastructure into `platform/packages/django-tenancy/` as a pip-installable Django app, based on risk-hub's implementation (the most mature).

### 2.1 Package Structure

```text
platform/packages/django-tenancy/
├── pyproject.toml
├── README.md
├── django_tenancy/
│   ├── __init__.py           # Version, default_app_config
│   ├── apps.py               # DjangoTenancyConfig
│   ├── models.py             # Organization, Membership (abstract-ready)
│   ├── managers.py           # TenantAwareManager
│   ├── middleware.py          # SubdomainTenantMiddleware
│   ├── context.py            # contextvars: get_context(), set_tenant(), set_db_tenant()
│   ├── healthz.py            # liveness + readiness (DB + Redis + latency)
│   ├── decorators.py         # @with_tenant(tenant_id) for Celery tasks
│   ├── types.py              # RequestContext dataclass
│   └── migrations/
│       └── 0001_initial.py   # Organization + Membership tables
└── tests/
    ├── __init__.py
    ├── test_models.py
    ├── test_managers.py
    ├── test_middleware.py
    ├── test_context.py
    └── test_healthz.py
```

### 2.2 Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Canonical model | risk-hub's Organization (Status lifecycle, constraints, indexes) | Most mature, production-proven |
| Tenant field | `tenant_id = UUIDField(db_index=True)` on all user-data models | Global Rules mandate this; `Organization.id != Organization.tenant_id` |
| Manager | Explicit `for_tenant(tenant_id)` — NO auto-filter on `get_queryset()` | Thread-local auto-filter is implicit, breaks in Celery/management commands |
| Context | `contextvars` (not threading.local) | Async-safe, works with Django 5.x async views |
| RLS glue | `set_db_tenant(uuid)` → `SET app.tenant_id = %s` | Defense in depth: DB-level isolation even if app filter forgotten |
| Middleware | Subdomain + `X-Tenant-ID` header fallback | API clients and tests need header-based tenant resolution |
| healthz | DB + Redis + latency measurement | Merge best of weltenhub (Redis) and cad-hub (`/health/` compat) |
| Abstract vs concrete models | **Concrete** — Organization + Membership are real tables | Apps install `django_tenancy` in INSTALLED_APPS, get tables via migrations |
| `db_table` prefix | `tenancy_organization`, `tenancy_membership` | Consistent with risk-hub; avoids collision with app-specific tables |

### 2.3 Core Interfaces

```python
# django_tenancy/context.py
def get_context() -> RequestContext: ...
def set_tenant(tenant_id: UUID | None, slug: str | None) -> None: ...
def set_db_tenant(tenant_id: UUID | None) -> None: ...  # SET app.tenant_id
def clear_context() -> None: ...

# django_tenancy/managers.py
class TenantAwareManager(models.Manager):
    def for_tenant(self, tenant_id: UUID) -> QuerySet: ...

# django_tenancy/middleware.py
class SubdomainTenantMiddleware(MiddlewareMixin):
    # Resolves: subdomain → Organization.slug lookup
    # Fallback: X-Tenant-ID header (for API/tests)
    # Sets: request.tenant_id, request.tenant, request.tenant_slug
    # Calls: set_tenant() + set_db_tenant()
    # Excludes: HEALTH_PATHS

# django_tenancy/decorators.py
def with_tenant(tenant_id: UUID):  # For Celery tasks
    ...
```

### 2.4 Migration Plan

| Phase | App | Action | Risk |
|-------|-----|--------|------|
| 1 | **platform** | Create `django-tenancy` package from risk-hub reference | None |
| 2 | **cad-hub** | Replace `apps/core/{models,managers,middleware,healthz}.py` with `django_tenancy` | LOW — minimal current impl, same pattern |
| 3 | **weltenhub** | Migrate FK-based `Tenant` → UUID-based `Organization` | MEDIUM — schema change, but low usage |
| 4 | **risk-hub** | Replace `src/tenancy/` + `src/common/{context,middleware,views}.py` with `django_tenancy` | LOW — same code, just moved |
| 5 | **travel-beat** | Adopt when multi-tenancy needed | None |
| 6 | **bfagent** | Adopt when multi-tenancy needed | None |

## 3. Consequences

### Positive

- **Single source of truth**: One tenancy implementation, bug fixes propagate
- **Onboarding**: New apps add `django_tenancy` to `INSTALLED_APPS` + pip install
- **Consistency**: All apps use same Organization model, same middleware, same RLS pattern
- **Async-safe**: `contextvars` works with Django async views and Celery

### Negative

- **Migration effort**: weltenhub needs schema migration (FK → UUID)
- **Dependency**: All tenant-aware apps depend on `platform/packages/django-tenancy`
- **risk-hub specifics**: `Site` model stays in risk-hub (domain-specific, not shared)

## 4. Alternatives Considered

### 4.1 Keep copying per repo

- **Rejected**: Drift is already happening; 3 incompatible implementations exist

### 4.2 Abstract models only (no concrete tables)

- **Rejected**: Each app would still define its own Organization table, losing cross-app consistency

### 4.3 django-tenants (third-party)

- **Rejected**: Uses schema-based isolation (one PG schema per tenant); our pattern uses row-level `tenant_id` filtering, which is simpler and more flexible

## 5. References

- ADR-003: risk-hub Tenancy (original design)
- ADR-022: Platform Consistency Standard
- ADR-029: cad-hub Extraction (identified duplication)
- Global Development Rules §3.3: Multi-Tenancy (CRITICAL)
