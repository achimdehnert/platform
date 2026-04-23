# Changelog — bfagent-core

All notable changes to this package are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.2.0] — current

### Fixed
- Internal imports now use `platform_context` directly instead of deprecated `bfagent_core` shims
  (`checker`, `decorators`, `mixins`, `services`, `events`)
- `TenantPermissionMiddleware`: log exceptions instead of silent `except pass`
- Migrations 0005/0006: wrapped PostgreSQL-specific `RunSQL` with vendor check for SQLite test compat
- `permission.py`: replaced deprecated `unique_together` with `UniqueConstraint`

### Removed
- Unused `warnings` import from `__init__.py`
- Unused `User` variable from `user.py`
- Unused `ABC` import from `repositories/`
- Unused `Optional` import from `events/`

### Changed
- `bfagent_core` shims are now thin re-exports from `platform_context` (ADR-028)
- All 32 tests passing after refactor

---

## [0.1.x]

### Added
- `admin.py` — Django admin registrations for core models
- `models/` — Tenant, Permission, Role, User models with migrations
- `middleware.py` — TenantPermissionMiddleware, request logging
- `permissions/` — Role-based access control (RBAC)
- `handlers/` — Domain event handlers
- `events/` — Event definitions
- `services/` — Service layer base classes
- `repositories/` — Repository pattern base

---

## [0.0.1]

### Added
- Initial package extracted from bfagent monolith
- Declared dependency on `platform-context>=0.1.0`
- Django 5.x + Pydantic v2 + structlog as core dependencies
