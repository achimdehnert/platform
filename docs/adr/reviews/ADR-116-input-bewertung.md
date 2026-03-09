# ADR-116 Input-Bewertung: Review + Implementierungsplan + Use-Case-Ergänzungen

**Reviewer**: Cascade  
**Datum**: 2026-03-09  
**Basis**: ADR-116-review.md (Blocker B-01/B-02/B-03 + Kritisch K-01/K-02/K-03)  
**Input-Dateien**: 8 Dateien in `docs/adr/inputs/dynamic router/`  
**Use-Cases**: UC-SE-2 (Multi-Agent Code Review), UC-SE-3 (CI/CD Automation), UC-SE-5 (Security Audit)  

---

## 1. Gesamturteil

| Aspekt | Bewertung |
|--------|-----------|
| **Blocker-Behebung (B-01/B-02/B-03)** | ✅ Vollständig behoben |
| **Kritisch-Behebung (K-01/K-02/K-03)** | ✅ Vollständig behoben |
| **Code-Qualität (rule_based_router.py)** | ✅ Produktionsreif |
| **Budget-Tracker (budget_tracker.py)** | ✅ Korrekt, Redis-Fallback vorhanden |
| **DB-Modell (model_route_config_model.py)** | ⚠️ 1 kritischer Bug (TIMESTAMPTZ) |
| **Migration (0043_model_route_config.py)** | ✅ Idempotent, korrekt |
| **Discord-Config (discord_config.py)** | ✅ Sauber abgegrenzt |
| **ADR-068 Patch (router_budget_guard_patch.py)** | ⚠️ DI-Pattern unvollständig |
| **Test-Suite (test_rule_based_router.py)** | ✅ Gut, 2 Lücken identifiziert |
| **UC-SE-2/3/5 Abdeckung** | ⚠️ 2 von 3 abgedeckt — UC-SE-5 braucht Erweiterung |

**Empfehlung**: ✅ **FREIGABE mit 3 Minor-Fixes** — kein erneuter Blocker-Review nötig

---

## 2. Blocker-Behebung — Verifikation

### B-01: Paralleles Routing-System ✅ BEHOBEN

`router_budget_guard_patch.py` zeigt korrekte Architektur:

```
Budget ≥ 80% → RuleBasedBudgetRouter (Pre-Filter, kein LLM-Call)
Budget < 80% → ADR-068 TaskRouter._llm_route() (unverändert)
```

`TaskRouterBudgetGuardMixin` erweitert `TaskRouter` — kein paralleles System.
Feature-Flag `BUDGET_GUARD_ENABLED=false` für sicheres Rollout. ✅

### B-02: In-Memory Budget-Tracking ✅ BEHOBEN

`budget_tracker.py` aggregiert `SUM(cost_usd)` aus `llm_calls` (UTC-Datumsabschneidung):

```sql
WHERE created_at >= date_trunc('day', NOW() AT TIME ZONE 'UTC')
AND deleted_at IS NULL
```

Multi-Container-safe ✅ — alle Instanzen lesen dieselbe DB.  
Redis-Cache (60s TTL) ✅ — kein DB-Hit bei jedem Routing-Call.  
Tages-Reset automatisch über UTC-Datumstrunkierung ✅ — kein Cron-Job nötig.

### B-03: Hardcodierte Route-Tabelle ✅ BEHOBEN

`model_route_config_model.py`: `ModelRouteConfig`-Tabelle in PostgreSQL.  
Migration 0043 mit Seed-Daten via `ON CONFLICT DO NOTHING` ✅.  
Route-Cache (5min TTL) in `RuleBasedBudgetRouter._route_cache` ✅.  
`invalidate_cache()` Methode für sofortige Änderungen ✅.

---

## 3. Kritisch-Behebung — Verifikation

### K-01: Audit-Trail ✅ BEHOBEN

`routing_reason` in `ModelSelection` durchgängig propagiert.  
Format lesbar und strukturiert — Beispiele aus Tests bestätigt:
- `"rule:developer+complex→premium|budget=50.0%"`
- `"budget_downgrade:85.0%|normal=anthropic/claude-3.5-sonnet|downgrade=openai/gpt-4o"`
- `"emergency:budget=105.0%>$10.00|role=tech_lead"`
- `"fallback:no_route|role=new_unknown_role|complexity=complex"`

Migration 0043 fügt `llm_calls.routing_reason TEXT` hinzu ✅.

### K-02: Discord-Rollen ✅ BEHOBEN

`AgentRole`-Enum enthält keine Discord-Rollen:
```python
DEVELOPER | TESTER | GUARDIAN | TECH_LEAD | PLANNER | RE_ENGINEER
```

`discord_config.py` ist vollständig unabhängig — eigene `DiscordModelConfig`,  
keine Imports aus `rule_based_router.py` oder `model_route_config.py` ✅.  
Test `test_discord_role_not_routable` verifiziert Fallback-Verhalten ✅.

### K-03: Enum-Validierung ✅ BEHOBEN

`TaskComplexityHint._missing_()` — case-insensitive + Fallback MODERATE ✅.  
`AgentRole._missing_()` — case-insensitive + None bei unbekannt ✅.  
`from_adr068_complexity()` — explizites Mapping mit aliases (low/medium/high) ✅.

---

## 4. Verbleibende Befunde (Minor)

### M-1: TIMESTAMPTZ Import-Bug in model_route_config_model.py — FIX ERFORDERLICH

```python
# AKTUELL (Zeile 23):
from sqlalchemy.dialects.postgresql import TIMESTAMPTZ, UUID
```

`TIMESTAMPTZ` ist kein valider SQLAlchemy-Import — gleiches Problem wie in ADR-115 (bereits behoben in `llm_call.py`).

**Fix**:
```python
from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import UUID
# Verwendung: DateTime(timezone=True) statt TIMESTAMPTZ
```

### M-2: DI-Pattern in router_budget_guard_patch.py — MINOR

```python
# Zeile 86 — direkte Instantiierung statt DI:
router = RuleBasedBudgetRouter(budget_tracker)
```

Kommentar sagt "in Produktion via DI" — aber kein konkretes DI-Konzept.  
**Empfehlung**: `RuleBasedBudgetRouter` als FastAPI-Dependency via `lifespan` registrieren (analog zu `BudgetTracker`). Im Implementierungsplan dokumentieren.

### M-3: UniqueConstraint in model_route_config_model.py — FIX ERFORDERLICH

```python
# Zeile 198-205 — UniqueConstraint mit postgresql_where:
UniqueConstraint(
    "agent_role", "complexity_hint",
    name="uq_model_route_configs_active",
    postgresql_where="deleted_at IS NULL AND is_active = TRUE",  # NICHT UNTERSTÜTZT
)
```

`UniqueConstraint` akzeptiert kein `postgresql_where` — das muss ein `Index` mit `unique=True` sein.  
Migration 0043 macht es **korrekt** als SQL-Index — aber das SQLAlchemy-Model ist inkonsistent und wirft bei `alembic autogenerate` Fehler.

**Fix** (wie in `llm_call.py` bereits korrekt gelöst):
```python
__table_args__ = (
    Index(
        "uq_model_route_configs_active",
        "agent_role", "complexity_hint",
        unique=True,
        postgresql_where="deleted_at IS NULL AND is_active = TRUE",
    ),
    Index("model_route_configs_role_idx", "agent_role"),
)
```

---

## 5. Use-Case-Bewertung: UC-SE-2, UC-SE-3, UC-SE-5

### UC-SE-2: Multi-Agent Code Review ✅ GUT ABGEDECKT

**Anforderung**: Mehrere Agenten (Developer, Guardian, Tech Lead) reviewen Code parallel.  
Jeder Agent braucht ein rollenspezifisches Modell — Guardian strenger als Developer.

**Abdeckung durch ADR-116**:
- `guardian + complex → anthropic/claude-3.5-sonnet` ✅ (Seed-Daten)
- `guardian + moderate → openai/gpt-4o` ✅
- `tech_lead + architectural → anthropic/claude-3.5-sonnet` ✅
- Budget-Downgrade schont Budget bei parallelen Review-Calls ✅
- `routing_reason` unterscheidet welcher Agent welches Modell nutzte ✅

**Fehlende Route** (Ergänzung empfohlen):
```python
# Guardian trivial (z.B. Whitespace/Format-Checks) — fehlt in Seed-Daten
{"agent_role": "guardian", "complexity_hint": "trivial",
 "model": "openai/gpt-4o-mini", "tier": "budget", "provider": "openai",
 "budget_model": "meta-llama/llama-3.1-8b-instruct", "budget_tier": "local"}
```

**Bewertung**: ✅ Strukturell korrekt — 1 fehlende Route im Seed.

---

### UC-SE-3: CI/CD & DevOps Automation ✅ ABGEDECKT

**Anforderung**: Automatisierte CI/CD-Tasks (Deploy-Entscheidungen, Infra-Checks).  
Typische Agenten: Planner (Planung), Developer (Skripte), Guardian (Config-Validation).

**Abdeckung durch ADR-116**:
- `planner + complex → anthropic/claude-3.5-sonnet` ✅
- Feature-Flag `BUDGET_GUARD_ENABLED` ermöglicht separates Routing für CI-Tasks ✅
- Budget-Tracker verhindert CI/CD-Loops die Budget sprengen ✅
- `routing_reason` in llm_calls erlaubt CI/CD-spezifisches Grafana-Panel ✅

**Fehlendes Konzept**: CI/CD-Tasks laufen oft nachts (Budget schon aufgebraucht).  
Budget-Reset um Mitternacht UTC ist automatisch (✅), aber:

> **Empfehlung**: `task_id` aus CI/CD-Workflow-Run-ID befüllen → Grafana zeigt Kosten pro Pipeline-Run.

**Bewertung**: ✅ Strukturell korrekt — `task_id` Nutzungskonvention dokumentieren.

---

### UC-SE-5: Security & Dependency Audit ⚠️ PARTIELL — ERWEITERUNG NÖTIG

**Anforderung**: Automatisierte Security-Scans (Dependency-Vulnerabilities, CVE-Matching,  
SBOM-Analyse). Typisch: Guardian-Agent + dedizierter Security-Analyst-Modus.

**Problem**: ADR-116 kennt kein Security-spezifisches Routing. Der `guardian`-Agent  
wird für Code-Review UND Security-Audit verwendet — gleiche Modelle, obwohl  
Security-Audits fundamental andere Anforderungen haben:

| Aspekt | Code Review | Security Audit |
|--------|------------|----------------|
| Kontext | Code-Diff (kurz) | SBOM + CVE-DB + Deps (lang) |
| Modell | Claude 3.5 Sonnet | Claude 3.5 Sonnet **mit erweitertem Kontext** |
| Cost | Standard | Höher (mehr Tokens) |
| Priorität | Budget-Downgrade akzeptabel | Downgrade **riskant** — CVE wird übersehen |

**Konkrete Lücke**: Im Budget-Downgrade-Modus würde ein Security-Audit auf  
`gpt-4o-mini` downgegradet — das ist sicherheitskritisch falsch.

**Empfohlene Erweiterung** — 2 Optionen:

#### Option A: Neue AgentRole `SECURITY_AUDITOR` (sauber, empfohlen)

```python
class AgentRole(str, enum.Enum):
    ...
    SECURITY_AUDITOR = "security_auditor"  # NEU
```

Seed-Daten:
```python
{"agent_role": "security_auditor", "complexity_hint": "moderate",
 "model": "anthropic/claude-3.5-sonnet", "tier": "premium", "provider": "anthropic",
 "budget_model": "anthropic/claude-3.5-sonnet",  # Kein Downgrade!
 "budget_tier": "premium"},
{"agent_role": "security_auditor", "complexity_hint": "complex",
 "model": "anthropic/claude-3.5-sonnet", "tier": "premium", "provider": "anthropic",
 "budget_model": "anthropic/claude-3.5-sonnet",  # Kein Downgrade!
 "budget_tier": "premium"},
```

Vorteil: `budget_model == model` → Security-Audits werden nie downgegradet, auch bei 80%+ Budget.

#### Option B: `no_budget_downgrade` Flag auf ModelRouteConfig

```python
# model_route_config.py — neues Feld:
no_budget_downgrade: Mapped[bool] = mapped_column(
    Boolean, nullable=False, default=False,
    comment="True: dieser Route wird nie downgegradet (Security, Compliance)"
)
```

In `rule_based_router.py`:
```python
if effective_budget.mode == BudgetMode.COST_SENSITIVE and route.budget_model \
        and not route.no_budget_downgrade:
    # Downgrade
```

Vorteil: Keine neue Enum-Rolle nötig — flexibel pro Route konfigurierbar.

**Empfehlung**: Option A für UC-SE-5 — klare semantische Abgrenzung.  
Option B als generisches Feature ergänzend sinnvoll.

---

## 6. Test-Lücken

Bestehende Tests in `test_rule_based_router.py` decken alle Hauptpfade ab.  
2 fehlende Testfälle:

### T-01: Cache-Invalidierung nach Budget-Threshold-Wechsel

```python
@pytest.mark.asyncio
async def test_cache_stale_does_not_use_old_budget_mode():
    """Nach 60s Redis-TTL muss Budget neu abgefragt werden."""
    # Test dass alter Cache-Wert nicht zu falschen Routing-Entscheidungen führt
```

### T-02: no_budget_downgrade Flag (falls Option B implementiert)

```python
@pytest.mark.asyncio
async def test_security_auditor_never_downgraded():
    """security_auditor bleibt bei premium auch bei 85% Budget."""
```

---

## 7. Implementierungsreihenfolge (empfohlen)

```
Tag 1:
  ① Fix TIMESTAMPTZ → DateTime(timezone=True) in model_route_config_model.py
  ② Fix UniqueConstraint → Index(unique=True) in model_route_config_model.py
  ③ Migration 0043 deployen (idempotent, backward-compatible)

Tag 2:
  ④ BudgetTracker + RuleBasedBudgetRouter deployen
  ⑤ Discord-Config deployen (handlers.py anpassen)
  ⑥ router.py + TaskRouterBudgetGuardMixin integrieren (BUDGET_GUARD_ENABLED=false)

Tag 3:
  ⑦ BUDGET_GUARD_ENABLED=true setzen (nach Monitoring-Check)
  ⑧ UC-SE-5: security_auditor AgentRole + Seed-Daten hinzufügen
  ⑨ Grafana-Panel: routing_reason Verteilung (ADR-115 Dashboard ergänzen)
```

---

## 8. Bewertungsmatrix

| Befund aus Review | Input-Dateien | Status |
|---|---|---|
| B-01: Paralleles System | `router_budget_guard_patch.py` | ✅ Behoben — Mixin-Pattern |
| B-02: In-Memory Budget | `budget_tracker.py` | ✅ Behoben — PostgreSQL+Redis |
| B-03: Hardcodierte Routes | `model_route_config_model.py` + `0043_model_route_config.py` | ✅ Behoben — DB-backed |
| K-01: Kein Audit-Trail | `rule_based_router.py` (routing_reason) | ✅ Behoben |
| K-02: Discord im Router | `discord_config.py` | ✅ Behoben — eigene Config |
| K-03: String-Input | `model_route_config_model.py` (_missing_) | ✅ Behoben |
| H-01: Budget-Hysterese | nicht explizit adressiert | ⚠️ Redis-TTL 60s ist implizite Hysterese |
| H-02: _map_task_complexity | `from_adr068_complexity()` | ✅ Behoben — explizites Mapping |
| H-03: Kein Entscheidungs-Model | routing_reason in llm_calls | ✅ Ausreichend |
| H-04: KeyError bei unbekannter Rolle | Fallback-Kette in router | ✅ Behoben |
| M-01: Budget-Reset | UTC-Datumstrunkierung in SQL | ✅ Behoben — automatisch |
| M-02: Kostenangaben $/1K vs $/1M | nicht adressiert | ℹ️ Kein Code-Impact |
| M-03: Keine Tests | `test_rule_based_router.py` | ✅ Behoben (367 Zeilen) |
| M-04: Fehlende Parameter | select() hat tenant_id + task_id | ✅ Behoben |
| **Neu: TIMESTAMPTZ-Bug** | `model_route_config_model.py` Z.23 | ❌ Fix erforderlich |
| **Neu: UniqueConstraint-Bug** | `model_route_config_model.py` Z.198 | ❌ Fix erforderlich |
| **Neu: UC-SE-5 Security** | Route-Tabelle fehlt no-downgrade | ⚠️ Erweiterung empfohlen |

---

## 9. Fazit

Die Input-Dateien beheben alle 3 Blocker und alle 3 kritischen Befunde des Reviews korrekt.  
Der Implementierungsplan ist strukturell solide und backward-compatible.

**Vor Deployment zwingend fixen**:
1. `TIMESTAMPTZ` → `DateTime(timezone=True)` in `model_route_config_model.py`
2. `UniqueConstraint(postgresql_where=...)` → `Index(unique=True, postgresql_where=...)` in `model_route_config_model.py`

**Empfohlene Erweiterung** (UC-SE-5):
3. `AgentRole.SECURITY_AUDITOR` mit `budget_model == model` (kein Downgrade für Security-Audits)

Nach diesen 3 Fixes: **ADR-116 v2.0 kann als ACCEPTED deployt werden.**
