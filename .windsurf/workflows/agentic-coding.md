---
description: Fully Agentic Coding — Task definieren, routen, ausführen, bewerten
---

# Agentic Coding Workflow

Operationalisiert ADR-066 (AI Engineering Squad) + ADR-068 (Adaptive Model Routing).
Verwende diesen Workflow für jeden AI-Agent-Task — von Bugfix bis Architektur-Review.

---

## Voraussetzungen

- `agent_team_config.yaml` im Repo vorhanden und aktuell
- GitHub Issue für den Task existiert (ADR-067: Issues als Single Source of Truth)
- Betroffene ADRs sind bekannt

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

## Step 2: TaskRouter aufrufen (ADR-068)

Der Router analysiert das Task-Template und empfiehlt einen Modell-Tier.

```python
# Manuell bis router.py implementiert (Phase 2 ADR-068):
# Nutze Routing-Matrix aus ADR-068 §Implementation Details

# Kurzregel:
# trivial/low    → lean_local oder budget_cloud
# simple/medium  → budget_cloud
# moderate       → standard_coding
# complex/high   → standard_coding oder high_reasoning
# architectural  → high_reasoning
```

**Confidence < 0.7 oder risk_level = critical**: Gate 2 — Mensch entscheidet Tier.

---

## Step 3: Agent-Rolle zuweisen (ADR-066)

Basierend auf Task-Typ die passende Rolle wählen:

| Task-Typ | Primäre Rolle | Gate |
|----------|--------------|------|
| `feature` | Developer → TL Review | Gate 2 |
| `bugfix` | Developer | Gate 1 |
| `refactor` | Re-Engineer → TL Approve | Gate 2 |
| `test` | Tester → Developer | Gate 1 |
| `adr` | Tech Lead | Gate 2 |
| `review` | Tech Lead | Gate 2 |
| `infra` | Tech Lead | Gate 3 |

---

## Step 4: Guardian-Check ausführen (Gate 0 — immer)

```bash
# Ruff
ruff check . --fix

# Bandit
bandit -r . -ll

# MyPy (wenn typed)
mypy . --ignore-missing-imports
```

Guardian blockiert bei `critical` oder `error`. Kein Merge ohne grünen Guardian.

---

## Step 5: Tests ausführen (Gate 0–1)

```bash
# Unit-Tests (kein DB)
pytest -m unit -x

# Integration-Tests (mit DB)
pytest -m integration

# Coverage-Report
pytest --cov=. --cov-report=term-missing
```

Coverage-Delta muss ≥ 0 sein (ADR-068 Quality Gate).

---

## Step 6: Quality Evaluator (ADR-068)

Bis `evaluator.py` implementiert ist — manuell prüfen:

| Metrik | Ziel | Prüfung |
|--------|------|---------|
| `completion_score` | ≥ 0.80 | Alle Acceptance Criteria erfüllt? |
| `guardian_passed` | 100% | Schritt 4 grün? |
| `coverage_delta` | ≥ 0 | Schritt 5 Coverage nicht gesunken? |
| `iteration_count` | ≤ 2 | Wie viele Review-Zyklen? |
| `adr_compliance` | 100% | Relevante ADRs eingehalten? |

---

## Step 7: PR erstellen + Issue verlinken (ADR-067)

```bash
# Branch-Pattern (ADR-066)
git checkout -b ai/{agent-role}/{task-id}

# Commit-Message mit Issue-Referenz
git commit -m "feat(scope): description

Closes #{issue-number}
ADR: ADR-066, ADR-068
Task: {task-id}"
```

PR-Beschreibung muss enthalten:
- Link zum GitHub Issue
- Ausgefülltes Task-Template (oder Link dazu)
- Quality-Score-Zusammenfassung (manuell bis Evaluator implementiert)

---

## Step 8: Metriken in AuditStore schreiben (ADR-068)

Bis `audit_store.py` implementiert — als Kommentar im GitHub Issue dokumentieren:

```markdown
## Task Quality Score
- Model Tier: standard_coding (claude-sonnet-4)
- Guardian: ✅ passed
- Coverage Delta: +0.02
- Iterations: 1
- Completion Score: 0.92 (alle Acceptance Criteria erfüllt)
- ADR Compliance: ✅
- Cost: ~$0.08
```

---

## Entscheidungsbaum: Wann welcher Tier?

```
Task eingehend
    │
    ├─ complexity=trivial, risk=low → lean_local (Qwen lokal)
    │
    ├─ complexity=simple|moderate, risk=low|medium → budget_cloud (M2.5)
    │   └─ Score < 0.80 nach 3 Versuchen → upgrade zu standard_coding
    │
    ├─ complexity=moderate|complex, risk=medium|high → standard_coding (Sonnet)
    │   └─ Score < 0.80 nach 3 Versuchen → upgrade zu high_reasoning
    │
    ├─ complexity=architectural, risk=high|critical → high_reasoning (Opus)
    │   └─ Kein automatischer Upgrade — Gate 4 (Human-Only) wenn nötig
    │
    └─ risk=critical (immer) → Gate 2: Mensch bestätigt Tier
```

---

## Referenzen

- ADR-066: AI Engineering Squad — Rollen, Gates, Workflows
- ADR-067: Work Management — Issues, Projects, AI-Agent-Protokoll
- ADR-068: Adaptive Model Routing — Routing-Matrix, Quality Metrics
- Template: `.windsurf/templates/ai-task.yaml`
