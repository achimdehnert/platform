# ADR-116: Dynamic Model Router — Budget-Aware Rule-Based Fallback Router

## Status

Accepted — v2.0 (2026-03-09, Post-Review)

**Änderungen gegenüber v1.0**: Vollständige Überarbeitung nach Review.
Alle 3 Blocker (B-01/B-02/B-03) und 3 kritische Befunde (K-01/K-02/K-03) behoben.
Siehe `docs/adr/reviews/ADR-116-review.md` und `docs/adr/reviews/ADR-116-input-bewertung.md`.

## Context

Das AI Engineering Squad (ADR-100) führt Tasks über 25 Repos aus. ADR-068 (TaskRouter)
ist vollständig implementiert (7/7 Phasen ✅) und liefert LLM-basiertes Routing mit
Confidence-Score und Feedback-Loop.

Folgende Lücken bestehen noch:

- **Kein Budget-Schutz**: ADR-068 prüft kein Tages-Budget — bei hohem Durchsatz
  können teure Modelle das Budget sprengen
- **Kein Cost-Sensitive Fallback**: Kein automatischer Downgrade bei Budget-Überschreitung
- **Route-Tabelle hardcoded**: Modell-Wechsel erfordern Code-Deployment
- **Security-Audits ungeschützt**: Budget-Downgrade könnte sicherheitskritische
  Analyse auf günstigere Modelle degradieren (UC-SE-5)

Das Grafana Controlling Dashboard (ADR-115) liefert Kosten-Daten in `llm_calls` —
diese Tabelle ist die Grundlage für persistentes Budget-Tracking.

## Decision

ADR-116 erweitert ADR-068 um einen **Budget-Aware Rule-Based Fallback Layer**.
Es ist **kein paralleles System** — es ist ein Pre-Filter vor dem bestehenden
`TaskRouter`, der bei Budget-Überschreitung die LLM-Routing-Entscheidung übernimmt.

### Revised Architecture

```
Agent Coding Team (developer, tester, guardian, tech_lead, planner,
                   re_engineer, security_auditor)
        │
        ▼
TaskRouter.route_with_budget_guard()        ← ADR-116 Erweiterung
        │
        ├── Budget < 80%
        │       └── ADR-068 TaskRouter._llm_route()    (LLM-basiert, Confidence-Score,
        │                                                Feedback-Loop, AuditStore)
        │
        └── Budget ≥ 80%  ODER  Emergency
                └── RuleBasedBudgetRouter.select()     (regelbasiert, kein LLM-Call)
                        │
                        ├── Route aus DB (ModelRouteConfig)
                        ├── Budget-Check via llm_calls SUM (PostgreSQL)
                        ├── routing_reason → llm_calls.routing_reason
                        └── Fallback-Kette: unbekannt → MODERATE → Emergency
        │
        ▼
   llm_mcp /v1/chat (ADR-114, OpenRouter, provider-agnostisch)
        │
        ▼
   OpenRouter → GPT-4o / Claude / Llama / ... (wechselbar ohne Code-Änderung)
```

**Discord-Commands sind NICHT Teil dieses Routers.**
Discord nutzt eigene ENV-basierte Config (`discord/config.py`, K-02 Fix).

### Neue Dateistruktur

```
orchestrator_mcp/
├── agent_team/
│   ├── router.py                    # ADR-068 (bestehend) — TaskRouterBudgetGuardMixin ergänzt
│   ├── rule_based_router.py         # NEU: RuleBasedBudgetRouter (Kernkomponente)
│   └── budget_tracker.py            # NEU: PostgreSQL-backed Budget-Check
├── models/
│   └── model_route_config.py        # NEU: DB-Model für Route-Tabelle
└── migrations/
    └── 0043_model_route_config.py   # NEU: Alembic-Migration + Seed-Daten
```

### Agent-Rollen (AgentRole Enum)

```python
class AgentRole(str, enum.Enum):
    DEVELOPER        = "developer"
    TESTER           = "tester"
    GUARDIAN         = "guardian"
    TECH_LEAD        = "tech_lead"
    PLANNER          = "planner"
    RE_ENGINEER      = "re_engineer"
    SECURITY_AUDITOR = "security_auditor"  # UC-SE-5: niemals Budget-Downgrade
```

Discord-Rollen (`discord_status`, `discord_ask`, `discord_chat`) sind **keine**
AgentRoles — sie werden über `DISCORD_*_MODEL` ENV-Variablen konfiguriert.

### Route-Tabelle (DB-backed, Stand 2026-03)

Route-Tabelle wird in PostgreSQL (`model_route_configs`) verwaltet.
Änderungen erfordern **kein Code-Deployment** — nur DB-Update oder Admin-UI.

| Agent | Complexity | Model (Normal) | Tier | Budget-Downgrade |
|---|---|---|---|---|
| developer | simple | gpt-4o-mini | budget | llama-3.1-8b (local) |
| developer | moderate | gpt-4o | standard | gpt-4o-mini (budget) |
| developer | complex | claude-3.5-sonnet | premium | gpt-4o (standard) |
| tester | simple/moderate | gpt-4o-mini | budget | llama-3.1-8b (local) |
| tester | complex | gpt-4o | standard | gpt-4o-mini (budget) |
| guardian | trivial | gpt-4o-mini | budget | llama-3.1-8b (local) |
| guardian | moderate | gpt-4o | standard | gpt-4o-mini (budget) |
| guardian | complex | claude-3.5-sonnet | premium | gpt-4o (standard) |
| tech_lead | complex/architectural | claude-3.5-sonnet | premium | gpt-4o (standard) |
| planner | complex | claude-3.5-sonnet | premium | gpt-4o (standard) |
| re_engineer | moderate | gpt-4o | standard | gpt-4o-mini (budget) |
| re_engineer | complex | claude-3.5-sonnet | premium | gpt-4o (standard) |
| **security_auditor** | **moderate/complex** | **claude-3.5-sonnet** | **premium** | **claude-3.5-sonnet** ⚠️ |

**security_auditor**: `budget_model == model` — kein Downgrade auch bei 80%+ Budget.
CVE-Analyse auf gpt-4o-mini würde Sicherheitslücken übersehen (UC-SE-5).

### Budget-Tracking (PostgreSQL-backed)

```sql
-- Tages-Budget: direkte Aggregation auf llm_calls (ADR-115)
SELECT COALESCE(SUM(cost_usd), 0) AS spent_today
FROM llm_calls
WHERE created_at >= date_trunc('day', NOW() AT TIME ZONE 'UTC')
  AND deleted_at IS NULL;
```

- **Multi-Container-safe**: alle Instanzen lesen dieselbe DB
- **Tages-Reset**: automatisch über UTC-Datumstrunkierung — kein Cron-Job
- **Redis-Cache**: 60s TTL für Performance (kein DB-Hit bei jedem Call)
- **Fallback**: Bei Redis-Ausfall direkter DB-Query

### Budget-Modi

```
Budget  < 80%  → NORMAL:         ADR-068 LLM-Router (volle Qualität)
Budget 80-100% → COST_SENSITIVE:  RuleBasedBudgetRouter mit budget_model
Budget > 100%  → EMERGENCY:       Alle Calls → openai/gpt-4o-mini
                                   (Ausnahme: security_auditor bleibt premium)
```

### Routing-Audit-Trail

Jede Entscheidung wird in `llm_calls.routing_reason` geschrieben (K-01 Fix):

```
rule:developer+complex→premium|budget=50.0%
budget_downgrade:85.0%|normal=anthropic/claude-3.5-sonnet|downgrade=openai/gpt-4o
emergency:budget=105.0%>$10.00|role=tech_lead|complexity=complex
fallback:no_route|role=new_role|complexity=complex
adr068_router:confidence=0.85
```

### Feature-Flag für sicheres Rollout

```bash
BUDGET_GUARD_ENABLED=false   # Default: ADR-068 Original-Verhalten
BUDGET_GUARD_ENABLED=true    # ADR-116 Budget-Guard aktiv
```

Rollback = `BUDGET_GUARD_ENABLED=false` → sofort, ohne Deployment.

### Usage

```python
# In router.py (TaskRouterBudgetGuardMixin):
result = await task_router.route_with_budget_guard(
    task=task,
    session=db_session,
    budget_tracker=budget_tracker,  # FastAPI DI Singleton
)
# result.model → z.B. "anthropic/claude-3.5-sonnet"
# result.routing_reason → "rule:developer+complex→premium|budget=45.2%"

# RuleBasedBudgetRouter direkt (für Tests):
router = RuleBasedBudgetRouter(budget_tracker)
selection = await router.select(
    session=session,
    agent_role="security_auditor",
    complexity="complex",
    tenant_id=tenant_id,
    task_id=task_id,
)
```

### Discord-Trennung (K-02 Fix)

```python
# discord/config.py — völlig unabhängig von RuleBasedBudgetRouter
from orchestrator_mcp.discord.config import get_discord_model

config = get_discord_model("chat")   # → DiscordModelConfig(model="openai/gpt-4o")
config = get_discord_model("ask")    # → DiscordModelConfig(model="meta-llama/llama-3.1-8b-instruct")
```

ENV-Variablen: `DISCORD_STATUS_MODEL`, `DISCORD_ASK_MODEL`, `DISCORD_CHAT_MODEL`,
`DISCORD_CODE_MODEL`. Kein DB-Eintrag, kein Code-Deployment bei Änderung.

## Alternatives Considered

### A: ADR-116 als eigenständiges paralleles System (v1.0 — verworfen)

- **Problem**: Zwei konkurrierende Routing-Systeme im selben Package (B-01 Blocker)
- **Entscheidung**: ADR-116 als Erweiterung von ADR-068, nicht als Ersatz

### B: In-Memory Budget-Counter

- **Problem**: Bei Docker-Restart oder Multi-Worker-Setup wird Counter auf 0 zurückgesetzt
- **Entscheidung**: PostgreSQL-Aggregation auf `llm_calls` — kein neues Schema nötig

### C: Budget-Guard als Post-Filter (nach ADR-068 Routing)

- **Problem**: ADR-068 macht bereits LLM-Call (Kosten + Latenz) bevor Budget geprüft wird
- **Entscheidung**: Pre-Filter — Budget ≥ 80% → kein LLM-Call für Routing nötig

### D: `no_budget_downgrade` Flag auf ModelRouteConfig

- **Pro**: Flexibel per Route konfigurierbar ohne neue Enum-Rolle
- **Contra**: Weniger semantisch klar als eigene AgentRole
- **Entscheidung**: `SECURITY_AUDITOR` als eigene Rolle (Option A) — klare Abgrenzung.
  `no_budget_downgrade` Flag kann später ergänzt werden.

## Consequences

### Positiv

- **60-80% Kosten-Reduktion**: Budget-aware Routing eliminiert teure Calls bei Engpässen
- **Provider-Wechsel ohne Deployment**: DB-backed Route-Tabelle — Admin-UI genügt
- **Budget-Schutz**: Automatischer Downgrade bei 80%, Emergency-Stop bei 100%
- **Security-garantiert**: `security_auditor` wird nie downgegradet — CVE-Analyse bleibt zuverlässig
- **Grafana-Sichtbarkeit**: `routing_reason` in `llm_calls` — nachvollziehbar warum Modell X
- **Rückwärtskompatibel**: Feature-Flag, bestehende ADR-068 `route()` unverändert

### Negativ / Risiken

- Route-Tabelle muss bei neuen AgentRoles initial befüllt werden (Migration)
- 60s Redis-Cache bedeutet: Budget-Überschreitung wird bis zu 60s verzögert erkannt
- `security_auditor` ist immer premium — auch wenn Budget bei 99% steht

### Migrations-Plan

```
Schritt 1: Migration 0043 deployen (model_route_configs + llm_calls.routing_reason)
Schritt 2: RuleBasedBudgetRouter + BudgetTracker deployen (BUDGET_GUARD_ENABLED=false)
Schritt 3: discord/handlers.py auf discord/config.py umstellen
Schritt 4: BUDGET_GUARD_ENABLED=true nach Monitoring-Check (7 Tage Grafana-Daten)
Schritt 5: Nach 30 Tagen: Route-Tabelle data-driven über DB-Admin anpassen
```

## References

- ADR-068: Task Router (LLM-basiert, Confidence-Score, Feedback-Loop)
- ADR-082: LLM Adapter Architecture
- ADR-084: Model Registry (DB-Backend für Tier-Auflösung)
- ADR-100: Extended Agent Team (Agent-Rollen)
- ADR-114: Discord + LLM Gateway
- ADR-115: Grafana Agent Controlling Dashboard (`llm_calls` Schema)
- `docs/adr/reviews/ADR-116-review.md` — Blocker-Review (2026-03-09)
- `docs/adr/reviews/ADR-116-input-bewertung.md` — Input-Bewertung + UC-SE-2/3/5
- `docs/adr/inputs/dynamic router/` — Implementierungsplan + alle Input-Dateien
- [OpenRouter Models](https://openrouter.ai/models)
