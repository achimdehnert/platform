---
status: accepted
date: 2026-03-08
decision-makers: Achim Dehnert
consulted: Cascade (Tech Lead)
informed: –
supersedes: –
amends: ADR-066-ai-engineering-team.md, ADR-068-aifw-quality-level-routing.md
related: ADR-066, ADR-068, ADR-080, ADR-107
---

# ADR-108: Agent QA-Zyklus — Aufgaben-Vollständigkeit, Fehlerbehandlung, Optimierungen, Kostenkontrolle

| Feld | Wert |
|------|------|
| **Status** | Accepted |
| **Datum** | 2026-03-08 |
| **Autor** | Achim Dehnert |
| **Amends** | ADR-066 (AI Engineering Squad), ADR-068 (Adaptive Model Routing) |
| **Related** | ADR-080 (Multi-Agent Pattern), ADR-107 (Extended Agent Team) |

---

## 1. Kontext und Problem

Nach ADR-107 (Extended Agent Team) ist die Rollen- und Deployment-Infrastruktur
operational. Es fehlt jedoch ein **systematischer QA-Zyklus**, der:

1. **Aufgaben-Vollständigkeit** misst — wurde der Task wirklich fertig gestellt?
2. **Fehler strukturiert behandelt** — Rollback-Eskalation L1→L4 ist beschrieben (ADR-080) aber nicht implementiert
3. **Optimierungspotenziale erkennt** — welche Agenten liefern schlechte Qualität, wo entstehen Retry-Schleifen?
4. **Kosten kontrolliert** — Token-Verbrauch pro Task, per Rolle, per Repo messen und begrenzen

### Konkrete Lücken (Stand 2026-03-08)

- `QualityEvaluator` in `agentic-coding.md` referenziert, aber nicht implementiert
- `AuditStore` ohne `completion_score`, `cost_tokens`, `model_tier`
- Keine `TokenBudget`-Durchsetzung — Kosten unkontrolliert
- Kein Feedback-Loop: schlechte Agent-Performance wird nicht erkannt
- `iteration_count` wird nicht getrackt → Endlosschleifen möglich

---

## 2. Decision Drivers

- **Vollständigkeit**: Jeder Task hat messbare Acceptance Criteria — Pass/Fail
- **Kostenkontrolle**: Budget pro Task-Typ und Modell-Tier — kein ungeplanter Overrun
- **Qualitätssicherung**: composite_score < 0.70 → automatischer Rollback
- **Transparenz**: Jeder QA-Lauf ist im AuditStore nachvollziehbar
- **Optimierung**: Trend-Daten für schlechteste Rollen/Repos sichtbar machen

---

## 3. Decision

### 3.1 QA-Zyklus — 4 Phasen

```
Task abgeschlossen
    │
    ▼
[Phase 1] Completion Check
    Alle Acceptance Criteria erfüllt?
    completion_score = erfüllt / gesamt
    completion_score < 1.0 → Retry (max. 2) oder L1-Rollback
    │
    ▼
[Phase 2] Quality Evaluation
    guardian_passed (Ruff/Bandit/MyPy)
    coverage_delta >= 0
    adr_compliance 100%
    iteration_count <= 2
    composite_score < 0.70 → L1-Rollback
    │
    ▼
[Phase 3] Cost Check
    tokens_used <= budget_limit für diesen task_type + model_tier
    Overrun > 20% → L2-Rollback (Tech Lead entscheidet)
    │
    ▼
[Phase 4] AuditStore
    QALog: alle Scores, Token-Kosten, Tier, Iterations
    GitHub Issue Kommentar mit QA-Summary
```

### 3.2 Quality Metrics

| Metrik | Ziel | Bei Unterschreitung | Gewichtung |
|--------|------|---------------------|------------|
| `completion_score` | 1.0 (alle AC erfüllt) | Retry → L1 | 40% |
| `guardian_passed` | True | L1-Rollback | 20% |
| `coverage_delta` | >= 0 | Warnung | 10% |
| `adr_compliance` | True | L2-Rollback | 20% |
| `iteration_count` | <= 2 | L2-Rollback | 10% |

`composite_score = Σ(metrik_wert * gewichtung)` — Schwelle: **0.70**

### 3.3 Rollback-Eskalation (operationalisiert)

| Level | Trigger | Aktion | Gate |
|-------|---------|--------|------|
| **L1** | composite_score < 0.70, guardian_fail, iteration_count > 2 | Re-Engineer, max. 1 Retry | 0 (auto) |
| **L2** | L1 2× gescheitert, adr_compliance=False, cost_overrun > 20% | Tech Lead Review | 2 |
| **L3** | L2 gescheitert | User-Benachrichtigung | 3 |
| **L4** | L3 ohne Response > 24h | Task-Abort, AuditStore status=aborted | 4 |

### 3.4 Token-Budget-Grenzen

| Task-Typ | Modell-Tier | Budget (Tokens) | Hard-Limit |
|----------|-------------|-----------------|------------|
| `trivial` | lean_local | 5.000 | 10.000 |
| `simple` | budget_cloud | 20.000 | 40.000 |
| `moderate` | standard_coding | 80.000 | 150.000 |
| `complex` | standard_coding | 200.000 | 400.000 |
| `architectural` | high_reasoning | 500.000 | 1.000.000 |

Overrun > Hard-Limit → Task-Abort (L4), kein Auto-Retry.

### 3.5 Neue Modelle / Implementierungsdateien

```
orchestrator_mcp/
├── agent_team/
│   ├── evaluator.py       # QualityEvaluator + QualityScore
│   └── completion.py      # TaskCompletionChecker + AcceptanceCriteria
├── models/
│   ├── qa_log.py          # QALog Django Model
│   └── cost_log.py        # CostLog Django Model (TokenBudget)
└── audit_store.py         # AuditStore Service
```

---

## 4. Implementierung

### Phase 1 — Core QA (dieser PR)
- [x] `orchestrator_mcp/agent_team/evaluator.py`
- [x] `orchestrator_mcp/agent_team/completion.py`
- [x] `orchestrator_mcp/models/qa_log.py`
- [x] `orchestrator_mcp/models/cost_log.py`
- [x] `orchestrator_mcp/audit_store.py`
- [x] `orchestrator_mcp/migrations/0002_qa_log_cost_log.py`

### Phase 2 — Workflow-Integration (nach Merge)
- [ ] `agentic-coding.md`: Step 7 QualityEvaluator auf echte Implementierung zeigen
- [ ] `agent_plan_task` in `tools.py`: completion_check nach Task-Ende
- [ ] GitHub Actions: QA-Summary als PR-Kommentar

### Phase 3 — Dashboard (mittelfristig)
- [ ] Operations Hub (dev-hub): QA-Trend-Ansicht
- [ ] Cost-Dashboard: Token-Verbrauch pro Rolle/Repo/Tag

---

## 5. Konsequenzen

### Positiv
- Aufgaben-Vollständigkeit messbar und durchsetzbar
- Token-Kosten pro Task sichtbar und begrenzt
- Rollback-Eskalation operationalisiert — kein manuelles Eingreifen bei L1
- Trend-Daten für Optimierung der Rollen- und Modell-Auswahl

### Negativ / Risiken
- QA-Overhead ~5% pro Task (Evaluation + AuditStore-Write)
- False Positives bei coverage_delta (neue Files zählen anders)
- Budget-Grenzen können zu frühem Abort führen (Hard-Limit zu eng)

### Neutrale Änderungen
- Alle Agent-Tasks schreiben jetzt QALog + CostLog — Storage-Overhead minimal
- `AuditStore` ersetzt direkte `DeploymentLog`-Writes in tools.py

---

## 6. Compliance

| ADR | Bezug |
|-----|-------|
| ADR-066 | Squad: Guardian-Fail → L1-Rollback jetzt implementiert |
| ADR-068 | Quality Metrics: composite_score, iteration_count jetzt tracking |
| ADR-080 | Rollback L1–L4: vollständig operationalisiert |
| ADR-107 | Agent Team: QA-Zyklus ergänzt bestehende Rollen |

---

## 7. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-03-08 | Achim Dehnert + Cascade | Initial |
