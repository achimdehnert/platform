# BF Agent Platform

Zentrales Meta-Repo für alle 41+ Repos des IIL Platform-Ökosystems:
Architektur-Entscheidungen (ADRs), geteilte CI/CD-Workflows, Governance-Tooling,
Repo-Registry und Windsurf-Rules.

## Quick Start — Neuer Computer / neue Session

**Einmalig nach dem Klonen:**
```bash
git clone https://github.com/achimdehnert/platform
bash platform/bootstrap.sh
source ~/.bashrc
```

`bootstrap.sh` richtet automatisch ein:
- `GITHUB_DIR` in `~/.bashrc`
- Windsurf-Workflows + Rules als Symlinks in alle lokalen Repos
- `project-facts.md` für alle Repos

Danach in Windsurf: `/session-start` zum Synchronisieren.

## Struktur

```
platform/
├── docs/adr/              # 149 Architecture Decision Records (MADR 4.0)
├── docs/concepts/         # Architektur-Konzepte, Guides, Referenz
├── .github/workflows/     # Reusable CI/CD Workflows (_ci-python, _build-docker, _deploy-*)
├── .windsurf/
│   ├── rules/             # 9 globale Rules (always_on) → Symlinks in alle Repos
│   └── workflows/         # 50+ Windsurf-Workflows (/session-start, /deploy, /adr, ...)
├── scripts/               # Ops-Scripts (gen_project_facts.py, sync-workflows.sh, ship.sh, ...)
├── agents/                # Governance-Agents (guardian, adr_scribe, context_reviewer)
├── concepts/              # Konzept-Dokumente
├── deployment/            # Docker Compose Templates, systemd Units
├── governance-deploy/     # Governance Django App
├── infra/                 # Infrastruktur-Konfiguration
├── orchestrator_mcp/      # MCP Orchestrator Module
├── registry/              # Repo-Registry (Metadaten)
├── scripts/               # Ops + Infra Scripts
├── shared/                # Geteilte Ressourcen
├── shared_contracts/      # Cross-Repo Python Contracts (Events, Schemas)
├── static-sites/          # iil.pet Landing Page
├── tools/                 # Dev-Tools (repo_checker, htmx-checker, bf-deploy CLI)
└── _ARCHIVED/             # Archivierte Monorepo-Artefakte (packages/, docs-infrastructure/)
```

## Repo-Registry (Master Identifier)

**Single Source of Truth für alle 41 Repos:**

```bash
# project-facts.md für alle Repos generieren/aktualisieren
python3 scripts/gen_project_facts.py

# Force-Regenerate alle
python3 scripts/gen_project_facts.py --force

# Einzelnes Repo
python3 scripts/gen_project_facts.py risk-hub
```

Registry-Datei: `scripts/repo-registry.yaml`

## Windsurf Rules (Global)

Alle Repos erhalten diese Rules automatisch als Symlinks:

| Rule | Trigger | Inhalt |
|------|---------|--------|
| `project-facts.md` | always_on | Repo-spezifische Fakten (Port, DB, URL) |
| `mcp-tools.md` | always_on | MCP-Server mcp0_–mcp6_ Referenz |
| `reviewer.md` | always_on | Code-Review Standards + verbotene Patterns |
| `platform-principles.md` | always_on | Architektur-Vertrag (Service Layer, DB-First) |
| `iil-packages.md` | always_on | iil-Package Ökosystem (aifw, promptfw, ...) |
| `testing.md` | always_on | Test-Naming, pytest, Factory Boy |
| `django-models-views.md` | always_on | Django Service Layer Regeln |
| `docker-deployment.md` | always_on | Docker/Compose/Deploy Regeln |
| `htmx-templates.md` | always_on | HTMX Playbook (hx-target, hx-indicator, ...) |

Rules verteilen: `GITHUB_DIR=~/github bash scripts/sync-workflows.sh`

## Reusable CI/CD Workflows

Alle Repos rufen diese auf via `uses: achimdehnert/platform/.github/workflows/...`:

| Workflow | Zweck |
|----------|-------|
| `_ci-python.yml` | Python CI (ruff, pytest, coverage) |
| `_build-docker.yml` | Docker Build + Push zu GHCR |
| `_deploy-hetzner.yml` | Deploy auf Hetzner via SSH |
| `_deploy-unified.yml` | Unified Deploy (CI + Build + Deploy) |
| `_ci-odoo.yml` | Odoo-spezifisches CI |

## MCP-Server (Windsurf)

| Prefix | Server | Zweck |
|--------|--------|-------|
| `mcp0_` | deployment-mcp | SSH, Docker, Git, DB, DNS, SSL, Nginx |
| `mcp1_` | github | Issues, PRs, Repos, Files, Reviews |
| `mcp2_` | orchestrator | Memory, Task-Analyse, Agent-Team, Tests |
| `mcp3_` | outline-knowledge | Wiki: Runbooks, Konzepte, Lessons |
| `mcp4_` | paperless-docs | Dokumente, Rechnungen |
| `mcp5_` | platform-context | Architektur-Regeln, ADR-Compliance |
| `mcp6_` | playwright | Browser-Automation, UI-Tests |

## Wichtigste Scripts

| Script | Zweck |
|--------|-------|
| `scripts/gen_project_facts.py` | Master Repo Identifier — generiert project-facts.md |
| `scripts/repo-registry.yaml` | Registry aller 41 Repos (Port, URL, DB, Typ) |
| `scripts/sync-workflows.sh` | Windsurf-Workflows als Symlinks in alle Repos |
| `scripts/ship.sh` | Standard-Deploy (Build → Push → SSH Deploy) |
| `scripts/deploy.sh` | Hetzner Deploy Script |
| `scripts/adr_next_number.py` | Nächste ADR-Nummer ermitteln |
| `scripts/sync_adrs_to_outline.sh` | ADRs nach Outline Wiki synchronisieren |

## ADRs

149 Architecture Decision Records in `docs/adr/` (MADR 4.0 Format).
Neue ADR: `/adr` Workflow in Windsurf.
Nächste Nummer: `python3 scripts/adr_next_number.py`

## Infrastruktur

- **Prod-Server**: `88.198.191.108` (Hetzner) — Deploy via `scripts/ship.sh` oder CI/CD
- **Registry**: `ghcr.io/achimdehnert/{repo}`
- **Secrets lokal**: `/home/devuser/shared/secrets/` (31 Dateien)
- **Secrets Server**: `/opt/shared-secrets/api-keys.env`
- **devuser**: KEIN sudo → `ssh root@localhost "apt-get install -y <package>"`
