# 🗄️ BF Agent - Database-First Architecture
## Zero-Hardcoding mit Database Storage

**Version:** 1.0  
**Datum:** 2025-11-05  
**Kritisch:** Database > Files

---

## 🎯 Das Problem mit der bisherigen Dokumentation

### ❌ Was bisher dokumentiert wurde:

```python
# templates.py - HARDCODED in Files ❌
BOOK_TEMPLATE = DomainTemplate(
    domain_id='books',
    phases=[
        PhaseTemplate(name='Planning', order=0),
        PhaseTemplate(name='Writing', order=1),
    ]
)
```

**Problem:** Änderungen erfordern Code-Deployment!

### ✅ Was tatsächlich sein sollte:

```python
# Database Models - DYNAMIC ✅
class DomainTemplate(models.Model):
    domain_id = models.CharField(max_length=100)
    display_name = models.CharField(max_length=200)
    # ... stored in DB, editable via UI!

class PhaseTemplate(models.Model):
    domain = models.ForeignKey(DomainTemplate)
    name = models.CharField(max_length=200)
    order = models.IntegerField()
    # ... editable via Django Admin!
```

**Vorteil:** Änderungen über UI, kein Deployment nötig! 🎉

---

## 📊 Zero-Hardcoding Philosophie

### Prinzip

```
┌────────────────────────────────────────────────────────┐
│  Alles was sich ändern kann:     → DATABASE           │
│  Alles was Code ist:              → FILES              │
│                                                         │
│  Konfiguration:                   → DATABASE ✅       │
│  Business Logic:                  → FILES (Handler)    │
│  Workflows:                       → DATABASE ✅       │
│  Templates:                       → DATABASE ✅       │
│  Handler-Code:                    → FILES              │
└────────────────────────────────────────────────────────┘
```

### Was gehört in die Database?

| Item | Storage | Reason |
|------|---------|--------|
| Domain Templates | **DATABASE** | Admin kann neue Domains hinzufügen |
| Phase Definitions | **DATABASE** | Reihenfolge anpassbar |
| Action Config | **DATABASE** | Parameter ändern ohne Deploy |
| Handler Registry | **DATABASE** | Welche Handler verfügbar sind |
| Feature Flags | **DATABASE** | Ein/Aus schalten über UI |
| Workflow Instances | **DATABASE** | Runtime State |
| User Context | **DATABASE** | Pro-User Daten |
| LLM Prompts | **DATABASE** | Prompt Engineering ohne Deploy |

### Was bleibt in Files?

| Item | Storage | Reason |
|------|---------|--------|
| Handler Code | **FILES** | Python Logic |
| Models.py | **FILES** | Database Schema |
| Views.py | **FILES** | HTTP Logic |
| Base Templates | **FILES** | HTML Structure |

---

## 🏗️ Korrigierte Architektur

### Database Models (Core)

```python
# apps_v2/core/workflows/models.py

from django.db import models
from django.contrib.auth import get_user_model
import json

User = get_user_model()


# ==================== TEMPLATE SYSTEM ====================

class DomainTemplate(models.Model):
    """
    Domain Template - Stored in DATABASE
    
    Defines workflow structure for a domain (books, science, etc.)
    Fully editable via Django Admin UI
    """
    domain_id = models.CharField(max_length=100, unique=True, db_index=True)
    display_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=10, default='📚')
    color = models.CharField(max_length=7, default='#3B82F6')
    
    # Configuration
    default_config = models.JSONField(default=dict)
    required_fields = models.JSONField(default=list)  # ['book_id', 'author']
    optional_fields = models.JSONField(default=list)
    
    # Output
    output_format = models.CharField(max_length=20, default='pdf')
    output_template_path = models.CharField(max_length=500, blank=True)
    
    # Metadata
    version = models.CharField(max_length=20, default='1.0')
    author = models.CharField(max_length=200, blank=True)
    tags = models.JSONField(default=list)
    category = models.CharField(max_length=100, default='general')
    
    # Capabilities
    supports_async = models.BooleanField(default=False)
    supports_resume = models.BooleanField(default=True)
    supports_branches = models.BooleanField(default=False)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_public = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        db_table = 'domain_templates'
        ordering = ['category', 'display_name']
        verbose_name = 'Domain Template'
        verbose_name_plural = 'Domain Templates'
    
    def __str__(self):
        return f"{self.icon} {self.display_name}"
    
    @property
    def estimated_duration(self):
        """Calculate total duration from all phases"""
        return sum(phase.estimated_duration_seconds for phase in self.phases.all())


class PhaseTemplate(models.Model):
    """
    Phase Template - Stored in DATABASE
    
    Defines a phase in a domain workflow
    """
    domain = models.ForeignKey(
        DomainTemplate,
        on_delete=models.CASCADE,
        related_name='phases'
    )
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    color = models.CharField(max_length=7, default='#3B82F6')
    icon = models.CharField(max_length=10, default='⚙️')
    
    # Execution
    execution_mode = models.CharField(
        max_length=20,
        choices=[
            ('sequential', 'Sequential'),
            ('parallel', 'Parallel'),
            ('conditional', 'Conditional'),
        ],
        default='sequential'
    )
    
    # Optional Phase
    required = models.BooleanField(default=True)
    
    # Timing
    estimated_duration_seconds = models.IntegerField(default=0)
    timeout_seconds = models.IntegerField(null=True, blank=True)
    
    # Dependencies
    depends_on = models.JSONField(default=list)  # ['phase_name1', 'phase_name2']
    
    class Meta:
        db_table = 'phase_templates'
        ordering = ['domain', 'order']
        unique_together = [['domain', 'order']]
    
    def __str__(self):
        return f"{self.domain.domain_id} - {self.name}"


class ActionTemplate(models.Model):
    """
    Action Template - Stored in DATABASE
    
    Defines an action (handler call) in a phase
    """
    phase = models.ForeignKey(
        PhaseTemplate,
        on_delete=models.CASCADE,
        related_name='actions'
    )
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    
    # Handler Configuration
    handler_class = models.CharField(max_length=500)  # 'apps_v2.domains.books.handlers.outline.SaveTheCatOutlineHandler'
    handler_type = models.CharField(
        max_length=20,
        choices=[
            ('classic', 'Classic'),
            ('llm_augmented', 'LLM Augmented'),
            ('agent', 'Agent'),
            ('long_running', 'Long Running'),
        ],
        default='classic'
    )
    
    # LLM Config (if handler_type = 'llm_augmented' or 'agent')
    llm_provider = models.CharField(max_length=50, blank=True)  # 'openai', 'anthropic'
    llm_model = models.CharField(max_length=100, blank=True)    # 'gpt-4-turbo'
    llm_temperature = models.FloatField(default=0.7)
    llm_max_tokens = models.IntegerField(default=2000)
    
    # Agent Config (if handler_type = 'agent')
    agent_config = models.CharField(max_length=200, blank=True)  # 'research_agent'
    tools = models.JSONField(default=list)  # ['web_search', 'calculator']
    max_iterations = models.IntegerField(default=10)
    
    # Handler Parameters
    config = models.JSONField(default=dict)  # Handler-specific config
    input_mapping = models.JSONField(default=dict)  # Map context -> handler input
    output_mapping = models.JSONField(default=dict)  # Map handler output -> context
    
    # Error Handling
    continue_on_error = models.BooleanField(default=False)
    retry_count = models.IntegerField(default=0)
    retry_delay_seconds = models.IntegerField(default=60)
    fallback_handler_class = models.CharField(max_length=500, blank=True)
    
    # Timing
    estimated_duration_seconds = models.IntegerField(default=0)
    timeout_seconds = models.IntegerField(null=True, blank=True)
    
    class Meta:
        db_table = 'action_templates'
        ordering = ['phase', 'order']
        unique_together = [['phase', 'order']]
    
    def __str__(self):
        return f"{self.phase.name} - {self.name}"


# ==================== HANDLER REGISTRY ====================

class HandlerRegistry(models.Model):
    """
    Handler Registry - Stored in DATABASE
    
    Catalog of all available handlers with metadata
    """
    name = models.CharField(max_length=200, unique=True)
    class_path = models.CharField(max_length=500)  # Full Python path
    
    category = models.CharField(
        max_length=100,
        choices=[
            ('planning', 'Planning'),
            ('content', 'Content Generation'),
            ('analysis', 'Analysis'),
            ('export', 'Export'),
            ('communication', 'Communication'),
        ]
    )
    domain = models.CharField(max_length=100, blank=True)  # 'books', 'shared', etc.
    
    description = models.TextField()
    
    # Schemas
    input_schema = models.JSONField(default=dict)   # JSON Schema
    output_schema = models.JSONField(default=dict)  # JSON Schema
    config_schema = models.JSONField(default=dict)  # JSON Schema
    
    # Metadata
    handler_type = models.CharField(max_length=20)
    version = models.CharField(max_length=20, default='1.0')
    author = models.CharField(max_length=200, blank=True)
    tags = models.JSONField(default=list)
    
    # Requirements
    dependencies = models.JSONField(default=list)  # ['numpy', 'openai']
    requires_llm = models.BooleanField(default=False)
    requires_tools = models.JSONField(default=list)
    
    # Analytics
    usage_count = models.IntegerField(default=0)
    success_rate = models.FloatField(default=1.0)
    avg_duration_seconds = models.FloatField(default=0)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('beta', 'Beta'),
            ('deprecated', 'Deprecated'),
        ],
        default='active'
    )
    
    is_public = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'handler_registry'
        ordering = ['category', 'name']
    
    def __str__(self):
        return self.name


# ==================== WORKFLOW INSTANCES ====================

class WorkflowInstance(models.Model):
    """
    Workflow Instance - Runtime State in DATABASE
    
    Represents a running workflow (e.g., "Book #42 being written")
    """
    template = models.ForeignKey(
        DomainTemplate,
        on_delete=models.CASCADE,
        related_name='instances'
    )
    
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('running', 'Running'),
            ('paused', 'Paused'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    
    # Context & Output
    context = models.JSONField(default=dict)  # Input context (book_id, author, etc.)
    output = models.JSONField(default=dict)   # Final output
    
    # User
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'workflow_instances'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.template.display_name} #{self.id} - {self.status}"


class PhaseInstance(models.Model):
    """Phase execution state"""
    workflow = models.ForeignKey(WorkflowInstance, on_delete=models.CASCADE, related_name='phases')
    template = models.ForeignKey(PhaseTemplate, on_delete=models.CASCADE)
    
    status = models.CharField(max_length=20, default='pending')
    
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'phase_instances'
        ordering = ['workflow', 'template__order']


class ActionInstance(models.Model):
    """Action execution state"""
    phase = models.ForeignKey(PhaseInstance, on_delete=models.CASCADE, related_name='actions')
    template = models.ForeignKey(ActionTemplate, on_delete=models.CASCADE)
    
    status = models.CharField(max_length=20, default='pending')
    
    # Input/Output
    input_data = models.JSONField(default=dict)
    output_data = models.JSONField(default=dict)
    error = models.TextField(blank=True)
    
    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)
    
    class Meta:
        db_table = 'action_instances'
        ordering = ['phase', 'template__order']


# ==================== FEATURE FLAGS ====================

class FeatureFlag(models.Model):
    """
    Feature Flags - Stored in DATABASE
    
    Enable/disable features without deployment
    """
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField()
    domain = models.CharField(max_length=100, blank=True)
    
    is_enabled = models.BooleanField(default=False)
    rollout_percentage = models.IntegerField(default=100)  # 0-100
    
    # Analytics
    usage_count = models.IntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        db_table = 'feature_flags'
        ordering = ['domain', 'name']
    
    def __str__(self):
        status = '✓' if self.is_enabled else '✗'
        return f"{status} {self.name}"


# ==================== LLM PROMPTS ====================

class LLMPromptTemplate(models.Model):
    """
    LLM Prompts - Stored in DATABASE
    
    Allows prompt engineering without code changes
    """
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField()
    
    handler_class = models.CharField(max_length=500)
    
    # Prompt
    system_prompt = models.TextField()
    user_prompt_template = models.TextField()
    
    # Config
    model = models.CharField(max_length=100, default='gpt-4-turbo')
    temperature = models.FloatField(default=0.7)
    max_tokens = models.IntegerField(default=2000)
    
    # Version
    version = models.CharField(max_length=20, default='1.0')
    is_active = models.BooleanField(default=True)
    
    # Analytics
    usage_count = models.IntegerField(default=0)
    success_rate = models.FloatField(default=1.0)
    avg_tokens_used = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'llm_prompt_templates'
        ordering = ['handler_class', 'name']
    
    def __str__(self):
        return f"{self.name} v{self.version}"
```

---

## 🎨 Django Admin UI

### Admin Configuration

```python
# apps_v2/core/workflows/admin.py

from django.contrib import admin
from .models import (
    DomainTemplate, PhaseTemplate, ActionTemplate,
    HandlerRegistry, WorkflowInstance, FeatureFlag,
    LLMPromptTemplate
)


@admin.register(DomainTemplate)
class DomainTemplateAdmin(admin.ModelAdmin):
    list_display = ['icon', 'display_name', 'domain_id', 'category', 'is_active', 'created_at']
    list_filter = ['category', 'is_active', 'is_public']
    search_fields = ['domain_id', 'display_name', 'description']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('domain_id', 'display_name', 'description', 'icon', 'color')
        }),
        ('Configuration', {
            'fields': ('default_config', 'required_fields', 'optional_fields')
        }),
        ('Output', {
            'fields': ('output_format', 'output_template_path')
        }),
        ('Metadata', {
            'fields': ('version', 'author', 'tags', 'category')
        }),
        ('Capabilities', {
            'fields': ('supports_async', 'supports_resume', 'supports_branches')
        }),
        ('Status', {
            'fields': ('is_active', 'is_public')
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'created_by']
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


class ActionTemplateInline(admin.TabularInline):
    model = ActionTemplate
    extra = 1
    fields = ['order', 'name', 'handler_class', 'handler_type', 'config']
    ordering = ['order']


@admin.register(PhaseTemplate)
class PhaseTemplateAdmin(admin.ModelAdmin):
    list_display = ['domain', 'order', 'icon', 'name', 'execution_mode', 'required']
    list_filter = ['domain', 'execution_mode', 'required']
    search_fields = ['name', 'description']
    
    inlines = [ActionTemplateInline]
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('domain', 'name', 'description', 'order', 'icon', 'color')
        }),
        ('Execution', {
            'fields': ('execution_mode', 'required')
        }),
        ('Timing', {
            'fields': ('estimated_duration_seconds', 'timeout_seconds')
        }),
        ('Dependencies', {
            'fields': ('depends_on',)
        }),
    )


@admin.register(HandlerRegistry)
class HandlerRegistryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'domain', 'handler_type', 'status', 'usage_count']
    list_filter = ['category', 'domain', 'handler_type', 'status']
    search_fields = ['name', 'class_path', 'description']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'class_path', 'category', 'domain', 'description')
        }),
        ('Schemas', {
            'fields': ('input_schema', 'output_schema', 'config_schema'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('handler_type', 'version', 'author', 'tags')
        }),
        ('Requirements', {
            'fields': ('dependencies', 'requires_llm', 'requires_tools')
        }),
        ('Analytics', {
            'fields': ('usage_count', 'success_rate', 'avg_duration_seconds'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('status', 'is_public')
        }),
    )
    
    readonly_fields = ['usage_count', 'success_rate', 'avg_duration_seconds']


@admin.register(WorkflowInstance)
class WorkflowInstanceAdmin(admin.ModelAdmin):
    list_display = ['id', 'template', 'status', 'created_by', 'created_at', 'duration']
    list_filter = ['status', 'template']
    search_fields = ['context']
    
    readonly_fields = ['created_at', 'updated_at', 'started_at', 'completed_at']
    
    def duration(self, obj):
        if obj.started_at and obj.completed_at:
            delta = obj.completed_at - obj.started_at
            return f"{delta.total_seconds():.0f}s"
        return "-"


@admin.register(FeatureFlag)
class FeatureFlagAdmin(admin.ModelAdmin):
    list_display = ['status_icon', 'name', 'domain', 'rollout_percentage', 'usage_count']
    list_filter = ['is_enabled', 'domain']
    search_fields = ['name', 'description']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'description', 'domain')
        }),
        ('Status', {
            'fields': ('is_enabled', 'rollout_percentage')
        }),
        ('Analytics', {
            'fields': ('usage_count', 'last_used_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['usage_count', 'last_used_at']
    
    def status_icon(self, obj):
        return '✅' if obj.is_enabled else '❌'
    status_icon.short_description = 'Status'


@admin.register(LLMPromptTemplate)
class LLMPromptTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'handler_class', 'version', 'is_active', 'success_rate']
    list_filter = ['is_active', 'model']
    search_fields = ['name', 'handler_class']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'description', 'handler_class')
        }),
        ('Prompt', {
            'fields': ('system_prompt', 'user_prompt_template')
        }),
        ('Config', {
            'fields': ('model', 'temperature', 'max_tokens')
        }),
        ('Version', {
            'fields': ('version', 'is_active')
        }),
        ('Analytics', {
            'fields': ('usage_count', 'success_rate', 'avg_tokens_used'),
            'classes': ('collapse',)
        }),
    )
```

---

## 🔄 Usage: Database-First Workflow

### 1. Admin erstellt Domain Template (via UI)

```
1. Login to Django Admin
2. Go to: Domain Templates → Add Domain Template
3. Fill form:
   - Domain ID: books
   - Display Name: Book Writing
   - Icon: 📚
   - Required Fields: ["book_id", "author"]
4. Save
5. Add Phases:
   - Planning (order=0)
   - Writing (order=1)
   - Review (order=2)
6. Add Actions to each Phase
7. Done! No code deployment needed! ✅
```

### 2. Code holt Template aus Database

```python
# apps_v2/core/workflows/executor.py

class WorkflowExecutor:
    def __init__(self, workflow_id: int):
        self.workflow = WorkflowInstance.objects.get(id=workflow_id)
        self.template = self.workflow.template  # From DATABASE!
    
    def execute(self):
        # Get phases from DATABASE
        for phase_template in self.template.phases.all().order_by('order'):
            phase_instance = PhaseInstance.objects.create(
                workflow=self.workflow,
                template=phase_template,
                status='running'
            )
            
            # Get actions from DATABASE
            for action_template in phase_template.actions.all().order_by('order'):
                self._execute_action(action_template, phase_instance)
    
    def _execute_action(self, action_template: ActionTemplate, phase: PhaseInstance):
        # Get handler class from DATABASE
        handler_class_path = action_template.handler_class
        handler_config = action_template.config  # From DATABASE!
        
        # Import handler dynamically
        Handler = self._import_handler(handler_class_path)
        handler = Handler()
        
        # Execute
        result = handler.handle(
            input_data=self._map_input(action_template),
            config=handler_config  # From DATABASE!
        )
        
        # Store result in DATABASE
        ActionInstance.objects.create(
            phase=phase,
            template=action_template,
            status='completed',
            input_data=self._map_input(action_template),
            output_data=result
        )
```

---

## 🎯 Vorteile: Database-First

### ✅ Zero Deployment für Änderungen

```
Admin ändert:
- Phase-Reihenfolge
- Handler-Parameter
- LLM Temperature
- Feature Flags

→ Sofort aktiv! Kein git commit, kein deployment! 🚀
```

### ✅ UI für Non-Developers

```
Content Manager kann:
- Neue Domain Templates erstellen
- Workflows anpassen
- Prompts optimieren
- Feature Flags togglen

→ Ohne Code-Kenntnisse! 💪
```

### ✅ A/B Testing

```python
# Easy A/B Testing via Database
template_v1 = DomainTemplate.objects.get(domain_id='books', version='1.0')
template_v2 = DomainTemplate.objects.get(domain_id='books', version='2.0')

if random.random() < 0.5:
    workflow = WorkflowInstance.objects.create(template=template_v1)
else:
    workflow = WorkflowInstance.objects.create(template=template_v2)
```

### ✅ Audit Trail

```
Alle Änderungen in Database:
- Wer hat wann was geändert?
- Welche Template-Version wurde benutzt?
- Performance pro Handler tracked

→ Full transparency! 📊
```

---

## 📋 Migration: Von Files zu Database

### Schritt 1: Models erstellen

```bash
# Create migrations
python manage.py makemigrations core
python manage.py migrate core
```

### Schritt 2: Import von bestehenden templates.py

```python
# management/commands/import_templates.py

from django.core.management.base import BaseCommand
from apps_v2.core.workflows.models import DomainTemplate, PhaseTemplate, ActionTemplate

class Command(BaseCommand):
    help = 'Import templates from templates.py to database'
    
    def handle(self, *args, **options):
        # Import old template
        from domains.books.templates import BOOK_TEMPLATE
        
        # Create in database
        domain = DomainTemplate.objects.create(
            domain_id=BOOK_TEMPLATE.domain_id,
            display_name=BOOK_TEMPLATE.display_name,
            # ... map all fields
        )
        
        for phase in BOOK_TEMPLATE.phases:
            phase_db = PhaseTemplate.objects.create(
                domain=domain,
                name=phase.name,
                # ... map all fields
            )
            
            for action in phase.actions:
                ActionTemplate.objects.create(
                    phase=phase_db,
                    name=action.name,
                    # ... map all fields
                )
        
        self.stdout.write(self.style.SUCCESS(f'✅ Imported {domain.display_name}'))
```

### Schritt 3: Code umstellen

```python
# OLD - Hardcoded ❌
from domains.books.templates import BOOK_TEMPLATE
workflow = create_workflow(BOOK_TEMPLATE)

# NEW - Database ✅
template = DomainTemplate.objects.get(domain_id='books', is_active=True)
workflow = WorkflowInstance.objects.create(template=template)
```

---

## ✅ Zusammenfassung

### Das Konzept IST berücksichtigt!

**Aber:** Die Dokumentation hatte zu starken Fokus auf Files!

### Korrigierte Architektur:

```
DATABASE (editable via UI):
- ✅ Domain Templates
- ✅ Phase Definitions
- ✅ Action Config
- ✅ Handler Registry
- ✅ Feature Flags
- ✅ LLM Prompts
- ✅ Workflow State

FILES (code only):
- Handler Implementation
- Models.py (Schema)
- Admin.py (UI Config)
```

### Next Steps:

1. **Erstelle Models** wie oben gezeigt
2. **Setup Django Admin** für UI-Management
3. **Import existing templates** zu Database
4. **Update Code** um aus DB zu lesen
5. **Deploy** und genieße Zero-Hardcoding! 🎉

**Database-First = Best Practice! ✅**
