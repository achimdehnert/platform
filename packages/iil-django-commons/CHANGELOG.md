# Changelog — iil-django-commons

## [0.1.0] — 2026-02-27

### Added
- `iil_commons.logging`: Structured logging setup (`setup_logging()`), JSON + Human formatters, `CorrelationIDMiddleware`, `RequestLogMiddleware`
- `iil_commons.health`: Standardized `/livez/` and `/readyz/` endpoints, `DatabaseCheck`, `RedisCheck`, `CeleryCheck`, pluggable check registry
- `iil_commons.health.urls`: Drop-in URL patterns for Django `urls.py`
- `iil_commons.cache`: `@cached_view`, `@cached_method` decorators, `invalidate_pattern()` for django-redis
- `iil_commons.settings`: Central `IIL_COMMONS` settings dict with typed defaults
- `iil_commons.apps`: Django `AppConfig` with auto-logging setup on `ready()`
- Full test suite: 12 tests covering all Phase 1 modules
- `pyproject.toml` with optional extras: `cache`, `ratelimit`, `monitoring`, `email`, `logging`, `all`
