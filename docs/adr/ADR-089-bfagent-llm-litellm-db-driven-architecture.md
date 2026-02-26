---
status: proposed
date: 2026-02-26
decision-makers: Achim Dehnert
consulted: –
informed: –
supersedes: –
amends: ADR-084 (Model Registry), ADR-082 (LLM Tool Integration)
related: ADR-084, ADR-082, ADR-045, ADR-080, ADR-068
---

# ADR-089: bfagent-llm — LiteLLM-Backend + DB-driven Model-Routing

| Attribut       | Wert                                                                 |
|----------------|----------------------------------------------------------------------|
| **Status**     | Proposed                                                             |
| **Scope**      | Platform-wide — AI Infrastructure                                    |
| **Repo**       | platform (`packages/bfagent-llm/`)                                   |
| **Erstellt**   | 2026-02-26                                                           |
| **Autor**      | Achim Dehnert                                                        |
| **Amends**     | ADR-084 (Model Registry), ADR-082 (LLM Tool Integration)            |
| **Relates to** | ADR-068 (Routing), ADR-045 (Secrets), ADR-080 (Multi-Agent)         |
| **Tracking**   | [platform#9](https://github.com/achimdehnert/platform/issues/9)     |

---

## 1. Context

### 1.1 Ist-Zustand (2026-02-26)

`bfagent-llm` (v0.2.0) ist das zentrale LLM-Package mit eigenen Adaptern:

```
bfagent-llm (aktuell)
├── OpenAILLMAdapter      — custom httpx → OpenAI
├── AnthropicLLMAdapter   — custom httpx → Anthropic
├── GroqLLMAdapter        — custom httpx → Groq (NEU, ADR-084 v3)
├── GatewayLLMAdapter     — custom httpx → BFAgent Gateway
├── FallbackLLMAdapter    — Provider-Chain
├── ResilientPromptService — Retry, Circuit Breaker, Tier-Fallback
└── TierConfig            — Hardcoded Tier-Konfiguration im Code
```

### 1.2 Problem

Parallel dazu existiert in `travel-beat` (und identisch in `bfagent`, `weltenhub`)
ein **überlegenes Muster**:

```
travel-beat/apps/ai_services/ (aktuell)
├── llm_service.py    — LiteLLM-Backend (100+ Provider, zero custom code)
├── models.py         — DB-Models (LLMProvider, LLMModel, AIActionType, AIUsageLog)
├── admin.py          — Django Admin UI für Model-Config
├── llm_client.py     — LEGACY: raw requests (7 Provider-Handler) → zu entfernen
└── llm_providers.py  — LEGACY: Provider-Handler → zu entfernen
```

### 1.3 Vergleich

| Kriterium | bfagent-llm (custom) | travel-beat (LiteLLM + DB) |
|-----------|---------------------|---------------------------|
| Provider-Abdeckung | 4 custom Adapter | **100+ Provider** via LiteLLM |
| Neuen Provider hinzufügen | Code schreiben + deployen | **DB-Eintrag im Admin** |
| Model-Routing | `TierConfig` hardcoded | **`AIActionType` → `LLMModel` → `LLMProvider`** in DB |
| Fallback | `FallbackLLMAdapter` (Code) | **Per-Action Fallback-Model** in DB |
| Usage Tracking | Budget im Adapter (Memory) | **`AIUsageLog`** in DB, querybar |
| Cost Tracking | Per-Tier Schätzung | **Per-Model Cost** (input/output per 1M tokens) |
| Resilienz | Retry + Circuit Breaker ✅ | LiteLLM Retries (kein Circuit Breaker) |
| Dependencies | Leichtgewichtig | `litellm` (heavy, aber battle-tested) |

**Fazit:** Das travel-beat-Modell ist in den Kernpunkten überlegen:
- DB-driven = zero-code Model-Swaps
- LiteLLM = 100+ Provider ohne custom Adapter
- Per-Action Routing = verschiedene Tasks nutzen verschiedene Models

---

## 2. Decision

### bfagent-llm v1.0 übernimmt LiteLLM als Backend + DB-Models

```
bfagent-llm v1.0 (Ziel-Architektur)
│
├── Django App: bfagent_llm.django        ← NEU: DB-driven für Django-Apps
│   ├── models.py
│   │   ├── LLMProvider         (Name, API-Key Env-Var, Base-URL, is_active)
│   │   ├── LLMModel            (Provider FK, Name, Max-Tokens, Cost, Capabilities)
│   │   ├── AIActionType        (Code, Default-Model FK, Fallback FK, Temperature)
│   │   └── AIUsageLog          (Action, Model, User, Tokens, Cost, Latency)
│   ├── admin.py                (Django Admin Registration)
│   ├── service.py              (completion(), sync_completion(), completion_with_fallback())
│   └── migrations/
│
├── Core: bfagent_llm.adapters            ← BEHALTEN: Für MCP-Server ohne Django/DB
│   ├── LiteLLMAdapter          ← NEU: Universal-Adapter via litellm
│   ├── OpenAILLMAdapter        (Legacy, für MCP ohne DB)
│   ├── AnthropicLLMAdapter     (Legacy, für MCP ohne DB)
│   ├── GroqLLMAdapter          (Legacy, für MCP ohne DB)
│   ├── GatewayLLMAdapter       (Legacy, für MCP ohne DB)
│   └── FallbackLLMAdapter      (Legacy, für MCP ohne DB)
│
├── ResilientPromptService      ← BEHALTEN: Retry + Circuit Breaker
│
└── Protocols: LLMClientProtocol ← BEHALTEN: Interface für DI
```

### 2.1 Zwei Modi

**Modus A: Django-Apps (DB-driven)**

Für bfagent, travel-beat, weltenhub, risk-hub, 137-hub, pptx-hub:

```python
# In settings.py:
INSTALLED_APPS = [
    ...
    "bfagent_llm.django",
]

# In jedem Service:
from bfagent_llm.django.service import completion

result = await completion(
    action_code="character_generation",
    messages=[{"role": "user", "content": prompt}],
)
# → Model-Routing, Fallback, Cost-Tracking automatisch via DB
```

Neue Models hinzufügen:
1. Django Admin → LLM Providers → "Add Provider"
2. Django Admin → LLM Models → "Add Model"
3. Django Admin → AI Action Types → default_model zuweisen
4. **Kein Code, kein Deploy, kein Neustart**

**Modus B: MCP-Server (kein Django, kein DB)**

Für orchestrator_mcp, deployment_mcp, llm_mcp (laufen in WSL):

```python
from bfagent_llm import GroqLLMAdapter, OpenAILLMAdapter

adapter = GroqLLMAdapter(api_key=os.environ["GROQ_API_KEY"])
response = await adapter.complete(
    messages=messages,
    model="qwen/qwen3-32b",
)
```

### 2.2 DB-Models (aus travel-beat extrahiert + generalisiert)

```python
class LLMProvider(models.Model):
    name = CharField(max_length=50, unique=True)       # "openai", "anthropic", "groq"
    display_name = CharField(max_length=100)
    api_key_env_var = CharField(max_length=100)         # "OPENAI_API_KEY"
    base_url = URLField(blank=True)                     # Für custom endpoints
    is_active = BooleanField(default=True)

class LLMModel(models.Model):
    provider = ForeignKey(LLMProvider)
    name = CharField(max_length=100)                    # "gpt-4o", "claude-sonnet-4"
    display_name = CharField(max_length=100)
    max_tokens = IntegerField(default=4096)
    supports_vision = BooleanField(default=False)
    supports_tools = BooleanField(default=True)
    input_cost_per_million = DecimalField()             # Cost-Tracking
    output_cost_per_million = DecimalField()
    is_active = BooleanField(default=True)
    is_default = BooleanField(default=False)

class AIActionType(models.Model):
    code = CharField(max_length=50, unique=True)        # Frei wählbar pro App!
    name = CharField(max_length=100)
    default_model = ForeignKey(LLMModel, null=True)     # Per-Action Routing
    fallback_model = ForeignKey(LLMModel, null=True)    # Auto-Fallback
    max_tokens = IntegerField(default=2000)
    temperature = FloatField(default=0.7)
    is_active = BooleanField(default=True)

class AIUsageLog(models.Model):
    action_type = ForeignKey(AIActionType, null=True)
    model_used = ForeignKey(LLMModel, null=True)
    user = ForeignKey(AUTH_USER_MODEL, null=True)
    input_tokens = IntegerField(default=0)
    output_tokens = IntegerField(default=0)
    estimated_cost = DecimalField()                     # Auto-berechnet
    latency_ms = IntegerField(default=0)
    success = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)
```

**Wichtige Änderung vs. travel-beat:** `AIActionType.code` ist ein **freies CharField** (keine `choices`).
Jede App definiert eigene Action-Codes:
- travel-beat: `location_profile`, `character_generation`, `scene_analysis`
- risk-hub: `hazard_analysis`, `substance_risk`
- 137-hub: `supersystem_chat`
- bfagent: `code_generation`, `code_review`

### 2.3 Service-Funktion (LiteLLM als Backend)

```python
async def completion(
    action_code: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    user=None,
    **overrides,
) -> LLMResult:
    """DB-driven completion via LiteLLM.

    1. AIActionType[action_code] → LLMModel → LLMProvider (DB-Lookup)
    2. _build_model_string() → "provider/model" (LiteLLM-Format)
    3. litellm.acompletion() → Unified response
    4. AIUsageLog.create() → Cost + Usage tracking
    """
```

---

## 3. Konsequenzen

### 3.1 Was sich ändert

| Vorher | Nachher |
|--------|---------|
| Neuer Provider → Custom Adapter coden | Neuer Provider → DB-Eintrag im Admin |
| Model-Swap → Code ändern + deployen | Model-Swap → Admin-UI, sofort wirksam |
| 4 Provider (OpenAI, Anthropic, Groq, Gateway) | 100+ Provider via LiteLLM |
| TierConfig hardcoded | AIActionType per-action in DB |
| Budget-Tracking im Memory | AIUsageLog in DB, querybar |
| Jede App eigener LLM-Code (~41KB travel-beat) | Shared Django App aus bfagent-llm |

### 3.2 Was bleibt

- `bfagent-llm` bleibt **die einzige zentrale Schnittstelle** (Regel aus platform#9)
- `LLMClientProtocol` bleibt als Interface
- `ResilientPromptService` bleibt (Retry + Circuit Breaker)
- Legacy Adapter bleiben für MCP-Server (kein Django)
- API-Keys via ADR-045 (Secrets Management)

### 3.3 Was entfällt

- `travel-beat/apps/ai_services/llm_client.py` — ersetzt durch bfagent-llm
- `travel-beat/apps/ai_services/llm_providers.py` — ersetzt durch LiteLLM
- Identische Kopien in `bfagent`, `weltenhub` — alle nutzen bfagent-llm
- `risk-hub/src/ai_analysis/llm_client.py` — ersetzt durch bfagent-llm
- `creative_services.core.llm_client` — deprecated

---

## 4. Implementierungsplan

### Phase 1: bfagent-llm v1.0 Package (1-2 Tage)

1. `bfagent_llm/django/` Subpackage erstellen (Django App)
2. DB-Models aus travel-beat extrahieren + generalisieren
3. `service.py` mit `completion()`, `sync_completion()`, `completion_with_fallback()`
4. `LiteLLMAdapter` als neuer Core-Adapter
5. `litellm` als optionale Dependency (`pip install bfagent-llm[django]`)
6. Management Command: `init_llm_config` (Seed-Daten)
7. Tests

### Phase 2: travel-beat Migration (1 Tag)

1. `bfagent-llm[django]` in requirements.txt
2. `INSTALLED_APPS += ["bfagent_llm.django"]`
3. Migration: bestehende `ai_llm_*` Tabellen → bfagent-llm Tabellen (oder Alias)
4. `llm_service.py` → `from bfagent_llm.django.service import completion`
5. `llm_client.py` + `llm_providers.py` entfernen
6. `services.py` creative_services-Import entfernen

### Phase 3: Weitere Apps (je 0.5 Tag)

- **weltenhub**: Identisch zu travel-beat (gleiche SHA)
- **bfagent**: `apps/ai_services/llm_service.py` ersetzen
- **risk-hub**: `src/ai_analysis/llm_client.py` ersetzen
- **137-hub**: `supersystem/llm/providers/` ersetzen

### Phase 4: Cleanup

- `creative_services.core.llm_client` → deprecated markieren
- Legacy Adapter in bfagent-llm als `bfagent_llm.adapters` behalten (MCP-Server)
- Issue platform#9 schließen

---

## 5. Rejected Alternatives

### 5.1 LiteLLM komplett ersetzen durch bfagent-llm Adapter

Abgelehnt: LiteLLM deckt 100+ Provider ab. Eigene Adapter für jeden Provider
zu maintainen ist unverhältnismäßiger Aufwand.

### 5.2 travel-beat llm_service.py als Standard übernehmen (ohne bfagent-llm)

Abgelehnt: Verletzt die zentrale-Schnittstelle-Regel (platform#9).
Code wäre in 5 Repos dupliziert statt in einem shared Package.

### 5.3 Nur LiteLLM ohne DB-Models

Abgelehnt: Ohne DB-Models müssten Provider/Model-Konfigurationen
im Code stehen. DB-driven Config ist der Hauptvorteil.

---

## 6. Open Questions

1. **DB-Migration**: Sollen bestehende `ai_llm_*` Tabellen in travel-beat
   umbenannt werden oder per DB-View/Alias gemapped?
2. **Multi-Tenancy**: Soll `AIActionType` tenant-spezifisch sein
   (verschiedene Tenants nutzen verschiedene Models)?
3. **ResilientPromptService + LiteLLM**: LiteLLM hat eigene Retries.
   Soll ResilientPromptService den Circuit Breaker behalten und LiteLLM-Retries deaktivieren?

---

## 7. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-02-26 | Achim Dehnert | v0: Initial Draft — LiteLLM + DB-Models Architektur |
