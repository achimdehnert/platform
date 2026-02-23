---
status: "proposed"
date: 2026-02-23
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
amends: ["ADR-066-ai-engineering-team.md"]
related: ["ADR-066-ai-engineering-team.md", "ADR-067-work-management-strategy.md", "ADR-057-platform-test-strategy.md"]
---

# Adopt Adaptive Model Routing and Quality Feedback Loop for AI Agent Tasks

---

## Context and Problem Statement

ADR-066 definiert ein strukturiertes AI Engineering Squad mit statischer Tier-Zuweisung:
Tech Lead → High-Reasoning, Developer → Standard-Coding, Tester → Lean/Lokal.

Dieses statische Mapping hat drei fundamentale Probleme:

1. **Kein Routing-Intelligenz**: Nicht jede Tech-Lead-Aufgabe erfordert High-Reasoning.
   Ein einfaches ADR-Parsing ist kein Architektur-Review. Statische Zuweisung
   verschwendet Budget für triviale Tasks und unterschätzt komplexe.

2. **Kein Qualitätsfeedback**: Ob das zugewiesene Modell eine Aufgabe *gut* erledigt
   hat, wird nicht gemessen. Es gibt keinen Feedback-Loop — schlechte Ergebnisse
   werden nicht erkannt, gute nicht belohnt.

3. **Kein automatischer Modell-Wechsel**: Budget-Modelle (MiniMax M2.5: 80.2%
   SWE-Bench, ~$0.002/1k tokens) erreichen bei vielen Task-Klassen Frontier-Qualität.
   Ohne Metriken wechselt niemand automatisch auf günstigere Modelle.

**Ziel**: Ein modell-agnostisches Routing-System das (a) den optimalen Tier pro Task
wählt, (b) die Qualität der Ausführung misst, und (c) das Routing basierend auf
historischen Metriken automatisch optimiert.

---

## Decision Drivers

- **Kostenoptimierung**: Budget-Modelle wo möglich, High-Reasoning nur wo nötig
- **Qualitätssicherung**: Messbare Qualitäts-Scores pro Task und Modell-Tier
- **Modell-Agnostizität**: Modell-Wechsel ohne Workflow-Änderung (nur Config)
- **Lernfähigkeit**: Routing-Matrix verbessert sich durch historische Metriken
- **Menschliche Kontrolle**: Tier-Upgrades immer mit Gate 1+ (Notify/Approve)
- **Traceability**: Jede Routing-Entscheidung ist auditierbar (AuditStore)

---

## Considered Options

### Option 1 — Adaptive Routing + Quality Evaluator (gewählt)

3-Schichten-Architektur: TaskRouter (LLM-basiert) → Execution (Agent-Team) →
QualityEvaluator (LLM-basiert) mit Feedback-Loop in Router-Matrix.

**Pro:**
- Vollständiger Feedback-Loop: Metriken fließen zurück in Routing-Entscheidungen
- Router selbst ist Budget-Modell — kein High-Reasoning-Overhead für Routing
- Modell-Wechsel ohne Code-Änderung (nur `agent_team_config.yaml`)
- Qualitäts-Scores ermöglichen datengetriebene Tier-Entscheidungen
- Skaliert von Solo-Entwickler bis Multi-Agent-Team

**Con:**
- Höhere initiale Komplexität (3 neue Komponenten)
- Router-LLM-Call pro Task erhöht Latenz (~1–2s)
- Initiale Routing-Matrix ist heuristisch — braucht N≥20 Tasks zum Lernen

---

### Option 2 — Statisches Tier-Mapping mit manueller Überprüfung

Beibehaltung ADR-066-Mapping, monatliche manuelle Review der Kosten.

**Pro:** Kein Setup-Aufwand, sofort nutzbar

**Con:**
- Kein automatischer Feedback-Loop
- Manuelle Review ist fehleranfällig und wird vergessen
- Kein datengetriebener Modell-Wechsel

**Verworfen**: Löst keines der drei Kernprobleme.

---

### Option 3 — Regelbasiertes Routing ohne LLM

Heuristik-Tabelle (Complexity × Risk → Tier) ohne LLM-Routing.

**Pro:** Deterministisch, kein API-Call für Routing

**Con:**
- Heuristik kann Task-Nuancen nicht erfassen (z.B. kleiner Bugfix in kritischem Modul)
- Keine Selbstoptimierung — Matrix muss manuell gepflegt werden
- Kein Qualitätsfeedback

**Verworfen**: Zu starr für heterogene Task-Landschaft.

---

### Option 4 — Externes Routing-Service (LangChain/LlamaIndex Router)

Verwendung eines externen Routing-Frameworks.

**Pro:** Fertige Implementierung, Community-Support

**Con:**
- Externe Abhängigkeit, Vendor-Lock-in
- Nicht auf Platform-spezifische ADR-Struktur und Task-Templates abgestimmt
- Metriken-Schema nicht anpassbar

**Verworfen**: Platform-spezifische Anforderungen überwiegen.

---

## Pros and Cons of the Options

### Option 1 — Adaptive Routing + Quality Evaluator (gewählt)

- **Pro**: Vollständiger Feedback-Loop — Metriken verbessern Routing automatisch
- **Pro**: Router ist Budget-Modell — kein High-Reasoning-Overhead
- **Pro**: Modell-Wechsel ohne Code-Änderung
- **Pro**: Qualitäts-Scores sind auditierbar und nachvollziehbar
- **Con**: Höhere initiale Komplexität
- **Con**: Lernkurve — braucht N≥20 Tasks für valide Routing-Matrix

### Option 2 — Statisches Mapping

- **Pro**: Sofort nutzbar, kein Setup
- **Con**: Kein Feedback-Loop, kein automatischer Modell-Wechsel

### Option 3 — Regelbasiertes Routing

- **Pro**: Deterministisch, kein API-Call
- **Con**: Keine Selbstoptimierung, zu starr

### Option 4 — Externes Framework

- **Pro**: Fertige Implementierung
- **Con**: Vendor-Lock-in, nicht platform-spezifisch

---

## Decision Outcome

**Gewählt: Option 1** — 3-Schichten-Architektur mit TaskRouter, QualityEvaluator
und Feedback-Loop, implementiert als Erweiterung von `orchestrator_mcp/agent_team/`.

### Positive Consequences

- Datengetriebene Modell-Zuweisung statt statischer Heuristik
- Messbare Qualitäts-Scores pro Task, Modell und Tier
- Automatische Kostenoptimierung durch Tier-Downgrade bei gleichbleibender Qualität
- Vollständiger Audit-Trail für jede Routing-Entscheidung

### Negative Consequences

- Initiale Routing-Matrix ist heuristisch — Lernphase erforderlich
- Zusätzliche Latenz durch Router-LLM-Call (~1–2s pro Task)
- Komplexere Fehlerdiagnose bei Multi-Layer-System

---

## Implementation Details

### Architektur-Überblick

```
┌─────────────────────────────────────────────────────┐
│              TASK DEFINITION                         │
│  ai-task.yaml (Template: .windsurf/templates/)       │
│  type, complexity, risk_level, context_size          │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│              TASK ROUTER                             │
│  Modell: budget_cloud (M2.5-Lightning / Haiku)       │
│  Input: Task-Template + Routing-Matrix               │
│  Output: Tier-Empfehlung + Confidence (0.0–1.0)      │
│  Confidence < 0.7 → Gate 2 (Mensch entscheidet)      │
└──────────────────────┬──────────────────────────────┘
                       │ Tier + Modell
                       ▼
┌─────────────────────────────────────────────────────┐
│              EXECUTION LAYER (ADR-066)               │
│  Tech Lead / Developer / Tester / Re-Engineer        │
│  Guardian (regelbasiert, immer Gate 0)               │
└──────────────────────┬──────────────────────────────┘
                       │ Result + Artifacts
                       ▼
┌─────────────────────────────────────────────────────┐
│              QUALITY EVALUATOR                       │
│  Modell: budget_cloud (NICHT dasselbe wie Executor)  │
│  Objektive Metriken: automatisch gemessen            │
│  Subjektive Metriken: LLM-Bewertung                  │
│  Output: TaskQualityScore → AuditStore               │
└──────────────────────┬──────────────────────────────┘
                       │ Aggregierte Scores (N≥20 Tasks)
                       ▼
┌─────────────────────────────────────────────────────┐
│              FEEDBACK LOOP                           │
│  Score < Schwellwert → Tier-Upgrade vorschlagen      │
│  Score gut + Cost hoch → Tier-Downgrade (Gate 0)     │
│  Routing-Matrix aktualisieren                        │
└─────────────────────────────────────────────────────┘
```

### Modell-Tiers (Erweiterung ADR-066)

| Tier | Charakteristik | Typische Modelle (Feb 2026) | Kosten-Index |
|------|---------------|----------------------------|--------------|
| `high_reasoning` | Extended Thinking, Architektur | Claude Opus, o3 | 100% |
| `standard_coding` | Code-Generierung, Reviews | Claude Sonnet, GPT-4o | 20% |
| `budget_cloud` | Agentic, SWE-Bench ≥75% | MiniMax M2.5, GLM-5, Haiku | 2–5% |
| `lean_local` | Lokal, kein API-Cost | Qwen 2.5 (Ollama), Phi-4 | 0% |
| `rule_based` | Statische Analyse, kein LLM | Ruff, Bandit, MyPy | 0% |

> `budget_cloud` ist neu gegenüber ADR-066. Ollama dient als universeller
> Model-Router — auch für Cloud-Modelle (`ollama launch --model minimax-m2.5:cloud`).

### Routing-Matrix (initial heuristisch, lernend)

```python
# orchestrator_mcp/agent_team/router.py

ROUTING_MATRIX: dict[tuple, str] = {
    # (complexity, risk_level, requires_planning) → tier
    ("trivial",       "low",      False): "lean_local",
    ("trivial",       "low",      True):  "budget_cloud",
    ("simple",        "low",      False): "budget_cloud",
    ("simple",        "medium",   False): "budget_cloud",
    ("moderate",      "low",      False): "budget_cloud",
    ("moderate",      "medium",   False): "standard_coding",
    ("moderate",      "medium",   True):  "standard_coding",
    ("moderate",      "high",     True):  "standard_coding",
    ("complex",       "medium",   False): "standard_coding",
    ("complex",       "high",     True):  "high_reasoning",
    ("architectural", "medium",   True):  "high_reasoning",
    ("architectural", "high",     True):  "high_reasoning",
    ("architectural", "critical", True):  "high_reasoning",
}

FALLBACK_CHAIN: dict[str, str] = {
    "lean_local":     "budget_cloud",
    "budget_cloud":   "standard_coding",
    "standard_coding":"high_reasoning",
    "high_reasoning": "high_reasoning",  # No fallback — escalate to human
}
```

### Quality Metrics Schema

```python
# orchestrator_mcp/agent_team/metrics.py

@dataclass
class TaskQualityScore:
    task_id: str
    model_tier: str
    model_name: str
    task_type: str
    task_complexity: str

    # --- Objektiv messbar (automatisch) ---
    guardian_passed: bool           # Ruff + Bandit + MyPy grün
    coverage_delta: float           # +/- Coverage-Änderung (0.0 = neutral)
    iteration_count: int            # Review-Zyklen bis Approval (Ziel: ≤ 2)
    tokens_used: int                # API-Kosten-Proxy
    duration_seconds: float         # Durchlaufzeit
    cost_usd: float                 # Tatsächliche API-Kosten

    # --- Subjektiv (separates Budget-LLM bewertet) ---
    completion_score: float         # 0.0–1.0: Aufgabe vollständig gelöst?
    adr_compliance_score: float     # 0.0–1.0: ADR-Vorgaben eingehalten?
    code_quality_score: float       # 0.0–1.0: Lesbarkeit, Struktur, Patterns

    # --- Menschliches Feedback (optional, Gate 1+) ---
    human_override: bool            # Hat Mensch Output korrigiert?
    human_rating: int | None        # 1–5 Sterne

    @property
    def composite_score(self) -> float:
        """Gewichteter Gesamt-Score für Routing-Matrix-Update."""
        return (
            self.completion_score * 0.40 +
            self.adr_compliance_score * 0.25 +
            self.code_quality_score * 0.20 +
            (1.0 if self.guardian_passed else 0.0) * 0.10 +
            (1.0 if self.coverage_delta >= 0 else 0.0) * 0.05
        )
```

### Schwellwerte für automatischen Tier-Wechsel

| Metrik | Schwellwert | Aktion bei Unterschreitung |
|--------|-------------|---------------------------|
| `composite_score` | ≥ 0.80 | Tier-Upgrade vorschlagen (Gate 1: Notify) |
| `guardian_passed` | 100% | Workflow stoppt (Gate 0: blockiert) |
| `coverage_delta` | ≥ 0.0 | Warning (Gate 1: Notify) |
| `iteration_count` | ≤ 2 | Tier-Upgrade nach 3 Überschreitungen |
| `cost_usd` / Task | ≤ Budget | Tier-Downgrade wenn Score gut (Gate 0) |

**Aggregierungs-Fenster**: N=20 Tasks gleicher Klasse (type × complexity × risk_level).
Einzelne Ausreißer lösen keinen Tier-Wechsel aus.

### Feedback-Loop Algorithmus

```python
def update_routing_matrix(
    task_class: tuple,          # (complexity, risk_level, requires_planning)
    current_tier: str,
    scores: list[TaskQualityScore],  # letzte N=20 Tasks dieser Klasse
) -> RoutingMatrixUpdate | None:

    avg_composite = mean(s.composite_score for s in scores)
    avg_cost = mean(s.cost_usd for s in scores)

    if avg_composite < 0.80:
        # Qualität unzureichend → Tier-Upgrade (Gate 1: Notify Mensch)
        new_tier = FALLBACK_CHAIN[current_tier]
        return RoutingMatrixUpdate(
            task_class=task_class,
            old_tier=current_tier,
            new_tier=new_tier,
            reason=f"composite_score={avg_composite:.2f} < 0.80 over {len(scores)} tasks",
            gate=1,  # Mensch wird informiert, kann ablehnen
        )

    if avg_composite >= 0.85 and avg_cost > COST_BUDGET_PER_TASK[current_tier]:
        # Qualität gut, aber zu teuer → Tier-Downgrade (Gate 0: Automatisch)
        cheaper_tier = get_cheaper_tier(current_tier)
        if cheaper_tier:
            return RoutingMatrixUpdate(
                task_class=task_class,
                old_tier=current_tier,
                new_tier=cheaper_tier,
                reason=f"score={avg_composite:.2f} >= 0.85, cost=${avg_cost:.4f} > budget",
                gate=0,  # Automatisch, kein Mensch nötig
            )

    return None  # Kein Update nötig
```

### Implementierungsstruktur

```
orchestrator_mcp/
  agent_team/
    router.py          # TaskRouter: LLM-basiertes Routing + Routing-Matrix
    metrics.py         # TaskQualityScore, Schwellwerte, Aggregierung
    evaluator.py       # QualityEvaluator: LLM-Bewertung subjektiver Metriken
    feedback.py        # Feedback-Loop: update_routing_matrix()
    audit_store.py     # AuditStore: persistente Speicherung aller Scores

.windsurf/
  templates/
    ai-task.yaml       # Task-Template (maschinenlesbar, Router-Input)
```

### Konfiguration (`agent_team_config.yaml` — Erweiterung)

```yaml
routing:
  router_model_tier: "budget_cloud"     # Router selbst ist Budget-Modell
  evaluator_model_tier: "budget_cloud"  # Evaluator ≠ Executor (Bias-Vermeidung)
  confidence_threshold: 0.70            # < 0.70 → Gate 2 (Mensch entscheidet)
  learning_window: 20                   # N Tasks für Matrix-Update

tiers:
  high_reasoning:
    model: "claude-opus-4"
    extended_thinking: true
    cost_budget_per_task_usd: 2.00
  standard_coding:
    model: "claude-sonnet-4"
    cost_budget_per_task_usd: 0.20
  budget_cloud:
    model: "minimax-m2.5:cloud"         # via Ollama Launch
    fallback: "glm-5:cloud"
    cost_budget_per_task_usd: 0.02
  lean_local:
    model: "qwen2.5-coder:32b"          # Ollama lokal
    cost_budget_per_task_usd: 0.00
  rule_based:
    model: null
    cost_budget_per_task_usd: 0.00

quality_thresholds:
  composite_score_min: 0.80
  guardian_pass_rate_min: 1.00
  coverage_delta_min: 0.0
  max_iterations: 2
  escalation_rate_max: 0.20
```

---

## Migration Tracking

| Phase | Inhalt | Definition of Done | Status |
|-------|--------|--------------------|--------|
| 1 | Task-Template (`ai-task.yaml`) | Template in `.windsurf/templates/`, dokumentiert | ✅ done |
| 2 | Routing-Matrix + `router.py` | Heuristische Matrix, Unit-Tests grün | ✅ done (2026-02-23) |
| 3 | `metrics.py` + `audit_store.py` | Schema implementiert, PostgreSQL-Migration grün | ✅ done (2026-02-23) |
| 4 | `evaluator.py` (LLM-Bewertung) | Evaluator läuft gegen 5 Test-Tasks, Scores plausibel | ✅ done (2026-02-23) |
| 5 | `feedback.py` (Feedback-Loop) | Matrix-Update nach N=20 synthetischen Tasks korrekt | ✅ done (2026-02-23) |
| 6 | Integration mit ADR-066 Workflows | Workflow A/B/C nutzen Router statt statisches Mapping | ⬜ pending |
| 7 | Playbook + End-to-End Test | Agentic-Coding-Workflow dokumentiert und getestet | ⬜ pending |

---

## Consequences

### Risks

| Risiko | Schwere | Mitigation |
|--------|---------|-----------|
| Router-LLM gibt falschen Tier zurück | MEDIUM | Confidence-Threshold + Gate 2 bei Unsicherheit |
| Evaluator-Bias (gleiches Modell bewertet sich selbst) | HIGH | Evaluator-Modell ≠ Executor-Modell (erzwungen in Config) |
| Routing-Matrix konvergiert auf High-Reasoning (Qualitäts-Bias) | MEDIUM | Cost-Budget pro Tier als harte Grenze |
| N=20 Lernfenster zu klein für seltene Task-Klassen | LOW | Fallback auf Heuristik-Matrix wenn < N Tasks vorhanden |
| Feedback-Loop Instabilität (Tier-Ping-Pong) | LOW | Hysterese: Downgrade nur wenn Score ≥ 0.85 über 20 Tasks |

### Confirmation

- Router-Confidence wird bei jedem Task geloggt — Audit-Log prüfbar
- `composite_score` ≥ 0.80 als Ziel über alle Task-Klassen — messbar via AuditStore
- Tier-Downgrade-Rate ≥ 10% nach 100 Tasks (zeigt Kostenoptimierung wirkt)
- Kein Tier-Upgrade ohne Gate 1 (Notify) — verifizierbar via Audit-Log
- Evaluator-Modell ≠ Executor-Modell — erzwungen durch Config-Validation beim Start

---

## Deferred Decisions

| Entscheidung | Begründung | Zieldatum | Referenz |
|--------------|------------|-----------|----------|
| SWE-Bench-Score als Mindestanforderung pro Tier | Braucht Benchmark-Infrastruktur; erst nach Phase 4 sinnvoll | 2026-Q3 | ADR-066 |
| Intra-Role Parallelism (Sub-Agenten innerhalb einer Rolle) | M2.5 zeigt Analyst+Architect parallel — erst nach Phase 6 relevant | 2026-Q3 | ADR-066 |
| Persistente Routing-Matrix in PostgreSQL vs. YAML | YAML für MVP ausreichend; DB wenn Matrix > 100 Einträge | 2026-Q2 | ADR-066 |
| Human-Rating UI (1–5 Sterne pro Task) | Braucht Frontend-Komponente; erst nach Phase 3 | 2026-Q3 | ADR-067 |

---

## More Information

- ADR-066: AI Engineering Squad — Rollen, Gates, Workflows (wird durch dieses ADR erweitert)
- ADR-067: Work Management Strategy — GitHub Issues als Task-Store, AI-Agent-Protokoll
- ADR-057: Platform Test Strategy — Coverage-Ziele die QualityEvaluator prüft
- Task-Template: `.windsurf/templates/ai-task.yaml`
- MiniMax M2.5: 80.2% SWE-Bench Verified, ~$0.002/1k tokens (Stand Feb 2026)
- Ollama Launch: universeller Model-Router für lokale + Cloud-Modelle

---

## Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-02-23 | Achim Dehnert | Initial — Status: Proposed |

---

## Drift-Detector Governance Note

```yaml
paths:
  - orchestrator_mcp/agent_team/router.py
  - orchestrator_mcp/agent_team/metrics.py
  - orchestrator_mcp/agent_team/evaluator.py
  - orchestrator_mcp/agent_team/feedback.py
  - agent_team_config.yaml
gate: APPROVE
```
