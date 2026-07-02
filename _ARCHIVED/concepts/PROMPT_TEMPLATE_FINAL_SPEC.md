# Prompt Template System - Final Specification v1.0

**Status:** ✅ Implementierungsreif  
**Datum:** 27. Januar 2026  
**Package:** `creative-services/prompts`  
**Geschätzte Implementierungszeit:** 26-27 Tage

---

## 1. Executive Summary

Dieses Dokument ist die **finale Spezifikation** für das generische Prompt-Template-System in `creative-services`. Es konsolidiert alle Reviews und Feedback-Runden.

**Kernprinzipien:**
- Platform-agnostisch (kein Django im Core)
- Security-First (Injection Detection, Input Sanitization)
- Database-First (Validierung gegen Lookup-Tables)
- Observable (Structured Logging, Prometheus Metrics)
- Testbar (Dependency Injection, Protocols)

---

## 2. Verzeichnisstruktur

```
packages/creative-services/creative_services/prompts/
├── __init__.py              # Public API exports
├── exceptions.py            # Exception hierarchy
├── schemas/
│   ├── __init__.py
│   ├── variables.py         # PromptVariable
│   ├── llm_config.py        # LLMConfig, RetryConfig
│   ├── template.py          # PromptTemplateSpec
│   ├── execution.py         # PromptExecution
│   └── chain.py             # PromptChain, ChainStep
├── security/
│   ├── __init__.py
│   ├── validators.py        # Injection detection
│   └── sanitizers.py        # Input sanitization
├── registry/
│   ├── __init__.py
│   ├── protocols.py         # TemplateRegistry Protocol
│   ├── dict_registry.py     # In-memory implementation
│   ├── file_registry.py     # YAML/JSON file backend
│   └── domain_codes.py      # Domain validation
├── execution/
│   ├── __init__.py
│   ├── renderer.py          # Jinja2 template rendering
│   ├── executor.py          # Main PromptExecutor
│   ├── cache.py             # Caching protocol & utils
│   └── retry.py             # Retry configuration
├── observability/
│   ├── __init__.py
│   ├── events.py            # Structured event names
│   └── metrics.py           # Prometheus metrics
├── migration/
│   ├── __init__.py
│   └── migrator.py          # Schema version migration
└── adapters/
    ├── __init__.py
    └── bfagent_compat.py    # BFAgent compatibility layer
```

---

## 3. Exception Hierarchy

```python
# exceptions.py

class PromptSystemError(Exception):
    """Base exception for prompt system."""
    pass

class TemplateNotFoundError(PromptSystemError):
    """Template key not found in registry."""
    def __init__(self, template_key: str):
        self.template_key = template_key
        super().__init__(f"Template not found: {template_key}")

class TemplateValidationError(PromptSystemError):
    """Template failed validation."""
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__(f"Template validation failed: {errors}")

class InjectionDetectedError(PromptSystemError):
    """Potential prompt injection detected."""
    def __init__(self, pattern_type: str, pattern: str = "", value: str = ""):
        self.pattern_type = pattern_type
        self.pattern = pattern
        self.value = value[:100]  # Truncate for logging
        super().__init__(f"Injection pattern detected: {pattern_type}")

class VariableMissingError(PromptSystemError):
    """Required variable not provided."""
    def __init__(self, missing: list[str]):
        self.missing = missing
        super().__init__(f"Missing required variables: {missing}")

class VariableLengthExceededError(PromptSystemError):
    """Variable exceeds maximum length."""
    def __init__(self, variable_name: str, actual: int, maximum: int):
        self.variable_name = variable_name
        super().__init__(f"Variable '{variable_name}' exceeds max: {actual} > {maximum}")

class DomainNotFoundError(PromptSystemError):
    """Domain code not found in registry."""
    def __init__(self, domain_code: str, valid_codes: set[str]):
        self.domain_code = domain_code
        super().__init__(f"Unknown domain_code '{domain_code}'. Valid: {sorted(valid_codes)}")

class ExecutionError(PromptSystemError):
    """Error during prompt execution."""
    pass

class ContextLimitExceededError(ExecutionError):
    """Prompt exceeds model context limit."""
    def __init__(self, estimated_tokens: int, available_tokens: int):
        super().__init__(f"Context exceeded: ~{estimated_tokens} tokens, {available_tokens} available")

class QuotaExceededError(ExecutionError):
    """Cost or rate quota exceeded."""
    def __init__(self, quota_type: str, current: float, limit: float):
        super().__init__(f"{quota_type} quota exceeded: {current:.4f} >= {limit:.4f}")

class LLMError(ExecutionError):
    """Error from LLM provider."""
    pass

class RateLimitError(LLMError):
    """Rate limit hit on LLM provider."""
    def __init__(self, provider: str, retry_after: float | None = None):
        msg = f"Rate limit hit on {provider}"
        if retry_after:
            msg += f", retry after {retry_after}s"
        super().__init__(msg)

class LLMTimeoutError(LLMError):
    """Timeout waiting for LLM response."""
    def __init__(self, provider: str, timeout_seconds: float):
        super().__init__(f"Timeout after {timeout_seconds}s on {provider}")
```

---

## 4. Security Layer

### 4.1 Validators (security/validators.py)

```python
import re
import unicodedata
from ..exceptions import InjectionDetectedError

def normalize_text(text: str) -> str:
    """Normalize text for pattern matching."""
    # Remove zero-width characters
    text = ''.join(c for c in text if unicodedata.category(c) != 'Cf')
    # Unicode NFKC normalization
    text = unicodedata.normalize('NFKC', text)
    # Collapse whitespace
    text = ' '.join(text.split())
    # Replace leetspeak
    leetspeak = {'0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's', '7': 't', '@': 'a'}
    for old, new in leetspeak.items():
        text = text.replace(old, new)
    return text.lower()

INJECTION_PATTERNS: list[tuple[str, str]] = [
    # Instruction Override
    (r'ignore.*previous.*instruction', "instruction_override"),
    (r'disregard.*above', "instruction_override"),
    (r'forget.*everything', "instruction_override"),
    # Role Manipulation
    (r'you\s+are\s+(now\s+)?a', "role_manipulation"),
    (r'act\s+as\s+(if\s+you\s+are\s+)?a', "role_manipulation"),
    (r'pretend\s+(to\s+be|you\s+are)', "role_manipulation"),
    # System Extraction
    (r'repeat.*system.*prompt', "system_extraction"),
    (r'what.*your.*instructions', "system_extraction"),
    (r'show.*hidden.*prompt', "system_extraction"),
    # Jailbreak
    (r'dan\s+mode', "jailbreak"),
    (r'developer\s+mode', "jailbreak"),
    (r'bypass.*filter', "jailbreak"),
]

def check_injection_patterns(text: str, raise_on_detect: bool = True) -> list[tuple[str, str]]:
    """Check text for known injection patterns."""
    normalized = normalize_text(text)
    detected = []
    for pattern, pattern_type in INJECTION_PATTERNS:
        if re.search(pattern, normalized):
            if raise_on_detect:
                raise InjectionDetectedError(pattern_type, pattern, text)
            detected.append((pattern_type, pattern))
    return detected
```

### 4.2 Sanitizers (security/sanitizers.py)

```python
import html

def sanitize_for_prompt(text: str, max_length: int | None = None) -> str:
    """Sanitize text for safe inclusion in prompts."""
    # Remove control chars except newlines/tabs
    text = ''.join(c for c in text if c in '\n\t' or (ord(c) >= 32 and ord(c) != 127))
    if max_length and len(text) > max_length:
        text = text[:max_length - 15] + "...[truncated]"
    return text

def sanitize_variables(variables: dict, max_length: int = 10000) -> dict:
    """Sanitize all string variables in a dict."""
    return {
        k: sanitize_for_prompt(v, max_length) if isinstance(v, str) else v
        for k, v in variables.items()
    }
```

---

## 5. Core Schemas

### 5.1 LLMConfig (schemas/llm_config.py)

```python
from pydantic import BaseModel, Field

class RetryConfig(BaseModel):
    max_attempts: int = Field(default=3, ge=1, le=10)
    min_wait_seconds: float = Field(default=1.0)
    max_wait_seconds: float = Field(default=30.0)
    retry_on_rate_limit: bool = True
    retry_on_timeout: bool = True
    fallback_tier: str | None = None
    model_config = {"frozen": True}

class LLMConfig(BaseModel):
    preferred_tier: str = Field(default="standard")  # economy, standard, premium, reasoning
    max_tokens: int = Field(default=1000, ge=1, le=128000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float | None = None
    timeout_seconds: float = Field(default=60.0)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    response_format: str | None = None  # json_object, json_schema, None
    json_schema: dict | None = None
    model_config = {"frozen": True}
```

### 5.2 PromptTemplateSpec (schemas/template.py)

```python
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

class PromptTemplateSpec(BaseModel):
    # Identity
    template_key: str = Field(..., pattern=r'^[a-z][a-z0-9_\.]*$')
    name: str = Field(..., max_length=200)
    description: str | None = None
    
    # Domain
    domain_code: str = Field(default="general")
    category: str | None = None
    tags: list[str] = Field(default_factory=list)
    
    # Versioning
    schema_version: int = Field(default=1, ge=1)
    
    # Prompts
    system_prompt: str = Field(..., max_length=50000)
    user_prompt: str = Field(..., max_length=50000)
    
    # Variables (typed list)
    variables: list[PromptVariable] = Field(default_factory=list)
    
    # LLM Config
    llm_config: LLMConfig = Field(default_factory=LLMConfig)
    
    # Inheritance
    parent_key: str | None = None
    
    # Security
    sanitize_user_input: bool = True
    max_variable_length: int = Field(default=10000)
    check_injection: bool = True
    
    # Experimentation
    experiment_variant: str | None = None
    
    # Cost Control
    max_cost_per_execution: float | None = None
    daily_quota_key: str | None = None
    
    # Tracking
    track_executions: str = Field(default="sample")  # none, sample, all
    sample_rate: float = Field(default=0.1, ge=0.0, le=1.0)
    
    # Metadata
    author: str | None = None
    is_active: bool = True
    
    # Immutability: Templates sind nach Erstellung unveränderlich.
    # Für Änderungen: template.model_copy(update={"is_active": False})
    model_config = {"frozen": True}
    
    def get_variable_defaults(self) -> dict:
        return {v.name: v.default for v in self.variables if v.default is not None}
    
    def get_required_variables(self) -> list[str]:
        return [v.name for v in self.variables if v.required]
```

### 5.3 PromptExecution (schemas/execution.py)

```python
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

class ExecutionStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    CACHED = "cached"
    DRY_RUN = "dry_run"

class PromptExecution(BaseModel):
    execution_id: UUID = Field(default_factory=uuid4)
    template_key: str
    app_name: str = "unknown"
    user_id: str | None = None
    
    # Input
    variables_provided: dict = Field(default_factory=dict)
    rendered_system_prompt: str = ""
    rendered_user_prompt: str = ""
    
    # Output
    status: ExecutionStatus = ExecutionStatus.PENDING
    response_text: str | None = None
    
    # LLM Info
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_tier: str | None = None
    
    # Metrics
    tokens_input: int = 0
    tokens_output: int = 0
    cost_dollars: float = 0.0
    duration_seconds: float = 0.0
    
    # Error
    error_type: str | None = None
    error_message: str | None = None
    
    # Cache
    from_cache: bool = False
    
    # Timestamps
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    
    @property
    def tokens_total(self) -> int:
        return self.tokens_input + self.tokens_output
```

---

## 6. Observability

### 6.1 Events (observability/events.py)

```python
# Execution lifecycle
PROMPT_EXECUTION_STARTED = "prompt.execution.started"
PROMPT_EXECUTION_COMPLETED = "prompt.execution.completed"
PROMPT_EXECUTION_FAILED = "prompt.execution.failed"
PROMPT_EXECUTION_CACHED = "prompt.execution.cached"

# Security
PROMPT_INJECTION_DETECTED = "prompt.security.injection_detected"

# LLM
PROMPT_LLM_RATE_LIMITED = "prompt.llm.rate_limited"
PROMPT_LLM_TIMEOUT = "prompt.llm.timeout"
PROMPT_LLM_RETRY = "prompt.llm.retry"

# Cache
PROMPT_CACHE_HIT = "prompt.cache.hit"
PROMPT_CACHE_MISS = "prompt.cache.miss"
```

### 6.2 Metrics (observability/metrics.py)

```python
from prometheus_client import Counter, Histogram, Gauge

prompt_executions_total = Counter(
    'prompt_executions_total', 'Total executions',
    ['template_key', 'app_name', 'status', 'tier']
)

prompt_execution_duration_seconds = Histogram(
    'prompt_execution_duration_seconds', 'Duration',
    ['template_key', 'tier'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

prompt_active_executions = Gauge(
    'prompt_active_executions', 'Active executions', ['app_name']
)

prompt_tokens_total = Counter(
    'prompt_tokens_total', 'Tokens used',
    ['template_key', 'direction', 'tier']
)

prompt_cost_dollars_total = Counter(
    'prompt_cost_dollars_total', 'Cost in dollars',
    ['template_key', 'tier', 'provider']
)

prompt_security_events_total = Counter(
    'prompt_security_events_total', 'Security events',
    ['event_type', 'template_key']
)
```

---

## 7. Execution Layer

### 7.1 Cache (execution/cache.py)

```python
from typing import Protocol, Optional
from datetime import timedelta
import hashlib, json

class PromptCache(Protocol):
    async def get(self, key: str) -> Optional[str]: ...
    async def set(self, key: str, value: str, ttl: timedelta = timedelta(hours=1)) -> None: ...

def build_cache_key(template_key: str, variables: dict, llm_config) -> str:
    """Build deterministic cache key. Only for temperature=0."""
    if llm_config.temperature > 0:
        raise ValueError("Cannot cache non-deterministic outputs")
    sorted_vars = json.dumps(variables, sort_keys=True, default=str)
    content = f"{template_key}|{sorted_vars}|{llm_config.max_tokens}"
    return hashlib.sha256(content.encode()).hexdigest()
```

### 7.2 Retry (execution/retry.py)

```python
from tenacity import AsyncRetrying, stop_after_attempt, wait_exponential, retry_if_exception_type
from ..exceptions import RateLimitError, LLMTimeoutError

def create_retry_strategy(config):
    exceptions = []
    if config.retry_on_rate_limit:
        exceptions.append(RateLimitError)
    if config.retry_on_timeout:
        exceptions.append(LLMTimeoutError)
    
    return AsyncRetrying(
        stop=stop_after_attempt(config.max_attempts),
        wait=wait_exponential(min=config.min_wait_seconds, max=config.max_wait_seconds),
        retry=retry_if_exception_type(tuple(exceptions)) if exceptions else lambda _: False,
        reraise=True,
    )
```

### 7.3 Executor (execution/executor.py) - Kurzfassung

```python
class PromptExecutor:
    """Thread-safe prompt executor with full observability."""
    
    def __init__(self, llm_client, registry, cache=None, app_name="unknown"):
        self.llm_client = llm_client
        self.registry = registry
        self.cache = cache
        self.app_name = app_name
    
    async def execute(
        self,
        template_key: str,
        variables: dict,
        dry_run: bool = False,
        skip_cache: bool = False,
        user_id: str | None = None,
        **llm_overrides,
    ) -> PromptExecution:
        """
        Execute a prompt template.
        
        Steps:
        1. Get template from registry
        2. Validate variables
        3. Sanitize & check injection
        4. Merge with defaults
        5. Render prompts (Jinja2)
        6. Check context limits
        7. Check cache
        8. Execute LLM call with retry
        9. Track metrics
        10. Return PromptExecution
        """
        # ... (vollständige Implementierung siehe vorheriges Dokument)
```

---

## 8. Migration Layer

```python
# migration/migrator.py

class PromptTemplateMigrator:
    CURRENT_VERSION = 1
    
    def __init__(self):
        self._migrations: dict[tuple[int, int], callable] = {}
    
    def register(self, from_version: int, to_version: int):
        """Decorator to register migration function."""
        def decorator(func):
            self._migrations[(from_version, to_version)] = func
            return func
        return decorator
    
    def migrate(self, data: dict, target_version: int | None = None) -> dict:
        """Migrate data to target version."""
        target = target_version or self.CURRENT_VERSION
        current = data.get('schema_version', 1)
        
        result = data.copy()
        while current < target:
            next_v = current + 1
            result = self._migrations[(current, next_v)](result)
            result['schema_version'] = next_v
            current = next_v
        return result
```

---

## 9. Test-Strategie

### 9.1 Test-Kategorien

| Kategorie | Fokus | Beispiele |
|-----------|-------|-----------|
| **Unit** | Schemas, Validators | Variable validation, Injection patterns |
| **Integration** | Executor, Registry | Happy path, Error handling |
| **Security** | Bypass-Versuche | Unicode, Leetspeak, Length |
| **Performance** | Latenz, Throughput | Large variables, Cache |

### 9.2 Test-Fixtures

```python
# tests/conftest.py

@pytest.fixture
def mock_registry():
    return DictTemplateRegistry.from_dict({
        "test.simple": {...},
        "test.with_variables": {...},
        "test.injection": {...},
    })

@pytest.fixture
def mock_llm_client():
    """Mock LLM that returns predictable responses."""
    class MockLLMClient:
        async def generate(self, prompt: str, config: LLMConfig) -> str:
            return f"Mock response for: {prompt[:50]}..."
        
        def estimate_tokens(self, text: str) -> int:
            return len(text) // 4  # ~4 chars per token
    
    return MockLLMClient()

@pytest.fixture
def executor(mock_registry, mock_llm_client):
    return PromptExecutor(
        llm_client=mock_llm_client,
        registry=mock_registry,
        app_name="test",
    )
```

---

## 10. Roadmap

| Phase | Tage | Fokus |
|-------|------|-------|
| **0: Review** | 3 | Security-Design finalisieren, Test-Strategie |
| **1: Core + Security** | 5.5 | Schemas, Exceptions, Validators, Sanitizers |
| **2: Storage + Observability** | 5 | Registry, Events, Metrics, Retry |
| **3: Execution** | 4 | Renderer, Executor, Cache |
| **4: Advanced** | 4 | Vererbung, Chains, Partials |
| **5: Integration** | 5 | BFAgent Adapter, E2E Tests |

**Gesamt: 26.5 Tage**

---

## 11. Entscheidungslog

| Entscheidung | Begründung |
|--------------|------------|
| `template_key` statt `key` | Eindeutiger, selbstdokumentierend |
| `schema_version` Integer | Einfache Migration, keine Semver-Komplexität |
| Tier-basierte LLM-Auswahl | Flexibel, keine harten FK-Abhängigkeiten |
| Eigene Exception-Hierarchie | Klares Error-Handling, testbar |
| `normalize_text()` für Injection | Robuster gegen Bypass-Versuche |
| Protocol für Cache | Austauschbare Backends (Redis, Memory) |
| Retry im LLMConfig | Konfiguration pro Template möglich |
| `frozen=True` für Templates | Immutability, Audit-Trail, Thread-Safety |
| Domain-Validierung im Registry | Frühe Fehler beim Speichern, Schema bleibt DB-agnostisch |

---

*Dokument abgeschlossen. Bereit für Implementierung.*
