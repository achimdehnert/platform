---
description: Fully Agentic Coding — Task definieren, planen, routen, ausführen, bewerten (v3)
---

# Agentic Coding Workflow v3

Operationalisiert ADR-066 + ADR-068 + ADR-080 + ADR-107 + ADR-108.
**v3**: Vollständig auf verfügbare MCP-Tools umgestellt — kein Pseudo-Code mehr.

---

## Übersicht: Der vollständige Loop

```
Step 0: Governance Check       → mcp14_get_context_for_task
Step 1: Task definieren        → analyze_task + agent_plan_task
Step 2: Kostenschätzung        → get_cost_estimate
Step 3: Implementieren         → Developer (Gate 1)
Step 4: Guardian-Check         → ruff + bandit (Gate 0)
Step 5: Verifikation           → verify_task  ← NEU (ADR-108)
Step 6: QA Score               → evaluate_task ← NEU (ADR-108)
Step 7: PR + Commit
Step 8: AuditStore + Issue
```

Bei Fail in Step 5/6 → Rollback-Pfad, zurück zu Step 3.

---

## Step 0: Governance Check (immer bei complexity >= moderate)

> ⚠️ MCP-Prefixes sind environment-spezifisch — aktuellen Prefix aus `.windsurf/rules/mcp-tools.md` lesen.

```
MCP: <platform-context-mcp>_get_context_for_task(repo, file_type)
MCP: <platform-context-mcp>_check_violations(code_snippet)
MCP: <platform-context-mcp>_get_banned_patterns(context)
```

**Blockiert bei ADR-Verletzung.** Kein Weiter ohne grünen Check.

---

## Step 1: Task analysieren + planen

```
MCP: analyze_task(description)
→ liefert: task_type, complexity, recommended_role, gate_level, model_recommendation

MCP: agent_plan_task(description, task_type, complexity)
→ liefert: branches[], estimated_steps, assigned_role, gate_level
```

Rollen-Zuweisung nach Gate:

| Task-Typ | Rolle | Gate |
|----------|-------|------|
| `feature` | Developer | Gate 1 |
| `bugfix` | Developer | Gate 1 |
| `test` | Tester | Gate 0 |
| `refactor` | Re-Engineer | Gate 2 |
| `adr` / `architecture` | Tech Lead | Gate 2 |
| `deployment` | Deployment Agent | Gate 2 |
| `pr_review` | Review Agent | Gate 1 |

Gate 2+ → User um Approval bitten (Chat), bevor weitergemacht wird.

---

## Step 2: Kostenschätzung (optional, empfohlen bei complex+)

```
MCP: get_cost_estimate(task_id, model, estimated_tokens)
→ liefert: cost_usd, budget_status (ok/over), token_budget
```

Modell-Wahl:

| Complexity | Modell | Kosten/1k | Anwendung |
|------------|--------|-----------|-----------|
| `trivial` | `grok_fast` | $0.0002 | docu-update, CHANGELOG, README-Sync |
| `simple` | `gpt_low` | $0.001 | Tests schreiben, kleine Bugfixes |
| `moderate` | `swe` | $0.003 | Features, Refactoring |
| `complex/architectural` | `opus` | $0.015 | ADRs, Architektur, komplexe Bugs |

> **docu-update Issues** → immer `grok_fast` (Label: `tier-3`, `docu-update`)

Bei `budget_status = over` → complexity herunterstufen oder Task splitten.

---

## Step 3: Implementieren (Developer / Gate 1)

Cascade implementiert den Task.

**Pflicht-Konventionen:**
- Kein direktes `print()` in Produktion — Logger verwenden
- Imports immer am Dateianfang
- Keine Hard-coded Credentials
- Tests für jede neue Funktion
- Commit-Message: `type(scope): description\n\nCloses #N\nADR: ADR-XXX`

---

## Step 4: Guardian-Check (Gate 0 — immer nach Implementierung)

```bash
# Ruff (Linter + Formatter)
ruff check . --fix

# Bandit (Security)
bandit -r . -ll

# Tests
pytest tests/ -q --tb=short
```

**Bei Fail**: sofort fixen — nicht weitermachen.

---

## Step 5: Verifikation — verify_task (ADR-108, Gate 0)

```
MCP: verify_task(
    task_id,
    criteria=[
        {"description": "Tests grün", "met": True/False, "blocking": True},
        {"description": "Ruff clean", "met": True/False, "blocking": True},
        {"description": "Acceptance Criteria erfüllt", "met": True/False, "blocking": True},
    ],
    tests_passed=True/False,
    lint_passed=True/False,
    adr_violations=0,
)
```

**Ergebnis:**
- `is_complete = True` → weiter zu Step 6
- `is_complete = False` → `next_action` lesen → zurück zu Step 3 (max. 3 Retries)
- 3× Fail → User um Approval bitten (Gate 2 Escalation)

---

## Step 6: QA Score — evaluate_task (ADR-108)

```
MCP: evaluate_task(
    task_id,
    completion_score,     # aus verify_task.score
    guardian_passed,      # aus Step 4
    adr_violations,       # aus <platform-context-mcp>_check_violations
    iterations_used,      # Anzahl Implementierungs-Iterationen
    tokens_used,          # geschätzt aus Kontext
    complexity,
)
```

**Rollback-Entscheidung:**

| Score | Level | Aktion |
|-------|-------|--------|
| ≥ 0.85 | `none` | Ship it → Step 7 |
| 0.70–0.84 | `soft` | Retry mit Feedback → Step 3 |
| 0.50–0.69 | `hard` | Revert, neu planen → Step 1 |
| < 0.50 | `escalate` | User Approval (Gate 2) |

---

## Step 7: Commit + PR

```bash
git checkout -b ai/{role}/{task-id}
git add .
git commit -m "type(scope): description

Closes #{issue-number}
ADR: ADR-066, ADR-068, ADR-080, ADR-107, ADR-108
Task: {task-id}
QA: composite={score} rollback=none"
```

PR-Body enthält:
- Acceptance Criteria (✅ / ⬜)
- QA Score + Rollback-Level
- ADR-Referenzen

---

## Step 8: AuditStore + GitHub Issue Update (ADR-068)

```
# AuditStore: Log action to GitHub Issue comment
# Prefix aus mcp-tools.md (github-mcp)
MCP: <github-mcp>_add_issue_comment(owner, repo, issue_number, body)
```

Issue-Kommentar enthält: QA Score, verify_task Ergebnis, Cost-Estimate, Rollback-Level.

---

## Rollback-Pfad

```
verify_task → is_complete=False
    │
    ├─ next_action=fix_tests    → pytest failures beheben → retry Step 4
    ├─ next_action=fix_lint     → ruff check --fix → retry Step 4
    ├─ next_action=fix_adr      → platform-context violations beheben → retry Step 4
    └─ next_action=fix_criteria → Acceptance Criteria offen → retry Step 3

evaluate_task → rollback_level
    │
    ├─ soft     → Feedback an Developer → retry Step 3 (max. 1×)
    ├─ hard     → git revert → neu planen ab Step 1
    └─ escalate → User Approval → Human-in-the-Loop
```

---

## Workflow auf einen Blick (v3)

```
Step 0: Governance Check    → mcp14_get_context_for_task   (complexity >= moderate)
Step 1: analyze + plan      → analyze_task, agent_plan_task (immer)
Step 2: Kostenschätzung     → get_cost_estimate             (complex+)
Step 3: Implementieren      → Developer Gate 1              (immer)
Step 4: Guardian            → ruff, bandit, pytest          (immer)
Step 5: verify_task         → is_complete?                  (immer) ← ADR-108
Step 6: evaluate_task       → rollback_level?               (immer) ← ADR-108
Step 7: Commit + PR                                         (immer)
Step 8: AuditStore + Issue  → log_action, Issue-Kommentar   (immer)
```

---

## Referenzen

- ADR-066: AI Engineering Squad — Rollen, Gates, Workflows
- ADR-067: Work Management — Issues, AI-Agent-Protokoll
- ADR-068: Adaptive Model Routing — Routing-Matrix, Quality Metrics
- ADR-080: Multi-Agent Coding Team Pattern — Handoff, Parallelisierung, Rollback
- ADR-107: Extended Agent Team — Deployment Agent, Review Agent
- ADR-108: Agent QA Cycle — QualityEvaluator, TaskCompletionChecker, AuditStore
