---
trigger: always_on
---

# MCP Tools — Verfügbare Server & Fähigkeiten

> ⚠️ **MCP-Prefixes sind environment-spezifisch** — die Reihenfolge in `mcp_config.json`
> bestimmt den Prefix (`mcp0_`, `mcp1_`, ...). Immer zuerst prüfen welche Server aktiv sind.
> Konfig: `~/.codeium/windsurf/mcp_config.json`

## Prefix-Bestimmung zur Laufzeit (PFLICHT vor MCP-Calls)

Cascade bestimmt den korrekten Prefix wie folgt:

1. **project-facts.md lesen** (always_on) — enthält die aktuelle MCP-Prefix-Tabelle für diese Umgebung
2. **Fallback**: `~/.codeium/windsurf/mcp_config.json` lesen — Reihenfolge der Server = Prefix-Zuordnung
3. **Nie annehmen** — kein Prefix ist universell!

```bash
# Schnell-Check: welche MCP-Server sind aktiv?
cat ~/.codeium/windsurf/mcp_config.json | python3 -c "
import json, sys
cfg = json.load(sys.stdin)
servers = list(cfg.get('mcpServers', {}).keys())
for i, s in enumerate(servers): print(f'mcp{i}_ = {s}')
"
```

## Bekannte Umgebungen

### WSL / Prod-Server (Standard-Konfiguration)

| Prefix | Server | Zweck |
|--------|--------|-------|
| `mcp0_` | **deployment-mcp** | SSH, Docker, Compose, Git, DB, DNS, SSL, Nginx, CI/CD |
| `mcp1_` | **github** | Issues, PRs, Repos, Branches, Files, Reviews, Search |
| `mcp2_` | **orchestrator** | Memory, Task-Analyse, Agent-Team, Tests, Lint, Git-Ops |
| `mcp3_` | **outline-knowledge** | Wiki: Runbooks, Konzepte, Lessons, ADR-Suche |
| `mcp4_` | **paperless-docs** | Dokumente, Rechnungen, Archive |
| `mcp5_` | **platform-context** | Architektur-Regeln, ADR-Compliance, Banned Patterns |
| `mcp6_` | **playwright** | Browser-Automation, UI-Tests, Screenshots, Network |

### Dev Desktop (adehnert@dev-desktop — andere Reihenfolge!)

| Prefix | Server | Status |
|--------|--------|--------|
| `mcp0_` | **github** | ✅ aktiv |
| `mcp1_` | **orchestrator** | ✅ aktiv |

> ⚠️ Auf Dev Desktop ist `mcp0_` = github und `mcp1_` = orchestrator.
> Memory-Calls lauten dort `mcp1_agent_memory_*`, NICHT `mcp2_agent_memory_*`.
> **Immer project-facts.md prüfen** — sie dokumentiert die Umgebung verbindlich.

## Orchestrator — Memory + Agent (je nach Prefix)

> Prefix aus project-facts.md entnehmen. Hier `{ORC}` als Platzhalter.

- `{ORC}_agent_memory_upsert` — Session-Summary / Decision in pgvector speichern
- `{ORC}_agent_memory_context` — Relevante Memories laden (top_k)
- `{ORC}_agent_memory_search` — Semantische Suche im Memory Store
- `{ORC}_get_session_delta` — Was hat sich seit letzter Session geändert?
- `{ORC}_check_recurring_errors` — Wiederkehrende Fehler ≥3x erkennen
- `{ORC}_find_similar_errors` — Ähnliche Fehler im Error-Pattern-Store
- `{ORC}_deploy_check` — Health-Check aller bekannten Deploy-Targets
- `{ORC}_agent_plan_task` — Task in Branches + Sub-Tasks zerlegen
- `{ORC}_run_workflow` — Autonomes AI Coding Workflow
- `{ORC}_discord_notify` — Nachricht in Discord senden
- `{ORC}_log_error_pattern` — Fehler-Pattern für alle Repos sichern

## GitHub — je nach Prefix

> Prefix aus project-facts.md entnehmen. Hier `{GH}` als Platzhalter.

- `{GH}_get_file_contents` — Datei/Verzeichnis lesen (inkl. ADR-Listing)
- `{GH}_push_files` — Mehrere Dateien in einem Commit pushen
- `{GH}_create_or_update_file` — Einzelne Datei anlegen/aktualisieren
- `{GH}_create_issue` / `{GH}_list_issues` — Issues verwalten
- `{GH}_create_pull_request` — PR erstellen

## deployment-mcp (nur WSL/Prod — `mcp0_`)

- `mcp0_ssh_manage` — Remote Commands, File R/W, Health-Checks
- `mcp0_docker_manage` — Container + Compose Management
- `mcp0_git_manage` — Git auf Remote-Hosts
- `mcp0_database_manage` — PostgreSQL Management
- `mcp0_cicd_manage` — GitHub Actions, Deploy-Workflows

## platform-context (nur WSL/Prod — `mcp5_`)

- `mcp5_get_context_for_task(repo, file_type, topic)`
- `mcp5_check_violations(code_snippet, file_type)`
- `mcp5_get_banned_patterns(context)`
- `mcp5_get_project_facts(repo_name)`

## pgvector — Central Memory Store (alle Repos)

| Parameter | Wert |
|-----------|------|
| **Container** | `mcp_hub_db` (`pgvector/pgvector:pg16`) |
| **Server** | Prod `88.198.191.108` |
| **Port auf Server** | `127.0.0.1:15435` |
| **Lokaler Zugriff** | `localhost:15435` via SSH-Tunnel |
| **systemd Service** | `ssh-tunnel-postgres` (dev desktop) |

> pgvector ist der **zentrale Memory-Store für ALLE Repos**.
> ADR-Entscheidungen, Session-Summaries, Error-Patterns — alles landet hier.
> Damit ist jede Information in jeder künftigen Session überall verfügbar.

```bash
# Tunnel-Status prüfen:
ss -tlnp | grep 15435 && echo "✅ aktiv" || echo "❌ inaktiv"
# Starten: sudo systemctl start ssh-tunnel-postgres
```

## Memory-Key-Konventionen (repo-übergreifend einheitlich)

| Typ | entry_key Format | entry_type |
|-----|-----------------|------------|
| ADR-Entscheidung | `adr:{repo}:ADR-{NNN}` | `decision` |
| Session-Summary | `session:{YYYY-MM-DD}:{repo}` | `context` |
| Error-Pattern | automatisch via `log_error_pattern` | `error_pattern` |
| Repo-Kontext | `repo:{repo}:context` | `repo_context` |
| Offene Aufgabe | `task:{repo}:{id}` | `open_task` |

## Regeln

- **Prefix IMMER aus project-facts.md lesen** — nie hardcoden
- **KEIN Fallback auf Cascade Memory** — pgvector MUSS laufen
- `{ORC}_deploy_check health` nach jedem Deploy
- Bei Gate 2+ Tasks: `{ORC}_agent_plan_task` zur Planung nutzen
- Memory IMMER via pgvector — kein Cascade-Memory-Fallback
