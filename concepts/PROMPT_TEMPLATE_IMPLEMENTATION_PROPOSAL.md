# Optimaler Implementierungsvorschlag: Prompt-Template-System

**Version:** 2.0 (Post-Review)  
**Datum:** 27. Januar 2026  
**Basis:** Konzeptpapier + Kritische Analyse  
**Status:** Finaler Implementierungsvorschlag

---

## 1. Bewertung des Reviews

### Akzeptierte Kritikpunkte (✅)

| Kritikpunkt | Bewertung | Umsetzung |
|-------------|-----------|-----------|
| **Sicherheits-Architektur fehlt** | 🔴 Kritisch | Neue Security-Sektion |
| **Inkonsistenz mit Master-Architektur** | 🔴 Kritisch | `domain_code` + Lookup |
| **Spec/Derived Trennung** | 🟡 Akzeptiert | `PromptTemplateSpec` |
| **schema_version statt version** | ✅ Akzeptiert | Integer-basiert |
| **Migrator-Pattern** | ✅ Akzeptiert | `PromptTemplateMigrator` |
| **Observability fehlt** | ✅ Akzeptiert | Logging + Metrics |
| **Rate-Limiting/Quotas** | ✅ Akzeptiert | In `LLMConfig` |
| **Caching-Layer** | ✅ Akzeptiert | Optional |
| **Dry-Run Mode** | ✅ Akzeptiert | `dry_run` Parameter |
| **Zeitschätzung** | ✅ Akzeptiert | 24 Tage statt 9 |

### Nicht übernommen (❌)

| Kritikpunkt | Begründung |
|-------------|------------|
| Variables auto-extracted | Explizite Definition ist sicherer |
| AgentSkills.io als Extension | Bleibt optional im Core |

---

## 2. Finale Architektur

```
creative-services/prompts/
├── __init__.py           # Minimale Public API
├── schemas/
│   ├── base.py           # PromptVariable, LLMConfig
│   ├── template.py       # PromptTemplateSpec
│   ├── execution.py      # PromptExecution
│   └── chain.py          # PromptChain
├── security/             # 🆕 NEU
│   ├── validators.py     # Injection Detection
│   └── sanitizers.py     # Input Sanitization
├── registry/
│   ├── protocol.py       # TemplateRegistry Protocol
│   ├── dict_registry.py  # In-Memory
│   └── file_registry.py  # YAML/JSON
├── execution/
│   ├── renderer.py       # Jinja2
│   ├── executor.py       # PromptExecutor
│   └── cache.py          # Caching
├── migration/            # 🆕 NEU
│   └── migrator.py       # Schema Migration
└── observability/        # 🆕 NEU
    ├── events.py         # Structured Logging
    └── metrics.py        # Prometheus
```

---

## 3. Kern-Änderungen aus Review

### 3.1 Security Layer (NEU)

```python
# security/validators.py

INJECTION_PATTERNS = [
    (r'ignore\s+previous\s+instructions?', "instruction_override"),
    (r'you\s+are\s+now\s+a', "role_manipulation"),
    (r'repeat\s+your\s+prompt', "system_extraction"),
]

def check_injection_patterns(text: str) -> None:
    """Raises InjectionDetectedError if pattern found"""
    for pattern, pattern_type in INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            raise InjectionDetectedError(pattern_type)
```

### 3.2 Schema Migration (NEU)

```python
# migration/migrator.py

class PromptTemplateMigrator:
    CURRENT_VERSION = 1
    _migrations = {}
    
    @classmethod
    def migrate(cls, data: dict) -> dict:
        version = data.get("schema_version", 1)
        while version < cls.CURRENT_VERSION:
            fn = cls._migrations.get((version, version + 1))
            data = fn(data)
            version += 1
        return data
```

### 3.3 Observability (NEU)

```python
# observability/events.py

PROMPT_EXECUTION_STARTED = "prompt.execution.started"
PROMPT_EXECUTION_COMPLETED = "prompt.execution.completed"
PROMPT_INJECTION_DETECTED = "prompt.security.injection_detected"

# observability/metrics.py

prompt_executions_total = Counter(
    'prompt_executions_total',
    ['template_key', 'app_name', 'status', 'tier']
)
```

### 3.4 PromptTemplateSpec (Überarbeitet)

```python
class PromptTemplateSpec(BaseModel):
    # IDENTITY
    template_key: str  # Umbenannt von 'key'
    name: str
    schema_version: int = 1  # Umbenannt von 'version'
    
    # TAXONOMY (Database-First)
    domain_code: str = "general"  # Code statt freier String
    tags: list[str] = []
    
    # CONTENT
    system_prompt: str
    user_prompt: str
    variables: list[PromptVariable] = []
    
    # OUTPUT
    output_format: Literal["text", "json", "markdown"] = "text"
    output_schema: Optional[dict] = None
    
    # LLM
    llm_config: LLMConfig  # Umbenannt von 'llm_params'
    
    # SECURITY (NEU)
    requires_review: bool = False
    sanitize_user_input: bool = True
    max_variable_length: int = 10_000
    required_permission: str = "prompt.execute"
    
    # A/B TESTING
    experiment_variant: Optional[str] = None  # Umbenannt
    experiment_weight: float = 1.0
    
    # Validators für Injection Detection
    @field_validator('system_prompt', 'user_prompt')
    def validate_no_injection(cls, v):
        check_injection_patterns(v)
        return v
```

### 3.5 LLMConfig (Erweitert)

```python
class LLMConfig(BaseModel):
    max_tokens: int = 1000
    temperature: float = 0.7
    preferred_tier: Literal["economy", "standard", "premium", "local"] = "standard"
    
    # Cost Control (NEU aus Review)
    max_cost_per_execution: Optional[float] = None
    daily_quota_key: Optional[str] = None
```

### 3.6 Executor mit Dry-Run (Erweitert)

```python
async def execute(
    self,
    template_key: str,
    variables: dict,
    dry_run: bool = False,  # NEU
    **kwargs
) -> PromptExecution:
    # ... validation ...
    
    if dry_run:
        return PromptExecution(
            status=ExecutionStatus.SUCCESS,
            response_content="[DRY RUN]",
            rendered_system_prompt=rendered_system,
            rendered_user_prompt=rendered_user,
        )
    
    # ... LLM call ...
```

---

## 4. Revidierte Roadmap (24 Tage)

| Phase | Tage | Inhalt |
|-------|------|--------|
| **0: Review** | 3 | Security-Design, API-Finalisierung, Test-Plan |
| **1: Core + Security** | 5 | Schemas, Validators, Sanitizers, Unit Tests |
| **2: Storage + Observability** | 4 | Registries, Logging, Metrics |
| **3: Execution** | 4 | Renderer, Executor, Caching, Dry-Run |
| **4: Advanced** | 4 | Vererbung, Partials, Chains |
| **5: Integration** | 4 | Django Adapter, BFAgent Migration, E2E Tests |

---

## 5. Antworten auf offene Fragen

| Frage | Empfehlung |
|-------|------------|
| `key` vs `template_key` | **template_key** - expliziter |
| `parent_key` FK oder String? | **String mit Validierung** |
| A/B Testing automatisch? | **Explizit** via `experiment_variant` |
| Execution Tracking? | **Konfigurierbar**: none/sample/all |
| AgentSkills.io? | **Optional im Core** |
| Chains eigenes Model? | **Ja** - klare Trennung |
| BFAgent Migration? | **Hybrid** - Adapter + schrittweise |

---

## 6. Nächste Schritte

1. **Sofort**: Dieses Dokument als Basis für Implementierung
2. **Phase 0**: Security-Design mit Team reviewen
3. **Phase 1**: Core-Implementierung starten

**Empfehlung**: Mit `schemas/` und `security/` beginnen - das ist die Basis für alles andere.

---

*Implementierungsvorschlag basiert auf Konzeptpapier + kritischer Analyse.*
