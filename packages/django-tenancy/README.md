# django-tenancy

Shared multi-tenancy infrastructure for the BF Agent platform — per ADR-035.

## Core Components

- **Organization**: Tenant model with lifecycle management (trial → active → suspended → deleted)
- **Membership**: User-to-organization mapping with roles (owner, admin, member, viewer, external)
- **SubdomainTenantMiddleware**: Resolves tenant from subdomain or `X-Tenant-ID` header
- **TenantAwareManager**: Explicit `.for_tenant(uuid)` queryset filtering
- **Context propagation**: Async-safe contextvars + PostgreSQL RLS session variable
- **Health endpoints**: `/livez/` (liveness) + `/healthz/` (readiness with DB + Redis checks)
- **Decorators**: `tenant_context()` context manager, `@with_tenant_from_arg()` for Celery tasks

## Installation

```bash
pip install -e ".[dev]"
```

## Usage

```python
# settings.py
INSTALLED_APPS = [
    ...
    "django_tenancy",
]

MIDDLEWARE = [
    ...
    "django_tenancy.middleware.SubdomainTenantMiddleware",
]

# urls.py
from django_tenancy.healthz import liveness, readiness

urlpatterns = [
    path("livez/", liveness),
    path("healthz/", readiness),
]

# In views / services:
from django_tenancy.managers import TenantAwareManager

class MyModel(models.Model):
    tenant_id = models.UUIDField(db_index=True)
    objects = TenantAwareManager()

# Query with tenant isolation:
MyModel.objects.for_tenant(request.tenant_id)
```

## Critical Rule

`Organization.id != Organization.tenant_id` — **always** use `org.tenant_id` for data isolation.
