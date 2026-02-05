# 📋 Prompt & Template Framework - Implementierungsplan

**Basierend auf:** PROMPT_TEMPLATE_FRAMEWORK_RFC.md  
**Datum:** 2026-01-28  
**Geschätzte Dauer:** 9 Arbeitstage

---

## 🎯 ÜBERSICHT

```
Phase 1 ──► Phase 2 ──► Phase 3 ──► Phase 4 ──► Phase 5 ──► Phase 6
Framework   Django      Expert      Writing     Travel      SaaS
Package     Integration Hub         Hub         Beat        Features
(2 Tage)    (1 Tag)     (1 Tag)     (1 Tag)     (0.5 Tag)   (2 Tage)
```

---

## 📦 PHASE 1: Framework Package (2 Tage)

### Tag 1: Core-Implementierung

#### 1.1 Package-Struktur erstellen
```bash
mkdir -p platform/packages/prompt-framework/prompt_framework/{core,storage,adapters}
touch platform/packages/prompt-framework/pyproject.toml
touch platform/packages/prompt-framework/README.md
```

#### 1.2 Datenmodelle (`core/models.py`)
```python
# Zu implementieren:
- PromptTemplate (dataclass)
- PromptComponent (dataclass)
- PromptExecution (dataclass)
- RenderedPrompt (dataclass)
- PromptResult (dataclass)
- ValidationResult (dataclass)
```

#### 1.3 Registry Protocol (`core/registry.py`)
```python
# Zu implementieren:
- PromptRegistry (Protocol)
- ComponentStore (Protocol)
```

#### 1.4 Template Engine (`core/engine.py`)
```python
# Zu implementieren:
- TemplateEngine
  - __init__(): Jinja2 Environment setup
  - render(): Template rendern
  - validate(): Syntax prüfen
  - extract_variables(): Variablen extrahieren
  - _include_component(): Komponenten einbinden
```

### Tag 2: Service & Storage

#### 2.1 PromptService (`core/service.py`)
```python
# Zu implementieren:
- PromptService
  - generate(): Vollständiger Workflow
  - render_only(): Nur rendern
  - get_template(): Template laden
  - _enrich_context(): Context anreichern
  - _track_execution(): Tracking
```

#### 2.2 Context Builder (`core/context.py`)
```python
# Zu implementieren:
- BaseContextBuilder
  - build(): Template-Method
  - _sanitize(): Gefährliche Keys entfernen
  - _add_defaults(): Standard-Werte
  - _enrich(): Override-Punkt
```

#### 2.3 In-Memory Storage (`storage/dict_registry.py`)
```python
# Zu implementieren:
- DictPromptRegistry
- DictComponentStore
```

#### 2.4 Unit Tests
```python
# Tests für:
- TemplateEngine.render()
- TemplateEngine.validate()
- PromptService.generate()
- DictPromptRegistry CRUD
```

#### 2.5 pyproject.toml
```toml
[project]
name = "prompt-framework"
version = "0.1.0"
dependencies = [
    "jinja2>=3.1.0",
    "pydantic>=2.0.0",
]

[project.optional-dependencies]
django = ["django>=4.2"]
```

### Deliverables Phase 1
- [ ] `prompt_framework/core/models.py`
- [ ] `prompt_framework/core/registry.py`
- [ ] `prompt_framework/core/engine.py`
- [ ] `prompt_framework/core/service.py`
- [ ] `prompt_framework/core/context.py`
- [ ] `prompt_framework/storage/dict_registry.py`
- [ ] `tests/test_engine.py`
- [ ] `tests/test_service.py`
- [ ] `pyproject.toml`
- [ ] `README.md`

---

## 🗄️ PHASE 2: Django Integration (1 Tag)

### 2.1 Django Models (`bfagent/apps/core/models_prompt.py`)
```python
class PromptTemplate(models.Model):
    code = models.CharField(max_length=100, unique=True)
    app = models.CharField(max_length=50)
    category = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    system_prompt = models.TextField(blank=True)
    user_prompt = models.TextField()
    output_format = models.TextField(blank=True)
    
    variables = models.JSONField(default=dict)
    default_values = models.JSONField(default=dict)
    
    preferred_tier = models.CharField(max_length=20, default='standard')
    preferred_model = models.CharField(max_length=100, blank=True)
    max_tokens = models.IntegerField(default=2000)
    temperature = models.FloatField(default=0.7)
    
    version = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    tenant_id = models.UUIDField(null=True, blank=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'prompt_templates'
        unique_together = ['code', 'tenant_id', 'version']
        indexes = [
            models.Index(fields=['app', 'category']),
            models.Index(fields=['tenant_id', 'is_active']),
        ]


class PromptComponent(models.Model):
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    content = models.TextField()
    category = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'prompt_components'


class PromptExecution(models.Model):
    template = models.ForeignKey(PromptTemplate, on_delete=models.SET_NULL, null=True)
    template_version = models.IntegerField()
    
    context_hash = models.CharField(max_length=64)
    rendered_prompt = models.TextField()
    
    llm_model = models.CharField(max_length=100)
    llm_tier = models.CharField(max_length=20)
    tokens_in = models.IntegerField(default=0)
    tokens_out = models.IntegerField(default=0)
    cost = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    latency_ms = models.IntegerField(default=0)
    
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    user_rating = models.IntegerField(null=True, blank=True)
    
    tenant_id = models.UUIDField(null=True, blank=True)
    user_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'prompt_executions'
        indexes = [
            models.Index(fields=['template', 'created_at']),
            models.Index(fields=['tenant_id', 'created_at']),
        ]
```

### 2.2 Django Adapter (`prompt_framework/adapters/django.py`)
```python
# Zu implementieren:
- DjangoPromptRegistry(PromptRegistry)
  - get(): Mit Tenant-Fallback
  - list_by_app()
  - list_by_category()
  - save()
  - create_tenant_override()

- DjangoComponentStore(ComponentStore)
  - get()
  - list_all()
```

### 2.3 Admin Interface
```python
@admin.register(PromptTemplate)
class PromptTemplateAdmin(admin.ModelAdmin):
    list_display = ['code', 'app', 'category', 'version', 'is_active']
    list_filter = ['app', 'category', 'is_active']
    search_fields = ['code', 'name', 'description']
    readonly_fields = ['created_at', 'updated_at']
```

### 2.4 Migration erstellen
```bash
python manage.py makemigrations core --name add_prompt_framework
python manage.py migrate
```

### Deliverables Phase 2
- [ ] `apps/core/models_prompt.py`
- [ ] `prompt_framework/adapters/django.py`
- [ ] `apps/core/admin_prompt.py`
- [ ] Migration `0001_add_prompt_framework.py`
- [ ] Tests für Django-Adapter

---

## 🔬 PHASE 3: Expert Hub Migration (1 Tag)

### 3.1 Templates in DB migrieren
```python
# Migration: 0002_migrate_expert_hub_prompts.py

EXPERT_HUB_TEMPLATES = [
    {
        'code': 'expert_hub.phase_1',
        'app': 'expert_hub',
        'category': 'phase',
        'name': 'Phase 1: Betriebsbereich, Anlage',
        'system_prompt': '''Du bist ein Explosionsschutz-Experte...''',
        'user_prompt': '''Erstelle eine strukturierte Beschreibung für:
**Projekt:** {{ project_name }}
**Standort:** {{ project_location }}
{{ existing_section }}
**Verfügbare Dokumente:**
{{ document_list }}
...''',
        'output_format': '''## 1 Betriebsbereich, Anlage
### 1.1 Anlagenbeschreibung
...''',
        'variables': {
            'project_name': {'type': 'string', 'required': True},
            'project_location': {'type': 'string', 'required': False},
            'existing_section': {'type': 'string', 'required': False},
            'document_list': {'type': 'string', 'required': False},
        },
        'preferred_tier': 'standard',
        'max_tokens': 2500,
        'temperature': 0.7,
    },
    # ... weitere Phasen 2-8
]

def migrate_expert_hub_prompts(apps, schema_editor):
    PromptTemplate = apps.get_model('core', 'PromptTemplate')
    for template_data in EXPERT_HUB_TEMPLATES:
        PromptTemplate.objects.create(**template_data)
```

### 3.2 ExpertHubContextBuilder implementieren
```python
# apps/expert_hub/context_builders.py

class ExpertHubContextBuilder(BaseContextBuilder):
    def _enrich(self, context: Dict) -> Dict:
        context = super()._enrich(context)
        
        # Existing content section formatieren
        if context.get('existing_content'):
            context['existing_section'] = f'''**Bisherige Eingaben:**
```
{context['existing_content']}
```'''
        else:
            context['existing_section'] = '*Noch keine Eingaben vorhanden.*'
        
        # Dokumente formatieren
        if context.get('documents'):
            context['document_list'] = '\n'.join([
                f"- **{d.filename}** ({d.document_type})"
                for d in context['documents']
            ])
        else:
            context['document_list'] = '- Keine Dokumente zugeordnet'
        
        # Related data
        context['related_stoffdaten'] = context.get('related_data', {}).get(
            'stoffdaten', '[Noch nicht erfasst]'
        )
        
        return context
```

### 3.3 Views umstellen
```python
# apps/expert_hub/views.py

# Vorher:
from apps.expert_hub.prompts import generate_phase_content

# Nachher:
from prompt_framework import PromptService
from apps.core.prompt_adapters import get_prompt_service
from apps.expert_hub.context_builders import ExpertHubContextBuilder

async def generate_content_view(request, phase_id):
    service = get_prompt_service(request.tenant)
    context_builder = ExpertHubContextBuilder()
    
    context = context_builder.build({
        'project_name': session.project_name,
        'project_location': session.project_location,
        'existing_content': phase_status.content,
        'documents': documents,
    })
    
    result = await service.generate(
        f'expert_hub.phase_{phase.number}',
        context
    )
    
    return JsonResponse({
        'content': result.content,
        'usage': result.usage,
    })
```

### 3.4 Fallback beibehalten
```python
# Temporär: Alte Implementierung als Fallback
try:
    result = await service.generate(...)
except TemplateNotFoundError:
    # Fallback auf alte Implementierung
    content, hints = generate_phase_content(session, phase, phase_status, documents)
```

### Deliverables Phase 3
- [ ] Migration `0002_migrate_expert_hub_prompts.py`
- [ ] `apps/expert_hub/context_builders.py`
- [ ] Views auf PromptService umgestellt
- [ ] Fallback-Mechanismus
- [ ] Tests für Expert Hub Integration

---

## ✍️ PHASE 4: Writing Hub Migration (1 Tag)

### 4.1 Bestehende PromptFactory ersetzen
```python
# apps/bfagent/services/prompt_factory.py wird deprecated

# Neue Implementierung nutzt prompt_framework
from prompt_framework import PromptService
from apps.core.prompt_adapters import get_prompt_service

# Wrapper für Rückwärtskompatibilität
def build_prompt(template_code: str, context: Dict, **kwargs) -> Dict[str, str]:
    """Legacy-Wrapper für PromptFactory."""
    service = get_prompt_service()
    rendered = service.render_only(template_code, context)
    return {
        'system': rendered.system_prompt,
        'user': rendered.user_prompt,
        'full': rendered.full_prompt,
    }
```

### 4.2 Writing Hub Templates migrieren
```python
# Templates für:
- 'writing_hub.premise_generator'
- 'writing_hub.character_generator'
- 'writing_hub.plot_generator'
- 'writing_hub.chapter_generator'
- 'writing_hub.scene_generator'
# etc.
```

### 4.3 Image Prompt System integrieren
```python
# Das bestehende models_prompt_system.py bleibt für Image-Prompts
# Aber nutzt PromptService für Text-Generierung

class PromptMasterStyle(models.Model):
    # ... bestehende Felder ...
    
    def get_full_style_prompt(self) -> str:
        """Nutzt PromptService für erweiterte Funktionalität."""
        if self.master_prompt:
            return self.master_prompt
        
        # Optional: PromptService für dynamische Generierung
        service = get_prompt_service()
        result = service.render_only('writing_hub.style_prompt', {
            'preset': self.preset,
            'style_base': self.style_base_prompt,
            'cultural_context': self.cultural_context,
        })
        return result.full_prompt
```

### Deliverables Phase 4
- [ ] Migration `0003_migrate_writing_hub_prompts.py`
- [ ] `apps/writing_hub/context_builders.py`
- [ ] Legacy-Wrapper für PromptFactory
- [ ] Image Prompt System Integration
- [ ] Tests

---

## ✈️ PHASE 5: Travel Beat Migration (0.5 Tage)

### 5.1 Templates migrieren
```python
# Templates für:
- 'travel_beat.story_outline'
- 'travel_beat.chapter_generation'
- 'travel_beat.location_research'
```

### 5.2 TravelBeatContextBuilder
```python
# apps/stories/context_builders.py

class TravelBeatContextBuilder(BaseContextBuilder):
    GENRE_PROMPTS = {...}  # Aus prompts.py übernehmen
    SPICE_LEVELS = {...}
    STORY_BEATS = {...}
    
    def _enrich(self, context: Dict) -> Dict:
        context = super()._enrich(context)
        
        if 'genre' in context:
            context['genre_guide'] = self.GENRE_PROMPTS.get(context['genre'], '')
        if 'spice_level' in context:
            context['spice_guide'] = self.SPICE_LEVELS.get(context['spice_level'], '')
        if 'story_beat' in context:
            context['beat_guide'] = self.STORY_BEATS.get(context['story_beat'], '')
        
        return context
```

### Deliverables Phase 5
- [ ] Migration für Travel Beat Templates
- [ ] `apps/stories/context_builders.py`
- [ ] PromptBuilder deprecated
- [ ] Tests

---

## 🏢 PHASE 6: SaaS Features (2 Tage)

### Tag 1: Multi-Tenancy

#### 6.1 Tenant-Aware Service
```python
# apps/core/prompt_adapters.py

def get_prompt_service(tenant: Optional[Tenant] = None) -> PromptService:
    """Factory für Tenant-spezifischen PromptService."""
    registry = DjangoPromptRegistry()
    
    if tenant:
        llm_registry = TenantLLMRegistry(tenant)
        tracker = TenantUsageTracker(tenant)
        tenant_id = tenant.id
    else:
        llm_registry = DictRegistry.from_env()
        tracker = InMemoryTracker()
        tenant_id = None
    
    return PromptService(
        registry=registry,
        llm_client=DynamicLLMClient(llm_registry),
        tracker=tracker,
        tenant_id=tenant_id,
    )
```

#### 6.2 Tenant Override API
```python
# apps/core/views_prompt.py

class PromptTemplateOverrideView(TenantMixin, APIView):
    def post(self, request, template_code):
        """Erstellt Tenant-spezifische Template-Variante."""
        service = get_prompt_service(request.tenant)
        
        override = service.registry.create_tenant_override(
            base_code=template_code,
            tenant_id=request.tenant.id,
            overrides=request.data,
        )
        
        return Response(PromptTemplateSerializer(override).data)
```

### Tag 2: A/B Testing & Analytics

#### 6.3 A/B Testing
```python
# prompt_framework/core/ab_testing.py

class ABTestingService:
    def __init__(self, registry: PromptRegistry):
        self.registry = registry
    
    def get_variant(
        self,
        template_code: str,
        user_id: UUID,
    ) -> PromptTemplate:
        """Konsistente Varianten-Zuweisung pro User."""
        variants = self.registry.get_variants(template_code)
        if len(variants) <= 1:
            return variants[0] if variants else None
        
        variant_index = hash(f"{template_code}:{user_id}") % len(variants)
        return variants[variant_index]
    
    def get_stats(self, template_code: str) -> Dict:
        """A/B Test Statistiken."""
        variants = self.registry.get_variants(template_code)
        stats = {}
        
        for variant in variants:
            executions = PromptExecution.objects.filter(
                template=variant,
                created_at__gte=timezone.now() - timedelta(days=7)
            )
            stats[variant.version] = {
                'count': executions.count(),
                'success_rate': executions.filter(success=True).count() / max(executions.count(), 1),
                'avg_rating': executions.exclude(user_rating=None).aggregate(Avg('user_rating'))['user_rating__avg'],
                'avg_cost': executions.aggregate(Avg('cost'))['cost__avg'],
            }
        
        return stats
```

#### 6.4 Analytics Dashboard API
```python
# apps/core/views_prompt_analytics.py

class PromptAnalyticsView(APIView):
    def get(self, request):
        """Dashboard-Daten für Prompt-Analytics."""
        tenant_id = getattr(request, 'tenant_id', None)
        
        executions = PromptExecution.objects.filter(
            tenant_id=tenant_id,
            created_at__gte=timezone.now() - timedelta(days=30)
        )
        
        return Response({
            'total_executions': executions.count(),
            'success_rate': executions.filter(success=True).count() / max(executions.count(), 1),
            'total_cost': executions.aggregate(Sum('cost'))['cost__sum'] or 0,
            'avg_latency_ms': executions.aggregate(Avg('latency_ms'))['latency_ms__avg'] or 0,
            'by_template': self._group_by_template(executions),
            'by_tier': self._group_by_tier(executions),
        })
```

### Deliverables Phase 6
- [ ] Tenant-Aware PromptService
- [ ] Tenant Override API
- [ ] A/B Testing Service
- [ ] Analytics Dashboard API
- [ ] Admin-Erweiterungen für Tenants
- [ ] Tests

---

## ✅ ABNAHMEKRITERIEN

### Phase 1
- [ ] `prompt-framework` Package installierbar
- [ ] TemplateEngine rendert Jinja2 korrekt
- [ ] PromptService funktioniert mit DictRegistry
- [ ] Unit Tests > 80% Coverage

### Phase 2
- [ ] Django Models migriert
- [ ] Admin-Interface funktional
- [ ] DjangoPromptRegistry funktioniert
- [ ] Cache-Hit-Rate messbar

### Phase 3
- [ ] Alle 8 Expert Hub Phasen in DB
- [ ] KI-Generierung funktioniert wie vorher
- [ ] Fallback auf alte Implementierung möglich
- [ ] Keine Regression in bestehender Funktionalität

### Phase 4
- [ ] Writing Hub Templates in DB
- [ ] PromptFactory-Wrapper funktioniert
- [ ] Bestehende Handler unverändert nutzbar

### Phase 5
- [ ] Travel Beat Templates in DB
- [ ] Story-Generierung funktioniert

### Phase 6
- [ ] Tenant-spezifische Overrides möglich
- [ ] A/B Testing funktional
- [ ] Analytics-Daten verfügbar

---

## 🚀 QUICK START

Nach Abschluss aller Phasen:

```python
# 1. Service holen
from apps.core.prompt_adapters import get_prompt_service
service = get_prompt_service(request.tenant)

# 2. Context bauen
from apps.expert_hub.context_builders import ExpertHubContextBuilder
context = ExpertHubContextBuilder().build({
    'project_name': 'Mein Projekt',
    'documents': documents,
})

# 3. Generieren
result = await service.generate('expert_hub.phase_5', context)

# 4. Ergebnis nutzen
print(result.content)
print(f"Kosten: ${result.usage.cost:.4f}")
```

---

## 📊 RISIKEN & MITIGATIONEN

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Breaking Changes in bestehenden Apps | Mittel | Hoch | Fallback-Mechanismen, Legacy-Wrapper |
| Performance-Regression | Niedrig | Mittel | Caching, Benchmarks vor/nach |
| Komplexität für Entwickler | Mittel | Mittel | Gute Dokumentation, Beispiele |
| Migration dauert länger | Mittel | Niedrig | Phasenweise Rollout, Prioritäten |

---

**Nächster Schritt:** Phase 1 starten - Package-Struktur erstellen
