# iil-django-commons

Shared backend services library for Django projects on the iil.pet platform.

Implements [ADR-091](../../docs/adr/ADR-091-shared-backend-services.md) — Phase 1: Logging, Health, Cache.

## Installation

```bash
# Minimal (logging + health only)
pip install -e packages/iil-django-commons

# With cache support (django-redis)
pip install -e "packages/iil-django-commons[cache]"

# Full
pip install -e "packages/iil-django-commons[all]"

# From GitHub (pinned)
pip install "git+https://github.com/achimdehnert/platform.git@v0.1.0#subdirectory=packages/iil-django-commons"
```

## Setup

```python
# settings.py
INSTALLED_APPS = [
    "iil_commons",
    ...
]

MIDDLEWARE = [
    "iil_commons.logging.middleware.CorrelationIDMiddleware",
    "iil_commons.logging.middleware.RequestLogMiddleware",
    ...
]

IIL_COMMONS = {
    "LOG_FORMAT": "json",        # "json" | "human"
    "LOG_LEVEL": "INFO",
    "CACHE_DEFAULT_TTL": 300,
    "HEALTH_CHECKS": ["db", "redis"],
}
```

```python
# urls.py
from django.urls import include, path

urlpatterns = [
    path("", include("iil_commons.health.urls")),
    ...
]
```

## Modules (Phase 1)

### Logging

```python
# Auto-configured via AppConfig.ready() — no manual call needed.
# Override format per project:
IIL_COMMONS = {"LOG_FORMAT": "json"}  # structured JSON for production
```

Middlewares add `X-Correlation-ID` header to every request/response and log
`method`, `path`, `status`, `duration_ms`, `user_id` per request.

### Health Checks

| Endpoint | Purpose |
|----------|---------|
| `/livez/` | Liveness — always 200 if process is running |
| `/readyz/` | Readiness — checks DB, Redis, Celery (configurable) |

```python
IIL_COMMONS = {"HEALTH_CHECKS": ["db", "redis"]}
```

### Cache

```python
from iil_commons.cache import cached_view, cached_method, invalidate_pattern

@cached_view(ttl=300, key_func=lambda r: f"guests:{r.org.pk}")
def guest_list(request): ...

class GuestService:
    @cached_method(ttl=60, key_prefix="guest_service")
    def get_active(self, org_id): ...

# Invalidate on model save
invalidate_pattern(f"iil:view:guests:{org.pk}:*")
```

`invalidate_pattern` requires `django-redis` backend (`iter_keys` support).

## Running Tests

```bash
cd packages/iil-django-commons
pip install -e ".[dev]"
pytest
```

## Roadmap

| Phase | Modules | Version |
|-------|---------|---------|
| ✅ Phase 1 | Logging, Health, Cache | v0.1.0 |
| Phase 2 | Rate Limiting, Security Headers | v0.2.0 |
| Phase 3 | Email abstraction, Celery BaseTask, Prometheus | v0.3.0 |
| Phase 4 | Second project integration, Cookiecutter starter | v0.4.0 |
