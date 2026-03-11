---
status: accepted
date: 2026-03-08
decision-makers: Achim Dehnert
consulted: Cascade (Tech Lead)
informed: –
supersedes: –
amends: –
related: [ADR-066, ADR-068, ADR-080, ADR-107, ADR-116]
implementation_status: implemented
implementation_evidence:
  - "orchestrator_mcp/agent_team/evaluator.py: QualityEvaluator + QualityScore"
  - "orchestrator_mcp/audit_store.py: AuditStore service (QALog, CostLog)"
  - "orchestrator_mcp/models/qa_log.py: QALog Django model"
  - "orchestrator_mcp/models/cost_log.py: CostLog Django model"
  - "orchestrator_mcp/tools.py: evaluate_task, verify_task, get_cost_estimate MCP tools"
  - "orchestrator_mcp/agent_team/tests/test_qa_tools.py: unit tests"
---

# ADR-108: Agent QA Cycle -- Quality Evaluator, Completion Gate, AuditStore

| Feld | Wert |
|------|------|
| **Status** | Accepted |
| **Datum** | 2026-03-08 |
| **Autor** | Achim Dehnert |
| **Related** | ADR-066 (AI Engineering Squad), ADR-068 (Adaptive Model Routing), ADR-080 (Multi-Agent Pattern), ADR-107 (Extended Agent Team), ADR-116 (Dynamic Model Router) |

---

## 1. Kontext und Problem

ADR-107 definiert ein erweitertes Agent-Team mit Deployment Agent, Review Agent und
Cascade als Tech Lead. Was fehlt: ein systematischer **Quality Assurance Cycle**, der
nach jeder Agent-Ausführung automatisch prüft, ob die Arbeit die Anforderungen erfüllt.

### Konkrete Probleme (Stand 2026-03-08)

**Problem 1: Keine automatische Qualitätsbewertung**
Agents führen Tasks aus, aber es gibt keinen strukturierten Mechanismus, um die Qualität
des Ergebnisses zu bewerten. Ob ein Task "fertig" ist, wird ad-hoc entschieden.

**Problem 2: Keine Completion-Prüfung**
Acceptance Criteria existieren (via `agent_plan_task`), aber niemand prüft systematisch,
ob sie erfüllt sind. Tasks werden als "done" markiert, obwohl Kriterien offen sind.

**Problem 3: Kein Audit Trail für Qualität und Kosten**
Token-Verbrauch, Iterationen und Qualitäts-Scores werden nicht persistiert. Ohne diese
Daten sind Kostenoptimierung und Agent-Performance-Vergleiche nicht möglich.

**Problem 4: Kein Budget-Enforcement**
Agents können beliebig viele Tokens verbrauchen. Es gibt keine Budget-Schwellen
pro Komplexitätsstufe und keine Warnung bei Überschreitung.

---

## 2. Decision Drivers

- **Automatisierung**: QA-Cycle soll ohne manuellen Eingriff laufen
- **Transparenz**: Qualitäts-Scores und Kosten müssen auditierbar sein
- **Feedback-Loop**: Schlechte Ergebnisse müssen automatisch zu Rollback/Retry führen
- **Budget-Awareness**: Token-Verbrauch muss pro Task trackbar und limitierbar sein
- **ADR-Compliance**: Ergebnisse müssen gegen Platform-Patterns geprüft werden

---

## 3. Considered Options

### Option A — Manuelles Review (abgelehnt)
Cascade reviewed jede Agent-Ausgabe manuell.
**Contra**: Skaliert nicht, Cascade wird zum Bottleneck.

### Option B — Nur Guardian-Check (abgelehnt)
Guardian (Ruff, Bandit, MyPy) als einzige Qualitätsprüfung.
**Contra**: Prüft nur Syntax/Style, nicht funktionale Vollständigkeit.

### Option C — Vollständiger QA Cycle mit Evaluator, Completion Gate und AuditStore (gewählt)
Drei-Stufen-Prüfung nach jeder Agent-Ausführung:
1. `verify_task` — Completion-Check gegen Acceptance Criteria
2. `evaluate_task` — Composite Quality Score aus 5 Dimensionen
3. AuditStore — Persistierung in QALog + CostLog

**Pro**: Vollständig automatisiert, auditierbar, mit Rollback-Entscheidung.

---

## 4. Decision

### 4.1 QA Cycle Ablauf

```
Agent führt Task aus
    │
    ▼
verify_task(criteria, tests_passed, lint_passed)
    │
    ├─ is_complete=True  → weiter zu evaluate_task
    ├─ is_complete=False → Retry mit Feedback (blocking_open)
    │
    ▼
evaluate_task(completion, guardian, adr_violations, iterations, tokens)
    │
    ├─ composite >= 0.85 → NONE    (Task erfolgreich abgeschlossen)
    ├─ composite 0.70–0.84 → SOFT  (Retry mit Feedback)
    ├─ composite 0.50–0.69 → HARD  (Revert zu letztem Known Good)
    ├─ composite < 0.50  → ESCALATE (Cascade/Mensch eingreifen)
    │
    ▼
AuditStore.log_quality_score() + AuditStore.log_token_usage()
```

### 4.2 QualityScore — Composite aus 5 Dimensionen

| Dimension | Gewicht | Beschreibung |
|-----------|---------|-------------|
| `completion_score` | 35% | TaskCompletionChecker — sind alle Acceptance Criteria erfüllt? |
| `guardian_score` | 25% | Guardian Agent Sign-off (Ruff, Bandit, MyPy clean) |
| `adr_compliance_score` | 20% | platform-context `check_violations` Ergebnis |
| `iteration_score` | 10% | Penalty für Iterationen über dem erwarteten Maximum |
| `token_score` | 10% | Penalty für Token-Verbrauch über Budget |

### 4.3 Rollback-Level

| Level | Schwelle | Aktion |
|-------|----------|--------|
| `NONE` | composite >= 0.85 | Task abgeschlossen, kein Rollback |
| `SOFT` | 0.70 – 0.84 | Retry mit spezifischem Feedback |
| `HARD` | 0.50 – 0.69 | Revert zu letztem Known Good State |
| `ESCALATE` | < 0.50 | Mensch/Cascade muss eingreifen |

### 4.4 Token-Budgets pro Komplexität

| Complexity | Token Budget | Max Iterations |
|------------|-------------|----------------|
| trivial | 10.000 | 2 |
| simple | 25.000 | 3 |
| moderate | 60.000 | 5 |
| complex | 120.000 | 7 |
| architectural | 200.000 | 9 |

**Hard Limits**: 250.000 Tokens, 10 Iterationen (unabhängig von Komplexität).

### 4.5 AuditStore — Persistenz-Modelle

**QALog** (`orchestrator_mcp/models/qa_log.py`):
- BigAutoField PK, public_id UUID, tenant_id BigInt
- task_id, task_type, repo, branch, agent_role, complexity
- Alle 5 Sub-Scores + composite_score
- rollback_level, is_complete, blocking_open (JSONField)
- iterations_used, tokens_used, token_budget
- Soft-delete (deleted_at), Timestamps

**CostLog** (`orchestrator_mcp/models/cost_log.py`):
- BigAutoField PK, public_id UUID, tenant_id BigInt
- task_id, model, complexity, agent_role
- tokens_used, token_budget, over_budget (bool), utilization (float)
- Timestamps

### 4.6 MCP Tools (orchestrator_mcp/tools.py)

| Tool | Beschreibung |
|------|-------------|
| `get_cost_estimate` | Pre-Execution Budget-Check: geschätzte Tokens gegen Budget prüfen |
| `evaluate_task` | Post-Execution: QualityScore berechnen, Rollback-Level bestimmen, in QALog persistieren |
| `verify_task` | Completion-Check: Acceptance Criteria + Tests + Lint prüfen |

---

## 5. Implementierung

### Phase 1 — Core (abgeschlossen)

- [x] `orchestrator_mcp/agent_team/evaluator.py` — QualityEvaluator + QualityScore + RollbackLevel
- [x] `orchestrator_mcp/audit_store.py` — AuditStore Service (log_quality_score, log_completion, log_token_usage, get_cost_estimate)
- [x] `orchestrator_mcp/models/qa_log.py` — QALog Django Model (BigAutoField, platform-konform)
- [x] `orchestrator_mcp/models/cost_log.py` — CostLog Django Model (BigAutoField, platform-konform)

### Phase 2 — MCP Tools (abgeschlossen)

- [x] `get_cost_estimate` in `tools.py` — Token-Kosten-Vorhersage mit Model-spezifischen Preisen
- [x] `evaluate_task` in `tools.py` — QualityScore-Berechnung + AuditStore-Persistierung
- [x] `verify_task` in `tools.py` — Completion-Check + Test/Lint-Status-Integration

### Phase 3 — Tests (abgeschlossen)

- [x] `orchestrator_mcp/agent_team/tests/test_qa_tools.py` — Unit Tests

### Phase 4 — Grafana Dashboard Integration (ausstehend)

- [ ] QALog-Panel in Agent Controlling Dashboard (ADR-116/Grafana)
- [ ] CostLog-Budget-Alerts in Grafana
- [ ] Rollback-Level-Trend-Panel

---

## 6. Konsequenzen

### Positiv
- Jeder Agent-Task hat einen messbaren Quality Score
- Budget-Überschreitungen werden erkannt und geloggt
- Rollback-Entscheidungen sind datenbasiert, nicht ad-hoc
- Audit Trail für Compliance und Performance-Analyse
- Grundlage für Grafana-Dashboards (ADR-116) und Kosten-Controlling

### Negativ / Risiken
- QALog/CostLog erzeugen zusätzliches DB-Volumen (Mitigation: Soft-Delete + Retention Policy)
- Composite-Gewichtung ist initial heuristisch (Mitigation: Gewichte via Config anpassbar)
- `verify_task` ist nur so gut wie die definierten Acceptance Criteria

---

## 7. Compliance

| ADR | Bezug |
|-----|-------|
| ADR-022 | BigAutoField, Django ORM, kein hardcoded SQL |
| ADR-041 | Service-Layer Pattern (AuditStore) |
| ADR-066 | Agent-Rollen: QA als Querschnittsfunktion |
| ADR-107 | Erweitert den Deployment/Review-Agent um QA-Feedback |
| ADR-109 | Multi-Tenancy: tenant_id auf allen Models |
| ADR-116 | Grafana-Integration für QA-/Cost-Metriken |

---

## 8. Referenzen

- ADR-066: AI Engineering Squad
- ADR-068: Adaptive Model Routing — Quality Feedback Loop
- ADR-080: Multi-Agent Coding Team Pattern
- ADR-107: Extended Agent Team — Deployment Agent
- ADR-116: Dynamic Model Router — Cost Tracking
- Implementation: `orchestrator_mcp/agent_team/evaluator.py`, `orchestrator_mcp/audit_store.py`
- Models: `orchestrator_mcp/models/qa_log.py`, `orchestrator_mcp/models/cost_log.py`
- Tools: `orchestrator_mcp/tools.py` (evaluate_task, verify_task, get_cost_estimate)
- Tests: `orchestrator_mcp/agent_team/tests/test_qa_tools.py`

---

## 9. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-03-08 | Achim Dehnert | Initial (gleichzeitig mit ADR-107) |
| 2026-03-11 | Cascade | ADR-Datei erstellt (war nur als INDEX-Eintrag vorhanden); implementation_status: implemented |
