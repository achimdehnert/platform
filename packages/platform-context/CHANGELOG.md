# Changelog — platform-context

All notable changes to this package are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.5.0] — current

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
