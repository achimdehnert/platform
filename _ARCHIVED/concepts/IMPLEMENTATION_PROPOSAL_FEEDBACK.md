# Feedback: Implementierungsvorschlag v2.0

**Review-Datum:** 27. Januar 2026  
**Dokument:** PROMPT_TEMPLATE_IMPLEMENTATION_PROPOSAL.md  
**Gesamtbewertung:** 🟢 **Gut - mit kleineren Anpassungen umsetzbar**

---

## Executive Summary

Der Implementierungsvorschlag hat die **wesentlichen Kritikpunkte** aus dem Review aufgenommen und sinnvoll integriert. Die Architektur ist nun **konsistenter mit der Master-Architektur** und adressiert die kritischen Sicherheitslücken.

| Aspekt | Vorher | Nachher | Status |
|--------|--------|---------|--------|
| Security | ❌ Fehlend | ✅ Eigener Layer | Gelöst |
| Schema-Migration | ❌ Fehlend | ✅ Migrator-Pattern | Gelöst |
| Observability | ❌ Fehlend | ✅ Events + Metrics | Gelöst |
| Database-First | ❌ Inkonsistent | 🟡 Teilweise | Nachbesserung |
| Zeitschätzung | ❌ 9 Tage | ✅ 24 Tage | Realistisch |

---

## 1. Positiv: Gut umgesetzte Änderungen ✅

### 1.1 Security Layer
```
prompts/security/
├── validators.py     # Injection Detection
└── sanitizers.py     # Input Sanitization
```
**Bewertung:** Exzellent. Eigenes Modul statt inline-Validators macht den Code testbar und erweiterbar.

### 1.2 Schema-Migration
```python
class PromptTemplateMigrator:
    CURRENT_VERSION = 1
    _migrations = {}
```
**Bewertung:** Korrekte Umsetzung des Migrator-Patterns aus der Master-Architektur.

### 1.3 Observability-Integration
```python
PROMPT_EXECUTION_STARTED = "prompt.execution.started"
PROMPT_INJECTION_DETECTED = "prompt.security.injection_detected"
```
**Bewertung:** Gute Event-Struktur. Metrics mit Labels für Prometheus sind korrekt.

### 1.4 Naming-Konsistenz
| Alt | Neu | ✓ |
|-----|-----|---|
| `key` | `template_key` | ✅ |
| `version` | `schema_version` | ✅ |
| `llm_params` | `llm_config` | ✅ |
| `ab_test_group` | `experiment_variant` | ✅ |

### 1.5 Dry-Run Mode
```python
async def execute(..., dry_run: bool = False):
```
**Bewertung:** Wichtig für Testing und Preview - gut integriert.

---

## 2. Kritik: Verbesserungsbedarf 🟡

### 2.1 Injection-Patterns zu simpel

**Problem:** Die gezeigten Patterns sind zu einfach zu umgehen:

```python
# Aktuell:
INJECTION_PATTERNS = [
    (r'ignore\s+previous\s+instructions?', "instruction_override"),
    (r'you\s+are\s+now\s+a', "role_manipulation"),
]

# Bypass-Beispiele:
"Ign0re prev1ous instruct1ons"  # Leetspeak
"ignore    previous instructions"  # Extra Whitespace (nur \s+, nicht \s*)
"Ignore the PREVIOUS set of instructions"  # Wort dazwischen
```

**Empfehlung:** Robustere Pattern-Library + Fuzzy-Matching:

```python
# security/validators.py

import unicodedata

def normalize_text(text: str) -> str:
    """Normalize for pattern matching"""
    # Remove zero-width chars, normalize unicode
    text = unicodedata.normalize('NFKC', text)
    # Collapse whitespace
    text = ' '.join(text.split())
    # Replace common leetspeak
    replacements = {'0': 'o', '1': 'i', '3': 'e', '4': 'a', '@': 'a'}
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.lower()

INJECTION_PATTERNS = [
    # Mehr Varianten
    (r'ignore.*previous.*instruction', "instruction_override"),
    (r'disregard.*above', "instruction_override"),
    (r'forget.*everything', "instruction_override"),
    (r'you\s+are\s+(now\s+)?a', "role_manipulation"),
    (r'act\s+as\s+(if\s+you\s+are\s+)?a', "role_manipulation"),
    (r'pretend\s+(to\s+be|you\s+are)', "role_manipulation"),
    (r'repeat.*system.*prompt', "system_extraction"),
    (r'what.*your.*instructions', "system_extraction"),
    (r'show.*hidden.*prompt', "system_extraction"),
]

def check_injection_patterns(text: str) -> None:
    normalized = normalize_text(text)
    for pattern, pattern_type in INJECTION_PATTERNS:
        if re.search(pattern, normalized):
            raise InjectionDetectedError(pattern_type, pattern)
```

### 2.2 Domain-Lookup nicht vollständig umgesetzt

**Problem:** `domain_code: str = "general"` ist besser als vorher, aber es fehlt die **Validierung gegen die Lookup-Table**.

**Aktuell:**
```python
domain_code: str = "general"  # Code statt freier String
```

**Fehlt:** Validator der gegen existierende Domains prüft:

```python
# In PromptTemplateSpec:

@field_validator('domain_code')
@classmethod
def validate_domain_exists(cls, v: str) -> str:
    # Lazy import to avoid circular dependency
    from creative_services.prompts.registry import get_domain_codes
    
    valid_codes = get_domain_codes()  # Cached lookup
    if v not in valid_codes:
        raise ValueError(
            f"Unknown domain_code '{v}'. Valid: {valid_codes}"
        )
    return v

# In registry/__init__.py:
_domain_codes_cache: set[str] | None = None

def get_domain_codes() -> set[str]:
    global _domain_codes_cache
    if _domain_codes_cache is None:
        # Load from config/DB
        _domain_codes_cache = {"general", "writing", "travel", "cad", "research"}
    return _domain_codes_cache
```

### 2.3 Fehlende Error-Typen

**Problem:** Keine definierten Exception-Klassen im Vorschlag.

**Empfehlung:** Eigene Exception-Hierarchie:

```python
# exceptions.py

class PromptSystemError(Exception):
    """Base exception for prompt system"""
    pass

class TemplateNotFoundError(PromptSystemError):
    """Template key not found in registry"""
    def __init__(self, template_key: str):
        self.template_key = template_key
        super().__init__(f"Template not found: {template_key}")

class TemplateValidationError(PromptSystemError):
    """Template failed validation"""
    pass

class InjectionDetectedError(PromptSystemError):
    """Potential prompt injection detected"""
    def __init__(self, pattern_type: str, pattern: str = ""):
        self.pattern_type = pattern_type
        self.pattern = pattern
        super().__init__(f"Injection pattern detected: {pattern_type}")

class VariableMissingError(PromptSystemError):
    """Required variable not provided"""
    def __init__(self, missing: list[str]):
        self.missing = missing
        super().__init__(f"Missing required variables: {missing}")

class ExecutionError(PromptSystemError):
    """Error during prompt execution"""
    pass

class QuotaExceededError(ExecutionError):
    """Cost or rate quota exceeded"""
    pass
```

### 2.4 Cache-Strategie nicht definiert

**Problem:** `execution/cache.py` ist im Verzeichnis, aber keine Strategie definiert.

**Empfehlung:** Cache-Design spezifizieren:

```python
# execution/cache.py

from typing import Protocol
from datetime import timedelta

class PromptCache(Protocol):
    """Protocol for prompt response caching"""
    
    async def get(self, key: str) -> Optional[str]:
        """Get cached response"""
        ...
    
    async def set(
        self, 
        key: str, 
        value: str, 
        ttl: timedelta = timedelta(hours=1)
    ) -> None:
        """Cache response with TTL"""
        ...

def build_cache_key(
    template_key: str, 
    variables: dict,
    llm_config: LLMConfig
) -> str:
    """
    Build deterministic cache key.
    
    Note: Only cache for deterministic configs (temperature=0)
    """
    if llm_config.temperature > 0:
        raise ValueError("Cannot cache non-deterministic outputs")
    
    # Sort variables for consistent key
    sorted_vars = json.dumps(variables, sort_keys=True)
    content = f"{template_key}:{sorted_vars}:{llm_config.max_tokens}"
    return hashlib.sha256(content.encode()).hexdigest()
```

### 2.5 Metrics unvollständig

**Problem:** Nur `Counter` definiert, keine Histogramme für Latenz.

**Ergänzung:**
```python
# observability/metrics.py

from prometheus_client import Counter, Histogram, Gauge

# Execution counts
prompt_executions_total = Counter(
    'prompt_executions_total',
    'Total prompt executions',
    ['template_key', 'app_name', 'status', 'tier']
)

# Latency distribution
prompt_execution_duration_seconds = Histogram(
    'prompt_execution_duration_seconds',
    'Prompt execution duration',
    ['template_key', 'tier'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

# Token usage
prompt_tokens_total = Counter(
    'prompt_tokens_total',
    'Total tokens used',
    ['template_key', 'direction']  # direction: input/output
)

# Cost tracking
prompt_cost_dollars_total = Counter(
    'prompt_cost_dollars_total',
    'Total cost in dollars',
    ['template_key', 'tier', 'provider']
)

# Active executions (for rate limiting visibility)
prompt_active_executions = Gauge(
    'prompt_active_executions',
    'Currently running executions',
    ['app_name']
)
```

---

## 3. Fehlend: Übersehene Aspekte 🔴

### 3.1 Keine Retry-Strategie definiert

**Problem:** Was passiert bei LLM-Fehlern? Rate-Limits? Timeouts?

**Empfehlung:**
```python
# execution/retry.py

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

class RetryConfig(BaseModel):
    max_attempts: int = 3
    min_wait_seconds: float = 1.0
    max_wait_seconds: float = 30.0
    retry_on_rate_limit: bool = True
    retry_on_timeout: bool = True
    fallback_tier: Optional[str] = None  # Downgrade bei Fehler

def get_retry_decorator(config: RetryConfig):
    return retry(
        stop=stop_after_attempt(config.max_attempts),
        wait=wait_exponential(
            min=config.min_wait_seconds,
            max=config.max_wait_seconds
        ),
        retry=retry_if_exception_type(
            (RateLimitError, TimeoutError)
        )
    )
```

### 3.2 Keine Context-Limits

**Problem:** Was wenn `system_prompt + user_prompt + variables` das Context-Window sprengt?

**Empfehlung:**
```python
# In executor.py

def _check_context_limits(
    self,
    rendered_system: str,
    rendered_user: str,
    llm_config: LLMConfig
) -> None:
    """Validate total context fits in model limits"""
    
    # Rough token estimation (4 chars ≈ 1 token)
    estimated_input_tokens = (len(rendered_system) + len(rendered_user)) // 4
    
    # Get model limits from registry
    model_limit = self.llm_client.get_context_limit(llm_config.preferred_tier)
    
    # Reserve space for output
    available = model_limit - llm_config.max_tokens
    
    if estimated_input_tokens > available:
        raise ContextLimitExceededError(
            estimated=estimated_input_tokens,
            available=available,
            suggestion="Reduce prompt length or max_tokens"
        )
```

### 3.3 Keine Concurrency-Kontrolle

**Problem:** Parallele Ausführungen desselben Templates - Race Conditions bei A/B Testing?

**Empfehlung:** Mindestens dokumentieren, ob Thread-Safe:

```python
class PromptExecutor:
    """
    Thread-safe prompt executor.
    
    Note: Registry lookups are cached and thread-safe.
    LLM client handles its own connection pooling.
    Metrics are thread-safe (prometheus_client).
    
    NOT thread-safe:
    - Modifying registry during execution
    - Changing executor config during execution
    """
```

### 3.4 Test-Strategie fehlt

**Problem:** Kein Test-Plan im Dokument.

**Empfehlung:** Test-Matrix definieren:

```python
# tests/conftest.py - Fixtures

@pytest.fixture
def mock_registry():
    """In-memory registry with test templates"""
    return DictTemplateRegistry.from_dict({
        "test.simple": {...},
        "test.with_variables": {...},
        "test.with_injection": {...},  # Für Security-Tests
    })

@pytest.fixture
def mock_llm_client():
    """Mock LLM that returns predictable responses"""
    ...

# Test-Kategorien:

# 1. Unit Tests (schemas/)
# - PromptVariable validation
# - PromptTemplateSpec validation
# - Injection pattern detection
# - Schema migration

# 2. Integration Tests (execution/)
# - Renderer with partials
# - Executor happy path
# - Executor with validation errors
# - Executor with LLM errors
# - Caching behavior

# 3. Security Tests
# - Known injection patterns
# - Unicode normalization bypass attempts
# - Variable length limits
# - Permission checks

# 4. Performance Tests
# - Large variable rendering
# - Registry lookup speed
# - Cache hit/miss rates
```

---

## 4. Roadmap-Feedback

### Phase 0: Review (3 Tage) ✅
**Bewertung:** Sinnvoll. Security-Design vorab klären ist wichtig.

### Phase 1: Core + Security (5 Tage) 🟡
**Anpassung:** Exception-Klassen hinzufügen (+ 0.5 Tage)

### Phase 2: Storage + Observability (4 Tage) 🟡
**Anpassung:** Vollständige Metrics + Retry-Strategie (+ 1 Tag)

### Phase 3: Execution (4 Tage) ✅
**Bewertung:** Realistisch mit Cache-Design.

### Phase 4: Advanced (4 Tage) ✅
**Bewertung:** OK für Vererbung + Chains.

### Phase 5: Integration (4 Tage) 🟡
**Anpassung:** E2E Tests brauchen mehr Zeit wenn kein Test-Plan existiert (+ 1 Tag)

**Revidierte Schätzung: 26-27 Tage**

---

## 5. Entscheidungs-Review

### "Nicht übernommen" - Meine Einschätzung

| Entscheidung | Ihre Begründung | Mein Kommentar |
|--------------|-----------------|----------------|
| Variables nicht auto-extracted | "Explizit ist sicherer" | ✅ **Einverstanden** - Auto-Extraction ist fehleranfällig |
| AgentSkills.io im Core | "Bleibt optional" | 🟡 **OK, aber**: Klares Interface definieren |

### Offene Fragen - Mein Feedback

| Frage | Ihre Antwort | Kommentar |
|-------|--------------|-----------|
| `template_key` | ✅ | Richtige Wahl |
| `parent_key` String | ✅ | Mit Validierung korrekt |
| A/B explizit | ✅ | Feature-Flags sind besser |
| Tracking konfigurierbar | ✅ | `none/sample/all` ist gut |
| Chains eigenes Model | ✅ | Separation of Concerns |
| BFAgent Hybrid | ✅ | Schrittweise Migration reduziert Risiko |

---

## 6. Konkrete Empfehlungen

### Sofort umsetzen (vor Phase 1)

1. **Exception-Hierarchie definieren** - Basis für Error-Handling
2. **Injection-Patterns erweitern** - Robuster machen
3. **Domain-Validator hinzufügen** - Database-First vollständig umsetzen
4. **Test-Strategie dokumentieren** - Vor Implementierung

### In Phase 1 ergänzen

5. **Retry-Config** in `LLMConfig` integrieren
6. **Context-Limit-Check** im Executor
7. **Vollständige Metrics** (Histogram, Gauge)

### In Phase 2 ergänzen

8. **Cache-Interface** spezifizieren
9. **Thread-Safety** dokumentieren

---

## 7. Fazit

**Gesamtbewertung: 🟢 Gut**

Der Implementierungsvorschlag ist eine **solide Basis** und hat die kritischen Punkte aus dem Review adressiert. Mit den oben genannten Ergänzungen ist er **implementierungsreif**.

**Prioritäten für Nachbesserung:**

| Prio | Item | Aufwand |
|------|------|---------|
| 🔴 1 | Injection-Patterns robuster | 2h |
| 🔴 2 | Exception-Hierarchie | 1h |
| 🟡 3 | Domain-Validator | 1h |
| 🟡 4 | Test-Strategie | 2h |
| 🟢 5 | Retry-Config | 1h |
| 🟢 6 | Context-Limits | 1h |

**Empfehlung:** Mit diesen ~8h Nacharbeit kann Phase 1 starten.

---

## 8. Beispiel: Finaler Executor mit allen Ergänzungen

```python
# execution/executor.py

from contextlib import asynccontextmanager
from typing import Optional
import structlog

from ..schemas import PromptTemplateSpec, PromptExecution, ExecutionStatus
from ..security import check_injection_patterns, sanitize_variables
from ..observability import (
    prompt_executions_total,
    prompt_execution_duration_seconds,
    prompt_active_executions,
    PROMPT_EXECUTION_STARTED,
    PROMPT_EXECUTION_COMPLETED,
)
from ..exceptions import (
    TemplateNotFoundError,
    VariableMissingError,
    ContextLimitExceededError,
    QuotaExceededError,
)
from .cache import PromptCache, build_cache_key
from .retry import get_retry_decorator

logger = structlog.get_logger(__name__)


class PromptExecutor:
    """
    Execute prompt templates with full observability.
    
    Thread-safe for concurrent executions.
    """
    
    def __init__(
        self,
        llm_client: "DynamicLLMClient",
        registry: "TemplateRegistry",
        cache: Optional[PromptCache] = None,
        app_name: str = "unknown",
    ):
        self.llm_client = llm_client
        self.registry = registry
        self.cache = cache
        self.app_name = app_name
    
    @asynccontextmanager
    async def _execution_context(self, template_key: str, tier: str):
        """Context manager for metrics and logging"""
        prompt_active_executions.labels(app_name=self.app_name).inc()
        
        with prompt_execution_duration_seconds.labels(
            template_key=template_key,
            tier=tier
        ).time():
            try:
                yield
            finally:
                prompt_active_executions.labels(app_name=self.app_name).dec()
    
    async def execute(
        self,
        template_key: str,
        variables: dict,
        dry_run: bool = False,
        skip_cache: bool = False,
        user_id: Optional[str] = None,
        **llm_overrides,
    ) -> PromptExecution:
        """
        Execute a prompt template.
        
        Args:
            template_key: Template identifier
            variables: Variables to render
            dry_run: If True, render but don't call LLM
            skip_cache: If True, bypass cache
            user_id: For quota tracking
            **llm_overrides: Override LLM config
        
        Returns:
            PromptExecution with results
        
        Raises:
            TemplateNotFoundError: Template not in registry
            VariableMissingError: Required variables missing
            InjectionDetectedError: Injection pattern in variables
            ContextLimitExceededError: Prompt too long
            QuotaExceededError: Cost/rate limit exceeded
        """
        
        logger.info(
            PROMPT_EXECUTION_STARTED,
            template_key=template_key,
            dry_run=dry_run,
            user_id=user_id,
        )
        
        # 1. Get template
        template = self.registry.get(template_key)
        if not template:
            raise TemplateNotFoundError(template_key)
        
        # 2. Validate variables
        missing = template.validate_provided_variables(variables)
        if missing:
            raise VariableMissingError(missing)
        
        # 3. Security: Sanitize & check injection
        if template.sanitize_user_input:
            variables = sanitize_variables(
                variables, 
                max_length=template.max_variable_length
            )
        
        for key, value in variables.items():
            if isinstance(value, str):
                check_injection_patterns(value)
        
        # 4. Merge with defaults
        final_vars = {**template.get_variable_defaults(), **variables}
        
        # 5. Render prompts
        rendered_system = self._render(template.system_prompt, final_vars)
        rendered_user = self._render(template.user_prompt, final_vars)
        
        # 6. Resolve LLM config
        llm_config = template.llm_config.model_copy(update=llm_overrides)
        tier = llm_config.preferred_tier
        
        # 7. Check context limits
        self._check_context_limits(rendered_system, rendered_user, llm_config)
        
        # 8. Check cache (if not dry_run)
        if not dry_run and not skip_cache and self.cache:
            try:
                cache_key = build_cache_key(template_key, final_vars, llm_config)
                cached = await self.cache.get(cache_key)
                if cached:
                    logger.info("Cache hit", template_key=template_key)
                    return self._build_execution(
                        template, rendered_system, rendered_user,
                        cached, final_vars, from_cache=True
                    )
            except ValueError:
                pass  # Non-deterministic config, skip cache
        
        # 9. Dry run?
        if dry_run:
            return self._build_execution(
                template, rendered_system, rendered_user,
                "[DRY RUN - No LLM call]", final_vars, dry_run=True
            )
        
        # 10. Execute LLM call with metrics
        async with self._execution_context(template_key, tier):
            response = await self._call_llm_with_retry(
                rendered_system, rendered_user, llm_config
            )
        
        # 11. Cache response
        if self.cache and llm_config.temperature == 0:
            cache_key = build_cache_key(template_key, final_vars, llm_config)
            await self.cache.set(cache_key, response.content)
        
        # 12. Build and return execution
        execution = self._build_execution(
            template, rendered_system, rendered_user,
            response.content, final_vars,
            tokens_input=response.usage.input_tokens,
            tokens_output=response.usage.output_tokens,
            cost=response.cost,
            llm_model=response.model,
        )
        
        # 13. Track metrics
        prompt_executions_total.labels(
            template_key=template_key,
            app_name=self.app_name,
            status="success",
            tier=tier,
        ).inc()
        
        logger.info(
            PROMPT_EXECUTION_COMPLETED,
            template_key=template_key,
            tokens_total=response.usage.total_tokens,
            cost=response.cost,
        )
        
        return execution
```

---

*Feedback abgeschlossen. Bereit für Implementierung nach Nachbesserungen.*
