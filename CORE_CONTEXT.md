# CORE_CONTEXT — platform

> Pflicht-Lektüre für jeden Coding-Agent vor dem ersten Keystroke.
> Aktualisiert: 2026-06-30

## Was ist platform?

**Meta-Repo** des IIL-Ökosystems. Enthält **keine ausführbare App**, sondern
ist die Single-Source-of-Truth für plattformweite Entscheidungen, Conventions
und geteilte Werkzeuge der Hub-Repos (Anzahl live:
`python3 -c "import yaml; print(len(yaml.safe_load(open('registry/canonical.yaml'))['repos']))"`).

**GitHub:** https://github.com/achimdehnert/platform
**ADR-Verzeichnis:** `docs/adr/` (Bestand live: `ls docs/adr/ADR-*.md | wc -l`; höchste Nr.: `ls docs/adr/ADR-*.md | grep -oE 'ADR-[0-9]+' | sort -V | tail -1`)

## Rolle gegenüber anderen Repos

| Repo-Typ | Beziehung zu platform |
|---|---|
| **Hub-Apps** (dev-hub, risk-hub, bfagent, …) | konsumieren `shared_contracts/`, Workflows via Symlinks, Project-Facts-Generierung |
| **dev-hub** | hostet das Cockpit, liest ADRs/Catalog aus platform |
| **Org-Hubs** (ttz-hub, meiki-hub) | folgen platform-Conventions plus org-spezifische Overrides |

## Verzeichnis-Karte

| Pfad | Zweck |
|---|---|
| `docs/adr/` | Architecture Decision Records (SSoT; live: `ls docs/adr/ADR-*.md | wc -l`) |
| `docs/konzepte/` | **Aktive** Konzept-Artefakte (KONZ-platform-NNN, via `/konzept`-Skill) |
| `docs/concepts/` | Legacy-CONCEPT-Dateien (Vor-`/konzept`-Ära, nur lesen) |
| `docs/templates/` | ADR-, Use-Case-, Settings-Templates für neue Repos |
| `docs/reference/` | Reference-Docs (audit/health-Checker, …) |
| `docs/guides/` | How-to-Guides (CI, Deploy, Multi-Env) |
| `shared_contracts/` | Pydantic-Models — Cross-Repo-Verträge (Status/Konsumenten: Issue #820) |
| `registry/` | **SSoT `canonical.yaml`** (ADR-234) → Views `repos.yaml`/`scripts/repo-registry.yaml` (generiert, gate-erzwungen); Accessor `tools/registry_api.py`. Owner-Auflösung: `registry_api.owner(repo)` |
| `governance/` | Policy-Konfiguration: `rulesets/` (ADR-242 Branch-Protection), `exit-classes.yaml`, `backup/` |
| `_ARCHIVED/governance-deploy/` | Archivierte tote Django-Alt-App (via #829 aus dem Root verschoben, Issue #817) |
| `tools/` | `repo_health_check.py`, `check_*.py`, `print_agent/` (MD → PDF), `registry_api.py` |
| `scripts/` | `audit_platform.py`, `adr_audit.py`, `drift_check.py`, `gen_adr_index.py` |
| `packages/` | Eigenständige Sub-Packages (z. B. `adr-review` — eigene pyproject/tests) |
| `orchestrator_mcp/` | Gespiegelter Code des extern laufenden Orchestrator-Service (ADR-256) — kein hier deploybares Django |
| `bootstrap.sh` | Public Setup-Script (verteilt Symlinks in alle Repos) |
| `.windsurf/workflows/` | Workflow-SSoT (wird über Symlinks in alle Repos verteilt) |
| `agents/` | Platform-Agent-Definitionen |
| `infra/`, `deployment/` | Infrastruktur-Configs für Cross-Repo-Deploys |
| `spikes/`, `audits/`, `baselines/`, `shared/`, `pdfs/`, `skills/`, `_ARCHIVED/` | Alt-/Arbeitsbestand — nichts Neues hier ablegen (`concepts/` wurde via #829 aufgelöst, Issue #817) |

**Registry-Schreibpfad** (`registry/canonical.yaml` editieren → `make registry-build` →
`make registry-verify`) — nie die generierten Views (`repos.yaml`/`scripts/repo-registry.yaml`)
von Hand anfassen, das `verify`-Gate schlägt sonst fehl.

## Lokales Setup & Testbefehl (SSoT)

```bash
make setup   # requirements-dev.txt + pre-commit install + install-push-hook (einmalig)
make test    # = pytest tools/tests/ (ruff läuft separat über `make lint`)
```

`make test` deckt **nicht** die volle CI-Testfläche ab: `.github/workflows/tools-tests.yml`
ist die SSoT für den CI-relevanten Gate-Umfang (aktuell zusätzlich `tests/test_render_staging.py`,
`tests/doc_profile_check/`, `tools/claude-hooks/tests/` — Datei live prüfen statt diese Liste
zu vertrauen, sie ändert sich unabhängig von hier). `ruff` ist **kein** CI-Gate, nur lokales
`make lint`. Nacktes `pytest` läuft zusätzlich über `tests/` (megatest + Altbestand, teils rot —
Triage: Issue #819).

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
2. **CC-Memory-Index** (auto-geladen) — Drift-Episoden & Lessons Learned.
   ⚠️ **`AGENT_MEMORY.md` ist deprecated** (Cascade-Ära, alle Einträge expired,
   Stand 2026-05-05) — nicht mehr als Lessons-Quelle lesen.
3. **Letzte ADRs**: `ls docs/adr/ADR-*.md | sort -V | tail -5`

## Konventionen (Repo-spezifisch — schlagen Global)

- **ADR-Nummern monoton steigend** — nie wiederverwenden, auch nach Rejection
- **`shared_contracts/`-Änderungen** triggern Downstream-Builds → erst ADR, dann Code
- **`bootstrap.sh` ist Public Interface** — Breaking Changes sind ADR-pflichtig
- **Commits in `docs/adr/`**: scope = `adr`, nicht `docs`
- **Org-Resolution & neue iil-* Pakete (ADR-255)**: Der GitHub-Org-Ziel für die
  `iil-*` PyPI-Familie ist **`iilgmbh`** (PyPI-Org **`iil`**, nicht `iilgmbh` —
  Trusted Publishing matcht den GitHub-Owner). **Jedes _neue_ `iil-*` Paket wird
  org-native angelegt**: Repo direkt unter `iilgmbh`, hardened OIDC `publish.yml`
  (REC-7), Eintrag in `registry/iil-migration.yaml` ab Tag 1 (REC-14). Org-Auflösung
  ist **explizit, kein stiller `achimdehnert`-Fallback** für `iil-*` (REC-4). Der
  **Ist-Owner** steht in `tools/registry-canonical.py` `repo_owner` (nur Repos, die
  _wirklich_ schon dort liegen); der **Ziel-Owner** der laufenden Migration steht
  ausschließlich in `registry/iil-migration.yaml` (SSoT, REC-3) — Reality-Check:
  `python3 tools/iil_migration_check.py`.
- **Workflows in `.windsurf/workflows/`**: **substanzielle** Änderungen brauchen `/workflow-review`
  vor Merge (neue/geänderte Schritte, Logik, Tool-Calls, Steuerfluss, semantische Edits) — Ergebnis
  im PR-Body zitieren. **Ausnahme (session-retro 2026-07-02, EF-4/R-5):** rein **mechanische,
  deterministische** Änderungen (Prefix-/Token-Sweep, Umbenennung nach fixem Muster, Refresh
  generierten Contents) brauchen **kein** manuelles `/workflow-review`, wenn (a) der PR-Body sie
  ausdrücklich als mechanisch kennzeichnet und (b) die automatisierten Gates greifen
  (`skill-mcp-signatures.yml` = MCP-Signatur-Lint, `cc-skill-dist-doctor.yml` = Distributions-
  Determinismus). Im Zweifel gilt `/workflow-review` — die Ausnahme ist eng und muss begründet werden,
  nicht stillschweigend angenommen.
- **Parallele Sessions — Haupt-Tree heilig (ADR-233)**: der geteilte Checkout `~/github/platform`
  bleibt auf `main`; **kein** Branch-Switch im Haupt-Tree. Editierende Arbeit läuft in einem eigenen
  Worktree via `tools/repo-session.sh start <repo> --task <slug>` (Branch `session/<date>/<owner>/<slug>`
  von `origin/main` + Lease). Aufräumen: `tools/worktree-reaper.py` (dry-run default, squash-aware,
  Dirty-Guard). Read-only-Analyse darf im Haupt-Tree bleiben.

### Parallel-Session-Hygiene (ADR-233) — Werkzeuge

| Werkzeug | Zweck |
|---|---|
| `tools/repo-session.sh` | verbindlicher Entry Point: `start`/`list`/`end` — Worktree von `origin/main`, Branch-Schema, Lease |
| `tools/worktree-reaper.py` | GC gemergter/stale Worktrees (dry-run default; `--apply`; entfernt nie einen Branch) |
| `tools/main-tree-guard.sh` | `install` = Snap-back-Hook (aktiv erst nach Skill-Migration); `report` = `unauthorized_head_flips/30d` (Kill-Gate-Metrik) |

> **Rollout-Hinweis:** Der harte `main-tree-guard` (Snap-back) wird **erst aktiviert**, wenn die
> Session-Skills den geteilten Tree nicht mehr per `git switch` umschalten — sonst bricht er
> bestehende Abläufe. Bis dahin: Konvention als Lesestoff + `repo-session` als empfohlener Einstieg;
> `main-tree-guard.sh report` misst Verstöße. Kill-Gate-Termin: 2026-09-01.

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
- **Orchestrator MCP**: `https://orchestrator.iil.pet/sse` (aktiv) — Ziel-Endpoint
  ist `/mcp` (ADR-256, accepted); Übergang läuft, `/sse` noch nicht abgeschaltet.
- **Dev-Hub Cockpit**: `https://devhub.iil.pet`
