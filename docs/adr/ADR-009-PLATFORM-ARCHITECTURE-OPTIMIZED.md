---
status: proposed
date: 2026-02-21
decision-makers: Achim Dehnert
---

# ADR-009: Platform Architecture - Optimized

**Status:** PROPOSED  
**Version:** 1.0  
**Datum:** 2026-02-02  
**Autoren:** Platform Architecture Team  
**Basis:** ADR-003, ADR-007, ADR-008 + Architecture Review

---

## Executive Summary

Konsolidiertes, optimiertes Architekturkonzept mit strikter Einhaltung der Kernprinzipien.

### Kernprinzipien

| Prinzip | Umsetzung |
|---------|-----------|
| **Database-First** | Constraints, RLS, Triggers in PostgreSQL |
| **Strikte Normalisierung** | Kein JSONB für kritische Daten, 3NF |
| **FK als Integer** | Surrogate Keys für Performance |
| **Naming Conventions** | `{app}_{entity}` für Tabellen |
| **Separation of Concerns** | 5-Layer-Architektur |
| **Handler-Pattern** | Command/Result mit Pydantic |

---

## 1. Database Schema (Normalisiert)

### 1.1 Naming Conventions

```sql
-- Tabellen: {app}_{entity}
-- Spalten: snake_case
-- PK: id (INTEGER SERIAL)
-- FK: {table}_id (INTEGER)
-- CHECK: chk_{table}_{desc}
-- UNIQUE: uq_{table}_{fields}
-- INDEX: idx_{table}_{fields}
```

### 1.2 Core Schema

```sql
-- Plan (Stammdaten)
CREATE TABLE core_plan (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    max_users INTEGER NOT NULL DEFAULT 5,
    CONSTRAINT chk_plan_max_users CHECK (max_users > 0)
);

-- Tenant
CREATE TABLE core_tenant (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    plan_id INTEGER NOT NULL REFERENCES core_plan(id),
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_tenant_status CHECK (status IN ('active', 'suspended', 'deleted'))
);

CREATE INDEX idx_tenant_slug ON core_tenant(slug);

-- User
CREATE TABLE core_user (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Role (Stammdaten)
CREATE TABLE core_role (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL
);

-- Permission (Stammdaten)
CREATE TABLE core_permission (
    id SERIAL PRIMARY KEY,
    code VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(50) NOT NULL
);

-- Role-Permission (M:N)
CREATE TABLE core_role_permission (
    id SERIAL PRIMARY KEY,
    role_id INTEGER NOT NULL REFERENCES core_role(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES core_permission(id) ON DELETE CASCADE,
    CONSTRAINT uq_role_permission UNIQUE (role_id, permission_id)
);

-- Membership
CREATE TABLE core_tenant_membership (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES core_tenant(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES core_user(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES core_role(id),
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    CONSTRAINT uq_membership UNIQUE (tenant_id, user_id)
);

CREATE INDEX idx_membership_tenant ON core_tenant_membership(tenant_id);
```

### 1.3 CAD-Hub Schema

```sql
-- Project
CREATE TABLE cadhub_project (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES core_tenant(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by_id INTEGER NOT NULL REFERENCES core_user(id),
    CONSTRAINT uq_project_tenant_name UNIQUE (tenant_id, name)
);

-- CAD Model
CREATE TABLE cadhub_cad_model (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES cadhub_project(id) ON DELETE CASCADE,
    version INTEGER NOT NULL DEFAULT 1,
    name VARCHAR(255) NOT NULL,
    source_format VARCHAR(20) NOT NULL,
    ifc_schema VARCHAR(20),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_model_format CHECK (source_format IN ('ifc', 'dxf', 'step', 'stl'))
);

-- Floor (IfcBuildingStorey)
CREATE TABLE cadhub_floor (
    id SERIAL PRIMARY KEY,
    cad_model_id INTEGER NOT NULL REFERENCES cadhub_cad_model(id) ON DELETE CASCADE,
    ifc_guid VARCHAR(36) NOT NULL,
    name VARCHAR(100) NOT NULL,
    elevation_m DECIMAL(10, 3) NOT NULL DEFAULT 0,
    CONSTRAINT uq_floor_guid UNIQUE (cad_model_id, ifc_guid)
);

-- Usage Category (DIN 277 - Stammdaten)
CREATE TABLE cadhub_usage_category (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    din_category VARCHAR(10) NOT NULL
);

-- Room (IfcSpace) - NORMALISIERT
CREATE TABLE cadhub_room (
    id SERIAL PRIMARY KEY,
    cad_model_id INTEGER NOT NULL REFERENCES cadhub_cad_model(id) ON DELETE CASCADE,
    floor_id INTEGER REFERENCES cadhub_floor(id),
    ifc_guid VARCHAR(36) NOT NULL,
    number VARCHAR(20) NOT NULL,
    name VARCHAR(100) NOT NULL,
    -- Geometrie (KEINE JSONB!)
    area_m2 DECIMAL(12, 3) NOT NULL DEFAULT 0,
    height_m DECIMAL(10, 3) NOT NULL DEFAULT 0,
    volume_m3 DECIMAL(12, 3) NOT NULL DEFAULT 0,
    perimeter_m DECIMAL(12, 3) NOT NULL DEFAULT 0,
    -- DIN 277 (FK Integer)
    usage_category_id INTEGER REFERENCES cadhub_usage_category(id),
    CONSTRAINT chk_room_area CHECK (area_m2 >= 0)
);

CREATE INDEX idx_room_model ON cadhub_room(cad_model_id);

-- Unit (Stammdaten)
CREATE TABLE cadhub_unit (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    symbol VARCHAR(20) NOT NULL
);

-- Property Definition (IFC PropertySets - Stammdaten)
CREATE TABLE cadhub_property_definition (
    id SERIAL PRIMARY KEY,
    code VARCHAR(150) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    data_type VARCHAR(20) NOT NULL,
    default_unit_id INTEGER REFERENCES cadhub_unit(id),
    CONSTRAINT chk_property_type CHECK (data_type IN ('text', 'numeric', 'boolean'))
);

-- Element Property (NORMALISIERT statt JSONB)
CREATE TABLE cadhub_element_property (
    id SERIAL PRIMARY KEY,
    element_type VARCHAR(20) NOT NULL,
    element_id INTEGER NOT NULL,
    property_definition_id INTEGER NOT NULL REFERENCES cadhub_property_definition(id),
    value_text TEXT,
    value_numeric DECIMAL(20, 6),
    value_boolean BOOLEAN,
    CONSTRAINT uq_element_prop UNIQUE (element_type, element_id, property_definition_id),
    CONSTRAINT chk_has_value CHECK (
        value_text IS NOT NULL OR value_numeric IS NOT NULL OR value_boolean IS NOT NULL
    )
);

CREATE INDEX idx_prop_element ON cadhub_element_property(element_type, element_id);

-- Window (IfcWindow) - NORMALISIERT
CREATE TABLE cadhub_window (
    id SERIAL PRIMARY KEY,
    cad_model_id INTEGER NOT NULL REFERENCES cadhub_cad_model(id) ON DELETE CASCADE,
    floor_id INTEGER REFERENCES cadhub_floor(id),
    ifc_guid VARCHAR(36) NOT NULL,
    number VARCHAR(50),
    name VARCHAR(100),
    width_m DECIMAL(10, 3),
    height_m DECIMAL(10, 3),
    area_m2 DECIMAL(10, 3),
    u_value_w_m2k DECIMAL(5, 2),
    material VARCHAR(100)
);

-- Door (IfcDoor) - NORMALISIERT  
CREATE TABLE cadhub_door (
    id SERIAL PRIMARY KEY,
    cad_model_id INTEGER NOT NULL REFERENCES cadhub_cad_model(id) ON DELETE CASCADE,
    floor_id INTEGER REFERENCES cadhub_floor(id),
    ifc_guid VARCHAR(36) NOT NULL,
    number VARCHAR(50),
    width_m DECIMAL(10, 3),
    height_m DECIMAL(10, 3),
    fire_rating VARCHAR(20)
);

-- Wall (IfcWall) - NORMALISIERT
CREATE TABLE cadhub_wall (
    id SERIAL PRIMARY KEY,
    cad_model_id INTEGER NOT NULL REFERENCES cadhub_cad_model(id) ON DELETE CASCADE,
    floor_id INTEGER REFERENCES cadhub_floor(id),
    ifc_guid VARCHAR(36) NOT NULL,
    length_m DECIMAL(10, 3),
    height_m DECIMAL(10, 3),
    thickness_m DECIMAL(10, 3),
    gross_area_m2 DECIMAL(10, 3),
    net_area_m2 DECIMAL(10, 3),
    is_external BOOLEAN NOT NULL DEFAULT false,
    is_load_bearing BOOLEAN NOT NULL DEFAULT false
);

-- Slab (IfcSlab) - NORMALISIERT
CREATE TABLE cadhub_slab (
    id SERIAL PRIMARY KEY,
    cad_model_id INTEGER NOT NULL REFERENCES cadhub_cad_model(id) ON DELETE CASCADE,
    floor_id INTEGER REFERENCES cadhub_floor(id),
    ifc_guid VARCHAR(36) NOT NULL,
    slab_type VARCHAR(20) NOT NULL DEFAULT 'FLOOR',
    area_m2 DECIMAL(10, 3),
    thickness_m DECIMAL(10, 3),
    volume_m3 DECIMAL(10, 3),
    CONSTRAINT chk_slab_type CHECK (slab_type IN ('FLOOR', 'ROOF', 'BASESLAB'))
);
```

### 1.4 Infrastructure Schema

```sql
-- Service Definition (Database-Driven Registry)
CREATE TABLE infra_service (
    id SERIAL PRIMARY KEY,
    code VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    service_type VARCHAR(50) NOT NULL,
    domain VARCHAR(255) NOT NULL UNIQUE,
    cpu_cores INTEGER NOT NULL DEFAULT 1,
    memory_mb INTEGER NOT NULL DEFAULT 512,
    is_active BOOLEAN NOT NULL DEFAULT true,
    CONSTRAINT chk_service_type CHECK (service_type IN ('django', 'fastapi', 'static', 'mcp'))
);

-- Auto-Fix Rules (Database-Driven)
CREATE TABLE infra_auto_fix_rule (
    id SERIAL PRIMARY KEY,
    code VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    error_pattern TEXT NOT NULL,
    fix_type VARCHAR(50) NOT NULL,
    confidence_threshold INTEGER NOT NULL DEFAULT 85,
    allowed_in_production BOOLEAN NOT NULL DEFAULT false,
    is_active BOOLEAN NOT NULL DEFAULT true,
    CONSTRAINT chk_fix_type CHECK (fix_type IN ('restart', 'rollback', 'scale_up'))
);

-- Deployment Event (Audit)
CREATE TABLE infra_deployment_event (
    id SERIAL PRIMARY KEY,
    service_id INTEGER NOT NULL REFERENCES infra_service(id),
    git_sha VARCHAR(40) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    CONSTRAINT chk_deploy_status CHECK (status IN ('pending', 'running', 'success', 'failed'))
);
```

### 1.5 Row Level Security

```sql
ALTER TABLE cadhub_project ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON cadhub_project
    USING (tenant_id = current_setting('app.current_tenant_id', true)::integer);
```

---

## 2. Python Architecture

### 2.1 Layer Structure

```
PRESENTATION → APPLICATION → DOMAIN → INFRASTRUCTURE → DATABASE
   (Views)      (Handlers)   (Services) (Repositories)   (PostgreSQL)
```

### 2.2 Pydantic Commands/Results

```python
from pydantic import BaseModel, Field, ConfigDict

class ParseIFCCommand(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)
    
    file_path: str = Field(..., min_length=1)
    project_id: int = Field(..., gt=0)
    tenant_id: int = Field(..., gt=0)
    user_id: int = Field(..., gt=0)

class ParseIFCResult(BaseModel):
    model_id: int
    room_count: int = Field(..., ge=0)
    window_count: int = Field(..., ge=0)
    total_area_m2: Decimal
    errors: list[str] = Field(default_factory=list)
```

### 2.3 Handler Pattern

```python
class ParseIFCHandler:
    def __init__(
        self,
        ifc_service: IFCDomainService,
        model_repo: CADModelRepository,
    ) -> None:
        self._ifc_service = ifc_service
        self._model_repo = model_repo
    
    def execute(self, command: ParseIFCCommand) -> ParseIFCResult:
        with transaction.atomic():
            result = self._ifc_service.parse_file(command.file_path)
            model = self._model_repo.create(...)
            return ParseIFCResult(model_id=model.id, ...)
```

---

## 3. MCP Server Integration

```python
from mcp.server import Server
from mcp.types import Tool

server = Server("cadhub-mcp")

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(name="parse_ifc", description="Parse IFC file", ...),
        Tool(name="list_rooms", description="List rooms", ...),
        Tool(name="list_windows", description="Fensterliste", ...),
        Tool(name="calculate_enclosed_volume", description="Umbauter Raum (BRI)", ...),
        Tool(name="calculate_woflv", description="WoFlV Berechnung", ...),
    ]
```

### MCP Config (WSL)

```json
{
  "mcpServers": {
    "cadhub": {
      "command": "wsl",
      "args": ["-e", "python", "-m", "cadhub.mcp.server"]
    }
  }
}
```

---

## 4. Naming Conventions

| Objekt | Pattern | Beispiel |
|--------|---------|----------|
| **DB Tabelle** | `{app}_{entity}` | `cadhub_room` |
| **DB Spalte** | `snake_case` | `area_m2` |
| **PK** | `id` (INTEGER) | `id SERIAL` |
| **FK** | `{table}_id` | `tenant_id` |
| **Python Klasse** | `PascalCase` | `ParseIFCHandler` |
| **Python Funktion** | `snake_case` | `calculate_volume` |
| **Handler** | `{Action}{Entity}Handler` | `GenerateCADHandler` |
| **Service** | `{Domain}Service` | `IFCDomainService` |
| **Repository** | `{Entity}Repository` | `RoomRepository` |

---

## 5. Compliance Checklist

- [x] **Database-First**: Alle Constraints in PostgreSQL
- [x] **Normalisierung**: Kein JSONB für Properties
- [x] **FK Integer**: Surrogate Keys für alle FKs
- [x] **Naming**: Konsistente Konventionen
- [x] **SoC**: 5-Layer-Architektur
- [x] **Handler**: Command/Result mit Pydantic
- [x] **MCP**: WSL-Integration dokumentiert
- [x] **RLS**: Tenant-Isolation

---

**Status:** Ready for Implementation
