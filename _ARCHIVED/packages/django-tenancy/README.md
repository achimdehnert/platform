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

## ADR-137: TenantManager (auto-filter)

```python
from django_tenancy.managers import TenantManager

class MyModel(models.Model):
    tenant_id = models.UUIDField(db_index=True)
    objects = TenantManager()

# In request context → auto-filtered by middleware tenant:
MyModel.objects.all()

# Explicit (Celery, management commands):
MyModel.objects.for_tenant(tenant_uuid)

# Admin / cross-tenant reports:
MyModel.objects.unscoped()
```

## ADR-137: Row-Level Security (Phase 2)

### Setup (once per database)

```bash
# 1. Create separate DB roles
python manage.py setup_rls_roles --dry-run   # preview
python manage.py setup_rls_roles \
    --app-user=risk_hub \
    --app-password=<secret>

# 2. Enable RLS on all tenant tables
python manage.py enable_rls --dry-run        # preview
python manage.py enable_rls                  # execute

# Single table:
python manage.py enable_rls --table=risk_assessment

# Remove RLS:
python manage.py enable_rls --disable
```

### DB Role Separation

| Role | Used by | RLS |
|------|---------|-----|
| `<db>_admin` (table owner) | migrate, createsuperuser | exempt |
| `<db>_app` (non-owner) | gunicorn, celery | **active** |

After `setup_rls_roles`, update `DATABASE_URL` for
gunicorn/celery to use the app-user. Keep the admin-user
for migrations.

## ADR-137: Phase 4 — RLS Rollout Checklist

### Pre-requisites

1. All tenant-scoped models use `TenantManager` (Phase 4.1 ✅)
2. `SubdomainTenantMiddleware` sets `app.tenant_id` session var
3. DB roles created via `setup_rls_roles`

### Rollout Steps (per environment)

```bash
# 1. Dry-run — verify SQL, no changes
python manage.py enable_rls --dry-run

# 2. Apply RLS policies
python manage.py enable_rls

# 3. Verify no query breakage (run test suite)
python -m pytest tests/ -x

# 4. Switch app to non-owner DB user
#    Update DATABASE_URL in .env.prod:
#    OLD: postgresql://risk_hub_admin:xxx@db/risk_hub
#    NEW: postgresql://risk_hub_app:xxx@db/risk_hub
#    Keep admin user for migrate service only.

# 5. Restart app containers
docker compose restart web celery

# 6. Smoke test — verify tenant isolation
curl -H "X-Tenant-ID: <uuid>" https://app/api/v1/...
```

### Covered Tables (28 models)

| App | Models |
|-----|--------|
| risk | Assessment, Hazard |
| actions | ActionItem |
| documents | Document, DocumentVersion |
| approvals | ApprovalWorkflow, ApprovalRequest |
| notifications | Notification, NotificationPreference |
| permissions | Role, Scope, Assignment |
| identity | ApiKey |
| tenancy | Membership, Site |
| explosionsschutz | Area, ExplosionConcept, ZoneDefinition, ProtectionMeasure, Equipment, Inspection, ZoneIgnitionSourceAssessment, VerificationDocument, ZoneCalculationResult, EquipmentATEXCheck |
| substances | Party + all TenantScopedModel subclasses |
| gbu | HazardAssessmentActivity, ActivityMeasure |

### Excluded (by design)

- `Organization` — tenant entity itself, not tenant-scoped
- `User` — nullable tenant_id, uses Django's UserManager
- `Permission`, `RolePermission`, `ApprovalStep`, `ApprovalDecision` — no tenant_id
- `TenantScopedMasterData` subclasses (explosionsschutz) — nullable tenant_id, hybrid isolation

## Critical Rule

`Organization.id != Organization.tenant_id` — **always** use `org.tenant_id` for data isolation.
