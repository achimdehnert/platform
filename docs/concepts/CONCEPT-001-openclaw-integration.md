---
title: "OpenCLAW Integration in AI Engineering Squad (ADR-066/067/068)"
id: "CONCEPT-001"
status: "review"
date: 2026-02-23
revised: 2026-02-23
author: [Achim Dehnert]
related_adrs:
  - ADR-066-ai-engineering-team.md
  - ADR-067-deployment-execution-strategy.md
  - ADR-068-adaptive-model-routing.md
tags: [openclaw, ai-agents, orchestration, multi-agent, adr-066, adr-068, make-or-buy]
---

# OpenCLAW Integration in AI Engineering Squad (ADR-066/067/068)

> **Zweck**: Make-or-Buy Analyse: OpenCLAW Szenario A (Framework-Integration) vs.
> Eigenimplementierung mit OpenCLAW-Prinzipien. Basis ist der tatsächliche
> Implementierungsstand von `orchestrator_mcp/agent_team/` (mcp-hub).

---

## 1. Executive Summary

Nach gründlicher Analyse des tatsächlichen Implementierungsstands in
`orchestrator_mcp/agent_team/` wird **Szenario A (OpenCLAW als Execution-Layer)
verworfen**. Die Empfehlung lautet: **Eigenimplementierung der fehlenden Komponenten
unter Übernahme der OpenCLAW-Prinzipien**.

**Begründung in einem Satz**: OpenCLAW würde ~80 Zeilen Boilerplate sparen, aber
~400 Zeilen bereits funktionierenden Code erfordern, eine externe Abhängigkeit
mit unklarer API-Stabilität einführen und das bestehende Gate-System neu integrieren
müssen — bei einem Netto-Nutzen nahe null.

**Fehlende Komponenten** (`developer.py`, `evaluator.py`, `router.py`, `metrics.py`)
werden eigenständig mit `litellm` + Pydantic v2 implementiert. Die OpenCLAW-Prinzipien
(Anti-Bias-Evaluation, Structured Outputs, Retry-Chain, explizite Workflows) werden
direkt übernommen — ohne Framework-Abhängigkeit.

---

## 2. Tatsächlicher Implementierungsstand (Stand 2026-02-23)

> **Kritische Erkenntnis**: Das initiale Konzeptpapier (v1) ging von "Phase 1
> (Datenmodell)" aus. Die tatsächliche Implementierung ist deutlich weiter.

### 2.1 Bereits vollständig implementiert

| Datei | Inhalt | Vollständigkeit |
|-------|--------|----------------|
| `agent_team/models.py` | `EngineeringTask`, `TaskPlan`, `WorkflowExecution`, `ImpactReport`, `TestGapReport` — alle Pydantic v2 | ✅ vollständig |
| `agent_team/workflows.py` | `create_workflow()`, `advance_workflow()`, `request_changes()` — Iteration-Counter, Eskalation | ✅ vollständig |
| `agent_team/tech_lead.py` | `parse_adr()`, `create_task_plan()`, `review_task()` | ✅ vollständig |
| `agent_team/tester.py` | `run_test_suite()`, `analyze_test_gaps()` — async pytest-Runner mit Regex-Parsing | ✅ vollständig |
| `agent_team/guardian.py` | Ruff/Bandit/MyPy Quality Gate | ✅ vollständig |
| `agent_team/config.py` | Tier-Mapping, Gate-Definitionen, Coverage-Targets | ✅ vollständig |
| `orchestrator_mcp/audit_store.py` | PostgreSQL + In-Memory-Fallback, vollständiges Schema inkl. `cost_usd` | ✅ vollständig |

### 2.2 Fehlende Komponenten (tatsächliche Lücken)

| Datei | Funktion | ADR-Referenz |
|-------|----------|-------------|
| `agent_team/developer.py` | LLM-basierte Code-Generierung / Koordinations-Wrapper | ADR-066 Phase 4 |
| `agent_team/evaluator.py` | QualityEvaluator (Evaluator ≠ Executor) | ADR-068 Phase 4 |
| `agent_team/router.py` | TaskRouter — Tier-Zuweisung per Task-Typ | ADR-068 Phase 2 |
| `agent_team/metrics.py` | `TaskQualityScore`, Feedback-Loop, Routing-Matrix-Update | ADR-068 Phase 3 |
| `agent_team/utils.py` | `llm_call_with_retry()`, FALLBACK_CHAIN | ADR-068 Phase 2 |

---

## 3. Make-or-Buy Analyse: OpenCLAW vs. Eigenimplementierung

### 3.1 Was OpenCLAW tatsächlich lösen würde

| OpenCLAW-Komponente | Theoretischer Nutzen | Tatsächlicher Nutzen nach Ist-Analyse |
|--------------------|---------------------|--------------------------------------|
| `CLAWAgent` für `tester.py` | Structured Outputs, Retry | **KEIN** — `tester.py` ist kein LLM-Agent, ruft `pytest` als Subprocess auf |
| `CLAWWorkflow` für `workflows.py` | Sequentielle Step-Chains | **KEIN** — `workflows.py` ist bereits vollständig implementiert |
| `CLAWEval` für `evaluator.py` | Anti-Bias-Evaluation | **GERING** — `litellm.acompletion()` + Pydantic v2 reicht (~80 Zeilen) |
| `CLAWTrace` für `audit_store.py` | Token-Kosten-Tracking | **KEIN** — `audit_store.py` existiert bereits mit `cost_usd`-Feld |
| `CLAWRetry` für alle Agenten | Exponential Backoff | **GERING** — ~15 Zeilen `utils.py` mit `litellm` |
| `CLAWAgent` für `developer.py` | LLM-Execution-Layer | **FRAGLICH** — Developer-Agent ist Cascade selbst, kein autonomer LLM-Caller |

### 3.2 Kosten der OpenCLAW-Integration

| Kostenfaktor | Beschreibung | Aufwand |
|-------------|-------------|---------|
| Umschreiben funktionierenden Codes | `tester.py`, `workflows.py` müssten auf CLAWAgent/CLAWWorkflow umgestellt werden | ~400 Zeilen |
| Gate-System-Integration | Kein OpenCLAW-Äquivalent — muss als Wrapper um CLAWWorkflow gebaut werden | ~100 Zeilen |
| Neue externe Abhängigkeit | OpenCLAW < 1 Jahr alt, API-Stabilität unklar | Risiko: HOCH |
| Debugging-Komplexität | Framework-Layer zwischen eigenem Code und LLM-API | Dauerhaft |
| Lernaufwand | OpenCLAW-Dokumentation, Patterns, Breaking Changes verfolgen | 1–2 Tage + laufend |

### 3.3 Kosten der Eigenimplementierung

| Fehlende Komponente | Ansatz | Aufwand |
|--------------------|--------|---------|
| `utils.py` — `llm_call_with_retry()` | `litellm` + `asyncio.sleep(2**attempt)` | ~20 Zeilen |
| `router.py` — TaskRouter | Heuristische Matrix + optionaler Budget-LLM-Call | ~120 Zeilen |
| `evaluator.py` — QualityEvaluator | `litellm.acompletion()` + Pydantic v2 + Anti-Bias-Assertion | ~80 Zeilen |
| `metrics.py` — Feedback-Loop | `TaskQualityScore` Dataclass + `update_routing_matrix()` | ~100 Zeilen |
| `developer.py` — Koordinations-Wrapper | Workflow-Koordination + optionaler LLM-Call für autonome Tasks | ~100 Zeilen |
| **Gesamt** | | **~420 Zeilen, 0 neue Abhängigkeiten** |

### 3.4 Direkter Vergleich

| Aspekt | OpenCLAW Szenario A | Eigenimplementierung |
|--------|--------------------|--------------------|
| Neue externe Abhängigkeit | Ja — junges Framework | Nein — nur `litellm` (bereits vorhanden) |
| Bereits vorhandener Code | Muss umgeschrieben werden | Bleibt unverändert |
| Netto-Boilerplate-Ersparnis | ~80 Zeilen | — |
| Zusätzlicher Umbau-Aufwand | ~500 Zeilen | — |
| Risiko API-Breaking-Change | HOCH | KEINE |
| Gate-System-Kompatibilität | Muss nachgebaut werden | Bereits implementiert |
| `litellm` bereits vorhanden? | Ja (chat-logging, travel-beat) | Ja |
| Debugging-Komplexität | Framework-Layer | Direkter Stack-Trace |
| Volle Kontrolle über Verhalten | Nein | Ja |

---

## 4. Übernommene OpenCLAW-Prinzipien (ohne Framework)

Die wertvollen Ideen aus OpenCLAW werden direkt in die Eigenimplementierung übernommen:

### Prinzip 1: Evaluator ≠ Executor (Anti-Bias)
```python
# evaluator.py — erzwungen durch Assertion:
def evaluate_task(task_result, executor_model: str) -> TaskQualityScore:
    evaluator_model = FALLBACK_CHAIN[executor_model]  # immer anderes Modell
    assert evaluator_model != executor_model, "Anti-bias: evaluator must differ"
```

### Prinzip 2: Structured Outputs immer via Pydantic v2
```python
# Bereits in models.py — konsequent fortführen:
response = await litellm.acompletion(
    model=evaluator_model,
    messages=[...],
    response_format=TaskQualityScore,  # litellm unterstützt das nativ
)
```

### Prinzip 3: Retry mit expliziter Fallback-Chain
```python
# utils.py — einmal schreiben, überall nutzen:
FALLBACK_CHAIN = {
    "lean_local": "budget_cloud",
    "budget_cloud": "standard_coding",
    "standard_coding": "high_reasoning",
}

async def llm_call_with_retry(model, messages, schema, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await litellm.acompletion(model=model, messages=messages,
                                              response_format=schema)
        except (RateLimitError, APIError):
            if attempt == max_retries - 1:
                fallback = FALLBACK_CHAIN.get(model)
                if fallback:
                    return await llm_call_with_retry(fallback, messages, schema)
                raise
            await asyncio.sleep(2 ** attempt)
```

### Prinzip 4: Jeder LLM-Step loggt Token-Kosten
```python
# AuditStore bereits vorhanden — cost_usd Feld bereits im Schema:
cost = response.usage.total_tokens * COST_PER_TOKEN[model]
audit_store.log({"task_id": task_id, "cost_usd": cost, "model": model, ...})
```

### Prinzip 5: Workflows sind explizit, nicht emergent
```python
# workflows.py bereits so implementiert — konsequent beibehalten.
# KEIN dynamisches Agent-Spawning, KEINE emergenten Chains.
```

---

## 5. Revidierte Bewertungsmatrix

> Bewertung nach Kenntnis des tatsächlichen Implementierungsstands.

| Kriterium | Gewicht | A (OpenCLAW) | E (Eigenimpl.) | C (Vollst. OpenCLAW) | D (Nichts tun) |
|-----------|---------|-------------|----------------|---------------------|----------------|
| Technischer Nutzen | 30% | 0.3 | 0.9 | 0.5 | 0.0 |
| Implementierungsaufwand | 25% | 0.2 | 0.9 | 0.1 | 1.0 |
| Wartbarkeit | 20% | 0.5 | 0.9 | 0.3 | 0.7 |
| Risiko (invertiert) | 15% | 0.4 | 1.0 | 0.2 | 0.8 |
| Strategische Passung | 10% | 0.6 | 0.9 | 0.5 | 0.1 |
| **Gesamt** | 100% | **0.39** | **0.92** | **0.32** | **0.54** |

> Szenario A fällt von 0.76 (v1, ohne Kenntnis des Ist-Stands) auf **0.39** (v2, nach Ist-Analyse).
> Eigenimplementierung gewinnt klar mit **0.92**.

---

## 6. Empfehlung

### 6.1 Entscheidung: Eigenimplementierung mit OpenCLAW-Prinzipien

OpenCLAW wird **nicht integriert**. Die fehlenden Komponenten werden eigenständig
mit `litellm` + Pydantic v2 implementiert. Die OpenCLAW-Prinzipien (Anti-Bias,
Structured Outputs, Retry-Chain, explizite Workflows) werden direkt übernommen.

### 6.2 Implementierungsplan

| Komponente | Datei | Priorität | Aufwand | ADR-Phase |
|-----------|-------|-----------|---------|-----------|
| Retry-Utility + FALLBACK_CHAIN | `agent_team/utils.py` | HIGH | ~20 Zeilen | ADR-068 Phase 2 |
| TaskRouter (heuristisch) | `agent_team/router.py` | HIGH | ~120 Zeilen | ADR-068 Phase 2 |
| QualityEvaluator | `agent_team/evaluator.py` | HIGH | ~80 Zeilen | ADR-068 Phase 4 |
| TaskQualityScore + Feedback-Loop | `agent_team/metrics.py` | MEDIUM | ~100 Zeilen | ADR-068 Phase 3 |
| Developer-Koordinations-Wrapper | `agent_team/developer.py` | MEDIUM | ~100 Zeilen | ADR-066 Phase 4 |

**Reihenfolge**: `utils.py` → `router.py` → `evaluator.py` → `metrics.py` → `developer.py`

### 6.3 ADR-Kandidaten

- [ ] **ADR-069**: Eigenimplementierung der ADR-068-Komponenten mit OpenCLAW-Prinzipien
  *(ersetzt den ursprünglichen ADR-069-Kandidaten "OpenCLAW als Execution-Layer")*

---

## 7. Offene Fragen

| Frage | Priorität | Wer klärt es? |
|-------|-----------|---------------|
| Ist `developer.py` ein autonomer LLM-Caller oder rein ein Koordinations-Wrapper für Cascade? | HIGH | Achim Dehnert — architektonische Entscheidung |
| Welches Budget-Modell für `router.py` (heuristisch vs. LLM-basiert)? | MEDIUM | ADR-068 Phase 2 |
| Soll `metrics.py` die Routing-Matrix persistent in PostgreSQL speichern? | MEDIUM | ADR-068 Phase 3 |

---

## 8. Referenzen

- [ADR-066: AI Engineering Squad](../adr/ADR-066-ai-engineering-team.md)
- [ADR-067: Deployment Execution Strategy](../adr/ADR-067-deployment-execution-strategy.md)
- [ADR-068: Adaptive Model Routing](../adr/ADR-068-adaptive-model-routing.md)
- [orchestrator_mcp/agent_team/](https://github.com/achimdehnert/mcp-hub/tree/main/orchestrator_mcp/agent_team)
- [Concept Paper Template](../templates/concept-paper-template.md)

---

## Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-02-23 | Achim Dehnert | Initial Draft (v1) — Szenario A empfohlen |
| 2026-02-23 | Achim Dehnert | v2 — Make-or-Buy Analyse nach Ist-Stand-Prüfung; Empfehlung revidiert auf Eigenimplementierung |
