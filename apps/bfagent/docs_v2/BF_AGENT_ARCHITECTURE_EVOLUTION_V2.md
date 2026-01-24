# 🚀 BF Agent Architecture Evolution
## Von Domain-Template zu Universal Domain-Action-Handler Framework

**Status:** Architektur-Vorschlag  
**Version:** 2.0  
**Datum:** 2025-11-05  
**Autor:** Architektur-Team

---

## 📋 Inhaltsverzeichnis

1. [Executive Summary](#1-executive-summary)
2. [Analyse der aktuellen Architektur](#2-analyse-der-aktuellen-architektur)
3. [Zielarchitektur](#3-zielarchitektur)
4. [Implementierungsplan](#4-implementierungsplan)
5. [Migration Strategy](#5-migration-strategy)
6. [Architektur-Entscheidungen](#6-architektur-entscheidungen)

---

## 1. Executive Summary

### 🎯 Vision

Transformation von BF Agent von einem buch-zentrierten System zu einem **Universal Domain Orchestration Framework** mit folgenden Kern-Capabilities:

```
Domain-Art → Domain-Typ → Phasen → Aktionen → Handler
                                              ↓
                                    LLM/Agent Integration
                                    Long-Running Tasks
                                    Event-Driven Processing
```

### 🔑 Kernkonzepte

**Hierarchische Struktur:**
```
DomainArt (z.B. "Content Creation")
  └─ DomainType (z.B. "Book", "Research Paper", "Forensic Report")
      └─ Phase (z.B. "Planning", "Execution", "Review")
          └─ Action (z.B. "Generate Outline", "Analyze Evidence")
              └─ Handler (z.B. "SaveTheCatHandler", "PhotoAnalysisHandler")
                  ↓
                  ├─ Traditional Handler (synchron)
                  ├─ LLM-Augmented Handler (LLM als Tool)
                  ├─ Agent Handler (Agent übernimmt)
                  └─ Long-Running Handler (async + callback)
```

### 📊 Key Benefits

| Feature | Vorher | Nachher |
|---------|--------|---------|
| **Flexibilität** | Buch-spezifisch | Multi-Domain |
| **LLM Integration** | Hart-codiert | Plugin-basiert |
| **Long-Running Tasks** | Blockierend | Event-basiert |
| **Wiederverwendung** | 40% | 85% |
| **Time-to-Market** | 4-6 Wochen | 1-2 Wochen |

---

## 2. Analyse der aktuellen Architektur

### ✅ Was funktioniert gut

1. **Handler-Framework**
   - Klare Input/Output Schemas (Pydantic)
   - Drei-Phasen-Pattern (Input → Processing → Output)
   - Transaction Safety mit Rollback
   - Handler Registry mit Metadaten

2. **Template-System**
   - DomainTemplate konzeptionell stark
   - PhaseTemplate / ActionTemplate modular
   - Custom Code Preservation funktioniert

3. **Consistency Framework**
   - AST-basierte Code-Analyse
   - Automated Code Generation
   - Backup & Rollback Mechanismen

### ⚠️ Verbesserungspotenzial

1. **Fehlende Abstraktion für Domain-Arten**
   - Aktuell: Direkt zu DomainType
   - Benötigt: DomainArt als übergeordnete Kategorie

2. **Keine native LLM/Agent Integration**
   - LLM-Calls sind in Handlern hart-codiert
   - Keine einheitliche Agent-Schnittstelle
   - Keine Tool-Use-Abstraktion

3. **Synchrone Ausführung limitiert**
   - Long-running tasks blockieren
   - Keine Event-basierte Kommunikation
   - Keine Progress-Updates

4. **Fehlende Callback-Mechanismen**
   - Kein Notification-System
   - Keine Workflow-Fortsetzung nach Async-Tasks

---

## 3. Zielarchitektur

### 🏗️ Architektur-Übersicht

```
┌────────────────────────────────────────────────────────────────┐
│                       BF Agent Core                            │
├────────────────────────────────────────────────────────────────┤
│  Domain Orchestration Layer                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │  DomainArt   │  │  DomainType  │  │    Phase     │        │
│  │              │  │              │  │              │        │
│  │ • Content    │  │ • Book       │  │ • Planning   │        │
│  │ • Science    │  │ • Paper      │  │ • Execution  │        │
│  │ • Forensics  │  │ • Report     │  │ • Review     │        │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘        │
│         │                 │                 │                │
│         └─────────────────┴─────────────────┘                │
│                           │                                   │
├───────────────────────────┼───────────────────────────────────┤
│  Action & Handler Layer   │                                   │
│  ┌─────────────────────────▼────────────────────────────┐    │
│  │              Action Templates                         │    │
│  │  • handler_type: classic | llm_augmented | agent |   │    │
│  │                  long_running                          │    │
│  │  • execution_mode: sync | async | event_driven       │    │
│  └───────────────────────┬───────────────────────────────┘    │
│                          │                                    │
│  ┌───────────────────────▼───────────────────────────────┐   │
│  │          Handler Execution Engine                      │   │
│  │                                                        │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐           │   │
│  │  │ Classic  │  │   LLM    │  │  Agent   │           │   │
│  │  │ Handler  │  │Augmented │  │ Handler  │           │   │
│  │  └──────────┘  └──────────┘  └──────────┘           │   │
│  │                                                        │   │
│  │  ┌────────────────────────────────────────┐          │   │
│  │  │   Long-Running Task Manager            │          │   │
│  │  │   • Celery Queue                       │          │   │
│  │  │   • Progress Tracking                  │          │   │
│  │  │   • Event Callbacks                    │          │   │
│  │  └────────────────────────────────────────┘          │   │
│  └────────────────────────────────────────────────────────┘   │
├────────────────────────────────────────────────────────────────┤
│  LLM & Agent Integration Layer                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │ LLM Provider │  │ Agent System │  │  Tool        │        │
│  │   Manager    │  │   Manager    │  │  Registry    │        │
│  │              │  │              │  │              │        │
│  │ • OpenAI     │  │ • ReAct      │  │ • Handler    │        │
│  │ • Anthropic  │  │ • LangGraph  │  │   as Tool    │        │
│  │ • Local LLM  │  │ • AutoGen    │  │ • External   │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
├────────────────────────────────────────────────────────────────┤
│  Event & Messaging Layer                                      │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Event Bus (Redis Streams / Kafka)                   │    │
│  │  • Task Started / Completed / Failed                  │    │
│  │  • Progress Updates                                   │    │
│  │  • Domain Events                                      │    │
│  └──────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────┘
```

### 📐 Datenmodell

#### Core Models

```python
# ==================== DOMAIN HIERARCHY ====================

class DomainArt(models.Model):
    """
    Top-level domain category
    
    Examples:
    - Content Creation
    - Scientific Research
    - Forensic Analysis
    - Medical Assessment
    """
    id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=200)
    description = models.TextField()
    icon = models.CharField(max_length=50)
    color = models.CharField(max_length=7)  # Hex color
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Domain Art"
        verbose_name_plural = "Domain Arts"


class DomainType(models.Model):
    """
    Specific domain within an art
    
    Examples:
    - Book, Blog Post (under Content Creation)
    - Research Paper, Meta-Analysis (under Scientific Research)
    - Explosion Report, Fire Analysis (under Forensic Analysis)
    """
    id = models.CharField(max_length=100, primary_key=True)
    domain_art = models.ForeignKey(
        DomainArt,
        on_delete=models.CASCADE,
        related_name='domain_types'
    )
    name = models.CharField(max_length=200)
    description = models.TextField()
    
    # Configuration
    config_schema = models.JSONField(default=dict)
    required_fields = models.JSONField(default=list)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Domain Type"
        verbose_name_plural = "Domain Types"
        unique_together = [['domain_art', 'id']]


class Phase(models.Model):
    """
    Workflow phase within a domain type
    
    Examples:
    - Planning, Research, Writing, Review (for Book)
    - Evidence Collection, Analysis, Report (for Forensics)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    domain_type = models.ForeignKey(
        DomainType,
        on_delete=models.CASCADE,
        related_name='phases'
    )
    name = models.CharField(max_length=200)
    description = models.TextField()
    order = models.IntegerField()
    
    # Visual
    icon = models.CharField(max_length=50)
    color = models.CharField(max_length=7)
    
    # Execution settings
    execution_mode = models.CharField(
        max_length=20,
        choices=[
            ('sequential', 'Sequential'),
            ('parallel', 'Parallel'),
            ('conditional', 'Conditional')
        ],
        default='sequential'
    )
    required = models.BooleanField(default=True)
    skippable = models.BooleanField(default=False)
    
    # Conditions for execution
    preconditions = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['order']
        unique_together = [['domain_type', 'order']]


class Action(models.Model):
    """
    Specific action within a phase
    
    Examples:
    - "Create Save the Cat Outline" (Planning phase)
    - "Analyze Photo Evidence" (Evidence Collection phase)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    phase = models.ForeignKey(
        Phase,
        on_delete=models.CASCADE,
        related_name='actions'
    )
    name = models.CharField(max_length=200)
    description = models.TextField()
    order = models.IntegerField()
    
    # Handler Configuration
    handler_type = models.CharField(
        max_length=20,
        choices=[
            ('classic', 'Classic Handler'),
            ('llm_augmented', 'LLM-Augmented Handler'),
            ('agent', 'Agent Handler'),
            ('long_running', 'Long-Running Handler')
        ],
        default='classic'
    )
    
    # Handler reference
    handler_class = models.CharField(max_length=500, blank=True)
    agent_config = models.JSONField(default=dict, blank=True)
    
    # Execution settings
    execution_mode = models.CharField(
        max_length=20,
        choices=[
            ('sync', 'Synchronous'),
            ('async', 'Asynchronous'),
            ('event_driven', 'Event-Driven')
        ],
        default='sync'
    )
    
    timeout_seconds = models.IntegerField(default=300)
    retry_count = models.IntegerField(default=0)
    continue_on_error = models.BooleanField(default=False)
    
    # Configuration
    config = models.JSONField(default=dict)
    required_fields = models.JSONField(default=list)
    
    # Dependencies
    dependencies = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='dependent_actions',
        blank=True
    )
    
    # Estimated metrics
    estimated_duration_seconds = models.IntegerField(null=True, blank=True)
    estimated_cost_cents = models.IntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['order']
        unique_together = [['phase', 'order']]


# ==================== WORKFLOW EXECUTION ====================

class WorkflowInstance(models.Model):
    """
    Instance of a workflow execution
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    domain_type = models.ForeignKey(DomainType, on_delete=models.CASCADE)
    
    # Context data
    context = models.JSONField()
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('running', 'Running'),
            ('paused', 'Paused'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
            ('cancelled', 'Cancelled')
        ],
        default='pending'
    )
    
    # Execution metadata
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Progress tracking
    current_phase = models.ForeignKey(
        Phase,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+'
    )
    current_action = models.ForeignKey(
        Action,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+'
    )
    
    progress_percent = models.IntegerField(default=0)
    
    # Results
    output = models.JSONField(default=dict)
    error_log = models.TextField(blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['domain_type', 'status']),
            models.Index(fields=['status', 'created_at'])
        ]


class PhaseExecution(models.Model):
    """
    Execution record for a phase
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    workflow_instance = models.ForeignKey(
        WorkflowInstance,
        on_delete=models.CASCADE,
        related_name='phase_executions'
    )
    phase = models.ForeignKey(Phase, on_delete=models.CASCADE)
    
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('running', 'Running'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
            ('skipped', 'Skipped')
        ],
        default='pending'
    )
    
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    output = models.JSONField(default=dict)
    error_message = models.TextField(blank=True)
    
    class Meta:
        ordering = ['started_at']


class ActionExecution(models.Model):
    """
    Execution record for an action
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    phase_execution = models.ForeignKey(
        PhaseExecution,
        on_delete=models.CASCADE,
        related_name='action_executions'
    )
    action = models.ForeignKey(Action, on_delete=models.CASCADE)
    
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('running', 'Running'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
            ('retrying', 'Retrying')
        ],
        default='pending'
    )
    
    # Execution details
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    retry_count = models.IntegerField(default=0)
    
    # Input/Output
    input_data = models.JSONField(default=dict)
    output = models.JSONField(default=dict)
    error_message = models.TextField(blank=True)
    
    # For async/long-running tasks
    task_id = models.CharField(max_length=255, blank=True)
    
    # Metrics
    duration_seconds = models.FloatField(null=True, blank=True)
    tokens_used = models.IntegerField(null=True, blank=True)
    cost_cents = models.IntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['started_at']


# ==================== LLM & AGENT INTEGRATION ====================

class LLMProvider(models.Model):
    """
    LLM Provider configuration
    """
    id = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=200)
    
    # API Configuration
    api_endpoint = models.URLField()
    api_key_env_var = models.CharField(max_length=100)
    
    # Models available
    models_config = models.JSONField(default=dict)
    
    # Rate limits
    requests_per_minute = models.IntegerField(null=True, blank=True)
    tokens_per_minute = models.IntegerField(null=True, blank=True)
    
    # Pricing (cents per 1000 tokens)
    input_cost_per_1k = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True
    )
    output_cost_per_1k = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True
    )
    
    is_active = models.BooleanField(default=True)


class AgentConfiguration(models.Model):
    """
    Agent configuration for agent-based actions
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=200)
    description = models.TextField()
    
    # Agent type
    agent_type = models.CharField(
        max_length=50,
        choices=[
            ('react', 'ReAct Agent'),
            ('langgraph', 'LangGraph Agent'),
            ('autogen', 'AutoGen Agent'),
            ('custom', 'Custom Agent')
        ]
    )
    
    # LLM Configuration
    llm_provider = models.ForeignKey(
        LLMProvider,
        on_delete=models.CASCADE
    )
    llm_model = models.CharField(max_length=100)
    temperature = models.FloatField(default=0.7)
    
    # System prompt
    system_prompt = models.TextField()
    
    # Tools available to agent
    available_tools = models.JSONField(default=list)
    
    # Constraints
    max_iterations = models.IntegerField(default=10)
    max_execution_time = models.IntegerField(default=300)
    
    is_active = models.BooleanField(default=True)


class ToolRegistry(models.Model):
    """
    Registry of tools available to agents
    """
    id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=200)
    description = models.TextField()
    
    # Tool type
    tool_type = models.CharField(
        max_length=20,
        choices=[
            ('handler', 'Handler as Tool'),
            ('function', 'Python Function'),
            ('api', 'External API'),
            ('database', 'Database Query')
        ]
    )
    
    # Configuration
    handler_class = models.CharField(max_length=500, blank=True)
    function_path = models.CharField(max_length=500, blank=True)
    
    # Schema for LLM
    tool_schema = models.JSONField()
    
    is_active = models.BooleanField(default=True)


# ==================== EVENT SYSTEM ====================

class WorkflowEvent(models.Model):
    """
    Events generated during workflow execution
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    workflow_instance = models.ForeignKey(
        WorkflowInstance,
        on_delete=models.CASCADE,
        related_name='events'
    )
    
    # Event details
    event_type = models.CharField(
        max_length=50,
        choices=[
            ('workflow_started', 'Workflow Started'),
            ('workflow_completed', 'Workflow Completed'),
            ('workflow_failed', 'Workflow Failed'),
            ('phase_started', 'Phase Started'),
            ('phase_completed', 'Phase Completed'),
            ('action_started', 'Action Started'),
            ('action_completed', 'Action Completed'),
            ('action_failed', 'Action Failed'),
            ('progress_update', 'Progress Update'),
            ('llm_call', 'LLM Call Made'),
            ('agent_iteration', 'Agent Iteration'),
            ('custom', 'Custom Event')
        ]
    )
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Event data
    payload = models.JSONField(default=dict)
    
    # References
    phase_execution = models.ForeignKey(
        PhaseExecution,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    action_execution = models.ForeignKey(
        ActionExecution,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['workflow_instance', 'event_type']),
            models.Index(fields=['timestamp'])
        ]


class EventCallback(models.Model):
    """
    Callbacks to be triggered on events
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=200)
    
    # Event filter
    event_types = models.JSONField(default=list)
    
    # Callback configuration
    callback_type = models.CharField(
        max_length=20,
        choices=[
            ('webhook', 'Webhook'),
            ('email', 'Email'),
            ('function', 'Python Function'),
            ('workflow', 'Trigger Workflow')
        ]
    )
    
    callback_config = models.JSONField(default=dict)
    
    is_active = models.BooleanField(default=True)
```

---

## 4. Implementierungsplan

### Phase 1: Foundation (Woche 1-2)

#### 1.1 Core Models erweitern

```python
# migrations/0001_add_domain_hierarchy.py

from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('myapp', '0042_existing_migration'),
    ]
    
    operations = [
        # Create DomainArt
        migrations.CreateModel(
            name='DomainArt',
            fields=[
                ('id', models.CharField(max_length=100, primary_key=True)),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField()),
                # ... weitere Felder
            ],
        ),
        
        # Create DomainType
        migrations.CreateModel(
            name='DomainType',
            fields=[
                ('id', models.CharField(max_length=100, primary_key=True)),
                ('domain_art', models.ForeignKey(...)),
                # ...
            ],
        ),
        
        # Migrate existing templates to new structure
        migrations.RunPython(migrate_existing_templates),
    ]
```

#### 1.2 Handler Type Enum erweitern

```python
# myapp/handlers/base.py

from enum import Enum

class HandlerType(Enum):
    """Type of handler execution"""
    CLASSIC = "classic"
    LLM_AUGMENTED = "llm_augmented"
    AGENT = "agent"
    LONG_RUNNING = "long_running"


class BaseHandler(ABC):
    """Base handler with type support"""
    
    HANDLER_TYPE: HandlerType = HandlerType.CLASSIC
    
    # Existing methods...
    
    @property
    def is_async(self) -> bool:
        """Check if handler runs asynchronously"""
        return self.HANDLER_TYPE in [
            HandlerType.LONG_RUNNING,
            HandlerType.AGENT  # Agents might be long-running
        ]
```

#### 1.3 LLM Provider Manager

```python
# myapp/llm/provider_manager.py

from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
import openai
import anthropic

class LLMProviderBase(ABC):
    """Base class for LLM providers"""
    
    @abstractmethod
    def generate(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate completion"""
        pass
    
    @abstractmethod
    def get_usage_metrics(self) -> Dict[str, int]:
        """Get token usage metrics"""
        pass


class OpenAIProvider(LLMProviderBase):
    """OpenAI provider implementation"""
    
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
        self._usage_cache = []
    
    def generate(
        self,
        prompt: str,
        model: str = "gpt-4-turbo",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        response = self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        # Track usage
        self._usage_cache.append({
            'prompt_tokens': response.usage.prompt_tokens,
            'completion_tokens': response.usage.completion_tokens,
            'total_tokens': response.usage.total_tokens,
        })
        
        return {
            'content': response.choices[0].message.content,
            'usage': {
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens,
            }
        }
    
    def get_usage_metrics(self) -> Dict[str, int]:
        if not self._usage_cache:
            return {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
        
        return {
            'prompt_tokens': sum(u['prompt_tokens'] for u in self._usage_cache),
            'completion_tokens': sum(u['completion_tokens'] for u in self._usage_cache),
            'total_tokens': sum(u['total_tokens'] for u in self._usage_cache),
        }


class AnthropicProvider(LLMProviderBase):
    """Anthropic Claude provider implementation"""
    
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self._usage_cache = []
    
    def generate(
        self,
        prompt: str,
        model: str = "claude-3-opus-20240229",
        temperature: float = 0.7,
        max_tokens: Optional[int] = 4096,
        **kwargs
    ) -> Dict[str, Any]:
        response = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )
        
        # Track usage
        self._usage_cache.append({
            'prompt_tokens': response.usage.input_tokens,
            'completion_tokens': response.usage.output_tokens,
            'total_tokens': response.usage.input_tokens + response.usage.output_tokens,
        })
        
        return {
            'content': response.content[0].text,
            'usage': {
                'prompt_tokens': response.usage.input_tokens,
                'completion_tokens': response.usage.output_tokens,
                'total_tokens': response.usage.input_tokens + response.usage.output_tokens,
            }
        }
    
    def get_usage_metrics(self) -> Dict[str, int]:
        if not self._usage_cache:
            return {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
        
        return {
            'prompt_tokens': sum(u['prompt_tokens'] for u in self._usage_cache),
            'completion_tokens': sum(u['completion_tokens'] for u in self._usage_cache),
            'total_tokens': sum(u['total_tokens'] for u in self._usage_cache),
        }


class LLMProviderManager:
    """Manages multiple LLM providers"""
    
    def __init__(self):
        self.providers: Dict[str, LLMProviderBase] = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize providers from database"""
        from myapp.models import LLMProvider
        
        for provider_config in LLMProvider.objects.filter(is_active=True):
            if provider_config.id == 'openai':
                api_key = os.getenv(provider_config.api_key_env_var)
                self.providers['openai'] = OpenAIProvider(api_key)
            
            elif provider_config.id == 'anthropic':
                api_key = os.getenv(provider_config.api_key_env_var)
                self.providers['anthropic'] = AnthropicProvider(api_key)
    
    def get_provider(self, provider_id: str) -> LLMProviderBase:
        """Get provider by ID"""
        if provider_id not in self.providers:
            raise ValueError(f"Provider {provider_id} not found")
        return self.providers[provider_id]
    
    def generate(
        self,
        provider_id: str,
        prompt: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate using specified provider"""
        provider = self.get_provider(provider_id)
        return provider.generate(prompt, **kwargs)


# Global instance
llm_manager = LLMProviderManager()
```

### Phase 2: Handler Extensions (Woche 3)

#### 2.1 LLM-Augmented Handler

```python
# myapp/handlers/llm_augmented.py

from typing import Dict, Any, Optional
from myapp.handlers.base import BaseHandler, HandlerType
from myapp.llm.provider_manager import llm_manager

class LLMAugmentedHandler(BaseHandler):
    """
    Handler that uses LLM as a tool
    
    Example: Handler orchestrates workflow but delegates
    specific tasks to LLM
    """
    
    HANDLER_TYPE = HandlerType.LLM_AUGMENTED
    
    # LLM Configuration
    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = "gpt-4-turbo"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: Optional[int] = None
    
    def call_llm(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Call LLM with specified prompt
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            **kwargs: Additional LLM parameters
        
        Returns:
            Generated text
        """
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        # Merge with class defaults
        llm_kwargs = {
            'model': self.LLM_MODEL,
            'temperature': self.LLM_TEMPERATURE,
            'max_tokens': self.LLM_MAX_TOKENS,
        }
        llm_kwargs.update(kwargs)
        
        result = llm_manager.generate(
            provider_id=self.LLM_PROVIDER,
            prompt=full_prompt,
            **llm_kwargs
        )
        
        # Track usage
        self._track_llm_usage(result['usage'])
        
        return result['content']
    
    def _track_llm_usage(self, usage: Dict[str, int]):
        """Track LLM usage for cost calculation"""
        # Store in ActionExecution if available
        if hasattr(self, '_action_execution'):
            self._action_execution.tokens_used = usage['total_tokens']
            # Calculate cost based on provider pricing
            # self._action_execution.cost_cents = ...
            self._action_execution.save()


# Example: SaveTheCat Handler with LLM
class SaveTheCatOutlineHandler(LLMAugmentedHandler):
    """Generate Save the Cat outline using LLM"""
    
    INPUT_SCHEMA = {
        'type': 'object',
        'properties': {
            'story_id': {'type': 'integer'},
            'genre': {'type': 'string'},
            'target_audience': {'type': 'string'},
            'logline': {'type': 'string', 'optional': True}
        },
        'required': ['story_id', 'genre', 'target_audience']
    }
    
    OUTPUT_SCHEMA = {
        'type': 'object',
        'properties': {
            'outline': {'type': 'object'},
            'beats': {'type': 'array'},
            'character_arcs': {'type': 'array'}
        }
    }
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate outline using LLM"""
        
        # 1. Fetch story context
        story = Story.objects.get(pk=input_data['story_id'])
        
        # 2. Build prompt
        system_prompt = """You are a professional story consultant specializing in 
        Save the Cat beat sheet methodology. Create structured outlines that follow 
        the 15-beat structure."""
        
        user_prompt = f"""
        Create a Save the Cat beat sheet for:
        
        Genre: {input_data['genre']}
        Target Audience: {input_data['target_audience']}
        Story Title: {story.title}
        Logline: {input_data.get('logline', 'TBD')}
        
        Provide a JSON response with:
        - outline: dict with all 15 beats
        - beats: array of beat objects with name, description, page_range
        - character_arcs: array of character development points
        """
        
        # 3. Call LLM
        response = self.call_llm(
            prompt=user_prompt,
            system_prompt=system_prompt,
            response_format={"type": "json_object"}  # OpenAI JSON mode
        )
        
        # 4. Parse and validate
        result = json.loads(response)
        
        # 5. Save to database
        story.outline = result['outline']
        story.save()
        
        return result
```

#### 2.2 Agent Handler

```python
# myapp/handlers/agent.py

from typing import Dict, Any, List, Optional
from myapp.handlers.base import BaseHandler, HandlerType
from myapp.llm.provider_manager import llm_manager
from myapp.tools.registry import tool_registry

class AgentHandler(BaseHandler):
    """
    Handler that delegates to an AI agent
    
    Agent uses ReAct pattern (Reasoning + Acting) with access to tools
    """
    
    HANDLER_TYPE = HandlerType.AGENT
    
    # Agent Configuration
    AGENT_CONFIG_ID: Optional[str] = None
    MAX_ITERATIONS: int = 10
    AVAILABLE_TOOLS: List[str] = []
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.agent_config = self._load_agent_config()
    
    def _load_agent_config(self):
        """Load agent configuration"""
        if self.AGENT_CONFIG_ID:
            from myapp.models import AgentConfiguration
            return AgentConfiguration.objects.get(pk=self.AGENT_CONFIG_ID)
        return None
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent workflow"""
        
        # 1. Initialize agent state
        agent_state = {
            'goal': self._formulate_goal(input_data),
            'observations': [],
            'actions': [],
            'iteration': 0,
            'completed': False,
            'result': None
        }
        
        # 2. Agent loop
        while not agent_state['completed'] and agent_state['iteration'] < self.MAX_ITERATIONS:
            # Reasoning step
            thought = self._agent_think(agent_state, input_data)
            
            # Acting step
            action_result = self._agent_act(thought, input_data)
            
            # Update state
            agent_state['observations'].append(action_result)
            agent_state['iteration'] += 1
            
            # Check if goal achieved
            if self._is_goal_achieved(agent_state):
                agent_state['completed'] = True
                agent_state['result'] = self._extract_result(agent_state)
        
        if not agent_state['completed']:
            raise Exception(f"Agent did not complete within {self.MAX_ITERATIONS} iterations")
        
        return agent_state['result']
    
    def _formulate_goal(self, input_data: Dict[str, Any]) -> str:
        """Formulate the agent's goal"""
        # Override in subclass
        return "Complete the task"
    
    def _agent_think(
        self,
        agent_state: Dict[str, Any],
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Agent reasoning step"""
        
        # Build context
        context = self._build_agent_context(agent_state, input_data)
        
        # Call LLM for reasoning
        prompt = f"""
        Goal: {agent_state['goal']}
        
        Previous observations:
        {self._format_observations(agent_state['observations'])}
        
        Available tools:
        {self._format_available_tools()}
        
        What should you do next? Think step by step:
        1. Analyze the situation
        2. Decide on next action
        3. Format as: ACTION: <tool_name> | INPUT: <input_json>
        """
        
        response = llm_manager.generate(
            provider_id=self.agent_config.llm_provider.id,
            prompt=prompt,
            model=self.agent_config.llm_model,
            temperature=self.agent_config.temperature
        )
        
        # Parse thought
        thought = self._parse_thought(response['content'])
        
        return thought
    
    def _agent_act(
        self,
        thought: Dict[str, Any],
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Agent action step"""
        
        action_name = thought['action']
        action_input = thought['input']
        
        # Execute tool
        tool = tool_registry.get_tool(action_name)
        result = tool.execute(action_input)
        
        return {
            'action': action_name,
            'input': action_input,
            'result': result
        }
    
    def _is_goal_achieved(self, agent_state: Dict[str, Any]) -> bool:
        """Check if goal is achieved"""
        # Simple heuristic or LLM-based check
        # Override in subclass for complex logic
        return False
    
    def _extract_result(self, agent_state: Dict[str, Any]) -> Dict[str, Any]:
        """Extract final result from agent state"""
        # Override in subclass
        return {'observations': agent_state['observations']}


# Example: Research Agent
class ResearchQuestionAgentHandler(AgentHandler):
    """
    Agent that formulates research questions using multiple tools
    """
    
    AGENT_CONFIG_ID = "research_question_agent"
    AVAILABLE_TOOLS = [
        'literature_search',
        'gap_analysis',
        'finer_framework_validator'
    ]
    
    def _formulate_goal(self, input_data: Dict[str, Any]) -> str:
        return f"""Formulate a high-quality research question for: 
        {input_data['research_topic']} in the field of {input_data['field_of_study']}"""
    
    def _is_goal_achieved(self, agent_state: Dict[str, Any]) -> bool:
        """Check if we have a validated research question"""
        # Check if FINER validation passed
        for obs in agent_state['observations']:
            if obs['action'] == 'finer_framework_validator':
                return obs['result'].get('valid', False)
        return False
    
    def _extract_result(self, agent_state: Dict[str, Any]) -> Dict[str, Any]:
        """Extract the validated research question"""
        for obs in reversed(agent_state['observations']):
            if obs['action'] == 'finer_framework_validator':
                return {
                    'research_question': obs['input']['question'],
                    'finer_scores': obs['result']['scores'],
                    'iterations': agent_state['iteration']
                }
        return {}
```

#### 2.3 Long-Running Handler

```python
# myapp/handlers/long_running.py

from typing import Dict, Any
from celery import shared_task
from myapp.handlers.base import BaseHandler, HandlerType
from myapp.events.publisher import event_publisher

class LongRunningHandler(BaseHandler):
    """
    Handler for long-running tasks
    
    Uses Celery for async execution with progress updates
    """
    
    HANDLER_TYPE = HandlerType.LONG_RUNNING
    
    def handle(
        self,
        input_data: Dict[str, Any],
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Override handle to dispatch to Celery
        
        Returns:
            Dict with task_id for tracking
        """
        # Validate input
        validated_input = self.validate_input(input_data)
        
        # Dispatch to Celery
        task = self._execute_async.delay(
            handler_class=self.__class__.__name__,
            input_data=validated_input,
            config=config,
            action_execution_id=getattr(self, '_action_execution_id', None)
        )
        
        return {
            'task_id': task.id,
            'status': 'dispatched',
            'message': 'Task dispatched to background worker'
        }
    
    @staticmethod
    @shared_task(bind=True)
    def _execute_async(
        self,
        handler_class: str,
        input_data: Dict[str, Any],
        config: Dict[str, Any],
        action_execution_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Celery task for async execution
        
        Args:
            self: Celery task instance (for progress updates)
            handler_class: Handler class name
            input_data: Validated input
            config: Handler configuration
            action_execution_id: ID of ActionExecution record
        """
        try:
            # Update status
            if action_execution_id:
                _update_action_status(action_execution_id, 'running')
            
            # Instantiate handler
            handler_cls = _get_handler_class(handler_class)
            handler = handler_cls()
            
            # Execute process method
            result = handler.process(input_data)
            
            # Validate output
            handler.validate_output(result)
            
            # Update status
            if action_execution_id:
                _update_action_status(action_execution_id, 'completed', output=result)
            
            # Publish completion event
            event_publisher.publish({
                'event_type': 'action_completed',
                'action_execution_id': action_execution_id,
                'result': result
            })
            
            return result
        
        except Exception as e:
            # Update status
            if action_execution_id:
                _update_action_status(
                    action_execution_id,
                    'failed',
                    error_message=str(e)
                )
            
            # Publish failure event
            event_publisher.publish({
                'event_type': 'action_failed',
                'action_execution_id': action_execution_id,
                'error': str(e)
            })
            
            raise
    
    def report_progress(self, percent: int, message: str = ''):
        """
        Report progress (called from within process method)
        
        Args:
            percent: Progress percentage (0-100)
            message: Optional progress message
        """
        # Update Celery task state
        if hasattr(self, 'celery_task'):
            self.celery_task.update_state(
                state='PROGRESS',
                meta={'percent': percent, 'message': message}
            )
        
        # Publish progress event
        event_publisher.publish({
            'event_type': 'progress_update',
            'action_execution_id': getattr(self, '_action_execution_id', None),
            'percent': percent,
            'message': message
        })


# Example: Video Analysis Handler
class VideoAnalysisHandler(LongRunningHandler):
    """
    Analyze video evidence (long-running)
    """
    
    INPUT_SCHEMA = {
        'type': 'object',
        'properties': {
            'video_url': {'type': 'string'},
            'analysis_type': {
                'type': 'string',
                'enum': ['object_detection', 'scene_analysis', 'full']
            }
        },
        'required': ['video_url', 'analysis_type']
    }
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process video analysis"""
        
        video_url = input_data['video_url']
        analysis_type = input_data['analysis_type']
        
        # 1. Download video
        self.report_progress(10, "Downloading video...")
        video_path = self._download_video(video_url)
        
        # 2. Extract frames
        self.report_progress(30, "Extracting frames...")
        frames = self._extract_frames(video_path)
        
        # 3. Analyze frames
        self.report_progress(50, "Analyzing frames...")
        results = []
        for i, frame in enumerate(frames):
            frame_result = self._analyze_frame(frame, analysis_type)
            results.append(frame_result)
            
            # Update progress
            progress = 50 + int((i / len(frames)) * 40)
            self.report_progress(progress, f"Analyzed frame {i+1}/{len(frames)}")
        
        # 4. Generate report
        self.report_progress(95, "Generating report...")
        report = self._generate_report(results)
        
        self.report_progress(100, "Complete!")
        
        return {
            'frames_analyzed': len(frames),
            'report': report,
            'video_path': video_path
        }
```

### Phase 3: Event System (Woche 4)

#### 3.1 Event Publisher

```python
# myapp/events/publisher.py

import redis
import json
from typing import Dict, Any
from django.conf import settings

class EventPublisher:
    """
    Publishes events to Redis Streams
    """
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True
        )
        self.stream_name = 'workflow:events'
    
    def publish(self, event: Dict[str, Any]):
        """
        Publish event to stream
        
        Args:
            event: Event data (must include 'event_type')
        """
        if 'event_type' not in event:
            raise ValueError("Event must include 'event_type'")
        
        # Add timestamp
        event['timestamp'] = timezone.now().isoformat()
        
        # Publish to Redis Stream
        message_id = self.redis_client.xadd(
            self.stream_name,
            {'data': json.dumps(event)}
        )
        
        # Also save to database
        self._save_to_db(event)
        
        return message_id
    
    def _save_to_db(self, event: Dict[str, Any]):
        """Save event to database"""
        from myapp.models import WorkflowEvent
        
        WorkflowEvent.objects.create(
            workflow_instance_id=event.get('workflow_instance_id'),
            event_type=event['event_type'],
            payload=event,
            phase_execution_id=event.get('phase_execution_id'),
            action_execution_id=event.get('action_execution_id')
        )


# Global instance
event_publisher = EventPublisher()
```

#### 3.2 Event Consumer

```python
# myapp/events/consumer.py

import redis
import json
from typing import Callable, Dict, Any
from django.conf import settings

class EventConsumer:
    """
    Consumes events from Redis Streams
    """
    
    def __init__(self, consumer_group: str, consumer_name: str):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True
        )
        self.stream_name = 'workflow:events'
        self.consumer_group = consumer_group
        self.consumer_name = consumer_name
        
        # Create consumer group if not exists
        try:
            self.redis_client.xgroup_create(
                self.stream_name,
                self.consumer_group,
                id='0',
                mkstream=True
            )
        except redis.ResponseError:
            pass  # Group already exists
    
    def consume(
        self,
        event_handler: Callable[[Dict[str, Any]], None],
        block_ms: int = 5000
    ):
        """
        Consume events from stream
        
        Args:
            event_handler: Function to handle events
            block_ms: Block for this many milliseconds
        """
        while True:
            # Read from stream
            messages = self.redis_client.xreadgroup(
                self.consumer_group,
                self.consumer_name,
                {self.stream_name: '>'},
                count=10,
                block=block_ms
            )
            
            for stream, message_list in messages:
                for message_id, message_data in message_list:
                    try:
                        # Parse event
                        event = json.loads(message_data['data'])
                        
                        # Handle event
                        event_handler(event)
                        
                        # Acknowledge message
                        self.redis_client.xack(
                            self.stream_name,
                            self.consumer_group,
                            message_id
                        )
                    
                    except Exception as e:
                        print(f"Error processing event: {e}")
                        # Could implement retry logic here


# Example usage
def handle_workflow_event(event: Dict[str, Any]):
    """Handle workflow events"""
    event_type = event['event_type']
    
    if event_type == 'action_completed':
        # Trigger callback
        trigger_callbacks(event)
    
    elif event_type == 'workflow_completed':
        # Send notification
        send_completion_notification(event)


# Start consumer
if __name__ == '__main__':
    consumer = EventConsumer(
        consumer_group='workflow_processor',
        consumer_name='worker_1'
    )
    consumer.consume(handle_workflow_event)
```

### Phase 4: Workflow Orchestrator (Woche 5-6)

#### 4.1 Enhanced Workflow Executor

```python
# myapp/workflows/executor.py

from typing import Dict, Any, Optional
from django.db import transaction
from myapp.models import (
    WorkflowInstance, PhaseExecution, ActionExecution,
    Action, Phase
)
from myapp.events.publisher import event_publisher
from myapp.handlers.base import HandlerType

class WorkflowExecutor:
    """
    Executes workflows with support for:
    - Sync/Async handlers
    - LLM/Agent handlers
    - Long-running tasks
    - Event-driven processing
    """
    
    def __init__(self, workflow_instance: WorkflowInstance):
        self.workflow = workflow_instance
        self.context = workflow_instance.context
    
    async def execute(self):
        """Execute entire workflow"""
        
        try:
            # Update status
            self.workflow.status = 'running'
            self.workflow.started_at = timezone.now()
            self.workflow.save()
            
            # Publish event
            event_publisher.publish({
                'event_type': 'workflow_started',
                'workflow_instance_id': str(self.workflow.id),
                'domain_type': self.workflow.domain_type.id
            })
            
            # Execute phases
            phases = self.workflow.domain_type.phases.all().order_by('order')
            
            for phase in phases:
                await self._execute_phase(phase)
            
            # Complete workflow
            self.workflow.status = 'completed'
            self.workflow.completed_at = timezone.now()
            self.workflow.save()
            
            event_publisher.publish({
                'event_type': 'workflow_completed',
                'workflow_instance_id': str(self.workflow.id)
            })
        
        except Exception as e:
            self.workflow.status = 'failed'
            self.workflow.error_log = str(e)
            self.workflow.save()
            
            event_publisher.publish({
                'event_type': 'workflow_failed',
                'workflow_instance_id': str(self.workflow.id),
                'error': str(e)
            })
            
            raise
    
    async def _execute_phase(self, phase: Phase):
        """Execute a single phase"""
        
        # Create phase execution record
        phase_exec = PhaseExecution.objects.create(
            workflow_instance=self.workflow,
            phase=phase,
            status='running',
            started_at=timezone.now()
        )
        
        try:
            event_publisher.publish({
                'event_type': 'phase_started',
                'workflow_instance_id': str(self.workflow.id),
                'phase_execution_id': str(phase_exec.id),
                'phase_name': phase.name
            })
            
            # Execute actions
            actions = phase.actions.all().order_by('order')
            
            if phase.execution_mode == 'sequential':
                for action in actions:
                    await self._execute_action(action, phase_exec)
            
            elif phase.execution_mode == 'parallel':
                # Execute all actions in parallel
                await asyncio.gather(*[
                    self._execute_action(action, phase_exec)
                    for action in actions
                ])
            
            # Complete phase
            phase_exec.status = 'completed'
            phase_exec.completed_at = timezone.now()
            phase_exec.save()
            
            event_publisher.publish({
                'event_type': 'phase_completed',
                'workflow_instance_id': str(self.workflow.id),
                'phase_execution_id': str(phase_exec.id)
            })
        
        except Exception as e:
            phase_exec.status = 'failed'
            phase_exec.error_message = str(e)
            phase_exec.save()
            raise
    
    async def _execute_action(
        self,
        action: Action,
        phase_exec: PhaseExecution
    ):
        """Execute a single action"""
        
        # Create action execution record
        action_exec = ActionExecution.objects.create(
            phase_execution=phase_exec,
            action=action,
            status='running',
            started_at=timezone.now(),
            input_data=self.context
        )
        
        try:
            event_publisher.publish({
                'event_type': 'action_started',
                'workflow_instance_id': str(self.workflow.id),
                'action_execution_id': str(action_exec.id),
                'action_name': action.name
            })
            
            # Get handler
            handler = self._get_handler(action)
            handler._action_execution_id = str(action_exec.id)
            
            # Execute based on handler type
            if action.execution_mode == 'sync':
                result = handler.handle(self.context, action.config)
            
            elif action.execution_mode == 'async':
                # For long-running handlers, we get task_id
                result = handler.handle(self.context, action.config)
                action_exec.task_id = result['task_id']
                action_exec.status = 'dispatched'
                action_exec.save()
                
                # Wait for completion (or return and handle via events)
                return  # Event will complete this action
            
            # Update context with result
            self.context.update(result)
            
            # Complete action
            action_exec.status = 'completed'
            action_exec.completed_at = timezone.now()
            action_exec.output = result
            action_exec.save()
            
            event_publisher.publish({
                'event_type': 'action_completed',
                'workflow_instance_id': str(self.workflow.id),
                'action_execution_id': str(action_exec.id)
            })
        
        except Exception as e:
            action_exec.status = 'failed'
            action_exec.error_message = str(e)
            action_exec.save()
            
            if not action.continue_on_error:
                raise
    
    def _get_handler(self, action: Action):
        """Get handler instance for action"""
        from myapp.handlers import get_handler_class
        
        handler_class = get_handler_class(action.handler_class)
        return handler_class()
```

---

## 5. Migration Strategy

### 5.1 Backward Compatibility

```python
# Ensure existing book workflows continue to work

def migrate_book_template_to_new_structure():
    """
    Migrate existing book template to new domain hierarchy
    """
    
    # 1. Create Domain Art
    content_creation = DomainArt.objects.create(
        id='content_creation',
        name='Content Creation',
        description='Domains for creating various types of content',
        icon='📝',
        color='#3B82F6'
    )
    
    # 2. Create Domain Type for books
    book_domain = DomainType.objects.create(
        id='book',
        domain_art=content_creation,
        name='Book Writing',
        description='Novel and book creation workflows',
        config_schema={},
        required_fields=['book_id', 'title', 'genre']
    )
    
    # 3. Migrate existing phases
    # ... (similar to current template structure)
    
    # 4. Migrate existing handlers to new registry
    from myapp.handlers import SaveTheCatOutlineHandler
    
    HandlerRegistry.objects.create(
        name='SaveTheCatOutlineHandler',
        class_path='myapp.handlers.SaveTheCatOutlineHandler',
        category='creative',
        domain='book',
        handler_type='llm_augmented',
        input_schema=SaveTheCatOutlineHandler.INPUT_SCHEMA,
        output_schema=SaveTheCatOutlineHandler.OUTPUT_SCHEMA,
        # ...
    )
```

### 5.2 Rollout Plan

**Week 1-2:**
- Deploy core models (DomainArt, DomainType, Phase, Action)
- Migrate existing book template
- Test backward compatibility

**Week 3-4:**
- Deploy LLM Provider Manager
- Deploy handler type extensions
- Migrate 2-3 handlers to new types

**Week 5-6:**
- Deploy Event System
- Deploy enhanced Workflow Executor
- Full integration testing

**Week 7-8:**
- Deploy to production
- Monitor performance
- Gather feedback

---

## 6. Architektur-Entscheidungen

### 6.1 Warum Redis Streams statt Kafka?

**Entscheidung:** Redis Streams für Event Messaging

**Rationale:**
- ✅ Einfachere Konfiguration und Betrieb
- ✅ Geringere Infrastruktur-Komplexität
- ✅ Ausreichend für bis zu 10K events/second
- ✅ Bereits Redis für Caching vorhanden
- ⚠️ Migration zu Kafka möglich wenn Skalierung nötig

### 6.2 Warum Celery für Long-Running Tasks?

**Entscheidung:** Celery mit Redis als Broker

**Rationale:**
- ✅ Ausgereiftes Django-Ökosystem
- ✅ Built-in Retry-Mechanismen
- ✅ Progress Tracking
- ✅ Scheduled Tasks Support
- ⚠️ Alternativen: Dramatiq, RQ

### 6.3 Warum Plugin-basierte LLM Integration?

**Entscheidung:** Provider-Manager Pattern

**Rationale:**
- ✅ Provider-Unabhängigkeit
- ✅ Einfacher Provider-Wechsel
- ✅ Cost-Tracking pro Provider
- ✅ Rate-Limiting Implementation
- ✅ Fallback-Strategien möglich

### 6.4 Warum getrennte Handler-Typen?

**Entscheidung:** Classic / LLM-Augmented / Agent / Long-Running

**Rationale:**
- ✅ Klare Trennung der Concerns
- ✅ Unterschiedliche Execution-Patterns
- ✅ Bessere Fehlerbehandlung
- ✅ Vereinfachtes Testing
- ✅ Performance-Optimierung pro Typ

---

## 7. Zusammenfassung & Nächste Schritte

### ✅ Was wir erreichen

1. **Universal Framework**
   - Beliebige Domain-Arts und Types
   - Wiederverwendbare Handler
   - Flexible Workflows

2. **LLM/Agent Integration**
   - Provider-unabhängig
   - Tool-Use Pattern
   - Agent-Orchestrierung

3. **Long-Running Support**
   - Async Execution
   - Progress Tracking
   - Event-basierte Callbacks

4. **Production-Ready**
   - Comprehensive Error Handling
   - Transaction Safety
   - Monitoring & Observability

### 🎯 Empfohlene Prioritäten

**High Priority (P0):**
1. Core Models erweitern (DomainArt, Phase, Action)
2. LLM Provider Manager
3. Handler Type Extensions

**Medium Priority (P1):**
4. Event System (Publisher/Consumer)
5. Long-Running Handler Support
6. Workflow Executor Updates

**Low Priority (P2):**
7. Agent Handler Framework
8. Tool Registry
9. Advanced Callbacks

### 📊 ROI-Schätzung

**Development Investment:**
- 6 Wochen Engineering Time
- ~€15K Development Cost

**Expected Benefits:**
- 60% Reduction in New Domain Setup Time
- 85% Code Reusability
- 40% Faster Feature Development
- Scalable to 50+ Domains

---

**Ende des Dokuments**
