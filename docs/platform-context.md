# Platform Context

> **This document is the canonical AI context file for the achimdehnert platform.**
> Use it as a system prompt or attachment when querying external AI services
> (ChatGPT, Claude, Gemini, etc.) about platform architecture, requirements, or analysis.
>
> **Live version** (always current): `https://devhub.iil.pet/api/v1/context/?format=markdown`

---

## How This Document Is Maintained

```
catalog-info.yaml (per repo)
        ↓  import via: manage.py populate_catalog
dev-hub catalog DB (Django models: Component, System, Domain, Resource)
        ↓  export via:
GET https://devhub.iil.pet/api/v1/context/?format=markdown   → Markdown
GET https://devhub.iil.pet/api/v1/context/?format=json       → JSON
```

**Update cycle**: Daily import via cron + manual trigger per `populate_catalog` command.

---

## Infrastructure

- **Platform**: achimdehnert Platform
- **Server**: Hetzner VM `88.198.191.108` (all services)
- **Registry**: `ghcr.io/achimdehnert/`
- **Stack**: Python 3.12, Django 5.x, Docker Compose, PostgreSQL 16, Redis 7, Nginx + Let's Encrypt
- **Deployment**: GHCR images → SSH pull → `docker compose up --force-recreate` via `infra-deploy` GitHub Actions
- **CI/CD**: GitHub Actions (platform reusable workflows + `infra-deploy` for write ops)
- **Secrets**: SOPS + age (ADR-045)
- **Multi-Tenancy**: Row-Level Isolation via `tenant_id` UUIDField + Postgres RLS (ADR-050)

---

## Service Registry

| Service | Brand | Domain | URL | Port | Status |
|---------|-------|--------|-----|------|--------|
| `bfagent` | BF Agent | Content & Publishing | https://bfagent.iil.pet | 8088 | Production |
| `travel-beat` | DriftTales | Content & Publishing | https://drifttales.com | 8089 | Production |
| `weltenhub` | Weltenforger | Content & Publishing | https://weltenforger.com | 8081 | Production |
| `risk-hub` | Schutztat | Compliance & Safety | https://demo.schutztat.de | 8090 | Production |
| `dev-hub` | DevHub | Platform | https://devhub.iil.pet | 8085 | Production |
| `pptx-hub` | Prezimo | Platform | https://prezimo.com | 8020 | Production |
| `coach-hub` | KI ohne Risiko | Compliance & Safety | https://kiohnerisiko.de | 8007 | Experimental |
| `trading-hub` | — | Finance & Trading | https://trading-hub.iil.pet | 8088 | Experimental |
| `wedding-hub` | — | Events & Lifestyle | https://wedding-hub.iil.pet | 8093 | Experimental |
| `cad-hub` | nl2cad | Engineering | https://nl2cad.de | 8094 | Stopped |
| `mcp-hub` | — | Platform | intern | — | Production |

---

## Architecture Principles

- **Service Layer**: `views.py` → `services.py` → `models.py` (mandatory, no logic in views)
- **Multi-Tenancy**: Every user-data model has `tenant_id = UUIDField(db_index=True)`
- **HTMX**: Dynamic interactions without custom JS frameworks
- **API**: Django REST Framework (`/api/v1/`) or Django Ninja (risk-hub)
- **Testing**: pytest + pytest-django, minimum 80% coverage
- **ADRs**: All architecture decisions documented in `platform/docs/adr/` (ADR-001 to ADR-067+)

---

## Deployment Topology

```
Hetzner VM 88.198.191.108
├── Nginx (reverse proxy, SSL termination)
├── Docker Compose stacks per service
│   ├── <service>-web (gunicorn)
│   ├── <service>-worker (celery)
│   ├── <service>-beat (celery beat)
│   ├── <service>-db (postgres:16-alpine) — own stack
│   └── <service>-redis (redis:7-alpine)
├── Shared: bfagent_db (weltenhub + dev-hub share this)
└── infra-deploy runner (/opt/actions-runner)
    ├── health-check.yml  — every 15 min
    ├── deploy-service.yml — on dispatch
    ├── db-backup.yml     — daily 02:00 UTC
    └── migrate.yml       — on demand
```

---

## Key ADRs

| ADR | Title | Status |
|-----|-------|--------|
| ADR-021 | Unified Deployment Pattern | Accepted |
| ADR-037 | Chat Logging | Accepted |
| ADR-045 | Secrets Management (SOPS+age) | Accepted |
| ADR-050 | Platform Decomposition (Hub Landscape) | Accepted |
| ADR-053 | Documentation Strategy | Accepted |
| ADR-062 | Content Store Shared Persistence | Proposed |
| ADR-064 | coach-hub | Accepted |
| ADR-066 | AI Engineering Team | Proposed |
| ADR-067 | Deployment Execution Strategy (infra-deploy) | Accepted |

Full ADR index: https://github.com/achimdehnert/platform/blob/main/docs/adr/INDEX.md

---

## For External AI Queries

When asking an external AI service about this platform, prepend:

```
Context: I am working on the achimdehnert platform.
Full infrastructure context: [paste content of this document or link to API]
Please answer in the context of this specific platform setup.
```

Or use the live API:
```bash
curl https://devhub.iil.pet/api/v1/context/?format=markdown
```
