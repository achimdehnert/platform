# Kritischer Architektur-Review: ADR-003, ADR-007, ADR-008

**Reviewer:** IT-Architekt (Expert Review)  
**Datum:** 2026-02-02  
**Geprüfte Prinzipien:**
- Datenbankgetriebenheit (Database-First)
- Strikte Normalisierung
- Separation of Concerns
- Einhaltung von Naming Conventions

---

## Executive Summary

Die drei ADRs zeigen eine **grundsätzlich solide Architektur** mit klarem Fokus auf Enterprise-Patterns. Jedoch gibt es **signifikante Inkonsistenzen** zwischen den Dokumenten, **Verstöße gegen die eigenen Prinzipien** und **strukturelle Schwachstellen**, die vor der Implementierung adressiert werden sollten.

### Gesamtbewertung

| ADR | Stärken | Schwächen | Reifegrad |
|-----|---------|-----------|-----------|
| **ADR-003 (CAD-Hub)** | Klare Feature-Definition, gute API-Konzepte | JSONB-Overuse, Normalisierungsverstöße, Naming-Inkonsistenzen | 🟡 60% |
| **ADR-007 (Tenant/RBAC)** | Exzellente Normalisierung, klare Layer-Trennung | Überkomplexität an einigen Stellen | 🟢 85% |
| **ADR-008 (Infrastructure)** | Gutes Self-Healing-Konzept, GitOps | Unvollständige DB-Integration, fehlende Normalisierung bei Configs | 🟡 70% |

---

## Teil 1: ADR-003 (CAD-Hub NL2CAD) - Kritische Analyse

### 1.1 ❌ Schwerwiegende Verstöße: JSONB-Overuse

**Problem:** Das Dokument widerspricht dem Prinzip "Strikte Normalisierung" massiv:

```python
# PROBLEMATISCH - Zeile 439-472 in ADR-003
class Window(models.Model):
    properties = models.JSONField(default=dict)  # ❌ JSONB für kritische Daten

class Door(models.Model):
    properties = models.JSONField(default=dict)  # ❌ JSONB für kritische Daten

class Wall(models.Model):
    properties = models.JSONField(default=dict)  # ❌ JSONB für kritische Daten

class CADModel(models.Model):  # Zeile 527-552
    generation_params = models.JSONField(default=dict)  # ❌ Kritisch für Audit
    elements_json = models.JSONField(default=dict)      # ❌ Sollte normalisiert sein
    statistics = models.JSONField(default=dict)         # ❌ Verlust von Abfragbarkeit
```

**Impact:**
- Keine referentielle Integrität für Properties
- Keine DB-Level-Constraints
- Keine effiziente Abfrage (kein Index auf JSONB-Felder)
- Audit-Trail inkonsistent

**Optimierungsvorschlag:**

```python
# KORREKT: Normalisierte Property-Struktur
class ElementProperty(models.Model):
    """Normalisierte Properties für alle CAD-Elemente"""
    id = models.UUIDField(primary_key=True)
    
    # Polymorphe Referenz
    content_type = models.ForeignKey(ContentType, on_delete=CASCADE)
    object_id = models.UUIDField()
    element = GenericForeignKey('content_type', 'object_id')
    
    # Normalisierte Felder
    property_definition = models.ForeignKey('PropertyDefinition', on_delete=PROTECT)
    value_text = models.TextField(null=True)
    value_numeric = models.DecimalField(max_digits=20, decimal_places=6, null=True)
    value_boolean = models.BooleanField(null=True)
    unit = models.ForeignKey('Unit', on_delete=PROTECT, null=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['property_definition', 'value_numeric']),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(value_text__isnull=False) | 
                      Q(value_numeric__isnull=False) | 
                      Q(value_boolean__isnull=False),
                name='chk_element_property_has_value'
            )
        ]


class PropertyDefinition(models.Model):
    """Stammdaten für Property-Typen (IFC PropertySets)"""
    code = models.CharField(max_length=100, primary_key=True)  # z.B. "Pset_WindowCommon.ThermalTransmittance"
    name = models.CharField(max_length=255)
    data_type = models.CharField(max_length=20, choices=[
        ('text', 'Text'),
        ('numeric', 'Numeric'),
        ('boolean', 'Boolean'),
    ])
    default_unit = models.ForeignKey('Unit', null=True, on_delete=SET_NULL)
    ifc_property_set = models.CharField(max_length=100)
    
    class Meta:
        db_table = 'cad_property_definition'
```

### 1.2 ❌ Naming Convention Verstöße

**Inkonsistenzen gefunden:**

| Zeile | Problem | Korrekt |
|-------|---------|---------|
| 484 | `Organization` | `core_organization` (DB) oder `Tenant` (Konsistenz mit ADR-007) |
| 269 | `FlächenSummary` (Deutsch) | `AreaSummary` (Englisch konsistent) |
| 314 | `UsageCategory` vs ADR-007 `TenantRole` | Inkonsistentes Enum-Naming |
| 559-560 | `cad_model` Tabelle ohne Prefix | `cad_cad_model` oder `cadhub_model` |
| 566 | `current_setting('app.current_org_id')` | `current_setting('app.current_tenant_id')` (ADR-007 Konsistenz) |

**Optimierungsvorschlag - Einheitliche Naming Convention:**

```python
# Konsistente Naming Convention für CAD-Hub

# === MODELS ===
# Pattern: {app}_{entity} für Tabellennamen
# Pattern: {Entity}Model für Python-Klassen bei Kollisionen

class Tenant(models.Model):  # NICHT Organization - konsistent mit ADR-007
    class Meta:
        db_table = 'cadhub_tenant'  # Präfix für CAD-Hub

class Project(models.Model):
    class Meta:
        db_table = 'cadhub_project'

class CADModelRecord(models.Model):  # Umbenennung wegen Kollision mit "Model"
    class Meta:
        db_table = 'cadhub_cad_model'

# === ENUMS ===
# Pattern: {Domain}{Type}
class CADObjectType(str, Enum):  # NICHT SupportedCADTypes
    COLUMN = "column"
    BEAM = "beam"

class DIN277UsageCategory(str, Enum):  # NICHT UsageCategory - Domain-spezifisch
    NF1_RESIDENTIAL = "NF1.1"
    NF2_OFFICE = "NF2"

# === SERVICES ===
# Pattern: {Domain}{Action}Service
class CADGenerationService:  # NICHT NL2CADService
    pass

class CADParsingService:  # NICHT IFCParserService
    pass
```

### 1.3 ⚠️ Separation of Concerns Verstöße

**Problem:** Die Domain-Layer-Definition mischt Verantwortlichkeiten:

```
# Aus ADR-003 Zeile 119-138
DOMAIN LAYER enthält:
  - cad-services (Parser, Extractor) → ✅ OK
  - nl2cad-engine (PromptParser, CADGenerator) → ⚠️ Hybrid AI/Domain
```

**Problem-Analyse:**
- `PromptParser` ist eigentlich APPLICATION Layer (Use Case)
- `CADGenerator` mischt AI-Orchestration mit Domain-Logik
- `ModelRefiner` gehört in APPLICATION Layer

**Optimierte Layer-Struktur:**

```
┌─────────────────────────────────────────────────────────────────────┐
│                       APPLICATION LAYER                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │ NL2CADHandler│  │CADTransform │  │CADAnalysis  │                 │
│  │             │  │  Handler    │  │  Handler    │                 │
│  │ - execute() │  │ - execute() │  │ - execute() │                 │
│  │ - validate()│  │             │  │             │                 │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                 │
│         │                │                │                         │
│         └────────────────┼────────────────┘                         │
│                          │                                          │
│  ┌───────────────────────▼───────────────────────────────────┐     │
│  │                    AI ORCHESTRATION SERVICE                │     │
│  │  - LLMPromptService (prompt engineering)                   │     │
│  │  - IntentExtractionService (NL → structured)               │     │
│  │  - RefinementService (iterative improvement)               │     │
│  └───────────────────────────────────────────────────────────┘     │
├─────────────────────────────────────────────────────────────────────┤
│                         DOMAIN LAYER                                 │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                      cad-services                            │   │
│  │  - IFCDomainService (IFC business rules)                    │   │
│  │  - DXFDomainService (DXF business rules)                    │   │
│  │  - GeometryCalculationService (area, volume, etc.)          │   │
│  │  - MaterialService (material library, constraints)          │   │
│  │  - ValidationService (CAD schema validation)                │   │
│  └─────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│                      INFRASTRUCTURE LAYER                            │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  - IFCParser (ifcopenshell wrapper)                         │   │
│  │  - DXFParser (ezdxf wrapper)                                │   │
│  │  - LLMGateway (Claude/OpenAI adapter)                       │   │
│  │  - StorageAdapter (S3, local)                               │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.4 ❌ Fehlende Datenbankgetriebenheit

**Problem:** Generation-Parameter sind nicht DB-enforced:

```python
# PROBLEMATISCH - Keine DB-Constraints für Generation
class CADModel(models.Model):
    generation_params = models.JSONField(default=dict)  # Keine Validierung
```

**Optimierung - Database-Enforced Generation Config:**

```python
class GenerationRequest(models.Model):
    """Normalisierte Generation-Anfrage mit DB-Constraints"""
    id = models.UUIDField(primary_key=True)
    cad_model = models.OneToOneField('CADModel', on_delete=CASCADE)
    
    # Normalisierte Parameter
    prompt_text = models.TextField()
    prompt_hash = models.CharField(max_length=64, db_index=True)  # Für Caching
    
    object_type = models.CharField(
        max_length=50,
        choices=CADObjectType.choices,
        db_comment='Generated object type from intent extraction'
    )
    
    # Dimensionen - normalisiert statt JSONB
    dimension_x = models.DecimalField(max_digits=12, decimal_places=3, null=True)
    dimension_y = models.DecimalField(max_digits=12, decimal_places=3, null=True)
    dimension_z = models.DecimalField(max_digits=12, decimal_places=3, null=True)
    unit = models.ForeignKey('Unit', on_delete=PROTECT)
    
    # Material - FK statt String
    material = models.ForeignKey('MaterialDefinition', on_delete=PROTECT, null=True)
    
    # LLM Metadata
    llm_model_used = models.CharField(max_length=100)
    llm_tokens_input = models.IntegerField()
    llm_tokens_output = models.IntegerField()
    llm_cost_cents = models.IntegerField()  # Für Billing
    
    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=PROTECT)
    
    class Meta:
        db_table = 'cadhub_generation_request'
        indexes = [
            models.Index(fields=['prompt_hash']),
            models.Index(fields=['object_type', 'created_at']),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(llm_tokens_input__gte=0) & Q(llm_tokens_output__gte=0),
                name='chk_generation_positive_tokens'
            ),
        ]
```

---

## Teil 2: ADR-007 (Tenant/RBAC) - Kritische Analyse

### 2.1 ✅ Stärken (Best Practice)

ADR-007 ist das **stärkste Dokument** und folgt den Prinzipien gut:

```python
# EXCELLENT: Vollständig normalisierte Permissions (Zeile 188-200)
core_permission (code PK)
     ↑
core_role_permission (role, permission_code FK)
     ↑
core_membership_permission_override (membership_id FK, permission_code FK, allowed)
```

### 2.2 ⚠️ Schwachstelle: Cache-Invalidierung

**Problem:** Die Cache-Strategie (Zeile 1401) ist zu simpel:

```python
PERMISSION_CACHE_TTL = 60  # Sekunden - zu lang für kritische Permissions
```

**Risiko:** Bei Permission-Änderungen bis zu 60s inkorrekte Autorisierung.

**Optimierung:**

```python
# settings.py
PERMISSION_CACHE_CONFIG = {
    'backend': 'django.core.cache.backends.redis.RedisCache',
    'ttl_seconds': 30,  # Reduziert
    'invalidation_strategy': 'write_through',  # Sofortige Invalidierung
    'fallback_on_cache_miss': 'database',  # Fail-safe
}

# services/authorization.py
class AuthorizationService:
    def grant_permission(self, membership_id: UUID, permission_code: str) -> None:
        with transaction.atomic():
            # 1. DB Update
            self._permission_repo.grant(membership_id, permission_code)
            
            # 2. Sofortige Cache-Invalidierung
            transaction.on_commit(
                lambda: self._cache.invalidate_user_permissions(membership_id)
            )
            
            # 3. Event für andere Instanzen
            transaction.on_commit(
                lambda: self._event_bus.publish(
                    PermissionChangedEvent(membership_id=membership_id)
                )
            )
```

### 2.3 ⚠️ Fehlende Namenskonvention-Dokumentation

**Problem:** ADR-007 definiert Tabellennamen wie `core_tenant`, `core_tenant_membership`, aber dokumentiert nicht das Pattern.

**Optimierung - Explizite Naming Convention:**

```markdown
## Naming Conventions (Ergänzung für ADR-007)

### Datenbank-Tabellen
| Pattern | Beispiel | Beschreibung |
|---------|----------|--------------|
| `{app}_{entity}` | `core_tenant` | Haupt-Entitäten |
| `{app}_{entity}_{sub}` | `core_tenant_membership` | Abhängige Entitäten |
| `{app}_{entity1}_{entity2}` | `core_role_permission` | M:N Beziehungen |

### Constraints
| Pattern | Beispiel |
|---------|----------|
| `chk_{table}_{description}` | `chk_tenant_valid_status` |
| `uq_{table}_{fields}` | `uq_tenant_slug` |
| `fk_{table}_{referenced}` | `fk_membership_tenant` |

### Indexes
| Pattern | Beispiel |
|---------|----------|
| `idx_{table}_{fields}` | `idx_membership_user_tenant` |
```

---

## Teil 3: ADR-008 (Infrastructure) - Kritische Analyse

### 3.1 ❌ Fehlende Datenbankgetriebenheit für Configs

**Problem:** Service-Registry und Package-Registry sind YAML-Files statt DB:

```yaml
# PROBLEMATISCH - Zeile 113-153 in ADR-008
# services/registry.yaml - Keine DB-Integration
services:
  bfagent:
    type: django
    domain: bfagent.iil.pet
```

**Impact:**
- Keine transaktionale Konsistenz
- Keine Audit-Trail für Config-Änderungen
- Keine DB-Constraints für Abhängigkeiten

**Optimierung - Database-Driven Service Registry:**

```python
# infrastructure/models.py

class ServiceDefinition(models.Model):
    """Database-driven Service Registry"""
    code = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=255)
    
    service_type = models.CharField(max_length=50, choices=[
        ('django', 'Django Application'),
        ('static', 'Static Site'),
        ('worker', 'Background Worker'),
        ('api', 'API Service'),
    ])
    
    # Deployment
    domain = models.CharField(max_length=255, unique=True)
    repo_url = models.URLField()
    default_branch = models.CharField(max_length=100, default='main')
    health_endpoint = models.CharField(max_length=255, default='/health/')
    
    # Resources - normalisiert
    cpu_cores = models.IntegerField(default=1)
    memory_mb = models.IntegerField(default=512)
    
    # Status
    is_active = models.BooleanField(default=True)
    tier = models.CharField(max_length=50, choices=[
        ('production', 'Production'),
        ('staging', 'Staging'),
        ('development', 'Development'),
    ])
    
    class Meta:
        db_table = 'infra_service_definition'
        constraints = [
            models.CheckConstraint(
                check=Q(cpu_cores__gte=1) & Q(cpu_cores__lte=32),
                name='chk_service_cpu_range'
            ),
            models.CheckConstraint(
                check=Q(memory_mb__gte=128) & Q(memory_mb__lte=65536),
                name='chk_service_memory_range'
            ),
        ]


class ServiceDependency(models.Model):
    """Normalisierte Service-Abhängigkeiten"""
    id = models.UUIDField(primary_key=True, default=uuid4)
    
    service = models.ForeignKey(ServiceDefinition, on_delete=CASCADE, related_name='dependencies')
    depends_on = models.ForeignKey(ServiceDefinition, on_delete=PROTECT, related_name='dependents')
    
    dependency_type = models.CharField(max_length=50, choices=[
        ('required', 'Required'),
        ('optional', 'Optional'),
    ])
    
    class Meta:
        db_table = 'infra_service_dependency'
        unique_together = [['service', 'depends_on']]
        constraints = [
            models.CheckConstraint(
                check=~Q(service=F('depends_on')),
                name='chk_no_self_dependency'
            ),
        ]


class DeploymentEvent(models.Model):
    """Audit-Trail für alle Deployments"""
    id = models.UUIDField(primary_key=True, default=uuid4)
    
    service = models.ForeignKey(ServiceDefinition, on_delete=PROTECT)
    environment = models.CharField(max_length=50)
    
    # Deployment Details
    git_sha = models.CharField(max_length=40)
    git_ref = models.CharField(max_length=255)
    image_tag = models.CharField(max_length=255)
    
    # Status
    status = models.CharField(max_length=50, choices=[
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('rolled_back', 'Rolled Back'),
    ])
    
    # Self-Healing
    auto_fix_applied = models.BooleanField(default=False)
    auto_fix_type = models.CharField(max_length=100, null=True)
    
    # Timestamps
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True)
    
    # Audit
    triggered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=PROTECT, null=True)
    trigger_source = models.CharField(max_length=50, choices=[
        ('manual', 'Manual'),
        ('ci_cd', 'CI/CD Pipeline'),
        ('self_healing', 'Self-Healing'),
        ('rollback', 'Automatic Rollback'),
    ])
    
    class Meta:
        db_table = 'infra_deployment_event'
        indexes = [
            models.Index(fields=['service', '-started_at']),
            models.Index(fields=['status', 'environment']),
        ]
```

### 3.2 ⚠️ Self-Healing Konfiguration nicht normalisiert

**Problem:** Auto-Fix-Rules sind in YAML (Zeile 1451):

```yaml
# concepts/auto_fix_rules.yaml - Nicht DB-enforced
```

**Optimierung:**

```python
class AutoFixRule(models.Model):
    """Database-driven Auto-Fix Rules mit Audit"""
    id = models.UUIDField(primary_key=True, default=uuid4)
    
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField()
    
    # Pattern Matching
    error_pattern = models.TextField(help_text='Regex pattern for error detection')
    error_category = models.CharField(max_length=100)
    
    # Fix Configuration
    fix_type = models.CharField(max_length=50, choices=[
        ('restart_service', 'Restart Service'),
        ('clear_cache', 'Clear Cache'),
        ('rollback', 'Rollback to Previous'),
        ('scale_up', 'Scale Up Resources'),
        ('run_migration', 'Run Migration'),
    ])
    fix_script = models.TextField(null=True, help_text='Optional custom fix script')
    
    # Safety
    confidence_threshold = models.IntegerField(
        default=85,
        validators=[MinValueValidator(50), MaxValueValidator(100)]
    )
    requires_approval = models.BooleanField(default=False)
    max_auto_attempts = models.IntegerField(default=3)
    
    # Environment Restrictions
    allowed_in_production = models.BooleanField(default=False)
    allowed_in_staging = models.BooleanField(default=True)
    
    # Audit
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=PROTECT)
    
    class Meta:
        db_table = 'infra_auto_fix_rule'
        constraints = [
            models.CheckConstraint(
                check=Q(confidence_threshold__gte=50) & Q(confidence_threshold__lte=100),
                name='chk_autofix_confidence_range'
            ),
        ]
```

### 3.3 ❌ Inkonsistenz mit ADR-007

**Problem:** ADR-008 definiert keine Tenant-Isolation für Infrastructure:

- Deployment-Events sollten tenant-aware sein (wenn Service tenant-spezifisch ist)
- Keine RLS-Integration definiert

**Optimierung:**

```sql
-- RLS für Deployment-Events (wenn tenant-spezifisch)
ALTER TABLE infra_deployment_event ENABLE ROW LEVEL SECURITY;

CREATE POLICY deployment_tenant_policy ON infra_deployment_event
    USING (
        service_id IN (
            SELECT code FROM infra_service_definition sd
            WHERE sd.tenant_id = current_setting('app.current_tenant_id')::uuid
            OR sd.is_platform_service = true  -- Platform-Services für alle sichtbar
        )
    );
```

---

## Teil 4: Cross-ADR-Inkonsistenzen

### 4.1 Tenant-Model Diskrepanz

| ADR | Tenant-Bezeichnung | Tabelle |
|-----|-------------------|---------|
| ADR-003 | `Organization` | `organization` |
| ADR-007 | `Tenant` | `core_tenant` |
| ADR-008 | Nicht definiert | - |

**Empfehlung:** Einheitlich `Tenant` mit Tabelle `core_tenant` verwenden.

### 4.2 RLS-Context-Variable Inkonsistenz

| ADR | Context Variable |
|-----|-----------------|
| ADR-003 | `app.current_org_id` |
| ADR-007 | `app.current_tenant_id` (implizit) |

**Empfehlung:** Einheitlich `app.current_tenant_id`.

### 4.3 Handler-Pattern Adoption

| ADR | Handler-Pattern |
|-----|----------------|
| ADR-003 | Nicht definiert |
| ADR-007 | Vollständig definiert |
| ADR-008 | Teilweise (Self-Healing) |

**Empfehlung:** ADR-003 muss Handler-Pattern übernehmen:

```python
# cad_hub/handlers/generation.py

@dataclass
class GenerateCADCommand:
    prompt: str
    output_formats: list[str]
    project_id: UUID | None = None
    tenant_id: UUID  # Von Context

@dataclass
class GenerateCADResult:
    model_id: UUID
    files: list[GeneratedFile]
    statistics: GenerationStatistics
    errors: list[str]

class GenerateCADHandler(Handler[GenerateCADCommand, GenerateCADResult]):
    """Handler für CAD-Generierung - analog ADR-007 Pattern"""
    
    def __init__(
        self,
        generation_service: CADGenerationService,
        storage_service: StorageService,
        model_repository: CADModelRepository,
    ):
        self._generation = generation_service
        self._storage = storage_service
        self._repo = model_repository
    
    def execute(self, command: GenerateCADCommand) -> GenerateCADResult:
        # 1. Validate
        self._validate(command)
        
        # 2. Generate
        with transaction.atomic():
            result = self._generation.generate(command.prompt)
            
            # 3. Store
            model = self._repo.create(
                tenant_id=command.tenant_id,
                project_id=command.project_id,
                prompt=command.prompt,
            )
            
            # 4. Upload files
            files = self._storage.upload_all(result.files, model.id)
            
            return GenerateCADResult(
                model_id=model.id,
                files=files,
                statistics=result.statistics,
                errors=[],
            )
```

---

## Teil 5: Priorisierte Handlungsempfehlungen

### Priorität 1: KRITISCH (vor Implementierung)

| # | Maßnahme | ADR | Aufwand |
|---|----------|-----|---------|
| 1.1 | JSONB → Normalisierte Tabellen in ADR-003 | ADR-003 | 3 Tage |
| 1.2 | Einheitliche Tenant-Bezeichnung (`Tenant`) | Alle | 1 Tag |
| 1.3 | Einheitliche Context-Variable | Alle | 0.5 Tag |
| 1.4 | Handler-Pattern für ADR-003 definieren | ADR-003 | 2 Tage |

### Priorität 2: WICHTIG (erste Iteration)

| # | Maßnahme | ADR | Aufwand |
|---|----------|-----|---------|
| 2.1 | Database-driven Service Registry | ADR-008 | 2 Tage |
| 2.2 | Naming Convention Dokument | Alle | 1 Tag |
| 2.3 | Cache-Invalidierung verbessern | ADR-007 | 1 Tag |
| 2.4 | Auto-Fix-Rules in DB | ADR-008 | 1.5 Tage |

### Priorität 3: EMPFOHLEN (spätere Iteration)

| # | Maßnahme | ADR | Aufwand |
|---|----------|-----|---------|
| 3.1 | RLS für Infrastructure | ADR-008 | 1 Tag |
| 3.2 | Cross-Service Event-Bus | Alle | 3 Tage |
| 3.3 | Zentrale Property-Definition | ADR-003 | 2 Tage |

---

## Teil 6: Architektur-Referenz (Konsolidiert)

### Einheitliche Naming Conventions

```markdown
## Database Objects

### Tabellen
- Pattern: `{app}_{entity}`
- Beispiele: `core_tenant`, `cadhub_cad_model`, `infra_service_definition`

### Constraints
- CHECK: `chk_{table}_{description}`
- UNIQUE: `uq_{table}_{fields}`
- FK: `fk_{table}_{referenced_table}`

### Indexes
- Pattern: `idx_{table}_{fields}`
- Beispiel: `idx_membership_user_tenant`

## Python Code

### Models
- Pattern: `{Entity}` oder `{Entity}Model` bei Kollision
- Beispiel: `Tenant`, `CADModelRecord`

### Services
- Pattern: `{Domain}{Action}Service`
- Beispiel: `CADGenerationService`, `AuthorizationService`

### Handlers
- Pattern: `{Action}{Entity}Handler`
- Beispiel: `GenerateCADHandler`, `CreateTenantHandler`

### Repositories
- Pattern: `{Entity}Repository`
- Beispiel: `TenantRepository`, `CADModelRepository`

## Enums
- Pattern: `{Domain}{Type}`
- Beispiel: `CADObjectType`, `TenantStatus`, `DeploymentStatus`
```

### Einheitliche Layer-Struktur

```
┌─────────────────────────────────────────────────────────────────────────┐
│ PRESENTATION (Views, API, MCP)                                          │
│ - HTTP Handling, Serialization, Auth Decorators                         │
├─────────────────────────────────────────────────────────────────────────┤
│ APPLICATION (Handlers)                                                   │
│ - Use Case Orchestration, Command/Result Pattern                        │
│ - Transaction Boundaries                                                 │
├─────────────────────────────────────────────────────────────────────────┤
│ DOMAIN (Services)                                                        │
│ - Business Logic, Domain Rules, Validation                              │
│ - NO external dependencies                                               │
├─────────────────────────────────────────────────────────────────────────┤
│ INFRASTRUCTURE (Repositories, Adapters, Cache)                          │
│ - Data Access, External Services, Caching                               │
│ - Technology-specific implementations                                    │
├─────────────────────────────────────────────────────────────────────────┤
│ DATABASE (PostgreSQL)                                                    │
│ - RLS, Constraints, Triggers, Indexes                                   │
│ - Data Integrity, Isolation, Enforcement                                │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Fazit

Die ADRs zeigen eine **ambitionierte und durchdachte Architektur**, die jedoch vor der Implementierung **Harmonisierung** benötigt:

1. **ADR-003** verstößt gegen die eigenen Prinzipien (JSONB-Overuse) und muss überarbeitet werden
2. **ADR-007** ist das Referenz-Dokument und sollte als Template dienen
3. **ADR-008** muss stärker an die Database-First-Philosophie angepasst werden
4. **Cross-ADR-Konsistenz** bei Naming und Patterns muss hergestellt werden

**Empfehlung:** Vor Implementierungsbeginn ein konsolidiertes "Platform Architecture Guidelines" Dokument erstellen, das die gemeinsamen Patterns verbindlich festlegt.

---

**Erstellt:** 2026-02-02  
**Reviewer:** IT-Architekt  
**Status:** Review abgeschlossen - Überarbeitung empfohlen
