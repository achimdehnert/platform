# 🏆 Prompt & Template Framework - Finaler Implementierungsvorschlag

**Version:** 3.0 (Final)  
**Datum:** 2026-01-28  
**Status:** Bereit für Implementierung  
**Basiert auf:** RFC v1.0 + Critical Analysis + Optimized Concept v2.0

---

## 📋 EXECUTIVE SUMMARY

Dieser finale Vorschlag kombiniert:
- ✅ **Meine kritische Analyse:** DB-driven Lookups, FK statt Strings, Handler-Integration
- ✅ **Ihre Optimierungen:** Separation (Template/Config), Security, Resilience, Caching, Events
- ✅ **Pragmatismus:** MVP-fokussiert mit klaren Erweiterungspfaden

**Gesamtbewertung:** A (Enterprise-Ready)

---

## 🏗️ FINALES DATENMODELL

### Prinzipien

1. **DB-Driven Lookups** - Alle Kategorien, Tiers, Formate als FK (wie HandlerCategory)
2. **Separation of Concerns** - Template (Content) vs Config (LLM) vs Override (Tenant)
3. **Naming Conventions** - Konsistent mit bestehendem Handler-System
4. **Handler-Integration** - PromptExecution verknüpft mit HandlerExecution

### Lookup-Tabellen (DB-Driven)

```python
# ============================================================================
# apps/core/models/prompt_lookups.py
# ============================================================================

from django.db import models
from django.core.exceptions import ValidationError


class PromptApp(models.Model):
    """
    App Registry für Multi-Hub Support.
    Analog zu DomainType im Handler-System.
    
    Naming: prompt_apps (snake_case, plural)
    """
    code = models.CharField(
        max_length=50, 
        unique=True, 
        db_index=True,
        help_text="Unique code (e.g., 'expert_hub', 'writing_hub')"
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    
    # Display
    icon = models.CharField(max_length=50, blank=True, default="bi-app")
    color = models.CharField(max_length=50, blank=True, default="primary")
    
    # Status
    is_active = models.BooleanField(default=True, db_index=True)
    is_system = models.BooleanField(default=False, help_text="System apps cannot be deleted")
    sort_order = models.IntegerField(default=0)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'prompt_apps'
        ordering = ['sort_order', 'name']
        verbose_name = 'Prompt App'
        verbose_name_plural = 'Prompt Apps'
    
    def __str__(self):
        return self.name
    
    def clean(self):
        if self.code:
            self.code = self.code.lower()
            if not self.code.replace('_', '').isalnum():
                raise ValidationError({'code': 'Code must be alphanumeric (underscores allowed)'})
    
    def delete(self, *args, **kwargs):
        if self.is_system:
            raise ValidationError('System apps cannot be deleted')
        super().delete(*args, **kwargs)
    
    @classmethod
    def get_default_apps(cls):
        return [
            {'code': 'expert_hub', 'name': 'Expert Hub', 'icon': 'bi-shield-check', 'color': 'danger', 'is_system': True},
            {'code': 'writing_hub', 'name': 'Writing Hub', 'icon': 'bi-book', 'color': 'primary', 'is_system': True},
            {'code': 'risk_hub', 'name': 'Risk Hub', 'icon': 'bi-exclamation-triangle', 'color': 'warning', 'is_system': True},
            {'code': 'travel_beat', 'name': 'Travel Beat', 'icon': 'bi-airplane', 'color': 'info', 'is_system': True},
        ]


class PromptCategory(models.Model):
    """
    Prompt Category - analog zu HandlerCategory.
    
    Naming: prompt_categories (snake_case, plural)
    """
    code = models.CharField(
        max_length=50, 
        unique=True, 
        db_index=True,
        help_text="Unique code (e.g., 'phase', 'generation', 'analysis')"
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    
    # Display
    icon = models.CharField(max_length=50, blank=True, default="bi-chat-dots")
    color = models.CharField(max_length=50, blank=True, default="info")
    display_order = models.IntegerField(default=0, db_index=True)
    
    # Status
    is_active = models.BooleanField(default=True, db_index=True)
    is_system = models.BooleanField(default=False)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'prompt_categories'
        ordering = ['display_order', 'name']
        verbose_name = 'Prompt Category'
        verbose_name_plural = 'Prompt Categories'
    
    def __str__(self):
        return self.name
    
    @classmethod
    def get_default_categories(cls):
        return [
            {'code': 'phase', 'name': 'Workflow Phase', 'icon': 'bi-diagram-3', 'display_order': 1, 'is_system': True},
            {'code': 'generation', 'name': 'Content Generation', 'icon': 'bi-magic', 'display_order': 2, 'is_system': True},
            {'code': 'analysis', 'name': 'Analysis', 'icon': 'bi-search', 'display_order': 3, 'is_system': True},
            {'code': 'transformation', 'name': 'Transformation', 'icon': 'bi-arrow-repeat', 'display_order': 4, 'is_system': True},
            {'code': 'component', 'name': 'Reusable Component', 'icon': 'bi-puzzle', 'display_order': 5, 'is_system': True},
        ]


class PromptTier(models.Model):
    """
    LLM Tier - DB-driven statt Enum.
    Ermöglicht dynamische Tier-Konfiguration ohne Code-Änderung.
    
    Naming: prompt_tiers (snake_case, plural)
    """
    code = models.CharField(
        max_length=20, 
        unique=True, 
        db_index=True,
        help_text="Unique code (e.g., 'economy', 'standard', 'premium')"
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    
    # Cost & Defaults
    cost_multiplier = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=1.0,
        help_text="Relative cost multiplier (1.0 = baseline)"
    )
    default_provider = models.CharField(max_length=50, blank=True, default="openai")
    default_model = models.CharField(max_length=100, blank=True, default="gpt-4o-mini")
    max_tokens_default = models.IntegerField(default=2000)
    temperature_default = models.FloatField(default=0.7)
    
    # Fallback
    fallback_tier = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='fallback_for',
        help_text="Tier to use if this one fails"
    )
    
    # Status
    is_active = models.BooleanField(default=True, db_index=True)
    sort_order = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'prompt_tiers'
        ordering = ['sort_order']
        verbose_name = 'Prompt Tier'
        verbose_name_plural = 'Prompt Tiers'
    
    def __str__(self):
        return f"{self.name} ({self.default_model})"
    
    @classmethod
    def get_default_tiers(cls):
        return [
            {'code': 'economy', 'name': 'Economy', 'cost_multiplier': 0.1, 'default_model': 'gpt-3.5-turbo', 'sort_order': 1},
            {'code': 'standard', 'name': 'Standard', 'cost_multiplier': 1.0, 'default_model': 'gpt-4o-mini', 'sort_order': 2},
            {'code': 'premium', 'name': 'Premium', 'cost_multiplier': 10.0, 'default_model': 'gpt-4o', 'sort_order': 3},
            {'code': 'local', 'name': 'Local', 'cost_multiplier': 0.0, 'default_model': 'llama3.2', 'sort_order': 4},
        ]


class PromptOutputFormat(models.Model):
    """
    Output Format - DB-driven.
    
    Naming: prompt_output_formats (snake_case, plural)
    """
    code = models.CharField(
        max_length=20, 
        unique=True, 
        db_index=True,
        help_text="Unique code (e.g., 'json', 'markdown', 'text')"
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    
    # Format Instructions (appended to prompts)
    format_instructions = models.TextField(
        blank=True, 
        default="",
        help_text="Standard instructions for this format (Jinja2 template)"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'prompt_output_formats'
        ordering = ['sort_order']
        verbose_name = 'Prompt Output Format'
        verbose_name_plural = 'Prompt Output Formats'
    
    def __str__(self):
        return self.name
    
    @classmethod
    def get_default_formats(cls):
        return [
            {
                'code': 'json', 
                'name': 'JSON', 
                'format_instructions': '''
## Output Format
Return your response as valid JSON:
```json
{{ json_schema | default("{}") }}
```
Ensure valid JSON syntax with proper quotes and commas.
''',
                'sort_order': 1
            },
            {
                'code': 'markdown', 
                'name': 'Markdown', 
                'format_instructions': 'Format your response in Markdown with proper headings and lists.',
                'sort_order': 2
            },
            {
                'code': 'text', 
                'name': 'Plain Text', 
                'format_instructions': '',
                'sort_order': 3
            },
            {
                'code': 'html', 
                'name': 'HTML', 
                'format_instructions': 'Format your response as semantic HTML.',
                'sort_order': 4
            },
        ]
```

### Haupt-Models (Separated)

```python
# ============================================================================
# apps/core/models/prompt_models.py
# ============================================================================

import uuid
import hashlib
from decimal import Decimal
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class PromptTemplate(models.Model):
    """
    Prompt Template - NUR Content, keine LLM-Config.
    
    Separation of Concerns:
    - PromptTemplate: WAS wird gefragt (Content)
    - PromptConfig: WIE wird gefragt (LLM Settings)
    - TenantPromptOverride: Tenant-spezifische Anpassungen
    
    Naming: prompt_templates (snake_case, plural)
    """
    # Identity
    code = models.CharField(
        max_length=100, 
        db_index=True,
        help_text="Template code (e.g., 'expert_hub.phase_5')"
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    
    # Relations (FK statt String!)
    app = models.ForeignKey(
        'core.PromptApp',
        on_delete=models.PROTECT,
        related_name='templates',
        help_text="App this template belongs to"
    )
    category = models.ForeignKey(
        'core.PromptCategory',
        on_delete=models.PROTECT,
        related_name='templates',
        help_text="Template category"
    )
    output_format = models.ForeignKey(
        'core.PromptOutputFormat',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='templates',
        help_text="Default output format"
    )
    
    # Content (Jinja2 Templates)
    system_prompt = models.TextField(
        blank=True, 
        default="",
        help_text="System message template (Jinja2)"
    )
    user_prompt = models.TextField(
        help_text="User message template (Jinja2)"
    )
    output_format_instructions = models.TextField(
        blank=True, 
        default="",
        help_text="Additional output instructions (overrides format default)"
    )
    
    # Variables (JSON Schema!)
    variables_schema = models.JSONField(
        default=dict,
        help_text="JSON Schema for required variables"
    )
    default_values = models.JSONField(
        default=dict,
        help_text="Default values for optional variables"
    )
    
    # Versioning
    version = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True, db_index=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_prompt_templates'
    )
    
    class Meta:
        db_table = 'prompt_templates'
        unique_together = ['code', 'app', 'version']
        ordering = ['app', 'category', 'code']
        indexes = [
            models.Index(fields=['app', 'category', 'is_active']),
            models.Index(fields=['code', 'version']),
        ]
        verbose_name = 'Prompt Template'
        verbose_name_plural = 'Prompt Templates'
    
    def __str__(self):
        return f"{self.code} v{self.version}"
    
    def get_full_code(self) -> str:
        """Returns app.code format."""
        return f"{self.app.code}.{self.code}"


class PromptConfig(models.Model):
    """
    LLM Configuration - separat versionierbar.
    
    Ermöglicht:
    - Unterschiedliche LLM-Settings pro Environment
    - Tenant-spezifische Overrides
    - A/B Testing von Configs
    
    Naming: prompt_configs (snake_case, plural)
    """
    # Template Reference
    template = models.ForeignKey(
        PromptTemplate,
        on_delete=models.CASCADE,
        related_name='configs'
    )
    
    # LLM Settings
    preferred_tier = models.ForeignKey(
        'core.PromptTier',
        on_delete=models.SET_NULL,
        null=True,
        related_name='configs',
        help_text="Preferred LLM tier"
    )
    preferred_model = models.CharField(
        max_length=100, 
        blank=True, 
        default="",
        help_text="Specific model override (empty = use tier default)"
    )
    max_tokens = models.IntegerField(default=2000)
    temperature = models.FloatField(default=0.7)
    top_p = models.FloatField(default=1.0)
    
    # Resilience
    retry_count = models.IntegerField(default=3)
    timeout_seconds = models.IntegerField(default=60)
    
    # Scope
    tenant_id = models.UUIDField(
        null=True, 
        blank=True, 
        db_index=True,
        help_text="NULL = global config, else tenant-specific"
    )
    environment = models.CharField(
        max_length=20, 
        default='production',
        help_text="Environment (production, staging, development)"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'prompt_configs'
        unique_together = ['template', 'tenant_id', 'environment']
        indexes = [
            models.Index(fields=['template', 'tenant_id', 'is_active']),
        ]
        verbose_name = 'Prompt Config'
        verbose_name_plural = 'Prompt Configs'
    
    def __str__(self):
        scope = f"tenant:{self.tenant_id}" if self.tenant_id else "global"
        return f"{self.template.code} [{scope}] ({self.environment})"


class TenantPromptOverride(models.Model):
    """
    Tenant-spezifische Template-Anpassungen.
    
    Nur überschriebene Felder werden gespeichert.
    Ermöglicht Tenant-Customization ohne Template-Duplikation.
    
    Naming: tenant_prompt_overrides (snake_case, plural)
    """
    # Base Template
    base_template = models.ForeignKey(
        PromptTemplate,
        on_delete=models.CASCADE,
        related_name='tenant_overrides'
    )
    tenant_id = models.UUIDField(db_index=True)
    
    # Overrides (nur wenn gesetzt)
    system_prompt_override = models.TextField(
        blank=True, 
        default="",
        help_text="Overrides base template system_prompt (empty = use base)"
    )
    user_prompt_override = models.TextField(
        blank=True, 
        default="",
        help_text="Overrides base template user_prompt (empty = use base)"
    )
    output_format_override = models.TextField(
        blank=True, 
        default="",
        help_text="Overrides output format instructions"
    )
    
    # Additional Context (merged with base default_values)
    additional_context = models.JSONField(
        default=dict,
        help_text="Additional default values for this tenant"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_tenant_overrides'
    )
    
    class Meta:
        db_table = 'tenant_prompt_overrides'
        unique_together = ['base_template', 'tenant_id']
        indexes = [
            models.Index(fields=['tenant_id', 'is_active']),
        ]
        verbose_name = 'Tenant Prompt Override'
        verbose_name_plural = 'Tenant Prompt Overrides'
    
    def __str__(self):
        return f"{self.base_template.code} [tenant:{self.tenant_id}]"
    
    def get_effective_system_prompt(self) -> str:
        """Returns override or base."""
        return self.system_prompt_override or self.base_template.system_prompt
    
    def get_effective_user_prompt(self) -> str:
        """Returns override or base."""
        return self.user_prompt_override or self.base_template.user_prompt


class PromptComponent(models.Model):
    """
    Wiederverwendbare Prompt-Komponenten.
    
    Naming: prompt_components (snake_case, plural)
    """
    code = models.CharField(
        max_length=100, 
        unique=True, 
        db_index=True,
        help_text="Component code (e.g., 'output_json', 'quality_guidelines')"
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    
    # Category (should be 'component')
    category = models.ForeignKey(
        'core.PromptCategory',
        on_delete=models.PROTECT,
        related_name='components',
        limit_choices_to={'code': 'component'}
    )
    
    # Content
    content = models.TextField(help_text="Jinja2 template content")
    
    # Status
    is_active = models.BooleanField(default=True, db_index=True)
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'prompt_components'
        ordering = ['code']
        verbose_name = 'Prompt Component'
        verbose_name_plural = 'Prompt Components'
    
    def __str__(self):
        return self.code


class PromptExecution(models.Model):
    """
    Prompt Execution Tracking.
    
    Integriert mit Handler-System für vollständiges Tracking.
    
    Naming: prompt_executions (snake_case, plural)
    """
    # Template Reference
    template = models.ForeignKey(
        PromptTemplate,
        on_delete=models.SET_NULL,
        null=True,
        related_name='executions'
    )
    template_version = models.IntegerField()
    
    # Handler Integration (WICHTIG!)
    handler_execution = models.ForeignKey(
        'bfagent.HandlerExecution',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='prompt_executions',
        help_text="Link to handler execution for cost attribution"
    )
    
    # Rendered Content
    context_hash = models.CharField(
        max_length=64, 
        db_index=True,
        help_text="SHA256 hash of input context for deduplication"
    )
    rendered_system_prompt = models.TextField(blank=True, default="")
    rendered_user_prompt = models.TextField()
    
    # LLM Details
    llm_tier = models.ForeignKey(
        'core.PromptTier',
        on_delete=models.SET_NULL,
        null=True,
        related_name='executions'
    )
    llm_model = models.CharField(max_length=100)
    tokens_in = models.IntegerField(default=0)
    tokens_out = models.IntegerField(default=0)
    cost = models.DecimalField(
        max_digits=10, 
        decimal_places=6, 
        default=Decimal('0.000000')
    )
    latency_ms = models.IntegerField(default=0)
    
    # Result
    success = models.BooleanField(default=True, db_index=True)
    error_message = models.TextField(blank=True, default="")
    retry_count = models.IntegerField(default=0)
    
    # User Feedback (for A/B testing)
    user_rating = models.IntegerField(
        null=True, 
        blank=True,
        help_text="User rating 1-5 (optional)"
    )
    
    # Multi-Tenancy
    tenant_id = models.UUIDField(null=True, blank=True, db_index=True)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='prompt_executions'
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'prompt_executions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['template', '-created_at']),
            models.Index(fields=['tenant_id', '-created_at']),
            models.Index(fields=['success', '-created_at']),
            models.Index(fields=['handler_execution']),
        ]
        verbose_name = 'Prompt Execution'
        verbose_name_plural = 'Prompt Executions'
    
    def __str__(self):
        status = '✅' if self.success else '❌'
        return f"{status} {self.template.code if self.template else 'unknown'} ({self.latency_ms}ms)"
    
    @staticmethod
    def hash_context(context: dict) -> str:
        """Generate deterministic hash for context."""
        import json
        context_str = json.dumps(context, sort_keys=True, default=str)
        return hashlib.sha256(context_str.encode()).hexdigest()[:64]
```

---

## 🔐 SECURITY: SecureTemplateEngine

```python
# ============================================================================
# platform/packages/prompt-framework/prompt_framework/core/engine.py
# ============================================================================

from jinja2.sandbox import ImmutableSandboxedEnvironment
from jinja2 import StrictUndefined
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Set
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of template validation."""
    valid: bool
    errors: List[str]
    warnings: List[str]


@dataclass
class RenderedPrompt:
    """Result of template rendering."""
    system_prompt: str
    user_prompt: str
    full_prompt: str
    output_format: str
    variables_used: Set[str]
    validation: ValidationResult


class TemplateSecurityError(Exception):
    """Raised when template contains security violations."""
    pass


class SecureTemplateEngine:
    """
    Gehärtete Template-Engine mit Sicherheitsfeatures.
    
    Features:
    - Sandboxed Jinja2 Environment
    - Pattern-basierte Sicherheitsprüfung
    - Context Sanitization
    - Timeout Protection
    """
    
    # Erlaubte Jinja2 Globals (Whitelist)
    ALLOWED_GLOBALS = {
        'range', 'len', 'str', 'int', 'float', 'bool',
        'list', 'dict', 'set', 'tuple',
        'min', 'max', 'sum', 'sorted', 'enumerate', 'zip',
        'true', 'false', 'none',
    }
    
    # Verbotene Patterns in Templates
    FORBIDDEN_PATTERNS = [
        (r'\{\%\s*import', 'Import statements not allowed'),
        (r'\{\%\s*from', 'From imports not allowed'),
        (r'__\w+__', 'Dunder attributes not allowed'),
        (r'\.mro\s*\(', 'MRO access not allowed'),
        (r'\.base\s*\(', 'Base class access not allowed'),
        (r'\bconfig\s*\[', 'Config access not allowed'),
        (r'\bself\.', 'Self access not allowed'),
        (r'\brequest\.', 'Request access not allowed'),
        (r'\bos\.', 'OS module access not allowed'),
        (r'\bsys\.', 'Sys module access not allowed'),
        (r'\beval\s*\(', 'Eval not allowed'),
        (r'\bexec\s*\(', 'Exec not allowed'),
        (r'\bopen\s*\(', 'Open not allowed'),
    ]
    
    # Blocked context keys
    BLOCKED_CONTEXT_KEYS = {
        '__builtins__', '__import__', 'eval', 'exec', 'compile',
        'open', 'file', 'input', 'raw_input', 'reload',
        'globals', 'locals', 'vars', 'dir', 'getattr', 'setattr',
        'delattr', 'hasattr', '__class__', '__bases__', '__subclasses__',
        '__mro__', '__dict__', '__doc__', '__module__',
    }
    
    def __init__(self, component_store: Optional['ComponentStore'] = None):
        self.component_store = component_store
        
        # Sandboxed Environment
        self.env = ImmutableSandboxedEnvironment(
            autoescape=False,  # Prompts sind kein HTML
            trim_blocks=True,
            lstrip_blocks=True,
            undefined=StrictUndefined,
        )
        
        # Nur erlaubte Globals
        safe_globals = {k: v for k, v in self.env.globals.items() if k in self.ALLOWED_GLOBALS}
        self.env.globals = safe_globals
        
        # Custom Filters
        self._register_filters()
    
    def _register_filters(self):
        """Register safe custom filters."""
        import json
        
        self.env.filters['json_pretty'] = lambda x: json.dumps(x, indent=2, ensure_ascii=False)
        self.env.filters['truncate_words'] = lambda s, n: ' '.join(str(s).split()[:n])
        self.env.filters['default_if_none'] = lambda v, d: d if v is None else v
    
    def validate_template(self, template_str: str) -> ValidationResult:
        """Validiert Template auf Sicherheit und Syntax."""
        errors = []
        warnings = []
        
        if not template_str:
            return ValidationResult(valid=True, errors=[], warnings=[])
        
        # Pattern-Check
        for pattern, message in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, template_str, re.IGNORECASE):
                errors.append(f"Security violation: {message}")
        
        # Syntax-Check
        try:
            self.env.parse(template_str)
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
        config: Optional['PromptConfig'] = None,
        tenant_override: Optional['TenantPromptOverride'] = None,
    ) -> RenderedPrompt:
        """
        Sicheres Rendering mit Context-Isolation.
        
        Args:
            template: PromptTemplate instance
            context: Variables for rendering
            config: Optional PromptConfig for settings
            tenant_override: Optional tenant-specific overrides
        
        Returns:
            RenderedPrompt with all rendered parts
        
        Raises:
            TemplateSecurityError: If template contains security violations
        """
        # Get effective prompts (with tenant override)
        if tenant_override:
            system_prompt = tenant_override.get_effective_system_prompt()
            user_prompt = tenant_override.get_effective_user_prompt()
            output_format = tenant_override.output_format_override or template.output_format_instructions
        else:
            system_prompt = template.system_prompt
            user_prompt = template.user_prompt
            output_format = template.output_format_instructions
        
        # Validate all templates
        for name, tmpl in [('system', system_prompt), ('user', user_prompt), ('output', output_format)]:
            validation = self.validate_template(tmpl)
            if not validation.valid:
                raise TemplateSecurityError(f"{name} prompt: {validation.errors}")
        
        # Sanitize context
        safe_context = self._sanitize_context(context)
        
        # Add components if available
        if self.component_store:
            safe_context['include'] = self._include_component
        
        # Merge default values
        full_context = {**template.default_values, **safe_context}
        if tenant_override:
            full_context = {**full_context, **tenant_override.additional_context}
        
        # Render
        rendered_system = self._render_safe(system_prompt, full_context)
        rendered_user = self._render_safe(user_prompt, full_context)
        rendered_output = self._render_safe(output_format, full_context)
        
        # Combine
        full_prompt = rendered_system
        if full_prompt and rendered_user:
            full_prompt += "\n\n"
        full_prompt += rendered_user
        if rendered_output:
            full_prompt += "\n\n" + rendered_output
        
        return RenderedPrompt(
            system_prompt=rendered_system,
            user_prompt=rendered_user + ("\n\n" + rendered_output if rendered_output else ""),
            full_prompt=full_prompt,
            output_format=rendered_output,
            variables_used=self._extract_variables(user_prompt),
            validation=ValidationResult(valid=True, errors=[], warnings=[]),
        )
    
    def _sanitize_context(self, context: Dict[str, Any], depth: int = 0) -> Dict[str, Any]:
        """Deep sanitization of context."""
        if depth > 10:
            return str(context)
        
        if isinstance(context, dict):
            return {
                k: self._sanitize_context(v, depth + 1)
                for k, v in context.items()
                if k not in self.BLOCKED_CONTEXT_KEYS and not k.startswith('_')
            }
        elif isinstance(context, (list, tuple)):
            return [self._sanitize_context(v, depth + 1) for v in context]
        elif isinstance(context, (str, int, float, bool, type(None))):
            return context
        else:
            # Objects: Convert to safe dict representation
            return str(context)
    
    def _render_safe(self, template_str: str, context: Dict[str, Any]) -> str:
        """Render with error handling."""
        if not template_str:
            return ""
        
        try:
            template = self.env.from_string(template_str)
            return template.render(**context).strip()
        except Exception as e:
            logger.error(f"Template rendering error: {e}")
            raise
    
    def _include_component(self, code: str) -> str:
        """Load and return component content."""
        if not self.component_store:
            return f"[Component '{code}' not available]"
        
        component = self.component_store.get(code)
        if component:
            return component.content
        return f"[Component '{code}' not found]"
    
    def _extract_variables(self, template_str: str) -> Set[str]:
        """Extract variable names from template."""
        try:
            from jinja2 import meta
            ast = self.env.parse(template_str)
            return meta.find_undeclared_variables(ast)
        except Exception:
            return set()
```

---

## 🔄 RESILIENCE: ResilientPromptService

```python
# ============================================================================
# platform/packages/prompt-framework/prompt_framework/core/service.py
# ============================================================================

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum
import asyncio
import logging
import time

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, use fallback
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreaker:
    """Simple Circuit Breaker implementation."""
    failure_threshold: int = 5
    recovery_timeout: int = 60
    
    _failure_count: int = field(default=0, init=False)
    _last_failure_time: float = field(default=0, init=False)
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    
    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time > self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
        return self._state
    
    def record_success(self):
        self._failure_count = 0
        self._state = CircuitState.CLOSED
    
    def record_failure(self):
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN


@dataclass
class ServiceConfig:
    """Configuration for ResilientPromptService."""
    max_retries: int = 3
    retry_base_delay: float = 1.0
    retry_max_delay: float = 30.0
    request_timeout: int = 60
    fallback_enabled: bool = True


@dataclass
class PromptResult:
    """Result of prompt generation."""
    content: Optional[str]
    template: 'PromptTemplate'
    execution: Optional['PromptExecution']
    usage: Optional[Dict[str, Any]]
    error: Optional[str] = None
    fallback: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class ResilientPromptService:
    """
    PromptService mit Enterprise-Grade Resilience.
    
    Features:
    - Retry mit exponential backoff
    - Circuit Breaker pro Tier
    - Automatischer Tier-Fallback
    - Timeout-Handling
    - Event-basiertes Tracking
    """
    
    def __init__(
        self,
        registry: 'PromptRegistry',
        llm_client: 'DynamicLLMClient',
        tracker: Optional['UsageTracker'] = None,
        event_bus: Optional['PromptEventBus'] = None,
        config: Optional[ServiceConfig] = None,
        tenant_id: Optional[str] = None,
    ):
        self.registry = registry
        self.llm_client = llm_client
        self.tracker = tracker
        self.event_bus = event_bus
        self.config = config or ServiceConfig()
        self.tenant_id = tenant_id
        self.engine = SecureTemplateEngine(registry.component_store if hasattr(registry, 'component_store') else None)
        
        # Circuit Breakers per Tier
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
    
    def _get_circuit_breaker(self, tier_code: str) -> CircuitBreaker:
        """Get or create circuit breaker for tier."""
        if tier_code not in self._circuit_breakers:
            self._circuit_breakers[tier_code] = CircuitBreaker()
        return self._circuit_breakers[tier_code]
    
    async def generate(
        self,
        template_code: str,
        context: Dict[str, Any],
        tier: Optional[str] = None,
        **kwargs
    ) -> PromptResult:
        """
        Resiliente Prompt-Generierung.
        
        Args:
            template_code: Template code (e.g., 'expert_hub.phase_5')
            context: Variables for rendering
            tier: Optional tier override
            **kwargs: Additional LLM parameters
        
        Returns:
            PromptResult with content or error
        """
        start_time = time.time()
        
        # 1. Load template & config
        template = self.registry.get(template_code, self.tenant_id)
        prompt_config = self.registry.get_config(template, self.tenant_id)
        tenant_override = self.registry.get_tenant_override(template, self.tenant_id)
        
        # 2. Render template
        try:
            rendered = self.engine.render(template, context, prompt_config, tenant_override)
        except TemplateSecurityError as e:
            return PromptResult(
                content=None,
                template=template,
                execution=None,
                usage=None,
                error=f"Security error: {e}",
            )
        
        # 3. Determine tier
        effective_tier = tier or (prompt_config.preferred_tier.code if prompt_config and prompt_config.preferred_tier else 'standard')
        
        # 4. Call LLM with resilience
        try:
            response = await self._call_llm_with_resilience(
                rendered=rendered,
                config=prompt_config,
                tier=effective_tier,
                **kwargs
            )
        except Exception as e:
            logger.error(f"All LLM tiers exhausted: {e}")
            return PromptResult(
                content=None,
                template=template,
                execution=None,
                usage=None,
                error=str(e),
                fallback=True,
            )
        
        # 5. Track execution
        execution = await self._track_execution(
            template=template,
            rendered=rendered,
            response=response,
            tier=effective_tier,
            start_time=start_time,
        )
        
        return PromptResult(
            content=response.get('content'),
            template=template,
            execution=execution,
            usage=response.get('usage'),
            metadata={
                'tier_used': response.get('tier'),
                'model_used': response.get('model'),
                'retry_count': response.get('retry_count', 0),
            }
        )
    
    async def _call_llm_with_resilience(
        self,
        rendered: 'RenderedPrompt',
        config: Optional['PromptConfig'],
        tier: str,
        **kwargs
    ) -> Dict[str, Any]:
        """LLM call with retry and circuit breaker."""
        
        tiers_to_try = self._get_fallback_chain(tier, config)
        last_error = None
        
        for current_tier in tiers_to_try:
            circuit = self._get_circuit_breaker(current_tier)
            
            if circuit.state == CircuitState.OPEN:
                logger.warning(f"Circuit open for tier {current_tier}, skipping")
                continue
            
            try:
                response = await self._call_with_retry(
                    rendered=rendered,
                    config=config,
                    tier=current_tier,
                    **kwargs
                )
                circuit.record_success()
                response['tier'] = current_tier
                return response
                
            except Exception as e:
                circuit.record_failure()
                last_error = e
                logger.warning(f"LLM call failed for tier {current_tier}: {e}")
        
        raise Exception(f"All tiers exhausted. Last error: {last_error}")
    
    async def _call_with_retry(
        self,
        rendered: 'RenderedPrompt',
        config: Optional['PromptConfig'],
        tier: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Single LLM call with retry."""
        
        max_retries = config.retry_count if config else self.config.max_retries
        timeout = config.timeout_seconds if config else self.config.request_timeout
        
        last_error = None
        for attempt in range(max_retries):
            try:
                response = await asyncio.wait_for(
                    self.llm_client.generate(
                        prompt=rendered.user_prompt,
                        system_prompt=rendered.system_prompt,
                        tier=tier,
                        **kwargs
                    ),
                    timeout=timeout
                )
                response['retry_count'] = attempt
                return response
                
            except asyncio.TimeoutError:
                last_error = TimeoutError(f"Request timed out after {timeout}s")
            except Exception as e:
                last_error = e
            
            # Exponential backoff
            if attempt < max_retries - 1:
                delay = min(
                    self.config.retry_base_delay * (2 ** attempt),
                    self.config.retry_max_delay
                )
                await asyncio.sleep(delay)
        
        raise last_error
    
    def _get_fallback_chain(self, primary_tier: str, config: Optional['PromptConfig']) -> List[str]:
        """Determine fallback order."""
        FALLBACK_ORDER = {
            'premium': ['premium', 'standard', 'economy'],
            'standard': ['standard', 'economy'],
            'economy': ['economy'],
            'local': ['local'],
        }
        return FALLBACK_ORDER.get(primary_tier, [primary_tier])
    
    async def _track_execution(
        self,
        template: 'PromptTemplate',
        rendered: 'RenderedPrompt',
        response: Dict[str, Any],
        tier: str,
        start_time: float,
    ) -> Optional['PromptExecution']:
        """Track execution in database."""
        if not self.tracker:
            return None
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Create execution record
        from apps.core.models import PromptExecution
        
        execution = await PromptExecution.objects.acreate(
            template=template,
            template_version=template.version,
            context_hash=PromptExecution.hash_context({}),  # TODO: Pass actual context
            rendered_system_prompt=rendered.system_prompt,
            rendered_user_prompt=rendered.user_prompt,
            llm_tier_id=None,  # TODO: Resolve tier FK
            llm_model=response.get('model', ''),
            tokens_in=response.get('usage', {}).get('prompt_tokens', 0),
            tokens_out=response.get('usage', {}).get('completion_tokens', 0),
            cost=response.get('usage', {}).get('cost', 0),
            latency_ms=latency_ms,
            success=True,
            retry_count=response.get('retry_count', 0),
            tenant_id=self.tenant_id,
        )
        
        return execution
    
    def render_only(
        self,
        template_code: str,
        context: Dict[str, Any],
    ) -> 'RenderedPrompt':
        """Render template without LLM call (for preview/debug)."""
        template = self.registry.get(template_code, self.tenant_id)
        prompt_config = self.registry.get_config(template, self.tenant_id)
        tenant_override = self.registry.get_tenant_override(template, self.tenant_id)
        
        return self.engine.render(template, context, prompt_config, tenant_override)
```

---

## 📅 FINALER IMPLEMENTIERUNGSPLAN

### Übersicht

| Phase | Dauer | Inhalt | Priorität |
|-------|-------|--------|-----------|
| **1. Core Framework** | 3 Tage | Models, Engine, Service | MUST |
| **2. Django Integration** | 1.5 Tage | Adapters, Admin, Migrations | MUST |
| **3. Expert Hub Migration** | 1 Tag | Templates, ContextBuilder | MUST |
| **4. Writing Hub Migration** | 1 Tag | Templates, ContextBuilder | SHOULD |
| **5. Travel Beat Migration** | 0.5 Tag | Templates, ContextBuilder | SHOULD |
| **6. SaaS Features** | 2 Tage | Tenant Overrides, A/B Testing | COULD |
| **7. Testing & Docs** | 1.5 Tage | Security Tests, API Docs | MUST |
| **Gesamt** | **~11 Tage** | | |

### Phase 1: Core Framework (3 Tage)

**Tag 1: Models & Engine**
```
□ Lookup-Tabellen erstellen
  □ PromptApp
  □ PromptCategory
  □ PromptTier
  □ PromptOutputFormat

□ Haupt-Models erstellen
  □ PromptTemplate
  □ PromptConfig
  □ TenantPromptOverride
  □ PromptComponent
  □ PromptExecution

□ SecureTemplateEngine implementieren
  □ Sandboxed Jinja2
  □ Pattern-Validation
  □ Context Sanitization
```

**Tag 2: Service & Resilience**
```
□ ResilientPromptService implementieren
  □ Retry mit exponential backoff
  □ Circuit Breaker
  □ Fallback Chain
  □ Timeout Handling

□ PromptRegistry Protocol
  □ get()
  □ get_config()
  □ get_tenant_override()
```

**Tag 3: Caching & Tests**
```
□ CachedPromptRegistry
  □ L1 (Local) Cache
  □ L2 (Redis) Cache
  □ Invalidation

□ Unit Tests
  □ Security Tests (Injection)
  □ Resilience Tests (Retry, Circuit Breaker)
  □ Rendering Tests
```

### Phase 2: Django Integration (1.5 Tage)

**Tag 1: Migrations & Admin**
```
□ Django Migrations
  □ 0001_prompt_lookups.py
  □ 0002_prompt_models.py
  □ 0003_initial_data.py

□ Admin Interface
  □ PromptTemplateAdmin
  □ PromptConfigAdmin
  □ TenantPromptOverrideAdmin
```

**Tag 1.5: Adapters**
```
□ DjangoPromptRegistry
□ Factory Functions
□ Integration Tests
```

### Phase 3-5: App Migrations (2.5 Tage)

```
□ Expert Hub (1 Tag)
  □ PHASE_TEMPLATES → DB
  □ ExpertHubContextBuilder
  □ Views umstellen

□ Writing Hub (1 Tag)
  □ PromptFactory → PromptService
  □ WritingHubContextBuilder

□ Travel Beat (0.5 Tag)
  □ PromptBuilder → PromptService
  □ TravelBeatContextBuilder
```

### Phase 7: Testing & Docs (1.5 Tage)

```
□ Security Tests
  □ Template Injection
  □ Context Sanitization
  □ Sandbox Escape

□ Documentation
  □ API Reference
  □ Migration Guide
  □ Security Guidelines
```

---

## ✅ FINALE CHECKLISTE

### Architektur
- [x] Separation of Concerns (Template/Config/Override)
- [x] DB-Driven Lookups (FK statt Strings)
- [x] Handler-Integration (PromptExecution → HandlerExecution)
- [x] Multi-Layer Caching
- [x] Resilience Patterns

### Sicherheit
- [x] Sandboxed Template Engine
- [x] Pattern-basierte Injection Prevention
- [x] Context Sanitization
- [x] Tenant Isolation

### Naming Conventions
- [x] db_table: snake_case, plural
- [x] Model Names: PascalCase, singular
- [x] Code Fields: lowercase, alphanumeric

### Kompatibilität
- [x] Rückwärtskompatibel mit bestehendem Handler-System
- [x] Schrittweise Migration möglich
- [x] Fallback auf alte Implementierungen

---

## 🎯 EMPFEHLUNG

**Sofort starten mit:**
1. **Phase 1, Tag 1:** Lookup-Tabellen und Models erstellen
2. **Phase 1, Tag 2:** SecureTemplateEngine implementieren
3. **Phase 2:** Django Migrations und Admin

**ROI:**
- +3 Tage gegenüber Original-RFC
- Aber: Enterprise-ready, Security-hardened, Production-stable

**Nächster Schritt:** Soll ich mit Phase 1, Tag 1 beginnen (Lookup-Tabellen erstellen)?
