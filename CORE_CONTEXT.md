# CORE_CONTEXT — platform

> Pflicht-Lektüre für jeden Coding-Agent vor dem ersten Keystroke.
> Aktualisiert: 2026-05-15

## Was ist platform?

**Meta-Repo** des IIL-Ökosystems. Enthält **keine ausführbare App**, sondern
ist die Single-Source-of-Truth für plattformweite Entscheidungen, Conventions
und geteilte Werkzeuge der 45+ Hub-Repos.

**GitHub:** https://github.com/achimdehnert/platform
**ADR-Verzeichnis:** `docs/adr/` (168 ADRs, höchste Nummer 206)

## Rolle gegenüber anderen Repos

| Repo-Typ | Beziehung zu platform |
|---|---|
| **Hub-Apps** (dev-hub, risk-hub, bfagent, …) | konsumieren `shared_contracts/`, Workflows via Symlinks, Project-Facts-Generierung |
| **dev-hub** | hostet das Cockpit, liest ADRs/Catalog aus platform |
| **Org-Hubs** (ttz-hub, meiki-hub) | folgen platform-Conventions plus org-spezifische Overrides |

## Verzeichnis-Karte

| Pfad | Zweck |
|---|---|
| `docs/adr/` | Architecture Decision Records (SSoT, 168 Dateien) |
| `docs/concepts/` | Konzeptpapiere vor ADRs |
| `docs/templates/` | ADR-, Use-Case-, Settings-Templates für neue Repos |
| `docs/reference/` | Reference-Docs (audit/health-Checker, …) |
| `docs/guides/` | How-to-Guides (CI, Deploy, Multi-Env) |
| `shared_contracts/` | Pydantic-Models — Cross-Repo-Verträge |
| `registry/` | `repos.yaml` + `sync_registry.py` (drift-check liest hier) |
| `governance-deploy/` | Governance-Automation für Deploys |
| `tools/` | `repo_health_check.py`, `check_*.py`, `print_agent/` (MD → PDF) |
| `scripts/` | `audit_platform.py`, `adr_audit.py`, `drift_check.py` |
| `bootstrap.sh` | Public Setup-Script (verteilt Symlinks in alle Repos) |
| `.windsurf/workflows/` | Workflow-SSoT (wird über Symlinks in alle Repos verteilt) |
| `agents/` | Platform-Agent-Definitionen |
| `infra/`, `deployment/` | Infrastruktur-Configs für Cross-Repo-Deploys |

## Tech Stack

| Was | Wie |
|---|---|
| **Python** | 3.12 (Skripte in `tools/`, `scripts/`) |
| **YAML/Markdown** | Hauptformate für ADRs, Templates, Registry |
| **kein Django** | platform selbst hat kein Web-Backend; Django lebt in Hub-Repos |
| **Workflow-Engine** | GitHub Actions (`_ci-python.yml@v1` als reusable workflow) + Windsurf-Workflows |

## Was hier NICHT reingehört

- **App-Code** (gehört in den jeweiligen Hub)
- **Secrets** (immer `~/.secrets/` oder verschlüsselte `secrets.enc.env` im Hub)
- **Generierte PDFs** außer als Release-Artefakt unter `pdfs/`
- **Repo-spezifische Deploy-Configs** (gehören ins Hub-Repo)

## Pflicht-Lesestoff vor Änderungen

1. **`AGENT_HANDOVER.md`** — aktueller Stand, MCP-Tool-Mapping, Infra-Zugänge
2. **`AGENT_MEMORY.md`** — Drift-Episoden & Lessons Learned
3. **Letzte ADRs**: `ls docs/adr/ADR-*.md | sort -V | tail -5`

## Konventionen (Repo-spezifisch — schlagen Global)

- **ADR-Nummern monoton steigend** — nie wiederverwenden, auch nach Rejection
- **`shared_contracts/`-Änderungen** triggern Downstream-Builds → erst ADR, dann Code
- **`bootstrap.sh` ist Public Interface** — Breaking Changes sind ADR-pflichtig
- **Commits in `docs/adr/`**: scope = `adr`, nicht `docs`
- **Workflows in `.windsurf/workflows/`**: Änderungen brauchen `/workflow-review` vor Merge

## Verwandte Skills

| Skill | Zweck |
|---|---|
| `/adr`, `/adr-review`, `/adr-health` | ADR-Lifecycle |
| `/workflow-review`, `/workflow-index` | Workflow-Qualität |
| `/onboard-repo` | neues Repo ins Ökosystem |
| `/platform-audit`, `/repo-health-check` | Cross-Repo-Schwachstellen |
| `/governance-check` | vor neuer Funktionalität |
| `/session-docu` | Dokumentations-Audit (dieser hier) |

## Infrastruktur (Cross-Repo)

- **Prod-Server**: `88.198.191.108`
- **Staging-Server**: `88.99.38.75`
- **Orchestrator MCP**: `https://orchestrator.iil.pet/sse`
- **Dev-Hub Cockpit**: `https://devhub.iil.pet`
