---
status: accepted
date: 2026-05-11
decision-makers: [Achim Dehnert]
implementation_status: stufe-1-2-implemented
related: [ADR-068, ADR-095, ADR-115, ADR-116, ADR-194, ADR-195]
---

# ADR-196: Adaptive Erweiterung zu ADR-116 — Outcome-Telemetrie, Drift-Report, Bandit

## Status

Accepted — Stufen 1 + 2 in Produktion seit 2026-05-11.
Stufe 3 (Bandit) als Framework hinter Feature-Flag (default OFF).

## Context

ADR-116 etabliert ein **deterministisches** Routing über `_ROUTE_TABLE` in
`orchestrator_mcp.model_selector`. Vorteil: 100 % vorhersagbar, debugbar.
Nachteil: Statisch — kein Lernsignal aus realen Outcomes, keine Drift-Erkennung
wenn Modellqualität sich ändert.

Beobachtete Lücken in 6 Wochen Betrieb (ADR-115 + ADR-194):

- **Lock-in auf veraltete Defaults**: Wechsel von claude-3.5-sonnet → claude-sonnet-4-6
  blieb mehrere Releases unbemerkt, weil kein Wirksamkeits-Signal existierte.
- **Cerebras-Migration ohne Feedback**: Umstellung Tier 1a auf Cerebras-Modelle
  (2026-05-11) — niemand konnte sagen ob Success-Rate gehalten wird.
- **Kostendrift unsichtbar**: Per-Cell Cost-Drift (Modell wird teurer/billiger)
  schlug sich nicht im Dashboard nieder.

Vorbild: Job-Dauer-Feedback-Loop in `estimate_job.py` (70 % Katalog +
30 % Mittelwert, persistiert in `.job_measurements.json`).

## Decision

Die statische Matrix bleibt **Single Source of Truth**. Wir legen drei
**additive Stufen** darüber, ohne den deterministischen Default zu brechen:

### Stufe 1 — Outcome-Telemetrie (Stand: implementiert 2026-05-11)

- `ModelSelection` um Felder `role` und `complexity` erweitert
- `ModelSelector.record_outcome(selection, success, latency_seconds, retry_count)`
- Persistenz: `.routing_outcomes.json` (Cap 50/Cell, Env-Override `MODEL_SELECTOR_OUTCOMES_PATH`)
- Helper `record_outcome_for_call(role, complexity, model, …)` für Call-Sites
  ohne `ModelSelection`-Objekt
- Verdrahtet:
  - `agent_team/step_executor.py` (StepExecutor)
  - `agent_team/llm_adapter.py` (Adapter — fängt alle direkten Caller inkl. `task_pipeline`)
- **Per-call DB-Persistierung** (2026-05-11): `tier`-Spalte in `llm_calls`,
  gefüllt via `lookup_tier(role, complexity, model)` an allen 4 INSERT-Sites
  (`llm_adapter`, `task_pipeline`, `cascade_logger`, `headless/bridge`)

### Stufe 2 — Wöchentlicher Drift-Report (Stand: implementiert 2026-05-11)

- `scripts/routing_outcomes_report.py` — Markdown-Output
- Sektionen: Overview, Per-Cell-Tabelle, Matrix-vs-Observed, Downgrade-Kandidaten,
  Anomalien <50 % Success, Coverage-Gaps
- Persistenz: Tabelle `routing_reports` in orchestrator_mcp DB
- systemd: `routing-report.timer` (Mon 06:00 UTC) → `routing-report.service`
  (docker exec orchestrator_mcp + `--persist`-Flag) — installiert auf 88.198.191.108
- Dev-Hub-Karte: `apps/controlling/services.py:get_latest_routing_report()` +
  Partial `_routing_report.html` im Controlling-Dashboard, HTMX-Refresh alle 5 min

### Stufe 3 — Thompson Sampling Bandit (Stand: Framework, default OFF)

- `orchestrator_mcp/bandit.py`
- Aktivierung via env `MODEL_SELECTOR_BANDIT_ENABLED=1`
- 6 soft cells: `(developer|tester|reviewer) × (moderate|complex)`
- **Hard constraints außerhalb des Bandits**: `SECURITY_AUDITOR` und `ARCHITECTURAL`
  bleiben deterministisch
- Beta(1+s, 1+f)-Posteriors aus `get_outcome_stats()`, Floor `BANDIT_FLOOR=10 %`
  gegen Lock-in
- Genau **eine** Alternative pro soft cell (`_BANDIT_ALTS`)
- Audit: stdlib `logging.warning(deviation=true)` wenn Bandit von Matrix abweicht
- Verdrahtung in `ModelSelector._lookup` (cost_sensitive bypasst Bandit)
- 11 Tests in `tests/test_bandit.py`
- **Aktivierungs-Kriterium**: ≥ 30 Observations pro soft cell

### Stufe 4 — Contextual Bandit (Future)

Nicht entscheiden bevor Stufe 3 messbaren Gewinn nachweist.

## Architektur-Prinzipien (nicht verhandelbar)

1. **Matrix bleibt deterministischer Default** — bei `MODEL_SELECTOR_BANDIT_ENABLED=0`
   verhält sich das System identisch zu reinem ADR-116.
2. **Hard Constraints sind kein Lernziel** — `SECURITY_AUDITOR` darf nie
   downgegradet werden, `ARCHITECTURAL` nicht in Cerebras.
3. **Kein objektives Signal → keine Adaption** — `chat`/`ask`/`planner` haben
   keine harten Erfolgs-Metriken; deren Outcome bleibt heuristisch.
4. **Erklärbarkeit per Audit** — jede Bandit-Abweichung erzeugt eine Log-Zeile
   mit `(role, complexity, matrix_default, chosen_alt, posterior)`.

## Open Items

- **Concept-Drift-Decay**: Bandit-Posteriors müssen resettet werden wenn
  `_TIER_COST_PER_1K` oder `_BANDIT_ALTS` mutiert — sonst lernt der Bandit
  gegen veraltete Annahmen.
- **Audit-Persistenz**: Bandit-Deviations aktuell nur in stdout — sollten in
  eigene Tabelle `routing_bandit_audit` für Wochenreport-Aggregation.

## Consequences

### Positiv
- Drift-Erkennung pro `(role, complexity)`-Zelle, sichtbar im dev-hub Dashboard
- Datengrundlage für ADR-Reviews bei Modell-Wechseln
- Optionale Bandit-Aktivierung pro Squad/Repo ohne Code-Deployment
- `tier`-Persistierung macht Per-Task-Spend-Analysen unabhängig von Modell-Namen

### Negativ
- Lernsignal nur bei ~60 % der Roles objektiv (developer/tester via Tests/Lint/recurring_errors)
- Bandit braucht mehrere Wochen organische Last bis Aktivierung sinnvoll ist
- Zusätzliche Tabelle (`routing_reports`) + JSON-File (`.routing_outcomes.json`)
  als zusätzlicher State

## Implementation Status

| Stufe | Status | Commit / Artefakt |
|-------|--------|-------------------|
| 1 — Outcome-Telemetrie | ✅ live | `75b0a17` (StepExecutor) + 2026-05-11 Adapter-Hook |
| 1b — `tier` in `llm_calls` | ✅ live | mcp-hub `a9651ad`, dev-hub `4259680` |
| 2 — Wochenreport | ✅ live | `scripts/routing_outcomes_report.py`, systemd timer |
| 2b — Drift-Card | ✅ live | dev-hub `173d735` |
| 3 — Bandit Framework | ✅ OFF | `orchestrator_mcp/bandit.py` |
| 3b — Bandit-Aktivierung | ⏳ wartet | ≥ 30 obs/cell |
| 3c — Decay + Audit-Persistenz | ⏳ open | — |
| 4 — Contextual Bandit | 🔮 future | nach Stufe-3-Gewinn-Nachweis |

## References

- ADR-068 — TaskRouter mit LLM-Routing
- ADR-095 — Quality Level Routing
- ADR-115 — Controlling Dashboard (`llm_calls`)
- ADR-116 — Statisches Routing (`_ROUTE_TABLE`)
- ADR-194/195 — Universal LLM-Logging via Gateway
- Policy: `~/.claude/policies/llm-routing.md`
- Code: `mcp-hub/orchestrator_mcp/model_selector.py`,
  `agent_team/model_router_integration.py`, `bandit.py`
- Report-Script: `mcp-hub/scripts/routing_outcomes_report.py`
- Dashboard: `dev-hub/apps/controlling/templates/.../_routing_report.html`
