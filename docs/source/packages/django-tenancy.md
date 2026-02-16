# django-tenancy

Shared multi-tenancy infrastructure for the BF Agent platform.
Provides models, middleware, context propagation, and managers for
row-level tenant isolation across all Django apps.

**Package**: `platform/packages/django-tenancy`
**Version**: 0.1.0
**Python**: ≥ 3.11 | **Django**: ≥ 4.2

## Installation

```bash
pip install -e ".[dev]"
```

## Architecture

```text
django_tenancy/
├── context.py       # Contextvars-based tenant propagation (async-safe)
├── decorators.py    # @tenant_context, @with_tenant_from_arg
├── managers.py      # TenantAwareManager (auto-filters by tenant_id)
├── middleware.py     # TenantMiddleware (subdomain → tenant resolution)
├── models.py        # Organization, Membership
├── types.py         # RequestContext (frozen dataclass)
├── healthz.py       # /livez/, /healthz/ endpoints
└── migrations/
    └── 0001_initial.py
```

## Core Components

### Context Propagation (`context.py`)

Async-safe tenant context using Python `contextvars`:

```python
from django_tenancy.context import get_context, set_tenant, set_db_tenant

# In middleware (automatic):
set_tenant(org.tenant_id, subdomain)
set_db_tenant(org.tenant_id)  # Sets PostgreSQL session var for RLS

# In application code:
ctx = get_context()
queryset.filter(tenant_id=ctx.tenant_id)
```

### Decorators (`decorators.py`)

- **`tenant_context(tenant_id, slug)`** — context manager that sets/clears tenant
- **`@with_tenant_from_arg("tenant_id")`** — decorator for functions/Celery tasks
  that extracts tenant_id from arguments (sync + async support)

### TenantAwareManager (`managers.py`)

Auto-filters querysets by current tenant:

```python
class MyModel(models.Model):
    tenant_id = models.UUIDField(db_index=True)
    objects = TenantAwareManager()
```

### Models

- **Organization** — tenant entity with `tenant_id` (UUID), name, slug,
  domain, status (trial/active/suspended/deleted), settings (JSON)
- **Membership** — user↔tenant relationship with roles
  (owner/admin/member/viewer/external)

### Middleware (`middleware.py`)

Resolves tenant from subdomain, sets context for the request lifecycle:

```python
MIDDLEWARE = [
    "django_tenancy.middleware.TenantMiddleware",
    # ...
]
```

### Health Endpoints (`healthz.py`)

Kubernetes-compatible health check paths:

- `/livez/` — liveness probe
- `/healthz/` — readiness probe
- `/health/` — compatibility alias

## Configuration

```python
# settings.py
INSTALLED_APPS = [
    "django_tenancy",
    # ...
]
```

## Recent Fixes (2026-02-16)

- **Django 6.0 deprecation**: `CheckConstraint(check=...)` → `CheckConstraint(condition=...)`
  in both `models.py` and `migrations/0001_initial.py`
- **pytest-asyncio**: Added to dev dependencies for async decorator tests

## Tests

```bash
# Run all tests (45 passed)
cd packages/django-tenancy
.venv/bin/python -m pytest tests/ -v
```
