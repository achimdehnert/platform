---
description: Fully Agentic Coding — Task definieren, planen, routen, ausführen, bewerten (v2)
---

# Agentic Coding Workflow v2

Operationalisiert ADR-066 (AI Engineering Squad) + ADR-068 (Adaptive Model Routing)
+ ADR-080 (Multi-Agent Coding Team Pattern — Handoff, Parallelisierung, Rollback).

---

## Voraussetzungen

- `agent_team_config.yaml` im Repo vorhanden und aktuell
- GitHub Issue für den Task existiert (ADR-067: Issues als Single Source of Truth)
- Betroffene ADRs sind bekannt

---

## Step 0: Governance Check (immer — Gate 0)

Vor jedem nicht-trivialen Task (complexity >= moderate):

```bash
# /governance-check aufrufen
# Prüft: ADR-Compliance, Platform-Patterns, bekannte Anti-Patterns
```

**Blockiert bei ADR-Verletzung.** Kein Weiter ohne grünen Governance-Check.

---

## Step 1: Task-Template ausfüllen

Kopiere `.windsurf/templates/ai-task.yaml` und fülle alle Pflichtfelder aus:

```bash
cp .windsurf/templates/ai-task.yaml /tmp/task-$(date +%s).yaml
```

Pflichtfelder:
- `title` — kurze imperative Beschreibung
- `type` — feature | bugfix | refactor | test | adr | review | infra
- `complexity` — trivial | simple | moderate | complex | architectural
- `risk_level` — low | medium | high | critical
- `github_issue` — verlinktes Issue (z.B. `achimdehnert/platform#4`)
- `acceptance_criteria` — mindestens 1 maschinenprüfbares Kriterium
- `affected_paths` — betroffene Dateien/Verzeichnisse

---

## Step 2: Planner (ADR-080 — nur bei complexity >= complex)

Bei einfachen Tasks diesen Schritt überspringen → direkt zu Step 3.

```python
from orchestrator_mcp.agent_team.planner import Planner

planner = Planner()
task_graph = planner.decompose(task)
# task_graph.branches: Liste von Sub-Tasks
# task_graph.dependencies: Welche Branches parallel laufen können
print(task_graph.summary())
```

**Ergebnis:** `TaskGraph` mit 1–3 Branches. Unabhängige Branches (disjunkte
`affected_paths`) laufen in Step 4 parallel.

---

## Step 3: TaskRouter aufrufen (ADR-068)

Der Router analysiert das Task-Template und empfiehlt einen Modell-Tier pro Branch.

```python
from orchestrator_mcp.agent_team.router import TaskRouter

router = TaskRouter()
decision = router.route(
    task_id="t-001",
    complexity=TaskComplexity.MODERATE,
    risk_level=RiskLevel.MEDIUM,
    requires_planning=True,
)
print(decision.recommended_tier, decision.confidence, decision.reason)
```

Routing-Matrix:
- `trivial/low`    → `lean_local`
- `simple/medium`  → `budget_cloud`
- `moderate`       → `standard_coding`
- `complex/high`   → `standard_coding` oder `high_reasoning`
- `architectural`  → `high_reasoning`

**Confidence < 0.7 oder risk_level = critical**: Gate 2 — Mensch entscheidet Tier.

---

## Step 4: Agent-Rolle + Ausführung (ADR-066 + ADR-080)

### Rollen-Zuweisung

| Task-Typ | Primäre Rolle | Gate |
|----------|--------------|------|
| `feature` | Developer → TL Review | Gate 2 |
| `bugfix` | Developer | Gate 1 |
| `refactor` | Re-Engineer → TL Approve | Gate 2 |
| `test` | Tester → Developer | Gate 1 |
| `adr` | Tech Lead | Gate 2 |
| `review` | Tech Lead | Gate 2 |
| `infra` | Tech Lead | Gate 3 |

### Parallele Ausführung (bei TaskGraph mit Branches)

```python
from orchestrator_mcp.agent_team.workflows import run_workflow

result = run_workflow(task_graph, router=TaskRouter())
# Bei mehreren Branches: parallel wenn affected_paths disjunkt
# Jeder Branch produziert ein AgentHandoff-Objekt
```

Jeder Agenten-Übergang produziert ein `AgentHandoff` (ADR-080):
- `artifacts_produced` — erzeugte Dateien/Änderungen
- `criteria_fulfilled` / `criteria_open` — Acceptance-Criteria-Status
- `context_summary` — ≤ 500 Zeichen für den nächsten Agenten
- `blocking_issues` — leer = kein Block, sonst → Rollback-Pfad (Step 4b)

### Step 4b: Rollback-Pfad (ADR-080)

Bei `blocking_issues` oder `quality_score < 0.70`:

```
Level 1: Re-Engineer (automatisch, Gate 0) — max. 1 Retry
Level 2: Tech Lead Review (Gate 2) — Architektur-Entscheidung
Level 3: Human-in-the-Loop (Gate 3) — User-Benachrichtigung
Level 4: Task-Abort (Gate 4) — AuditStore: status=aborted
```

---

## Step 5: Merger (ADR-080 — nur bei parallelen Branches)

```python
from orchestrator_mcp.agent_team.merger import Merger

merger = Merger()
merged = merger.merge(task_graph.branches)
# Merge-Konflikt → Level 2 Rollback (Tech Lead)
```

Bei Single-Branch-Tasks diesen Schritt überspringen.

---

## Step 6: Guardian-Check (Gate 0 — immer, nach Merge)

```bash
# Ruff
ruff check . --fix

# Bandit
bandit -r . -ll

# MyPy (wenn typed)
mypy . --ignore-missing-imports
```

Guardian-Fail → Level 1 Rollback (Re-Engineer, max. 1 Retry).
2× Fail → Level 2 (Tech Lead).

---

## Step 7: Quality Evaluator (ADR-068)

```python
from orchestrator_mcp.agent_team.evaluator import QualityEvaluator

evaluator = QualityEvaluator()
score = evaluator.evaluate(result)
print(score.composite_score, score.completion_score)
```

Quality-Ziele:

| Metrik | Ziel | Bei Unterschreitung |
|--------|------|---------------------|
| `completion_score` | ≥ 0.80 | Level 1 Rollback |
| `guardian_passed` | 100% | Level 1 Rollback |
| `coverage_delta` | ≥ 0 | Warnung (kein Block) |
| `iteration_count` | ≤ 2 | Level 2 Rollback |
| `adr_compliance` | 100% | Level 2 Rollback |

---

## Step 8: PR erstellen (ADR-067 + ADR-080)

```bash
git checkout -b ai/{agent-role}/{task-id}

git commit -m "feat(scope): description

Closes #{issue-number}
ADR: ADR-066, ADR-068, ADR-080
Task: {task-id}"
```

**PR-Body wird aus `AgentHandoff.context_summary` + Quality-Score automatisch generiert:**

```markdown
## Agent Handoff Summary
{handoff.context_summary}

## Acceptance Criteria
✅ {criteria_fulfilled}
⬜ {criteria_open}

## Quality Score
- Composite: {score.composite_score}
- Guardian: ✅ / ❌
- Coverage Delta: {delta}
- Iterations: {count}
- ADR Compliance: ✅ / ❌
```

---

## Step 9: AuditStore + GitHub Issue Update (ADR-068)

```python
from orchestrator_mcp.audit_store import AuditStore

store = AuditStore()
store.log_quality_score(score)         # Quality-Score
store.log_handoff(handoff)             # AgentHandoff (ADR-080)
```

GitHub Issue erhält automatisch Kommentar mit Quality-Score-Summary.

---

## Entscheidungsbaum: Wann welcher Tier?

```
Task eingehend
    │
    ├─ complexity=trivial, risk=low → lean_local
    │
    ├─ complexity=simple|moderate, risk=low|medium → budget_cloud
    │   └─ Score < 0.80 nach 3 Versuchen → upgrade zu standard_coding
    │
    ├─ complexity=moderate|complex, risk=medium|high → standard_coding
    │   └─ Score < 0.80 nach 3 Versuchen → upgrade zu high_reasoning
    │
    ├─ complexity=architectural, risk=high|critical → high_reasoning
    │   └─ Kein automatischer Upgrade — Gate 4 (Human-Only)
    │
    └─ risk=critical (immer) → Gate 2: Mensch bestätigt Tier
```

---

## Workflow auf einen Blick (v2)

```
Step 0: Governance Check        (immer bei complexity >= moderate)
Step 1: Task-Template           (immer)
Step 2: Planner / TaskGraph     (nur bei complexity >= complex)
Step 3: TaskRouter              (immer, pro Branch)
Step 4: Ausführung + Handoff    (immer) → bei Fail: Rollback L1–L4
Step 5: Merger                  (nur bei parallelen Branches)
Step 6: Guardian                (immer) → bei Fail: Rollback L1–L2
Step 7: Quality Evaluator       (immer) → bei Score < 0.70: Rollback
Step 8: PR + Handoff-Summary    (immer)
Step 9: AuditStore + Issue      (immer)
```

---

## Referenzen

- ADR-066: AI Engineering Squad — Rollen, Gates, Workflows
- ADR-067: Work Management — Issues, AI-Agent-Protokoll
- ADR-068: Adaptive Model Routing — Routing-Matrix, Quality Metrics
- ADR-080: Multi-Agent Coding Team Pattern — Handoff, Parallelisierung, Rollback
- Template: `.windsurf/templates/ai-task.yaml`
