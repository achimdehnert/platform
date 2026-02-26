---
status: accepted
date: 2026-02-26
implemented: 2026-02-26
decision-makers: Achim Dehnert
consulted: –
informed: –
supersedes: –
amends: ADR-084 (Model Registry), ADR-082 (LLM Tool Integration)
related: ADR-084, ADR-082, ADR-045, ADR-056, ADR-080, ADR-068
---

# ADR-089: bfagent-llm — LiteLLM-Backend + DB-driven Model-Routing

| Attribut       | Wert                                                                 |
|----------------|----------------------------------------------------------------------|
| **Status**     | **Accepted** (v4 — Phase 2 in progress)                             |
| **Scope**      | Platform-wide — AI Infrastructure                                    |
| **Repo**       | platform (`packages/bfagent-llm/`)                                   |
| **Erstellt**   | 2026-02-26                                                           |
| **Autor**      | Achim Dehnert                                                        |
| **Amends**     | ADR-084 (Model Registry), ADR-082 (LLM Tool Integration)            |
| **Relates to** | ADR-068 (Routing), ADR-045 (Secrets), ADR-056 (Multi-Tenancy), ADR-080 (Multi-Agent) |
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
bfagent-llm v1.0 (implementiert)
│
├── Django App: bfagent_llm.django_app    ← NEU: DB-driven für Django-Apps
│   ├── models.py
│   │   ├── LLMProvider         (Name, API-Key Env-Var, Base-URL, is_active)
│   │   ├── LLMModel            (Provider FK, Name, Max-Tokens, Cost, Capabilities)
│   │   ├── AIActionType        (tenant_id!, Code, Default-Model FK, Fallback FK)
│   │   └── AIUsageLog          (tenant_id!, Action, Model, User, Tokens, Cost)
│   ├── admin.py                (Django Admin Registration)
│   ├── service.py              (completion(), sync_completion(), completion_with_fallback())
│   ├── checks.py               (System checks: config validation)
│   ├── management/commands/
│   │   ├── init_llm_config.py  (Idempotent seed data)
│   │   └── check_llm_config.py (Configuration validation)
│   └── migrations/0001_initial.py
│
├── Core: bfagent_llm.adapters
│   ├── LiteLLMAdapter          ← NEU: Universal-Adapter via litellm
│   ├── OpenAILLMAdapter        (für MCP ohne DB)
│   ├── AnthropicLLMAdapter     (für MCP ohne DB)
│   ├── GroqLLMAdapter          (für MCP ohne DB)
│   ├── GatewayLLMAdapter       (für MCP ohne DB)
│   └── FallbackLLMAdapter
│
├── ResilientPromptService      (Retry + Circuit Breaker)
│
└── Protocols: LLMClientProtocol (Interface für DI)
```

### 2.1 Invarianten

1. **Multi-Tenancy (ADR-056):** `AIActionType` und `AIUsageLog` MÜSSEN `tenant_id` haben.
   `LLMProvider` und `LLMModel` sind globale Infrastruktur (kein `tenant_id`).
2. **Secrets (ADR-045):** `_get_api_key()` MUSS `read_secret()` nutzen
   (Priorität: `/run/secrets/<key_lower>` → `os.environ[KEY]` → Fehler).
3. **Kein stiller Fallback:** Wenn `AIActionType` kein `default_model` hat → `LLMConfigurationError`.
4. **Naming:** `AIActionType.code` MUSS `^[a-z][a-z0-9_]{2,49}$` matchen (snake_case).
5. **Idempotenz:** Management Commands nutzen `update_or_create()`, nie `create()`.
6. **DB-Tabellen:** Prefix `bfllm_` (bfllm_providers, bfllm_models, bfllm_action_types, bfllm_usage_logs).
7. **Explicit `app_label` (v3):** Jede `AppConfig` in einem reusable Django-Package
   MUSS ein explizites `label` setzen, das dem Package-Namen entspricht.
   Niemals den automatisch abgeleiteten Label verwenden.
   ```python
   # ✅ RICHTIG:
   class BfagentLlmConfig(AppConfig):
       name = "bfagent_llm.django_app"
       label = "bfagent_llm"  # explicit!

   # ❌ FALSCH: ohne label → Django leitet "django_app" ab
   class BfagentLlmConfig(AppConfig):
       name = "bfagent_llm.django_app"
       # label fehlt → app_label = "django_app" (generisch, fragil)
   ```
   **Begründung:** Ohne explizites Label erzeugt Django den Label aus dem
   letzten Modul-Segment. Bei `pkg.django_app` wird das `"django_app"` —
   generisch, kollidiert mit anderen Packages, verwirrt Entwickler UND
   AI-Agenten bei Migration-Dependencies.
8. **Explicit `related_name` (v3):** Jeder `ForeignKey` zu `AUTH_USER_MODEL`
   in einem reusable Package MUSS ein explizites `related_name` haben.
   Ohne `related_name` erzeugt Django identische Reverse-Accessors wenn
   die Consumer-App ein Model mit gleichem Namen hat (E304).
9. **Version-Bump bei Code-Änderungen (v4):** Jede Code-Änderung an einem
   veröffentlichten Package MUSS einen Version-Bump in `pyproject.toml`
   beinhalten. NIEMALS den gleichen Versions-String für geänderten Code
   verwenden. `pip wheel` und Docker-Build-Cache nutzen den Dateinamen
   (`pkg-X.Y.Z-py3-none-any.whl`) als Cache-Key — gleiche Version +
   geänderter Code = stale Wheel im Container.
   ```
   # ❌ FALSCH: Code ändern ohne Version-Bump
   # → pip/Docker liefert altes 1.0.0 Wheel aus Cache
   version = "1.0.0"  # Code geändert, aber Version nicht!

   # ✅ RICHTIG: Immer bumpen
   version = "1.0.1"  # Neuer Dateiname → kein Cache-Hit
   ```

### 2.2 Zwei Modi

**Modus A: Django-Apps (DB-driven)**

```python
# settings.py:
INSTALLED_APPS = [..., "bfagent_llm.django_app"]

# Service:
from bfagent_llm.django_app.service import completion
result = await completion(
    action_code="character_generation",
    messages=[{"role": "user", "content": prompt}],
    tenant_id=request.tenant_id,
)
```

**Modus B: MCP-Server (kein Django, kein DB)**

```python
from bfagent_llm import GroqLLMAdapter
adapter = GroqLLMAdapter(api_key=os.environ["GROQ_API_KEY"])
response = await adapter.complete(messages=messages, model="qwen/qwen3-32b", ...)
```

### 2.3 `litellm` Dependency-Management

- Version pinned: `litellm>=1.55,<1.60`
- Optionale Dependency: `pip install bfagent-llm[django]`
- Nur `litellm.acompletion()` und `litellm.completion_cost()` genutzt
- Langfrist-Exit: Service-API bleibt stabil falls LiteLLM ersetzt wird

---

## 3. Implementierungsplan

### Phase 1: bfagent-llm v1.0 ✅ DONE

- `bfagent_llm/django_app/` mit Models, Admin, Service, Checks, Migrations
- `LiteLLMAdapter` in adapters.py
- Management Commands: `init_llm_config`, `check_llm_config`
- pyproject.toml v1.0.0 mit `[django]` und `[litellm]` extras
- Tests: models, service, management commands

### Phase 2: travel-beat Migration 🔄 IN PROGRESS

1. ✅ `bfagent-llm[django]` in requirements.txt (PR #11 merged)
2. ✅ `bfagent_llm.django_app` in `TENANT_APPS`
3. ✅ DB-Migration: `0003_copy_to_bfllm` (data copy per tenant schema)
4. ✅ `llm_service.py` Adapter (bfagent-llm primary, LiteLLM fallback)
5. ✅ Fix: `app_label="bfagent_llm"` (Invariante 7)
6. ✅ Fix: `related_name="bfllm_usage_logs"` (Invariante 8)
7. ✅ Fix: Version-Bump 1.0.0 → 1.0.1 (Invariante 9)
8. 🔄 Deploy + Migrate auf Server
9. ⏳ Cleanup: `llm_client.py`, `llm_providers.py` entfernen

### Phase 3: Weitere Apps (pending)

- weltenhub, bfagent, risk-hub, 137-hub

### Phase 4: Cleanup (pending)

- creative_services.core.llm_client deprecated
- AIUsageLog Retention: cleanup_usage_logs --days=90

---

## 4. Rejected Alternatives

1. **LiteLLM ersetzen durch custom Adapter** — 100+ Provider-Support unverhältnismäßig
2. **travel-beat llm_service.py direkt übernehmen** — verletzt zentrale-Schnittstelle-Regel
3. **LiteLLM ohne DB-Models** — kein zero-code Model-Swap möglich
4. **Globaler Default-Fallback** — stiller Fallback ist gefährlich
5. **tenant_id auf LLMProvider/LLMModel** — globale Infrastruktur braucht kein tenant_id

---

## 5. Review-Protokoll

| # | Befund | Risiko | Status |
|---|--------|--------|--------|
| R-01 | tenant_id fehlt | KRITISCH | ✅ v1 |
| R-02 | litellm Dependency | HOCH | ✅ v1 |
| R-03 | Stiller Fallback | MITTEL | ✅ v1 |
| R-04 | DB-Tabellennamen | MITTEL | ✅ v1 |
| R-05 | ADR-045 Secrets | MITTEL | ✅ v1 |
| R-06 | Code Naming | NIEDRIG | ✅ v1 |
| R-07 | Index-Strategie | MITTEL | ✅ v1 |
| R-08 | Idempotenz | MITTEL | ✅ v1 |
| R-09 | App-Label generisch ("django_app") | **HOCH** | ✅ v3 — `label="bfagent_llm"` + Invariante 7 |
| R-10 | Rollback-Plan | HOCH | ✅ v1 |
| R-11 | ForeignKey ohne related_name | HOCH | ✅ v3 — `related_name="bfllm_usage_logs"` + Invariante 8 |
| R-12 | Wheel ohne Version-Bump deployed | **HOCH** | ✅ v4 — Invariante 9: Pflicht-Bump bei Code-Änderung |

---

## 6. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-02-26 | Achim Dehnert | v0: Initial Draft |
| 2026-02-26 | Achim Dehnert | v1: Review-Fixes R-01 bis R-10 |
| 2026-02-26 | Achim Dehnert | v2: Status → Accepted. Phase 1 implementiert (bfagent-llm v1.0.0) |
| 2026-02-26 | Achim Dehnert | v3: Invarianten 7+8 (explicit app_label + related_name). R-09 NIEDRIG→HOCH. R-11 neu. |
| 2026-02-26 | Achim Dehnert | v4: Invariante 9 (Pflicht-Version-Bump). R-12 neu. Bump 1.0.0→1.0.1. |
