---
id: ADR-084
title: "Model Registry — Dynamisches LLM-Modell-Routing mit datenbankgestützter Tier-Verwaltung"
status: accepted
decision_date: 2026-02-25
amended: 2026-05-12
deciders:
  - Achim Dehnert
consulted: []
informed: []
supersedes: []
amends:
  - ADR-068
related:
  - ADR-068
  - ADR-082
  - ADR-045
  - ADR-080
implementation_status: implemented
implementation_evidence:
  - "aifw: LLMModel + LLMProvider Django Models in aifw/models.py (Migration 001)"
  - "DB-driven routing via aifw.sync_completion(action_code=...) — action_code → LLMModel Lookup"
  - "v3 Amendment: 9 Groq-Modelle via Migration 002_add_groq_provider.sql (registry_mcp)"
  - "TierRules in model_registry_updater.py mit budget/standard/premium Mapping"
  - "Alle Consumer-Repos (pptx-hub, travel-beat, weltenhub, ...) nutzen action_code statt hardcoded model strings"
---

# ADR-084: Model Registry — Dynamisches LLM-Modell-Routing mit datenbankgestützter Tier-Verwaltung

## Context

ADR-068 hat ein Tier-basiertes Adaptive Model Routing eingeführt (`budget` /
`standard` / `premium`). Die Tier-Zuordnung war jedoch **in Code-Konstanten
hardcodiert** (`llm_config.py`) — jeder Modell-Wechsel erforderte einen
Code-Change + Deployment aller betroffenen Services.

### Konkrete Probleme vor diesem ADR

| Problem | Konsequenz |
|---|---|
| Modell-Namen als Code-Konstanten | Provider-Deprecation erzwingt Deploy in jedem Repo |
| Kein zentrales Cost-Control | Jedes Repo entschied selbst über Modell-Qualität |
| Kein Usage-Tracking pro Action | Kein Überblick über Token-Verbrauch pro Feature |
| Provider-Ausfall erfordert Code-Change | Kein Fallback ohne Deploy |
| A/B-Testing von Modellen unmöglich | Keine per-Tenant / per-Action Varianten |

### Auslöser

Mit dem Wachstum auf 15+ Django-Apps und 30+ LLM-Calls entstand der Bedarf
nach einer **zentralen, zur Laufzeit änderbaren** Routing-Tabelle. `iil-aifw`
ist der natürliche Ort dafür — er ist bereits der einzige LLM-Einstiegspunkt
per Platform-Policy (ADR-082).

## Decision

**PostgreSQL-gestützte Model Registry in `aifw` via Django ORM**, mit
DB-driven Routing über `action_code`-Lookup.

### D1: Django ORM als Storage

`LLMModel` + `LLMProvider` als Django-Models in `aifw`. Kein YAML, kein
JSON-File: die DB ist Single Source of Truth. Begründung: PostgreSQL ist
ohnehin Pflicht-Dep (ADR-094), Django-ORM-Migrations sind auditierbar,
Admin-UI ist kostenlos dabei.

### D2: Drei-Tier-System

| Tier | Typische Modelle | Einsatz |
|---|---|---|
| `budget` | llama-3.1-8b-instant, groq-compound-mini | Einfache Tasks, hohe Frequenz |
| `standard` | llama-3.3-70b-versatile, llama-4-scout-17b | Standard LLM-Calls, Outline-Generierung |
| `premium` | groq-compound, openai-gpt-oss-120b | Komplexe Reasoning-Tasks, paid Plans |

### D3: action_code als Routing-Key

Consumer-Services übergeben einen `action_code` (z. B.
`pptx_hub.outline_generation_v1`). `aifw` schlägt in der Routing-Tabelle
nach: welches Modell, welcher Provider, welches Token-Budget.
Modell-Wechsel = DB-Row-Update, kein Deploy.

```python
# Consumer-Code — model string NEVER hardcoded
result = aifw.sync_completion(
    action_code="pptx_hub.outline_generation_v1",
    messages=[...],
)
# aifw löst intern auf:
# action_code → LLMActionType → LLMModel → Provider → API-Call
```

### D4: Provider-Constraint via CHECK

`LLMProvider.provider` ist auf bekannte Provider beschränkt (`openai`,
`anthropic`, `groq`, `moonshot`, `alibaba`, `meta`, `cerebras`). Neue
Provider erfordern Migration — bewusste Governance-Entscheidung, kein
freies String-Feld.

### D5: `is_default_for_tier`-Flag

Pro Tier gibt es genau ein Default-Modell (`is_default_for_tier=TRUE`).
Neue Modelle werden mit `FALSE` seeded; der Operator aktiviert sie manuell
nach Smoke-Test. Verhindert ungeprüfte Modelle als automatischen Default.

### D6: OpenRouter-Sync (manuell)

`model_registry_updater.py` kann aus dem OpenRouter-Katalog neue Modelle
vorschlagen. Import ist **nicht automatisch** — Review + explizites
`is_active=TRUE`-Setzen erforderlich.

### D7: API-Key-Verwaltung via ADR-045

Provider-API-Keys werden ausschließlich als Umgebungsvariablen verwaltet
(`.env.prod`, `decouple.config()`). Niemals in der DB, niemals in Code.

## Alternatives considered

| Alternative | Verworfen weil |
|---|---|
| **Hardcoded Konstanten** (Status quo) | Deploy pro Modell-Wechsel; kein zentrales Cost-Control |
| **YAML-File-Registry** (`models.yaml` im Repo) | Versioniert, aber kein Runtime-Update, kein Admin-UI, kein Usage-Tracking |
| **Env-Variable-Routing** (`LLM_MODEL=gpt-4o`) | Nur ein Modell global; keine Action-spezifische Steuerung |
| **OpenRouter-Only** (alle Calls via OpenRouter) | Single-Provider-Dependency; höhere Latenz; kein Self-Hosted-Option |
| **Feature-Flags-System** (LaunchDarkly/Unleash) | Overhead für diesen Use-Case; Django-Admin reicht |

## Consequences

### Positive

- **Zero-Deploy Modell-Wechsel** — Provider deprecated? DB-Row ändern, fertig.
- **Zentrales Cost-Control** — Token-Budget + Tier pro Action konfigurierbar.
- **Usage-Tracking** — `aifw` loggt Tokens + Calls pro `action_code` → Grafana.
- **A/B-Testing** — Routing-Tabelle kann pro Tenant / Experiment variieren.
- **Fallback-Kette** — Mehrere Modelle pro Action; `aifw` versucht nächstes bei Fehler.
- **Audit-Trail** — Django-Admin + Migration-History dokumentieren jeden Modell-Switch.

### Negative / Risiken

- **DB als kritischer Dependency** — Fällt Postgres aus, kein LLM-Routing.
  Mitigation: Lokaler In-Process-Cache in `aifw` (TTL 5 min).
- **Migration pro neuem Provider** — `chk_provider` CHECK-Constraint muss
  erweitert werden. Overhead gering, aber nicht null.
- **`registry_mcp`-Migrations als Raw SQL** — Der MCP-Hub-spezifische
  Registry-Layer nutzt Raw-SQL-Migrations (nicht Django ORM), da `registry_mcp`
  kein Django-App ist. **Bewusste Ausnahme**: Migrations werden in
  `registry_mcp/migrations/` versioniert + reviewed. Django ORM bleibt
  Pflicht für alle regulären Django-App-Models.
- **Groq Free-Tier Rate-Limits** — 9 Groq-Modelle mit unterschiedlichen
  RPM-/TPM-Limits; Rate-Limit-Handling obliegt `aifw` (Retry + Fallback).

### Out of Scope (v1)

- Per-Tenant Modell-Overrides (z. B. Tenant A → GPT-4o, Tenant B → Groq)
- Automatischer OpenRouter-Import ohne manuelles Review
- LLM-Evaluation-Framework (Quality-Scores pro Modell/Action)

## Confirmation

Die Entscheidung gilt als bestätigt wenn:

- ✅ `LLMModel` + `LLMProvider` Django-Models in aifw implementiert (Migration 001)
- ✅ `aifw.sync_completion(action_code=...)` löst über DB-Lookup auf
- ✅ Kein Consumer-Repo enthält hardcoded Model-Strings (`hardcode_scanner.py`)
- ✅ 9 Groq-Modelle via Migration 002 seeded (`is_default_for_tier=FALSE`)
- ✅ `model_registry_updater.py` mit TierRules implementiert
- ✅ Django-Admin zeigt `LLMModel`/`LLMProvider`-Tabellen
- ⬜ Per-Tenant Routing-Overrides (v2 — deferred)
- ⬜ Cerebras `llama-3.3-70b` offiziell in registry_mcp Migration erfasst

## Open Questions

- ~~**Groq-Provider-Integration?**~~ **Entschieden:** 9 Groq-Modelle seeded
  (v3 Amendment, 2026-02-26).
- ~~**OpenRouter-Sync-Strategie?**~~ **Entschieden:** Manueller Import-Workflow
  mit explizitem `is_active=TRUE`-Gate; kein Auto-Import (D6).
- **Cerebras-Integration?** `cerebras/llama-3.3-70b` ist laut
  `policies/llm-routing.md` Tier-1a. Offizielle Migration in `registry_mcp`
  ausstehend; pptx-hub nutzt es bereits via `action_code`-Config.
- **Per-Tenant Routing-Overrides?** V2-Feature als `LLMTenantOverride`-Model
  erweiterbar; kein separates ADR nötig.

## Glossar

| Begriff | Erklärung |
|---|---|
| **action_code** | String-ID (z. B. `pptx_hub.outline_generation_v1`) die einen LLM-Call identifiziert; dient als Routing-Lookup-Key |
| **aifw** | `iil-aifw` — Platform-internes Python-Package; einziger erlaubter LLM-Einstiegspunkt für alle Django-Apps (ADR-082) |
| **budget / standard / premium** | Drei Qualitäts-Tiers: `budget` = schnell + günstig, `standard` = ausgewogen, `premium` = höchste Qualität |
| **chk_provider** | PostgreSQL CHECK-Constraint auf `LLMProvider.provider` — erlaubt nur bekannte Provider-Strings |
| **is_default_for_tier** | Boolesches Flag — genau ein Modell pro Tier ist Default; neue Modelle starten mit `FALSE` |
| **LLMModel** | Django-Model in aifw; speichert Modell-Name, Tier, Token-Limits, Provider-Referenz |
| **LLMProvider** | Django-Model in aifw; speichert Provider-Name + API-Endpoint-Konfiguration |
| **model_registry_updater.py** | Script das OpenRouter-Katalog liest und neue Modelle als Vorschläge importiert |
| **OpenRouter** | Drittanbieter-Proxy für LLM-APIs; dient als Modell-Katalog-Referenz (https://openrouter.ai) |
| **registry_mcp** | Modul im `mcp-hub`-Repo für MCP-seitige Registry-Verwaltung; nutzt Raw-SQL (kein Django-App) |
| **TierRules** | Mapping-Regeln die Modell-Eigenschaften (Context-Länge, Param-Count) einem Tier zuordnen |

## Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-02-25 | Achim Dehnert | v0: Initial Draft — PostgreSQL Model Registry, Tier-Abstraktion, OpenRouter-Sync |
| 2026-02-25 | Achim Dehnert | v1: Review-Fixes — Decision Drivers, ADR-075-Konformität, Confirmation, Migration-Tracking |
| 2026-02-25 | Achim Dehnert | v2: Status Proposed → Accepted nach Review |
| 2026-02-26 | Achim Dehnert | v3: **Groq Provider Amendment** — 9 Groq-Modelle, Migration 002, erweiterte TierRules, Provider-Constraint |
| 2026-05-12 | Achim Dehnert | v4: ADR-Review-Optimierung — Context/Decision/Alternatives/Consequences/Confirmation/Glossar ergänzt; Frontmatter auf MADR 4.0 (`id`, `deciders`); Raw-SQL-Ausnahme dokumentiert; Open Questions aktualisiert |

### v3 Amendment: Groq Provider Integration (2026-02-26)

**Änderungen:**

1. **Schema:** `chk_provider` Constraint erweitert um `'groq'`, `'moonshot'`, `'alibaba'`, `'meta'`
2. **Migration:** `registry_mcp/migrations/002_add_groq_provider.sql`
3. **TierRules:** 9 neue Groq-spezifische Mapping-Regeln in `model_registry_updater.py`
4. **Seed-Daten:** 9 Groq-Modelle (alle `is_active=TRUE`, `is_default_for_tier=FALSE`)

**Neue Groq-Modelle:**

| Model | Tier | Context | Besonderheit |
|-------|------|---------|-------------|
| `qwen-qwen3-32b` | standard | 131k | Bestes Coding-Modell auf Groq |
| `openai-gpt-oss-120b` | premium | 131k | Größtes Modell auf Groq |
| `openai-gpt-oss-20b` | budget | 131k | Klein + schnell |
| `llama-3.3-70b-versatile` | standard | 131k | Bewährter Workhorse |
| `llama-4-scout-17b-16e-instruct` | standard | 512k | MoE, riesiger Context |
| `llama-3.1-8b-instant` | budget | 131k | Ultra-schnell, einfache Tasks |
| `groq-compound` | premium | 131k | Agentic System mit Tool Use |
| `groq-compound-mini` | budget | 131k | Leichterer Agentic |
| `kimi-k2-instruct-0905` | standard | 131k | Moonshot MoE via Groq |

**Groq-Playground zum Testen:** https://console.groq.com/playground
