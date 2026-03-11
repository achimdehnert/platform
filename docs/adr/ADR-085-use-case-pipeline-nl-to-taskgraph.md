---
status: accepted
date: 2026-02-25
implemented: 2026-02-25
decision-makers: Achim Dehnert
consulted: –
informed: –
supersedes: –
amends: –
related: ADR-080, ADR-082, ADR-084, ADR-066
implementation_status: partial
implementation_evidence:
  - "mcp-hub/orchestrator_mcp/: basic task pipeline, NL-to-TaskGraph pending"
---

# ADR-085: Use Case Pipeline — Natural Language → Structured TaskGraph

| Attribut       | Wert                                                                 |
|----------------|----------------------------------------------------------------------|
| **Status**     | Accepted                                                             |
| **Scope**      | Platform-wide — AI Infrastructure / Agent Orchestration              |
| **Repo**       | platform / mcp-hub                                                   |
| **Erstellt**   | 2026-02-25                                                           |
| **Autor**      | Achim Dehnert                                                        |
| **Reviewer**   | –                                                                    |
| **Supersedes** | –                                                                    |
| **Amends**     | –                                                                    |
| **Relates to** | ADR-080 (Multi-Agent), ADR-082 (LLM-Tool), ADR-084 (Model Registry), ADR-066 (AI Squad) |

<!-- Drift-Detector-Felder
staleness_months: 6
drift_check_paths:
  - orchestrator_mcp/agent_team/use_case_pipeline.py
  - orchestrator_mcp/agent_team/use_case_decomposer.py
  - orchestrator_mcp/agent_team/planner.py
-->

---

## 1. Kontext und Problemstellung

Die bisherige Orchestrierungs-Pipeline (ADR-080) setzt voraus, dass ein `Task`-Objekt bereits vollständig strukturiert vorliegt — mit `type`, `complexity`, `risk_level`, `affected_paths` und `acceptance_criteria`. Für externe Systeme (bfagent, cad-hub, API-Aufrufe) ist diese Voraussetzung zu hoch: Benutzer oder Systeme haben lediglich einen **natürlichsprachigen Use Case** als Eingabe.

**Lücke:**
```
Use Case (Text)  →  ???  →  Task  →  Planner  →  TaskGraph  →  Workflow
                   fehlt
```

**Auswirkung:**
- bfagent-Nutzer können keine Aufgaben direkt beschreiben — müssen erst manuell `Task`-Objekte konstruieren
- cad-hub Issue-Triage hat keine automatische Zerlegung in Subtasks
- Keine Wiederverwendung der `Planner`-Logik aus ADR-080 für externe Systeme

---

## 2. Entscheidungstreiber

- **Nahtlose Integration**: Use Cases aus bfagent, cad-hub und API direkt verarbeitbar
- **ADR-084-Konformität**: Keine hardcodierten Modell-Namen — Auflösung via `ModelRegistry`
- **ADR-080-Kompatibilität**: Bestehender `Planner` wird wiederverwendet, nicht ersetzt
- **Fallback-Sicherheit**: Kein LLM verfügbar → 1 generischer Task als Fallback
- **Testbarkeit**: Jede Stufe einzeln testbar und mockbar
- **ADR-075-Konformität**: Write-Ops via GitHub Actions, MCP liest nur

---

## 3. Betrachtete Optionen

### Option A: Direktes LLM-Prompting pro Anfrage (abgelehnt)
- Kein Caching, keine Tier-Auflösung, keine Fehlertoleranz
- Kein Fallback bei LLM-Ausfall
- Kopplung von Prompt-Engineering und Orchestrierung

### Option B: Regelbasierter Use-Case-Parser (abgelehnt)
- Keyword-Matching für `TaskType` + `complexity` nicht ausreichend präzise
- Keine Erfassung von `affected_paths` oder `acceptance_criteria` aus Freitext
- Kurzfristig einfacher, langfristig nicht wartbar

### Option C: Zweistufige Pipeline mit LLM-Decomposer + Planner ✅ (gewählt)
- `UseCaseDecomposer`: LLM (premium tier via ModelRegistry) → strukturierte `TaskSpec`-Liste
- `Planner.decompose()`: je `Task` → `TaskGraph` (bewährte ADR-080-Logik)
- Klare Trennung der Verantwortlichkeiten, beide Stufen einzeln testbar
- Fallback auf jeder Stufe

---

## 4. Entscheidung

**Zweistufige `UseCasePipeline`** als offizielles Platform-Pattern:

```
UseCasePipeline.run(use_case, context)
    │
    ▼
UseCaseDecomposer.decompose_async()   [LLM: premium tier via ModelRegistry]
    │  JSON-Parsing + Fehlertoleranz
    ▼
list[Task]                            [type, complexity, risk, paths, criteria]
    │
    ▼  (pro Task)
Planner.decompose(task)               [rule-based, ADR-080]
    │
    ▼
list[TaskGraph]                       [Branches, SubTasks, Roles, GateLevels]
    │
    ▼
PipelineResult                        [summary() + to_dict()]
```

### 4.1 Komponenten

| Komponente | Datei | Verantwortung |
|------------|-------|---------------|
| `UseCaseDecomposer` | `orchestrator_mcp/agent_team/use_case_decomposer.py` | NL → `list[Task]` via LLM |
| `Planner` | `orchestrator_mcp/agent_team/planner.py` | `Task` → `TaskGraph` (ADR-080) |
| `UseCasePipeline` | `orchestrator_mcp/agent_team/use_case_pipeline.py` | Orchestrierung beider Stufen |
| `PipelineResult` | `orchestrator_mcp/agent_team/use_case_pipeline.py` | Ergebnis-Aggregation + Serialisierung |
| MCP-Tool `run_use_case_pipeline` | `orchestrator_mcp/server.py` | Externe Nutzung via MCP |
| MCP-Tool `decompose_use_case` | `orchestrator_mcp/server.py` | Nur Decomposition (ohne Planner) |

### 4.2 Modell-Auflösung (ADR-084)

```python
# Kein hardcoded Modell-Name
decomposer = UseCaseDecomposer(tier="premium")
# → get_registry().get_model("premium") → aktuell: claude-opus-4-5-20250514
```

Tier-Wahl nach Anwendungsfall:

| Kontext | Empfohlener Tier | Begründung |
|---------|-----------------|------------|
| Architektur-/ADR-Tasks | `premium` | Maximale Decompositions-Qualität |
| Feature-Tickets (bfagent) | `standard` | Gutes Kosten/Qualitäts-Verhältnis |
| Issue-Triage (cad-hub) | `budget` | Hohe Volumen, einfache Strukturierung |
| CI-Automatisierung | `local` | $0 für einfache Regelaufgaben |

### 4.3 Fallback-Hierarchie

```
LLM verfügbar + valid JSON   →  vollständige Task-Liste
LLM verfügbar + invalid JSON →  1 generischer Task + DeprecationWarning
LLM nicht verfügbar          →  1 generischer Task (type=FEATURE, complexity=MODERATE)
Planner-Exception            →  TaskGraph.single_branch(task)
```

Kein Call schlägt je mit einer unkontrollierten Exception fehl.

### 4.4 Interaktiver Klärungsprozess (optional)

```python
# Stufe 1: Klärungsfragen (vor Decomposition)
questions = await pipeline.get_clarifying_questions(use_case)
# ["What auth provider?", "OAuth2 or JWT only?", "Token expiry requirement?"]

# Stufe 2: Decomposition mit verfeinerten Antworten
result = await pipeline.run(use_case, context=answers_as_context)
```

### 4.5 Nutzung in bfagent und cad-hub

**bfagent (Issue → Pipeline):**
```python
# bfagent/apps/bfagent/services/pipeline_service.py
from orchestrator_mcp.agent_team.use_case_pipeline import UseCasePipeline

pipeline = UseCasePipeline(tier="standard")
result = await pipeline.run(
    use_case=issue.title + "\n" + issue.body,
    context=f"Repo: bfagent, Stack: Django/Celery/PostgreSQL, ADRs: ADR-045, ADR-075",
)
# result.task_graphs → Basis für automatisches Issue-Labeling + Assignment
```

**cad-hub (Issue-Triage via MCP-Tool):**
```python
# MCP-Call aus cad-hub Automation:
{
  "tool": "run_use_case_pipeline",
  "arguments": {
    "use_case": "Add IFC-file upload with async processing",
    "context": "Stack: Django, Celery, S3. Existing: htmx.py, core/ module.",
    "tier": "standard",
    "output_format": "json"
  }
}
# → PipelineResult mit Branches, SubTasks, Rollen, Gate-Levels
```

---

## 5. Konsequenzen

### Positiv
- **Einheitlicher Einstiegspunkt** für alle Repos: 1 MCP-Call → vollständiger Ausführungsplan
- **ADR-080/084-Kompatibilität**: Kein Code gebrochen, alles additiv
- **Testbar auf jeder Stufe**: 56 Tests (27 Decomposer + 21 Pipeline + 8 Integration)
- **Tier-Flexibilität**: bfagent kann `standard` nutzen, cad-hub `budget` für Triage-Volumen

### Negativ / Risiken
- **LLM-Latenz**: Premium-Modell braucht ~3-8s für Decomposition → nicht für Echtzeit-UX
  - Mitigation: `decompose_use_case` (ohne Planner) als leichtere Variante verfügbar
- **JSON-Parsing-Fehler**: LLM gibt manchmal Markdown statt reines JSON
  - Mitigation: Robustes Multi-Strategy-Parsing + Fallback bereits implementiert
- **Tier-Kosten bei hohem Volumen**: Premium für jede Triage = teuer
  - Mitigation: `tier="budget"` für automatische Triage, `tier="premium"` nur für Architektur-Tasks

### Neutral
- `Planner` bleibt unverändert (ADR-080) — reine Erweiterung durch vorgelagerte Stufe
- `UseCaseDecomposer` und `UseCasePipeline` sind eigenständig nutzbar

---

## 6. Implementierungsstatus

| Komponente | Status | Commit |
|------------|--------|--------|
| `UseCaseDecomposer` | 🟢 implementiert | `2721bd6` |
| `UseCasePipeline` | 🟢 implementiert | `922ab26` |
| MCP-Tool `decompose_use_case` | 🟢 implementiert | `2721bd6` |
| MCP-Tool `run_use_case_pipeline` | 🟢 implementiert | `922ab26` |
| Tests (56 total) | 🟢 293 passed | `922ab26` |
| bfagent Integration | 🔴 offen | — |
| cad-hub Integration | 🔴 offen | — |

---

## 7. Integration Roadmap

### Phase 1 — bfagent (nächste Session)
- `bfagent/apps/bfagent/services/pipeline_service.py` — Wrapper für MCP-Call
- GitHub Issue → `use_case` → `PipelineResult` → Label-Vorschläge + Assignment
- Tier: `standard` (Kosten/Qualitäts-Balance)

### Phase 2 — cad-hub (nächste Session)
- cad-hub Issue-Triage Automation via `run_use_case_pipeline`
- IFC-Upload-Tasks als Use Cases formulieren → automatische Subtask-Erzeugung
- Tier: `budget` für Triage-Volumen

### Phase 3 — Feedback-Loop (zukünftig)
- `PipelineResult` → Workflow-Ausführung → Ergebnis → Registry-Update
- Composite-Score der Modelle anhand realer Decompositions-Qualität kalibrieren

---

## 8. Offene Fragen

| Frage | Priorität | Antwort |
|-------|-----------|---------|
| Sollen Clarifying Questions in bfagent interaktiv (Slack-Bot) oder automatisch beantwortet werden? | Mittel | Offen |
| Maximale Task-Anzahl pro Use Case (aktuell: 8) — ausreichend für cad-hub? | Niedrig | Beobachten |
| Caching von Decompositions-Ergebnissen für identische Use Cases? | Niedrig | Phase 3 |
