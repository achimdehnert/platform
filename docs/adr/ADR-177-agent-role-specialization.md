---
status: proposed
date: 2026-04-30
version: 1.2
deciders: [achimdehnert, cascade]
related: [ADR-068, ADR-173, ADR-174]
amends: [ADR-066]
staleness_months: 6
tags: [agent-team, llm-routing, cost-optimization, autonomy, multi-agent]
---

# ADR-177 — Agent Role Specialization

**Split monolithic Developer into 5 specialized agents with deterministic
routing, observability, prompt-caching, and a documented misclassification fallback.**

## Versionshistorie

| Version | Datum | Änderungen |
|---------|-------|------------|
| 1.0 | 2026-04-30 | Erstentwurf — 4 Bots, qualitatives Cost-Modell |
| 1.1 | 2026-04-30 | Self-Review-Fixes: 5 Bots + Re-Engineer, Stage-Routing, Observability, Caching |
| **1.2** | **2026-04-30** | **Cost-Math korrigiert (B-5), Modell-Namen verifiziert (B-6), config.py-Migration explizit (M-7), Demotion-Konflikt geklärt (M-8), Wave-1–3-Integration, Truth-Table-Klassen, Rollback-Pfad** |

## Context

Der aktuelle `DeveloperAgent` im `orchestrator_mcp` bearbeitet **alle**
Task-Types von Typo-Fixes bis Feature-Implementation mit dem gleichen Modell
(`swe`). Vier dokumentierte Probleme:

1. **Überqualifikation** — Typo-Fix verbraucht ~$0.003 (`swe`), könnte aber für ~$0.0004 (`gpt_low`) bearbeitet werden (Faktor 7).
2. **Unterqualifikation** — Architecture-Tasks (ADR-Drafts, Migrations-Pläne) scheitern mit `swe`-Class-Modellen, weil die nötige Reasoning-Tiefe fehlt. Das Tier-System in `config.py:MODEL_SELECTION` weist `opus` zu, aber **kein Agent konsumiert es**.
3. **Keine Skill-Trennung** — Identischer System-Prompt für Docs, Tests, Refactor, Feature → undifferenzierte Outputs, kein Prompt-Caching möglich.
4. **Stub-Rollen** — `Tech Lead` und `Re-Engineer` aus ADR-066 sind Stubs; Gate-2+-Tasks fallen auf Menschen zurück, auch wenn ein Modell sie bewältigen könnte.

### State of the Art (2026)

- **MALBO** (Sabbatella, 2025, arxiv 2511.11788) — Heterogene spezialisierte Multi-Agent-Teams: 45.2 % avg Cost-Reduktion, bis 65.8 % in Pareto-optimalen Konfigurationen, ohne Quality-Verlust.
- **HierRouter** (Gupta et al., 2025, arxiv 2511.09873) — RL-basiertes hierarchisches Routing: +2.4× Quality bei marginalen Mehrkosten.
- **Mavik Labs** (Jan 2026) — Routing + Prompt-Caching kombiniert: 47–80 % Spend-Reduktion. **Caching-Anteil ist dominanter Lever.**
- **Moltbook-AI** (März 2026) — Selbst bei 10 % Misclassification netto Savings → rule-based Routing als pragmatischer Einstieg.

### Bestehende Infrastruktur (Wave 1–3)

Bereits live im Workflow-Layer:
- **`/agentic-coding` v6** (Wave 1) — Auto-Dispatch Router + Cost-Aware Downgrade-Ladder
- **`/session-start` Phase 2.5** (Wave 2) — Error-Learning erzeugt `adr-candidate` Issues
- **`/process-agent-queue`** (Wave 3) — Queue-Prozessor für `auto`-labeled Issues

ADR-177 (Wave 5) ergänzt diese Workflow-Schicht durch **Code-seitige Spezialisierung im `orchestrator_mcp`**.

## Decision

**5 spezialisierte Agents** statt einem Monolith, **deterministisches Stage-Routing**,
**Prompt-Caching first**, **Misclassification-Fallback**, **Audit-Logging**.

### Agent-Matrix

| Agent | Task-Types | Modell-Tier | Gate | Prompt-Skeleton |
|-------|-----------|-------------|------|-----------------|
| **DocBot** | `docs`, `typo`, `lint`, CHANGELOG, README, ADR-Text | `gpt_low` | ≤ 1 | `system_prompts/doc_bot.md` |
| **TestBot** | `test`, Fixtures, Factories, Coverage-Fixes | `gpt_low` | ≤ 1 | `system_prompts/test_bot.md` |
| **FeatureBot** | `feature`, `bugfix` | `swe` | ≤ 2 | `system_prompts/feature_bot.md` |
| **ReEngineerBot** | `refactor`, `tech_debt` (komplexitätsabhängig) | `swe` | ≤ 2 | `system_prompts/re_engineer_bot.md` |
| **ArchitectBot** | `architecture`, `breaking_change`, `security`, ADR-Drafts, komplexer Refactor | `opus` | ≤ 3 | `system_prompts/architect_bot.md` |

### Cross-Cutting (unverändert aus ADR-066)

- **Guardian** — Lint/Security/Tests — prüft Output **aller 5 Agents**
- **Tester** — pytest-Runner — Verifikationsstufe
- **Planner** — entscheidet welcher Agent zugeteilt wird
- **Merger** — fasst parallele Agent-Branches zusammen (Vorbereitung Wave 4)
- **Tech Lead** — Human-Eskalation für Gate ≥ 3 (siehe § Escalation Protocol)

### Enums (verbindliche API)

```python
from enum import Enum

class AgentType(str, Enum):
    DOC_BOT = "doc_bot"
    TEST_BOT = "test_bot"
    FEATURE_BOT = "feature_bot"
    RE_ENGINEER_BOT = "re_engineer_bot"
    ARCHITECT_BOT = "architect_bot"
    TECH_LEAD = "tech_lead"  # Human escalation only

class ModelTier(str, Enum):
    NONE = "none"          # Tech Lead / human
    GPT_LOW = "gpt_low"
    SWE = "swe"
    OPUS = "opus"

class GateLevel(int, Enum):
    ZERO = 0; ONE = 1; TWO = 2; THREE = 3; FOUR = 4

class Complexity(str, Enum):
    TRIVIAL = "trivial"; SIMPLE = "simple"; MODERATE = "moderate"
    COMPLEX = "complex"; EXPERT = "expert"; ARCHITECTURAL = "architectural"

class TaskType(str, Enum):
    DOCS = "docs"; TYPO = "typo"; LINT = "lint"
    TEST = "test"
    FEATURE = "feature"; BUGFIX = "bugfix"
    REFACTOR = "refactor"; TECH_DEBT = "tech_debt"
    ARCHITECTURE = "architecture"; BREAKING_CHANGE = "breaking_change"
    SECURITY = "security"; ADR = "adr"
```

### Modell-Tier-Auflösung (B-6 Fix — verifizierte Modelle)

Tier-Labels werden in `config.py` auf konkrete Modelle aufgelöst. Zwei
**getrennte** Dicts (M-7 Fix — kein Breaking Change im bestehenden `MODEL_SELECTION`):

```python
# orchestrator_mcp/config.py

# NEU: Tier-Label → konkretes Modell (verified gegen agent_team/config.py)
MODEL_TIER_TO_MODEL: dict[ModelTier, str] = {
    ModelTier.GPT_LOW: "anthropic/claude-haiku-4-5-20251001",
    ModelTier.SWE:     "anthropic/claude-sonnet-4-6-20260217",
    ModelTier.OPUS:    "anthropic/claude-opus-4-6-20260205",
    ModelTier.NONE:    "",  # human only
}

# UMBENANNT von MODEL_SELECTION (Migration-Shim siehe unten)
TASK_TYPE_TO_TIER: dict[TaskType, ModelTier] = {
    TaskType.DOCS: ModelTier.GPT_LOW,
    TaskType.TYPO: ModelTier.GPT_LOW,
    TaskType.LINT: ModelTier.GPT_LOW,
    TaskType.TEST: ModelTier.GPT_LOW,
    TaskType.FEATURE: ModelTier.SWE,
    TaskType.BUGFIX: ModelTier.SWE,
    TaskType.REFACTOR: ModelTier.SWE,
    TaskType.TECH_DEBT: ModelTier.SWE,
    TaskType.ARCHITECTURE: ModelTier.OPUS,
    TaskType.BREAKING_CHANGE: ModelTier.OPUS,
    TaskType.SECURITY: ModelTier.OPUS,
    TaskType.ADR: ModelTier.OPUS,
}

# Backward-Compat-Shim — 1 Release lang behalten
MODEL_SELECTION = {tt.value: tier.value for tt, tier in TASK_TYPE_TO_TIER.items()}
```

**Fallback-Strategie:** Bei API-Outage des Primary-Tiers → Promotion auf
nächst-höheren Tier (HierRouter-Pattern).

**Demotion-Verbot — präzisiert (M-8 Fix):**

```python
ARCH_TYPES = {TaskType.ARCHITECTURE, TaskType.BREAKING_CHANGE,
              TaskType.SECURITY, TaskType.ADR}

# Demotion erlaubt: NUR wenn Task NICHT in ARCH_TYPES UND
#                   complexity != ARCHITECTURAL
# /agentic-coding v6 Cost-Aware Downgrade-Ladder gilt unter dieser Bedingung.
# Bei ARCH_TYPES oder ARCHITECTURAL: kein opus → swe Demotion (Quality > Cost).
```

### Routing-Logik — Stage-Pipeline (deterministisch)

```python
@dataclass(frozen=True)
class RoutingDecision:
    agent: AgentType
    model: ModelTier
    rationale: str
    confidence: float  # 0.0–1.0; <0.7 → Tech-Lead bestätigt

DOC_TYPES = {TaskType.DOCS, TaskType.TYPO, TaskType.LINT}

# Initial confidence — wird in Phase 5 anhand AuditStore-Daten kalibriert (m-8 Fix)
INITIAL_CONFIDENCE: dict[AgentType, float] = {
    AgentType.ARCHITECT_BOT: 0.95,
    AgentType.DOC_BOT: 0.90,
    AgentType.TEST_BOT: 0.90,
    AgentType.FEATURE_BOT: 0.90,
    AgentType.RE_ENGINEER_BOT: 0.85,
    AgentType.TECH_LEAD: 1.00,
}

def select_agent(
    task_type: TaskType,
    complexity: Complexity,
    gate: GateLevel,
) -> RoutingDecision:
    """Deterministic four-stage routing.

    Property-tested (hypothesis): same inputs → same RoutingDecision.
    Truth-Table-tested: 27 Äquivalenzklassen-Cases (siehe Test-Sektion).
    """
    # Stage 1: Architectural / high-stakes override
    if complexity is Complexity.ARCHITECTURAL or task_type in ARCH_TYPES:
        return RoutingDecision(
            AgentType.ARCHITECT_BOT, ModelTier.OPUS,
            "architectural complexity or arch-class task",
            INITIAL_CONFIDENCE[AgentType.ARCHITECT_BOT],
        )

    # Stage 2: Gate-based veto
    if gate >= GateLevel.THREE:
        return RoutingDecision(
            AgentType.TECH_LEAD, ModelTier.NONE,
            "Gate >= 3 requires human approval (ADR-066)",
            INITIAL_CONFIDENCE[AgentType.TECH_LEAD],
        )

    # Stage 3: Task-type matching
    if task_type in DOC_TYPES:
        return RoutingDecision(AgentType.DOC_BOT, ModelTier.GPT_LOW,
                               "docs/lint/typo",
                               INITIAL_CONFIDENCE[AgentType.DOC_BOT])
    if task_type is TaskType.TEST:
        return RoutingDecision(AgentType.TEST_BOT, ModelTier.GPT_LOW,
                               "tests",
                               INITIAL_CONFIDENCE[AgentType.TEST_BOT])
    if task_type in {TaskType.REFACTOR, TaskType.TECH_DEBT}:
        if complexity in {Complexity.COMPLEX, Complexity.EXPERT}:
            return RoutingDecision(AgentType.ARCHITECT_BOT, ModelTier.OPUS,
                                   "complex refactor → architect",
                                   INITIAL_CONFIDENCE[AgentType.ARCHITECT_BOT])
        return RoutingDecision(AgentType.RE_ENGINEER_BOT, ModelTier.SWE,
                               "standard refactor",
                               INITIAL_CONFIDENCE[AgentType.RE_ENGINEER_BOT])
    if task_type in {TaskType.FEATURE, TaskType.BUGFIX}:
        return RoutingDecision(AgentType.FEATURE_BOT, ModelTier.SWE,
                               "feature/bug",
                               INITIAL_CONFIDENCE[AgentType.FEATURE_BOT])

    # Stage 4: Unknown → escalate (no silent default)
    return RoutingDecision(
        AgentType.TECH_LEAD, ModelTier.NONE,
        f"unknown: task_type={task_type!r}, complexity={complexity!r}",
        0.0,
    )
```

### Misclassification & Escalation

Drei komplementäre Mechanismen (Industry-Best-Practice 2026):

1. **Confidence-Gate.** `confidence < 0.7` → Auto-Eskalation an Tech-Lead-Queue (1-Klick-Bestätigung, kein inhaltlicher Eingriff).
2. **Self-Revision.** Jeder Bot darf via `request_reroute(reason: str)` zurückmelden, dass er falsch zugeordnet ist. Planner verlangt dann Re-Routing mit explizitem `complexity`-Override.
3. **Guardian-Veto-Eskalation.** Bei 2× Folge-Fail wird Task an nächst-höheren Bot promoted (DocBot-Fail → FeatureBot, FeatureBot-Fail → ArchitectBot).

### Caching-Layer (primärer Cost-Lever — B-5 Fix)

Alle Bots nutzen `iil-aifw.PromptCache` mit Anthropic prompt-caching beta
header. System-Prompts pro Bot werden als statische
`cache_control: {"type": "ephemeral"}` markiert.

**Nach Mavik 2026:** Caching-Saving 30–50 % — **dominanter Cost-Lever**, nicht
Routing allein. Routing primär für **Quality-Gain bei Architektur** (opus
liefert brauchbare ADR-Drafts statt Mensch-Eskalation), sekundär für Cost.

## Considered Alternatives

### A) Status quo (ein Developer für alles)

- ❌ **Cost:** typo_fix = $0.003 statt $0.0004 (Faktor 7 zu teuer für triviale Tasks)
- ❌ **Quality:** Architecture-Tasks scheitern — `swe`-Modell genügt nicht
- ✅ **Simplicity:** eine Code-Basis

### B) Per-Task-Type Model-Dispatch ohne Agent-Split (nur Model-Routing)

- ✅ Löst Cost-Problem teilweise
- ❌ Kein spezialisiertes Prompt-Engineering, kein effektives Caching
- ❌ Tech Lead bleibt Stub
- ❌ Empirisch in MALBO als unterlegen gegen heterogene Teams

### C) Volle Spezialisierung (gewählt — v1.2 mit 5 Bots + Caching-Priorität)

- ✅ Quality-Gain bei Architektur (opus statt Eskalation)
- ✅ Prompt-Engineering pro Rolle isoliert optimierbar
- ✅ **Caching pro Bot maximal effektiv** (statische System-Prompts)
- ✅ Re-Engineer bleibt eigene Rolle (Konsistenz mit ADR-066)
- ✅ Net-Saving 30–45 % erwartet (Caching-dominiert, siehe Cost-Modeling)
- ⚠️ 3–5 Tage Implementation-Aufwand

### D) Hybrid: Routing nur für Modell, Single Agent für Code

- ✅ Geringer Code-Aufwand
- ❌ Verliert Prompt-Spezialisierung (gleicher Prompt, anderes Modell ≠ Skill-Trennung)
- ❌ Caching weniger effektiv (weniger Cache-Hits bei generischem Prompt)

### E) RL-basiertes Routing (HierRouter)

- ✅ Theoretisch optimal
- ❌ Braucht große Training-Datenmenge (bei uns nicht vorhanden)
- ⏸ Future Work — wenn AuditStore 6+ Monate Daten hat, evaluieren

## Cost Modeling (B-5 Fix — korrigierte Math)

### Annahmen (Phase-0 kalibrierbar)

Token-Annahmen basieren auf Stichproben aus aktuellem `MODEL_SELECTION`-Logging.
Anteilsverteilung ist **Hypothese** und wird in Phase 0 verifiziert.

| Task-Type | Anteil | Tokens (in/out) | Cost old (`swe`) | Cost new (Routing) | Diff/Task |
|-----------|--------|-----------------|------------------|---------------------|-----------|
| docs/typo/lint | 35 % | 1.5K / 0.8K | $0.0165 | $0.000395 (`gpt_low`) | −$0.0161 |
| test | 20 % | 2.0K / 1.5K | $0.0285 | $0.0007 (`gpt_low`) | −$0.0278 |
| feature/bug | 30 % | 4.0K / 3.0K | $0.057 | $0.057 (`swe`) | $0 |
| refactor | 10 % | 3.5K / 2.5K | $0.048 | $0.048 (`swe`) | $0 |
| architecture | 5 % | 6.0K / 5.0K | $0.093 | $0.465 (`opus`) | **+$0.372** |

### Korrekte Berechnung pro 100 Tasks

| Bucket | Old Cost | New Cost (Routing) |
|--------|----------|---------------------|
| docs/typo/lint (35×) | $0.578 | $0.014 |
| test (20×) | $0.570 | $0.014 |
| feature/bug (30×) | $1.710 | $1.710 |
| refactor (10×) | $0.480 | $0.480 |
| architecture (5×) | $0.465 | $2.325 |
| **Σ pro 100 Tasks** | **$3.803** | **$4.543** |

→ **Routing allein: +19 % MEHRkosten** (nicht Saving!), weil Architecture-Promotion
auf opus die Doc/Test-Savings überkompensiert.

### Saving entsteht durch Caching, nicht Routing

Mit Prompt-Caching (Mavik 2026 Median 40 %, Range 30–50 %) auf alle Bot-Calls:

| Szenario | Cost pro 100 Tasks | Saving vs Status quo |
|----------|---------------------|----------------------|
| Status quo (alle swe, kein Caching) | $3.803 | Baseline |
| Routing only (kein Caching) | $4.543 | **−19 % (Mehrkosten)** |
| Status quo + Caching (40 %) | $2.282 | +40 % |
| **Routing + Caching (40 %)** | **$2.726** | **+28 % netto** |
| Routing + Caching (50 %, optimistic) | $2.272 | +40 % netto |

### Ehrliche Saving-Quelle

**Saving = Caching-dominiert.** Routing liefert Quality-Gain (Architektur
durch opus), nicht Cost-Saving. Beide kombiniert ergeben **erwartet 25–40 %
netto** — verifizierbar in Phase 5.

**Validierungsplan:**
- Phase 0 Baseline: Cost-Verteilung über 14 Tage → falsifiziert oder bestätigt 35/20/30/10/5 Annahme
- Phase 5: Diff vs Baseline. Bei < 20 % Saving → Routing-Tuning oder Rollback (siehe Phase 6)

### Zusatzkosten Shadow-Mode (m-7 Fix)

Während Phase 2 Shadow-Week laufen alte + neue Bots parallel.
Bei aktueller Tagesrate ($3.80/100 Tasks × ~10 Tasks/Tag) zusätzlich
**~$26 für die Shadow-Woche** — vernachlässigbar gegen erwartetes Monats-Saving.

## Implementation

### Phase 0 — Baseline-Messung (PFLICHT vor Phase 1)

**Vor** Phase 1: 14 Tage `session_stats`-Aufzeichnung unter Status quo. Metriken:

- Cost pro Task-Type (mean, p50, p95)
- Erfolgsrate pro Task-Type (Gate-passed / total)
- Token-Verteilung pro Task-Type
- Häufigkeitsverteilung der Task-Types (verifiziert die 35/20/30/10/5-Annahme)

→ Diese Baseline ist die **Referenz** für Cost-Reduction-Validierung in Phase 5.

### Phase 1 — Code-Struktur

```
orchestrator_mcp/agents/
├── __init__.py             # exposiert FeatureBot als DeveloperAgent (Shim)
├── base.py                 # BaseAgent — gemeinsame Interfaces
├── planner.py              # select_agent() Stage-Pipeline
├── doc_bot.py              # NEU
├── test_bot.py             # NEU
├── feature_bot.py          # = bisheriger developer.py (git mv)
├── re_engineer_bot.py      # NEU (5. Bot, ehemaliger Stub aus ADR-066)
├── architect_bot.py        # NEU (ersetzt Tech-Lead-Stub für ≤ Gate-2 Arch-Tasks)
├── guardian.py             # unverändert
├── tester.py               # unverändert
└── merger.py               # unverändert
```

Backward-Compat-Shim 1 Release lang in `__init__.py`:

```python
from .feature_bot import FeatureBot as DeveloperAgent  # noqa: F401
```

### Phase 2 — Migration (Strangler-Pattern)

1. `git mv developer.py feature_bot.py`, Klasse umbenennen
2. `DocBot`, `TestBot`, `ReEngineerBot`, `ArchitectBot` implementieren (~100 LoC + Tests pro Bot)
3. `Planner.select_agent()` Routing-Funktion + Truth-Table-Test
4. `delegate_subtask` API-Erweiterung — **Option C** aus Self-Review: optionales `task_type`, Default `feature` (= aktuelles Verhalten, **kein** Breaking Change)
5. **Shadow-Mode** für 1 Woche: neue Bots werden parallel zu FeatureBot aufgerufen, Outputs geloggt aber nicht verwendet → Vergleichsdaten
6. Cutover nach Shadow-Mode-Audit (Misclassification-Rate < 10 %)
7. `agent_team_status` Response erweitert auf 5 Agents

### Phase 3 — Tests (Test-Pyramide)

| Stufe | Was | Akzeptanz | CI-Job |
|-------|-----|-----------|--------|
| Unit | **Truth-Table 27 Äquivalenzklassen** (3 task-Klassen × 3 complexity-Klassen × 3 gate-Klassen — m-6 Fix) | 100 % deterministisch | `pytest test_planner_routing.py` |
| Property | `select_agent` ist total + deterministisch (alle 12×6×5=360 Inputs) | hypothesis 1000 cases | `pytest test_planner_properties.py` |
| Bot-Unit | Pro Bot ≥ 80 % line + branch coverage | coverage.py | `pytest test_*_bot.py` |
| Integration | Bot → Guardian → Tester End-to-End | je 3 Goldset-Tasks pro Bot grün | `pytest tests/integration/` |
| Eval | Quality-Score ≥ Status-quo-Baseline | 95 % der Goldset-Tasks bestehen | `python tools/run_eval_suite.py` |
| Regression | Routing-Distribution-Drift | < 20 % Verschiebung pro Task-Type | nightly cron |

**Truth-Table-Klassen (m-6):**
- `task_class ∈ {doc-class, feature-class, arch-class}`
- `complexity_class ∈ {trivial+simple, moderate, complex+expert+architectural}`
- `gate_class ∈ {0-1, 2, 3+}`
- → 3 × 3 × 3 = 27 Äquivalenzklassen
- Property-Test deckt vollständige 360 Kombinationen ab

### Phase 4 — Dokumentation

- `platform/docs/governance/agent-team.md` aktualisieren
- `/agentic-coding` Workflow v6 → v7 (5 Bots in Step-1-Tabelle, `recommended_agent` aus `analyze_task` konsumieren)
- `/process-agent-queue` aktualisieren — nutzt `RoutingDecision` aus Phase 1
- Migration-Guide für `delegate_subtask`-Caller
- Pro Bot: System-Prompt-Skeleton in `system_prompts/{bot}.md`

### Phase 5 — Validierung

Nach 2 Wochen Live: `session_stats` vs Phase-0-Baseline. Re-Review mit Achim.
Confidence-Werte (`INITIAL_CONFIDENCE`) anhand AuditStore-Daten kalibrieren.
Ggf. `TASK_TYPE_TO_TIER` nachjustieren oder Routing-Pipeline tunen.

### Phase 6 — Rollback-Pfad (m-9 Fix)

**Wenn Phase 5 Saving < 20 % netto trotz Tuning:**

1. Backward-Compat-Shim aktivieren — `from .feature_bot import FeatureBot as DeveloperAgent`
2. Planner hartkodiert auf `AgentType.FEATURE_BOT` für alle Task-Types
3. AuditStore-Daten in ADR-178 (Lessons Learned) auswerten
4. Issue-Stub `[adr-candidate] ADR-177 reverted — was geht stattdessen?` öffnen

**Reversibilität:** durch Shim ist Rollback ohne Caller-Änderungen möglich.

## Wave 1–3 Integration (m-11 Fix)

**Wave 1 — `/agentic-coding` v6:**
- Auto-Dispatch Router muss `analyze_task` Response um `recommended_agent` erweitern
- Cost-Aware Downgrade-Ladder respektiert `ARCH_TYPES`-Demotion-Verbot

**Wave 2 — `/session-start` Phase 2.5:**
- Error-Patterns werden pro Agent gelernt (Tag `agent:doc_bot`, `agent:feature_bot` etc.)
- `check_recurring_errors` aggregiert pro Agent → Misclassification-Erkennung

**Wave 3 — `/process-agent-queue`:**
- Queue-Sortierung nutzt `RoutingDecision.confidence` als Tie-Breaker
- Skip-Logik: `confidence < 0.7` → wartet auf nächste interaktive Session

## Observability (ADR-068-konform)

### Audit-Logging

Jede Routing-Entscheidung → AuditStore-Event:

```json
{
  "event": "agent_routing",
  "task_id": "...",
  "task_type": "feature",
  "complexity": "moderate",
  "gate": 1,
  "decision": {
    "agent": "feature_bot",
    "model": "swe",
    "rationale": "feature/bug",
    "confidence": 0.90
  },
  "timestamp": "2026-04-30T..."
}
```

### Prometheus-Metriken

```
agent_routing_decisions_total{agent, model, confidence_bucket}
agent_routing_misclassifications_total{from_agent, to_agent, reason}
agent_cost_per_task_usd{agent, task_type}        (histogram)
agent_quality_score{agent}                       (gauge, 0.0–1.0, post-Guardian)
agent_cache_hit_rate{agent}                      (gauge, 0.0–1.0)
```

### Dashboard (Grafana)

Neues Dashboard `Agent-Team-Specialization`:

- Cost-pro-Task-Type vs Baseline (Phase 0)
- Routing-Distribution (Donut)
- Misclassification-Rate (line, target ≤ 10 %)
- Confidence-Histogram (target: ≥ 80 % der Decisions confidence ≥ 0.85)
- **Cache-Hit-Rate pro Bot** (target: DocBot/TestBot ≥ 60 %, andere ≥ 40 %)

## Implementation Done When

| Akzeptanz | CI-Job / Messung |
|-----------|------------------|
| Phase-0-Baseline aufgezeichnet (14 Tage) | `session_stats` Daten in Postgres |
| 5 Agent-Klassen, je ≥ 80 % Branch-Coverage | `coverage report --fail-under=80` |
| `select_agent` Truth-Table 27/27 grün | `pytest test_planner_routing.py` |
| Property-Tests 1000 Cases ohne Failure | `pytest test_planner_properties.py` |
| `agent_team_status` zeigt 5 Agents | `pytest test_status_endpoint.py` |
| `analyze_task` Response enthält `recommended_agent` + `confidence` | OpenAPI-Schema-Test |
| Migration-Guide existiert + 1 Beispiel-PR | manueller Review |
| Shadow-Mode-Run zeigt < 10 % Misclassification | Audit-Log-Auswertung |
| Prometheus-Metriken im Grafana-Dashboard | Manueller Smoke-Test |
| Cache-Hit-Rate DocBot/TestBot ≥ 60 % | Grafana-Panel |
| CHANGELOG in `mcp-hub` mit Migration-Hinweis | git diff |
| `/agentic-coding` v7 + `/process-agent-queue` v2 mergen | PR Approval |
| Phase-5-Saving ≥ 20 % netto (oder Rollback via Phase 6) | `session_stats` Diff |
| ADR-177 Status `accepted` | Front-Matter |

## Consequences

### Positive

- **Quality Up:** Architecture-Tasks bekommen `opus` → ADR-Drafts werden brauchbar (vorher: Eskalation an Mensch)
- **Fully Autonomous bis Gate 2:** ArchitectBot bearbeitet bisher gestubbte Arch-Tasks
- **Cost-Saving 25–40 % netto** durch Caching-Layer (primärer Lever) + Routing-Mix
- **Pareto-aligned:** Architektur entspricht state-of-the-art (MALBO heterogene Teams)
- **Parallelisierung vorbereitet** (Wave 4): Verschiedene Agents → verschiedene Branches
- **Reversibel** via Backward-Compat-Shim (Phase 6)

### Negative

- **Code-Komplexität:** 5 Agent-Klassen + Planner-Pipeline statt 1 Agent
- **Test-Aufwand:** ~16 h für Test-Pyramide inkl. Eval-Suite
- **Migration-Risiko:** mitigiert via Option-C-Default + Shadow-Mode
- **Misclassification-Risiko:** gemanagt via 3 Mechanismen (Confidence / Self-Revision / Guardian-Veto)
- **Cost-Saving primär durch Caching, nicht Routing** — Routing-Wert liegt im Quality-Gain

### Neutral

- `MODEL_SELECTION` bleibt als Backward-Compat-Alias (Migration-Shim)
- Anthropic-API-Beta-Header für Caching müssen aktiviert sein (`anthropic-beta: prompt-caching-2024-07-31`)

## Rollout-Plan

| Woche | Phase | Aktivität | Gate |
|-------|-------|-----------|------|
| 1–2 | 0 | Baseline-Messung Status quo | 14 Tage `session_stats` aufgezeichnet |
| 2–3 | 1 + 2 | Code-Struktur + Migration auf Branch `feat/agent-specialization` | CI grün, Coverage ≥ 80 % |
| 3 | 2 | Shadow-Mode (1 Woche parallel zu FeatureBot) | Misclassification < 10 % |
| 4 | 2 | Cutover, alte `developer.py`-Klasse weg (Shim bleibt) | Smoke-Tests grün |
| 4 | 3 + 4 | Test-Pyramide-Vervollständigung + Doku + Workflow v7 | Eval-Suite grün |
| 5–6 | 5 | Validierung gegen Baseline, ggf. `TASK_TYPE_TO_TIER` tunen | Cost-Saving ≥ 20 % netto |
| 7 | – | ADR-Status auf `accepted`, Re-Review (oder Phase 6 Rollback) | – |

## Human Escalation Protocol

- **Trigger:** Routing `confidence < 0.7` ODER Gate ≥ 3 ODER 2× Guardian-Fail
- **Mechanismus:** Discord-Channel `#tech-lead-queue` (Webhook) + GitHub-Issue mit Label `agent-escalation`
- **SLA:** 24 h Response, sonst Auto-Pause des Workflows
- **Fallback:** 72 h ohne Response → Task `failed` mit Reason `human_review_timeout`, Notification an Achim per E-Mail

## References

- ADR-066 — Agent Team Architecture (amended)
- ADR-068 — AuditStore (Logging-Pflicht)
- ADR-173 — Orchestrator MCP Server
- ADR-174 — QM Gate (ASSUMPTION[unverified] = 0)
- `/agentic-coding` Workflow v6 → v7 (Wave 1)
- `/session-start` Phase 2.5 (Wave 2)
- `/process-agent-queue` Workflow (Wave 3)
- Sabbatella, A. — *MALBO* (arxiv 2511.11788, 2025)
- Gupta et al. — *HierRouter* (arxiv 2511.09873, 2025)
- Mavik Labs — *LLM Cost Optimization 2026* (Jan 2026) — Caching als dominanter Lever
- Moltbook-AI — *AI Agent Cost Optimization Guide 2026* (März 2026)

## Appendix — System-Prompt-Skeletons (referenziert in Phase 4)

Pro Bot eine `system_prompts/{bot}.md` mit fester Struktur:

```markdown
# {BotName} System Prompt v1.0

## Role (1 Satz)
## Allowed Tools / Boundaries
## Output Format (strikt)
## Few-Shot Examples (mindestens 2)
## Negative Constraints (was du NICHT tust)
## Self-Revision Trigger (wann du request_reroute() aufrufst)
```

Initiale Skeleton-Drafts werden in der Implementierungs-PR mitgeliefert,
nicht in diesem ADR (Trennung Architektur ↔ Implementation).
