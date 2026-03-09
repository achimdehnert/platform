# ADR-116: Implementierungsplan — Budget-Aware Rule-Based Fallback Router

**Version**: 1.0 (Post-Review, alle Blocker behoben)  
**Datum**: 2026-03-09  
**Einordnung**: Erweiterung von ADR-068, nicht paralleles System

---

## Revised Architecture

ADR-116 wird als **ergänzender Budget-aware Layer** über ADR-068 positioniert:

```
RuleBasedBudgetRouter (ADR-116)
    ├── Budget < 80%  → ADR-068 TaskRouter (volle LLM-Routing-Qualität)
    └── Budget ≥ 80%  → Direkte DB-Rule-Table (kein LLM-Call nötig)
         └── Unbekannte Rolle/Complexity → budget_default Fallback
```

**Keine neuen Konkurrenz-Systeme.** ADR-068's router.py wird erweitert, nicht ersetzt.

---

## Dateistruktur

```
orchestrator_mcp/
├── agent_team/
│   ├── router.py                          # ADR-068 (bestehend) — MINIMAL erweitern
│   ├── rule_based_router.py               # NEU: ADR-116 Kernkomponente
│   └── budget_tracker.py                  # NEU: PostgreSQL-backed Budget-Check
├── models/
│   └── model_route_config.py              # NEU: DB-Model für Route-Tabelle
└── migrations/
    └── 0043_model_route_config.py         # NEU: Alembic-Migration
```

---

## Phase 1: Datenmodell (Tag 1)

### 1.1 `ModelRouteConfig` — DB-backed Route-Tabelle

→ Datei: `model_route_config_model.py`

- Platform-Standards: BigAutoField PK + public_id UUID
- Kein tenant_id: globale System-Konfiguration (wie llm_model_pricing)
- Soft-Delete: deleted_at
- Unique: (agent_role, complexity_hint) WHERE deleted_at IS NULL

### 1.2 Migration

→ Datei: `0043_model_route_config.py`

- Idempotent (IF NOT EXISTS)
- Seed-Daten aus ADR-116 Route-Tabelle
- Discord-Rollen NICHT als ModelRouteConfig (eigenes Config-System)

---

## Phase 2: Budget-Tracker (Tag 1)

### 2.1 `BudgetTracker` — PostgreSQL-backed, Redis-gecacht

→ Datei: `budget_tracker.py`

- Liest `SUM(cost_usd)` aus `llm_calls` für aktuellen Tag UTC
- 60s Redis-Cache (kein DB-Hit bei jedem Call)
- Thread-safe via asyncio.Lock
- Gibt `BudgetStatus` zurück: spent, limit, pct, mode

---

## Phase 3: Rule-Based Router (Tag 2)

### 3.1 `RuleBasedBudgetRouter`

→ Datei: `rule_based_router.py`

- `select(agent_role, complexity, tenant_id, task_id)` → `ModelSelection`
- Lädt Route-Tabelle aus DB (5min-Cache)
- Budget-Check via `BudgetTracker`
- Schreibt `routing_reason` in llm_calls
- Vollständige Enum-Validierung für `AgentRole` und `TaskComplexityHint`
- Fallback-Kette: unbekannte Combo → MODERATE → budget_default

---

## Phase 4: ADR-068 Integration (Tag 2-3)

### 4.1 `router.py` Minimal-Erweiterung

```python
# orchestrator_mcp/agent_team/router.py — Ergänzung
class TaskRouter:
    """Bestehender ADR-068 Router (unverändert)."""
    
    async def route_with_budget_guard(
        self,
        task: TaskDefinition,
        budget_tracker: BudgetTracker,
    ) -> RoutingDecision:
        """
        ADR-116 Integration:
        - Budget ≥ 80% → RuleBasedBudgetRouter (schnell, kein LLM-Call)
        - Budget < 80%  → Bestehender LLM-Router (volle Qualität)
        """
        budget = await budget_tracker.get_status()
        
        if budget.mode == BudgetMode.COST_SENSITIVE:
            # Fast-path: Rule-based (keine LLM-Latenz)
            from orchestrator_mcp.agent_team.rule_based_router import RuleBasedBudgetRouter
            return await RuleBasedBudgetRouter.select(
                agent_role=task.agent_role,
                complexity=task.complexity,
                tenant_id=task.tenant_id,
                task_id=task.task_id,
                reason_prefix="budget_guard",
            )
        
        # Normal-path: ADR-068 LLM-basiertes Routing (unverändert)
        return await self._llm_route(task)
```

### 4.2 Discord-Handler — Eigene Minimal-Config

Discord-Commands bekommen **keinen** Zugang zu `ModelSelector`. Stattdessen:

```python
# discord/config.py
DISCORD_COMMAND_MODELS: dict[str, str] = {
    "status":  os.environ.get("DISCORD_STATUS_MODEL", "openai/gpt-4o-mini"),
    "ask":     os.environ.get("DISCORD_ASK_MODEL", "meta-llama/llama-3.1-8b-instruct"),
    "chat":    os.environ.get("DISCORD_CHAT_MODEL", "openai/gpt-4o"),
}
# Keine DB, kein Router — Discord-Modelle sind operationelle Config, keine Routing-Logik
```

---

## Umgebungsvariablen

```bash
# ADR-116 Budget-Config
MODEL_SELECTOR_DAILY_BUDGET_USD=10.0       # Tages-Budget in USD
MODEL_SELECTOR_BUDGET_WARNING_PCT=0.80     # Downgrade-Trigger
MODEL_SELECTOR_BUDGET_EMERGENCY_PCT=1.00   # Emergency-Fallback

# Budget-Cache TTL
MODEL_SELECTOR_BUDGET_CACHE_TTL=60         # Sekunden

# Discord-Modelle (unabhängig vom Agent-Router)
DISCORD_STATUS_MODEL=openai/gpt-4o-mini
DISCORD_ASK_MODEL=meta-llama/llama-3.1-8b-instruct
DISCORD_CHAT_MODEL=openai/gpt-4o
```

---

## Test-Plan

```
orchestrator_mcp/agent_team/tests/
├── test_rule_based_router.py      # Routing-Logik, Fallbacks, Enum-Validierung
├── test_budget_tracker.py         # Budget-Berechnung, Cache, Reset-Timing
└── test_router_integration.py     # Budget-Guard-Integration mit ADR-068 router.py
```

Ziel: 100% Abdeckung der Fallback-Kette und Budget-Trigger-Logik.

---

## Migrations-Plan für bestehende Agenten

```
Schritt 1: RuleBasedBudgetRouter deployed, Budget-Tracking aktiv
    → Keine Änderung an Agent-Code (backward-compatible)

Schritt 2: router.py erhält route_with_budget_guard()
    → Optional opt-in pro Agent (Feature-Flag)

Schritt 3: Nach 30 Tagen Grafana-Daten: Route-Tabelle in Admin anpassen
    → Kein Code-Deployment nötig (DB-backed!)

Schritt 4: Discord-Handler migrieren auf DISCORD_COMMAND_MODELS
    → ModelSelector-Dependency aus Discord entfernen
```

---

## Rollback-Plan

Da alle Änderungen additiv und über Feature-Flags steuerbar:

```python
# Feature-Flag (ENV)
BUDGET_GUARD_ENABLED = os.environ.get("BUDGET_GUARD_ENABLED", "false") == "true"

# In router.py:
if settings.BUDGET_GUARD_ENABLED:
    return await self.route_with_budget_guard(task, budget_tracker)
return await self._llm_route(task)  # ADR-068 original, unverändert
```

Rollback = `BUDGET_GUARD_ENABLED=false` → sofort ohne Deployment.
