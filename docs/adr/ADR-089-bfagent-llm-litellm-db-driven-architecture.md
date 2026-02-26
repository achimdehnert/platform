---
status: proposed
date: 2026-02-26
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
| **Status**     | Proposed (v1 — Review-Fixes eingearbeitet)                           |
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
bfagent-llm v1.0 (Ziel-Architektur)
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
    "bfagent_llm.django_app",
]

# In jedem Service:
from bfagent_llm.django_app.service import completion

result = await completion(
    action_code="character_generation",
    messages=[{"role": "user", "content": prompt}],
    tenant_id=request.tenant_id,
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

### 2.2 DB-Models (aus travel-beat extrahiert, generalisiert, Review-Fixes)

#### Invarianten

1. **Multi-Tenancy (ADR-056):** `AIActionType` und `AIUsageLog` MÜSSEN `tenant_id` haben.
   `LLMProvider` und `LLMModel` sind globale Infrastruktur (kein `tenant_id`).
2. **Secrets (ADR-045):** `_get_api_key()` MUSS `read_secret()` nutzen
   (Priorität: `/run/secrets/<key_lower>` → `os.environ[KEY]` → Fehler).
3. **Kein stiller Fallback:** Wenn `AIActionType` kein `default_model` hat → `LLMConfigurationError`.
   Kein globaler Default-Fallback auf irgendeinen `is_default=True` Model.
4. **Naming:** `AIActionType.code` MUSS `^[a-z][a-z0-9_]{2,49}$` matchen (snake_case).
5. **Idempotenz:** Management Commands nutzen `update_or_create()`, nie `create()`.

#### Models

```python
from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models


class LLMProvider(models.Model):
    """Globale LLM-Provider (shared across tenants).

    Kein tenant_id — Provider sind Infrastruktur-Ressourcen.
    """

    name = models.CharField(
        max_length=50,
        unique=True,
        validators=[RegexValidator(r"^[a-z][a-z0-9_-]*$")],
    )
    display_name = models.CharField(max_length=100)
    api_key_env_var = models.CharField(
        max_length=100,
        help_text="Env-Var Name, z.B. OPENAI_API_KEY. "
        "Wird via read_secret() aufgelöst (ADR-045).",
    )
    base_url = models.URLField(
        blank=True,
        default="",
        help_text="Custom endpoint URL. Leer = Provider-Default.",
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "bfllm_providers"
        verbose_name = "LLM Provider"
        verbose_name_plural = "LLM Providers"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.display_name


class LLMModel(models.Model):
    """Globale LLM-Modelle (shared across tenants).

    Kein tenant_id — Modelle sind Infrastruktur-Ressourcen.
    Cost-Daten ermöglichen per-tenant Kostenzuordnung via AIUsageLog.
    """

    provider = models.ForeignKey(
        LLMProvider,
        on_delete=models.CASCADE,
        related_name="models",
    )
    name = models.CharField(max_length=100)
    display_name = models.CharField(max_length=150)

    max_tokens = models.IntegerField(default=4096)
    context_window = models.IntegerField(
        default=128_000,
        help_text="Max context window in tokens.",
    )
    supports_vision = models.BooleanField(default=False)
    supports_tools = models.BooleanField(default=True)

    input_cost_per_million = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0,
        help_text="USD per 1M input tokens.",
    )
    output_cost_per_million = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0,
        help_text="USD per 1M output tokens.",
    )

    is_active = models.BooleanField(default=True, db_index=True)
    is_default = models.BooleanField(
        default=False,
        help_text="Globaler Default für init_llm_config. "
        "Wird NICHT als stiller Fallback genutzt.",
    )

    class Meta:
        db_table = "bfllm_models"
        verbose_name = "LLM Model"
        verbose_name_plural = "LLM Models"
        unique_together = [("provider", "name")]
        ordering = ["provider__name", "name"]

    def __str__(self) -> str:
        return f"{self.provider.name}:{self.name}"


class AIActionType(models.Model):
    """Per-Action LLM-Routing — tenant-spezifisch (ADR-056).

    Jeder Tenant kann eigene Model-Zuordnungen haben.
    Ohne default_model → LLMConfigurationError (kein stiller Fallback).
    """

    tenant_id = models.UUIDField(
        db_index=True,
        help_text="Tenant-ID (ADR-056). Pflicht für Multi-Tenancy.",
    )

    code = models.CharField(
        max_length=50,
        validators=[RegexValidator(
            r"^[a-z][a-z0-9_]{2,49}$",
            "Code muss snake_case sein (3-50 Zeichen, a-z/0-9/_).",
        )],
        help_text="Eindeutiger Action-Code pro Tenant, z.B. "
        "'character_generation', 'hazard_analysis'.",
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")

    default_model = models.ForeignKey(
        LLMModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="default_for_actions",
        help_text="Pflicht für aktive Actions. "
        "Ohne Model → LLMConfigurationError.",
    )
    fallback_model = models.ForeignKey(
        LLMModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fallback_for_actions",
        help_text="Fallback wenn default_model fehlschlägt.",
    )

    max_tokens = models.IntegerField(default=2000)
    temperature = models.FloatField(default=0.7)

    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "bfllm_action_types"
        verbose_name = "AI Action Type"
        verbose_name_plural = "AI Action Types"
        unique_together = [("tenant_id", "code")]
        indexes = [
            models.Index(
                fields=["tenant_id", "code", "is_active"],
                name="bfllm_action_tenant_code_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} ({self.name})"

    def clean(self) -> None:
        from django.core.exceptions import ValidationError

        if self.is_active and not self.default_model_id:
            raise ValidationError(
                {"default_model": "Aktive Actions MÜSSEN ein default_model haben."}
            )
        if self.default_model_id and self.default_model and not self.default_model.is_active:
            raise ValidationError(
                {"default_model": "default_model muss aktiv sein."}
            )

    def get_model(self) -> "LLMModel":
        """Explizites Model-Lookup. Kein stiller Fallback."""
        if self.default_model and self.default_model.is_active:
            return self.default_model
        if self.fallback_model and self.fallback_model.is_active:
            return self.fallback_model
        raise LLMConfigurationError(
            f"Kein aktives Model für Action '{self.code}' konfiguriert. "
            f"Setze default_model in Admin → AI Action Types."
        )


class AIUsageLog(models.Model):
    """LLM-Usage-Tracking — tenant-spezifisch (ADR-056).

    Jeder Call wird geloggt für Cost-Zuordnung und Monitoring.
    """

    tenant_id = models.UUIDField(
        db_index=True,
        help_text="Tenant-ID für Cost-Zuordnung.",
    )

    action_type = models.ForeignKey(
        AIActionType,
        on_delete=models.SET_NULL,
        null=True,
    )
    model_used = models.ForeignKey(
        LLMModel,
        on_delete=models.SET_NULL,
        null=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    input_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)
    estimated_cost = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        default=0,
    )

    latency_ms = models.IntegerField(default=0)
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bfllm_usage_logs"
        verbose_name = "AI Usage Log"
        verbose_name_plural = "AI Usage Logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "-created_at"],
                name="bfllm_usage_tenant_date_idx",
            ),
            models.Index(
                fields=["action_type_id", "-created_at"],
                name="bfllm_usage_action_date_idx",
            ),
        ]

    def save(self, *args, **kwargs) -> None:
        self.total_tokens = self.input_tokens + self.output_tokens
        if self.model_used:
            input_cost = (
                self.input_tokens / 1_000_000
            ) * float(self.model_used.input_cost_per_million)
            output_cost = (
                self.output_tokens / 1_000_000
            ) * float(self.model_used.output_cost_per_million)
            self.estimated_cost = input_cost + output_cost
        super().save(*args, **kwargs)


class LLMConfigurationError(Exception):
    """Raised when no active LLM model is configured for an action."""
```

### 2.3 Secret-Auflösung (ADR-045-konform)

```python
def _get_api_key(provider: LLMProvider) -> str:
    """Resolve API key via ADR-045 read_secret() pattern.

    Priority: /run/secrets/<key_lower> → os.environ[KEY] → Error.
    NEVER silently return empty string.
    """
    env_var = provider.api_key_env_var
    if not env_var:
        raise LLMConfigurationError(
            f"Provider '{provider.name}' hat kein api_key_env_var konfiguriert."
        )

    # ADR-045: read_secret() mit /run/secrets/ Priorität
    try:
        from config.secrets import read_secret
        value = read_secret(env_var, required=True)
        if value:
            return value
    except ImportError:
        pass  # read_secret() nicht verfügbar (z.B. MCP-Server)

    # Fallback: os.environ (Legacy, vor SOPS-Migration)
    import os
    value = os.environ.get(env_var, "")
    if value:
        return value

    raise LLMConfigurationError(
        f"API-Key für Provider '{provider.name}' nicht gefunden. "
        f"Erwartet: /run/secrets/{env_var.lower()} oder env {env_var}."
    )
```

### 2.4 Service-Funktion (LiteLLM als Backend)

```python
async def completion(
    action_code: str,
    messages: list[dict],
    tenant_id: str | None = None,
    tools: list[dict] | None = None,
    user=None,
    **overrides,
) -> LLMResult:
    """DB-driven completion via LiteLLM.

    1. AIActionType.objects.get(tenant_id=tid, code=code)
    2. action.get_model() → LLMModel (oder LLMConfigurationError)
    3. _build_model_string() → "provider/model" (LiteLLM-Format)
    4. _get_api_key() → ADR-045-konform
    5. litellm.acompletion() → Unified response
    6. AIUsageLog.objects.create() → Cost + Usage tracking

    Raises:
        LLMConfigurationError: Kein Model konfiguriert (KEIN stiller Fallback)
    """
```

### 2.5 `litellm` Dependency-Management

**Risiko:** `litellm` ist ~50MB mit 200+ transitiven Dependencies und patcht
`openai`/`anthropic` Clients zur Laufzeit (monkey-patching).

**Mitigation:**
1. Version strikt pinnen: `litellm>=1.55,<1.60`
2. Nur `litellm.acompletion()` und `litellm.completion_cost()` nutzen
3. `litellm` als optionale Dependency: `pip install bfagent-llm[litellm]`
4. Basis-Package (`bfagent-llm`) bleibt leichtgewichtig (nur Core-Adapter)
5. Django-App (`bfagent-llm[django]`) zieht `litellm` + Django Dependencies

```toml
# pyproject.toml
[project.optional-dependencies]
django = ["django>=5.0", "litellm>=1.55,<1.60"]
litellm = ["litellm>=1.55,<1.60"]
```

**Langfrist-Option:** Falls `litellm` problematisch wird, kann `service.py`
intern auf die Core-Adapter umgestellt werden (OpenAI, Anthropic, Groq decken
95% der Nutzung ab). Der Service-API bleibt stabil.

---

## 3. Konsequenzen

### 3.1 Was sich ändert

| Vorher | Nachher |
|--------|---------|
| Neuer Provider → Custom Adapter coden | Neuer Provider → DB-Eintrag im Admin |
| Model-Swap → Code ändern + deployen | Model-Swap → Admin-UI, sofort wirksam |
| 4 Provider (OpenAI, Anthropic, Groq, Gateway) | 100+ Provider via LiteLLM |
| TierConfig hardcoded | AIActionType per-action in DB |
| Budget-Tracking im Memory | AIUsageLog in DB, querybar, per-tenant |
| Jede App eigener LLM-Code (~41KB travel-beat) | Shared Django App aus bfagent-llm |
| Kein tenant_id auf LLM-Config | AIActionType + AIUsageLog mit tenant_id |
| `os.environ.get()` für API-Keys | `read_secret()` (ADR-045) |

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

1. `bfagent_llm/django_app/` Subpackage erstellen (Django App)
2. DB-Models mit `bfllm_` Tabellen-Prefix, tenant_id, Indizes
3. `service.py` mit `completion()`, `sync_completion()`, `completion_with_fallback()`
4. `_get_api_key()` mit ADR-045 `read_secret()` Integration
5. `LiteLLMAdapter` als neuer Core-Adapter
6. `litellm` als optionale Dependency (`pip install bfagent-llm[django]`)
7. Management Commands:
   - `init_llm_config` — Seed-Daten via `update_or_create()` (idempotent)
   - `check_llm_config` — Validiert dass alle aktiven AIActionTypes ein default_model haben
8. Django System Check: warnt bei fehlenden API-Keys
9. Tests (pytest, min. 80% coverage)

### Phase 2: travel-beat Migration (1 Tag)

1. `bfagent-llm[django]` in requirements.txt
2. `INSTALLED_APPS += ["bfagent_llm.django_app"]`
3. DB-Migration (2-Schritt):
   - Schritt 1: `bfllm_*` Tabellen erstellen, Daten aus `ai_llm_*` kopieren
   - Schritt 2: `ai_llm_*` Tabellen erst nach Validierung droppen
   - **Vorher:** `pg_dump` der `ai_llm_*` Tabellen als Rollback-Sicherung
4. `llm_service.py` → `from bfagent_llm.django_app.service import completion`
5. `llm_client.py` + `llm_providers.py` entfernen
6. `services.py` creative_services-Import entfernen

**Rollback-Plan:**
```bash
# Bei Fehler: Daten aus Backup wiederherstellen
pg_dump -t ai_llm_providers -t ai_llm_models \
    -t ai_action_types -t ai_usage_logs \
    travel_beat > /tmp/ai_llm_backup.sql

# Rollback:
psql travel_beat < /tmp/ai_llm_backup.sql
# + git revert des Migration-Commits
```

### Phase 3: Weitere Apps (je 0.5 Tag)

- **weltenhub**: Identisch zu travel-beat (gleiche SHA)
- **bfagent**: `apps/ai_services/llm_service.py` ersetzen
- **risk-hub**: `src/ai_analysis/llm_client.py` ersetzen
- **137-hub**: `supersystem/llm/providers/` ersetzen

### Phase 4: Cleanup + Monitoring

- `creative_services.core.llm_client` → deprecated markieren
- Legacy Adapter in bfagent-llm als `bfagent_llm.adapters` behalten (MCP-Server)
- `AIUsageLog` Retention: Management Command `cleanup_usage_logs --days=90`
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

### 5.4 Globaler Default-Fallback (is_default=True Model)

Abgelehnt: Stiller Fallback auf "irgendeinen" Default ist gefährlich.
Sicherheitskritische Actions (hazard_analysis) könnten auf ein
Budget-Model fallen. Expliziter Fehler ist besser.

### 5.5 tenant_id auf LLMProvider/LLMModel

Abgelehnt: Provider und Models sind globale Infrastruktur.
Tenant-Isolation erfolgt auf AIActionType-Ebene (welcher Tenant
welches Model für welche Action nutzt).

---

## 6. Review-Protokoll

| # | Befund | Risiko | Maßnahme | Status |
|---|--------|--------|----------|--------|
| R-01 | `tenant_id` fehlt auf AIActionType + AIUsageLog | KRITISCH | tenant_id + unique_together hinzugefügt | ✅ v1 |
| R-02 | `litellm` Dependency-Gewicht | HOCH | Optionale Dep, Version gepinnt, Langfrist-Exit | ✅ v1 |
| R-03 | Stiller globaler Default-Fallback | MITTEL | Stufe 3 entfernt → LLMConfigurationError | ✅ v1 |
| R-04 | DB-Tabellennamen `ai_*` | MITTEL | Prefix `bfllm_` | ✅ v1 |
| R-05 | `_get_api_key()` ignoriert ADR-045 | MITTEL | `read_secret()` Integration | ✅ v1 |
| R-06 | `AIActionType.code` ohne Naming | NIEDRIG | RegexValidator snake_case | ✅ v1 |
| R-07 | `AIUsageLog` ohne Indizes | MITTEL | Composite Indizes + Retention | ✅ v1 |
| R-08 | `init_llm_config` Idempotenz | MITTEL | `update_or_create()` Pflicht | ✅ v1 |
| R-09 | `bfagent_llm.django` Name | NIEDRIG | Umbenannt zu `bfagent_llm.django_app` | ✅ v1 |
| R-10 | Kein Rollback-Plan | HOCH | pg_dump + 2-Schritt-Migration | ✅ v1 |

---

## 7. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-02-26 | Achim Dehnert | v0: Initial Draft — LiteLLM + DB-Models Architektur |
| 2026-02-26 | Achim Dehnert | v1: Review-Fixes — R-01 bis R-10 eingearbeitet (tenant_id, bfllm_ prefix, read_secret, LLMConfigurationError, Indizes, Rollback-Plan, litellm pinning) |
