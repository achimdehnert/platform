# Kritische Analyse: Prompt-Template-System Konzeptpapier

**Review-Datum:** 27. Januar 2026  
**Reviewer:** Software Architecture Review  
**Status:** Detaillierte Analyse mit Optimierungsvorschlägen

---

## Executive Summary

Das Konzeptpapier beschreibt ein **ambitioniertes, gut durchdachtes System** zur Vereinheitlichung der Prompt-Verwaltung. Die Grundarchitektur ist solide, allerdings gibt es **kritische Lücken und Inkonsistenzen** zur Platform-Master-Architektur sowie einige **Design-Schwächen**, die vor der Implementierung adressiert werden sollten.

### Bewertung auf einen Blick

| Aspekt | Bewertung | Priorität |
|--------|-----------|-----------|
| Architektur-Design | 🟡 Gut mit Lücken | Hoch |
| Konsistenz mit Master-Architektur | 🔴 Inkonsistent | Kritisch |
| Sicherheit | 🔴 Unzureichend | Kritisch |
| Performance-Überlegungen | 🟡 Teilweise | Mittel |
| Testbarkeit | 🟢 Gut geplant | - |
| Wartbarkeit | 🟡 Verbesserbar | Mittel |
| Vollständigkeit | 🟡 Lücken vorhanden | Hoch |

---

## 1. Kritische Probleme (Müssen vor Implementierung gelöst werden)

### 1.1 🔴 Inkonsistenz mit Database-First Prinzip

**Problem:** Das Konzept definiert `domain` als String-Feld statt als FK zu einer Lookup-Table.

```python
# ❌ AKTUELL IM KONZEPT (Zeile 178-181):
domain: str = Field(
    default="general", 
    description="Domain: writing, travel, cad, research, general"
)
```

**Verstoß gegen Master-Architektur (Kapitel 1.1):**
> "FK statt String - Referenzen als Foreign Keys, nicht als Strings"

**Vorschlag:**
```python
# ✅ KORRIGIERT: FK zu Domain-Lookup
class PromptDomain(BaseLookupTable):
    """Lookup Table für Prompt-Domains"""
    prompt_guidance: str = ""  # Domain-spezifische Hinweise

# In PromptTemplate:
domain_id: Optional[int] = None  # FK zur PromptDomain
# Für Pydantic-Core: domain_code als Alternative
domain_code: str = Field(default="general", pattern=r'^[a-z_]+$')
```

### 1.2 🔴 Fehlende Sicherheits-Architektur

**Problem:** Das Konzept enthält **keine Sicherheits-Sektion**. Bei Prompt-Templates ist dies kritisch wegen:

1. **Prompt Injection Risks** - User-Variablen könnten manipuliert werden
2. **Keine Validierung von Template-Inhalten** - System-Prompts könnten malicious sein
3. **Keine Berechtigungsprüfung** - Wer darf welche Templates erstellen/ändern?

**Empfehlung:** Neue Sektion "Security Considerations" hinzufügen:

```python
class PromptTemplate(BaseModel):
    # ...existing fields...
    
    # SECURITY
    allow_user_variables: bool = True          # Dürfen User-Variablen genutzt werden?
    sanitize_variables: bool = True            # HTML/Script-Sanitization?
    max_variable_length: int = 10000           # Max Länge pro Variable
    allowed_variable_types: list[str] = ["string", "int", "float", "bool"]
    requires_permission: str = "prompt_user"   # Permission-Level für Ausführung
    
    # Audit
    requires_review: bool = False              # Muss von Admin geprüft werden?
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    
    @validator('system_prompt', 'user_prompt')
    def validate_no_injection(cls, v):
        """Check for common injection patterns"""
        dangerous_patterns = [
            r'ignore.*previous.*instructions',
            r'system.*prompt.*is',
            r'you.*are.*now',
        ]
        # Implementation...
```

### 1.3 🔴 Output-Parser ohne Sicherheits-Validierung

**Problem (Zeile 209):**
```python
output_parser: Optional[str] = None  # Custom parser class path
```

**Risiko:** Beliebiger Code kann als Parser referenziert werden.

**Lösung:**
```python
# Whitelist für erlaubte Parser
ALLOWED_PARSERS = {
    "json": "creative_services.prompts.parsers.JSONParser",
    "markdown": "creative_services.prompts.parsers.MarkdownParser",
    "structured": "creative_services.prompts.parsers.StructuredParser",
}

output_parser: Optional[Literal["json", "markdown", "structured"]] = None
```

---

## 2. Architektur-Schwächen

### 2.1 🟡 Fehlende "Spec vs. Derived" Trennung

**Problem:** Das Konzept definiert `PromptTemplate` als monolithisches Modell, ohne klare Trennung zwischen **Spec** (User-Input) und **Derived** (berechnete Werte).

**Master-Architektur Kapitel 1.2:**
> "In der DB nur Fakten speichern. Alles Berechnete zur Laufzeit."

**Beispiel problematischer Felder:**
```python
# Diese Felder sind DERIVED, nicht SPEC:
output_schema: Optional[dict] = None  # Sollte aus output_format abgeleitet werden können
variables: list[PromptVariable]       # Kann aus Template-Content extrahiert werden
```

**Vorschlag: Aufteilen in PromptTemplateSpec und PromptTemplateResolved**

```python
class PromptTemplateSpec(BaseModel):
    """Was der User/Admin definiert (persistiert)"""
    key: str
    name: str
    system_prompt: str
    user_prompt: str
    domain_code: str = "general"
    tags: list[str] = []
    llm_params: LLMParameters
    schema_version: int = 1  # Wichtig für Migration!

class PromptTemplateResolved(BaseModel):
    """Berechnet zur Laufzeit (nicht persistiert)"""
    spec: PromptTemplateSpec
    extracted_variables: list[PromptVariable]  # Auto-extracted aus Jinja2
    parent_resolved: Optional["PromptTemplateResolved"]  # Nach Vererbungs-Resolution
    effective_system_prompt: str  # Nach Partial-Auflösung
    effective_user_prompt: str
```

### 2.2 🟡 Versionierung ohne Migrator-Pattern

**Problem:** `version: str = "1.0"` ohne Schema-Migration-Strategie.

**Master-Architektur definiert explizit:**
```python
# Kapitel 1.4: Zero Breaking Changes
def _v1_to_v2(payload: dict) -> dict:
    payload = dict(payload)
    payload.setdefault("reader_speed_wpm", 250)
    payload["schema_version"] = 2
    return payload
```

**Im Konzept fehlt:**
1. `schema_version: int` statt `version: str`
2. Migrator-Klasse für Template-Schema-Upgrades
3. Strategie für Breaking Changes (neue Required-Felder etc.)

**Empfehlung:**
```python
class PromptTemplateMigrator:
    """Schema-Migration für PromptTemplates"""
    
    MIGRATIONS = {
        (1, 2): _migrate_v1_to_v2,
        (2, 3): _migrate_v2_to_v3,
    }
    
    CURRENT_VERSION = 3
    
    @classmethod
    def migrate(cls, data: dict) -> dict:
        version = data.get("schema_version", 1)
        while version < cls.CURRENT_VERSION:
            migration_fn = cls.MIGRATIONS.get((version, version + 1))
            if not migration_fn:
                raise ValueError(f"No migration path from v{version}")
            data = migration_fn(data)
            version += 1
        return data
```

### 2.3 🟡 Chain-Design zu komplex

**Problem (Zeilen 698-733):** Das Chain-System hat:
- `input_mapping` und `output_mapping` doppelt definiert
- `condition` als String (Jinja2) - schwer testbar
- Kein Error-Reporting pro Step

**Alternative: Simplified Chain mit Explicit State**

```python
class ChainStep(BaseModel):
    name: str
    template_key: str
    extract_to_context: list[str] = []  # Welche Keys aus Output in Context?
    skip_if: Optional[str] = None        # Simpler: "not include_relationships"
    
class PromptChain(BaseModel):
    key: str
    steps: list[ChainStep]
    
    # Ergebnisse werden automatisch unter step.name im Context gespeichert
    # z.B. context["basic_profile"] = step1_result
```

---

## 3. Fehlende Komponenten

### 3.1 🟡 Kein Rate-Limiting / Quotas

Das System hat `preferred_tier` aber keine Kosten-Kontrolle:

```python
class LLMParameters(BaseModel):
    # ... existing ...
    
    # FEHLT: Cost Control
    max_cost_per_execution: Optional[float] = None  # Max $ pro Aufruf
    daily_quota_key: Optional[str] = None           # Quota-Bucket-Key
```

### 3.2 🟡 Kein Caching-Layer

Für häufig ausgeführte Templates mit gleichen Variablen:

```python
class PromptExecutor:
    def __init__(
        self,
        # ... existing ...
        cache: Optional[PromptCache] = None,
    ):
        self.cache = cache
    
    async def execute(self, template_key: str, variables: dict, **kwargs):
        # Check cache
        if self.cache:
            cache_key = self._build_cache_key(template_key, variables)
            cached = await self.cache.get(cache_key)
            if cached:
                return cached
```

### 3.3 🟡 Kein Dry-Run Mode

Für Testing und Preview:

```python
async def execute(
    self,
    template_key: str,
    variables: dict,
    dry_run: bool = False,  # ← FEHLT
    **kwargs
) -> PromptExecution:
    """
    dry_run=True: Rendert Template, ruft LLM NICHT auf
    """
```

### 3.4 🔴 Keine Observability-Integration

**Master-Architektur Kapitel 10:** Definiert explizit Observability-Patterns.

**Im Konzept fehlt:**
```python
# Structured Logging Events
PROMPT_EXECUTION_STARTED = "prompt.execution.started"
PROMPT_EXECUTION_COMPLETED = "prompt.execution.completed"
PROMPT_EXECUTION_FAILED = "prompt.execution.failed"
PROMPT_VALIDATION_FAILED = "prompt.validation.failed"

# Metrics
prompt_execution_duration = Histogram(
    "prompt_execution_duration_seconds",
    "Time spent executing prompts",
    ["template_key", "tier", "success"]
)
```

---

## 4. API-Design Verbesserungen

### 4.1 Public API zu umfangreich

**Problem:** Das vorgeschlagene `__init__.py` exportiert zu viele interne Klassen.

**Aktuell (implizit):**
```python
from creative_services.prompts import (
    PromptTemplate,
    PromptVariable,
    LLMParameters,
    PromptExecution,
    PromptChain,
    ChainStep,
    TemplateRegistry,
    DictTemplateRegistry,
    FileTemplateRegistry,
    PromptExecutor,
    PromptRenderer,
    # ...
)
```

**Besser: Minimale Public API**
```python
# creative_services/prompts/__init__.py

# Core (für Template-Definition)
from .schemas import PromptTemplate, PromptVariable, LLMParameters

# Execution (für App-Integration)
from .executor import execute_prompt, execute_chain

# Registry Factory (versteckt Implementierungen)
from .registry import get_registry

__all__ = [
    "PromptTemplate",
    "PromptVariable", 
    "LLMParameters",
    "execute_prompt",
    "execute_chain",
    "get_registry",
]
```

### 4.2 Naming-Inkonsistenzen

| Aktuell | Empfehlung | Grund |
|---------|------------|-------|
| `key` | `template_key` | Expliziter, vermeidet Python-Keyword-Nähe |
| `version` | `schema_version` | Konsistent mit Master-Architektur |
| `ab_test_group` | `experiment_variant` | Industry-Standard Terminology |
| `llm_params` | `llm_config` | "Config" deutet auf Konfiguration hin |

---

## 5. Roadmap-Kritik

### 5.1 Zeitschätzung zu optimistisch

**Aktuell: 9 Tage total**

| Phase | Geschätzt | Realistisch | Delta |
|-------|-----------|-------------|-------|
| Core Implementation | 3 Tage | 5 Tage | +2 |
| Storage Backends | 2 Tage | 3 Tage | +1 |
| Advanced Features | 2 Tage | 4 Tage | +2 |
| BFAgent Integration | 2 Tage | 4 Tage | +2 |
| **Security Layer** | ❌ Fehlt | 3 Tage | +3 |
| **Observability** | ❌ Fehlt | 2 Tage | +2 |
| **Testing (umfassend)** | ❌ Fehlt | 3 Tage | +3 |

**Realistisch: 24 Tage (ca. 5 Wochen)**

### 5.2 Fehlende Milestones

```
Phase 0: Security & Architecture Review (1 Woche)
├── Security-Architektur definieren
├── Konsistenz mit Master-Architektur herstellen
└── API-Design finalisieren

Phase 1: Core + Security (1.5 Wochen)
├── Schemas mit Spec/Derived Trennung
├── Security-Validatoren
├── Migrator-Pattern
└── Unit Tests

Phase 2: Storage + Observability (1 Woche)
├── Registry-Implementierungen
├── Structured Logging
├── Metrics
└── Integration Tests

Phase 3: Advanced Features (1 Woche)
├── Template-Vererbung
├── Partials
├── Chains (vereinfacht)
└── Caching

Phase 4: Integration (1 Woche)
├── BFAgent Adapter
├── Migration Guide
├── E2E Tests
└── Documentation
```

---

## 6. Offene Fragen - Empfohlene Antworten

Das Konzept listet 7 offene Fragen (Abschnitt 14). Hier meine Empfehlungen:

### Frage 1: `key` vs `template_key`
**Empfehlung:** `template_key` - expliziter und vermeidet Verwechslung mit Dict-Keys.

### Frage 2: `parent_key` - FK oder String-Lookup?
**Empfehlung:** String-Lookup mit Validierung beim Speichern.
```python
@validator('parent_key')
def validate_parent_exists(cls, v, values):
    if v and not registry.exists(v):
        raise ValueError(f"Parent template '{v}' not found")
    return v
```

### Frage 3: A/B Testing - automatisch oder explizit?
**Empfehlung:** Explizit mit Feature-Flag-Integration.
```python
# Nicht automatisch - User/Service wählt Variante
result = await executor.execute(
    template_key="writing.character.backstory",
    experiment_variant="B",  # Explizit
    variables={...}
)
```

### Frage 4: Execution Tracking - immer oder auf Anfrage?
**Empfehlung:** Konfigurierbar mit Default "sample".
```python
class ExecutorConfig(BaseModel):
    track_executions: Literal["none", "sample", "all"] = "sample"
    sample_rate: float = 0.1  # 10% bei "sample"
```

### Frage 5: AgentSkills.io - Core oder Extension?
**Empfehlung:** Extension. Nicht im Core-System.

### Frage 6: Chains - eigenes Model oder Template-Typ?
**Empfehlung:** Eigenes Model (`PromptChain`) - klare Trennung.

### Frage 7: BFAgent Migration - 1:1 oder neu starten?
**Empfehlung:** Hybrid. Adapter für Kompatibilität + schrittweise Migration.

---

## 7. Konkrete Optimierungsvorschläge - Zusammenfassung

### Sofort umsetzen (vor Implementierung)

1. ✅ Sicherheits-Sektion hinzufügen
2. ✅ `schema_version: int` statt `version: str`
3. ✅ Migrator-Pattern definieren
4. ✅ `domain` als FK/Code-Lookup statt freier String
5. ✅ Observability-Events definieren

### Architektur-Änderungen

1. ✅ Spec/Derived Trennung einführen
2. ✅ Chain-Design vereinfachen
3. ✅ Public API minimieren
4. ✅ Rate-Limiting/Quotas ergänzen
5. ✅ Caching-Layer planen

### Roadmap-Anpassungen

1. ✅ Security-Phase hinzufügen
2. ✅ Zeitschätzungen realistischer
3. ✅ Observability-Phase einplanen
4. ✅ Test-Coverage explizit definieren

---

## 8. Beispiel: Überarbeitetes PromptTemplate

```python
from datetime import datetime
from typing import Optional, Literal, Any
from pydantic import BaseModel, Field, validator
import re

# Konstanten
CURRENT_SCHEMA_VERSION = 1
ALLOWED_OUTPUT_PARSERS = ("json", "markdown", "text", "structured")
MAX_PROMPT_LENGTH = 50000
MAX_VARIABLE_COUNT = 50


class PromptVariable(BaseModel):
    """Definition einer Template-Variable"""
    name: str = Field(..., pattern=r'^[a-z][a-z0-9_]*$', max_length=64)
    description: str = Field(default="", max_length=500)
    required: bool = True
    default: Optional[Any] = None
    var_type: Literal["string", "int", "float", "bool", "list", "dict"] = "string"
    max_length: Optional[int] = None  # Für Strings
    examples: list[str] = Field(default_factory=list, max_items=5)


class LLMConfig(BaseModel):
    """LLM-Konfiguration (umbenannt von LLMParameters)"""
    max_tokens: int = Field(default=1000, ge=1, le=100000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    preferred_tier: Literal["economy", "standard", "premium", "local"] = "standard"
    preferred_provider: Optional[str] = None
    fallback_tier: Optional[str] = None
    allow_downgrade: bool = True
    max_cost: Optional[float] = None  # Max $ pro Aufruf


class PromptTemplateSpec(BaseModel):
    """
    Prompt Template Specification (persistiert).
    
    Folgt dem Spec/Derived Pattern der Platform-Architektur.
    """
    
    # IDENTITY
    template_key: str = Field(
        ..., 
        pattern=r'^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$',
        max_length=128,
        description="Unique key: 'writing.character.backstory'"
    )
    name: str = Field(..., max_length=200)
    schema_version: int = Field(default=CURRENT_SCHEMA_VERSION, ge=1)
    
    # TAXONOMY
    domain_code: str = Field(
        default="general",
        pattern=r'^[a-z][a-z0-9_]*$',
        max_length=32
    )
    tags: list[str] = Field(default_factory=list, max_items=20)
    
    # CONTENT
    system_prompt: str = Field(..., max_length=MAX_PROMPT_LENGTH)
    user_prompt: str = Field(..., max_length=MAX_PROMPT_LENGTH)
    
    # VARIABLES (explizit definiert, nicht auto-extracted)
    variables: list[PromptVariable] = Field(
        default_factory=list, 
        max_items=MAX_VARIABLE_COUNT
    )
    
    # OUTPUT
    output_format: Literal["text", "json", "markdown"] = "text"
    output_schema: Optional[dict] = None
    
    # LLM CONFIG
    llm_config: LLMConfig = Field(default_factory=LLMConfig)
    
    # COMPOSITION
    parent_key: Optional[str] = None
    partials: dict[str, str] = Field(default_factory=dict, max_items=20)
    
    # METADATA
    description: str = Field(default="", max_length=2000)
    author: str = Field(default="", max_length=100)
    is_active: bool = True
    
    # SECURITY
    requires_review: bool = False
    sanitize_user_input: bool = True
    max_variable_length: int = Field(default=10000, ge=100, le=100000)
    
    # A/B TESTING
    experiment_variant: Optional[str] = Field(default=None, max_length=32)
    experiment_weight: float = Field(default=1.0, ge=0.0, le=1.0)
    
    # TIMESTAMPS (für DB-Backend)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # ══════════════════════════════════════════════════════════════
    # VALIDATORS
    # ══════════════════════════════════════════════════════════════
    
    @validator('system_prompt', 'user_prompt')
    def validate_no_obvious_injection(cls, v: str) -> str:
        """Basic injection pattern detection"""
        dangerous_patterns = [
            r'ignore\s+(all\s+)?previous\s+instructions?',
            r'forget\s+(all\s+)?previous',
            r'you\s+are\s+now\s+a',
            r'new\s+instructions?:',
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError(f"Potentially dangerous pattern detected in prompt")
        return v
    
    @validator('tags', each_item=True)
    def validate_tag_format(cls, v: str) -> str:
        if not re.match(r'^[a-z][a-z0-9_-]*$', v):
            raise ValueError(f"Invalid tag format: {v}")
        return v.lower()
    
    @validator('output_schema')
    def validate_json_schema(cls, v):
        if v is not None:
            # Basic JSON Schema validation
            if not isinstance(v, dict):
                raise ValueError("output_schema must be a dict")
            if 'type' not in v:
                raise ValueError("output_schema must have 'type' field")
        return v
    
    # ══════════════════════════════════════════════════════════════
    # HELPER METHODS
    # ══════════════════════════════════════════════════════════════
    
    def get_required_variable_names(self) -> list[str]:
        return [v.name for v in self.variables if v.required]
    
    def get_variable_defaults(self) -> dict[str, Any]:
        return {v.name: v.default for v in self.variables if v.default is not None}
    
    def validate_provided_variables(self, provided: dict[str, Any]) -> list[str]:
        """Return list of missing required variables"""
        required = self.get_required_variable_names()
        return [name for name in required if name not in provided]
    
    class Config:
        # Pydantic v2 style
        json_schema_extra = {
            "example": {
                "template_key": "writing.character.backstory",
                "name": "Character Backstory Generator",
                "domain_code": "writing",
                "tags": ["character", "creative"],
                "system_prompt": "Du bist ein erfahrener Autor...",
                "user_prompt": "Erstelle eine Backstory für {{character_name}}",
                "variables": [
                    {"name": "character_name", "required": True, "var_type": "string"}
                ],
            }
        }
```

---

## 9. Fazit

Das Konzeptpapier bietet eine **solide Grundlage**, aber es bedarf **signifikanter Überarbeitung** vor der Implementierung:

**Stärken:**
- Klare Problemanalyse des bestehenden Systems
- Gute Trennung von Concerns (Registry, Renderer, Executor)
- Durchdachtes Execution-Tracking

**Kritische Lücken:**
- Sicherheits-Architektur fehlt komplett
- Inkonsistenz mit Master-Architektur (Database-First, Spec/Derived)
- Keine Observability-Integration
- Zu optimistische Zeitschätzung

**Empfehlung:** 
1. Diesen Review mit dem Architecture Team besprechen
2. Kritische Lücken schließen
3. Revidierte Version erstellen
4. Dann erst implementieren

---

*Review abgeschlossen. Für Rückfragen stehe ich zur Verfügung.*
