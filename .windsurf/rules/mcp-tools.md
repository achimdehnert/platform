---
trigger: always_on
---

# MCP Tools — Verfügbare Server & Fähigkeiten

## Aktive MCP-Server (Windsurf)

| Server | Tools | Zweck |
|--------|-------|-------|
| **deployment-mcp** | SSH, Docker, Git, DB, DNS, SSL, Firewall, Env, CI/CD | Server-Management, Deployment |
| **github** | Issues, PRs, Repos, Branches, Files, Reviews | GitHub API (vollständig) |
| **platform-context** | get_context_for_task, check_violations, get_banned_patterns | Architektur-Regeln, ADR-Compliance |
| **orchestrator** | analyze_task, deploy_check, agent_team_status, agent_plan_task, run_tests, run_lint, run_git | Task-Analyse, Agent-Team, Quality |
| **cloudflare-api** | DNS, Zones, Tunnels, Security | Cloudflare Management |

## orchestrator MCP — Neue Tools

### `deploy_check`
Prüft Deployment-Status für bekannte Repos.
- `action: targets` — zeigt alle bekannten Deploy-Konfigurationen
- `action: health` — curl Health-Check (repo oder custom URL)
- `action: status` — docker compose ps via SSH

### `agent_team_status`
Zeigt den aktuellen Stand des AI Engineering Squad:
- Aktive Agenten (Developer, Tester, Guardian)
- 15 interne Tools + 25 Shell-Commands
- Planner v1 (rule-based) + v2 (LLM für architectural Tasks)
- Bekannte Deploy-Targets

### `agent_plan_task`
Zerlegt eine Task-Beschreibung in Branches und Sub-Tasks:
- `description` — Task-Beschreibung
- `task_type` — feature, bugfix, refactor, test, docs, infra
- `complexity` — trivial, simple, moderate, complex, architectural

## deployment-mcp — Wichtigste Tools

- `mcp5_docker_manage` — Container + Compose Management
- `mcp5_ssh_manage` — Remote Commands, File R/W, Health-Checks
- `mcp5_git_manage` — Git auf Remote-Hosts
- `mcp5_database_manage` — PostgreSQL Management
- `mcp5_cicd_manage` — GitHub Actions, Deploy-Workflows
- `mcp5_system_manage` — Nginx, Services, Logs, Cron

## Regeln

- PROD-Server (88.198.191.108) nur **read-only** via MCP
- Deploys über `scripts/ship.sh` oder CI/CD — nie direkt
- `deploy_check health` nach jedem Deploy
- Bei Gate 2+ Tasks: `agent_plan_task` zur Planung nutzen
