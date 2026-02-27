# BF Agent Platform — Architecture Contract

> MANDATORY. Every code change MUST comply. Violations = immediate fix.
> Source: ADR-094, ADR-009, ADR-048, ADR-071
> Always-On Rule (Layer 1) — loaded in every Cascade session.

## Service Layer (NEVER skip)

- `views.py` → `services.py` → `models.py` (3-tier, no shortcuts)
- Views: HTTP only. NO queries, NO business logic, NO `model.save()`
- Services: All business logic. Return data, raise exceptions.
- Models: Data + constraints. NO HTTP, NO rendering.

## Database-First

- PostgreSQL 16. All constraints in DB, not just Python.
- `DEFAULT_AUTO_FIELD = BigAutoField` (INTEGER PKs, NEVER UUIDs as PK)
- FK naming: `{referenced_model}_id` with `on_delete=PROTECT`
- No `JSONField()` for structured data. Lookup tables for choices.
- Computed values → `@property`, never DB columns

## Naming

- DB tables: `{app}_{entity}` snake_case singular
- Python: PascalCase classes, snake_case functions/vars
- URL names: `{model}_list`, `{model}_detail`, `{model}_create`, `{model}_edit`, `{model}_delete`
- Templates: `templates/{app}/{model}_{action}.html`
- Partials: `templates/{app}/partials/_{component}.html`
- Tests: `test_should_{expected_behavior}`

## Settings (ALL repos)

- Root URL conf: `config.urls` (NEVER `{app_name}.urls` as ROOT_URLCONF)
- WSGI: `config.wsgi.application`
- Repo-specific details: see `project-facts.md`

## HTMX (ADR-048)

- ALWAYS: `hx-target` + `hx-swap` + `hx-indicator` (all three, no exceptions)
- ALWAYS: `data-testid` on interactive elements
- NEVER: `hx-boost` on forms, `inline style=`, `onclick=` with `hx-*`
- Partials: standalone fragments, no `{% extends %}`
- **Detection method is repo-specific — ALWAYS check `project-facts.md` first.**
- **Im Zweifel: project-facts.md ist massgeblich.**

## Code Quality (ADR-071)

- Commits: `[TAG] module: description` (feat/fix/refactor/docs/test/chore)
- Bash: `set -euo pipefail` in every script
- No silent fallbacks. Explicit over implicit.
- Max function: 50 lines. Max class: 200 lines. Max file: 500 lines.

## Infrastructure

- Registry: `ghcr.io/achimdehnert/{repo}`
- Compose: `docker-compose.prod.yml`, `env_file: .env.prod`
- Health: `/livez/` (liveness) + `/healthz/` (readiness)
- Secrets: NEVER hardcode IPs, passwords, API keys in code
- SSH: NEVER `StrictHostKeyChecking=no`
