# BF Agent Platform

[![License](https://img.shields.io/badge/license-MIT-green)]()

> Zentrales Meta-Repo des IIL Platform-Ökosystems:
> Architektur-Entscheidungen (ADRs), geteilte CI/CD-Workflows, Governance-Tooling,
> Repo-Registry und Print-Agent (MD→PDF). **Kein App-Code, kein Django** — der lebt
> in den Hub-Repos (dev-hub, risk-hub, …).

Live-Zahlen statt eingefrorener Werte (Repo- und ADR-Bestand ändern sich laufend):

```bash
# Anzahl Repos in der Registry
python3 -c "import yaml; print(len(yaml.safe_load(open('registry/canonical.yaml'))['repos']))"

# Anzahl + höchste ADR-Nummer
ls docs/adr/ADR-*.md | wc -l
ls docs/adr/ADR-*.md | grep -oE 'ADR-[0-9]+' | sort -V | tail -1
```

---

## Wer sollte hier lesen?

| Zielgruppe | Einstieg |
|---|---|
| **Mensch** (neu im Projekt, Setup, Orientierung) | dieses README |
| **Coding-Agent** (Claude Code) | [`CORE_CONTEXT.md`](CORE_CONTEXT.md) — Pflicht-SSoT vor dem ersten Keystroke, plus [`AGENT_HANDOVER.md`](AGENT_HANDOVER.md) für den aktuellen Session-Stand |

## Quick Start — Neuer Computer / neue Session

**Einmalig nach dem Klonen:**
```bash
git clone https://github.com/achimdehnert/platform
bash platform/bootstrap.sh
source ~/.bashrc
```

`bootstrap.sh` richtet automatisch ein:
- `GITHUB_DIR` in `~/.bashrc`
- Claude-Code-Skills (Symlinks/generierte Kopien) in `~/.claude/commands/` — siehe CC-first unten
- `project-facts.md` für alle Repos

**Tests lokal:**
```bash
python3 -m pytest tools/tests/ -q
```

## Coding-Interface: Claude Code (CC-first, ADR-230)

Seit **ADR-230** (accepted 2026-05-30) läuft Coding **nur über Claude Code**. Die
Skills liegen kanonisch in `.windsurf/workflows/` (Quelle) und werden per
`tools/cc-skill-dist/generate.py` deterministisch nach `~/.claude/commands/` verteilt:

```bash
python3 tools/cc-skill-dist/generate.py --target ~/.claude/commands --allow-live
python3 tools/cc-skill-dist/doctor.py   # Drift-Check
```

**Windsurf ist kein Coding-Ziel mehr** — nur noch **Review-only** für ein generiertes
ADR-Review-Subset (`tool_targets: [windsurf-review]`, ADR-229/230). Details, Rollout-Stand
und das volle MCP-Tool-Mapping stehen nicht hier, sondern in
[`AGENT_HANDOVER.md`](AGENT_HANDOVER.md) (aktuell) bzw.
[`AGENT_HANDOVER_ARCHIVE.md`](AGENT_HANDOVER_ARCHIVE.md) (historisch) — die Prefixe
`mcp0_`–`mcp6_` sind volatil und werden dort gepflegt, nicht dupliziert.

## Struktur (Grobkarte)

```
platform/
├── docs/adr/              # Architecture Decision Records (MADR 4.0) — Bestand: s.o.
├── docs/concepts/         # Architektur-Konzepte, Guides, Referenz
├── .github/workflows/     # Reusable CI/CD Workflows (_ci-python, _build-docker, _deploy-*)
├── .windsurf/workflows/   # Skill-Quelle (CC-first, ADR-230) — Windsurf selbst nur Review-only
├── scripts/                # Ops-Scripts (gen_project_facts.py, sync-workflows.sh, ship.sh, ...)
├── agents/                 # Governance-Agents (guardian, adr_scribe, context_reviewer)
├── governance-deploy/      # Governance Django App
├── infra/, deployment/     # Infrastruktur-Konfiguration
├── registry/                # SSoT canonical.yaml (Repo-Registry, ADR-234)
├── shared_contracts/        # Cross-Repo Python Contracts (Events, Schemas)
├── tools/                   # Dev-Tools (repo_health_check, cc-skill-dist, print_agent, ...)
└── _ARCHIVED/                # Archivierte Monorepo-Artefakte
```

Vollständige, gepflegte Verzeichnis-Karte inkl. Zweck jedes Pfads: [`CORE_CONTEXT.md`](CORE_CONTEXT.md).

## Repo-Registry

**Single Source of Truth**: `registry/canonical.yaml` (ADR-234) — generiert die Views
`registry/repos.yaml` / `scripts/repo-registry.yaml`. Zugriff nur über
`tools/registry_api.py`, nicht die generierten Views direkt lesen/editieren.

`project-facts.md` wird automatisch an die Repo-Root jedes Django-Repos gepusht:
```bash
python3 scripts/gen_project_facts.py [--force] [repo-name]
```

## Reusable CI/CD Workflows

Alle Repos rufen diese auf via `uses: achimdehnert/platform/.github/workflows/...`:

| Workflow | Zweck |
|----------|-------|
| `_ci-python.yml` | Python CI (ruff, pytest, coverage) |
| `_build-docker.yml` | Docker Build + Push zu GHCR |
| `_deploy-hetzner.yml` | Deploy auf Hetzner via SSH |
| `_deploy-unified.yml` | Unified Deploy (CI + Build + Deploy) |
| `_ci-odoo.yml` | Odoo-spezifisches CI |

## Dokumentation

| Dokument | Inhalt |
|---|---|
| [`CORE_CONTEXT.md`](CORE_CONTEXT.md) | Agent-SSoT: Rolle, Verzeichnis-Karte, Tech-Stack, Konventionen |
| [`AGENT_HANDOVER.md`](AGENT_HANDOVER.md) | Aktueller Session-Stand, Infra-Zugänge, Deploy-Targets |
| [docs/adr/](docs/adr/) | Architecture Decision Records (MADR 4.0) |
| [docs/concepts/](docs/concepts/) | Architektur-Konzepte, Entscheidungshintergründe |
| [docs/guides/](docs/guides/) | How-To Anleitungen (Deployment, Setup, Workflows) |
| [docs/reference/](docs/reference/) | API, Config, Scripts Referenz |
| [docs/templates/](docs/templates/) | Canonical Templates (README, CHANGELOG, CONTRIBUTING, ADR) |
| [tools/print_agent/](tools/print_agent/) | MD→PDF Generator (SSoT für alle Repos) |
| [CHANGELOG.md](CHANGELOG.md) | Versionshistorie |

Neuen ADR anlegen: `/adr`-Skill in Claude Code; nächste freie Nummer via
`python3 scripts/adr_next_number.py`.

## Infrastruktur

- **Prod-Server**: `88.198.191.108` (Hetzner) — Deploy via `scripts/ship.sh` oder CI/CD
- **Registry**: `ghcr.io/achimdehnert/{repo}`
- **Secrets lokal**: `~/.secrets/` (github_PAT, github_token, groq_api_key, outline_api_token, cloudflare_*)
- **Secrets Server**: `/opt/shared-secrets/api-keys.env`
- **pgvector**: Container `mcp_hub_db` auf Prod `88.198.191.108:15435` — Tunnel via `ssh-tunnel-postgres` systemd-Service
- **devuser**: KEIN sudo → `ssh root@localhost "apt-get install -y <package>"`

Details, aktueller Stand, Betriebs-Runbooks: [`AGENT_HANDOVER.md`](AGENT_HANDOVER.md).
