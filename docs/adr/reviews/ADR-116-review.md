# ADR-116 Review: Dynamic Model Router

**Reviewer**: Principal IT-Architekt  
**Datum**: 2026-03-09  
**ADR**: ADR-116 — Dynamic Model Router — Flexibles LLM-Routing im Agent Coding Team  
**Gesamturteil**: ❌ **NICHT FREIGEGEBEN** — 3 Blocker, davon 1 grundlegend architektonisch

---

## 1. Review-Tabelle

| # | Befund | Severity | Bereich |
|---|--------|----------|---------|
| B-01 | ADR-116 führt paralleles Routing-System neben ADR-068 ein, das bereits vollständig implementiert ist (7/7 Phasen ✅) — zwei konkurrierende Systeme im selben Package | **BLOCKER** | Architektur |
| B-02 | Budget-Tracking ist offensichtlich in-memory — kein Persistenz-Konzept. Bei Docker-Restart, Multi-Worker oder Scale-out wird der Tages-Counter auf 0 zurückgesetzt | **BLOCKER** | Correctness |
| B-03 | Route-Tabelle hardcodiert in `model_selector.py` (Python-Dict) — widerspricht Platform-Standard „Database-first design". Änderungen erfordern Code-Deployment | **BLOCKER** | Platform-Standard |
| K-01 | Kein Audit-Trail für Routing-Entscheidungen — ADR-068 hat `AuditStore`, ADR-116 schreibt nur „landet in llm_calls". Debugging warum Modell X ausgewählt wurde ist unmöglich | **KRITISCH** | Observability |
| K-02 | `AgentRole.DISCORD_*` in der Route-Tabelle sind keine Agenten des Agent Coding Teams — Discord-Handler sind externe Clients. Konzeptueller Fehler der Rollenabgrenzung | **KRITISCH** | Architektur |
| K-03 | Kein Validierungsmechanismus für `TaskComplexityHint` beim Caller — String-Input ohne Enum-Guard, kein expliziter Fehler bei ungültigem Wert → Silent-Wrong-Routing | **KRITISCH** | Correctness |
| H-01 | Budget-Downgrade fehlt Hysterese: Bei 79% normal, 81% downgraded, 79% normal → instabiles Model-Ping-Pong pro Call | **HOCH** | Betrieb |
| H-02 | `_map_task_complexity()` im ADR nur erwähnt, nicht definiert — das ist die kritische Schnittstelle zu ADR-068 und sie ist eine Black Box | **HOCH** | Integration |
| H-03 | Kein `ModelSelectorDecision`-Model in DB — kein Tracking welcher Task welches Modell bekam, für wie lange, aus welchem Grund | **HOCH** | Observability |
| H-04 | Fallback-Kette bei unbekanntem `(role, complexity)` nicht spezifiziert — neue Rollen führen zu KeyError | **HOCH** | Robustheit |
| M-01 | Budget-Reset-Mechanismus nicht definiert: Wann? Cron-Job? Celery Beat? Bei Midnight UTC? Lokal? Kein Konzept beschrieben | **MEDIUM** | Betrieb |
| M-02 | Kostenangaben in Route-Tabelle als $/1K Token — inkonsistent mit ADR-115/116 (dort $/1M Token). Verwechslungsgefahr | **MEDIUM** | Konsistenz |
| M-03 | Keine Tests für Budget-Logik, Downgrade-Trigger, Fallback-Kette im ADR beschrieben | **MEDIUM** | Qualität |
| M-04 | `select_model()` API zu minimal — kein `tenant_id`, kein `task_id` als Parameter → Logging-Kontext fehlt im llm_calls-Record | **MEDIUM** | Observability |

---

## 2. Detailbefunde

### B-01: Paralleles Routing-System — BLOCKER (Architektonisch)

**Problem**: ADR-068 (Adaptive Model Routing) ist laut eigenem Status **vollständig implementiert** (alle 7 Phasen ✅ done, 2026-02-23). Es existiert bereits:

```
orchestrator_mcp/agent_team/
  router.py       # TaskRouter: LLM-basiertes Routing + Routing-Matrix ✅
  metrics.py      # TaskQualityScore ✅
  evaluator.py    # QualityEvaluator ✅
  feedback.py     # Feedback-Loop: update_routing_matrix() ✅
  audit_store.py  # AuditStore ✅
```

ADR-116 möchte zusätzlich einführen:
```
orchestrator_mcp/
  model_selector.py                        # NEU — parallel zu router.py
  agent_team/model_router_integration.py   # NEU — parallel zu router.py
```

Das ergibt **zwei konkurrierende Routing-Systeme** im selben Package:
- ADR-068 `router.py`: LLM-basiert, Confidence-Score, Feedback-Loop, AuditStore
- ADR-116 `model_selector.py`: regelbasiert, Budget-aware, kein Feedback-Loop

**Korrekte Lösung**: ADR-116 muss als **Erweiterung von ADR-068** spezifiziert werden, nicht als paralleles System. Der `ModelSelector` ist eine neue Strategie innerhalb des bestehenden `TaskRouter`-Frameworks (Option 3 von ADR-068: "Regelbasiertes Routing ohne LLM" — dort wurde als zu starr verworfen, ist aber als Budget-Fallback-Layer sinnvoll).

**Revised Architektur**:
```
ADR-068 TaskRouter (LLM-basiert, high confidence)
    │
    ├── Confidence ≥ 0.70  → LLM-Routing (bisher)
    └── Confidence < 0.70 ODER Budget ≥ 80% 
        → RuleBasedFallbackRouter (ADR-116 Beitrag)
              └── Route-Tabelle aus DB (ModelRouteConfig)
```

ADR-116 liefert den regelbasierten Budget-aware Fallback-Layer — als ergänzende Komponente, nicht als Ersatz.

---

### B-02: In-Memory Budget-Tracking — BLOCKER

**Problem**: Das ADR beschreibt:
```python
MODEL_SELECTOR_DAILY_BUDGET_USD=10.0
```
...aber kein Persistenz-Konzept. Die Route-Tabelle in `model_selector.py` mit `record_llm_cost()` impliziert eine klassenweite Variable oder ein Modul-Level Dict — beide werden bei:
- Docker-Container-Restart → 0
- Gunicorn Worker Reload → 0
- Scale-out (2+ Container) → jeder Container hat eigene 0

**Korrekte Lösung**: Budget-Tracking in PostgreSQL (nutzt ADR-115's `llm_calls` Tabelle!):

```sql
-- Tages-Budget abfragen: direkte SQL-Aggregation auf llm_calls
SELECT 
    COALESCE(SUM(cost_usd), 0) AS spent_today
FROM llm_calls
WHERE 
    created_at >= date_trunc('day', NOW() AT TIME ZONE 'UTC')
    AND deleted_at IS NULL
    AND source NOT IN ('budget_check');  -- Circularity vermeiden
```

Das ist **keine neue Tabelle** — ADR-115 hat `llm_calls` bereits. Budget-Check = aggregierte SQL-Query. Redis-Cache mit 60s TTL für Performance.

---

### B-03: Hardcodierte Route-Tabelle — BLOCKER

**Problem**:
```python
# ADR-116 beschreibt:
(AgentRole.DEVELOPER, TaskComplexityHint.COMPLEX): 
    ("anthropic/claude-3.5-sonnet", "premium", "anthropic"),
```

Platform-Standard: **Database-first design**. Änderungen an der Route-Tabelle müssen ohne Code-Deployment möglich sein. Bei 25 Repos und häufigen Provider-Wechseln (ADR-116 selbst: "häufig Provider wechseln") ist das nicht verhandelbar.

**Korrekte Lösung**: `ModelRouteConfig`-Tabelle in PostgreSQL (siehe Implementierungsplan).

---

### K-01: Kein Routing-Audit-Trail — KRITISCH

**Problem**: ADR-068 hat einen vollständigen `AuditStore` für jede Routing-Entscheidung. ADR-116 hat keinen. Weder `select_model()` noch `get_model_for_agent()` loggen warum ein Modell ausgewählt wurde.

**Folge**: Grafana zeigt "model=gpt-4o-mini" in llm_calls — aber warum? Budget-Trigger? Rule-Match? Fallback? Nicht nachvollziehbar.

**Korrektur**: Routing-Entscheidungen in `llm_calls.routing_reason TEXT` loggen (Ergänzung zu ADR-115-Schema):
```sql
ALTER TABLE llm_calls ADD COLUMN IF NOT EXISTS routing_reason TEXT;
-- Beispiel-Werte: 
-- 'rule:developer+complex→premium'
-- 'budget_downgrade:80%→standard'
-- 'fallback:unknown_role→budget_default'
-- 'adr068_router:confidence=0.85'
```

---

### K-02: Discord-Rollen im Agent Coding Team — KRITISCH

**Problem**: Die Route-Tabelle enthält:
```
discord_status | trivial | gpt-4o-mini
discord_ask    | simple  | llama-3.1-8b
discord_chat   | moderate | gpt-4o
```

Discord-Handler (`discord/handlers.py`) sind **keine Agenten** im Agent Coding Team. Sie sind Eingabe-Kanäle. Das Agent Coding Team (ADR-100) besteht aus: Developer, Tester, Guardian, Tech Lead, Planner, Re-Engineer.

Discord-Commands sollten ihre Modell-Auswahl über einen separaten, einfacheren Mechanismus steuern — nicht durch den Agent Coding Team Router.

**Korrekte Abgrenzung**:
```python
# discord/handlers.py — eigener simpler Selector
DISCORD_COMMAND_MODELS = {
    "status":  "openai/gpt-4o-mini",
    "ask":     "meta-llama/llama-3.1-8b-instruct",
    "chat":    "openai/gpt-4o",
}
# Kein ADR-116 ModelSelector nötig für Discord
```

Discord-Routing → Discord-Config. Agent-Routing → ModelSelector/ADR-068.

---

### K-03: String-Input ohne Enum-Validierung — KRITISCH

**Problem**:
```python
sel = select_model(AgentRole.DEVELOPER, "complex")  # String!
```

Kein Enum für `TaskComplexityHint`. Wenn ein Caller `"Complex"` (Großschreibung), `"COMPLEX"` oder `"komplex"` übergibt → KeyError oder falsches Routing. Silent failure ist hier schlimmer als lauter Fehler.

**Korrektur**:
```python
class TaskComplexityHint(str, enum.Enum):
    TRIVIAL = "trivial"
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    ARCHITECTURAL = "architectural"
    
    @classmethod
    def _missing_(cls, value: object) -> "TaskComplexityHint":
        # Case-insensitive lookup + Warning
        if isinstance(value, str):
            for member in cls:
                if member.value == value.lower():
                    return member
        logger.warning("Unknown TaskComplexityHint '%s', falling back to MODERATE", value)
        return cls.MODERATE
```

---

## 3. Architektur-Empfehlung: Revised Design

### Korrekte Einordnung von ADR-116 in den ADR-Stack

```
                    ┌─────────────────────────────────┐
                    │   ADR-068 TaskRouter (LLM)      │
                    │   Confidence ≥ 0.70             │
                    │   + Feedback-Loop               │
                    │   + AuditStore                  │
                    └────────────┬────────────────────┘
                                 │ Confidence < 0.70
                                 │ ODER Budget ≥ 80%
                                 ▼
                    ┌─────────────────────────────────┐
                    │   ADR-116 RuleBasedRouter       │
                    │   Route-Tabelle aus DB          │◄── Neuer Beitrag
                    │   Budget-Check via llm_calls    │
                    │   Routing-Reason in llm_calls   │
                    └────────────┬────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────────────┐
                    │   llm_mcp /v1/chat (ADR-114)   │
                    │   OpenRouter                    │
                    └─────────────────────────────────┘
```

### Alternativ: ADR-116 als eigenständiger Budget-Guard-Layer

Falls das LLM-basierte Routing von ADR-068 zu langsam ist (1-2s Latenz), kann ADR-116 als **Pre-Filter vor ADR-068** positioniert werden:

```
Budget ≥ 80% → ModelSelector gibt Budget-Modell zurück (sofort, kein LLM-Call)
Budget < 80% → ADR-068 TaskRouter (volle LLM-Routing-Qualität)
```

**Trade-off**: Schneller, aber überschreibt ADR-068's Qualitäts-Feedback-Loop im Budget-Fall.

---

## 4. Gesamtbewertung

| Kriterium | Bewertung |
|-----------|-----------|
| Kern-Idee (Budget-aware Routing) | ✅ Richtig und sinnvoll |
| Verhältnis zu ADR-068 | ❌ Nicht definiert — paralleles System |
| Budget-Tracking | ❌ In-Memory nicht produktionstauglich |
| Route-Tabelle | ❌ Hardcodiert — Platform-Standard-Verstoß |
| Discord-Rollen im Agent-Router | ❌ Konzeptuell falsch |
| Enum-Validierung | ⚠️ Fehlt |
| Audit-Trail | ⚠️ Fehlt |

**Empfehlung**: ADR-116 überarbeiten als "Erweiterung von ADR-068 um Budget-aware Rule-Based Fallback". Blocker B-01 bis B-03 sind vor Implementierung zu beheben. Implementierungsplan in `ADR-116-implementation-plan.md`.
