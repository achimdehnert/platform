# ADR-174 — Workflow Enforcement: CI Gate + PR Checklist + Symlink Policy

## Status

Accepted — 2026-04-29

## Context

Agentic Coding Workflows (v4, ADR-066) sind **advisory** — ein Agent kann `/pre-code`,
Phase 0 PCV und Step 5 Self-Review überspringen ohne mechanische Konsequenz.
`ASSUMPTION[unverified]`-Marker können in Production-Code landen.
Zusätzlich fehlte eine verbindliche Regel welche Workflow-Dateien repo-spezifisch (lokal)
vs. platform-global (Symlink) sein dürfen, was zu unkontrolliertem Drift führt.

**Problem:** Advisory-only QM ist nur so gut wie die Disziplin des Agents — kein Enforcement.

## Decision Drivers

- QM greift auch ohne menschliche PR-Review jedes Commits
- Minimaler Maintenance-Overhead (kein neues Tool/Service)
- Model-agnostisch (funktioniert mit jedem LLM)
- Enforcement im CI/PR-Layer, NICHT in Production-Code

## Considered Options

1. Nur Dokumentation (Checklisten in CONTRIBUTING.md) — kein technisches Enforcement, verworfen
2. Pre-commit Hooks lokal — nur auf Entwickler-Maschine, kein zentrales Gate, verworfen
3. **CI Gate + PR Template + Symlink Policy** — gewählt

## Decision

### Maßnahme 1 — CI Gate: `ASSUMPTION[unverified]` blockiert Merge

Reusable Workflow in `platform/.github/workflows/_ci-python.yml` (Input: `enable_qm_gate`).
Direkte Integration in Repo-spezifische `ci.yml` als `qm-gate` Job.

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

- Skipped bei Draft-PRs (`if: github.event.pull_request.draft == false`)
- GitHub-native `::error` Annotations für direkte PR-Anzeige
- `-F` (fixed string) für Grep-Zuverlässigkeit

### Maßnahme 2 — PR Template: Self-Review Gate als strukturierte Checkliste

`agent-pr.md` enthält pflichtigen Self-Review-Block (Spiegelung Step 5):
- Tests grün, Ruff clean, Acceptance Criteria, ADR-Violations = 0
- `ASSUMPTION[unverified]` aufgelöst (← CI prüft automatisch)
- CHANGELOG aktualisiert
- ADR-Impact-Feld (aus Step 3.5 B)
- `python -m pytest` statt `pytest` (konsistent mit Workflow-Standard)

### Maßnahme 3 — Symlink Policy

**Regel:** Symlink DEFAULT. Lokal NUR bei repo-spezifischem Inhalt.

| Typ | Strategie |
|-----|-----------|
| Platform-global | Symlink — Änderung in `platform/` wirkt sofort überall |
| Repo-spezifisch | Lokal — repo-eigene Befehle/Pfade/ADR-Referenzen |

Dokumentiert in `workflow-index.md` + `AGENT_HANDOVER.md` pro Repo.

## Consequences

### Positiv
- Enforcement ohne Agent-Discipline — CI erzwingt mechanisch
- PRs sind self-documenting (Checkliste = Audit-Trail)
- Symlink-Policy verhindert Workflow-Drift zwischen Repos
- Reusable CI Workflow: 1× pflegen, alle Repos profitieren sofort
- Draft-PR-Skip: WIP-Entwicklung bleibt ungestört

### Negativ / Risiken
- CI Gate blockiert auch WIP-PRs wenn nicht als Draft markiert
  → Mitigation: Draft-PR-Status nutzen während Entwicklung
- `ASSUMPTION[unverified]` muss immer aufgelöst werden
  → Akzeptiert: das ist der Zweck des QM-Systems

## Implementation

- `platform/.github/workflows/_ci-python.yml` — `enable_qm_gate` Input + `qm-gate` Job
- `risk-hub/.github/workflows/ci.yml` — `qm-gate` Job direkt integriert
- `risk-hub/.github/PULL_REQUEST_TEMPLATE/agent-pr.md` — Self-Review Gate Block
- `platform/.windsurf/workflows/workflow-index.md` — Symlink-Policy Abschnitt

## References

- ADR-066: AI Engineering Squad — Rollen, Gates, Workflows
- ADR-067: Work Management — Issues, AI-Agent-Protokoll
- ADR-081: Scope Management — affected_paths
- ADR-108: Agent QA Cycle — Self-Review, AuditStore
- agentic-coding.md v4: Phase 0 PCV, Step 5 Self-Review
