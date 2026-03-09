# ADR-116: Dynamic Model Router — Flexibles LLM-Routing im Agent Coding Team

## Status

Accepted

## Context

Das AI Engineering Squad (ADR-100) führt Tasks über 25 Repos aus. Bisher wird
ein statisches Default-Modell für alle Agenten verwendet. Das führt zu:

- **Zu hohe Kosten**: Einfache Status-Checks mit teuren Modellen (z.B. claude-3.5-sonnet
  für einen `/health` Discord-Command)
- **Suboptimale Qualität**: Billige Modelle für komplexe Architektur-Entscheidungen
- **Provider-Lock-in**: Modell-Name hardcoded im Code — Wechsel erfordert Code-Änderungen
- **Kein Budget-Schutz**: Kein automatischer Fallback bei Kosten-Überschreitung

Das Grafana Controlling Dashboard (ADR-115) liefert jetzt Daten über tatsächliche
Kosten pro Model und Task — die Grundlage für datengetriebenes Routing.

Wir werden **häufig Provider wechseln** — wenn ein besseres Model erscheint,
wenn sich Preise ändern, oder wenn ein spezialisiertes Model für einen Repo-Typ
besser geeignet ist. Der Router muss das ohne Code-Änderungen im Caller ermöglichen.

## Decision

Wir implementieren einen **Model Selector** als dynamischen Teil des Agent Coding Teams.

### Architektur

```
Agent Coding Team
  ├── Developer Agent
  ├── Tester Agent          ─── rufen alle auf:
  ├── Guardian Agent             model_selector.select_model(role, complexity)
  ├── Tech Lead                       ↓
  └── Model Selector        ←── neu: regelbasiert + budget-aware
            ↓
       llm_mcp /v1/chat (OpenRouter, provider-agnostisch)
            ↓
       OpenRouter → GPT-4o / Claude / Llama / ... (wechselbar)
```

Der Model Selector ist **kein LLM** — er ist ein regelbasierter Service:
1. **Route-Tabelle**: `(AgentRole, TaskComplexity) → (model, tier, provider)`
2. **Budget-Tracking**: Tages-Cap über `MODEL_SELECTOR_DAILY_BUDGET_USD`
3. **Cost-Sensitive Mode**: Automatischer Downgrade bei 80% Budget-Verbrauch
4. **Fallback-Kette**: Kein Match → einfachere Complexity → budget default

### Route-Tabelle (Stand 2026-03)

| Agent | Complexity | Model | Tier | Kosten/1K Token |
|---|---|---|---|---|
| discord_status | trivial | gpt-4o-mini | budget | $0.000375 |
| discord_ask | simple | llama-3.1-8b | local | $0.000055 |
| discord_ask | moderate | gpt-4o-mini | budget | $0.000375 |
| discord_chat | moderate | gpt-4o | standard | $0.006250 |
| discord_chat | complex | claude-3.5-sonnet | premium | $0.009000 |
| developer | simple | gpt-4o-mini | budget | $0.000375 |
| developer | moderate | gpt-4o | standard | $0.006250 |
| developer | complex | claude-3.5-sonnet | premium | $0.009000 |
| tester | simple/moderate | gpt-4o-mini | budget | $0.000375 |
| tester | complex | gpt-4o | standard | $0.006250 |
| guardian | moderate | gpt-4o | standard | $0.006250 |
| guardian | complex | claude-3.5-sonnet | premium | $0.009000 |
| tech_lead/planner | complex/architectural | claude-3.5-sonnet | premium | $0.009000 |

### Budget-Automatik

```
MODEL_SELECTOR_DAILY_BUDGET_USD=10.0    # Default: $10/Tag
MODEL_SELECTOR_BUDGET_WARNING_PCT=0.80  # Warnung + Downgrade bei 80%

Wenn Budget ≥ 80%:
  premium → openai/gpt-4o
  standard → openai/gpt-4o-mini
  budget → meta-llama/llama-3.1-8b-instruct

Wenn Budget 100% überschritten:
  ALLE Calls → openai/gpt-4o-mini (minimalste Kosten)
```

### Provider-Wechsel

Ein Provider-Wechsel erfordert **nur eine Änderung** in `model_selector.py`:

```python
# Alt:
(AgentRole.DEVELOPER, TaskComplexityHint.COMPLEX): ("anthropic/claude-3.5-sonnet", "premium", "anthropic"),

# Neu (z.B. bei Wechsel zu Gemini):
(AgentRole.DEVELOPER, TaskComplexityHint.COMPLEX): ("google/gemini-2.0-flash-thinking", "premium", "google"),
```

Kein Caller-Code muss geändert werden.

### Integration mit bestehenden ADRs

- **ADR-068 (TaskRouter)**: Bestehende `TaskComplexity` Enum wird gemappt auf
  `TaskComplexityHint` via `_map_task_complexity()`
- **ADR-084 (ModelRegistry)**: `ModelRegistry` bleibt für DB-getriebene Tier-Auflösung
  bestehen. `ModelSelector` ist der opinionated Routing-Layer darüber.
- **ADR-114 (llm_mcp Gateway)**: `sel.openrouter_model` wird direkt als `model`
  Parameter an `/v1/chat` übergeben.
- **ADR-115 (Grafana)**: `record_llm_cost()` trackt Kosten täglich;
  `llm_calls` Tabelle enthält Model-Tracking für Grafana-Auswertung.

### Implementierung

```
orchestrator_mcp/
  model_selector.py               — ModelSelector, AgentRole, select_model()
  agent_team/
    model_router_integration.py   — get_model_for_agent(), record_llm_cost()
```

**Usage in einem Agent:**

```python
from orchestrator_mcp.model_selector import select_model, AgentRole

# Einfachste Form:
sel = select_model(AgentRole.DEVELOPER, "complex")
# sel.openrouter_model → "anthropic/claude-3.5-sonnet"
# sel.tier → "premium"
# sel.reason → "role=developer | complexity=complex | tier=premium"

# Via Integration-Shim (empfohlen in agent_team/):
from orchestrator_mcp.agent_team.model_router_integration import get_model_for_agent
sel = get_model_for_agent("developer", task.complexity)
```

## Alternatives Considered

### A: LLM-basierter Router (Meta-LLM entscheidet)

- **Pro**: Kann komplexe Kontext-Faktoren berücksichtigen
- **Contra**: Kosten für den Router selbst, Latenz, Zirkuläres Problem (welches LLM wählt den Router?)
- **Entscheidung**: Regelbasiert ist deterministisch, schnell, kostenlos

### B: Prometheus-Metriken + automatisches Routing

- **Pro**: Echte Performance-Daten steuern Routing
- **Contra**: Zu komplex, Prometheus-Setup für 25 Repos overhead
- **Entscheidung**: Grafana + manuelle Anpassung der Route-Tabelle reicht

### C: Routing direkt in llm_mcp (Server-seitig)

- **Pro**: Zentraler Punkt
- **Contra**: llm_mcp kennt dann Agent-Semantik (SRP-Verletzung), schwerer testbar
- **Entscheidung**: Routing im orchestrator_mcp — kennt Agenten, Tasks, Budget

## Consequences

### Positiv

- **60-80% Kosten-Reduktion**: Einfache Tasks gehen auf günstige Models
- **Provider-Wechsel in <5 Minuten**: Nur Route-Tabelle anpassen, kein Deployment
- **Budget-Schutz**: Kein unerwartetes Überschreiten des Tages-Budgets
- **Grafana-Sichtbarkeit**: Jede Routing-Entscheidung landet in `llm_calls`
- **Rückwärtskompatibel**: Bestehende Agenten können `get_model_for_agent()` gradually adopten

### Negativ / Risiken

- Route-Tabelle muss bei neuen Models manuell aktualisiert werden
- `TaskComplexityHint` muss vom Caller korrekt gesetzt werden
  (falsche Einschätzung → falsches Model)
- Budget-Reset ist täglich (nicht per-Task) — ein teurer Task kann Budget aufbrauchen

### Migrations-Plan

1. `discord/handlers.py`: Discord-Commands nutzen `select_model(AgentRole.DISCORD_*)` ✅ (nächster Schritt)
2. `agent_team/developer.py`: Developer-Agent nutzt `get_model_for_agent("developer", ...)` 
3. `agent_team/tester.py`, `guardian.py`: analog
4. `agent_team/tech_lead.py`, `planner.py`: analog
5. Nach 30 Tagen Grafana-Daten: Route-Tabelle data-driven anpassen

## References

- ADR-068: Task Router (Tier-Konzept, ROUTING_MATRIX)
- ADR-082: LLM Adapter Architecture
- ADR-084: Model Registry (DB-Backend für Tier-Auflösung)
- ADR-100: Extended Agent Team
- ADR-114: Discord + LLM Gateway
- ADR-115: Grafana Agent Controlling Dashboard
- [OpenRouter Models](https://openrouter.ai/models)
