# MCP-Server Inventar

> **SSoT** für alle MCP-Server der Plattform (ADR-176)
> Stand: 2026-04-30

## Produktive Server

| Name | Prefix (WSL) | Prefix (DevDesktop) | Source | Zweck | Status |
|---|---|---|---|---|---|
| `deployment-mcp` | `mcp0_` | — | `mcp-hub/deployment_mcp/` | SSH, Docker, Compose, Git, DB, DNS, SSL, Nginx | ✅ Production |
| `github` | `mcp1_` | `mcp0_` | externes Paket (`@modelcontextprotocol/server-github`) | Issues, PRs, Repos, Files, Reviews | ✅ Production |
| `orchestrator` | `mcp2_` | `mcp1_` | `mcp-hub/orchestrator_mcp/` | Memory (pgvector), Task-Analyse, Agent-Team, Tests, Lint | ✅ Production |
| `outline-knowledge` | `mcp3_` | `mcp2_` | `mcp-hub/outline_mcp/` | Outline Wiki: Runbooks, Konzepte, Lessons, ADR-Suche | ✅ Production (migriert 2026-04-30 aus `_ARCHIVED`) |
| `paperless-docs` | `mcp4_` | — | `mcp-hub/paperless_mcp/` | Dokumente, Rechnungen, Archive | ✅ Production |
| `platform-context` | `mcp5_` | — | `mcp-hub/platform_context_mcp/` | Architektur-Regeln, ADR-Compliance, Banned Patterns | ✅ Production |
| `playwright` | `mcp6_` | — | externes Paket (`@playwright/mcp`) | Browser-Automation, UI-Tests, Screenshots | ✅ Production |

## In Entwicklung (offiziell, noch nicht in Config)

| Name | Source | Zweck | Nächste Schritte |
|---|---|---|---|
| `query-agent` | `mcp-hub/query_agent_mcp/` | RAG-Query über Plattform-Dokumentation (pgvector + LangGraph) | Config-Registrierung, E2E-Test |
| `registry` | `mcp-hub/registry_mcp/` | Platform Component Discovery (ADR-015) | Migrations-Set, Seed-Script |
| `ifc` | `mcp-hub/ifc_mcp/` | IFC-Dateien (BIM) Processing | `__main__.py`, Config, Tests |
| `illustration` | `mcp-hub/illustration_mcp/` | AI-Illustration Generation | `__main__.py`, Config, Tests |
| `travel` | `mcp-hub/travel_mcp/` | Multi-Provider Travel Search & Booking | `__main__.py`, Config, Tests |
| `web-intelligence` | `mcp-hub/web_intelligence_mcp/` | Web fetch + extract + Wikipedia | `__main__.py`, Config, Tests |
| `llm` | `mcp-hub/llm_mcp/` | LLM-Abfragen via MCP-Protokoll | Config-Registrierung |

## Separate HTTP-Services (kein MCP)

| Name | Source | Zweck |
|---|---|---|
| `llm_gateway` | `mcp-hub/llm_gateway/` (ex `llm_mcp_service`) | FastAPI HTTP-Gateway für LLM (ADR-115), Usage-Logging |

## Archiviert

| Name | Begründung |
|---|---|
| *(keine zurzeit)* | — |

## Offene Refactorings (ADR-176 Follow-ups)

- [ ] **`llm_mcp_service/` → `llm_gateway/` umbenennen**
  Betroffene Dateien: `docker-compose.llm-mcp.yml`, Imports in 12 Python-Files, Dockerfile, pyproject.toml.
  Aufwand: ~1h (Imports + Tests).

- [ ] **`packages/iil-testkit` extrahieren**
  Aktuell vendored in mcp-hub + separat in `github/testkit/` (PyPI).
  Ziel: nur PyPI-Dependency `iil-testkit>=X.Y` in `mcp-hub/pyproject.toml`.
  Aufwand: ~30min (imports prüfen).

- [ ] **`packages/creative-services` Status klären**
  Vendored in mcp-hub — eigenständiges Paket oder mcp-hub-exklusiv? ADR nötig.

- [ ] **Start-Scripts `/home/devuser/.local/bin/start-*-mcp.sh` zu `mcp-hub/scripts/` migrieren**
  Alte Scripts in `~/.local/bin/` deprecaten und nach Migration löschen.

## Prefix-Regel

Prefix = **Reihenfolge** in `~/.codeium/windsurf/mcp_config.json`.
Pro Environment kann die Reihenfolge abweichen — deshalb zwei Spalten oben.

Cascade liest den Prefix immer zur Laufzeit aus `project-facts.md` des aktiven Repos + fallback aus `mcp_config.json`.

## Verantwortlichkeit

- **Code-Änderungen**: `mcp-hub/<name>_mcp/` — PR gegen `main`
- **Config-Änderungen**: `platform/templates/mcp_config.<env>.json` — PR gegen `main`
- **Inventar-Pflege** (diese Datei): bei jedem neuen/archivierten Server
