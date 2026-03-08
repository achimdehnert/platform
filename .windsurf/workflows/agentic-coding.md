---
description: Fully Agentic Coding — Task definieren, planen, routen, ausführen, bewerten (v2)
---

# Agentic Coding Workflow v2

Operationalisiert ADR-066 (AI Engineering Squad) + ADR-068 (Adaptive Model Routing)
+ ADR-080 (Multi-Agent Coding Team Pattern) + ADR-107 (Extended Agent Team)
+ ADR-108 (Agent QA-Zyklus + Kostenkontrolle).

---

## Voraussetzungen

- `agent_team_config.yaml` im Repo vorhanden und aktuell (Schema v2.0)
- GitHub Issue für den Task existiert (ADR-067)
- Betroffene ADRs bekannt

---

## Step 0: Governance Check (immer — Gate 0)

Vor jedem nicht-trivialen Task (`complexity >= moderate`):

```bash
# /governance-check aufrufen
# Prüft: ADR-Compliance, Platform-Patterns, bekannte Anti-Patterns
```

**Blockiert bei ADR-Verletzung.** Kein Weiter ohne grünen Governance-Check.

---

## Step 1: Task-Template + Budget-Check

Pflichtfelder aus `.windsurf/templates/ai-task.yaml`:

- `title`, `type`, `complexity`, `risk_level`, `github_issue`
- `acceptance_criteria` — mindestens 1 maschinenprüfbares Kriterium
- `affected_paths`

**Budget-Check (ADR-108 §3.4)** vor Ausführung:

```python
from orchestrator_mcp.audit_store import AuditStore

store = AuditStore()
estimate = store.get_cost_estimate(
    task_id="t-001",
    model_tier="standard_coding",
    estimated_tokens=50_000,
)
if not estimate["within_budget"]:
    # Warnung: Budget-Überschreitung geplant — Tech Lead entscheidet
    pass
```

Budget-Grenzen (ADR-108):

| Complexity | Budget | Hard-Limit |
|------------|--------|------------|
| trivial | 5.000 | 10.000 |
| simple | 20.000 | 40.000 |
| moderate | 80.000 | 150.000 |
| complex | 200.000 | 400.000 |
| architectural | 500.000 | 1.000.000 |

---

## Step 2: Planner / TaskGraph (nur bei complexity >= complex)

```python
from orchestrator_mcp.tools import agent_plan_task

plan = agent_plan_task(
    description="Implement feature X",
    task_type="feature",
    complexity="complex",
)
# plan["branches"] — Liste von Sub-Tasks mit role + steps
# plan["estimated_steps"] — Gesamtzahl Schritte
# plan["needs_tech_lead_plan"] — True bei architectural
```

Unabhängige Branches (disjunkte `affected_paths`) laufen in Step 4 parallel.

---

## Step 3: TaskRouter (ADR-068)

```python
from orchestrator_mcp.tools import analyze_task

decision = analyze_task("Implement feature X")
# decision["recommended_role"], decision["gate_level"]
# decision["model_recommendation"] — swe | opus
# decision["auto_eligible"] — True = kein Approval nötig
```

Routing-Matrix:
- `trivial/simple`  → `swe` (budget_cloud)
- `moderate`        → `swe` (standard_coding)
- `complex`         → `opus` (high_reasoning)
- `architectural`   → `opus` (high_reasoning)

**Gate-2-Trigger**: `risk_level = critical` oder `auto_eligible = False`.

---

## Step 4: Ausführung + Handoff (ADR-080)

### Rollen-Zuweisung per ADR-107

| Task-Typ | Primäre Rolle | Gate |
|----------|--------------|------|
| `feature` | Developer | 1 |
| `bugfix` | Developer | 1 |
| `refactor` | Re-Engineer | 2 |
| `test` | Tester | 0 |
| `adr` | Tech Lead | 3 |
| `deployment` | Deployment Agent | 2 |
| `pr_review` | Review Agent | 1 |

### Step 4b: Rollback-Pfad (ADR-080 + ADR-108)

Bei `blocking_issues` oder `composite_score < 0.70`:

```
L1: Re-Engineer (auto, Gate 0) — max. 1 Retry
L2: Tech Lead Review (Gate 2) — bei 2× L1-Fail oder ADR-Verletzung
L3: User-Benachrichtigung (Gate 3)
L4: Task-Abort (AuditStore status=aborted)
```

---

## Step 5: Merger (nur bei parallelen Branches)

Merge-Konflikt → L2-Rollback (Tech Lead).

---

## Step 6: Guardian-Check (Gate 0 — immer)

```bash
ruff check . --fix
bandit -r . -ll
mypy . --ignore-missing-imports
```

Guardian-Fail → L1-Rollback. 2× Fail → L2.

---

## Step 7: Quality Evaluator (ADR-108 §3.2)

```python
from orchestrator_mcp.agent_team.evaluator import QualityEvaluator
from orchestrator_mcp.agent_team.completion import TaskCompletionChecker, AcceptanceCriterion

# Phase 1: Completion Check
checker = TaskCompletionChecker()
completion = checker.check(
    task_id="t-001",
    criteria=[
        AcceptanceCriterion(id="ac-1", description="Tests pass", fulfilled=True),
        AcceptanceCriterion(id="ac-2", description="Migration exists", fulfilled=True),
    ],
)

# Phase 2: Quality Evaluation
evaluator = QualityEvaluator()
score = evaluator.evaluate(
    task_id="t-001",
    task_type="moderate",
    agent_role="developer",
    model_tier="standard_coding",
    completion_score=completion.completion_score,
    guardian_passed=True,       # aus Step 6
    coverage_delta=0.02,        # aus pytest --cov
    adr_compliance=True,        # aus mcp12_check_violations
    iteration_count=1,
    tokens_used=45_000,
)

if not score.passed:
    # score.rollback_level: L1 / L2 / L3 / L4
    raise RuntimeError(f"QA failed: {score.summary()}")
```

Quality-Ziele (ADR-108):

| Metrik | Ziel | Gewicht | Bei Unterschreitung |
|--------|------|---------|---------------------|
| completion_score | 1.0 | 40% | L1-Retry |
| guardian_passed | True | 20% | L1-Rollback |
| coverage_delta | >= 0 | 10% | Warnung |
| adr_compliance | True | 20% | L2-Rollback |
| iteration_count | <= 2 | 10% | L2-Rollback |

`composite_score < 0.70` → L1-Rollback.

---

## Step 8: PR erstellen

```bash
git checkout -b ai/{agent-role}/{task-id}
git commit -m "feat(scope): description

Closes #{issue-number}
ADR: ADR-066, ADR-068, ADR-080, ADR-107, ADR-108
Task: {task-id}
QA: composite={score} guardian=OK iterations={n}"
```

PR-Body enthält automatisch:
- Acceptance Criteria: ✅ erfüllt / □ offen
- Quality Score: composite, guardian, coverage, iterations
- Token-Kosten: used / budget

---

## Step 9: AuditStore + GitHub Issue Update (ADR-108)

```python
from orchestrator_mcp.audit_store import AuditStore

store = AuditStore()
store.log_quality_score(score)          # QALog
store.log_cost(                          # CostLog
    task_id="t-001",
    task_type="moderate",
    agent_role="developer",
    model_tier="standard_coding",
    repository="org/repo",
    tokens_used=45_000,
    tokens_budget=80_000,
)
```

GitHub Issue erhält automatisch Kommentar mit QA-Summary.

---

## QA-Zyklus auf einen Blick (ADR-108)

```
Task fertig
    │
    ▼
[1] Completion Check     completion_score < 1.0 → Retry (max 2) → L1
    │
    ▼
[2] Quality Evaluation   composite_score < 0.70 → L1-Rollback
    │                    guardian=False → L1
    │                    adr_compliance=False → L2
    │                    iteration_count > 2 → L2
    ▼
[3] Cost Check           tokens > budget*1.2 → L2
    │                    tokens > hard_limit → L4-Abort
    ▼
[4] AuditStore           QALog + CostLog schreiben
                         GitHub Issue kommentieren
```

---

## Workflow auf einen Blick (v2.1)

```
Step 0: Governance Check        (immer bei complexity >= moderate)
Step 1: Task-Template + Budget  (immer)
Step 2: Planner / TaskGraph     (nur bei complexity >= complex)
Step 3: TaskRouter              (immer, pro Branch)
Step 4: Ausführung + Handoff   (immer) → bei Fail: Rollback L1–L4
Step 5: Merger                  (nur bei parallelen Branches)
Step 6: Guardian                (immer) → bei Fail: Rollback L1–L2
Step 7: Quality Evaluator       (immer) → ADR-108 QA-Zyklus
Step 8: PR + Handoff-Summary    (immer)
Step 9: AuditStore + Issue      (immer) → QALog + CostLog
```

---

## Referenzen

- ADR-066: AI Engineering Squad
- ADR-067: Work Management — Issues als SSOT
- ADR-068: Adaptive Model Routing
- ADR-080: Multi-Agent Coding Team Pattern
- ADR-107: Extended Agent Team — Deployment + Review Agent
- ADR-108: Agent QA-Zyklus — Aufgaben-Vollständigkeit, Kostenkontrolle
- Template: `.windsurf/templates/ai-task.yaml`
