# 🏗️ Unified Prompt & Template Framework - RFC

**Version:** 1.0  
**Datum:** 2026-01-28  
**Status:** Draft für Review  
**Autor:** Cascade (IT-Architekt)

---

## 📋 Executive Summary

Dieses RFC beschreibt ein **einheitliches Prompt & Template Framework** für das gesamte BF Agent Ökosystem (Risk-Hub, Expert-Hub, Writing-Hub, Travel-Beat). Das Framework ermöglicht:

- **Multi-Tenant SaaS-Fähigkeit** mit kundenspezifischen Prompts
- **Wiederverwendbare Komponenten** über alle Apps hinweg
- **Versionierung & A/B-Testing** für kontinuierliche Optimierung
- **Kostenoptimierung** durch Tier-basierte LLM-Auswahl

---

## 🔍 IST-ANALYSE

### Aktuelle Implementierungen (4 verschiedene Systeme)

| System | Location | Ansatz | Stärken | Schwächen |
|--------|----------|--------|---------|-----------|
| **Writing Hub Prompt System** | `apps/writing_hub/models_prompt_system.py` | Django Models für Image-Prompts | Strukturiert, DB-driven, Komponenten | Nur für Bilder, nicht generisch |
| **PromptFactory** | `apps/bfagent/services/prompt_factory.py` | Jinja2 + DB Templates | Caching, Variablen, Wiederverwendbar | Nur in bfagent, keine Tier-Auswahl |
| **Expert Hub Prompts** | `apps/expert_hub/prompts.py` | Python Dicts + Dataclasses | Phasen-spezifisch, Kontext-aware | Hardcoded, keine DB, nicht erweiterbar |
| **Travel Beat Prompts** | `apps/stories/services/prompts.py` | Python Klassen | Genre-aware, Story Beats | Keine DB, keine Wiederverwendung |

### Platform Package (creative-services)

| Komponente | Status | Beschreibung |
|------------|--------|--------------|
| `LLMClient` | ✅ Vorhanden | Basis-Client für LLM-Aufrufe |
| `LLMRegistry` | ✅ Vorhanden | Tier-basierte Modellauswahl |
| `UsageTracker` | ✅ Vorhanden | Kosten-Tracking |
| `PromptRegistry` | ❌ Fehlt | Zentrale Prompt-Verwaltung |
| `TemplateEngine` | ❌ Fehlt | Einheitliche Template-Verarbeitung |

---

## 🎯 ANFORDERUNGEN

### Funktionale Anforderungen

| ID | Anforderung | Priorität | Apps |
|----|-------------|-----------|------|
| F1 | Prompts in Datenbank speichern und versionieren | MUST | Alle |
| F2 | Jinja2-Templates mit Variablen-Substitution | MUST | Alle |
| F3 | Wiederverwendbare Prompt-Komponenten | MUST | Alle |
| F4 | Phasen-/Workflow-spezifische Prompts | MUST | Expert-Hub, Writing-Hub |
| F5 | Genre-/Stil-spezifische Prompts | MUST | Writing-Hub, Travel-Beat |
| F6 | Kundenspezifische Prompt-Overrides (SaaS) | SHOULD | Alle |
| F7 | A/B-Testing von Prompts | SHOULD | Alle |
| F8 | Prompt-Performance-Tracking | SHOULD | Alle |
| F9 | Multi-Language Support | COULD | Alle |
| F10 | Prompt-Import/Export | COULD | Alle |

### Nicht-Funktionale Anforderungen

| ID | Anforderung | Zielwert |
|----|-------------|----------|
| NF1 | Template-Rendering < 10ms | Performance |
| NF2 | Cache-Hit-Rate > 95% | Performance |
| NF3 | Keine Code-Änderung für Prompt-Updates | Wartbarkeit |
| NF4 | Rückwärtskompatibel mit bestehenden Systemen | Migration |
| NF5 | Mandantenfähig (Tenant-Isolation) | SaaS |

---

## 🏛️ ARCHITEKTUR

### Schichtenmodell

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         APPLICATION LAYER                                │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │
│  │  Risk-Hub   │ │ Expert-Hub  │ │ Writing-Hub │ │ Travel-Beat │       │
│  │   (neu)     │ │  (bfagent)  │ │  (bfagent)  │ │  (separate) │       │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘       │
└─────────┼───────────────┼───────────────┼───────────────┼───────────────┘
          │               │               │               │
          ▼               ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      PROMPT FRAMEWORK LAYER                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    PromptService (Facade)                        │   │
│  │  - build(template_code, context, tier) → PromptResult           │   │
│  │  - render(template_code, context) → str                          │   │
│  │  - get_template(code) → PromptTemplate                           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                │                                         │
│          ┌────────────────────┼────────────────────┐                    │
│          ▼                    ▼                    ▼                    │
│  ┌───────────────┐   ┌───────────────┐   ┌───────────────┐             │
│  │TemplateEngine │   │PromptRegistry │   │ContextBuilder │             │
│  │  (Jinja2)     │   │   (DB/Cache)  │   │  (Enrichment) │             │
│  └───────────────┘   └───────────────┘   └───────────────┘             │
│                                │                                         │
│                    ┌───────────┴───────────┐                            │
│                    ▼                       ▼                            │
│          ┌───────────────┐       ┌───────────────┐                      │
│          │ComponentStore │       │ TenantOverride│                      │
│          │(Reusable Parts)│       │   (SaaS)     │                      │
│          └───────────────┘       └───────────────┘                      │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       LLM LAYER (creative-services)                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│  │ DynamicLLMClient│  │   LLMRegistry   │  │  UsageTracker   │         │
│  │ (Tier-Selection)│  │ (Model Config)  │  │ (Cost Tracking) │         │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘         │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         LLM PROVIDERS                                    │
│     OpenAI    │    Anthropic    │    OpenRouter    │    Ollama          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Datenmodell

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           PromptTemplate                                 │
├─────────────────────────────────────────────────────────────────────────┤
│ id: UUID                                                                 │
│ code: str (unique per app+tenant)     # z.B. "expert_hub.phase_5"       │
│ app: str                              # "expert_hub", "writing_hub"...  │
│ category: str                         # "phase", "generation", "analysis"│
│ name: str                             # Human-readable name              │
│ description: str                                                         │
│ ─────────────────────────────────────────────────────────────────────── │
│ system_prompt: text                   # System message template          │
│ user_prompt: text                     # User message template (Jinja2)   │
│ output_format: text                   # Output instructions              │
│ ─────────────────────────────────────────────────────────────────────── │
│ variables: JSON                       # Required variables schema        │
│ default_values: JSON                  # Default variable values          │
│ ─────────────────────────────────────────────────────────────────────── │
│ preferred_tier: LLMTier               # ECONOMY, STANDARD, PREMIUM       │
│ preferred_model: str (optional)       # Specific model override          │
│ max_tokens: int                                                          │
│ temperature: float                                                       │
│ ─────────────────────────────────────────────────────────────────────── │
│ version: int                          # For A/B testing                  │
│ is_active: bool                                                          │
│ tenant_id: UUID (nullable)            # NULL = global, else tenant-specific│
│ parent_id: UUID (nullable)            # For inheritance/override         │
│ ─────────────────────────────────────────────────────────────────────── │
│ created_at, updated_at, created_by                                       │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                │ 1:n
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         PromptComponent                                  │
├─────────────────────────────────────────────────────────────────────────┤
│ id: UUID                                                                 │
│ code: str (unique)                    # z.B. "output_json", "quality"   │
│ name: str                                                                │
│ content: text                         # Jinja2 template snippet          │
│ category: str                         # "output", "style", "instruction" │
│ is_active: bool                                                          │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                         PromptExecution                                  │
├─────────────────────────────────────────────────────────────────────────┤
│ id: UUID                                                                 │
│ template_id: FK → PromptTemplate                                         │
│ template_version: int                                                    │
│ ─────────────────────────────────────────────────────────────────────── │
│ context_hash: str                     # Hash of input context            │
│ rendered_prompt: text                 # Final rendered prompt            │
│ ─────────────────────────────────────────────────────────────────────── │
│ llm_model: str                        # Actual model used                │
│ llm_tier: str                                                            │
│ tokens_in: int                                                           │
│ tokens_out: int                                                          │
│ cost: Decimal                                                            │
│ latency_ms: int                                                          │
│ ─────────────────────────────────────────────────────────────────────── │
│ success: bool                                                            │
│ error_message: str (nullable)                                            │
│ user_rating: int (1-5, nullable)      # For quality feedback             │
│ ─────────────────────────────────────────────────────────────────────── │
│ tenant_id: UUID                                                          │
│ user_id: UUID                                                            │
│ created_at                                                               │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🔧 KOMPONENTEN-DESIGN

### 1. PromptService (Facade)

```python
class PromptService:
    """
    Zentrale Facade für alle Prompt-Operationen.
    Vereint Template-Rendering, LLM-Auswahl und Tracking.
    """
    
    def __init__(
        self,
        registry: PromptRegistry,
        llm_client: DynamicLLMClient,
        tracker: UsageTracker,
        tenant_id: Optional[UUID] = None
    ):
        self.registry = registry
        self.llm_client = llm_client
        self.tracker = tracker
        self.tenant_id = tenant_id
        self.engine = TemplateEngine()
    
    async def generate(
        self,
        template_code: str,
        context: Dict[str, Any],
        tier: Optional[LLMTier] = None,
        **kwargs
    ) -> PromptResult:
        """
        Vollständiger Prompt-Workflow:
        1. Template laden (mit Tenant-Override)
        2. Context anreichern
        3. Template rendern
        4. LLM aufrufen (mit Tier-Auswahl)
        5. Execution tracken
        """
        # 1. Template laden
        template = self.registry.get(
            template_code, 
            tenant_id=self.tenant_id
        )
        
        # 2. Context anreichern
        enriched_context = self._enrich_context(context, template)
        
        # 3. Template rendern
        rendered = self.engine.render(template, enriched_context)
        
        # 4. LLM aufrufen
        tier = tier or template.preferred_tier
        response = await self.llm_client.generate(
            prompt=rendered.user_prompt,
            system_prompt=rendered.system_prompt,
            tier=tier,
            max_tokens=template.max_tokens,
            temperature=template.temperature,
            **kwargs
        )
        
        # 5. Execution tracken
        execution = self._track_execution(template, rendered, response)
        
        return PromptResult(
            content=response.content,
            template=template,
            execution=execution,
            usage=response.usage
        )
    
    def render_only(
        self,
        template_code: str,
        context: Dict[str, Any]
    ) -> RenderedPrompt:
        """Nur rendern, ohne LLM-Aufruf (für Preview/Debug)."""
        template = self.registry.get(template_code, self.tenant_id)
        return self.engine.render(template, context)
```

### 2. PromptRegistry

```python
class PromptRegistry(Protocol):
    """
    Protocol für Prompt-Speicherung.
    Implementierungen: DjangoPromptRegistry, DictPromptRegistry
    """
    
    def get(
        self, 
        code: str, 
        tenant_id: Optional[UUID] = None,
        version: Optional[int] = None
    ) -> PromptTemplate:
        """
        Lädt Template mit Tenant-Fallback:
        1. Tenant-spezifisches Template (wenn vorhanden)
        2. Globales Template (tenant_id=NULL)
        3. TemplateNotFoundError
        """
        ...
    
    def list_by_app(self, app: str) -> List[PromptTemplate]:
        """Alle Templates einer App."""
        ...
    
    def list_by_category(self, category: str) -> List[PromptTemplate]:
        """Alle Templates einer Kategorie."""
        ...
    
    def save(self, template: PromptTemplate) -> PromptTemplate:
        """Speichert Template (mit Auto-Versionierung)."""
        ...
    
    def create_tenant_override(
        self,
        base_code: str,
        tenant_id: UUID,
        overrides: Dict[str, Any]
    ) -> PromptTemplate:
        """Erstellt Tenant-spezifische Variante."""
        ...
```

### 3. TemplateEngine

```python
class TemplateEngine:
    """
    Jinja2-basierte Template-Engine mit Erweiterungen.
    """
    
    def __init__(self):
        self.env = Environment(
            loader=BaseLoader(),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._register_filters()
        self._register_globals()
    
    def render(
        self,
        template: PromptTemplate,
        context: Dict[str, Any]
    ) -> RenderedPrompt:
        """Rendert Template mit allen Komponenten."""
        # Komponenten laden
        components = self._load_components(template)
        
        # Context erweitern
        full_context = {
            **context,
            'components': components,
            'include': self._include_component,
        }
        
        # Rendern
        system = self._render_string(template.system_prompt, full_context)
        user = self._render_string(template.user_prompt, full_context)
        output = self._render_string(template.output_format, full_context)
        
        return RenderedPrompt(
            system_prompt=system,
            user_prompt=f"{user}\n\n{output}" if output else user,
            full_prompt=f"{system}\n\n{user}" if system else user,
            variables_used=self._extract_variables(template),
        )
    
    def _include_component(self, code: str) -> str:
        """Lädt und rendert eine Komponente."""
        component = self.component_store.get(code)
        return component.content if component else f"[Component '{code}' not found]"
    
    def validate(self, template_str: str) -> ValidationResult:
        """Validiert Template-Syntax."""
        try:
            self.env.parse(template_str)
            return ValidationResult(valid=True)
        except TemplateSyntaxError as e:
            return ValidationResult(valid=False, error=str(e))
```

### 4. ContextBuilder (App-spezifisch)

```python
class BaseContextBuilder:
    """Basis-Klasse für Context-Anreicherung."""
    
    def build(self, raw_context: Dict[str, Any]) -> Dict[str, Any]:
        """Template-Method Pattern."""
        context = self._sanitize(raw_context)
        context = self._add_defaults(context)
        context = self._enrich(context)
        return context
    
    def _sanitize(self, context: Dict) -> Dict:
        """Entfernt gefährliche Keys."""
        dangerous = {'__builtins__', 'eval', 'exec', 'open'}
        return {k: v for k, v in context.items() if k not in dangerous}
    
    def _add_defaults(self, context: Dict) -> Dict:
        """Fügt Standard-Werte hinzu."""
        return {
            'timestamp': datetime.now().isoformat(),
            'language': 'de',
            **context
        }
    
    def _enrich(self, context: Dict) -> Dict:
        """Override in Subklassen für App-spezifische Anreicherung."""
        return context


class ExpertHubContextBuilder(BaseContextBuilder):
    """Context-Builder für Expert Hub (Explosionsschutz)."""
    
    def _enrich(self, context: Dict) -> Dict:
        context = super()._enrich(context)
        
        # Phase-spezifische Daten laden
        if 'phase_number' in context:
            context['phase_template'] = self._get_phase_template(context['phase_number'])
            context['related_phases'] = self._get_related_phases(context)
        
        # Dokumente formatieren
        if 'documents' in context:
            context['document_list_md'] = self._format_documents(context['documents'])
        
        return context


class WritingHubContextBuilder(BaseContextBuilder):
    """Context-Builder für Writing Hub (Buchschreiben)."""
    
    def _enrich(self, context: Dict) -> Dict:
        context = super()._enrich(context)
        
        # Projekt-Daten
        if 'project' in context:
            context['genre_guide'] = self._get_genre_guide(context['project'].genre)
            context['style_guide'] = self._get_style_guide(context['project'])
        
        # Charakter-Daten
        if 'characters' in context:
            context['character_prompts'] = self._build_character_prompts(context['characters'])
        
        return context


class TravelBeatContextBuilder(BaseContextBuilder):
    """Context-Builder für Travel Beat (Reise-Geschichten)."""
    
    def _enrich(self, context: Dict) -> Dict:
        context = super()._enrich(context)
        
        # Genre & Spice Level
        if 'genre' in context:
            context['genre_guide'] = GENRE_PROMPTS.get(context['genre'], '')
        if 'spice_level' in context:
            context['spice_guide'] = SPICE_LEVELS.get(context['spice_level'], '')
        
        # Story Beats
        if 'story_beat' in context:
            context['beat_guide'] = STORY_BEATS.get(context['story_beat'], '')
        
        return context
```

---

## 📦 PACKAGE-STRUKTUR

```
platform/
└── packages/
    └── prompt-framework/
        ├── pyproject.toml
        ├── README.md
        └── prompt_framework/
            ├── __init__.py
            ├── core/
            │   ├── __init__.py
            │   ├── service.py          # PromptService
            │   ├── registry.py         # PromptRegistry Protocol
            │   ├── engine.py           # TemplateEngine
            │   ├── context.py          # BaseContextBuilder
            │   └── models.py           # PromptTemplate, PromptComponent, etc.
            ├── storage/
            │   ├── __init__.py
            │   ├── dict_registry.py    # In-Memory (Testing)
            │   └── file_registry.py    # YAML/JSON Files
            └── adapters/
                ├── __init__.py
                ├── django.py           # DjangoPromptRegistry
                └── fastapi.py          # FastAPI Integration

bfagent/
└── apps/
    ├── core/
    │   └── prompt_adapters.py          # Django-spezifische Adapter
    ├── expert_hub/
    │   └── context_builders.py         # ExpertHubContextBuilder
    ├── writing_hub/
    │   └── context_builders.py         # WritingHubContextBuilder
    └── risk_hub/                        # NEU
        └── context_builders.py         # RiskHubContextBuilder

travel-beat/
└── apps/
    └── stories/
        └── context_builders.py         # TravelBeatContextBuilder
```

---

## 🔄 MIGRATIONS-STRATEGIE

### Phase 1: Framework erstellen (1-2 Tage)

1. **Package `prompt-framework` erstellen**
   - Core-Klassen implementieren
   - Unit Tests schreiben
   - Dokumentation

2. **Django-Adapter erstellen**
   - Models für PromptTemplate, PromptComponent, PromptExecution
   - DjangoPromptRegistry implementieren
   - Admin-Interface

### Phase 2: Expert Hub migrieren (1 Tag)

1. **Bestehende PHASE_TEMPLATES in DB migrieren**
   ```python
   # Migration: 0010_migrate_prompts.py
   def migrate_expert_hub_prompts(apps, schema_editor):
       PromptTemplate = apps.get_model('core', 'PromptTemplate')
       for phase_num, template in PHASE_TEMPLATES.items():
           PromptTemplate.objects.create(
               code=f'expert_hub.phase_{phase_num}',
               app='expert_hub',
               category='phase',
               system_prompt=template['system_prompt'],
               user_prompt=template['user_prompt'],
               output_format=template.get('output_format', ''),
           )
   ```

2. **PhasePromptRenderer auf PromptService umstellen**
   ```python
   # Vorher
   renderer = PhasePromptRenderer(context)
   prompts = renderer.get_full_prompt_for_llm()
   
   # Nachher
   service = PromptService(registry, llm_client, tracker)
   result = await service.generate(f'expert_hub.phase_{phase.number}', context)
   ```

### Phase 3: Writing Hub migrieren (1 Tag)

1. **PromptFactory durch PromptService ersetzen**
2. **Image Prompt System integrieren**
3. **Bestehende Templates migrieren**

### Phase 4: Travel Beat migrieren (0.5 Tage)

1. **PromptBuilder durch PromptService ersetzen**
2. **Genre/Spice/Beat-Templates in DB**

### Phase 5: Risk Hub (neu) (0.5 Tage)

1. **Neue Templates erstellen**
2. **RiskHubContextBuilder implementieren**

---

## 🎯 SaaS-FEATURES

### Multi-Tenancy

```python
# Tenant-spezifischer Service
class TenantPromptService:
    def __init__(self, tenant: Tenant):
        self.tenant = tenant
        self.service = PromptService(
            registry=DjangoPromptRegistry(),
            llm_client=self._get_tenant_llm_client(),
            tracker=TenantUsageTracker(tenant),
            tenant_id=tenant.id
        )
    
    def _get_tenant_llm_client(self) -> DynamicLLMClient:
        """LLM-Client mit Tenant-spezifischen API-Keys."""
        registry = TenantLLMRegistry(self.tenant)
        return DynamicLLMClient(registry)
```

### Prompt-Customization UI

```
┌─────────────────────────────────────────────────────────────────┐
│ 🎨 Prompt Customization - Expert Hub Phase 5                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ Base Template: expert_hub.phase_5 (Global)                      │
│ ☑️ Create Tenant Override                                        │
│                                                                  │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ System Prompt:                                               │ │
│ │ ┌─────────────────────────────────────────────────────────┐ │ │
│ │ │ Du bist ein Gefahrstoff-Experte und erfasst...         │ │ │
│ │ │ [Tenant-spezifische Anpassungen hier]                   │ │ │
│ │ └─────────────────────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│ Variables: {{ project_name }}, {{ document_list }}              │
│                                                                  │
│ [Preview] [Test] [Save as Override]                             │
└─────────────────────────────────────────────────────────────────┘
```

### A/B Testing

```python
class ABTestingService:
    def get_template_variant(
        self,
        template_code: str,
        user_id: UUID
    ) -> PromptTemplate:
        """Wählt Template-Variante basierend auf User-Hash."""
        variants = self.registry.get_variants(template_code)
        if not variants:
            return self.registry.get(template_code)
        
        # Konsistente Zuweisung pro User
        variant_index = hash(f"{template_code}:{user_id}") % len(variants)
        return variants[variant_index]
    
    def track_result(
        self,
        execution_id: UUID,
        success: bool,
        user_rating: Optional[int] = None
    ):
        """Trackt Ergebnis für A/B-Analyse."""
        ...
```

---

## 📊 METRIKEN & MONITORING

### Dashboard-Metriken

| Metrik | Beschreibung | Ziel |
|--------|--------------|------|
| Template Usage | Aufrufe pro Template | Tracking |
| Success Rate | Erfolgreiche Generierungen | > 95% |
| Avg. Latency | Durchschnittliche Antwortzeit | < 3s |
| Cost per Template | Kosten pro Template | Optimierung |
| User Rating | Durchschnittliche Bewertung | > 4.0 |
| Cache Hit Rate | Template-Cache-Treffer | > 95% |

### Alerting

```python
ALERTS = {
    'high_error_rate': {
        'condition': 'error_rate > 0.05',
        'action': 'notify_ops',
    },
    'high_cost': {
        'condition': 'daily_cost > budget * 0.8',
        'action': 'notify_finance',
    },
    'low_rating': {
        'condition': 'avg_rating < 3.0 for template',
        'action': 'notify_content_team',
    },
}
```

---

## ✅ REVIEW-CHECKLISTE

### Architektur

- [ ] Schichtenmodell klar und sinnvoll?
- [ ] Abhängigkeiten in richtige Richtung?
- [ ] Erweiterbarkeit für neue Apps gegeben?
- [ ] SaaS-Anforderungen erfüllt?

### Datenmodell

- [ ] Alle notwendigen Felder vorhanden?
- [ ] Tenant-Isolation korrekt?
- [ ] Versionierung sinnvoll?
- [ ] Performance-Indizes definiert?

### Migration

- [ ] Rückwärtskompatibilität gewährleistet?
- [ ] Schrittweise Migration möglich?
- [ ] Rollback-Strategie vorhanden?
- [ ] Testabdeckung ausreichend?

### Sicherheit

- [ ] Template-Injection verhindert?
- [ ] Tenant-Isolation sicher?
- [ ] API-Key-Handling korrekt?
- [ ] Rate-Limiting vorgesehen?

---

## 📅 TIMELINE

| Phase | Dauer | Abhängigkeiten |
|-------|-------|----------------|
| 1. Framework Package | 2 Tage | - |
| 2. Django Integration | 1 Tag | Phase 1 |
| 3. Expert Hub Migration | 1 Tag | Phase 2 |
| 4. Writing Hub Migration | 1 Tag | Phase 2 |
| 5. Travel Beat Migration | 0.5 Tage | Phase 2 |
| 6. Risk Hub (neu) | 0.5 Tage | Phase 2 |
| 7. SaaS Features | 2 Tage | Phase 3-6 |
| 8. Monitoring & Dashboards | 1 Tag | Phase 7 |
| **Gesamt** | **~9 Tage** | |

---

## 🎯 EMPFEHLUNG

**Sofort starten mit:**
1. Package-Struktur in `platform/packages/prompt-framework/`
2. Core-Klassen implementieren
3. Expert Hub als Pilot migrieren

**Vorteile:**
- ✅ Einheitliche Prompt-Verwaltung über alle Apps
- ✅ SaaS-ready mit Multi-Tenancy
- ✅ Kostenoptimierung durch Tier-Auswahl
- ✅ A/B-Testing für kontinuierliche Verbesserung
- ✅ Zentrale Metriken und Monitoring

---

**Status:** Bereit für Review  
**Nächster Schritt:** Feedback einholen, dann Phase 1 starten
