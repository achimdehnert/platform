---
title: "ADR-174 — Workflow Enforcement: CI Gate + PR Checklist + Symlink Policy"
date: 2026-04-29
status: Accepted
deciders: achimdehnert
implementation_status: partial
implementation_evidence:
  - "risk-hub/.github/workflows/ci.yml — qm-gate Job implementiert (pilot)"
  - "platform/.github/workflows/_ci-python.yml — enable_qm_gate Input (alle Repos)"
  - "risk-hub/.github/PULL_REQUEST_TEMPLATE/agent-pr.md — Self-Review Gate"
  - "platform/.windsurf/workflows/workflow-index.md — Symlink-Policy + Rule #13"
  - "platform/.windsurf/workflows/onboard-repo.md — Step 6.9 Branch Protection"
  - "Rollout auf weitere ~18 Repos: ausstehend"
implementation_done_when:
  - "qm-gate als required status check in Branch Protection aller aktiven Repos aktiviert"
  - "enable_qm_gate: true in CI-Caller aller Repos die _ci-python.yml nutzen"
  - "onboard-repo.md Step 6.9 bei ≥3 neuen Repos durchlaufen"
---

# ADR-174 — Workflow Enforcement: CI Gate + PR Checklist + Symlink Policy

## Context and Problem Statement

Agentic Coding Workflows (v4, ADR-066) sind **advisory** — ein Agent kann `/pre-code`,
Phase 0 PCV und Step 5 Self-Review überspringen ohne mechanische Konsequenz.
`ASSUMPTION[unverified]`-Marker können unbemerkt in Production-Code landen.
Zusätzlich fehlte eine verbindliche Regel welche Workflow-Dateien repo-spezifisch (lokal)
vs. platform-global (Symlink) sein dürfen, was zu unkontrolliertem Drift führt.

**Problem:** Advisory-only QM ist nur so gut wie die Disziplin des Agents — kein Enforcement.

## Decision Drivers

- QM greift auch ohne menschliche PR-Review jedes Commits
- Minimaler Maintenance-Overhead (kein neues Tool/Service)
- Model-agnostisch (funktioniert mit jedem LLM-Modell)
- Enforcement im CI/PR-Layer, NICHT in Production-Code
- Draft-PRs dürfen nicht blockiert werden (WIP-Entwicklung ungestört)

## Considered Options

1. **Nur Dokumentation** — Checklisten in CONTRIBUTING.md
2. **Pre-commit Hooks lokal** — clientseitige Prüfung
3. **CI Gate + PR Template + Symlink Policy** — zentrales serverseitiges Enforcement
4. **Branch Protection Rules (GitHub Settings)** — Merge blockieren bis required status checks grün

## Decision Outcome

**Gewählt: Option 3 — CI Gate + PR Template + Symlink Policy**

Option 3 + 4 kombiniert — CI Gate (Option 3) erzeugt den Status-Check, Branch Protection (Option 4)
erzwingt dessen Erfolg vor dem Merge. Ohne Option 4 kann ein Admin Option 3 mit `--admin` bypass.
Option 1 bleibt advisory. Option 2 greift nur lokal — kein Schutz bei Remote-Agents.

**Scope: Plattformweit (alle Repos)** — gilt nicht nur für risk-hub.

### Maßnahme 1 — CI Gate: `ASSUMPTION[unverified]` blockiert Merge (alle Repos)

Reusable Workflow in `platform/.github/workflows/_ci-python.yml` (Input: `enable_qm_gate`).
Direkte Integration in Repo-spezifische `ci.yml` als `qm-gate` Job.
**Rollout:** via `/onboard-repo` Step 6.9 bei jedem Repo-Onboarding.

```yaml
- name: Block unverified assumptions
  run: |
    set -euo pipefail
    COUNT=$(grep -rnF "ASSUMPTION[unverified]" --include="*.py" . 2>/dev/null | wc -l)
    if [ "$COUNT" -gt 0 ]; then
      echo "::error title=QM Gate::$COUNT offene ASSUMPTION[unverified] — vor Merge auflösen"
      exit 1
    fi
```

**Known Limitations (by design):**
- Scan-Scope: nur `*.py` — `ASSUMPTION[unverified]` in `.html`/`.sh`/`.yaml` wird nicht erfasst.
  Begründung: ASSUMPTION-Marker sind eine Python-Code-Konvention (Phase 0 PCV).
- `workflow_dispatch`-Events: Gate wird geskippt (`github.event.pull_request.draft == false`
  evaluiert auf Non-PR-Events zu `null == false` → `false`). By design — Gate gilt nur für PRs.
- Test-Dateien (`test_*.py`) sind NICHT exempt — Assumptions in Tests müssen ebenfalls aufgelöst sein.

### Maßnahme 2 — PR Template: Self-Review Gate als strukturierte Checkliste

`agent-pr.md` enthält pflichtigen Self-Review-Block (Spiegelung von `/agentic-coding` Step 5):
- Tests grün, Ruff clean, Acceptance Criteria, ADR-Violations = 0
- `ASSUMPTION[unverified]` aufgelöst (← CI prüft automatisch)
- CHANGELOG aktualisiert, ADR-Impact-Feld (aus Step 3.5 B)
- `python -m pytest` statt `pytest` (konsistent mit Workflow-Standard)

### Maßnahme 3 — Symlink Policy

**Regel:** Symlink DEFAULT. Lokal NUR bei repo-spezifischem Inhalt.

| Typ | Strategie | Beispiele |
|-----|-----------|-----------|
| Platform-global | Symlink — Änderung in `platform/` wirkt sofort plattformweit | `agentic-coding.md`, `governance-check.md`, `pre-code.md` |
| Repo-spezifisch | Lokal — repo-eigene Befehle/Pfade/ADR-Referenzen | `complete.md`, `agent-task.md`, `run-tests.md` |

Dokumentiert in `workflow-index.md` + `AGENT_HANDOVER.md` pro Repo.

### Maßnahme 4 — Branch Protection: `qm-gate` als Required Status Check (alle Repos)

Für jedes Repo: GitHub → Settings → Branches → `main` → Branch Protection Rule:
- **Required status checks:** `QM Gate — ASSUMPTION Check (ADR-174)`
- **Require branches to be up to date before merging:** ✅

Ohne diese Einstellung kann ein Admin den CI Gate mit `--admin` bypassen.
Diese Maßnahme ist Teil von `/onboard-repo` Step 6.9 (PFLICHT für alle Repos).

### Confirmation

- CI Gate aktiv in risk-hub (PR auf `main` triggert `qm-gate` Job)
- Draft-PRs werden korrekt geskippt
- `grep -rnF` (fixed string) verhindert Regex-Fehlinterpretation
- PR Template enthält vollständigen Self-Review-Block
- Symlink-Policy in `workflow-index.md` als Non-Negotiable Rule #13 dokumentiert
- Branch Protection via `/onboard-repo` Step 6.9 für alle Repos ausrollbar

## Pros and Cons of the Options

### Option 1 — Nur Dokumentation

- ✅ Kein Infrastruktur-Aufwand
- ❌ Kein technisches Enforcement — bleibt advisory
- ❌ Skaliert nicht mit steigender Agent-Autonomie

### Option 2 — Pre-commit Hooks lokal

- ✅ Schnelles Feedback für Entwickler
- ❌ Bypassbar (--no-verify Flag)
- ❌ Kein Schutz bei Remote-Agent-Ausführung ohne lokales Setup

### Option 3 — CI Gate + PR Template + Symlink Policy

- ✅ GitHub-native Annotations zeigen Fehler direkt im PR-Diff
- ✅ Reusable Workflow: 1× pflegen, alle Repos erben via `enable_qm_gate: true`
- ✅ Model-agnostisch — funktioniert unabhängig vom LLM
- ⚠️ Allein nicht ausreichend — Admin kann mit `--admin` bypassen (→ Option 4 nötig)
- ⚠️ Rollout auf ~18 weitere Repos erfordert pro-Repo CI-Update

### Option 4 — Branch Protection Rules (ergänzend, kombiniert mit Option 3)

- ✅ Verhindert Admin-Bypass ohne explizite Rule-Deaktivierung
- ✅ GitHub-native — kein zusätzlicher Code
- ✅ Plattformweit einheitlich via `/onboard-repo` Step 6.9
- ⚠️ Nur GitHub-seitige Einstellung — kann von Repo-Admin geändert werden
- ⚠️ Erfordert initialen Setup-Aufwand pro Repo

## Open Questions

1. **Test-Datei-Exemption:** Sollen `ASSUMPTION[unverified]` in `test_*.py` exempt sein?
   → Aktuell: NEIN (Test-Assumptions müssen ebenfalls aufgelöst sein). Kann per ADR-Amendment geändert werden.

2. **Rollout-Plan weitere Repos:** Die ~18 anderen Repos nutzen noch kein `qm-gate`.
   → Deferred: Rollout via `/onboard-repo` Workflow bei nächsten Repo-Onboardings.
   → Issue erstellen für bulk-Rollout wenn Feedback aus risk-hub positiv.

3. **Scan-Scope Erweiterung:** Sollen ASSUMPTION-Marker auch in Templates geprüft werden?
   → Deferred: Erst Praxiserfahrung mit `*.py`-Scan sammeln, dann entscheiden.

4. **Track 3 — Workflow-Metriken:** `log_action`-Audit-Daten auswerten für QM-Report.
   → Deferred: Separate ADR oder Amendment wenn Datenbasis ausreicht.

## Implementation

- `platform/.github/workflows/_ci-python.yml` — `enable_qm_gate` Input + `qm-gate` Job
- `risk-hub/.github/workflows/ci.yml` — `qm-gate` Job direkt integriert (pilot)
- `risk-hub/.github/PULL_REQUEST_TEMPLATE/agent-pr.md` — Self-Review Gate Block
- `platform/.windsurf/workflows/workflow-index.md` — Symlink-Policy Abschnitt
- Weitere Repos: via `enable_qm_gate: true` in deren CI-Caller

## More Information

- ADR-066: AI Engineering Squad — Rollen, Gates, Workflows
- ADR-067: Work Management — Issues, AI-Agent-Protokoll
- ADR-081: Scope Management — affected_paths
- ADR-108: Agent QA Cycle — Self-Review, AuditStore
- agentic-coding.md v4: Phase 0 PCV, Step 5 Self-Review (ASSUMPTION-Konvention)
