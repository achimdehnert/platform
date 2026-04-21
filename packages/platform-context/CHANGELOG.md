# Changelog — platform-context

All notable changes to this package are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.7.0] — current (ADR-167 v1.1)

### BREAKING CHANGES
- Default `HEALTH_PROBE_PATHS` reduced to `{"/livez/", "/healthz/"}`.
  `/readyz/` and `/health/` are no longer bypassed.
- Response format is now `text/plain` ("ok\n") by default (was JSON).
  Use `Accept: application/json` header or `HEALTH_RESPONSE_FORMAT = "json"`.
- Non-GET/HEAD requests to health paths return `405 Method Not Allowed` (was 200).

### Added
- `health/views.py` — `ReadinessView` (opt-in DB-checking readiness endpoint)
- `health/urls.py` — URL patterns for `ReadinessView` at `/readyz/`
- `health_checks.py` — Django system checks (`E167.*`/`W167.*`) for ADR-167 compliance
- `metrics.py` — Prometheus counter `iil_health_probe_total{path,mode}` with `_NoopCounter` fallback
- Content negotiation: Accept header selects JSON or text/plain response
- Response headers: `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`
- Async dual-mode: `@sync_and_async_middleware` for ASGI-native dispatch
- Structured DEBUG logging on health path hits

### Changed
- `middleware.py` — `HealthBypassMiddleware` rewritten as function-based dual-mode middleware
- `apps.py` — `PlatformContextConfig.ready()` now registers ADR-167 system checks

---

## [0.6.0] — 2026-04-21 (ADR-167 v1.0)

### Added
- `HealthBypassMiddleware` — Tier 1 middleware short-circuiting health probe paths (ADR-021)
- `SubdomainTenantMiddleware` — health-path bypass integrated
- Phase 1 rollout to 9 repos (risk-hub, bfagent, billing-hub, coach-hub, tax-hub, wedding-hub, writing-hub, pptx-hub, trading-hub)
- 22 unit tests for middleware

---

## [0.5.0]

### Added
- `temporal_client.py` — Temporal workflow engine client integration (ADR-079)
- `tenant_utils/` — Shared tenant utility helpers
- `testing/` — Shared test fixtures and helpers for downstream packages (ADR-084)
- `outbox.py` — Transactional outbox pattern for reliable event publishing

### Changed
- `middleware.py` — RequestContextMiddleware now sets tenant context per request
- `htmx.py` — HtmxErrorMiddleware hardened; handles non-HTMX requests gracefully
- `exceptions.py` — Platform-wide exception hierarchy extended

---

## [0.4.x]

### Added
- `audit.py` — Shared audit log base model and mixin
- `db.py` — Database utilities (connection helpers, vendor detection)
- `context_processors.py` — Django context processors for platform-wide template vars
- `context.py` — Request context holder (thread-local + async-safe)

### Changed
- `apps.py` — AppConfig registered as `platform_context`

---

## [0.3.x]

### Added
- Initial package structure with `src/` layout
- Django 5.x compatibility (requires `Django>=5.0,<6.0`)
- Optional extras: `tenants` (django-tenants), `temporal` (temporalio)

---

## [0.2.x]

### Added
- First stable release as shared foundation package
- Extracted from bfagent monolith (ADR-028)

---

## [0.1.0]

### Added
- Initial extraction from bfagent-core (ADR-028: Platform Context Consolidation)
