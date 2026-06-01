---
description: Readiness-Gate für ein Repo — aktuelle Version aktiv (git+install konsistent) + laufzeit-bereit, sichere Fehler auto-fixen
mode: write
---

# /repo-ready — Readiness-Gate vor dem Testen

> **Wann:** Bevor du ein Repo (lokal oder dessen Render/Deploy) testest und sicher
> sein willst, dass **die aktuelle Version aktiv ist** und **keine behebbaren
> Fehler** mehr im Weg stehen. Genau für den Fall „die Live-/Test-Sicht zeigt eine
> alte Version" (stale editable-Install, Branch hinter `main`).
> **Wann NICHT:**
> - Reiner Test-Lauf (Lint/pytest/Django) → `/teste-repo` (delegiere ich ohnehin).
> - Vollständigkeit vor Publish/Deploy → `/repo-health-check`.
> - 3-Node-Sync WSL↔GitHub↔Server → `/sync-repo`. Config-Drift → `/drift-check`.
> - Django-Views-Smoke → `/frontend-ui-test` / `/pre-release-test`.
>
> `/repo-ready` **dupliziert keine** dieser Skills — es prüft die *eine* fehlende
> Schicht (Versions-/Env-Konsistenz + Runtime-Bereitschaft) und **ruft** die
> obigen für ihren Teil auf.

## Verwendung

```
/repo-ready <repo>              # prüft UND fixt sichere Dinge (default)
/repo-ready <repo> --report-only # nur Diagnose, keine Mutation
/repo-ready <repo> --json        # maschinenlesbar
```

`<repo>` = Name relativ zu `$GITHUB_DIR` oder absoluter Pfad.

## Step 0: Repo-Kontext aus project-facts.md (NICHT hardcoden)

Der Repo-**Typ** steuert die Runtime-Smoke. Quelle (in dieser Reihenfolge):
1. `<repo>/.windsurf/rules/project-facts.md` → Feld `**Type**:`
   (`python-package` | `django` | `mcp` | `renderer`/`klickdummy` | …).
2. Ist `Type: unknown` oder fehlt → Heuristik (manage.py→django, `*_mcp/server.py`→mcp,
   `**/klickdummy/*/screens-spec.yaml`→renderer, sonst pyproject→python-package).

> Steht `unknown` im project-facts, ist das selbst ein Befund — Typ dort setzen.

## Step 1: Gate ausführen

// turbo
```bash
set -euo pipefail
PLATFORM_DIR="${GITHUB_DIR:-$HOME/github}/platform"
python3 "$PLATFORM_DIR/tools/repo_readiness.py" "<REPO_ARG>"
```

> Cascade: `<REPO_ARG>` aus Step 0 einsetzen. Für reine Diagnose `--report-only`
> anhängen.

Das Script prüft drei Schichten und **fixt sichere/idempotente Dinge selbst**:

| Schicht | Prüft | Auto-Fix (default) |
|---|---|---|
| **freshness** | git `HEAD==origin/main`, Working-Tree clean, **installed==source** (editable-Target == Repo) | `git pull --ff-only` (nur clean), `pip install -e .` (Repoint bei stale/fehlend) |
| **quality** | `scripts/teste_repo.py` (Lint/pytest/Hardcoding) | `ruff check --fix` vorab |
| **runtime** | typ-bewusst: Import+Entrypoint (lib) · Renderer-Marker (renderer) · `/healthz` (mcp, via `ORCHESTRATOR_HEALTH_URL`) · delegiert (django) | — |

## Step 2 (nur renderer/klickdummy): Voll-Smoke via Playwright

Die Engine prüft Renderer nur statisch (Marker im Quelltext). Für die *echte*
Laufzeit-Probe einen gerenderten Screen headless fahren:

1. Repo-`.venv` nutzen (aktueller Source, **nicht** stale Install) und eine Seite
   rendern (z. B. `python -m iil_klickdummy.lineage --genesor --out /tmp/rr`).
2. Lokal serven (`python -m http.server`), mit dem **Playwright-MCP** öffnen:
   - `browser_console_messages(onlyErrors=true)` → **keine** JS-Exceptions (favicon-404 ist Test-Server-Artefakt, kein Befund).
   - Schlüssel-Marker prüfen (z. B. Toggle `#spec-toggle`, `.trace-strip`, Widget).
3. Screenshot als Beleg.

## Output-Format

```
== /repo-ready · <repo> (type=<typ>) · fix=on|off ==
  ✅/🔧/⚠️/❌/· [<layer>/<check>] <detail>  → <action>
  ...
→ BEREIT ✅ | mit Warnungen ⚠️ | FAIL ❌  (N fail, M warn)
```
Exit 0 = keine `fail` (bereit); 1 = mindestens ein `fail`; 2 = Repo nicht gefunden.

## Anti-Patterns (darf NICHT)

- ❌ **Dirty Working-Tree auto-„fixen"** (reset/clean/checkout/stash) — Datenverlust.
  Dirty → nur **melden**, nie mutieren.
- ❌ `git push`, `git reset --hard`, force-Operationen, fremde Working-Trees anfassen.
- ❌ Lint/pytest/Django-Checks **neu implementieren** — immer `teste_repo.py` delegieren.
- ❌ Repo-Pfade/Orgs/IPs/MCP-Prefixe hardcoden — `$GITHUB_DIR` + project-facts.md.
- ❌ `--break-system-packages` außerhalb des `pip install -e .`-Repoints einsetzen.
- ❌ favicon-404 oder fehlende `ORCHESTRATOR_HEALTH_URL` als „Fehler" werten (Artefakte/skip).
- ❌ Behaupten „bereit", wenn `teste_repo` rot ist — Exit-Code ist bindend.

## Changelog

- 2026-06-01: Initial. Geboren aus dem Stale-Install-Vorfall (genesor-Live-Render
  lief auf v1.4.0 statt main-v1.9.0, weil das systemweite editable auf `/tmp/iilk-v1.4`
  zeigte). Engine `tools/repo_readiness.py`. Komponiert `teste_repo.py`/`repo_health_check.py`
  statt zu duplizieren. Dogfood gegen iil-klickdummy (Report im PR-Body). Kein neuer
  ADR (Skill nach bestehendem Muster, `adr-threshold.md`); Verteilung via cc-skill-dist
  (ADR-230).
