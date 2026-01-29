# 🔍 Kritische Analyse: Prompt & Template Framework

**Datum:** 2026-01-28  
**Analysiert gegen:** Best Practices (DB-driven, Separation of Concerns, Naming, Handler-Pattern)

---

## ✅ BESTEHENDE BEST PRACTICES IM CODEBASE

### 1. DB-Driven Frameworks (Vorbildlich)

| Komponente | Location | Bewertung |
|------------|----------|-----------|
| **HandlerCategory** | `apps/core/models/handler_category.py` | ⭐⭐⭐⭐⭐ Exzellent |
| **HandlerPhase** | `apps/writing_hub/models_handler_lookups.py` | ⭐⭐⭐⭐⭐ Exzellent |
| **ErrorStrategy** | `apps/writing_hub/models_handler_lookups.py` | ⭐⭐⭐⭐⭐ Exzellent |
| **Handler** | `apps/core/models/` | ⭐⭐⭐⭐⭐ Exzellent |
| **HandlerRegistry** | `apps/genagent/core/handler_registry.py` | ⭐⭐⭐⭐ Sehr gut |

**Beispiel: HandlerCategory (Best Practice)**
```python
# ✅ RICHTIG: DB-driven statt Enum
class HandlerCategory(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=50, blank=True)
    display_order = models.IntegerField(default=0)
    config = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(default=False)  # Schutz vor Löschung
```

### 2. Separation of Concerns (Gut umgesetzt)

```
apps/
├── core/                    # Shared Models & Utilities
│   └── models/
│       └── handler_category.py
├── bfagent/                 # Business Logic
│   ├── models_handlers.py   # Handler-spezifische Models
│   └── services/
│       └── prompt_factory.py
├── genagent/                # Handler Registry & Execution
│   └── core/
│       └── handler_registry.py
└── writing_hub/             # Domain-spezifisch
    └── models_handler_lookups.py
```

### 3. Naming Conventions (Konsistent)

| Pattern | Beispiele | Status |
|---------|-----------|--------|
| `models_*.py` | `models_handlers.py`, `models_prompt_system.py` | ✅ Konsistent |
| `*_handler.py` | `chapter_writer_handler.py`, `quality_handler.py` | ✅ Konsistent |
| `db_table` | `handler_categories`, `action_handlers` | ✅ snake_case |
| Model Names | `HandlerCategory`, `ActionHandler` | ✅ PascalCase |

---

## ❌ PROBLEME IM RFC-KONZEPT

### Problem 1: Inkonsistenz mit bestehendem Handler-Pattern

**RFC schlägt vor:**
```python
class PromptTemplate(models.Model):
    code = models.CharField(max_length=100, unique=True)
    app = models.CharField(max_length=50)  # ❌ String statt FK
    category = models.CharField(max_length=50)  # ❌ String statt FK
```

**Sollte sein (wie HandlerCategory):**
```python
class PromptCategory(models.Model):
    """DB-driven Prompt Category - analog zu HandlerCategory"""
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=50, blank=True)
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(default=False)

class PromptApp(models.Model):
    """DB-driven App Registry - für Multi-App Support"""
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

class PromptTemplate(models.Model):
    code = models.CharField(max_length=100)
    app = models.ForeignKey(PromptApp, on_delete=models.PROTECT)  # ✅ FK
    category = models.ForeignKey(PromptCategory, on_delete=models.PROTECT)  # ✅ FK
    # ...
    
    class Meta:
        unique_together = ['code', 'app', 'tenant_id']
```

### Problem 2: Fehlende Lookup-Tabellen

**RFC fehlt:**
- `PromptCategory` (analog zu `HandlerCategory`)
- `PromptApp` (analog zu `DomainType`)
- `PromptTier` (analog zu `LLMTier` aber DB-driven)
- `PromptOutputFormat` (json, markdown, text als DB-Lookup)

**Korrektur:**
```python
class PromptTier(models.Model):
    """LLM Tier als DB-Lookup statt Enum"""
    code = models.CharField(max_length=20, unique=True)  # economy, standard, premium
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    cost_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    default_model = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

class PromptOutputFormat(models.Model):
    """Output Format als DB-Lookup"""
    code = models.CharField(max_length=20, unique=True)  # json, markdown, text
    name = models.CharField(max_length=100)
    template_suffix = models.TextField(blank=True)  # Standard-Anweisungen
    is_active = models.BooleanField(default=True)
```

### Problem 3: Naming Convention Verletzung

**RFC verwendet:**
```python
db_table = 'prompt_templates'  # ❌ Inkonsistent
db_table = 'prompt_components'
db_table = 'prompt_executions'
```

**Sollte sein (wie Handler-System):**
```python
# Bestehende Konvention im Codebase:
db_table = 'handler_categories'
db_table = 'handler_phases'
db_table = 'error_strategies'
db_table = 'action_handlers'

# Prompt-System sollte folgen:
db_table = 'prompt_categories'
db_table = 'prompt_apps'
db_table = 'prompt_tiers'
db_table = 'prompt_output_formats'
db_table = 'prompt_templates'
db_table = 'prompt_components'
db_table = 'prompt_executions'
```

### Problem 4: Fehlende Integration mit HandlerExecution

**RFC:**
```python
class PromptExecution(models.Model):
    template = models.ForeignKey(PromptTemplate, ...)
    # Separate Tracking
```

**Besser: Integration mit bestehendem System:**
```python
class PromptExecution(models.Model):
    template = models.ForeignKey(PromptTemplate, ...)
    handler_execution = models.ForeignKey(
        'bfagent.HandlerExecution',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='prompt_executions',
        help_text="Verknüpfung zur Handler-Ausführung"
    )
    # So können Prompt-Kosten dem Handler zugeordnet werden
```

---

## 🔧 KORRIGIERTES DATENMODELL

### Vollständige Lookup-Tabellen

```python
# ============================================================================
# LOOKUP TABLES - DB-driven statt Enums
# ============================================================================

class PromptApp(models.Model):
    """
    App Registry für Multi-Hub Support
    Analog zu DomainType
    """
    code = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, default='bi-app')
    color = models.CharField(max_length=50, blank=True, default='primary')
    is_active = models.BooleanField(default=True, db_index=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'prompt_apps'
        ordering = ['sort_order', 'name']
        verbose_name = 'Prompt App'
        verbose_name_plural = 'Prompt Apps'
    
    @classmethod
    def get_default_apps(cls):
        return [
            {'code': 'expert_hub', 'name': 'Expert Hub', 'icon': 'bi-shield-check', 'color': 'danger'},
            {'code': 'writing_hub', 'name': 'Writing Hub', 'icon': 'bi-book', 'color': 'primary'},
            {'code': 'risk_hub', 'name': 'Risk Hub', 'icon': 'bi-exclamation-triangle', 'color': 'warning'},
            {'code': 'travel_beat', 'name': 'Travel Beat', 'icon': 'bi-airplane', 'color': 'info'},
        ]


class PromptCategory(models.Model):
    """
    Prompt Category - analog zu HandlerCategory
    """
    code = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, default='bi-chat-dots')
    color = models.CharField(max_length=50, blank=True, default='info')
    display_order = models.IntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    is_system = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'prompt_categories'
        ordering = ['display_order', 'name']
        verbose_name = 'Prompt Category'
        verbose_name_plural = 'Prompt Categories'
    
    @classmethod
    def get_default_categories(cls):
        return [
            {'code': 'phase', 'name': 'Workflow Phase', 'icon': 'bi-diagram-3', 'is_system': True},
            {'code': 'generation', 'name': 'Content Generation', 'icon': 'bi-magic', 'is_system': True},
            {'code': 'analysis', 'name': 'Analysis', 'icon': 'bi-search', 'is_system': True},
            {'code': 'transformation', 'name': 'Transformation', 'icon': 'bi-arrow-repeat', 'is_system': True},
            {'code': 'component', 'name': 'Reusable Component', 'icon': 'bi-puzzle', 'is_system': True},
        ]


class PromptTier(models.Model):
    """
    LLM Tier - DB-driven statt Enum
    """
    code = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    cost_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    default_provider = models.CharField(max_length=50, blank=True)
    default_model = models.CharField(max_length=100, blank=True)
    max_tokens_default = models.IntegerField(default=2000)
    temperature_default = models.FloatField(default=0.7)
    is_active = models.BooleanField(default=True, db_index=True)
    sort_order = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'prompt_tiers'
        ordering = ['sort_order']
        verbose_name = 'Prompt Tier'
        verbose_name_plural = 'Prompt Tiers'
    
    @classmethod
    def get_default_tiers(cls):
        return [
            {'code': 'economy', 'name': 'Economy', 'cost_multiplier': 0.1, 'default_model': 'gpt-3.5-turbo'},
            {'code': 'standard', 'name': 'Standard', 'cost_multiplier': 1.0, 'default_model': 'gpt-4o-mini'},
            {'code': 'premium', 'name': 'Premium', 'cost_multiplier': 10.0, 'default_model': 'gpt-4o'},
            {'code': 'local', 'name': 'Local', 'cost_multiplier': 0.0, 'default_model': 'llama3.2'},
        ]


class PromptOutputFormat(models.Model):
    """
    Output Format - DB-driven
    """
    code = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    format_instructions = models.TextField(blank=True, help_text="Standard-Anweisungen für dieses Format")
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'prompt_output_formats'
        ordering = ['sort_order']
    
    @classmethod
    def get_default_formats(cls):
        return [
            {'code': 'json', 'name': 'JSON', 'format_instructions': 'Return your response as valid JSON.'},
            {'code': 'markdown', 'name': 'Markdown', 'format_instructions': 'Format your response in Markdown.'},
            {'code': 'text', 'name': 'Plain Text', 'format_instructions': ''},
            {'code': 'html', 'name': 'HTML', 'format_instructions': 'Format your response as HTML.'},
        ]


# ============================================================================
# MAIN MODELS - Mit FK zu Lookups
# ============================================================================

class PromptTemplate(models.Model):
    """
    Prompt Template - Korrigiert mit FK statt Strings
    """
    # Identity
    code = models.CharField(max_length=100, db_index=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Relations (FK statt String!)
    app = models.ForeignKey(
        PromptApp,
        on_delete=models.PROTECT,
        related_name='templates',
        help_text="App, zu der dieses Template gehört"
    )
    category = models.ForeignKey(
        PromptCategory,
        on_delete=models.PROTECT,
        related_name='templates',
        help_text="Kategorie des Templates"
    )
    preferred_tier = models.ForeignKey(
        PromptTier,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='templates',
        help_text="Bevorzugter LLM-Tier"
    )
    output_format = models.ForeignKey(
        PromptOutputFormat,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='templates',
        help_text="Standard-Ausgabeformat"
    )
    
    # Content
    system_prompt = models.TextField(blank=True)
    user_prompt = models.TextField()
    output_format_instructions = models.TextField(blank=True)
    
    # Variables
    variables = models.JSONField(default=dict, help_text="Variable Schema")
    default_values = models.JSONField(default=dict, help_text="Default-Werte")
    
    # LLM Settings
    preferred_model = models.CharField(max_length=100, blank=True)
    max_tokens = models.IntegerField(default=2000)
    temperature = models.FloatField(default=0.7)
    
    # Versioning
    version = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True, db_index=True)
    
    # Multi-Tenancy
    tenant_id = models.UUIDField(null=True, blank=True, db_index=True)
    parent = models.ForeignKey(
        'self',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='overrides',
        help_text="Parent-Template für Overrides"
    )
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_prompt_templates'
    )
    
    class Meta:
        db_table = 'prompt_templates'
        unique_together = ['code', 'app', 'tenant_id', 'version']
        ordering = ['app', 'category', 'code']
        indexes = [
            models.Index(fields=['app', 'category', 'is_active']),
            models.Index(fields=['tenant_id', 'is_active']),
            models.Index(fields=['code', 'version']),
        ]
        verbose_name = 'Prompt Template'
        verbose_name_plural = 'Prompt Templates'


class PromptComponent(models.Model):
    """
    Wiederverwendbare Prompt-Komponenten
    """
    code = models.CharField(max_length=100, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    category = models.ForeignKey(
        PromptCategory,
        on_delete=models.PROTECT,
        related_name='components',
        limit_choices_to={'code': 'component'}
    )
    
    content = models.TextField(help_text="Jinja2 Template Content")
    
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'prompt_components'
        ordering = ['code']


class PromptExecution(models.Model):
    """
    Prompt Execution Tracking - Integriert mit Handler-System
    """
    # Template Reference
    template = models.ForeignKey(
        PromptTemplate,
        on_delete=models.SET_NULL,
        null=True,
        related_name='executions'
    )
    template_version = models.IntegerField()
    
    # Integration mit Handler-System
    handler_execution = models.ForeignKey(
        'bfagent.HandlerExecution',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='prompt_executions',
        help_text="Verknüpfung zur Handler-Ausführung"
    )
    
    # Rendered Content
    context_hash = models.CharField(max_length=64, db_index=True)
    rendered_system_prompt = models.TextField(blank=True)
    rendered_user_prompt = models.TextField()
    
    # LLM Details
    llm_tier = models.ForeignKey(
        PromptTier,
        on_delete=models.SET_NULL,
        null=True,
        related_name='executions'
    )
    llm_model = models.CharField(max_length=100)
    tokens_in = models.IntegerField(default=0)
    tokens_out = models.IntegerField(default=0)
    cost = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    latency_ms = models.IntegerField(default=0)
    
    # Result
    success = models.BooleanField(default=True, db_index=True)
    error_message = models.TextField(blank=True)
    user_rating = models.IntegerField(null=True, blank=True)
    
    # Multi-Tenancy
    tenant_id = models.UUIDField(null=True, blank=True, db_index=True)
    user = models.ForeignKey(
        'auth.User',
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
        ]
```

---

## 📋 CHECKLISTE FÜR RFC-UPDATE

### Datenmodell

- [ ] `PromptApp` Lookup-Tabelle hinzufügen
- [ ] `PromptCategory` Lookup-Tabelle hinzufügen (analog HandlerCategory)
- [ ] `PromptTier` Lookup-Tabelle hinzufügen (statt Enum)
- [ ] `PromptOutputFormat` Lookup-Tabelle hinzufügen
- [ ] `PromptTemplate.app` → FK statt String
- [ ] `PromptTemplate.category` → FK statt String
- [ ] `PromptTemplate.preferred_tier` → FK statt String
- [ ] `PromptExecution.handler_execution` → FK für Integration

### Naming Conventions

- [ ] Alle `db_table` Namen prüfen (snake_case, Plural)
- [ ] Model-Namen prüfen (PascalCase, Singular)
- [ ] Code-Felder prüfen (lowercase, alphanumeric)

### Integration

- [ ] Integration mit `HandlerExecution` dokumentieren
- [ ] Integration mit `LLMRegistry` aus creative-services
- [ ] Migration von bestehenden Prompt-Systemen planen

### Default Data

- [ ] `get_default_*()` Methoden für alle Lookups
- [ ] Migration für Initial Data
- [ ] `is_system` Flag für System-Kategorien

---

## 🎯 EMPFEHLUNG

**Das RFC-Konzept ist grundsätzlich gut, aber:**

1. **Lookup-Tabellen fehlen** - Analog zum Handler-System sollten alle Kategorien, Tiers, Formate als DB-Lookups implementiert werden

2. **FK statt Strings** - `app` und `category` sollten ForeignKeys sein, nicht Strings

3. **Integration mit Handler-System** - `PromptExecution` sollte mit `HandlerExecution` verknüpft werden

4. **Naming Conventions** - Bereits gut, aber `db_table` Namen sollten konsistent sein

**Nächster Schritt:** RFC mit diesen Korrekturen aktualisieren, dann Phase 1 starten.
