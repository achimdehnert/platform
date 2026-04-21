# BF Agent Platform

Shared packages, reusable CI/CD workflows, governance tooling, and architecture documentation for the BF Agent ecosystem.

## Struktur

```
platform/
├── packages/              # 22 shared Python packages
├── agents/                # Autonomous governance agents (guardian, drift_detector, adr_scribe, ...)
├── docs/adr/              # 90+ Architecture Decision Records (MADR 4.0)
├── .github/workflows/     # 25 reusable CI/CD workflows (_ci-python, _build-docker, _deploy-unified, ...)
├── tools/                 # repo_checker, check_htmx_patterns, check_design_tokens
├── scripts/               # Ops/infra scripts (ship.sh, sync-repo.sh, adr_next_number, ...)
├── governance-deploy/     # Standalone governance Django app
├── deployment/            # Docker Compose templates, systemd units
└── concepts/              # Architecture concept docs
```

## Packages

| Package | Version | Beschreibung |
|---------|---------|--------------|
| `platform-context` | 0.7.0 | Core Django foundation (Context, Health, Audit, Outbox, Tenancy, HTMX) |
| `iil-platform` | 1.0.0 | Umbrella for Context, Commons, Tenancy |
| `iil-django-commons` | 0.3.0 | Shared backend services (Logging, Caching, Pagination) |
| `bfagent-core` | 0.2.0 | BFAgent-spezifische Core-Komponenten (Auth, Permissions, Models) |
| `bfagent-llm` | 1.0.1 | LiteLLM-Backend + DB-driven Model-Routing (ADR-089) |
| `creative-services` | 0.3.0 | LLM Client, Adapters, Story/Character/World-Generierung |
| `django-tenancy` | 0.1.0 | Subdomain-basierte Multi-Tenancy |
| `django-module-shop` | 0.2.0 | Reusable Django module catalogue & subscription management |
| `chat-agent` | 0.1.0 | Domain-agnostic Chat-Agent mit Tool-Use Loop |
| `docs-agent` | 0.2.0 | AI-assisted Documentation Quality Agent (AST scanner, DIATA) |
| `doc-templates` | 0.3.0 | Reusable Django document template system |
| `concept-templates` | 0.5.0 | Structured concept extraction, PDF, schemas |
| `content-store` | 0.1.0 | AI-generated content persistence (ADR-050) |
| `hub-identity` | 0.1.0 | Hub Visual & Language Identity System |
| `platform-notifications` | 0.1.0 | Multi-Channel Notification Registry (ADR-088) |
| `dvelop-client` | 0.1.0 | Python client for d.velop DMS REST API |
| `task_scorer` | 0.1.0 | Task-Scoring und Routing-Engine (ADR-023) |
| `mcp-governance` | 0.1.0 | MCP Tool Governance & Service Discovery |
| `inception-mcp` | 0.1.0 | MCP Server for DDL Inception — AI-driven Business Cases |
| `outline-mcp` | 0.2.0 | MCP Server for Outline Wiki |
| `sphinx-export` | — | Sphinx → Markdown Export |
| `cad-services` | — | IFC/DXF CAD-Verarbeitung (stub) |

## Installation

```bash
# Core foundation
pip install -e packages/platform-context

# BFAgent-spezifische Komponenten
pip install -e packages/bfagent-core

# LLM-Services (mit optionalen Providern)
pip install -e "packages/creative-services[openai,anthropic]"
```

## Deployed Services

| Service | Brand | URL | Status |
|---------|-------|-----|--------|
| bfagent | BF Agent | https://bfagent.iil.pet | ✅ Production |
| risk-hub | Schutztat | https://schutztat.de | ✅ Production |
| travel-beat | DriftTales | https://drifttales.com | ✅ Production |
| weltenhub | Weltenforger | https://weltenforger.com | ✅ Production |
| dev-hub | DevHub | https://devhub.iil.pet | ✅ Production |
| pptx-hub | Prezimo | https://prezimo.com | ✅ Production |
| coach-hub | KI ohne Risiko | https://kiohnerisiko.de | ✅ Production |
| trading-hub | — | https://trading-hub.iil.pet | ✅ Production |
| wedding-hub | — | https://wedding-hub.iil.pet | ✅ Production |
| ausschreibungs-hub | — | https://ausschreibungs-hub.iil.pet | ✅ Production |
| billing-hub | — | https://billing-hub.iil.pet | ✅ Production |
| cad-hub | nl2cad | https://nl2cad.de | ⏸ Gestoppt |

## Tech Stack

| Bereich | Technologie |
|---------|-------------|
| Framework | Django 5.x |
| APIs | DRF (dev-hub) / Django Ninja (risk-hub) |
| Frontend | HTMX + TailwindCSS |
| Datenbank | PostgreSQL 16 + pgvector |
| Async | Celery + Redis |
| Build | Hatchling (pyproject.toml) |
| Lint/Format | Ruff |
| Tests | pytest + pytest-django + factory-boy |
| Container | Docker (non-root, healthchecks in Compose) |
| Secrets | SOPS |
| CI/CD | GitHub Actions + Self-hosted Runner (Hetzner) |
| Proxy | Nginx |

## Architecture Decision Records

90+ ADRs im MADR 4.0 Format — alle Architekturentscheidungen sind dokumentiert.

```bash
# Nächste freie ADR-Nummer ermitteln
python3 scripts/adr_next_number.py

# Konflikte und Lücken prüfen (CI)
python3 scripts/adr_next_number.py --audit
python3 scripts/adr_next_number.py --check
```

→ [ADR Index](docs/adr/INDEX.md)

## Related Repositories

- **[bfagent](https://github.com/achimdehnert/bfagent)** — AI Book Writing Platform
- **[risk-hub](https://github.com/achimdehnert/risk-hub)** — Schutztat (Brandschutz/Risikobewertung)
- **[travel-beat](https://github.com/achimdehnert/travel-beat)** — DriftTales (Reisegeschichten)
- **[mcp-hub](https://github.com/achimdehnert/mcp-hub)** — MCP Server Collection
- **[dev-hub](https://github.com/achimdehnert/dev-hub)** — Developer Portal
- **[infra-deploy](https://github.com/achimdehnert/infra-deploy)** — Zentrales Deployment-API

## License

MIT License
