# Tenant Rollout Template (ADR-137)

How to integrate `django-tenancy` TenantManager + RLS into a new hub.

## Step 1: Install django-tenancy

```bash
# In the hub's packages/ or requirements
pip install -e packages/django-tenancy
```

Add to `INSTALLED_APPS`:
```python
INSTALLED_APPS = [
    ...
    "django_tenancy",
]
```

Add middleware:
```python
MIDDLEWARE = [
    ...
    "django_tenancy.middleware.SubdomainTenantMiddleware",
    "django_tenancy.lifecycle.TenantLifecycleMiddleware",
]
```

## Step 2: Add TenantManager to all tenant-scoped models

For each model with a `tenant_id` field (non-nullable):

```python
from django_tenancy.managers import TenantManager

class MyModel(models.Model):
    tenant_id = models.UUIDField(db_index=True)
    ...
    objects = TenantManager()
```

**Skip** models where `tenant_id` is nullable (hybrid/system data).
**Skip** the Organization/tenant model itself.

## Step 3: Verify no query breakage

```bash
# Run full test suite
python -m pytest tests/ -x

# Or verify imports programmatically
python -c "
from django_tenancy.managers import TenantManager
from myapp.models import MyModel
assert isinstance(MyModel.objects, TenantManager)
"
```

## Step 4: Enable RLS (PostgreSQL)

```bash
# Create separate DB roles (once per database)
python manage.py setup_rls_roles \
    --app-user=<hub>_app \
    --app-password=<secret> \
    --dry-run

python manage.py setup_rls_roles \
    --app-user=<hub>_app \
    --app-password=<secret>

# Enable RLS policies on all tenant tables
python manage.py enable_rls --dry-run
python manage.py enable_rls
```

## Step 5: Switch DB users

In `docker-compose.prod.yml` or `.env.prod`:

| Service | DB User | RLS |
|---------|---------|-----|
| `migrate` | `<hub>_admin` (table owner) | exempt |
| `web` (gunicorn) | `<hub>_app` | **active** |
| `celery` | `<hub>_app` | **active** |

## Step 6: Add Module-Shop (optional)

```bash
pip install -e packages/django-module-shop
```

```python
# settings.py
INSTALLED_APPS += ["django_module_shop"]

BILLING_HUB_CHECKOUT_URL = "https://billing.iil.pet/checkout"
MODULE_SHOP_PRODUCT_NAME = "<hub-name>"

MODULE_SHOP_CATALOGUE = {
    "module_code": {
        "name": "Module Name",
        "description": "...",
        "included_in_plans": ["professional"],
        "standalone_bookable": True,
        "trial_days": 14,
        "icon": "shield",
    },
}
```

```python
# urls.py
urlpatterns += [
    path("billing/modules/",
         include("django_module_shop.urls",
                 namespace="module_shop")),
]
```

## Checklist

- [ ] `django_tenancy` in INSTALLED_APPS
- [ ] `SubdomainTenantMiddleware` in MIDDLEWARE
- [ ] `TenantLifecycleMiddleware` in MIDDLEWARE
- [ ] All tenant-scoped models use `TenantManager`
- [ ] `enable_rls --dry-run` shows correct SQL
- [ ] DB user separation configured
- [ ] Test suite passes with TenantManager
- [ ] Health endpoints (`/livez/`, `/healthz/`) registered
- [ ] Module-Shop configured (if applicable)

## Reference

- **ADR-137**: Tenant Lifecycle, Module Self-Service, RLS
- **ADR-035**: Shared Django Tenancy Package
- **ADR-118**: billing-hub as Platform Store
- **risk-hub**: Reference implementation (first hub)
