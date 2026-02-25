---
status: accepted
date: 2026-02-25
decision-makers: Achim Dehnert
consulted: –
informed: –
supersedes: –
amends: ADR-068-adaptive-model-routing.md
related: ADR-068, ADR-082, ADR-045, ADR-080
---

# ADR-084: Model Registry — Dynamisches LLM-Modell-Routing mit datenbankgestützter Tier-Verwaltung

| Attribut       | Wert                                                                 |
|----------------|----------------------------------------------------------------------|
| **Status**     | Accepted                                                             |
| **Scope**      | Platform-wide — AI Infrastructure                                    |
| **Repo**       | platform / mcp-hub                                                   |
| **Erstellt**   | 2026-02-25                                                           |
| **Autor**      | Achim Dehnert                                                        |
| **Reviewer**   | –                                                                    |
| **Supersedes** | –                                                                    |
| **Amends**     | ADR-068 (Adaptive Model Routing) — erweitert Tier-Konzept            |
| **Relates to** | ADR-068 (Routing), ADR-082 (LLM-Tool-Integration), ADR-045 (Secrets), ADR-080 (Multi-Agent) |

<!-- Drift-Detector-Felder
staleness_months: 6
drift_check_paths:
  - orchestrator_mcp/config.py
  - orchestrator_mcp/model_registry.py
  - orchestrator_mcp/agent_team/config.py
supersedes_check: ADR-068
-->

---

## Decision Drivers

- **Model Staleness:** LLM-Ökosystem folgt 3–6-Monats-Zyklus — hardcoded Namen veralten systematisch
- **Doppelkonfiguration:** `config.py` und `agent_team/config.py` divergieren unbemerkt → inkonsistente Routing-Entscheidungen
- **Kosten-Transparenz:** Routing-Entscheidungen (ADR-068) müssen auf aktuellen Preisen basieren, nicht auf Schätzungen
- **Audit-Anforderung:** Welches Modell wann aktiv war muss nachvollziehbar sein (Kostenrechnung, Fehleranalyse)
- **Deprecation-Resilienz:** Provider deprecaten Modelle ohne lange Vorwarnung → Runtime-Fehler ohne Fallback-Mechanismus
- **Plattform-Konsistenz:** PostgreSQL bereits Standard (ADR-021) — kein neuer Technologie-Stack nötig
- **Provider-Unabhängigkeit:** Tier-Semantik darf nicht an einzelnen Provider gebunden sein

---

## 1. Kontext

### 1.1 Ausgangslage

ADR-068 etabliert ein Tier-basiertes Modell-Routing (`premium`, `standard`, `budget`, `local`)
mit einer statischen `TIER_MODELS`-Mapping-Tabelle in `orchestrator_mcp/config.py`.
ADR-082 baut darauf auf und führt `OrchestratorLLMAdapter` ein, der konkrete Modell-Namen
aus dieser Konfiguration bezieht.

Der aktuelle Stand:

```python
# orchestrator_mcp/config.py — hardcoded, veraltet innerhalb von Wochen
TIER_MODELS: Final[dict[str, str]] = {
    "opus":         "claude-opus-4",       # ← ersetzt durch claude-opus-4-5 (Feb 2026)
    "swe":          "claude-sonnet-4",     # ← ersetzt durch claude-sonnet-4-5 (Jan 2026)
    "gpt_low":      "gpt-4o-mini",         # ← o4-mini verfügbar seit Apr 2026
    "budget_cloud": "minimax-m2.5:cloud",  # ← ggf. nicht mehr verfügbar
    "lean_local":   "qwen2.5-coder:32b",   # ← qwen3:32b veröffentlicht Mai 2026
}
```

Zusätzlich sind in `agent_team/config.py` über 160 Zeilen Modell-Namen in `MODEL_SCENARIOS`
hardcoded — eine zweite, divergente Quelle für dieselbe Information.

### 1.2 Problem: Model Staleness als strukturelles Risiko

**Das LLM-Ökosystem folgt einem 3–6-Monats-Zyklus** für signifikante Modell-Updates.
Neue Modelle bieten typischerweise:

- 20–50% bessere Benchmark-Performance (SWE-bench, HumanEval) bei gleichem Preis
- Neue Capabilities (Extended Thinking, Tool-Calling Verbesserungen, längeres Context Window)
- Teils signifikante Preisreduktionen (OpenAI o3: $20→$0.40/1M Input Tokens)

Hardcoded Modell-Namen führen zu drei konkreten Problemen:

| Problem | Auswirkung |
|---------|-----------|
| **Veraltete Modelle** | Sub-optimale Code-Qualität bei gleichen Kosten |
| **Preisdrift** | Routing-Entscheidungen basieren auf falschen Kosten → falsche Tier-Auswahl |
| **Deprecation-Risiko** | Provider deprecaten Modelle ohne lange Vorwarnung → Runtime-Fehler |
| **Doppelte Konfiguration** | `config.py` vs. `agent_team/config.py` divergieren unbemerkt |

### 1.3 Architektur-Constraints

- PostgreSQL ist bereits Plattform-Standard (ADR-021, ADR-072)
- `registry_mcp` existiert und hat eine PostgreSQL-Datenbankanbindung
- API-Keys werden über ADR-045 (SOPS + `/run/secrets/`) verwaltet
- Der `OrchestratorLLMAdapter` (ADR-082) ist der einzige LLM-Aufruf-Punkt
- **OpenRouter** (`openrouter.ai/api/v1/models`) bietet eine öffentliche, kostenlose API
  mit Echtzeit-Modell-Metadaten für alle major Provider

---

## 2. Entscheidung

### We adopt a database-backed Model Registry with tier abstraction and scheduled refresh

**Kerndiziplin: Code referenziert ausschließlich Tier-Namen — niemals Modell-Namen.**

```
┌─────────────────────────────────────────────────────────┐
│  Agent / StepExecutor / UseCaseDecomposer               │
│  registry.get_model(tier="premium", capability="tools") │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│  ModelRegistry  (orchestrator_mcp)                      │
│  - In-memory Cache (TTL: 5 min)                         │
│  - Fallback: hardcoded Defaults                         │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│  model_registry Tabelle (PostgreSQL, registry_mcp DB)   │
│  - Aktive Modelle pro Tier                              │
│  - Preise, Benchmarks, Context Window, Capabilities     │
│  - Historisierung via valid_from / valid_until          │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│  ModelRegistryUpdater  (Scheduled Job, wöchentlich)     │
│  - Quelle 1: OpenRouter API (automatisch)               │
│  - Quelle 2: Manuelle Overrides (ADR-045 gesichert)     │
└─────────────────────────────────────────────────────────┘
```

### 2.1 Tier-Definitionen (stabil, nicht im DB)

Tiers sind **semantische Contracts** — sie ändern sich nicht, nur die Modell-Zuordnung ändert sich:

| Tier | Semantik | Typischer Use Case | Aktuelles Modell (Beispiel) |
|------|---------|-------------------|----------------------------|
| `premium` | Höchste Reasoning-Qualität, architektonische Entscheidungen | TechLead Design, UseCaseDecomposer, ADR-Analyse | `claude-opus-4-5` |
| `standard` | Beste Coding-Performance, Tool-Calling | Developer Implement, Re-Engineer | `claude-sonnet-4-5` |
| `budget` | Günstigste Option mit Tool-Calling | Triage, einfache Transformationen, Guardian-Support | `gpt-4o-mini` |
| `local` | Lokal via Ollama, $0 Kosten, kein API-Key | Gate-0 Autonomous Steps, Tester-Hilfe | `qwen2.5-coder:32b` |
| `reasoning` | Extended Thinking für mehrstufige Analyse | Planner (Phase 3), Root-Cause Analysis | `o3` / `claude-opus-4-5` (ET) |

### 2.2 Datenbankschema

```sql
-- registry_mcp Datenbank
CREATE TABLE model_registry (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identität
    tier                  VARCHAR(32)   NOT NULL,  -- premium | standard | budget | local | reasoning
    provider              VARCHAR(32)   NOT NULL,  -- openai | anthropic | google | ollama | openrouter
    model_name            VARCHAR(128)  NOT NULL,  -- exakter API-Bezeichner (z.B. claude-opus-4-5-20250514)
    display_name          VARCHAR(128)  NOT NULL,  -- lesbarer Name für Logs

    -- Capabilities
    context_window_tokens INTEGER       NOT NULL,
    supports_tool_calling BOOLEAN       NOT NULL DEFAULT FALSE,
    supports_json_mode    BOOLEAN       NOT NULL DEFAULT FALSE,
    supports_vision       BOOLEAN       NOT NULL DEFAULT FALSE,
    max_output_tokens     INTEGER,

    -- Kosten (USD per 1M Tokens)
    cost_input_per_1m     NUMERIC(10,4) NOT NULL,
    cost_output_per_1m    NUMERIC(10,4) NOT NULL,

    -- Qualität
    swe_bench_score       NUMERIC(5,2),   -- SWE-bench Verified % (NULL = nicht gemessen)
    humaneval_score       NUMERIC(5,2),   -- HumanEval Pass@1 % (NULL = nicht gemessen)
    composite_score       NUMERIC(5,4),   -- Interner Score: 0.0–1.0 (Basis für Tier-Ranking)

    -- Lebenszyklus
    is_active             BOOLEAN       NOT NULL DEFAULT TRUE,
    is_default_for_tier   BOOLEAN       NOT NULL DEFAULT FALSE,
    valid_from            TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    valid_until           TIMESTAMPTZ,             -- NULL = unbegrenzt aktiv
    deprecated_at         TIMESTAMPTZ,
    deprecation_notice    TEXT,

    -- Herkunft
    source                VARCHAR(32)   NOT NULL DEFAULT 'manual',  -- openrouter | manual | benchmark
    last_refreshed_at     TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    external_id           VARCHAR(256),  -- OpenRouter model ID

    -- Constraints
    CONSTRAINT uq_model_per_tier UNIQUE (tier, model_name, valid_from),
    CONSTRAINT chk_tier CHECK (tier IN ('premium', 'standard', 'budget', 'local', 'reasoning')),
    CONSTRAINT chk_provider CHECK (provider IN ('openai', 'anthropic', 'google', 'ollama', 'openrouter', 'other'))
);

-- Index für häufigste Query: aktives Default-Modell pro Tier
CREATE INDEX idx_model_registry_active_tier
    ON model_registry (tier, is_active, is_default_for_tier)
    WHERE is_active = TRUE;

-- Audit-Trail: jede Änderung wird protokolliert
CREATE TABLE model_registry_audit (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id      UUID REFERENCES model_registry(id),
    changed_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    changed_by    VARCHAR(64) NOT NULL DEFAULT 'system',  -- system | manual | openrouter-sync
    change_type   VARCHAR(32) NOT NULL,  -- activated | deactivated | updated | deprecated
    old_values    JSONB,
    new_values    JSONB
);
```

### 2.3 ModelRegistry Python-Klasse

```python
# orchestrator_mcp/model_registry.py

@dataclass
class ModelSpec:
    tier: str
    provider: str
    model_name: str
    context_window_tokens: int
    supports_tool_calling: bool
    cost_input_per_1m: float
    cost_output_per_1m: float
    composite_score: float


class ModelRegistry:
    """Tier-zu-Modell-Auflösung mit DB-Backend und In-Memory-Cache.

    Fallback-Kette: DB → Cache → Hardcoded Defaults (niemals None).
    """

    _FALLBACK: dict[str, str] = {
        "premium":   "claude-opus-4-5-20250514",
        "standard":  "claude-sonnet-4-5-20250514",
        "budget":    "gpt-4o-mini",
        "local":     "qwen2.5-coder:32b",
        "reasoning": "o3",
    }

    def get_model(
        self,
        tier: str,
        capability: str | None = None,  # "tools" | "vision" | "json"
    ) -> ModelSpec:
        """Gibt das aktuell beste Modell für den Tier zurück.

        Selektion: is_active=TRUE, is_default_for_tier=TRUE, höchster composite_score.
        Bei capability-Filter: zusätzlich supports_<capability>=TRUE.
        Cache-TTL: 5 Minuten (verhindert DB-Round-Trip bei jedem LLM-Call).
        """
        ...

    def get_cost_estimate(self, tier: str, tokens: int) -> float:
        """Gibt aktuelle Kosten-Schätzung für einen LLM-Call zurück."""
        ...
```

### 2.4 ModelRegistryUpdater — Wöchentlicher Refresh

```python
# orchestrator_mcp/model_registry_updater.py

class ModelRegistryUpdater:
    """Synchronisiert model_registry Tabelle mit OpenRouter API.

    Läuft als Scheduled Job (wöchentlich via Temporal Worker, ADR-079).
    Schreibt nur neue Zeilen — deaktiviert nie automatisch bestehende Modelle.
    Manuelle Deaktivierung via Admin-Interface oder direkt in DB.
    """

    OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"

    TIER_MAPPING_RULES: list[TierRule] = [
        # Regel: Claude Opus → premium
        TierRule(provider="anthropic", name_contains="opus", tier="premium"),
        TierRule(provider="anthropic", name_contains="sonnet", tier="standard"),
        TierRule(provider="openai",    name_contains="o3",    tier="reasoning"),
        TierRule(provider="openai",    name_contains="4o-mini", tier="budget"),
        TierRule(provider="ollama",    name_pattern=".*",     tier="local"),
        # Qualitäts-Override: o3 trotz Budget-Preis → premium (nach Feb-2026 Preisreduktion)
        TierRule(provider="openai", name_contains="o3",
                 cost_input_max=1.0, tier="premium", priority=10),
    ]

    def refresh(self) -> RefreshResult:
        """Holt aktuelle Modelle, mappt zu Tiers, schreibt in DB."""
        ...
```

---

## 3. Betrachtete Alternativen

### 3.1 Status Quo — Hardcoded TIER_MODELS in config.py

| Kriterium | Bewertung |
|-----------|----------|
| Aufwand | ✅ Null — bereits vorhanden |
| Aktualität | ❌ Veraltet innerhalb von Wochen ohne manuelle Eingriffe |
| Dopplung | ❌ `config.py` vs. `agent_team/config.py` divergieren |
| Historisierung | ❌ Nicht vorhanden |
| Preis-Tracking | ❌ Nicht möglich |

**Abgelehnt:** Das strukturelle Risiko wächst mit der Anzahl der Agenten quadratisch.

### 3.2 JSON/YAML-Datei in `~/.config/mcp-hub/models.json`

| Kriterium | Bewertung |
|-----------|----------|
| Aufwand | ✅ Gering |
| Historisierung | ❌ Keine — Datei wird überschrieben |
| Multi-Process | ❌ Race Conditions bei parallelen Agenten |
| Zentrale Verwaltung | ❌ Lokal auf jedem Rechner separat |
| Query-Fähigkeit | ❌ Keine SQL-Abfragen möglich |

**Abgelehnt:** Keine Historisierung, kein Audit-Trail, nicht multi-process-safe.

### 3.3 Externes SaaS (Portkey, LiteLLM Proxy, OpenRouter direkt)

| Kriterium | Bewertung |
|-----------|----------|
| Aktualität | ✅ Immer aktuell |
| Datensouveränität | ❌ Metadaten verlassen Infrastruktur |
| Vendor Lock-in | ❌ Abhängigkeit von externem Service |
| Kosten | ❌ $50–200/Monat für managed Proxy |
| Latenz | ❌ Zusätzlicher Hop für jeden LLM-Call |

**Abgelehnt:** Datensouveränität und Kosten nicht akzeptabel für aktuelle Plattformgröße.

### 3.4 **Gewählt: PostgreSQL Model Registry** (diese Entscheidung)

Kombiniert alle Vorteile:
- Historisierung und Audit-Trail nativ
- Multi-Process-Safe
- SQL-Queries für Tier-Selektion nach Score, Preis, Capability
- Zentrales Management über alle Agenten und Services
- Passt in bestehende Plattform-Infrastruktur (ADR-021, `registry_mcp`)
- Kein neuer Service nötig

---

## 4. Begründung im Detail

### 4.1 Warum Tier-Abstraktion nicht aufgeben?

Die Versuchung ist groß, direkt Modell-Namen zu konfigurieren. Das führt jedoch zu:

```python
# Anti-Pattern — direkte Modell-Namen im Code
executor = StepExecutor(model="claude-opus-4-5-20250514")  
# → In 6 Monaten deprecated, Code veraltet, keine zentrale Verwaltung
```

Tier-Namen sind semantische Verträge über **Qualitätsniveau und Kosten-Klasse**, nicht über
spezifische Modelle. Die Frage "Welches Modell ist gerade das beste im Premium-Tier?" ist
eine Datenbankfrage — nicht eine Code-Frage.

### 4.2 Warum OpenRouter als Datenquelle?

OpenRouter aggregiert **alle major Provider** in einer einheitlichen API:
- Anthropic (Claude), OpenAI (GPT, o-Serie), Google (Gemini), Meta (Llama), Mistral
- Echtzeit-Preise, Context Windows, Capability-Flags
- Kostenlos, kein API-Key nötig für `/api/v1/models`
- Etabliert, CNCF-adjacent, breite Community

Alternative: LiteLLM Model List — ähnlich, aber weniger vollständig für Preise.

### 4.3 Warum wöchentlicher Refresh, nicht on-demand?

- **Stabilität:** LLM-Calls sollen deterministisch sein — dasselbe Modell für den gesamten
  Workflow-Lauf, nicht mitten im Lauf wechseln
- **Kosten:** OpenRouter API kostenlos, aber Rate Limits für Burst-Queries
- **Audit:** Wöchentliche Snapshots erlauben präzise Aussagen ("Am 2026-03-01 war claude-opus-4-5
  das aktive Premium-Modell")
- **Manuelle Kontrolle:** Der Operator entscheidet bewusst, welche Modelle aktiviert werden

### 4.4 Composite Score — Priorisierungsformel

```python
composite_score = (
    0.50 * normalized_swe_bench_score    # Coding-Qualität (primär)
    + 0.30 * normalized_benchmark_avg    # Allgemeine Qualität
    + 0.20 * (1.0 - normalized_cost)     # Kosten-Effizienz (niedriger Preis → höherer Score)
)
```

Für Tiers mit explizitem Kosten-Fokus (`budget`) wird die Kosten-Gewichtung auf 0.50 erhöht.
Für `reasoning`-Tier wird `swe_bench_score` durch `math_benchmark_score` ersetzt.

---

## 5. Implementation Plan

### Phase 1: Schema + Seed-Daten (Tag 1–2)

```sql
-- Migration in registry_mcp
CREATE TABLE model_registry (...);    -- siehe §2.2
CREATE TABLE model_registry_audit (...);
CREATE INDEX idx_model_registry_active_tier (...);

-- Seed: aktuelle Modelle aus config.py migrieren
INSERT INTO model_registry (tier, provider, model_name, ..., is_default_for_tier)
VALUES
  ('premium',   'anthropic', 'claude-opus-4-5-20250514',  ..., TRUE),
  ('standard',  'anthropic', 'claude-sonnet-4-5-20250514',..., TRUE),
  ('budget',    'openai',    'gpt-4o-mini',                ..., TRUE),
  ('reasoning', 'openai',    'o3',                         ..., TRUE),
  ('local',     'ollama',    'qwen2.5-coder:32b',          ..., TRUE);
```

### Phase 2: ModelRegistry Python-Klasse (Tag 2–3)

- `orchestrator_mcp/model_registry.py` — Query-Klasse mit Cache
- `orchestrator_mcp/model_registry_updater.py` — OpenRouter-Sync
- `OrchestratorLLMAdapter` (ADR-082) nutzt `ModelRegistry.get_model(tier=...)` statt hardcoded Name
- `agent_team/config.py` `MODEL_SCENARIOS` → auf Tier-Namen reduzieren

### Phase 3: MCP-Tool (read-only) + GitHub Actions (write-ops) + Scheduled Job (Tag 3–4)

**ADR-075-Konformität:** Write-Ops laufen ausschließlich via GitHub Actions — nicht via MCP.

```python
# server.py: NUR read-only MCP-Tool
Tool(name="list_models")  # Aktuelle Modell-Liste pro Tier anzeigen — read-only
```

Write-Ops als GitHub Actions Workflows:

```yaml
# .github/workflows/model-registry-refresh.yml
# Ersetzt: refresh_models MCP-Tool (ADR-075: Write-Ops via GitHub Actions)
on:
  schedule:
    - cron: "0 3 * * 1"   # Wöchentlich Montags 03:00 UTC
  workflow_dispatch:        # Manueller Trigger
jobs:
  refresh:
    runs-on: [self-hosted, hetzner, dev]
    steps:
      - uses: actions/checkout@v4
      - run: python -m orchestrator_mcp.model_registry_updater
```

```yaml
# .github/workflows/model-registry-set-active.yml
# Ersetzt: set_active_model MCP-Tool (ADR-075: Write-Ops via GitHub Actions)
on:
  workflow_dispatch:
    inputs:
      tier:       { required: true, description: "premium|standard|budget|local|reasoning" }
      model_name: { required: true, description: "Exakter API-Bezeichner" }
      reason:     { required: true, description: "Begründung für Modellwechsel" }
jobs:
  set-active:
    runs-on: [self-hosted, hetzner, dev]
    steps:
      - uses: actions/checkout@v4
      - run: python -m orchestrator_mcp.model_registry_cli set-active --tier ${{ inputs.tier }} --model ${{ inputs.model_name }}
```

Jeder Modellwechsel ist damit ein GitHub-Audit-Trail-Eintrag mit `actor`, `timestamp`, `inputs` und Rollback-Fähigkeit via erneutem `workflow_dispatch`.

Scheduled Refresh via Temporal Worker (ADR-079) als Alternative zum GitHub-Actions-Cron:
```python
@workflow.defn
class ModelRegistryRefreshWorkflow:
    """Läuft wöchentlich. Holt OpenRouter-Daten, schreibt neue Einträge."""
    schedule = "0 3 * * 1"  # Montags 03:00 UTC
```

### Phase 4: Cleanup (Tag 4) — Zero Breaking Changes

Gemäß ADR Zero-Breaking-Changes-Prinzip: Deprecation über **2 Releases** vor Entfernung.

| Schritt | Release N | Release N+1 | Release N+2 |
|---------|-----------|-------------|-------------|
| `TIER_MODELS` in `config.py` | Deprecation-Warning hinzufügen | Deprecation-Warning | **Entfernen** |
| `MODEL_SCENARIOS` in `agent_team/config.py` | Auf Tier-Referenzen umstellen | — | Cleanup |
| Hardcoded Modell-Namen | `grep`-CI-Check einschalten (warn) | `grep`-CI-Check (error) | 0 Treffer erzwungen |

```python
# config.py — Release N: Deprecation statt sofortiges Entfernen
import warnings
TIER_MODELS: Final[dict[str, str]] = {  # deprecated: use ModelRegistry
    ...
}
warnings.warn(
    "TIER_MODELS is deprecated — use ModelRegistry.get_model(tier=...) instead. "
    "Will be removed in Release N+2.",
    DeprecationWarning, stacklevel=2,
)```

### Migration Tracking (ADR-021 §4-Pattern)

| Komponente | Status | Target | Notiz |
|------------|--------|--------|-------|
| `TIER_MODELS` in `orchestrator_mcp/config.py` | 🔴 hardcoded | `ModelRegistry.get_model()` | Phase 2 |
| `MODEL_SCENARIOS` in `agent_team/config.py` | 🔴 hardcoded | Tier-Referenzen | Phase 2 |
| `OrchestratorLLMAdapter` Modell-Auflösung | 🔴 direkt aus config | `ModelRegistry` | Phase 2 |
| `refresh_models` MCP-Tool | 🟡 geplant (Write-Op) | GitHub Actions Workflow | Phase 3 |
| `set_active_model` MCP-Tool | 🟡 geplant (Write-Op) | GitHub Actions Workflow | Phase 3 |
| CI-Guard `grep claude-\|gpt-4` | 🔴 fehlt | CI-Check (warn→error) | Phase 4 |

*Legende: 🔴 offen · 🟡 in Planung · 🟢 abgeschlossen*

---

## 6. Risiken

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|-----------|
| DB nicht erreichbar beim LLM-Call | Mittel | Hoch | Hardcoded Fallback-Defaults (niemals `None`) |
| OpenRouter API ändert Schema | Niedrig | Mittel | Schema-Validation + Alert bei Sync-Fehler |
| Falsches Tier-Mapping für neues Modell | Mittel | Mittel | Manuelle Review vor `is_default_for_tier=TRUE` |
| Modell deprecated ohne DB-Update | Mittel | Hoch | Provider-Error → automatisch Fallback auf zweitbestes aktives Modell im Tier |
| Kosten-Drift durch teureres Modell im Tier | Niedrig | Mittel | Cost-Guard in `BudgetState` (ADR-082) als zweite Schutzschicht |
| Wöchentlicher Job schlägt fehl | Niedrig | Niedrig | Alter Eintrag bleibt aktiv — kein Ausfall, nur veraltete Daten |

---

## 7. Konsequenzen

### 7.1 Positiv

- **Modell-Aktualität:** Wöchentlicher Refresh → typisch nicht mehr als 7 Tage hinter dem Stand der Technik
- **Kosten-Transparenz:** Preise in DB → Routing-Entscheidungen (ADR-068) basieren auf echten, aktuellen Kosten
- **Audit-Trail:** Vollständige Historie welches Modell wann für welchen Tier aktiv war
- **Eliminierung von Dopplung:** Eine einzige Quelle für Modell-Konfiguration statt `config.py` + `agent_team/config.py`
- **Provider-Unabhängigkeit:** Tier-Semantik ändert sich nicht wenn Anthropic durch OpenAI überholt wird oder umgekehrt

### 7.2 Trade-offs

| Akzeptiert | Abgelehnte Alternative |
|-----------|----------------------|
| PostgreSQL-Abhängigkeit für Modell-Selektion | Datei-basiert (kein Audit-Trail) |
| Wöchentliche Latenz bei Modell-Updates | On-demand API-Call pro LLM-Request (Latenz + Rate Limit) |
| Manueller Aktivierungs-Schritt für neue Modelle | Auto-Aktivierung (unkontrolliertes Kostenrisiko) |
| Separater Scheduled Job (Temporal) | Cron auf Server (kein Retry, kein Audit) |

### 7.3 Nicht in Scope

- **Automatische Modell-Evaluierung:** Benchmark-Scores werden aus externen Quellen übernommen,
  nicht intern gemessen. Eigene Evaluierungs-Pipeline ist ein separates ADR.
- **Per-Task Modell-Selektion:** Der Router (ADR-068) wählt den Tier — die Registry liefert das
  Modell im Tier. Feinere Granularität (z.B. "für Python-Tasks immer Codex") ist Phase 2.
- **Kostenbudget-Enforcement:** Liegt in `BudgetState` (ADR-082), nicht in der Registry.
- **Local-Modell-Management:** Ollama-spezifisches Pull/Update ist separates operatives Thema.

---

## 7.4 Offene Fragen (Deferred Decisions)

| Frage | Defer-Ziel | Referenz |
|-------|-----------|----------|
| Eigene Benchmark-Pipeline: Interne Evaluation statt externer Scores | Separates ADR (ADR-085 oder ADR-08x) | SWE-bench läuft extern — interne Messung für spezifische Use Cases |
| Per-Task Modell-Selektion: Feinere Granularität als Tier | ADR-068 Amendment v2 | z.B. "für Python-Refactoring immer Standard, für Shell-Skripte Budget" |
| ORM vs. raw SQL für `registry_mcp` Migration | In Phase 1 entscheiden | Abhängig von vorhandenem `registry_mcp`-Stack (Django Migrations vs. Alembic vs. raw) |
| `registry_mcp` DB-Instanz: eigene oder geteilt | In Phase 1 prüfen | Shared-DB-Risk gemäß ADR-021 §4 bewerten |

---

## 8. Validation Criteria

| Phase | Kriterium | Messung |
|-------|-----------|---------|
| Phase 1 | Schema deployed, Seed-Daten korrekt | `SELECT COUNT(*) FROM model_registry WHERE is_active = TRUE` >= 5 |
| Phase 2 | `ModelRegistry.get_model("premium")` liefert korrekten API-Bezeichner | Unit-Test mit Mock-DB |
| Phase 2 | Fallback bei DB-Ausfall liefert Defaults | Unit-Test: DB disconnected |
| Phase 3 | OpenRouter-Sync schreibt neue Zeilen ohne bestehende zu löschen | Integration-Test |
| Phase 3 | MCP-Tool `list_models` zeigt aktuelle Tier-Zuordnungen | manueller Smoke-Test |
| Phase 4 | `grep -r "claude-\|gpt-4" orchestrator_mcp/` liefert 0 hardcoded Treffer | CI-Check |

### Confirmation

ADR-084-Compliance wird wie folgt im laufenden Betrieb verifiziert:

| Prüfpunkt | Methode | Frequenz |
|-----------|---------|----------|
| Kein hardcoded Modell-Name im Code | CI-Check: `grep -r "claude-\|gpt-4\|opus\|sonnet" orchestrator_mcp/ \| grep -v model_registry` | Jeder PR |
| `ModelRegistry.get_model()` liefert aktives Modell | Unit-Test mit Mock-DB + Fallback-Test (DB disconnected) | CI |
| Wöchentlicher Refresh läuft durch | Temporal Workflow Health-Check + GitHub Actions Run-Log | Wöchentlich |
| Write-Ops ausschließlich via GitHub Actions | ADR-075-Guard: kein `set_active`/`refresh` in `server.py` | Code Review |
| Migration-Tracking vollständig 🟢 | Alle Zeilen in §5 Migration-Tabelle auf 🟢 | vor Accept von Phase 4 |

---

## 9. Referenzen

- [OpenRouter Models API](https://openrouter.ai/api/v1/models) — Quelle für Modell-Metadaten
- [SWE-bench Leaderboard](https://www.swebench.com/) — Coding-Benchmark-Referenz
- [LiteLLM Model Pricing](https://models.litellm.ai/) — Alternative Preisquelle
- ADR-021: Unified Deployment Strategy
- ADR-045: Secrets & Environment Management
- ADR-068: Adaptive Model Routing (wird durch dieses ADR amendiert)
- ADR-079: Temporal Workflow Engine (für Scheduled Refresh Job)
- ADR-080: Multi-Agent Coding Team Pattern
- ADR-082: LLM-Tool-Integration — Autonomous Coding

---

## 10. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-02-25 | Achim Dehnert | v0: Initial Draft — PostgreSQL Model Registry, Tier-Abstraktion, OpenRouter-Sync |
| 2026-02-25 | Achim Dehnert | v2: Status Proposed → Accepted nach Review |
| 2026-02-25 | Achim Dehnert | v1: Review-Fixes — Decision Drivers, ADR-075-Konformität (Write-Ops → GitHub Actions), Confirmation, Migration-Tracking, Drift-Detector, Deferred Decisions, Zero-Breaking-Changes Deprecation-Plan |
