# tools/ — Index

Kurzindex der 33 `tools/*.py`-Skripte (DEVX-2, Issue #1202). Jedes Skript
unterstützt `--help`/`-h` (zeigt sein eigenes Docstring-Usage, kein echter
Check-Lauf — DEVX-1). Details stehen im Docstring des jeweiligen Skripts,
hier nur der 1-Zeiler zur Orientierung "was tut das, wann brauche ich es".

| Skript | Zweck |
|---|---|
| `adr_citation_lint.py` | Deterministischer Lint für ADR-Querverweise (Body-Zitate) |
| `adr_index_check.py` | Konsistenz-Check `INDEX.md` ↔ ADR-Dateibestand |
| `backup_meter.py` | ADR-241 §4 — maschinelle Confirmation der Backup-Baseline |
| `branch_protection_meter.py` | ADR-242 — Enforcement-Meter für Branch-Protection-Rollout |
| `check_deploy_adr_supersession.py` | Gate gegen Deploy-ADR-Sprawl (KONZ-platform-011/ADR-264) |
| `check_design_tokens.py` | Pre-commit Hook: Design-Token-Compliance (ADR-049) |
| `check_htmx_patterns.py` | Pre-commit Hook: HTMX-Anti-Pattern-Erkennung (ADR-048, AP-001..004) |
| `check_publish_gate.py` | Org-Gate gegen ungegatete PyPI-Publish-Workflows (ADR-226) |
| `check_registry_view_readers.py` | Guard gegen neue Direct-Reads der generierten Registry-Views (ADR-234 §11.1) |
| `check_workflow_index.py` | Vollständigkeits-Gate für den `.windsurf/workflows/`-Index |
| `deploy_config_lint.py` | Org-Gate gegen Auto-Prod-Deploy-Drift (push→main darf nicht auf `production` defaulten) |
| `deploy_failure_monitor.py` | Gate gegen wiederholte Deploy-Failures ohne Fix (session-retro 2026-06-22) |
| `exit-plan.py` | Exit-/Portability-Runbook aus Live-GitHub-Zustand ableiten (KONZ-platform-002) |
| `iil_migration_check.py` | Idempotenter Reality-Checker für die iil-*-Org-Migration (ADR-255) |
| `measure-evidence-discipline.py` | Signal-R-Messung für die evidence-discipline-Policy (#256) |
| `optimize_debt_radar.py` | KONZ-platform-019 — read-only wöchentlicher Fleet-Optimierungs-Radar |
| `publish_gate_meter.py` | Fleet-weiter Backlog-Meter ungegateter PyPI-Uploads (ADR-226 Phase 2a) |
| `pypi_fleet_inventory.py` | PyPI-Fleet-Inventar — deterministischer Ground-Truth-Scanner (ADR-266 Stufe 1) |
| `reconcile_registry_live.py` | Abgleich Registry ↔ Live-Prod-Zustand (KONZ-platform-015) |
| `ref-sweep.py` | Hardcodierte GitHub-Actions-`uses:`-Refs über Consumer-Repos ummünzen |
| `registry_api.py` | Importierbarer Accessor für die kanonische Registry — **sanktionierter** Lesepfad (ADR-234 P0) |
| `registry-canonical.py` | Union-Canonical-Registry + View-Generatoren (ADR-234 P0) |
| `registry-consistency-check.py` | Macht die Registry-Doppelquelle sichtbar/vergleichbar (ADR-234 P0) |
| `registry_coverage_drift.py` | KONZ-001 R5 „Liar-Liste" v2 — GitHub-Realität vs. `canonical.yaml` (#488) |
| `repo_checker.py` | ADR-022 Repository-Consistency-Checker (inkl. Testing-Compliance, ADR-058) |
| `repo_health_check.py` | Vollständigkeits-Check für Repos/Packages — Quality-Gate vor Publish/Deploy |
| `repo_readiness.py` | Readiness-Gate für ein Repo (`/repo-ready`) |
| `retro_kpis.py` | Längsschnitt-KPIs für `/session-retro` |
| `sync_drift_meter.py` | ADR-265 REC-3 — read-only Sync-Drift-Melder |
| `test_claim_check.py` | Warn-only CI-Gate gegen unbelegte Test-Claims (session-retro Gate 1) |
| `usage_sweep.py` | Quartalsweiser Nutzungs-Sweep — Entbürokratisierungs-Baustein (#1076) |
| `worktree-reaper.py` | Deterministischer GC für git-Worktrees (ADR-233) |

`__init__.py` macht `tools/` zum importierbaren Package (kein CLI-Skript,
daher nicht oben gelistet).

## Registry-Tooling (ARCH-5, Issue #1202)

Registry-Skripte sind auf `tools/` **und** `registry/` verstreut (2
Verzeichnisse), nur `registry-canonical.py` hat Makefile-Targets
(`registry-flip`, `registry-verify`). Statt neue Targets für jedes Skript
zu ergänzen (mehr Makefile-Oberfläche, mehr CI-Risiko für wenig Nutzen bei
Skripten, die primär ad-hoc/lokal laufen), hier die vollständige Übersicht
als Index — kleinere, schnellere Lösung für dasselbe Auffindbarkeits-Problem:

| Skript | Verzeichnis | Make-Target | Zweck |
|---|---|---|---|
| `registry-canonical.py` | `tools/` | `make registry-flip` / `make registry-verify` | canonical.yaml → Views generieren + Round-Trip prüfen |
| `registry_api.py` | `tools/` | – (Library, kein CLI) | Sanktionierter Lesepfad für andere Skripte |
| `check_registry_view_readers.py` | `tools/` | über `make check-push` | Guard gegen neue Direct-Reads der generierten Views |
| `registry_coverage_drift.py` | `tools/` | – (ad-hoc) | GitHub-Realität vs. canonical.yaml — „Liar-Liste" |
| `reconcile_registry_live.py` | `tools/` | – (ad-hoc) | Registry vs. Live-Prod-Host-Zustand |
| `registry-consistency-check.py` | `tools/` | – (ad-hoc) | Zeigt die Registry-Doppelquelle (scripts/repo-registry.yaml vs. registry/repos.yaml) |
| `sync_registry.py` | `registry/` | – (ad-hoc) | `repos.yaml` → Consumer synchronisieren + `--check`-Modus |

Alle "ad-hoc"-Skripte sind `python3 <pfad> [--help]` direkt lauffähig — kein
zusätzlicher Makefile-Wrapper nötig, da sie unregelmäßig/manuell (nicht
routinemäßig in CI) genutzt werden.
