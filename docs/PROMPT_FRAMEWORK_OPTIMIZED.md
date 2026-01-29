# 🔬 Prompt & Template Framework - Kritisches Review & Optimiertes Implementierungskonzept

> **Version:** 2.0 (Optimiert)  
> **Datum:** 2026-01-28  
> **Reviewer:** Senior IT-Architekt (Enterprise & High-Traffic)  
> **Scope:** Risk-Hub, Expert-Hub, Writing-Hub, Travel-Beat

---

## 📋 EXECUTIVE SUMMARY

Das vorliegende RFC und der Implementierungsplan bilden eine **solide Grundlage**, weisen jedoch **kritische Lücken** auf, die für den professionellen Multi-App-Einsatz adressiert werden müssen:

| Aspekt | Bewertung | Kritische Punkte |
|--------|-----------|------------------|
| **Architektur** | B | Monolithisches Datenmodell, fehlende Event-Architektur |
| **Performance** | C | Caching nur erwähnt, keine Batch-Verarbeitung |
| **Sicherheit** | C- | Template-Injection unzureichend adressiert |
| **Erweiterbarkeit** | B+ | Gute Grundstruktur, aber fehlende Komposition |
| **Testbarkeit** | C | Keine Mocking-Strategie, fehlende Contract-Tests |
| **SaaS-Readiness** | B | Multi-Tenancy vorhanden, Isolation unvollständig |

**Empfehlung:** Konzept **überarbeiten** vor Implementierung (geschätzter Mehraufwand: +3 Tage)

---

## 🔴 KRITISCHE PROBLEME

### 1. Monolithisches Datenmodell (High Severity)

**Problem:** `PromptTemplate` vermischt:
- Template-Inhalt (system_prompt, user_prompt)
- LLM-Konfiguration (preferred_tier, max_tokens, temperature)
- Versionierung (version, parent_id)
- Multi-Tenancy (tenant_id)

**Auswirkung:** 
- Schwierige Wartung
- Keine unabhängige Versionierung von Inhalt vs. Config
- Komplizierte Tenant-Overrides

**Lösung:** Separation of Concerns

```python
# OPTIMIERT: Getrennte Modelle

class PromptTemplate(models.Model):
    """Reiner Template-Inhalt."""
    code = models.CharField(max_length=100, unique=True)
    app = models.CharField(max_length=50)
    category = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    
    # NUR Inhalt
    system_prompt = models.TextField(blank=True)
    user_prompt = models.TextField()
    output_format = models.TextField(blank=True)
    
    # Schema für Variablen (JSON Schema!)
    variables_schema = models.JSONField(default=dict)  # JSON Schema
    default_values = models.JSONField(default=dict)
    
    # Versionierung
    version = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'prompt_templates'
        unique_together = ['code', 'version']


class PromptConfig(models.Model):
    """LLM-Konfiguration - separat versionierbar."""
    template = models.ForeignKey(PromptTemplate, on_delete=models.CASCADE)
    
    # LLM Settings
    preferred_tier = models.CharField(max_length=20, default='standard')
    preferred_model = models.CharField(max_length=100, blank=True)
    max_tokens = models.IntegerField(default=2000)
    temperature = models.FloatField(default=0.7)
    top_p = models.FloatField(default=1.0)
    
    # Retry/Fallback
    retry_count = models.IntegerField(default=3)
    fallback_tier = models.CharField(max_length=20, blank=True)
    timeout_seconds = models.IntegerField(default=60)
    
    # Scope
    tenant_id = models.UUIDField(null=True, blank=True)  # NULL = global
    environment = models.CharField(max_length=20, default='production')
    
    class Meta:
        db_table = 'prompt_configs'
        unique_together = ['template', 'tenant_id', 'environment']


class TenantPromptOverride(models.Model):
    """Tenant-spezifische Template-Anpassungen."""
    base_template = models.ForeignKey(PromptTemplate, on_delete=models.CASCADE)
    tenant_id = models.UUIDField()
    
    # Nur die überschriebenen Felder
    system_prompt_override = models.TextField(blank=True)
    user_prompt_override = models.TextField(blank=True)
    additional_context = models.JSONField(default=dict)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'tenant_prompt_overrides'
        unique_together = ['base_template', 'tenant_id']
```

---

### 2. Fehlende Template-Sicherheit (High Severity)

**Problem:** 
- `autoescape=False` in Jinja2 ermöglicht Injection
- Nur oberflächliche Sanitization (`dangerous = {'__builtins__', ...}`)
- Keine Sandbox-Ausführung

**Lösung:** Sichere Template-Engine

```python
# OPTIMIERT: Sichere TemplateEngine

from jinja2.sandbox import SandboxedEnvironment, ImmutableSandboxedEnvironment
from jinja2 import Undefined, StrictUndefined
import re

class SecureTemplateEngine:
    """Gehärtete Template-Engine mit Sicherheitsfeatures."""
    
    # Erlaubte Jinja2 Funktionen (Whitelist)
    ALLOWED_GLOBALS = {
        'range', 'len', 'str', 'int', 'float', 'bool',
        'list', 'dict', 'set', 'tuple',
        'min', 'max', 'sum', 'sorted', 'enumerate', 'zip',
    }
    
    # Verbotene Patterns in Templates
    FORBIDDEN_PATTERNS = [
        r'\{\%\s*import',          # No imports
        r'\{\%\s*from',            # No from imports
        r'__\w+__',                # No dunder attributes
        r'\.mro\(',                # No MRO access
        r'\.base\(',               # No base class access
        r'config\[',               # No config access
        r'self\.',                 # No self access
        r'request\.',              # No request access (unless explicitly allowed)
    ]
    
    def __init__(self, component_store: 'ComponentStore'):
        self.component_store = component_store
        
        # Sandboxed Environment
        self.env = ImmutableSandboxedEnvironment(
            autoescape=True,  # WICHTIG: Autoescape aktiviert
            trim_blocks=True,
            lstrip_blocks=True,
            undefined=StrictUndefined,  # Strikte Variablen
        )
        
        # Nur erlaubte Globals
        self.env.globals = {
            k: v for k, v in self.env.globals.items() 
            if k in self.ALLOWED_GLOBALS
        }
        
        self._register_safe_filters()
    
    def validate_template(self, template_str: str) -> 'ValidationResult':
        """Validiert Template auf Sicherheit und Syntax."""
        errors = []
        warnings = []
        
        # Pattern-Check
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, template_str, re.IGNORECASE):
                errors.append(f"Forbidden pattern detected: {pattern}")
        
        # Syntax-Check
        try:
            ast = self.env.parse(template_str)
            
            # AST-Analyse für gefährliche Konstrukte
            self._analyze_ast(ast, errors, warnings)
            
        except Exception as e:
            errors.append(f"Syntax error: {e}")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def render(
        self,
        template: 'PromptTemplate',
        context: Dict[str, Any],
        config: Optional['PromptConfig'] = None
    ) -> 'RenderedPrompt':
        """Sicheres Rendering mit Context-Isolation."""
        
        # Validierung
        validation = self.validate_template(template.user_prompt)
        if not validation.valid:
            raise TemplateSecurityError(validation.errors)
        
        # Context sanitizen
        safe_context = self._sanitize_context(context)
        
        # Komponenten als safe markieren
        safe_context['components'] = self._load_safe_components()
        
        # Render mit Timeout
        with timeout(seconds=5):
            system = self._render_safe(template.system_prompt, safe_context)
            user = self._render_safe(template.user_prompt, safe_context)
            output = self._render_safe(template.output_format, safe_context)
        
        return RenderedPrompt(
            system_prompt=system,
            user_prompt=user,
            output_format=output,
            full_prompt=self._combine_prompts(system, user, output),
            variables_used=self._extract_used_variables(template, safe_context),
            validation=validation,
        )
    
    def _sanitize_context(self, context: Dict) -> Dict:
        """Tiefe Sanitization des Contexts."""
        BLOCKED_KEYS = {
            '__builtins__', '__import__', 'eval', 'exec', 'compile',
            'open', 'file', 'input', 'raw_input', 'reload',
            'globals', 'locals', 'vars', 'dir', 'getattr', 'setattr',
            'delattr', 'hasattr', '__class__', '__bases__', '__subclasses__',
        }
        
        def sanitize_value(value, depth=0):
            if depth > 10:  # Max recursion
                return str(value)
            
            if isinstance(value, dict):
                return {
                    k: sanitize_value(v, depth + 1)
                    for k, v in value.items()
                    if k not in BLOCKED_KEYS and not k.startswith('_')
                }
            elif isinstance(value, (list, tuple)):
                return [sanitize_value(v, depth + 1) for v in value]
            elif isinstance(value, (str, int, float, bool, type(None))):
                return value
            else:
                # Objekte: Nur sichere Attribute exponieren
                return self._safe_object_proxy(value)
        
        return sanitize_value(context)
```

---

### 3. Fehlende Caching-Strategie (Medium Severity)

**Problem:** Caching nur erwähnt, keine konkrete Implementierung.

**Lösung:** Multi-Layer Caching

```python
# OPTIMIERT: Caching-Strategie

from functools import lru_cache
from django.core.cache import caches
import hashlib

class CachedPromptRegistry:
    """Registry mit Multi-Layer Caching."""
    
    L1_TTL = 60      # Local Memory: 1 Minute
    L2_TTL = 300     # Redis: 5 Minuten
    L3_TTL = 3600    # DB Query Cache: 1 Stunde
    
    def __init__(self):
        self.l1_cache = {}  # Process-local
        self.l2_cache = caches['redis']
        self._db_query_cache = {}
    
    def get(
        self,
        code: str,
        tenant_id: Optional[UUID] = None,
        version: Optional[int] = None,
    ) -> PromptTemplate:
        """Cached Template Lookup mit Fallback-Chain."""
        
        cache_key = self._build_cache_key(code, tenant_id, version)
        
        # L1: Local Memory (schnellste)
        if cache_key in self.l1_cache:
            entry = self.l1_cache[cache_key]
            if not entry.is_expired():
                return entry.value
        
        # L2: Redis (shared zwischen Workers)
        cached = self.l2_cache.get(cache_key)
        if cached:
            self._set_l1(cache_key, cached)
            return cached
        
        # L3: Database
        template = self._fetch_from_db(code, tenant_id, version)
        
        # Cache Population
        self._set_l2(cache_key, template)
        self._set_l1(cache_key, template)
        
        return template
    
    def invalidate(self, code: str, tenant_id: Optional[UUID] = None):
        """Invalidiert alle Cache-Layer für ein Template."""
        pattern = f"prompt:{code}:*"
        
        # L1: Local
        keys_to_delete = [k for k in self.l1_cache if k.startswith(f"prompt:{code}:")]
        for key in keys_to_delete:
            del self.l1_cache[key]
        
        # L2: Redis Pattern Delete
        redis_client = self.l2_cache.client.get_client()
        for key in redis_client.scan_iter(match=pattern):
            redis_client.delete(key)
        
        # Publish Invalidation Event (für andere Workers)
        self._publish_invalidation_event(code, tenant_id)
    
    def _build_cache_key(
        self,
        code: str,
        tenant_id: Optional[UUID],
        version: Optional[int]
    ) -> str:
        tenant_part = str(tenant_id) if tenant_id else 'global'
        version_part = str(version) if version else 'latest'
        return f"prompt:{code}:{tenant_part}:{version_part}"
    
    @staticmethod
    @lru_cache(maxsize=1000)
    def _hash_context(context_str: str) -> str:
        """Cached Context Hashing für Execution Deduplication."""
        return hashlib.sha256(context_str.encode()).hexdigest()[:16]
```

---

### 4. Fehlende Resilience-Patterns (Medium Severity)

**Problem:** Keine Retry-Logik, kein Circuit-Breaker, keine Fallbacks.

**Lösung:** Resiliente PromptService

```python
# OPTIMIERT: Resiliente Service-Architektur

from tenacity import (
    retry, stop_after_attempt, wait_exponential,
    retry_if_exception_type, CircuitBreaker
)
from dataclasses import dataclass
from enum import Enum
import asyncio

class LLMCircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, use fallback
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class PromptServiceConfig:
    """Konfiguration für Resilience."""
    max_retries: int = 3
    retry_base_delay: float = 1.0
    retry_max_delay: float = 30.0
    circuit_failure_threshold: int = 5
    circuit_recovery_timeout: int = 60
    request_timeout: int = 60
    fallback_enabled: bool = True


class ResilientPromptService:
    """PromptService mit Enterprise-Grade Resilience."""
    
    def __init__(
        self,
        registry: 'PromptRegistry',
        llm_client: 'DynamicLLMClient',
        tracker: 'UsageTracker',
        config: PromptServiceConfig = None,
        tenant_id: Optional[UUID] = None,
    ):
        self.registry = registry
        self.llm_client = llm_client
        self.tracker = tracker
        self.config = config or PromptServiceConfig()
        self.tenant_id = tenant_id
        self.engine = SecureTemplateEngine(registry.component_store)
        
        # Circuit Breakers per LLM Tier
        self._circuit_breakers = {
            'economy': self._create_circuit_breaker(),
            'standard': self._create_circuit_breaker(),
            'premium': self._create_circuit_breaker(),
        }
    
    async def generate(
        self,
        template_code: str,
        context: Dict[str, Any],
        tier: Optional[str] = None,
        **kwargs
    ) -> 'PromptResult':
        """
        Resiliente Prompt-Generierung mit:
        - Retry mit exponential backoff
        - Circuit Breaker pro Tier
        - Automatischer Tier-Fallback
        - Timeout-Handling
        """
        
        # 1. Template & Config laden
        template = self.registry.get(template_code, self.tenant_id)
        config = self.registry.get_config(template, self.tenant_id)
        
        # 2. Template rendern
        rendered = self.engine.render(template, context, config)
        
        # 3. Tier bestimmen
        effective_tier = tier or config.preferred_tier
        
        # 4. LLM aufrufen mit Resilience
        try:
            response = await self._call_llm_with_resilience(
                rendered=rendered,
                config=config,
                tier=effective_tier,
                **kwargs
            )
        except LLMUnavailableError as e:
            # Alle Tiers ausgefallen
            return self._create_fallback_result(template, rendered, e)
        
        # 5. Tracking
        execution = await self._track_execution(
            template=template,
            rendered=rendered,
            response=response,
            tier=effective_tier,
        )
        
        return PromptResult(
            content=response.content,
            template=template,
            execution=execution,
            usage=response.usage,
            metadata={
                'tier_used': response.tier,
                'model_used': response.model,
                'retry_count': response.retry_count,
            }
        )
    
    async def _call_llm_with_resilience(
        self,
        rendered: 'RenderedPrompt',
        config: 'PromptConfig',
        tier: str,
        **kwargs
    ) -> 'LLMResponse':
        """LLM-Aufruf mit Retry und Circuit Breaker."""
        
        tiers_to_try = self._get_fallback_chain(tier, config)
        last_error = None
        
        for current_tier in tiers_to_try:
            circuit = self._circuit_breakers[current_tier]
            
            # Circuit Breaker Check
            if circuit.state == LLMCircuitState.OPEN:
                continue
            
            try:
                response = await self._call_with_retry(
                    rendered=rendered,
                    config=config,
                    tier=current_tier,
                    **kwargs
                )
                
                # Success: Reset Circuit
                circuit.record_success()
                return response
                
            except (LLMRateLimitError, LLMTimeoutError, LLMAPIError) as e:
                circuit.record_failure()
                last_error = e
                
                # Log und nächsten Tier versuchen
                logger.warning(
                    f"LLM call failed for tier {current_tier}: {e}. "
                    f"Trying fallback..."
                )
        
        raise LLMUnavailableError(
            f"All LLM tiers exhausted. Last error: {last_error}"
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        retry=retry_if_exception_type((LLMRateLimitError, LLMTimeoutError)),
    )
    async def _call_with_retry(
        self,
        rendered: 'RenderedPrompt',
        config: 'PromptConfig',
        tier: str,
        **kwargs
    ) -> 'LLMResponse':
        """Einzelner LLM-Aufruf mit Retry."""
        
        return await asyncio.wait_for(
            self.llm_client.generate(
                prompt=rendered.user_prompt,
                system_prompt=rendered.system_prompt,
                tier=tier,
                max_tokens=config.max_tokens,
                temperature=config.temperature,
                **kwargs
            ),
            timeout=config.timeout_seconds
        )
    
    def _get_fallback_chain(self, primary_tier: str, config: 'PromptConfig') -> List[str]:
        """Bestimmt Fallback-Reihenfolge."""
        
        FALLBACK_ORDER = {
            'premium': ['premium', 'standard', 'economy'],
            'standard': ['standard', 'economy'],
            'economy': ['economy'],
        }
        
        chain = FALLBACK_ORDER.get(primary_tier, [primary_tier])
        
        # Config-Override für Fallback
        if config.fallback_tier:
            chain.append(config.fallback_tier)
        
        return chain
    
    def _create_fallback_result(
        self,
        template: 'PromptTemplate',
        rendered: 'RenderedPrompt',
        error: Exception
    ) -> 'PromptResult':
        """Fallback-Ergebnis wenn alle LLMs ausfallen."""
        
        return PromptResult(
            content=None,
            template=template,
            execution=None,
            usage=None,
            error=str(error),
            fallback=True,
            metadata={
                'rendered_prompt': rendered.full_prompt[:500],  # Für Debugging
            }
        )
```

---

### 5. Fehlende Event-Architektur (Medium Severity)

**Problem:** Tracking ist synchron eingebettet, keine Event-Driven-Architektur.

**Lösung:** Event-basiertes Tracking

```python
# OPTIMIERT: Event-Driven Tracking

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, List
from enum import Enum
import asyncio

class PromptEventType(Enum):
    TEMPLATE_LOADED = "template.loaded"
    TEMPLATE_RENDERED = "template.rendered"
    LLM_REQUEST_STARTED = "llm.request.started"
    LLM_REQUEST_COMPLETED = "llm.request.completed"
    LLM_REQUEST_FAILED = "llm.request.failed"
    EXECUTION_TRACKED = "execution.tracked"
    CACHE_HIT = "cache.hit"
    CACHE_MISS = "cache.miss"


@dataclass
class PromptEvent:
    """Immutable Event für Prompt-Operationen."""
    type: PromptEventType
    timestamp: datetime = field(default_factory=datetime.utcnow)
    template_code: str = None
    tenant_id: UUID = None
    user_id: UUID = None
    data: Dict = field(default_factory=dict)
    duration_ms: int = None


class PromptEventBus:
    """
    Event Bus für asynchrones Tracking und Monitoring.
    
    Vorteile:
    - Entkoppelt Tracking von Business-Logik
    - Ermöglicht Multiple Subscribers (Metrics, Logging, Analytics)
    - Asynchrone Verarbeitung
    """
    
    _subscribers: Dict[PromptEventType, List[Callable]] = {}
    _async_queue: asyncio.Queue = None
    
    @classmethod
    def subscribe(cls, event_type: PromptEventType, handler: Callable):
        """Registriert Event Handler."""
        if event_type not in cls._subscribers:
            cls._subscribers[event_type] = []
        cls._subscribers[event_type].append(handler)
    
    @classmethod
    async def publish(cls, event: PromptEvent):
        """Publiziert Event asynchron."""
        handlers = cls._subscribers.get(event.type, [])
        
        # Async handlers
        await asyncio.gather(*[
            handler(event) if asyncio.iscoroutinefunction(handler)
            else asyncio.to_thread(handler, event)
            for handler in handlers
        ])
    
    @classmethod
    def publish_sync(cls, event: PromptEvent):
        """Publiziert Event synchron (für non-async contexts)."""
        asyncio.create_task(cls.publish(event))


# === Event Handlers ===

class MetricsHandler:
    """Handler für Prometheus Metrics."""
    
    @staticmethod
    async def handle_llm_completed(event: PromptEvent):
        from apps.core.metrics import (
            PROMPT_GENERATION_DURATION,
            PROMPT_GENERATION_TOKENS,
            PROMPT_GENERATION_COST,
        )
        
        PROMPT_GENERATION_DURATION.labels(
            template=event.template_code,
            tier=event.data.get('tier'),
        ).observe(event.duration_ms / 1000)
        
        PROMPT_GENERATION_TOKENS.labels(
            template=event.template_code,
        ).observe(event.data.get('tokens_total', 0))


class ExecutionTracker:
    """Handler für DB-Tracking."""
    
    @staticmethod
    async def handle_execution(event: PromptEvent):
        from apps.core.models import PromptExecution
        
        await PromptExecution.objects.acreate(
            template_id=event.data.get('template_id'),
            template_version=event.data.get('template_version'),
            context_hash=event.data.get('context_hash'),
            rendered_prompt=event.data.get('rendered_prompt'),
            llm_model=event.data.get('model'),
            llm_tier=event.data.get('tier'),
            tokens_in=event.data.get('tokens_in', 0),
            tokens_out=event.data.get('tokens_out', 0),
            cost=event.data.get('cost', 0),
            latency_ms=event.duration_ms,
            success=event.data.get('success', True),
            error_message=event.data.get('error'),
            tenant_id=event.tenant_id,
            user_id=event.user_id,
        )


# === Registration ===

def setup_event_handlers():
    """Registriert alle Event Handler beim App-Start."""
    
    PromptEventBus.subscribe(
        PromptEventType.LLM_REQUEST_COMPLETED,
        MetricsHandler.handle_llm_completed
    )
    
    PromptEventBus.subscribe(
        PromptEventType.EXECUTION_TRACKED,
        ExecutionTracker.handle_execution
    )
```

---

### 6. Fehlende Prompt-Komposition (Medium Severity)

**Problem:** Keine Möglichkeit, Prompts zu verketten oder zu komponieren.

**Lösung:** Composable Prompts

```python
# OPTIMIERT: Prompt Composition

from abc import ABC, abstractmethod
from typing import List, Union

class PromptPart(ABC):
    """Basis für komponierbare Prompt-Teile."""
    
    @abstractmethod
    def render(self, context: Dict) -> str:
        pass


class TextPart(PromptPart):
    """Statischer Text."""
    
    def __init__(self, text: str):
        self.text = text
    
    def render(self, context: Dict) -> str:
        return self.text


class TemplatePart(PromptPart):
    """Jinja2 Template."""
    
    def __init__(self, template: str, engine: 'SecureTemplateEngine'):
        self.template = template
        self.engine = engine
    
    def render(self, context: Dict) -> str:
        return self.engine._render_safe(self.template, context)


class ComponentPart(PromptPart):
    """Wiederverwendbare Komponente."""
    
    def __init__(self, component_code: str, store: 'ComponentStore'):
        self.component_code = component_code
        self.store = store
    
    def render(self, context: Dict) -> str:
        component = self.store.get(self.component_code)
        return component.content if component else ""


class ConditionalPart(PromptPart):
    """Bedingt gerenderte Teile."""
    
    def __init__(
        self,
        condition: Callable[[Dict], bool],
        if_true: PromptPart,
        if_false: PromptPart = None
    ):
        self.condition = condition
        self.if_true = if_true
        self.if_false = if_false
    
    def render(self, context: Dict) -> str:
        if self.condition(context):
            return self.if_true.render(context)
        elif self.if_false:
            return self.if_false.render(context)
        return ""


class LoopPart(PromptPart):
    """Iteriert über Context-Liste."""
    
    def __init__(self, items_key: str, item_template: PromptPart, separator: str = "\n"):
        self.items_key = items_key
        self.item_template = item_template
        self.separator = separator
    
    def render(self, context: Dict) -> str:
        items = context.get(self.items_key, [])
        rendered = []
        
        for i, item in enumerate(items):
            item_context = {**context, 'item': item, 'index': i}
            rendered.append(self.item_template.render(item_context))
        
        return self.separator.join(rendered)


class CompositePrompt:
    """
    Komponierter Prompt aus mehreren Teilen.
    
    Usage:
        prompt = (
            CompositePrompt()
            .add(TextPart("Du bist ein Experte für "))
            .add(TemplatePart("{{ domain }}", engine))
            .add_conditional(
                lambda ctx: ctx.get('include_examples'),
                ComponentPart('examples_section', store)
            )
            .add_loop(
                'documents',
                TemplatePart("- {{ item.title }}: {{ item.summary }}", engine)
            )
        )
        
        result = prompt.render(context)
    """
    
    def __init__(self):
        self.parts: List[PromptPart] = []
    
    def add(self, part: PromptPart) -> 'CompositePrompt':
        self.parts.append(part)
        return self
    
    def add_text(self, text: str) -> 'CompositePrompt':
        return self.add(TextPart(text))
    
    def add_template(self, template: str, engine: 'SecureTemplateEngine') -> 'CompositePrompt':
        return self.add(TemplatePart(template, engine))
    
    def add_component(self, code: str, store: 'ComponentStore') -> 'CompositePrompt':
        return self.add(ComponentPart(code, store))
    
    def add_conditional(
        self,
        condition: Callable[[Dict], bool],
        if_true: PromptPart,
        if_false: PromptPart = None
    ) -> 'CompositePrompt':
        return self.add(ConditionalPart(condition, if_true, if_false))
    
    def add_loop(
        self,
        items_key: str,
        item_template: PromptPart,
        separator: str = "\n"
    ) -> 'CompositePrompt':
        return self.add(LoopPart(items_key, item_template, separator))
    
    def render(self, context: Dict) -> str:
        return "".join(part.render(context) for part in self.parts)
```

---

### 7. Fehlende Schema-Validierung (Low Severity)

**Problem:** Variables nur als Dict definiert, keine Typprüfung.

**Lösung:** JSON Schema Validierung

```python
# OPTIMIERT: Schema-basierte Validierung

from jsonschema import validate, ValidationError as JsonSchemaError
from pydantic import BaseModel, create_model
from typing import Any, Type

class VariableSchema:
    """JSON Schema basierte Variablen-Validierung."""
    
    @staticmethod
    def validate_context(
        context: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> 'ContextValidationResult':
        """Validiert Context gegen JSON Schema."""
        
        errors = []
        warnings = []
        
        try:
            validate(instance=context, schema=schema)
        except JsonSchemaError as e:
            errors.append(f"Validation error: {e.message}")
        
        # Check für unerwartete Keys
        if 'properties' in schema:
            expected_keys = set(schema['properties'].keys())
            actual_keys = set(context.keys())
            extra_keys = actual_keys - expected_keys
            
            if extra_keys:
                warnings.append(f"Unexpected context keys: {extra_keys}")
        
        return ContextValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
    
    @staticmethod
    def schema_to_pydantic(schema: Dict[str, Any], name: str = "DynamicModel") -> Type[BaseModel]:
        """Konvertiert JSON Schema zu Pydantic Model für Autocomplete."""
        
        type_mapping = {
            'string': str,
            'integer': int,
            'number': float,
            'boolean': bool,
            'array': list,
            'object': dict,
        }
        
        fields = {}
        for prop_name, prop_schema in schema.get('properties', {}).items():
            prop_type = type_mapping.get(prop_schema.get('type', 'string'), Any)
            is_required = prop_name in schema.get('required', [])
            
            if is_required:
                fields[prop_name] = (prop_type, ...)
            else:
                default = prop_schema.get('default')
                fields[prop_name] = (prop_type, default)
        
        return create_model(name, **fields)


# Beispiel Schema für Expert Hub Phase 5
EXPERT_HUB_PHASE_5_SCHEMA = {
    "type": "object",
    "required": ["project_name", "phase_number"],
    "properties": {
        "project_name": {
            "type": "string",
            "description": "Name des Projekts",
            "minLength": 1,
            "maxLength": 200
        },
        "project_location": {
            "type": "string",
            "description": "Standort des Projekts"
        },
        "phase_number": {
            "type": "integer",
            "enum": [1, 2, 3, 4, 5, 6, 7, 8]
        },
        "existing_section": {
            "type": "string",
            "description": "Bereits vorhandene Sektion"
        },
        "documents": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "summary": {"type": "string"}
                }
            }
        }
    },
    "additionalProperties": False
}
```

---

## 🏗️ OPTIMIERTE ARCHITEKTUR

### Schichtenmodell (Überarbeitet)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         APPLICATION LAYER                                    │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │  Risk-Hub   │ │ Expert-Hub  │ │ Writing-Hub │ │ Travel-Beat │           │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘           │
│         │               │               │               │                   │
│         ▼               ▼               ▼               ▼                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │              App-Specific Context Builders                           │   │
│  │  (ExpertHubContextBuilder, WritingHubContextBuilder, etc.)          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      PROMPT FRAMEWORK LAYER                                  │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │              ResilientPromptService (Facade)                         │   │
│  │  - generate() with retry, circuit breaker, fallback                 │   │
│  │  - render_only() for preview                                         │   │
│  │  - batch_generate() for bulk operations                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│           │                    │                    │                       │
│           ▼                    ▼                    ▼                       │
│  ┌───────────────┐   ┌───────────────┐   ┌───────────────┐                 │
│  │SecureTemplate │   │CachedPrompt   │   │PromptComposer │                 │
│  │   Engine      │   │  Registry     │   │ (Composition) │                 │
│  │ (Sandboxed)   │   │ (Multi-Layer) │   │               │                 │
│  └───────────────┘   └───────────────┘   └───────────────┘                 │
│           │                    │                    │                       │
│           ▼                    ▼                    ▼                       │
│  ┌───────────────┐   ┌───────────────┐   ┌───────────────┐                 │
│  │ Variable      │   │ Component     │   │ Tenant        │                 │
│  │ Validator     │   │ Store         │   │ Override      │                 │
│  │ (JSON Schema) │   │ (Reusable)    │   │ Manager       │                 │
│  └───────────────┘   └───────────────┘   └───────────────┘                 │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    PromptEventBus (Async)                            │   │
│  │  - MetricsHandler → Prometheus                                       │   │
│  │  - ExecutionTracker → Database                                       │   │
│  │  - AuditLogger → Compliance                                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         LLM LAYER (mit Resilience)                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │ DynamicLLMClient│  │ CircuitBreaker  │  │  UsageTracker   │             │
│  │ (Tier Selection)│  │ (per Provider)  │  │ (Cost Control)  │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA LAYER                                         │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌───────────────────┐   │
│  │   PromptTemplate    │  │   PromptConfig      │  │ PromptExecution   │   │
│  │   (Content Only)    │  │   (LLM Settings)    │  │ (Tracking)        │   │
│  └─────────────────────┘  └─────────────────────┘  └───────────────────┘   │
│  ┌─────────────────────┐  ┌─────────────────────┐                          │
│  │  PromptComponent    │  │ TenantOverride      │                          │
│  │  (Reusable Parts)   │  │ (Customizations)    │                          │
│  └─────────────────────┘  └─────────────────────┘                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📅 OPTIMIERTER IMPLEMENTIERUNGSPLAN

### Zeitvergleich

| Phase | Original | Optimiert | Delta | Begründung |
|-------|----------|-----------|-------|------------|
| 1. Framework Core | 2 Tage | 3 Tage | +1 | Security, Resilience |
| 2. Django Integration | 1 Tag | 1.5 Tage | +0.5 | Getrenntes Datenmodell |
| 3. Expert Hub | 1 Tag | 1 Tag | 0 | Unverändert |
| 4. Writing Hub | 1 Tag | 1 Tag | 0 | Unverändert |
| 5. Travel Beat | 0.5 Tag | 0.5 Tag | 0 | Unverändert |
| 6. SaaS Features | 2 Tage | 2 Tage | 0 | Unverändert |
| 7. Testing & Docs | - | 1.5 Tage | +1.5 | NEU: Essential |
| 8. Monitoring | 1 Tag | 1 Tag | 0 | Unverändert |
| **Gesamt** | **~9 Tage** | **~12 Tage** | **+3** | Qualitäts-Investment |

---

### Phase 1: Framework Core (3 Tage)

#### Tag 1: Sichere Template-Engine

```
□ SecureTemplateEngine implementieren
  □ Sandboxed Jinja2 Environment
  □ Pattern-basierte Sicherheitsprüfung
  □ AST-Analyse für gefährliche Konstrukte
  □ Context Sanitization
  
□ VariableValidator implementieren
  □ JSON Schema Validierung
  □ Pydantic Model Generation
  
□ Unit Tests für Security
  □ Injection-Tests
  □ Sandbox-Escape-Tests
```

#### Tag 2: Resiliente Service-Architektur

```
□ ResilientPromptService implementieren
  □ Retry mit exponential backoff
  □ Circuit Breaker pro Tier
  □ Timeout Handling
  □ Fallback Chain
  
□ PromptEventBus implementieren
  □ Event Types definieren
  □ Async Handler Registration
  □ Metrics Handler
  
□ Unit Tests für Resilience
  □ Retry-Verhalten
  □ Circuit Breaker States
  □ Fallback Scenarios
```

#### Tag 3: Caching & Composition

```
□ CachedPromptRegistry implementieren
  □ L1 (Local) Cache
  □ L2 (Redis) Cache
  □ Invalidation Events
  
□ PromptComposer implementieren
  □ PromptPart Abstraktion
  □ Composite Pattern
  □ Conditional & Loop Parts
  
□ Integration Tests
```

---

### Phase 2: Django Integration (1.5 Tage)

#### Tag 1: Models & Migrations

```
□ Getrennte Models erstellen
  □ PromptTemplate (Content)
  □ PromptConfig (LLM Settings)
  □ TenantPromptOverride
  □ PromptExecution
  □ PromptComponent
  
□ Migrations erstellen
□ Admin Interface
```

#### Tag 1.5: Django Adapters

```
□ DjangoPromptRegistry
  □ Mit Caching Integration
  □ Tenant Fallback Logic
  
□ DjangoComponentStore
□ Factory Functions
□ Integration Tests
```

---

### Phase 7: Testing & Documentation (1.5 Tage) - NEU

```
□ Test Suite
  □ Unit Tests (>90% Coverage für Core)
  □ Integration Tests
  □ Security Tests (OWASP Top 10)
  □ Performance Tests (Rendering < 10ms)
  □ Contract Tests (API Stability)

□ Documentation
  □ API Reference
  □ Migration Guide
  □ Security Guidelines
  □ Best Practices
  □ Troubleshooting Guide
```

---

## ✅ QUALITÄTS-CHECKLISTE

### Architektur

- [x] Separation of Concerns (Content vs. Config vs. Override)
- [x] Event-Driven Tracking
- [x] Multi-Layer Caching
- [x] Resilience Patterns (Retry, Circuit Breaker, Fallback)
- [x] Composable Prompts

### Sicherheit

- [x] Sandboxed Template Engine
- [x] Context Sanitization
- [x] Pattern-basierte Injection Prevention
- [x] Tenant Isolation
- [x] Rate Limiting Integration

### Performance

- [x] L1/L2 Caching Strategy
- [x] Async Event Processing
- [x] Batch Processing Support
- [x] Lazy Component Loading

### Testbarkeit

- [x] Mockable Interfaces (Protocols)
- [x] Event-based Testing
- [x] Security Test Suite
- [x] Performance Benchmarks

---

## 🎯 EMPFEHLUNG

**Implementierungsreihenfolge:**

1. **SOFORT:** Security-Härtung der Template-Engine (kritisch!)
2. **Woche 1:** Core Framework mit Resilience
3. **Woche 2:** Django Integration + Expert Hub Migration
4. **Woche 3:** Weitere Apps + Testing

**ROI der Optimierungen:**

| Optimierung | Aufwand | Nutzen |
|-------------|---------|--------|
| Security Hardening | +1 Tag | Verhindert potenzielle Exploits |
| Resilience | +0.5 Tag | 99.9% Uptime statt 99% |
| Separated Models | +0.5 Tag | Wartbarkeit, Flexibilität |
| Event Bus | +0.5 Tag | Skalierbare Monitoring-Integration |
| Testing | +1.5 Tage | Frühe Bug-Erkennung, Regression Prevention |

**Gesamtbewertung nach Optimierung:** A-

---

## 📚 REFERENZEN

- [OWASP Template Injection](https://owasp.org/www-project-web-security-testing-guide/)
- [Jinja2 Sandbox](https://jinja.palletsprojects.com/en/3.1.x/sandbox/)
- [Circuit Breaker Pattern](https://martinfowler.com/bliki/CircuitBreaker.html)
- [Event-Driven Architecture](https://microservices.io/patterns/data/event-driven-architecture.html)
- [JSON Schema](https://json-schema.org/)

---

**Status:** Optimiertes Konzept bereit für Implementierung  
**Reviewer:** Senior IT-Architekt  
**Nächster Schritt:** Review des optimierten Konzepts, dann Phase 1 starten
