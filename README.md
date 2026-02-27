# BF Agent Platform

Shared packages, reusable CI/CD workflows, governance tooling, and architecture documentation for the BF Agent ecosystem.

## Struktur

```
platform/
├── packages/              # 15 shared Python packages
├── agents/                # Autonomous governance agents (guardian, drift_detector, adr_scribe, ...)
├── docs/adr/              # 90+ Architecture Decision Records (MADR 4.0)
├── .github/workflows/     # 20 reusable CI/CD workflows (_ci-python, _build-docker, _deploy-hetzner, ...)
├── tools/                 # repo_checker, check_htmx_patterns, check_design_tokens
├── scripts/               # Ops/infra scripts (adr_next_number, hardcode_scanner, ...)
├── governance-deploy/     # Standalone governance Django app
├── deployment/            # Docker Compose templates, systemd units
└── concepts/              # Architecture concept docs
```

## Packages

| Package | Version | Beschreibung |
|---------|---------|--------------|
| `platform-context` | 0.5.0 | Core Django foundation (Context, Audit, Outbox, Tenancy, HTMX) |
| `bfagent-core` | 0.2.0 | BFAgent-spezifische Core-Komponenten (Auth, Permissions, Models) |
| `bfagent-llm` | — | LiteLLM-Backend + DB-driven Model-Routing (ADR-089) |
| `creative-services` | 0.3.0 | LLM Client, Adapters, Story/Character/World-Generierung |
| `django-tenancy` | — | Subdomain-basierte Multi-Tenancy |
| `chat-agent` | — | Chat-Konversations-Handling |
| `chat-logging` | — | Persistentes Konversations-Logging (ADR-037) |
| `docs-agent` | — | Dokumentations-Agent mit Pre-commit-Hooks |
| `platform-notifications` | — | Multi-Channel Notification Registry (ADR-088) |
| `platform-search` | — | Hybrid pgvector + FTS Search (ADR-087) |
| `task_scorer` | — | Task-Scoring und Routing-Engine (ADR-023) |
| `mcp-governance` | — | MCP Tool Governance |
| `inception-mcp` | — | Meta-MCP Tooling |
| `cad-services` | — | IFC/DXF CAD-Verarbeitung |
| `sphinx-export` | — | Sphinx → Markdown Export |

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
| risk-hub | Schutztat | https://demo.schutztat.de | ✅ Production |
| travel-beat | DriftTales | https://drifttales.com | ✅ Production |
| weltenhub | Weltenforger | https://weltenforger.com | ✅ Production |
| dev-hub | DevHub | https://devhub.iil.pet | ✅ Production |
| pptx-hub | Prezimo | https://prezimo.com | ✅ Production |
| coach-hub | KI ohne Risiko | https://kiohnerisiko.de | ✅ Production |
| trading-hub | — | https://trading-hub.iil.pet | ✅ Production |
| wedding-hub | — | https://wedding-hub.iil.pet | ✅ Production |
| cad-hub | nl2cad | https://nl2cad.de | ⏸ Gestoppt |

## Tech Stack

| Bereich | Technologie |
|---------|-------------|
| Framework | Django 5.x |
| APIs | DRF (dev-hub) / Django Ninja (risk-hub) |
| Frontend | HTMX + TailwindCSS |
| Datenbank | PostgreSQL |
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
