---
title: "OpenCLAW Integration in AI Engineering Squad (ADR-066/067/068)"
id: "CONCEPT-001"
status: "draft"
date: 2026-02-23
author: [Achim Dehnert]
related_adrs:
  - ADR-066-ai-engineering-team.md
  - ADR-067-deployment-execution-strategy.md
  - ADR-068-adaptive-model-routing.md
tags: [openclaw, ai-agents, orchestration, multi-agent, adr-066, adr-068]
---

# OpenCLAW Integration in AI Engineering Squad (ADR-066/067/068)

> **Zweck**: Analyse ob und wie OpenCLAW (Open Cognitive LLM Agent Workflow) und seine
> Ergänzungen (CLAW-Eval, CLAW-Tools, CLAW-Trace, CLAW-Retry) in die bestehende
> AI-Engineering-Squad-Architektur (ADR-066), die Deployment-Strategie (ADR-067) und
> das Adaptive Model Routing (ADR-068) integriert werden können.

---

## 1. Executive Summary

OpenCLAW ist ein Open-Source Framework für strukturierte, auditierbare LLM-Workflows
mit nativem Multi-Agent-Support, Pydantic v2 Structured Outputs, Retry-Logik und
OpenTelemetry-Observability. Die Platform betreibt mit ADR-066/068 eine eigene
Agent-Team-Architektur in `orchestrator_mcp/agent_team/`, die konzeptuell mit OpenCLAW
überlappt — aber auf einer höheren Abstraktionsebene operiert.

**Kernaussage**: OpenCLAW ist kein Ersatz für die bestehende Architektur, sondern ein
potentieller **Execution-Layer** unterhalb der ADR-066-Rollen. Die höchste
Integrationstiefe liegt im `Developer`- und `Tester`-Agenten (ADR-066) sowie im
`QualityEvaluator` (ADR-068). Für ADR-067 (Deployment via GitHub Actions) ist
OpenCLAW nicht relevant. **Empfehlung: Szenario A** — selektive Integration als
Execution-Layer ab ADR-066 Phase 3.

---

## 2. Motivation und Problemkontext

### 2.1 Ausgangssituation

ADR-066 definiert 4 AI-Rollen + Guardian mit konkreter Implementierungsstruktur in
`orchestrator_mcp/agent_team/`. Die Implementierung befindet sich in Phase 1
(Datenmodell). Vor Phase 3 (Tester) und Phase 4 (Developer) stellt sich die Frage:
Soll der LLM-Execution-Layer selbst gebaut werden oder kann OpenCLAW als Basis dienen?

**Konkrete Lücken in der aktuellen ADR-066/068-Spezifikation:**

| Lücke | Betrifft | OpenCLAW-Lösung |
|-------|----------|------------------|
| Kein Tool-Calling-Protokoll definiert | ADR-066 Developer, TL | `CLAWTools` Registry |
| Keine Retry-Logik spezifiziert | ADR-066 alle Agenten | `CLAWRetry` Exponential Backoff |
| Kein Streaming für lange Tasks | ADR-066 Re-Engineer, TL | `CLAWAgent` Streaming |
| Observability nicht adressiert | ADR-068 AuditStore | `CLAWTrace` OpenTelemetry |
| QualityEvaluator: kein Framework | ADR-068 Phase 4 | `CLAWEval` |
| Token-Kosten-Tracking manuell | ADR-068 `cost_usd` | `CLAWTrace` Budget-Tracking |

### 2.2 Relevante bestehende ADRs

| ADR | Titel | Relevanz |
|-----|-------|----------|
| ADR-066 | AI Engineering Squad | **HOCH** — Rollen, Workflows, Execution-Layer |
| ADR-067 | Deployment Execution Strategy | **KEINE** — GitHub Actions, kein Agent-Framework |
| ADR-068 | Adaptive Model Routing | **HOCH** — QualityEvaluator, AuditStore, Fallback-Chain |
| ADR-044 | MCP-Hub Architecture | **MITTEL** — Ziel-Repo für `orchestrator_mcp` |

### 2.3 Nicht-Ziele

- OpenCLAW als Ersatz für `orchestrator_mcp` (zu invasiv)
- OpenCLAW für Deployment-Operationen (ADR-067 ist GitHub-Actions-basiert, kein Agent-Framework)
- Vollständige Evaluation aller Alternativen (LangChain, LlamaIndex, AutoGen, CrewAI)
- Produktions-Entscheidung in diesem Dokument → folgt als ADR-069 nach PoC

---

## 3. OpenCLAW Analyse

### 3.1 Überblick

OpenCLAW positioniert sich zwischen raw LLM-API-Calls (zu niedrig-level) und
vollständigen Frameworks wie LangChain (zu opinionated). Es ist **workflow-first**:
Workflows sind explizit definiert, nicht emergent. Lizenz: Apache 2.0.

**Kernprinzipien:**
- **Structured Outputs**: Pydantic v2 nativ, kein JSON-Parsing-Overhead
- **Auditierbar**: Jeder Step ist traceable (OpenTelemetry-kompatibel)
- **Modell-agnostisch**: Anthropic, OpenAI, Ollama, MiniMax
- **Retry-native**: Exponential Backoff, Fallback-Chains konfigurierbar
- **Composable**: Steps können sequentiell oder parallel kombiniert werden

**OpenCLAW-Ecosystem (relevante Ergänzungen):**

| Modul | Funktion | Relevanz |
|-------|----------|----------|
| **CLAW-Eval** | LLM-basierte Output-Evaluation (Evaluator ≠ Executor) | **HOCH** — ADR-068 QualityEvaluator |
| **CLAW-Tools** | Tool-Registry mit Schema-Validation | **HOCH** — ADR-066 Developer/TL |
| **CLAW-Trace** | OpenTelemetry Tracing + Budget-Tracking | **HOCH** — ADR-068 AuditStore |
| **CLAW-Retry** | Strukturierte Retry-Logik + Fallback-Chains | **HOCH** — ADR-068 FALLBACK_CHAIN |

### 3.2 Kernfähigkeiten und Relevanz

| Fähigkeit | Beschreibung | Relevanz für Platform |
|-----------|-------------|----------------------|
| `CLAWAgent` | LLM-Agent mit Pydantic v2 Output | **HOCH** — ADR-066 Developer, Tester |
| `CLAWWorkflow` | Sequentielle + parallele Step-Chains | **HOCH** — ADR-066 Workflow A/B/C |
| `CLAWEval` | Evaluation: Evaluator ≠ Executor (Bias-Vermeidung) | **HOCH** — ADR-068 Phase 4 |
| `CLAWRetry` | Exponential Backoff + Tier-Fallback | **HOCH** — ADR-068 FALLBACK_CHAIN |
| `CLAWTrace` | Span/Trace pro Step, Token-Kosten | **MITTEL** — ADR-068 cost_usd |
| Streaming | Token-Streaming für lange Tasks | **MITTEL** — Re-Engineer, TL |
| Budget-Tracking | Token-Kosten pro Step und Workflow | **HOCH** — ADR-068 TaskQualityScore |

### 3.3 Mapping: OpenCLAW → ADR-066/068 Konzepte

| ADR-066/068 Konzept | OpenCLAW Äquivalent | Überlappung |
|--------------------|--------------------|--------------|
| `AgentRole` (TL, Dev, Tester, RE) | `CLAWAgent` mit Role-Config | **DIREKT** |
| `TaskPlan` (Pydantic v2) | `CLAWOutput[TaskPlan]` | **DIREKT** |
| Workflow A/B/C (Sequenz) | `CLAWWorkflow(steps=[...])` | **DIREKT** |
| `FALLBACK_CHAIN` (ADR-068) | `CLAWRetry(fallback_model=...)` | **DIREKT** |
| `QualityEvaluator` (ADR-068) | `CLAWEval(evaluator=budget_model)` | **DIREKT** |
| `AuditStore` (ADR-068) | `CLAWTrace` → PostgreSQL Exporter | **INDIREKT** |
| `Guardian` (regelbasiert) | Kein Äquivalent — bleibt eigenständig | **KEIN** |
| `TaskRouter` (ADR-068) | `CLAWRouter` (experimentell) | **TEILWEISE** |
| Gate-System (0–4) | Kein natives Äquivalent | **KEIN** |

### 3.4 Einschränkungen und Risiken

| Einschränkung | Schwere | Mitigation |
|---------------|---------|------------|
| OpenCLAW jung (< 1 Jahr) — API-Stabilität unklar | MEDIUM | Wrapper-Layer; kein direkter Import in Business-Logic |
| Gate-System (ADR-066 Gate 0–4) hat kein Äquivalent | MEDIUM | Gate-System bleibt eigenständig in `workflows.py` |
| `CLAWRouter` experimentell — nicht production-ready | HIGH | Nur `CLAWAgent` + `CLAWWorkflow` verwenden; Router selbst bauen |
| Vendor-Abhängigkeit | MEDIUM | Abstraktion via `agent_team/` Interface; OpenCLAW nur im Execution-Layer |
| Lizenz: Apache 2.0 | NIEDRIG | Kompatibel mit Platform-Anforderungen |

---

## 4. Integrations-Szenarien

### Szenario A — Execution-Layer für Developer + Tester + QualityEvaluator (Empfohlen)

`CLAWAgent` + `CLAWWorkflow` ersetzen den manuellen LLM-Call-Code in `developer.py`
und `tester.py`. `CLAWEval` wird als Basis für `evaluator.py` (ADR-068) verwendet.
`CLAWTrace` liefert Token-Kosten für `TaskQualityScore.cost_usd`.

Der `TaskRouter`, das Gate-System und der `Guardian` bleiben eigenständig.

```
ADR-066 Workflow A (vereinfacht)

TechLead.parse_adr()          ← Eigenständig (High-Reasoning)
  → TaskPlan

Developer.implement()         ← CLAWWorkflow
  CLAWAgent(
    model=router.get_tier(task),    ← ADR-068 TaskRouter
    tools=[read_file, write_file, run_tests],
    output_schema=ImplementationResult,
    retry=CLAWRetry(max=3, fallback=next_tier),
  )

Guardian.check()              ← Eigenständig (Ruff/Bandit/MyPy)

Tester.validate()             ← CLAWAgent
  CLAWAgent(
    model=lean_local,
    tools=[run_pytest, read_coverage],
    output_schema=TestResult,
  )

QualityEvaluator              ← CLAWEval
  CLAWEval(
    evaluator_model=budget_cloud,   ← != executor_model (Bias-Vermeidung)
    metrics=[completion, adr_compliance, code_quality],
    output_schema=TaskQualityScore, ← ADR-068
  )

TechLead.review()             ← Eigenständig (High-Reasoning, Gate 2)
```

**Aufwand**: MEDIUM (2–3 Wochen, ab ADR-066 Phase 3)

**Nutzen**:
- Retry-Logik + Fallback-Chains out-of-the-box (~200 Zeilen Boilerplate gespart)
- `CLAWEval` implementiert QualityEvaluator (ADR-068 Phase 4) direkt
- `CLAWTrace` liefert `cost_usd` und `duration_seconds` für `TaskQualityScore`
- Structured Outputs via Pydantic v2 — kein JSON-Parsing-Overhead
- Modell-Agnostizität: Tier-Wechsel nur in `agent_team_config.yaml`

**Abhängigkeiten**: ADR-066 Phase 1 (Datenmodell) abgeschlossen

---

### Szenario B — Nur CLAWEval für QualityEvaluator

Nur `CLAWEval` für `evaluator.py` (ADR-068 Phase 4). Alle anderen Agenten bleiben
eigenständig.

**Aufwand**: LOW (1 Woche)
**Nutzen**: Schnellste Integration; minimales Risiko
**Nachteil**: Kein Retry/Fallback, kein Tracing für Developer/Tester

---

### Szenario C — Vollständige Integration (alle Agenten + CLAWRouter)

Alle 4 Agenten als `CLAWAgent`. `CLAWRouter` ersetzt ADR-068 TaskRouter.

**Aufwand**: HIGH (4–6 Wochen)
**Risiko**: HIGH — `CLAWRouter` experimentell; Gate-System muss neu integriert werden
**Empfehlung**: Nicht empfohlen

---

### Szenario D — Nicht integrieren

ADR-066/068 sind selbst ausreichend spezifiziert. OpenCLAW würde externe
Abhängigkeit ohne klaren Mehrwert einführen.

**Wann sinnvoll**: Wenn API-Stabilität nicht nachgewiesen oder Lizenzprobleme entstehen.

---

## 5. Bewertungsmatrix

| Kriterium | Gewicht | A (Execution) | B (Eval-only) | C (Vollst.) | D (Nicht) |
|-----------|---------|--------------|--------------|-------------|----------|
| Technischer Nutzen | 30% | 0.9 | 0.5 | 0.8 | 0.0 |
| Implementierungsaufwand | 25% | 0.6 | 0.9 | 0.2 | 1.0 |
| Wartbarkeit | 20% | 0.7 | 0.8 | 0.4 | 0.9 |
| Risiko (invertiert) | 15% | 0.7 | 0.9 | 0.3 | 1.0 |
| Strategische Passung | 10% | 0.9 | 0.6 | 0.7 | 0.2 |
| **Gesamt** | 100% | **0.76** | **0.72** | **0.44** | **0.60** |

> Bewertung: 0.0 = schlecht, 1.0 = optimal. Szenario A gewinnt.

---

## 6. Empfehlung

### 6.1 Empfohlenes Szenario: A — OpenCLAW als Execution-Layer

OpenCLAW wird als **Implementierungsdetail**, nicht als Architektur eingesetzt.
Das Gate-System, der `Guardian` und der `TaskRouter` bleiben vollständig eigenständig.

**Klare Integrationsgrenze:**

| ADR-066/068 Komponente | Ansatz | Begründung |
|------------------------|--------|-------------|
| `developer.py` | `CLAWAgent` + `CLAWWorkflow` | Retry, Structured Outputs, Tools |
| `tester.py` | `CLAWAgent` | Structured Outputs, Lean-Local-Tier |
| `evaluator.py` (ADR-068) | `CLAWEval` | Bias-Vermeidung erzwungen, Metriken |
| `audit_store.py` (ADR-068) | `CLAWTrace` → PostgreSQL | Token-Kosten, Latenz automatisch |
| `router.py` (ADR-068) | **Eigenständig** | `CLAWRouter` zu experimentell |
| `guardian.py` | **Eigenständig** | Regelbasiert, kein LLM |
| `tech_lead.py` | **Eigenständig** | High-Reasoning, Gate 2–4 |
| `re_engineer.py` | **Optional** | `CLAWAgent` wenn Streaming nötig |

### 6.2 Nächste Schritte

| Schritt | Verantwortlich | Zieldatum | Ergebnis |
|---------|---------------|-----------|----------|
| OpenCLAW PoC: `CLAWAgent` für Developer-Task | Cascade (ADR-066 Phase 4) | 2026-Q2 | PoC-Branch in mcp-hub |
| `CLAWEval` für QualityEvaluator evaluieren | Cascade (ADR-068 Phase 4) | 2026-Q2 | Entscheidung A oder B |
| `CLAWTrace` → AuditStore-Exporter | Cascade (ADR-068 Phase 3) | 2026-Q2 | `audit_store.py` |
| ADR-069 erstellen | Achim Dehnert | 2026-Q2 | ADR-069 (accepted) |

### 6.3 ADR-Kandidaten

- [ ] **ADR-069**: OpenCLAW als Execution-Layer für AI Engineering Squad
  *(Entscheidung nach PoC-Ergebnis in ADR-066 Phase 4)*

---

## 7. Offene Fragen

| Frage | Priorität | Wer klärt es? |
|-------|-----------|---------------|
| Ist OpenCLAW-API ab v0.x stabil genug für Production? | HIGH | PoC in ADR-066 Phase 4 |
| Kann `CLAWTrace` direkt in PostgreSQL (AuditStore) exportieren? | HIGH | PoC Phase 3 |
| Unterstützt `CLAWEval` das `evaluator != executor`-Constraint aus ADR-068? | HIGH | PoC Phase 4 |
| Ist `CLAWTools` kompatibel mit bestehenden MCP-Tools in `deployment-mcp`? | MEDIUM | ADR-066 Phase 4 |
| Lizenz-Kompatibilität bei kommerziellem Einsatz (coach-hub, risk-hub)? | MEDIUM | Achim Dehnert |

---

## 8. Referenzen

- [OpenCLAW GitHub](https://github.com/openclaw/openclaw)
- [ADR-066: AI Engineering Squad](../adr/ADR-066-ai-engineering-team.md)
- [ADR-067: Deployment Execution Strategy](../adr/ADR-067-deployment-execution-strategy.md)
- [ADR-068: Adaptive Model Routing](../adr/ADR-068-adaptive-model-routing.md)
- [Concept Paper Template](../templates/concept-paper-template.md)

---

## Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-02-23 | Achim Dehnert | Initial Draft |
