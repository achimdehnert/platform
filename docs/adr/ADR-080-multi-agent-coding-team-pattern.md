---
status: proposed
date: 2026-02-24
decision-makers: Achim Dehnert
consulted: –
informed: –
supersedes: –
amends: ADR-066-ai-engineering-team.md
related: ADR-066, ADR-068, ADR-070, ADR-075
---

# ADR-080: Multi-Agent Coding Team Pattern — Handoff, Parallelisierung und Rollback

| Feld | Wert |
|------|------|
| **Status** | Proposed |
| **Datum** | 2026-02-24 |
| **Autor** | Achim Dehnert |
| **Amends** | ADR-066 (AI Engineering Squad) |
| **Related** | ADR-068 (Adaptive Model Routing), ADR-070 (Progressive Autonomy), ADR-075 (Deployment Execution) |

---

## 1. Kontext und Problem

ADR-066 definiert ein AI Engineering Squad mit 5 Rollen (Tech Lead, Developer, Tester,
Re-Engineer, Guardian). ADR-068 fügt adaptives Model Routing hinzu. ADR-070 ergänzt
Progressive Autonomy für den Developer.

**Drei kritische Lücken bleiben ungelöst:**

### Lücke 1: Kein formales Handoff-Protokoll

Wenn Developer → Re-Engineer → Tech Lead wechselt, gibt es kein definiertes
Übergabe-Format. Der nächste Agent startet ohne strukturierten Kontext:
- Welche Änderungen wurden gemacht?
- Welche Acceptance Criteria sind erfüllt / offen?
- Welche Entscheidungen wurden getroffen und warum?

Das führt zu redundanter Analyse, Kontext-Verlust und inkonsistenter Qualität.

### Lücke 2: Keine Parallelisierung

Der `agentic-coding.md` Workflow ist vollständig sequentiell:
```
Task → Router → Rolle → Guardian → Tests → Evaluator → PR → AuditStore
```

Mehrere unabhängige Sub-Tasks (z.B. Feature + zugehörige Tests) werden sequentiell
bearbeitet, obwohl sie parallel ausführbar wären.

### Lücke 3: Keine Rollback-Strategie

Bei gescheitertem Task (Score < 0.70, Guardian-Fail, ungelöste Konflikte) gibt es
keinen definierten Eskalations- und Rollback-Pfad. Der Workflow endet im Nichts.

---

## 2. Decision Drivers

- **Kontext-Kontinuität**: Handoff zwischen Agenten ohne Kontext-Verlust
- **Durchsatz**: Parallele Sub-Tasks reduzieren Gesamtdurchlaufzeit
- **Resilienz**: Gescheiterte Tasks haben definierten Recovery-Pfad
- **Auditierbarkeit**: Jeder Handoff ist im AuditStore nachvollziehbar
- **Kompatibilität**: Aufbauend auf ADR-066/068/070 — kein Refactor der Basis

---

## 3. Considered Options

### Option A — Strukturiertes Handoff-Objekt + Sequentiell (gewählt als Basis)

Jeder Agenten-Übergang übergibt ein `AgentHandoff`-Objekt (Pydantic v2) mit
vollständigem Kontext. Sequentielle Ausführung bleibt Standard.

**Pro:**
- Minimale Änderung an bestehender Infrastruktur
- Handoff-Objekt ist direkt auditierbar
- Sofort implementierbar

**Con:**
- Keine Parallelisierung (separates Opt-in nötig)

### Option B — Task-Graph mit parallelen Branches (erweitert Option A)

Planner-Agent zerlegt komplexe Tasks in einen DAG. Unabhängige Branches laufen
parallel. Ergebnisse werden durch Merge-Agent zusammengeführt.

**Pro:**
- Deutlich höherer Durchsatz bei komplexen Tasks
- Natürliche Strukturierung von Feature + Test als parallele Branches

**Con:**
- Höhere Implementierungskomplexität
- Merge-Konflikte müssen explizit behandelt werden

### Option C — Vollautonomes Crew-AI-artiges System

Externe Bibliothek (CrewAI, AutoGen) für Multi-Agent-Koordination.

**Con:**
- Externes Framework-Dependency widerspricht Platform-Philosophie (ADR-073: kein Vendor-Lock)
- Kein Control über MCP-Integration und AuditStore
- **Verworfen**

---

## 4. Entscheidung

**Option A + B (kombiniert):** Strukturiertes Handoff-Protokoll als Fundament,
parallele Task-Branches als Opt-in für komplexe Tasks.

Der **Planner** ist eine neue, eigenständige Agenten-Rolle (ergänzt ADR-066).

---

## 5. Architektur: Multi-Agent Coding Team Pattern

### 5.1 Rollen-Erweiterung (amends ADR-066)

```
ADR-066 Rollen (unverändert):
  Tech Lead    — Architektur, ADR-Review, Gate 3
  Developer    — Code-Implementierung, Gate 1–2
  Tester       — Test-Erstellung und -Ausführung, Gate 0–1
  Re-Engineer  — Refactoring, Tech-Debt, Gate 2
  Guardian     — Statisches Quality Gate (Ruff, Bandit, MyPy)

NEU (ADR-080):
  Planner      — Task-Zerlegung in Sub-Tasks + DAG, Gate 2
  Merger       — Zusammenführung paralleler Branches, Gate 1
```

### 5.2 Handoff-Protokoll

Jeder Agenten-Übergang produziert und konsumiert ein `AgentHandoff`-Objekt:

```python
class AgentHandoff(BaseModel):
    """Strukturierter Kontext-Transfer zwischen Agenten (ADR-080)."""

    # Identität
    handoff_id: str               # UUID
    task_id: str                  # Referenz auf Task (ADR-066)
    from_agent: AgentRole         # Sendender Agent
    to_agent: AgentRole           # Empfangender Agent
    timestamp: datetime

    # Ergebnis des sendenden Agenten
    artifacts_produced: list[Artifact]   # Code, Tests, ADR, Config, ...
    criteria_fulfilled: list[str]        # Erfüllte Acceptance Criteria
    criteria_open: list[str]             # Noch offene Acceptance Criteria
    decisions_made: list[Decision]       # Getroffene Entscheidungen + Begründung

    # Kontext für empfangenden Agenten
    context_summary: str          # ≤ 500 Zeichen: Was wurde gemacht, warum?
    blocking_issues: list[str]    # Blockierende Probleme (leer = kein Block)
    suggested_next_steps: list[str]

    # Quality-Snapshot
    quality_score: float          # 0.0–1.0
    guardian_passed: bool
    coverage_delta: float | None

    # Gate-Steuerung
    requires_human_review: bool   # True → Gate 2+ aktivieren
    escalation_reason: str | None
```

### 5.3 Task-Graph (parallele Branches)

```
ComplexTask
    │
    ▼
Planner.decompose()
    │
    ├── Branch A: Developer (Feature-Code)    ──┐
    │                                           │
    ├── Branch B: Tester (Test-Suite)         ──┤ Merger.merge()
    │                                           │
    └── Branch C: Tech Lead (ADR-Update)     ──┘
                                                │
                                                ▼
                                        Guardian (merged result)
                                                │
                                                ▼
                                        Evaluator + AuditStore
```

**Regel:** Branch-Parallelisierung nur bei `complexity >= complex`. Für
`trivial/simple/moderate` bleibt der sequentielle Pfad.

### 5.4 Rollback-Strategie

```
Rollback-Trigger:
  - quality_score < 0.70 nach max_iteration_count
  - Guardian-Fail nach 2 Retry-Versuchen
  - blocking_issues nicht leer nach Re-Engineer-Pass
  - Merge-Konflikt nicht auflösbar

Rollback-Pfad (Eskalations-Leiter):
  Level 1: Re-Engineer (automatisch, Gate 0)
    → Refactor + Retry (max. 1×)
  Level 2: Tech Lead Review (Gate 2)
    → Architektur-Entscheidung + neuer Plan
  Level 3: Human-in-the-Loop (Gate 3)
    → User-Benachrichtigung mit Kontext-Summary + Handoff-Objekt
  Level 4: Task-Abort (Gate 4)
    → AuditStore: status=aborted, reason=..., last_handoff_id=...
    → GitHub Issue: Kommentar mit Rollback-Report
```

### 5.5 Planner-Logik

```python
class Planner:
    """Zerlegt komplexe Tasks in parallelisierbare Sub-Tasks (ADR-080)."""

    def decompose(self, task: Task) -> TaskGraph:
        """
        Nur für complexity >= complex.
        Einfachere Tasks bypassen den Planner direkt.
        """
        if task.complexity < TaskComplexity.COMPLEX:
            return TaskGraph.single_branch(task)

        # LLM-gestützte Zerlegung (Budget-Tier)
        sub_tasks = self._llm_decompose(task)
        dependencies = self._analyze_dependencies(sub_tasks)
        return TaskGraph(sub_tasks=sub_tasks, dependencies=dependencies)

    def _analyze_dependencies(self, sub_tasks: list[Task]) -> dict[str, list[str]]:
        """Bestimmt welche Sub-Tasks parallel laufen können."""
        # Sub-Tasks ohne gemeinsame affected_paths → parallel
        # Sub-Tasks mit shared paths → sequentiell
        ...
```

---

## 6. Erweiterter Workflow (amends agentic-coding.md)

```
MULTI-AGENT CODING WORKFLOW v2 (ADR-080)

Step 0: Governance Check
  → /governance-check vor jedem nicht-trivialen Task
  → Blockiert bei ADR-Verletzung

Step 1: Task-Template ausfüllen (ai-task.yaml)
  → Pflichtfeld: complexity, risk_level, acceptance_criteria

Step 2: Planner (neu — nur bei complexity >= complex)
  → decompose(task) → TaskGraph
  → Einfache Tasks: Planner bypassed

Step 3: TaskRouter (ADR-068)
  → Modell-Tier pro Branch bestimmen
  → Confidence < 0.7 → Gate 2

Step 4: Parallele Ausführung (bei TaskGraph mit Branches)
  → Developer-Branch + Tester-Branch (parallel wenn unabhängig)
  → Jeder Branch produziert AgentHandoff

Step 5: Merger (bei parallelen Branches)
  → Zusammenführen der Branch-Ergebnisse
  → Merge-Konflikte → Level 2 Rollback

Step 6: Guardian (immer, nach Merge)
  → Ruff + Bandit + MyPy auf merged Result
  → Fail → Level 1 Rollback (Re-Engineer)

Step 7: Quality Evaluator (ADR-068)
  → composite_score berechnen
  → Score < 0.70 → Rollback-Leiter

Step 8: PR erstellen + AgentHandoff als PR-Body
  → Branch: ai/{agent-role}/{task-id}
  → PR-Body aus handoff.context_summary generiert

Step 9: AuditStore + GitHub Issue Update
  → Handoff-Objekt persistieren
  → Issue: Quality Score Kommentar
```

---

## 7. Implementierungsstruktur

```
orchestrator_mcp/agent_team/
  handoff.py          # AgentHandoff Pydantic-Model + Serialisierung (NEU)
  planner.py          # Task-Zerlegung + TaskGraph + Dependency-Analyse (NEU)
  merger.py           # Branch-Merge-Logik + Konflikt-Detection (NEU)
  rollback.py         # Rollback-Leiter Level 1–4 (NEU)
  developer.py        # Update: produziert/konsumiert AgentHandoff (UPDATE)
  evaluator.py        # Update: Score-Input aus Handoff (UPDATE)
  workflows.py        # Update: run_workflow() mit TaskGraph-Support (UPDATE)
```

**Implementierungsreihenfolge:**
1. `handoff.py` — Datenmodell, keine Abhängigkeiten
2. `rollback.py` — Abhängig von `handoff.py`
3. `planner.py` — Abhängig von `handoff.py`
4. `merger.py` — Abhängig von `handoff.py`, `planner.py`
5. Updates: `developer.py`, `evaluator.py`, `workflows.py`

---

## 8. Workflow-Update: agentic-coding.md

Der `agentic-coding.md` Workflow wird auf v2 gehoben:
- Step 0 (Governance Check) wird explizit vorangestellt
- Step 2 (Planner) wird zwischen Task-Template und Router eingefügt
- Steps 4–5 (parallele Ausführung + Merge) als optionaler Branch bei complexity >= complex
- Step 6 (Guardian) auf merged Result
- Rollback-Pfad nach Step 7 explizit dokumentiert
- PR-Body wird aus `AgentHandoff.context_summary` automatisch generiert

---

## 9. Kompatibilität mit bestehenden ADRs

| ADR | Impact |
|-----|--------|
| ADR-066 | Ergänzt: Planner + Merger als neue Rollen |
| ADR-068 | Kompatibel: Router läuft pro Branch im TaskGraph |
| ADR-070 | Kompatibel: Progressive Autonomy gilt pro Branch |
| ADR-075 | Kompatibel: Deployment bleibt GitHub Actions |
| ADR-067 | Ergänzt: AgentHandoff wird als Issue-Kommentar persistiert |

---

## 10. Konsequenzen

### Positiv
- **Kein Kontext-Verlust** bei Agenten-Übergaben (AgentHandoff)
- **Höherer Durchsatz** bei komplexen Tasks durch Parallelisierung
- **Definierter Recovery-Pfad** — kein "Task endet im Nichts"
- **Audit-Trail vollständig**: Jeder Handoff im AuditStore
- **Rückwärtskompatibel**: Einfache Tasks bypassen Planner + Merger

### Negativ / Risiken

| Risiko | Mitigation |
|--------|------------|
| Merge-Konflikte bei Parallelisierung | Konservativer Default: nur parallelisieren wenn affected_paths disjunkt |
| Planner-Overhead für einfache Tasks | Bypass-Bedingung: `complexity < complex` → kein Planner |
| AgentHandoff-Schema-Drift | Pydantic v2 — Schema-Version im Objekt |
| Rollback-Loop (L1 → L2 → L1) | Max 1 Re-Engineer-Retry pro Level |

---

## 11. Offene Fragen

| Frage | Empfehlung |
|-------|-----------|
| Soll Planner ein eigenes LLM-Modell nutzen oder Budget-Tier? | Budget-Tier (`budget_cloud`) — Zerlegung ist kein High-Reasoning-Task |
| Wie viele parallele Branches max? | `MAX_PARALLEL_BRANCHES = 3` als Config-Wert |
| AgentHandoff in DB oder nur im AuditStore? | AuditStore reicht für v1 — DB-Migration wenn Handoff-History gebraucht wird |

---

## 12. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-02-24 | Achim Dehnert | v1 — Initial Proposed; Handoff + Planner + Rollback-Architektur |
