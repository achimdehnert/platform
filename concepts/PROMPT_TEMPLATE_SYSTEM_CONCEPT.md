# Konzeptpapier: Generisches Prompt-Template-System für Platform

**Version:** 1.0  
**Datum:** 27. Januar 2026  
**Autor:** Platform Architecture Team  
**Status:** Draft - Review erforderlich

---

## 1. Executive Summary

Dieses Dokument beschreibt ein **generisches, framework-agnostisches Prompt-Template-System** für die Platform (`creative-services`). Das System ermöglicht die zentrale Verwaltung, Versionierung und Ausführung von KI-Prompts für alle Platform-Anwendungen (BFAgent, Travel-Beat, CAD Hub, Research Hub).

### Kernziele

1. **Wiederverwendbarkeit**: Ein System für alle Apps
2. **Framework-Agnostik**: Keine Django-Abhängigkeit im Core
3. **Flexibilität**: Verschiedene Storage-Backends (Memory, File, Database)
4. **Composability**: Template-Vererbung, Partials, Chains
5. **Observability**: Execution Tracking, Metriken, A/B Testing

---

## 2. Problemstellung

### 2.1 Ist-Zustand: BFAgent PromptTemplate

Das bestehende System in BFAgent (`apps/bfagent/models_main.py:3157-3509`) hat folgende Einschränkungen:

| Problem | Beschreibung |
|---------|--------------|
| **Django-Kopplung** | Hardcoded ForeignKeys zu `Llms`, `Agents`, `BookProjects` |
| **Domain-Spezifisch** | Categories nur für Writing: `character`, `chapter`, `world`... |
| **Nicht portabel** | Kann nicht in Travel-Beat oder anderen Apps verwendet werden |
| **Monolithisch** | 40+ Felder in einem Model, schwer erweiterbar |

### 2.2 Anforderungen für Platform

| Anforderung | Priorität |
|-------------|-----------|
| Framework-agnostisch (Pydantic-basiert) | 🔴 Kritisch |
| Mehrere Storage-Backends | 🔴 Kritisch |
| Tier-basierte LLM-Auswahl (statt FK) | 🔴 Kritisch |
| Template-Versionierung | 🟡 Hoch |
| Execution Tracking | 🟡 Hoch |
| A/B Testing Support | 🟢 Mittel |
| AgentSkills.io Kompatibilität | 🟢 Mittel |

---

## 3. Architektur-Übersicht

```
platform/packages/creative-services/
├── creative_services/
│   ├── core/                      # ✅ Existiert
│   │   ├── llm_client.py          # Multi-Provider LLM Client
│   │   ├── llm_registry.py        # Tier-basierte LLM Registry
│   │   └── usage_tracker.py       # Token & Cost Tracking
│   │
│   ├── prompts/                   # 🆕 NEU - Prompt System
│   │   ├── __init__.py            # Public API
│   │   ├── schemas.py             # Pydantic Models
│   │   ├── template.py            # PromptTemplate Core
│   │   ├── registry.py            # Template Storage Backends
│   │   ├── renderer.py            # Jinja2 Rendering Engine
│   │   ├── executor.py            # Template Execution
│   │   ├── chains.py              # Multi-Step Prompt Chains
│   │   └── testing.py             # Template Testing Utilities
│   │
│   └── adapters/
│       ├── django_adapter.py      # ✅ Existiert (LLM)
│       └── django_prompts.py      # 🆕 NEU (Prompts)
```

### 3.1 Komponenten-Diagramm

```
┌─────────────────────────────────────────────────────────────────┐
│                        Applications                              │
├─────────────┬─────────────┬─────────────┬─────────────┬─────────┤
│  BFAgent    │ Travel-Beat │  CAD Hub    │ Research Hub│  ...    │
└──────┬──────┴──────┬──────┴──────┬──────┴──────┬──────┴─────────┘
       │             │             │             │
       ▼             ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    creative-services/prompts                     │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  Executor   │──│  Renderer   │──│  Registry   │              │
│  └──────┬──────┘  └─────────────┘  └──────┬──────┘              │
│         │                                  │                     │
│         ▼                                  ▼                     │
│  ┌─────────────┐              ┌────────────────────────┐        │
│  │ LLM Client  │              │   Storage Backends     │        │
│  │ (Tier-based)│              ├────────────────────────┤        │
│  └─────────────┘              │ • DictRegistry (Memory)│        │
│                               │ • FileRegistry (YAML)  │        │
│                               │ • DjangoRegistry (ORM) │        │
│                               └────────────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Datenmodell

### 4.1 Core Schemas (Pydantic)

#### 4.1.1 PromptVariable

```python
class PromptVariable(BaseModel):
    """Definition einer Template-Variable"""
    
    name: str                           # Variable name: "character_name"
    description: str = ""               # Human-readable description
    required: bool = True               # Is this variable required?
    default: Optional[Any] = None       # Default value if not provided
    type: str = "string"                # Type hint: string, int, float, list, dict
    validation: Optional[str] = None    # Regex pattern or JSON Schema reference
    
    # Examples for documentation
    examples: list[str] = Field(default_factory=list)
```

#### 4.1.2 LLMParameters

```python
class LLMParameters(BaseModel):
    """LLM-Konfiguration für ein Template (ohne hardcoded LLM-ID)"""
    
    # Generation Parameters
    max_tokens: int = 1000
    temperature: float = 0.7
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    
    # Tier-basierte Auswahl (NICHT FK zu LLM!)
    preferred_tier: Optional[str] = None      # "economy", "standard", "premium", "local"
    preferred_provider: Optional[str] = None  # "openai", "anthropic", "groq", "ollama"
    
    # Fallback-Strategie
    fallback_tier: Optional[str] = None       # Fallback wenn preferred nicht verfügbar
    allow_downgrade: bool = True              # Automatisch niedrigeren Tier nutzen?
```

#### 4.1.3 PromptTemplate (Hauptmodell)

```python
class PromptTemplate(BaseModel):
    """
    Generisches, framework-agnostisches Prompt Template.
    
    Kann in jeder App verwendet werden:
    - BFAgent (Writing)
    - Travel-Beat (Travel Content)
    - CAD Hub (Technical Documentation)
    - Research Hub (Academic Research)
    """
    
    # ══════════════════════════════════════════════════════════════
    # IDENTITY
    # ══════════════════════════════════════════════════════════════
    id: Optional[str] = None                  # UUID oder DB-ID
    key: str = Field(
        ..., 
        description="Unique key: 'writing.character.backstory.v1'",
        pattern=r'^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$'
    )
    name: str = Field(..., description="Human-readable name")
    version: str = "1.0"
    
    # ══════════════════════════════════════════════════════════════
    # TAXONOMY (flexibel, nicht hardcoded)
    # ══════════════════════════════════════════════════════════════
    domain: str = Field(
        default="general", 
        description="Domain: writing, travel, cad, research, general"
    )
    tags: list[str] = Field(
        default_factory=list, 
        description="Flexible tags for filtering: ['character', 'fantasy', 'german']"
    )
    
    # ══════════════════════════════════════════════════════════════
    # PROMPT CONTENT
    # ══════════════════════════════════════════════════════════════
    system_prompt: str = Field(
        ..., 
        description="System message defining AI role and constraints"
    )
    user_prompt: str = Field(
        ..., 
        description="User prompt with {{variable}} Jinja2 placeholders"
    )
    
    # ══════════════════════════════════════════════════════════════
    # VARIABLES
    # ══════════════════════════════════════════════════════════════
    variables: list[PromptVariable] = Field(default_factory=list)
    
    # ══════════════════════════════════════════════════════════════
    # OUTPUT SPECIFICATION
    # ══════════════════════════════════════════════════════════════
    output_format: OutputFormat = OutputFormat.TEXT  # text, json, markdown, structured
    output_schema: Optional[dict] = None             # JSON Schema for validation
    output_parser: Optional[str] = None              # Custom parser class path
    
    # ══════════════════════════════════════════════════════════════
    # LLM PARAMETERS
    # ══════════════════════════════════════════════════════════════
    llm_params: LLMParameters = Field(default_factory=LLMParameters)
    
    # ══════════════════════════════════════════════════════════════
    # COMPOSITION (Template-Vererbung & Partials)
    # ══════════════════════════════════════════════════════════════
    parent_key: Optional[str] = None              # Inherit from parent template
    partials: dict[str, str] = Field(             # Reusable prompt blocks
        default_factory=dict,
        description="Named partials: {'character_intro': '...', 'world_context': '...'}"
    )
    
    # ══════════════════════════════════════════════════════════════
    # METADATA
    # ══════════════════════════════════════════════════════════════
    description: str = ""
    author: str = ""
    license: str = "Proprietary"
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # ══════════════════════════════════════════════════════════════
    # A/B TESTING
    # ══════════════════════════════════════════════════════════════
    ab_test_group: Optional[str] = None           # "A", "B", "C", or None
    ab_test_weight: float = 1.0                   # Selection weight (0.0-1.0)
    
    # ══════════════════════════════════════════════════════════════
    # AGENTSKILLS.IO KOMPATIBILITÄT (Optional)
    # ══════════════════════════════════════════════════════════════
    skill_description: Optional[str] = None       # Short description for auto-matching
    allowed_tools: list[str] = Field(default_factory=list)  # Pre-approved tools
    references: dict[str, str] = Field(default_factory=dict)  # Reference documents
    
    # ══════════════════════════════════════════════════════════════
    # HELPER METHODS
    # ══════════════════════════════════════════════════════════════
    def get_required_variables(self) -> list[str]:
        """Get names of required variables"""
        return [v.name for v in self.variables if v.required]
    
    def get_variable_defaults(self) -> dict[str, Any]:
        """Get default values for optional variables"""
        return {v.name: v.default for v in self.variables if v.default is not None}
    
    def validate_variables(self, provided: dict[str, Any]) -> list[str]:
        """Return list of missing required variables"""
        required = self.get_required_variables()
        return [v for v in required if v not in provided]
```

#### 4.1.4 PromptExecution (Tracking)

```python
class PromptExecution(BaseModel):
    """Record of a template execution for tracking and analytics"""
    
    # ══════════════════════════════════════════════════════════════
    # IDENTITY
    # ══════════════════════════════════════════════════════════════
    id: Optional[str] = None
    template_key: str
    template_version: str
    
    # ══════════════════════════════════════════════════════════════
    # INPUT/OUTPUT
    # ══════════════════════════════════════════════════════════════
    rendered_prompt: str                          # Final prompt after rendering
    variables_used: dict[str, Any]                # Variables that were provided
    response_content: str                         # Raw LLM response
    parsed_output: Optional[Any] = None           # Parsed/validated output
    
    # ══════════════════════════════════════════════════════════════
    # EXECUTION METRICS
    # ══════════════════════════════════════════════════════════════
    success: bool
    error_message: Optional[str] = None
    error_type: Optional[str] = None              # "validation", "llm_error", "timeout"
    execution_time_ms: int
    
    # ══════════════════════════════════════════════════════════════
    # LLM METRICS
    # ══════════════════════════════════════════════════════════════
    llm_provider: str = ""                        # "openai", "anthropic", etc.
    llm_model: str = ""                           # "gpt-4", "claude-3-sonnet", etc.
    llm_tier: str = ""                            # "economy", "standard", "premium"
    tokens_input: int = 0
    tokens_output: int = 0
    cost: float = 0.0
    
    # ══════════════════════════════════════════════════════════════
    # QUALITY METRICS (Optional)
    # ══════════════════════════════════════════════════════════════
    confidence_score: Optional[float] = None      # Model confidence (if available)
    user_rating: Optional[int] = None             # 1-5 stars
    user_feedback: Optional[str] = None           # Free-text feedback
    user_accepted: Optional[bool] = None          # Did user accept the output?
    user_edited: bool = False                     # Did user edit the output?
    
    # ══════════════════════════════════════════════════════════════
    # CONTEXT
    # ══════════════════════════════════════════════════════════════
    app_name: str = ""                            # "bfagent", "travel-beat", etc.
    user_id: Optional[str] = None                 # User identifier
    session_id: Optional[str] = None              # Session/request identifier
    
    # ══════════════════════════════════════════════════════════════
    # RETRY INFORMATION
    # ══════════════════════════════════════════════════════════════
    retry_count: int = 0
    retry_of: Optional[str] = None                # ID of original execution
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

---

## 5. Storage Backends

### 5.1 Registry Protocol

```python
class TemplateRegistry(Protocol):
    """Protocol for template storage backends"""
    
    def get(self, key: str, version: str = "latest") -> Optional[PromptTemplate]:
        """Get template by key and version"""
        ...
    
    def list(
        self, 
        domain: str = None, 
        tags: list[str] = None,
        is_active: bool = True
    ) -> list[PromptTemplate]:
        """List templates with optional filters"""
        ...
    
    def save(self, template: PromptTemplate) -> PromptTemplate:
        """Save or update template"""
        ...
    
    def delete(self, key: str, version: str = None) -> bool:
        """Delete template(s)"""
        ...
    
    def get_versions(self, key: str) -> list[str]:
        """Get all versions of a template"""
        ...
```

### 5.2 Implementierungen

| Backend | Use Case | Persistenz | Performance |
|---------|----------|------------|-------------|
| `DictTemplateRegistry` | Tests, Prototyping | ❌ Memory | ⚡ Schnell |
| `FileTemplateRegistry` | Versionskontrolle, GitOps | ✅ YAML/JSON | 🔄 Mittel |
| `DjangoTemplateRegistry` | Production, Admin UI | ✅ PostgreSQL | 🔄 Mittel |

#### 5.2.1 DictTemplateRegistry (In-Memory)

```python
class DictTemplateRegistry:
    """In-memory registry for testing and prototyping"""
    
    def __init__(self):
        self._templates: dict[str, dict[str, PromptTemplate]] = {}
    
    @classmethod
    def from_yaml(cls, path: str) -> "DictTemplateRegistry":
        """Load templates from YAML file"""
        ...
    
    @classmethod
    def from_dict(cls, data: dict) -> "DictTemplateRegistry":
        """Load templates from dictionary"""
        ...
```

#### 5.2.2 FileTemplateRegistry (YAML/JSON)

```python
class FileTemplateRegistry:
    """
    File-based registry with one file per template.
    
    Directory Structure:
        prompts/
        ├── writing/
        │   ├── character/
        │   │   ├── backstory.yaml
        │   │   └── dialogue.yaml
        │   └── chapter/
        │       └── generation.yaml
        └── travel/
            └── destination/
                └── description.yaml
    """
    
    def __init__(self, base_path: str, format: str = "yaml"):
        self.base_path = Path(base_path)
        self.format = format  # "yaml" or "json"
```

#### 5.2.3 DjangoTemplateRegistry (ORM)

```python
class DjangoTemplateRegistry:
    """
    Django ORM-backed registry.
    
    Allows Django apps to use database-backed template storage
    while keeping the core system framework-agnostic.
    
    Usage:
        from creative_services.adapters.django_prompts import DjangoTemplateRegistry
        from myapp.models import PromptTemplateModel
        
        registry = DjangoTemplateRegistry(PromptTemplateModel)
        template = registry.get("writing.character.backstory")
    """
    
    def __init__(
        self, 
        model_class: Any,                    # Django Model
        execution_model_class: Any = None,   # Optional: Execution tracking model
        field_mapping: dict = None           # Custom field name mapping
    ):
        ...
```

---

## 6. Template Execution

### 6.1 PromptExecutor

```python
class PromptExecutor:
    """
    Execute prompt templates with LLM calls.
    
    Features:
    - Variable validation
    - Jinja2 rendering with partials
    - Tier-based LLM selection
    - Output validation (JSON Schema)
    - Execution tracking
    - Retry with fallback
    """
    
    def __init__(
        self,
        llm_client: DynamicLLMClient,
        template_registry: TemplateRegistry,
        execution_tracker: Optional[ExecutionTracker] = None,
    ):
        self.llm_client = llm_client
        self.registry = template_registry
        self.tracker = execution_tracker
    
    async def execute(
        self,
        template_key: str,
        variables: dict[str, Any],
        version: str = "latest",
        app_name: str = "",
        user_id: str = None,
        **llm_overrides,
    ) -> PromptExecution:
        """
        Execute a template and return execution record.
        
        Args:
            template_key: Template identifier (e.g., "writing.character.backstory")
            variables: Variables to render into the template
            version: Template version ("latest", "1.0", "2.0-beta")
            app_name: Calling application name for tracking
            user_id: User identifier for tracking
            **llm_overrides: Override LLM parameters (temperature, max_tokens, tier)
        
        Returns:
            PromptExecution with results and metrics
        
        Example:
            result = await executor.execute(
                template_key="writing.character.backstory",
                variables={
                    "character_name": "Elena",
                    "genre": "fantasy",
                    "world_setting": "Medieval kingdom"
                },
                app_name="bfagent",
                tier="premium"  # Override default tier
            )
            
            if result.success:
                print(result.response_content)
            else:
                print(f"Error: {result.error_message}")
        """
        ...
```

### 6.2 Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     execute(template_key, variables)             │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ 1. GET TEMPLATE                                                  │
│    template = registry.get(key, version)                         │
│    if not template: return Error("Template not found")           │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. RESOLVE INHERITANCE                                           │
│    if template.parent_key:                                       │
│        parent = registry.get(template.parent_key)                │
│        template = merge(parent, template)                        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. VALIDATE VARIABLES                                            │
│    missing = template.validate_variables(variables)              │
│    if missing: return Error(f"Missing: {missing}")               │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. MERGE WITH DEFAULTS                                           │
│    final_vars = {**template.get_variable_defaults(), **variables}│
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. RENDER PROMPTS (Jinja2)                                       │
│    rendered_system = render(template.system_prompt, final_vars)  │
│    rendered_user = render(template.user_prompt, final_vars)      │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. SELECT LLM (Tier-based)                                       │
│    tier = overrides.get("tier") or template.llm_params.tier      │
│    llm = llm_client.get_for_tier(tier)                           │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. EXECUTE LLM CALL                                              │
│    response = await llm_client.generate(                         │
│        prompt=rendered_user,                                     │
│        system_prompt=rendered_system,                            │
│        tier=tier,                                                │
│        **llm_params                                              │
│    )                                                             │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ 8. VALIDATE OUTPUT (if schema defined)                           │
│    if template.output_schema:                                    │
│        parsed = validate_json_schema(response, schema)           │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ 9. TRACK EXECUTION                                               │
│    execution = PromptExecution(...)                              │
│    if tracker: await tracker.track(execution)                    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│ 10. RETURN RESULT                                                │
│     return execution                                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. Template-Vererbung & Partials

### 7.1 Template-Vererbung

```yaml
# Base Template: writing.character.base
key: writing.character.base
name: Character Base Template
domain: writing
system_prompt: |
  Du bist ein erfahrener Autor, der Charaktere für {{genre}}-Geschichten entwickelt.
  Schreibe auf Deutsch und achte auf Konsistenz mit der Welt.
user_prompt: |
  Erstelle einen Charakter mit folgenden Eigenschaften:
  - Name: {{character_name}}
  - Rolle: {{character_role}}
  
  {{additional_instructions}}
variables:
  - name: genre
    required: true
  - name: character_name
    required: true
  - name: character_role
    required: true
  - name: additional_instructions
    required: false
    default: ""
llm_params:
  preferred_tier: standard
  max_tokens: 1000

---

# Child Template: writing.character.backstory (erbt von base)
key: writing.character.backstory
name: Character Backstory Generator
parent_key: writing.character.base  # ← Vererbung
user_prompt: |
  {{super()}}  # ← Parent-Prompt einbinden
  
  Fokussiere dich besonders auf:
  - Kindheit und Herkunft
  - Prägende Ereignisse
  - Motivation und Ziele
  
  Backstory-Länge: {{backstory_length}} Wörter
variables:
  - name: backstory_length
    required: false
    default: 500
llm_params:
  max_tokens: 2000  # ← Override
```

### 7.2 Partials (Wiederverwendbare Blöcke)

```yaml
key: writing.chapter.generation
name: Chapter Generator
partials:
  character_context: |
    Hauptcharaktere in diesem Kapitel:
    {% for char in characters %}
    - {{char.name}}: {{char.role}} - {{char.current_state}}
    {% endfor %}
  
  world_rules: |
    Weltregeln die beachtet werden müssen:
    {% for rule in world_rules %}
    - {{rule}}
    {% endfor %}
  
  style_guide: |
    Schreibstil: {{style}}
    Perspektive: {{perspective}}
    Tempo: {{pacing}}

user_prompt: |
  Schreibe Kapitel {{chapter_number}}: "{{chapter_title}}"
  
  {{partial:character_context}}
  
  {{partial:world_rules}}
  
  {{partial:style_guide}}
  
  Kapitelinhalt:
  {{chapter_outline}}
```

---

## 8. Prompt Chains (Multi-Step)

### 8.1 Chain Definition

```python
class PromptChain(BaseModel):
    """Multi-step prompt execution with context propagation"""
    
    key: str
    name: str
    description: str = ""
    
    steps: list[ChainStep]
    
    # Context that flows through all steps
    initial_context: dict[str, Any] = Field(default_factory=dict)
    
    # Error handling
    on_step_error: str = "stop"  # "stop", "skip", "retry"
    max_retries: int = 2


class ChainStep(BaseModel):
    """Single step in a prompt chain"""
    
    name: str
    template_key: str
    
    # Input mapping: chain context → template variables
    input_mapping: dict[str, str] = Field(default_factory=dict)
    
    # Output mapping: template output → chain context
    output_mapping: dict[str, str] = Field(default_factory=dict)
    
    # Conditional execution
    condition: Optional[str] = None  # Jinja2 expression
    
    # Step-specific overrides
    llm_overrides: dict[str, Any] = Field(default_factory=dict)
```

### 8.2 Chain Example: Character Creation Pipeline

```yaml
key: writing.character.full_creation
name: Complete Character Creation Pipeline
description: Creates a fully developed character in 4 steps

steps:
  - name: basic_profile
    template_key: writing.character.basic
    input_mapping:
      character_name: character_name
      genre: genre
    output_mapping:
      basic_profile: parsed_output
  
  - name: backstory
    template_key: writing.character.backstory
    input_mapping:
      character_name: character_name
      genre: genre
      basic_profile: basic_profile
    output_mapping:
      backstory: parsed_output
  
  - name: relationships
    template_key: writing.character.relationships
    condition: "{{ include_relationships | default(true) }}"
    input_mapping:
      character_name: character_name
      backstory: backstory
      other_characters: other_characters
    output_mapping:
      relationships: parsed_output
  
  - name: final_synthesis
    template_key: writing.character.synthesis
    input_mapping:
      character_name: character_name
      basic_profile: basic_profile
      backstory: backstory
      relationships: relationships
    output_mapping:
      final_character: parsed_output

initial_context:
  include_relationships: true
```

---

## 9. Django Integration

### 9.1 Django Model (Empfohlen)

```python
# apps/core/models/prompt_template.py

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class PromptTemplateModel(models.Model):
    """
    Django Model für Prompt Templates.
    
    Kompatibel mit creative-services DjangoTemplateRegistry.
    """
    
    # Identity
    key = models.CharField(max_length=200, db_index=True)
    name = models.CharField(max_length=200)
    version = models.CharField(max_length=20, default="1.0")
    
    # Taxonomy
    domain = models.CharField(max_length=50, default="general", db_index=True)
    tags = models.JSONField(default=list, blank=True)
    
    # Content
    system_prompt = models.TextField()
    user_prompt = models.TextField()
    
    # Variables
    variables = models.JSONField(default=list, blank=True)
    
    # Output
    output_format = models.CharField(max_length=20, default="text")
    output_schema = models.JSONField(default=dict, blank=True)
    
    # LLM Parameters
    max_tokens = models.IntegerField(default=1000)
    temperature = models.FloatField(default=0.7)
    top_p = models.FloatField(default=1.0)
    preferred_tier = models.CharField(max_length=20, blank=True, null=True)
    preferred_provider = models.CharField(max_length=50, blank=True, null=True)
    
    # Composition
    parent_key = models.CharField(max_length=200, blank=True, null=True)
    partials = models.JSONField(default=dict, blank=True)
    
    # Metadata
    description = models.TextField(blank=True)
    author = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    
    # A/B Testing
    ab_test_group = models.CharField(max_length=10, blank=True, null=True)
    ab_test_weight = models.FloatField(default=1.0)
    
    # Tracking
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="created_templates"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "platform_prompt_templates"
        unique_together = [("key", "version")]
        ordering = ["-is_active", "domain", "key"]
        indexes = [
            models.Index(fields=["key", "is_active"]),
            models.Index(fields=["domain", "is_active"]),
        ]
    
    def __str__(self):
        return f"{self.name} (v{self.version})"
```

### 9.2 BFAgent Migration

```python
# apps/core/prompt_adapters.py

from creative_services.adapters.django_prompts import DjangoTemplateRegistry
from creative_services.prompts import PromptExecutor
from creative_services.core import DynamicLLMClient

# Option 1: Bestehende BFAgent PromptTemplate nutzen
from apps.bfagent.models import PromptTemplate as BFAgentPromptTemplate

bfagent_registry = DjangoTemplateRegistry(
    model_class=BFAgentPromptTemplate,
    field_mapping={
        "key": "template_key",           # BFAgent uses template_key
        "user_prompt": "user_prompt_template",  # BFAgent uses user_prompt_template
    }
)

# Option 2: Neue Platform PromptTemplateModel nutzen
from apps.core.models import PromptTemplateModel

platform_registry = DjangoTemplateRegistry(
    model_class=PromptTemplateModel
)

# Executor mit Registry
executor = PromptExecutor(
    llm_client=DynamicLLMClient.from_env(),
    template_registry=platform_registry
)
```

---

## 10. API Design

### 10.1 Public API (creative_services.prompts)

```python
# creative_services/prompts/__init__.py

from .schemas import (
    PromptTemplate,
    PromptVariable,
    PromptExecution,
    LLMParameters,
    OutputFormat,
)

from .registry import (
    TemplateRegistry,
    DictTemplateRegistry,
    FileTemplateRegistry,
)

from .executor import PromptExecutor

from .chains import (
    PromptChain,
    ChainStep,
    ChainExecutor,
)

__all__ = [
    # Schemas
    "PromptTemplate",
    "PromptVariable",
    "PromptExecution",
    "LLMParameters",
    "OutputFormat",
    
    # Registry
    "TemplateRegistry",
    "DictTemplateRegistry",
    "FileTemplateRegistry",
    
    # Execution
    "PromptExecutor",
    
    # Chains
    "PromptChain",
    "ChainStep",
    "ChainExecutor",
]
```

### 10.2 Usage Examples

```python
# Example 1: Simple execution with in-memory registry
from creative_services.prompts import (
    PromptTemplate, 
    PromptVariable,
    DictTemplateRegistry, 
    PromptExecutor
)
from creative_services.core import DynamicLLMClient

# Create template
template = PromptTemplate(
    key="greeting.simple",
    name="Simple Greeting",
    system_prompt="You are a friendly assistant.",
    user_prompt="Say hello to {{name}} in {{language}}.",
    variables=[
        PromptVariable(name="name", required=True),
        PromptVariable(name="language", required=False, default="English"),
    ]
)

# Setup registry and executor
registry = DictTemplateRegistry()
registry.save(template)

executor = PromptExecutor(
    llm_client=DynamicLLMClient.from_env(),
    template_registry=registry
)

# Execute
result = await executor.execute(
    template_key="greeting.simple",
    variables={"name": "Alice"},
    app_name="demo"
)

print(result.response_content)
# Output: "Hello Alice! How can I help you today?"


# Example 2: File-based templates (GitOps)
from creative_services.prompts import FileTemplateRegistry

registry = FileTemplateRegistry("./prompts")
template = registry.get("writing.character.backstory")


# Example 3: Django integration
from creative_services.adapters.django_prompts import DjangoTemplateRegistry
from myapp.models import PromptTemplateModel

registry = DjangoTemplateRegistry(PromptTemplateModel)
templates = registry.list(domain="writing", tags=["character"])
```

---

## 11. Migration von BFAgent

### 11.1 Migrations-Strategie

```
Phase 1: Adapter (0 Breaking Changes)
├── creative-services installieren
├── DjangoTemplateRegistry mit BFAgent PromptTemplate nutzen
└── Bestehender Code funktioniert weiter

Phase 2: Parallel-Betrieb
├── Neue Templates in Platform erstellen
├── Alte Templates in BFAgent belassen
└── execute_template → PromptExecutor migrieren

Phase 3: Graduelle Migration
├── Template für Template migrieren
├── Tests nach jeder Migration
└── Rollback-Möglichkeit

Phase 4: Cleanup (Optional)
├── Alte BFAgent PromptTemplate deprecaten
├── Alle Templates in Platform
└── BFAgent nutzt nur noch Adapter
```

### 11.2 Kompatibilitäts-Layer

```python
# apps/bfagent/services/llm_client.py - Erweiterung

def execute_template_v2(
    template_key: str,
    variables: dict,
    version: str = "latest",
    **kwargs
) -> dict:
    """
    Wrapper für Platform PromptExecutor.
    
    Behält die alte Signatur bei, nutzt aber Platform unter der Haube.
    """
    from apps.core.prompt_adapters import executor
    
    # Async → Sync wrapper
    import asyncio
    result = asyncio.run(executor.execute(
        template_key=template_key,
        variables=variables,
        version=version,
        app_name="bfagent",
        **kwargs
    ))
    
    # Convert to old format for backward compatibility
    return {
        "ok": result.success,
        "text": result.response_content,
        "rendered_prompt": result.rendered_prompt,
        "template": None,  # Not available in new system
        "llm_used": None,  # Not available in new system
        "execution": result,
        "error": result.error_message,
        "latency_ms": result.execution_time_ms,
    }
```

---

## 12. Vergleich: BFAgent vs Platform

| Aspekt | BFAgent (aktuell) | Platform (neu) |
|--------|-------------------|----------------|
| **Framework** | Django-only | Framework-agnostisch |
| **Storage** | PostgreSQL | Memory, File, DB |
| **Categories** | Hardcoded (9) | Flexible Tags |
| **LLM Binding** | FK zu `Llms` | Tier-basiert |
| **Variables** | JSON Lists | Typed Pydantic |
| **Execution** | Django Model | Pydantic + Adapter |
| **Vererbung** | FK parent_template | Key-basiert |
| **Partials** | ❌ Nicht vorhanden | ✅ Jinja2 Partials |
| **Chains** | ❌ Nicht vorhanden | ✅ Multi-Step |
| **Testing** | Separate Model | Integriert |
| **Portabilität** | Nur BFAgent | Alle Apps |

---

## 13. Implementierungs-Roadmap

### Phase 1: Core Implementation (3 Tage)

| Tag | Aufgabe | Output |
|-----|---------|--------|
| 1 | Schemas implementieren | `prompts/schemas.py` |
| 1 | DictTemplateRegistry | `prompts/registry.py` |
| 2 | Jinja2 Renderer | `prompts/renderer.py` |
| 2 | PromptExecutor | `prompts/executor.py` |
| 3 | Unit Tests | `tests/test_prompts.py` |
| 3 | Public API | `prompts/__init__.py` |

### Phase 2: Storage Backends (2 Tage)

| Tag | Aufgabe | Output |
|-----|---------|--------|
| 4 | FileTemplateRegistry | `prompts/registry.py` |
| 4 | DjangoTemplateRegistry | `adapters/django_prompts.py` |
| 5 | Integration Tests | `tests/test_adapters.py` |

### Phase 3: Advanced Features (2 Tage)

| Tag | Aufgabe | Output |
|-----|---------|--------|
| 6 | Template-Vererbung | `prompts/template.py` |
| 6 | Partials Support | `prompts/renderer.py` |
| 7 | Prompt Chains | `prompts/chains.py` |

### Phase 4: BFAgent Integration (2 Tage)

| Tag | Aufgabe | Output |
|-----|---------|--------|
| 8 | Adapter für BFAgent PromptTemplate | `adapters/django_prompts.py` |
| 8 | Kompatibilitäts-Layer | `bfagent/services/llm_client.py` |
| 9 | Migration Guide | `docs/migration.md` |

**Gesamt: 9 Tage**

---

## 14. Offene Fragen für Review

1. **Naming**: `key` vs `template_key` - welches Naming bevorzugen wir?

2. **Vererbung**: Soll `parent_key` ein FK sein oder nur ein String-Lookup?

3. **A/B Testing**: Soll das System automatisch A/B-Gruppen auswählen oder explizit?

4. **Execution Tracking**: Soll jede Execution in DB gespeichert werden oder nur auf Anfrage?

5. **AgentSkills.io**: Wie wichtig ist die Kompatibilität? Soll das im Core oder als Extension?

6. **Chains**: Sollen Chains ein eigenes Model sein oder als Template-Typ?

7. **Migration**: Sollen wir BFAgent's `PromptTemplate` 1:1 migrieren oder neu starten?

---

## 15. Anhang

### A. YAML Template Format

```yaml
# prompts/writing/character/backstory.yaml

key: writing.character.backstory
name: Character Backstory Generator
version: "1.0"

domain: writing
tags:
  - character
  - backstory
  - creative

system_prompt: |
  Du bist ein erfahrener Autor, spezialisiert auf Charakterentwicklung.
  Du schreibst auf Deutsch und achtest auf psychologische Tiefe.

user_prompt: |
  Erstelle eine detaillierte Hintergrundgeschichte für:
  
  **Charakter:** {{character_name}}
  **Genre:** {{genre}}
  **Rolle:** {{character_role}}
  
  {% if world_setting %}
  **Welt:** {{world_setting}}
  {% endif %}
  
  Die Backstory sollte enthalten:
  1. Kindheit und Herkunft
  2. Prägende Ereignisse
  3. Motivation und Ziele
  4. Innere Konflikte
  
  Länge: ca. {{word_count}} Wörter

variables:
  - name: character_name
    description: Name des Charakters
    required: true
    type: string
    examples: ["Elena Schwarzwald", "Marcus von Stein"]
  
  - name: genre
    description: Genre der Geschichte
    required: true
    type: string
    examples: ["Fantasy", "Science Fiction", "Thriller"]
  
  - name: character_role
    description: Rolle des Charakters
    required: true
    type: string
    examples: ["Protagonist", "Antagonist", "Mentor"]
  
  - name: world_setting
    description: Beschreibung der Welt
    required: false
    type: string
  
  - name: word_count
    description: Ungefähre Wortanzahl
    required: false
    default: 500
    type: integer

output_format: text

llm_params:
  preferred_tier: standard
  max_tokens: 2000
  temperature: 0.8

description: |
  Generiert detaillierte Hintergrundgeschichten für Charaktere.
  Berücksichtigt Genre und Weltenbau.

author: Platform Team
is_active: true
```

### B. JSON Schema für Output Validation

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "CharacterBackstory",
  "type": "object",
  "required": ["childhood", "defining_events", "motivation", "conflicts"],
  "properties": {
    "childhood": {
      "type": "object",
      "properties": {
        "birthplace": {"type": "string"},
        "family": {"type": "string"},
        "early_life": {"type": "string"}
      }
    },
    "defining_events": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "age": {"type": "integer"},
          "event": {"type": "string"},
          "impact": {"type": "string"}
        }
      }
    },
    "motivation": {
      "type": "object",
      "properties": {
        "primary_goal": {"type": "string"},
        "fears": {"type": "array", "items": {"type": "string"}},
        "desires": {"type": "array", "items": {"type": "string"}}
      }
    },
    "conflicts": {
      "type": "object",
      "properties": {
        "internal": {"type": "string"},
        "external": {"type": "string"}
      }
    }
  }
}
```

---

**Ende des Konzeptpapiers**

*Bitte um Review und Feedback zu den offenen Fragen in Abschnitt 14.*
