# iil-django-tenancy

Platform-standard multi-tenancy package for all IIL Django UI Hubs.

**ADR references:** ADR-035 (shared-django-tenancy), ADR-109 (multi-tenancy platform standard)

## Installation

```bash
pip install iil-django-tenancy
# or for local development:
pip install -e packages/django-tenancy
```

## Quick Start

```python
# settings.py
INSTALLED_APPS = [
    ...
    "django_tenancy",
]

TENANCY_MODE = "subdomain"   # subdomain | session | header | disabled
TENANCY_FALLBACK_URL = "/onboarding/"

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django_tenancy.middleware.SubdomainTenantMiddleware",  # after Locale
    "django.middleware.common.CommonMiddleware",
    ...
]

TEMPLATES[0]["OPTIONS"]["context_processors"].append(
    "django_tenancy.context_processors.tenant",
)
```

```python
# models.py — inherit from TenantModel
from django_tenancy.models import TenantModel

class MyContent(TenantModel):
    title = models.CharField(max_length=200)
    # tenant_id (BigIntegerField), public_id (UUID), deleted_at inherited
```

## TenancyMode

| Mode | Use case |
|------|----------|
| `subdomain` | Production — `tenant.hub.domain.tld` |
| `session` | Local dev — no subdomain setup needed |
| `header` | API / CI — `X-Tenant-ID` header |
| `disabled` | billing-hub, dev-hub — single tenant |

## Components

- `django_tenancy.models.Organization` — Tenant entity
- `django_tenancy.models.TenantModel` — Abstract base for all tenant-scoped models
- `django_tenancy.middleware.SubdomainTenantMiddleware` — Resolves tenant per request
- `django_tenancy.managers.TenantManager` — `for_tenant()`, `active()` QuerySet
- `django_tenancy.context_processors.tenant` — `request.tenant` in templates
- `django_tenancy.decorators.with_tenant` — Celery task decorator
