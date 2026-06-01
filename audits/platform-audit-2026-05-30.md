# Platform Audit — 2026-05-30

> Tiefer/solider Audit, Belege pro Befund. Scope dieses Laufs: **Phase 1 (Git-Hygiene)** +
> **Phase 2 (Code-/Architektur-Konsistenz)** über 35 lokal ausgecheckte Repos.
> **Nicht** in diesem Lauf: Phase 3 (Live-Prod-Infra/SSL/Container — deployment-MCP nicht gebunden)
> und vollständige CI-Run-Health pro Repo. Diese als „noch tiefer"-Erweiterung unten.

## Executive Summary

| Kennzahl | Wert |
|---|---|
| Repos gescannt | 35 (4 ohne lokalen Checkout: `risk-hub-tmp`, `openclaw`, `awesome-openclaw-skills`, `awesome-openclaw-usecases`) |
| Befunde | 2× HIGH, 3× MEDIUM, 2× LOW |
| Dominantes Muster | **~1.000 Phantom-Dirty-Files** (`.windsurf`-Typechange) über ~20 Repos |
| Direkte Architektur-Verstöße (belegt) | LLM-SDK-Imports an aifw vorbei in 3 App-Repos |

Gesamteindruck: **gesund im Kern** (keine UUIDField-PK-Verstöße, Secrets nicht im Klartext gefunden,
einheitliche Workflow-/ADR-Struktur), aber **zwei systematische Hygiene-Lecks** mit hohem
Reibungs-/Risiko-Wert, die platformweit *einmal* gelöst gehören.

---

## Findings

### F1 [HIGH] — ~1.000 Phantom-Dirty-Files: `.windsurf/workflows/*` als getrackte Datei vs. On-Disk-Symlink

**Beleg:** In jedem Hub sind exakt die ~50 `.windsurf/workflows/*.md` mit Git-Status **`T` (typechange)**.
```
illustration-hub: git-mode=100644 (Datei)  ondisk=Symlink->../../../platform/.windsurf/workflows/adr.md
learn-hub:        git-mode=100644           ondisk=Symlink->...
travel-beat:      git-mode=100644           ondisk=Symlink->...
```
`.gitignore` enthält `.windsurf/` (z. B. `illustration-hub/.gitignore:16`), **aber die Dateien sind
bereits getrackt** → `.gitignore` greift nicht (ignoriert nur Untracked). Ein Sync-Mechanismus
(`platform-workflows/.windsurf/workflows/sync-repo.md`) materialisiert die Workflows als Symlinks in
`platform/`, während Git die alten regulären Dateien hält.

**Impact:**
- ~50 Phantom-Änderungen × ~20 Repos = **~1.000 dauerhaft „dirty" angezeigte Dateien**.
- **Bricht Git-Ops** (rebase/stash/checkout scheitern an „uncommitted changes") — die Reibung, die
  diese Session wiederholt traf (Worktrees, Batch-Rollout).
- **Maskiert echte Änderungen** und riskiert, dass Typechanges versehentlich in Feature-PRs landen.

**Fix (platformweit, einmal):** pro Repo `git rm -r --cached .windsurf/` + Commit „stop tracking
synced .windsurf (now symlinked + gitignored)". Danach greift das bestehende `.gitignore`, der
Dirty-Zustand verschwindet, Git-Ops sind wieder sauber. Kandidat für ein kleines Sweep-Skript.

---

### F2 [HIGH] — LLM-SDK-Imports an aifw-Routing vorbei (App-Code)

Verstoß gegen `llm-routing.md` (Provider-Aufrufe laufen über aifw, nicht direkt). **Belege (file:line):**
```
bfagent/apps/media_hub/services/tts_service.py:132        from openai import OpenAI
bfagent/apps/bfagent/handlers/illustration_handler.py:105 from openai import AsyncOpenAI
bfagent/apps/expert_hub/agents/config.py:32               from openai import AsyncOpenAI
cad-hub/apps/dxf/handlers/pdf_vision.py:319               import openai
cad-hub/apps/dxf/handlers/pdf_vision.py:360               import anthropic
recruiting-hub/apps/candidates/llm_service.py:30          from groq import Groq
```
**Abgegrenzt (kein Verstoß):** `risk-hub/packages/bfagent-llm/.../adapters.py` (Adapter-Layer = by design)
und `mcp-hub/orchestrator_mcp|query_agent_mcp/*` (LLM-Infra-Layer; ein „Treffer" ist sogar der Kommentar
„NEVER import openai…").

**Fix:** Aufrufe in den 3 App-Repos auf aifw umstellen; mittelfristig per Lint erzwingen
(`grep`-Gate in CI gegen `import openai|anthropic|groq` außerhalb definierter Adapter-Pfade).

---

### F3 [MEDIUM] — Branch-/Checkout-Hygiene: stark veraltete lokale Stände + Cross-Repo-Migration in-flight

- **Sehr stale lokale Checkouts:** `137-hub` **169** Commits hinter `origin/main`, `authoringfw` **125** hinter.
- **~15 Repos nicht auf `main`**, davon **6 auf demselben Branch `feat/adr-212-traefik-migration`**
  (billing-hub, cad-hub, coach-hub, pptx-hub, trading-hub, writing-hub) = in-flight **Traefik-Migration (ADR-212)**.
- Weitere Feature-Branches: bfagent `ci/ruff-format`, risk-hub `fix/celery-build-regression`,
  weltenhub `ci/platform-context-pypi`, aifw `feat/anthropic-prompt-caching`, ausschreibungs-hub `feat/document-intelligence-mvp`.

**Impact:** Tools, die lokalen Working-Tree lesen, ziehen stale/falsche Stände (diese Session via
`--ref origin/main` im agent-handover-Generator entschärft). ADR-212 sollte koordiniert
zusammengeführt werden, bevor 6 parallele Branches divergieren.

---

### F4 [MEDIUM] — CI-Defekte auf aktiven Hubs (blockieren sogar Doku-PRs)

- **bfagent:** main-CI war rot — **pgvector-Extension fehlte** (58 Errors, `_ci-python.yml` ohne
  `postgres_image: pgvector/pgvector:pg16`) → in dieser Session via PR #39 gefixt. Dahinter ein
  **pytest-xdist `INTERNALERROR`** im Teardown von `apps/genagent/core/tests/test_executor.py` →
  Issue **bfagent#40** (offen).
- **cad-hub:** `Security Scan (pip-audit)` rot (pre-existing).

**Impact:** Triviale additive Doku-PRs (AGENT_HANDOVER-Anker) mussten per `--admin` gemergt werden.
Muster: „aktive" Hubs mit dauerhaft roter CI.

---

### F5 [MEDIUM] — `os.environ` statt `decouple` (First-Party-Hotspots)

Ohne vendor/.venv/migrations/test/config gezählt (Dateien mit `os.environ`):
```
bfagent 173 · mcp-hub 53 · trading-hub 15 · risk-hub 9 · weltenhub 8 · travel-beat 7 · pptx-hub 6 · odoo-hub 6 · dev-hub 6
```
bfagent/mcp-hub sind große Monorepos (Zahl entsprechend); dennoch Kandidaten für schrittweise
`config(...)`-Migration (12-Factor/Settings-Konsistenz).

---

### F6 [LOW] — Audit-Blindstellen: 4 gelistete Repos ohne lokalen Checkout

`risk-hub-tmp` (Name deutet auf Cruft → prüfen/löschen?), `openclaw`, `awesome-openclaw-skills`,
`awesome-openclaw-usecases`. Nicht auditierbar ohne Checkout.

### F7 [LOW] — `print()` statt Logging (First-Party)

Hotspots: pptx-hub 92, dev-hub 81, weltenhub 73, odoo-hub 47, travel-beat 45, risk-hub/writing-hub 40.
(bfagent/mcp-hub-Rohzahlen vendor-inflationiert — hier ausgeklammert.) Logging-Hygiene-Backlog.

---

## Cross-Repo-Muster → platformweite Lösungen

1. **F1 ist *ein* Fix für ~20 Repos** — `.windsurf`-Untracking-Sweep. Höchster Aufräum-Hebel.
2. **F2 LLM-Routing-Drift** in 3 App-Repos → CI-Lint-Gate statt Einzel-Reviews.
3. **F3 ADR-212-Traefik** über 6 Repos → koordinierter Merge-Plan, sonst Divergenz.
4. **F4 CI-Health** ist kein Einzelfall → systematischer „grüne-main"-Check pro Repo lohnt (eigener Lauf).

## Positiv (keine Befunde)

- Keine `UUIDField(primary_key=True)`-Verstöße.
- Keine Klartext-Secrets in First-Party-`.py` gefunden (Stichprobe).
- Einheitliche `.windsurf/`-Workflow- und ADR-Struktur über alle Repos.

## „Noch tiefer" — Folgelauf (empfohlen als Multi-Agent-Workflow)

- **Phase 3 Live-Infra:** Container-Status, Health-Endpoints, SSL-Ablauf, Disk/Memory auf Prod
  (braucht deployment-MCP).
- **CI-Run-Health pro Repo:** letzter `main`-Run je Repo grün? (deckt weitere F4-Fälle auf).
- **Per-Repo-Deep-Dive:** je ein Agent pro Repo (Secrets-Scan tief, Test-Coverage, Dependency-Audit,
  Dockerfile/Compose gegen ADR-021) — parallelisierbar, adversarisch verifiziert.

---
_Scan-Rohdaten: `/tmp/audit_git.txt`, `/tmp/audit_viol.txt` (dieser Lauf). Generiert 2026-05-30._

---

## Nachtrag: Validierung & Verdikte (2026-05-30, nach Bearbeitung)

> Die Roh-Befunde oben stammen aus Grep-Scans. Nach **per-Stelle-Validierung** (wie im Report
> gefordert) verschoben sich die Schweregrade deutlich — dokumentiert hier zur Ehrlichkeit.

| Finding | Roh | Validiertes Verdikt | Aktion |
|---|---|---|---|
| **F1** .windsurf Phantom-Dirty | HIGH | **bestätigt** — der eine große, reale, systematische Treffer | ✅ **gelöst**: ~32 Repos untracked; **ADR-229** (proposed, #340) |
| **F2** LLM-Routing-Drift | HIGH | **1 echt** (cad-hub `pdf_vision`: aifw-Bypass + stale Modelle); recruiting-hub = groq direkt aber **policy-bevorzugter Tier → akzeptiert**; bfagent **eingefroren** | Issue **cad-hub#13** |
| **F3** ADR-212-Traefik | MEDIUM | reale, halb-fertige Cross-Repo-Migration (Platform-Seite fertig) | ✅ **4 PRs gemergt** (billing/coach/pptx/trading-hub) |
| **F4** CI-Defekte | MEDIUM | bfagent pgvector **✅ #39**; bfagent xdist **#40** (eingefroren, low); cad-hub Security-Scan = **Self-hosted-Runner-Env-Pollution** (kein Dep-Problem; `_ci-python.yml` ohne venv-Isolation), **non-blocking** | CI-Infra-Track (venv-Isolation) |
| **F5** os.environ→decouple | MEDIUM | **überwiegend False-Positive** — Roh-Count zählte Django-Bootstrap (zwingend), `.github/scripts` (`hardcoded-ok`), Harness-Skripte, `.claude`-Worktree-Dupes, legitime Microservice-Env-Config. **1 echter Fall:** trading-hub `services/data_collector.py` (Broker-Keys) | 1-Datei-Fix trading-hub |

### Meta-Lehre
Roh-Grep-Findings (F5, teils F2/F4) **überzeichnen die Schwere**; Validierung schrumpft sie. Für künftige
Audits: Schweregrad **erst nach per-Stelle-Beleg** vergeben, nicht aus Zählungen. **F1 war der einzige
große systematische Gewinn** — der Rest kleiner/legitim/owner-getrieben als der Rohscan suggerierte.

### Falsch-Zuordnungen unterwegs (Cheap-Checks fingen sie ab)
- cad-hub Security-Scan: cad-hub-reqs → iil-testkit → **eigentlich Runner-Env-Pollution** (zwei Wrong-Layer-Fixes vermieden, PR cad-hub#14 ehrlich geschlossen).
- Repo-Slugs: `iil-relaunch` → **iilgmbh/iil-relaunch** (Org-Transfer, 307); Ordner `testkit` → Repo `iil-testkit`.
