---
trigger: always_on
---

# MCP Tools — Verfügbare Server & Fähigkeiten

> ⚠️ **MCP-Prefixes sind environment-spezifisch** — die Reihenfolge in `mcp_config.json`
> bestimmt den Prefix (`mcp0_`, `mcp1_`, ...). Immer zuerst prüfen welche Server aktiv sind.
> Konfig: `~/.codeium/windsurf/mcp_config.json`

## Referenz-Tabelle (WSL / Prod-Server)

| Prefix | Server | Zweck |
|--------|--------|-------|
| `mcp0_` | **deployment-mcp** | SSH, Docker, Compose, Git, DB, DNS, SSL, Nginx, CI/CD |
| `mcp1_` | **github** | Issues, PRs, Repos, Branches, Files, Reviews, Search |
| `mcp2_` | **orchestrator** | Memory, Task-Analyse, Agent-Team, Tests, Lint, Git-Ops |
| `mcp3_` | **outline-knowledge** | Wiki: Runbooks, Konzepte, Lessons, ADR-Suche |
| `mcp4_` | **paperless-docs** | Dokumente, Rechnungen, Archive |
| `mcp5_` | **platform-context** | Architektur-Regeln, ADR-Compliance, Banned Patterns |
| `mcp6_` | **playwright** | Browser-Automation, UI-Tests, Screenshots, Network |

## Dev Desktop (adehnert@dev-desktop) — aktuelle Konfiguration

| Prefix | Server | Status |
|--------|--------|--------|
| `mcp0_` | **github** | ✅ aktiv |
| `mcp1_` | **orchestrator** | ✅ aktiv |

## deployment-mcp (mcp0_) — Wichtigste Tools

- `mcp0_ssh_manage` — Remote Commands, File R/W, Health-Checks
- `mcp0_docker_manage` — Container + Compose Management
- `mcp0_git_manage` — Git auf Remote-Hosts
- `mcp0_database_manage` — PostgreSQL Management
- `mcp0_cicd_manage` — GitHub Actions, Deploy-Workflows
- `mcp0_system_manage` — Nginx, Services, Logs, Cron

## orchestrator (mcp2_) — Memory + Agent

- `mcp2_agent_memory_upsert` — Session-Summary in pgvector speichern
- `mcp2_agent_memory_context` — Relevante Memories laden (top_k)
- `mcp2_agent_memory_search` — Semantische Suche im Memory Store
- `mcp2_get_session_delta` — Was hat sich seit letzter Session geändert?
- `mcp2_check_recurring_errors` — Wiederkehrende Fehler ≥3x erkennen
- `mcp2_find_similar_errors` — Ähnliche Fehler im Error-Pattern-Store
- `mcp2_deploy_check` — Health-Check aller bekannten Deploy-Targets
- `mcp2_agent_plan_task` — Task in Branches + Sub-Tasks zerlegen
- `mcp2_run_workflow` — Autonomes AI Coding Workflow
- `mcp2_run_tests` — pytest für MCP-Module
- `mcp2_run_lint` — ruff für MCP-Module
- `mcp2_run_git` — Git-Ops (status, diff, log, add_commit_push)
- `mcp2_discord_notify` — Nachricht in Discord senden

## platform-context (mcp5_) — Architektur

- `mcp5_get_context_for_task(repo, file_type, topic)` — Architektur-Kontext für Task
- `mcp5_check_violations(code_snippet, file_type)` — ADR-Verletzungen prüfen
- `mcp5_get_banned_patterns(context)` — Verbotene Patterns abrufen
- `mcp5_get_project_facts(repo_name)` — Repo-Facts aus Knowledge Graph

## outline-knowledge (mcp3_) — Wiki

- `mcp3_search_knowledge(query, collection, limit)` — Volltext + Semantic Search
- `mcp3_get_document(document_id)` — Dokument lesen
- `mcp3_create_runbook / create_concept / create_lesson` — Neues Dokument
- `mcp3_update_document(document_id, content)` — Dokument aktualisieren
- `mcp3_list_recent(limit)` — Zuletzt geänderte Dokumente

## Regeln

- **Server (88.198.191.108)**: nur read-only via MCP — Deploys über `scripts/ship.sh` oder CI/CD
- **devuser hat KEIN sudo** → `ssh root@localhost "apt-get install -y <package>"`
- `mcp2_deploy_check health` nach jedem Deploy
- Bei Gate 2+ Tasks: `mcp2_agent_plan_task` zur Planung nutzen
- Memory IMMER via pgvector (`mcp2_agent_memory_*`) — kein Cascade-Memory-Fallback
