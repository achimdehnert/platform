# ADR-057 — Repo Scope & Migration Status (all 10 repos)

> Supplement to `ADR-057-platform-test-strategy.md` §3.
> **Last updated**: 2026-02-20

---

## Repo Scope Classification

| Repo | Type | ADR-057 Scope |
| --- | --- | --- |
| **weltenhub** | Django (multi-tenant, DRF) | ✅ Full scope |
| **travel-beat** | Django (allauth, HTMX) | ✅ Full scope |
| **bfagent** | Django (standard auth) | ✅ Full scope |
| **risk-hub** | Django (multi-tenant, `src/` layout) | ✅ Full scope |
| **cad-hub** | Django (django_tenancy, scaffold) | ✅ Full scope |
| **trading-hub** | Django (TimescaleDB, `src/trading_hub/`) | ✅ Full scope |
| **wedding-hub** | Django (`src/apps/`, allauth) | ✅ Full scope |
| **pptx-hub** | Python package (uv/PyPI, no Django) | ⚠️ Own CI — no pytest-django needed |
| **mcp-hub** | Python packages (FastMCP, no Django) | ⚠️ Own CI per module — no pytest-django needed |
| **odoo-hub** | Odoo 18 addons (no Django project) | ⚠️ Odoo test framework — out of scope |

---

## Phase 1 — Test Infrastructure Status

| Item | weltenhub | travel-beat | bfagent | risk-hub | cad-hub | trading-hub | wedding-hub |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `requirements-test.txt` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| pytest config | ✅ | ✅ | ✅ | ✅ | ✅ | existing | existing |
| `settings/test.py` | ✅ | ✅ | ✅ | ✅ (settings_test.py) | ✅ | own module | ✅ existing |
| `conftest.py` + `factories.py` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ existing |
| CI → `_ci-python.yml@main` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

## Phase 2 — Model + View Tests Status

| Item | weltenhub | travel-beat | bfagent | risk-hub | cad-hub | trading-hub | wedding-hub |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Model tests | ✅ World/Tenant | ✅ Trip/Stop | ✅ BookProject | ✅ Assessment/Hazard | — | — | ✅ existing |
| View/service tests | ✅ DRF API | ✅ HTMX | ✅ Django views | — | ✅ | — | ✅ existing |
| Property tests | — | ✅ | — | ✅ risk_score | — | — | — |
| Schemathesis | ✅ | — | — | — | — | — | — |
| Coverage 50% | 🔴 | 🔴 | 🔴 | 🔴 | 🔴 | 🔴 | 🔴 |

## Repo-spezifische Besonderheiten

| Repo | Besonderheit |
| --- | --- |
| **weltenhub** | Multi-Tenant UUID FK; DRF ViewSets; Schemathesis vorhanden |
| **travel-beat** | Custom `AUTH_USER_MODEL`; HTMX; allauth |
| **bfagent** | Standard auth; kein HTMX; `apps/`-Layout |
| **risk-hub** | `src/`-Layout; monolithisches Settings → `settings_test.py`; SQLite Unit-Tests |
| **cad-hub** | `apps/`-Layout; split settings; `django_tenancy` |
| **trading-hub** | `src/trading_hub/`-Layout; eigenes Settings-Modul; TimescaleDB |
| **wedding-hub** | `src/apps/`-Layout; allauth; `Organization`/`Guest`/`Event`; reichhaltige Tests bereits vorhanden |
| **pptx-hub** | Python-Package; `uv`/PyPI; kein `pytest-django` |
| **mcp-hub** | FastMCP-Packages; eigene Tests pro Modul; kein Django |
| **odoo-hub** | Odoo 18 Addons; Odoo-eigenes Test-Framework; kein Django-Projekt |
