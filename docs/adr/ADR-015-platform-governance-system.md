# ADR-015: Platform Governance System

| Metadata | Value |
|----------|-------|
| **Status** | Proposed |
| **Date** | 2026-02-03 |
| **Author** | Achim Dehnert |
| **Scope** | core |
| **Reviewers** | — |
| **Supersedes** | — |
| **Related** | ADR-012 (MCP Quality), ADR-014 (AI-Native Teams) |

---

## 1. Executive Summary

Dieses ADR etabliert ein **vollständiges Platform Governance System**, das sicherstellt, dass:

1. **Keine Duplikate** - Existierende Packages, Services, Handlers und Agents werden wiederverwendet
2. **Database-Driven Choices** - Keine hardcoded Enums, alle Auswahllisten aus Lookup Tables
3. **Kontrollierter Zugriff** - LLMs, externe APIs und Infrastruktur nur über definierte Gateways
4. **Konsistente Standards** - Naming Conventions und Patterns werden automatisch enforced
5. **Vollständige Nachvollziehbarkeit** - Audit Trail für alle Governance-Entscheidungen

**Kernprinzip:** *"Alles, was in der Datenbank definiert ist, wird auch enforced."*

---

## 2. Context

### 2.1 Problem Statement

| Problem | Impact | Häufigkeit |
|---------|--------|------------|
| AI-Agent vergisst existierende Services | Doppelte Implementierungen, Inkonsistenz | Täglich |
| Hardcoded Enums statt DB Lookups | Code-Änderung für neue Optionen nötig | Wöchentlich |
| Direkte OpenAI/Anthropic API Calls | Keine Kostenkontrolle, inkonsistentes Error Handling | Häufig |
| Direkte Redis/DB Zugriffe | Umgehung von Service-Layern, Sicherheitsrisiken | Gelegentlich |
| Inkonsistente Naming Conventions | Schwer lesbarer/wartbarer Code | Ständig |
| Fehlende Pattern-Nutzung | Inkonsistentes Error Handling/Logging | Häufig |

### 2.2 Anforderungen

| ID | Anforderung | Priorität | Kategorie |
|----|-------------|-----------|-----------|
| R1 | Zentrale Registry für alle Platform-Komponenten | CRITICAL | Discovery |
| R2 | Database-driven Lookup Tables statt Enums | CRITICAL | Data Model |
| R3 | Automatische Erkennung von Duplikaten | CRITICAL | Enforcement |
| R4 | Import-Regeln für verbotene direkte Zugriffe | HIGH | Enforcement |
| R5 | Naming Convention Enforcement | HIGH | Standards |
| R6 | Pattern Enforcement (Error Handling, Logging) | HIGH | Standards |
| R7 | LLM Gateway für alle AI-Aufrufe | HIGH | Access Control |
| R8 | CI/CD Integration für automatische Prüfung | HIGH | Automation |
| R9 | Vollständiger Audit Trail | MEDIUM | Compliance |
| R10 | Runtime Enforcement | MEDIUM | Enforcement |

### 2.3 Design-Prinzipien

| Prinzip | Beschreibung |
|---------|--------------|
| **Database-First** | Alle Konfiguration in der Datenbank, nicht im Code |
| **Strict Normalization** | 3NF, keine Redundanz, referentielle Integrität |
| **Convention over Configuration** | Sinnvolle Defaults, Ausnahmen explizit |
| **Fail-Fast** | Verstöße früh erkennen (CI/CD, Pre-Commit) |
| **Defense in Depth** | Mehrere Enforcement-Layer |
| **Audit Everything** | Vollständige Nachvollziehbarkeit |

---

## 3. Decision

### 3.1 Architektur-Übersicht

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    PLATFORM GOVERNANCE ARCHITECTURE                      │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│                    ┌──────────────────────────────────┐                  │
│                    │      PostgreSQL Database         │                  │
│                    │      schema: platform            │                  │
│                    └──────────────────┬───────────────┘                  │
│                                       │                                  │
│         ┌─────────────────────────────┼─────────────────────────────┐   │
│         │                             │                             │   │
│         ▼                             ▼                             ▼   │
│  ┌─────────────────┐        ┌─────────────────┐        ┌─────────────────┐
│  │  LOOKUP TABLES  │        │    REGISTRY     │        │  GOVERNANCE     │
│  │                 │        │                 │        │  RULES          │
│  │  lkp_domain     │        │  reg_package    │        │                 │
│  │  lkp_choice     │        │  reg_module     │        │  gov_access_rule│
│  │                 │        │  reg_class      │        │  gov_import_rule│
│  │  • status       │        │  reg_mcp_server │        │  gov_naming_rule│
│  │  • priority     │        │  reg_mcp_tool   │        │  gov_pattern_rule│
│  │  • llm_model    │        │  reg_handler    │        │                 │
│  │  • llm_provider │        │  reg_agent      │        │  gov_enforcement│
│  │  • gate_level   │        │  reg_service    │        │  _log           │
│  │  • ...          │        │  reg_pattern    │        │                 │
│  └────────┬────────┘        └────────┬────────┘        └────────┬────────┘
│           │                          │                          │        │
│           └──────────────────────────┼──────────────────────────┘        │
│                                      │                                   │
│                                      ▼                                   │
│           ┌──────────────────────────────────────────────────────┐      │
│           │                 ENFORCEMENT LAYER                     │      │
│           │                                                       │      │
│           │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │      │
│           │  │ registry_mcp│  │  CI/CD      │  │  Runtime    │   │      │
│           │  │             │  │  Validator  │  │  Guards     │   │      │
│           │  │ AI Agent    │  │             │  │             │   │      │
│           │  │ Discovery   │  │ PR Checks   │  │ Import Hook │   │      │
│           │  │             │  │ Pre-Commit  │  │ Access Check│   │      │
│           │  └─────────────┘  └─────────────┘  └─────────────┘   │      │
│           │                                                       │      │
│           └───────────────────────────┬──────────────────────────┘      │
│                                       │                                  │
│                                       ▼                                  │
│           ┌──────────────────────────────────────────────────────┐      │
│           │                  SERVICE LAYER                        │      │
│           │                                                       │      │
│           │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │      │
│           │  │LookupService│  │ Governance  │  │ LLMGateway  │   │      │
│           │  │             │  │ Service     │  │             │   │      │
│           │  │get_choices()│  │check_import │  │ generate()  │   │      │
│           │  │get_choice() │  │check_access │  │ chat()      │   │      │
│           │  │validate()   │  │check_naming │  │ embed()     │   │      │
│           │  └─────────────┘  └─────────────┘  └─────────────┘   │      │
│           │                                                       │      │
│           └──────────────────────────────────────────────────────┘      │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Komponenten-Übersicht

| Komponente | Typ | Zweck |
|------------|-----|-------|
| **Lookup Tables** | Database | Zentrale Verwaltung aller Choices |
| **Registry Tables** | Database | Katalog aller Platform-Komponenten |
| **Governance Rules** | Database | Regeln für Imports, Access, Naming |
| **LookupService** | Python Service | API für Lookup-Zugriff |
| **GovernanceService** | Python Service | Enforcement-Logik |
| **LLMGateway** | Python Service | Zentraler LLM-Zugriff |
| **registry_mcp** | MCP Server | AI Agent Discovery |
| **governance_check.py** | CI/CD Script | Automatische PR-Prüfung |

---

## 4. Naming Conventions

### 4.1 Database Objects

| Element | Format | Beispiele |
|---------|--------|-----------|
| Schema | snake_case | `platform`, `platform_registry` |
| Tables | `{prefix}_{entity}` (singular) | `lkp_choice`, `reg_package`, `gov_access_rule` |
| Columns | snake_case (no prefix) | `id`, `name`, `created_at` |
| Primary Keys | `id` (BIGINT IDENTITY) | `id` |
| Foreign Keys | `{referenced_table}_id` | `package_id`, `status_id` |
| Indexes | `idx_{table}_{columns}` | `idx_lkp_choice_domain` |
| Constraints | `{type}_{table}_{desc}` | `pk_lkp_choice`, `fk_reg_module_package` |
| Views | `{prefix}_v_{description}` | `lkp_v_active_choices` |
| Functions | `{prefix}_{action}_{subject}` | `lkp_get_choices`, `reg_search` |

### 4.2 Table Prefixes

| Prefix | Bedeutung | Beispiele |
|--------|-----------|-----------|
| `lkp_` | Lookup Tables | `lkp_domain`, `lkp_choice` |
| `reg_` | Registry Tables | `reg_package`, `reg_mcp_server` |
| `gov_` | Governance Rules | `gov_access_rule`, `gov_import_rule` |

### 4.3 Python Code

| Element | Format | Beispiele |
|---------|--------|-----------|
| Packages | snake_case | `platform_core`, `mcp_core` |
| Modules | snake_case | `rate_limiting`, `error_handling` |
| Classes | PascalCase | `RateLimiter`, `CacheService` |
| Functions | snake_case (verb_noun) | `get_user`, `create_document` |
| Constants | UPPER_SNAKE | `MAX_RETRIES`, `DEFAULT_TIMEOUT` |
| MCP Servers | snake_case with `_mcp` suffix | `llm_mcp`, `registry_mcp` |
| MCP Tools | snake_case (verb_noun) | `search_functionality`, `list_packages` |

### 4.4 Fully Qualified Names (FQN)

| Typ | Format | Beispiel |
|-----|--------|----------|
| Package Class | `{package}.{module}.{class}` | `platform_core.caching.CacheService` |
| MCP Tool | `{server}:{tool}` | `llm_mcp:generate_text` |
| Pattern | `pattern:{code}` | `pattern:error_handling` |

---

## 5. Database Schema

### 5.1 Entity Relationship Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         ENTITY RELATIONSHIPS                             │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  LOOKUP TABLES                                                          │
│  ═════════════                                                           │
│                                                                          │
│  lkp_domain ─────────< lkp_choice                                       │
│       │                    │                                             │
│       │                    └──── (self-reference for hierarchy)         │
│       │                                                                  │
│       └──── used_in_tables[] → describes usage                          │
│                                                                          │
│  ────────────────────────────────────────────────────────────────────── │
│                                                                          │
│  REGISTRY TABLES                                                        │
│  ═══════════════                                                         │
│                                                                          │
│  reg_package ────────< reg_module ────────< reg_class                   │
│       │                                         │                        │
│       ├── status_id ──────┐                     └── class_type_id       │
│       ├── owner_id ───────┼──> lkp_choice                               │
│       └── category_id ────┘                                              │
│                                                                          │
│  reg_mcp_server ────────< reg_mcp_tool                                  │
│       │                                                                  │
│       ├── status_id ──────┐                                              │
│       ├── owner_id ───────┼──> lkp_choice                               │
│       └── category_id ────┘                                              │
│       │                                                                  │
│       └────< reg_mcp_server_antipattern                                 │
│                                                                          │
│  reg_handler ──────> handler_type_id, status_id, owner_id → lkp_choice  │
│  reg_agent ────────> status_id, owner_id, default_model_id → lkp_choice │
│  reg_service ──────> service_type_id, status_id, owner_id → lkp_choice  │
│  reg_pattern ──────> category_id → lkp_choice                           │
│                                                                          │
│  reg_integration ────────< reg_integration_accessor                     │
│                                                                          │
│  ────────────────────────────────────────────────────────────────────── │
│                                                                          │
│  GOVERNANCE TABLES                                                      │
│  ═════════════════                                                       │
│                                                                          │
│  gov_access_rule ──────> enforcement_id → lkp_choice                    │
│  gov_import_rule ──────> enforcement_id → lkp_choice                    │
│  gov_naming_rule ──────> enforcement_id → lkp_choice                    │
│  gov_pattern_rule ─────> enforcement_id → lkp_choice                    │
│                                                                          │
│  gov_enforcement_log (audit trail)                                      │
│  reg_audit_log (registry changes)                                       │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Lookup Tables

```sql
-- ============================================================================
-- LOOKUP TABLES - Database-Driven Choices
-- ============================================================================
-- RULE: NO HARDCODED ENUMS IN CODE! Use these tables instead.

CREATE SCHEMA IF NOT EXISTS platform;

-- Domain definitions
CREATE TABLE platform.lkp_domain (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code            VARCHAR(50) NOT NULL UNIQUE,
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    allow_hierarchy BOOLEAN NOT NULL DEFAULT false,
    allow_custom    BOOLEAN NOT NULL DEFAULT false,
    cache_ttl       INTEGER DEFAULT 3600,
    used_in_tables  TEXT[],
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Choice values
CREATE TABLE platform.lkp_choice (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    domain_id       BIGINT NOT NULL REFERENCES platform.lkp_domain(id),
    domain          VARCHAR(50) NOT NULL,
    code            VARCHAR(50) NOT NULL,
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    parent_id       BIGINT REFERENCES platform.lkp_choice(id),
    sort_order      INTEGER NOT NULL DEFAULT 0,
    icon            VARCHAR(50),
    color           VARCHAR(20),
    is_active       BOOLEAN NOT NULL DEFAULT true,
    is_default      BOOLEAN NOT NULL DEFAULT false,
    is_system       BOOLEAN NOT NULL DEFAULT false,
    valid_from      DATE,
    valid_until     DATE,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_lkp_choice_domain_code UNIQUE (domain, code),
    CONSTRAINT ck_lkp_choice_valid_dates CHECK (
        valid_from IS NULL OR valid_until IS NULL OR valid_from <= valid_until
    )
);

CREATE INDEX idx_lkp_choice_domain ON platform.lkp_choice (domain, is_active, sort_order);
```

### 5.3 Pre-Defined Lookup Domains

| Domain | Beschreibung | Beispiel-Werte |
|--------|--------------|----------------|
| `status` | Component lifecycle | planned, development, beta, production, deprecated |
| `priority` | Task/Issue priority | critical, high, medium, low |
| `owner` | Team ownership | architect, alpha, bravo, guild |
| `category` | Component categories | core, integration, utility, domain |
| `environment` | Deployment environments | local, development, staging, production |
| `llm_model` | Available LLM models | claude-opus-4-5, claude-sonnet-4-5, gpt-4o |
| `llm_provider` | LLM providers | anthropic, openai, azure_openai |
| `gate_level` | Approval gates (ADR-014) | autonomous, async, explicit, synchronous, human_initiated |
| `enforcement` | Rule enforcement | block, warn, log |
| `handler_type` | Handler types | event, request, signal, task, webhook |
| `service_type` | Service types | internal, external, hybrid |
| `class_type` | Python class types | class, function, decorator, constant |

### 5.4 LLM Model Configuration (Lookup Data)

```sql
-- LLM Models with metadata for cost calculation and routing
INSERT INTO platform.lkp_choice (domain_id, domain, code, name, metadata, sort_order) VALUES
(
    (SELECT id FROM platform.lkp_domain WHERE code = 'llm_model'),
    'llm_model', 
    'claude-opus-4-5', 
    'Claude Opus 4.5',
    '{
        "provider": "anthropic",
        "model_id": "claude-opus-4-5-20250514",
        "context_window": 200000,
        "cost_input": 15.0,
        "cost_output": 75.0,
        "tier": "premium",
        "capabilities": ["reasoning", "coding", "analysis", "creative"]
    }',
    10
),
(
    (SELECT id FROM platform.lkp_domain WHERE code = 'llm_model'),
    'llm_model',
    'claude-sonnet-4-5',
    'Claude Sonnet 4.5',
    '{
        "provider": "anthropic",
        "model_id": "claude-sonnet-4-5-20250514",
        "context_window": 200000,
        "cost_input": 3.0,
        "cost_output": 15.0,
        "tier": "standard",
        "capabilities": ["coding", "analysis", "general"]
    }',
    20
),
(
    (SELECT id FROM platform.lkp_domain WHERE code = 'llm_model'),
    'llm_model',
    'claude-haiku-4-5',
    'Claude Haiku 4.5',
    '{
        "provider": "anthropic",
        "model_id": "claude-haiku-4-5-20250514",
        "context_window": 200000,
        "cost_input": 0.25,
        "cost_output": 1.25,
        "tier": "economy",
        "capabilities": ["fast", "simple-tasks"]
    }',
    30
);
```

### 5.5 Registry Tables

```sql
-- ============================================================================
-- REGISTRY TABLES - Platform Component Catalog
-- ============================================================================

-- Python Packages
CREATE TABLE platform.reg_package (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            VARCHAR(100) NOT NULL UNIQUE,
    pypi_name       VARCHAR(100) UNIQUE,
    version         VARCHAR(20),
    description     TEXT NOT NULL,
    long_description TEXT,
    repository      VARCHAR(200) NOT NULL DEFAULT 'platform',
    path            VARCHAR(500) NOT NULL,
    category_id     BIGINT NOT NULL REFERENCES platform.lkp_choice(id),
    status_id       BIGINT NOT NULL REFERENCES platform.lkp_choice(id),
    owner_id        BIGINT NOT NULL REFERENCES platform.lkp_choice(id),
    search_vector   TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(description, '')), 'B')
    ) STORED,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Package Modules
CREATE TABLE platform.reg_module (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    package_id      BIGINT NOT NULL REFERENCES platform.reg_package(id) ON DELETE CASCADE,
    name            VARCHAR(100) NOT NULL,
    fqn             VARCHAR(300) NOT NULL UNIQUE,
    description     TEXT NOT NULL,
    search_vector   TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(description, '')), 'B')
    ) STORED,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_reg_module_package_name UNIQUE (package_id, name)
);

-- Module Classes/Functions
CREATE TABLE platform.reg_class (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    module_id       BIGINT NOT NULL REFERENCES platform.reg_module(id) ON DELETE CASCADE,
    name            VARCHAR(100) NOT NULL,
    fqn             VARCHAR(500) NOT NULL UNIQUE,
    class_type_id   BIGINT NOT NULL REFERENCES platform.lkp_choice(id),
    description     TEXT NOT NULL,
    usage_example   TEXT,
    import_statement TEXT,
    search_vector   TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(description, '')), 'B')
    ) STORED,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_reg_class_module_name UNIQUE (module_id, name)
);

-- MCP Servers
CREATE TABLE platform.reg_mcp_server (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            VARCHAR(100) NOT NULL UNIQUE,
    display_name    VARCHAR(200),
    description     TEXT NOT NULL,
    when_to_use     TEXT,
    repository      VARCHAR(200) NOT NULL DEFAULT 'mcp-hub',
    path            VARCHAR(500) NOT NULL,
    category_id     BIGINT NOT NULL REFERENCES platform.lkp_choice(id),
    status_id       BIGINT NOT NULL REFERENCES platform.lkp_choice(id),
    owner_id        BIGINT NOT NULL REFERENCES platform.lkp_choice(id),
    port            INTEGER,
    requires_auth   BOOLEAN NOT NULL DEFAULT false,
    search_vector   TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(description, '')), 'B')
    ) STORED,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- MCP Tools
CREATE TABLE platform.reg_mcp_tool (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    server_id       BIGINT NOT NULL REFERENCES platform.reg_mcp_server(id) ON DELETE CASCADE,
    name            VARCHAR(100) NOT NULL,
    fqn             VARCHAR(300) NOT NULL UNIQUE,
    description     TEXT NOT NULL,
    parameters      JSONB DEFAULT '{}',
    usage_example   TEXT,
    search_vector   TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(description, '')), 'B')
    ) STORED,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_reg_mcp_tool_server_name UNIQUE (server_id, name)
);

-- MCP Server Antipatterns (DO NOT REIMPLEMENT)
CREATE TABLE platform.reg_mcp_server_antipattern (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    server_id       BIGINT NOT NULL REFERENCES platform.reg_mcp_server(id) ON DELETE CASCADE,
    description     TEXT NOT NULL,
    reason          TEXT,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Event Handlers
CREATE TABLE platform.reg_handler (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    fqn             VARCHAR(500) NOT NULL UNIQUE,
    handler_type_id BIGINT NOT NULL REFERENCES platform.lkp_choice(id),
    handles_event   VARCHAR(200),
    handles_pattern VARCHAR(500),
    description     TEXT NOT NULL,
    module_path     VARCHAR(500) NOT NULL,
    status_id       BIGINT NOT NULL REFERENCES platform.lkp_choice(id),
    owner_id        BIGINT NOT NULL REFERENCES platform.lkp_choice(id),
    is_async        BOOLEAN NOT NULL DEFAULT true,
    priority        INTEGER NOT NULL DEFAULT 100,
    max_retries     INTEGER DEFAULT 3,
    timeout_seconds INTEGER DEFAULT 30,
    search_vector   TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(handles_event, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(description, '')), 'B')
    ) STORED,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- AI Agents
CREATE TABLE platform.reg_agent (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    code            VARCHAR(50) NOT NULL UNIQUE,
    fqn             VARCHAR(500) NOT NULL UNIQUE,
    description     TEXT NOT NULL,
    capabilities    TEXT[],
    module_path     VARCHAR(500) NOT NULL,
    status_id       BIGINT NOT NULL REFERENCES platform.lkp_choice(id),
    owner_id        BIGINT NOT NULL REFERENCES platform.lkp_choice(id),
    default_model_id BIGINT REFERENCES platform.lkp_choice(id),
    allowed_models  BIGINT[],
    allowed_mcp_servers BIGINT[],
    max_iterations  INTEGER DEFAULT 10,
    timeout_seconds INTEGER DEFAULT 300,
    search_vector   TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(code, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(description, '')), 'B')
    ) STORED,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Internal Services
CREATE TABLE platform.reg_service (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    code            VARCHAR(50) NOT NULL UNIQUE,
    fqn             VARCHAR(500) NOT NULL UNIQUE,
    service_type_id BIGINT NOT NULL REFERENCES platform.lkp_choice(id),
    description     TEXT NOT NULL,
    module_path     VARCHAR(500) NOT NULL,
    status_id       BIGINT NOT NULL REFERENCES platform.lkp_choice(id),
    owner_id        BIGINT NOT NULL REFERENCES platform.lkp_choice(id),
    depends_on      BIGINT[],
    is_singleton    BOOLEAN NOT NULL DEFAULT true,
    requires_init   BOOLEAN NOT NULL DEFAULT false,
    direct_access_allowed BOOLEAN NOT NULL DEFAULT false,
    access_via_fqn  VARCHAR(500),
    search_vector   TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(code, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(description, '')), 'B')
    ) STORED,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Design Patterns
CREATE TABLE platform.reg_pattern (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    code            VARCHAR(50) NOT NULL UNIQUE,
    description     TEXT NOT NULL,
    implementation_fqn VARCHAR(500),
    usage_example   TEXT NOT NULL,
    category_id     BIGINT NOT NULL REFERENCES platform.lkp_choice(id),
    search_vector   TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(code, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(description, '')), 'B')
    ) STORED,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_reg_package_search ON platform.reg_package USING GIN (search_vector);
CREATE INDEX idx_reg_module_search ON platform.reg_module USING GIN (search_vector);
CREATE INDEX idx_reg_class_search ON platform.reg_class USING GIN (search_vector);
CREATE INDEX idx_reg_mcp_server_search ON platform.reg_mcp_server USING GIN (search_vector);
CREATE INDEX idx_reg_mcp_tool_search ON platform.reg_mcp_tool USING GIN (search_vector);
CREATE INDEX idx_reg_handler_search ON platform.reg_handler USING GIN (search_vector);
CREATE INDEX idx_reg_agent_search ON platform.reg_agent USING GIN (search_vector);
CREATE INDEX idx_reg_service_search ON platform.reg_service USING GIN (search_vector);
CREATE INDEX idx_reg_pattern_search ON platform.reg_pattern USING GIN (search_vector);
```

### 5.6 Governance Rules Tables

```sql
-- ============================================================================
-- GOVERNANCE RULES TABLES
-- ============================================================================

-- Access Rules (What can access what)
CREATE TABLE platform.gov_access_rule (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,
    code            VARCHAR(50) NOT NULL UNIQUE,
    description     TEXT,
    target_type     VARCHAR(30) NOT NULL CHECK (target_type IN ('service', 'integration', 'table', 'api', 'module')),
    target_pattern  VARCHAR(500) NOT NULL,
    allowed_accessors TEXT[] NOT NULL,
    access_method   TEXT NOT NULL,
    enforcement_id  BIGINT NOT NULL REFERENCES platform.lkp_choice(id),
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Import Rules (Forbidden imports)
CREATE TABLE platform.gov_import_rule (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,
    code            VARCHAR(50) NOT NULL UNIQUE,
    description     TEXT,
    forbidden_import VARCHAR(500) NOT NULL,
    import_pattern  VARCHAR(500),
    applies_to      TEXT[] DEFAULT ARRAY['*'],
    exceptions      TEXT[] DEFAULT ARRAY[]::TEXT[],
    alternative_fqn VARCHAR(500) NOT NULL,
    alternative_usage TEXT,
    enforcement_id  BIGINT NOT NULL REFERENCES platform.lkp_choice(id),
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Naming Convention Rules
CREATE TABLE platform.gov_naming_rule (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,
    code            VARCHAR(50) NOT NULL UNIQUE,
    description     TEXT,
    applies_to      VARCHAR(50) NOT NULL CHECK (applies_to IN ('class', 'function', 'variable', 'constant', 'table', 'column', 'module', 'package')),
    scope_pattern   VARCHAR(500),
    naming_pattern  VARCHAR(500) NOT NULL,
    naming_example  VARCHAR(200),
    enforcement_id  BIGINT NOT NULL REFERENCES platform.lkp_choice(id),
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Pattern Enforcement Rules
CREATE TABLE platform.gov_pattern_rule (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,
    code            VARCHAR(50) NOT NULL UNIQUE,
    description     TEXT,
    trigger_keywords TEXT[] NOT NULL,
    trigger_context TEXT,
    pattern_fqn     VARCHAR(500) NOT NULL,
    pattern_usage   TEXT NOT NULL,
    antipattern_regex VARCHAR(1000),
    enforcement_id  BIGINT NOT NULL REFERENCES platform.lkp_choice(id),
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Enforcement Log
CREATE TABLE platform.gov_enforcement_log (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    rule_type       VARCHAR(30) NOT NULL CHECK (rule_type IN ('access', 'import', 'naming', 'pattern', 'registry')),
    rule_code       VARCHAR(50) NOT NULL,
    file_path       VARCHAR(1000),
    line_number     INTEGER,
    code_snippet    TEXT,
    context         JSONB,
    action_taken    VARCHAR(20) NOT NULL CHECK (action_taken IN ('blocked', 'warned', 'logged', 'approved')),
    message         TEXT NOT NULL,
    detected_at     TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    detected_by     VARCHAR(50) NOT NULL,
    commit_sha      VARCHAR(40),
    pr_number       INTEGER,
    user_id         VARCHAR(100)
);

CREATE INDEX idx_gov_enforcement_log_time ON platform.gov_enforcement_log (detected_at DESC);
CREATE INDEX idx_gov_enforcement_log_rule ON platform.gov_enforcement_log (rule_type, rule_code);
CREATE INDEX idx_gov_enforcement_log_pr ON platform.gov_enforcement_log (pr_number) WHERE pr_number IS NOT NULL;
```

### 5.7 Pre-Defined Governance Rules

#### Access Rules

| Code | Target | Enforcement | Beschreibung |
|------|--------|-------------|--------------|
| `no_direct_openai` | `openai.*` | **BLOCK** | Use llm_mcp instead of direct OpenAI SDK |
| `no_direct_anthropic` | `anthropic.*` | **BLOCK** | Use llm_mcp instead of direct Anthropic SDK |
| `no_direct_redis` | `redis.*` | WARN | Use CacheService instead of direct Redis |
| `no_direct_stripe` | `stripe.*` | **BLOCK** | Use billing_service for payments |
| `no_raw_sql` | `cursor.execute` | WARN | Use Django ORM instead of raw SQL |

#### Import Rules

| Code | Forbidden Import | Alternative | Enforcement |
|------|------------------|-------------|-------------|
| `no_import_openai` | `import openai` | `llm_mcp` | **BLOCK** |
| `no_import_anthropic` | `import anthropic` | `llm_mcp` | **BLOCK** |
| `no_import_redis` | `import redis` | `platform_core.caching` | WARN |
| `no_import_requests` | `import requests` | `platform_core.http` | WARN |
| `no_enum_choices` | `class X(Enum)` | `LookupService` | WARN |

#### Naming Rules

| Code | Applies To | Pattern | Example | Enforcement |
|------|------------|---------|---------|-------------|
| `class_pascal` | class | `^[A-Z][a-zA-Z0-9]*$` | CacheService | WARN |
| `func_snake` | function | `^[a-z_][a-z0-9_]*$` | get_user | WARN |
| `const_upper` | constant | `^[A-Z][A-Z0-9_]*$` | MAX_RETRIES | WARN |
| `mcp_suffix` | module | `.*_mcp$` | llm_mcp | **BLOCK** |
| `handler_suffix` | class | `.*Handler$` | DocumentHandler | WARN |

#### Pattern Rules

| Code | Trigger Keywords | Required Pattern | Antipattern Regex |
|------|------------------|------------------|-------------------|
| `use_error_handler` | error, exception | `@error_handler` | `except.*:.*pass` |
| `use_cache_service` | cache, redis | `CacheService` | `redis\.(get\|set)` |
| `use_get_logger` | log, logger | `get_logger` | `logging\.getLogger` |

---

## 6. Django Implementation

### 6.1 LookupService

```python
# platform/apps/governance/services/lookup_service.py
"""
LookupService - Central access point for database-driven choices.

USE THIS instead of hardcoded Enums!

Example:
    # ❌ WRONG - Don't do this:
    class Status(Enum):
        PLANNED = 'planned'
        PRODUCTION = 'production'
    
    # ✅ RIGHT - Do this:
    from governance.services import LookupService
    
    statuses = LookupService.get_choices('status')
    status = LookupService.get_choice('status', 'production')
"""

from typing import Optional, Any
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone


class LookupService:
    """
    Service for accessing database-driven lookup values.
    All methods are class methods - no instantiation needed.
    """
    
    CACHE_PREFIX = 'lkp:'
    DEFAULT_CACHE_TTL = 3600
    
    @classmethod
    def get_choices(
        cls,
        domain: str,
        include_inactive: bool = False,
        parent_code: Optional[str] = None,
        as_dict: bool = False,
    ) -> list[dict] | dict[str, dict]:
        """
        Get all choices for a domain.
        
        Args:
            domain: The lookup domain (e.g., 'status', 'priority', 'llm_model')
            include_inactive: Include inactive choices
            parent_code: Filter by parent code (for hierarchical domains)
            as_dict: Return as dict keyed by code
        
        Returns:
            List of choice dictionaries, or dict if as_dict=True
        
        Example:
            statuses = LookupService.get_choices('status')
            # [{'code': 'planned', 'name': 'Planned', ...}, ...]
            
            models = LookupService.get_choices('llm_model', as_dict=True)
            # {'claude-opus-4-5': {'name': 'Claude Opus 4.5', ...}, ...}
        """
        from ..models import LookupChoice, LookupDomain
        
        cache_key = f"{cls.CACHE_PREFIX}{domain}:{include_inactive}:{parent_code}:{as_dict}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        
        queryset = LookupChoice.objects.filter(domain_code=domain)
        
        if not include_inactive:
            today = timezone.now().date()
            queryset = queryset.filter(is_active=True).filter(
                Q(valid_from__isnull=True) | Q(valid_from__lte=today)
            ).filter(
                Q(valid_until__isnull=True) | Q(valid_until__gte=today)
            )
        
        if parent_code:
            queryset = queryset.filter(parent__code=parent_code)
        
        choices = list(queryset.values(
            'id', 'code', 'name', 'description',
            'icon', 'color', 'is_default', 'metadata', 'sort_order'
        ).order_by('sort_order'))
        
        result = {c['code']: c for c in choices} if as_dict else choices
        
        try:
            domain_obj = LookupDomain.objects.get(code=domain)
            ttl = domain_obj.cache_ttl
        except LookupDomain.DoesNotExist:
            ttl = cls.DEFAULT_CACHE_TTL
        
        cache.set(cache_key, result, ttl)
        return result
    
    @classmethod
    def get_choice(cls, domain: str, code: str) -> Optional[dict]:
        """Get a single choice by domain and code."""
        choices = cls.get_choices(domain, as_dict=True)
        return choices.get(code)
    
    @classmethod
    def get_choice_id(cls, domain: str, code: str) -> Optional[int]:
        """Get the database ID of a choice (for FK relationships)."""
        choice = cls.get_choice(domain, code)
        return choice['id'] if choice else None
    
    @classmethod
    def get_default(cls, domain: str) -> Optional[dict]:
        """Get the default choice for a domain."""
        choices = cls.get_choices(domain)
        for choice in choices:
            if choice['is_default']:
                return choice
        return choices[0] if choices else None
    
    @classmethod
    def get_for_django_choices(cls, domain: str) -> list[tuple[str, str]]:
        """Get choices formatted for Django model field choices."""
        choices = cls.get_choices(domain)
        return [(c['code'], c['name']) for c in choices]
    
    @classmethod
    def validate(cls, domain: str, code: str) -> bool:
        """Validate that a code is valid for a domain."""
        return cls.get_choice(domain, code) is not None
    
    @classmethod
    def get_metadata(cls, domain: str, code: str, key: str, default: Any = None) -> Any:
        """Get a specific metadata value from a choice."""
        choice = cls.get_choice(domain, code)
        if choice and choice.get('metadata'):
            return choice['metadata'].get(key, default)
        return default
    
    @classmethod
    def clear_cache(cls, domain: Optional[str] = None):
        """Clear cached choices."""
        if domain:
            cache.delete_pattern(f"{cls.CACHE_PREFIX}{domain}:*")
        else:
            cache.delete_pattern(f"{cls.CACHE_PREFIX}*")
```

### 6.2 GovernanceService

```python
# platform/apps/governance/services/governance_service.py
"""
GovernanceService - Enforcement of platform governance rules.
"""

import re
from typing import Optional, Tuple
from ..models import ImportRule, AccessRule, NamingRule, PatternRule, EnforcementLog


class GovernanceService:
    """Service for enforcing platform governance rules."""
    
    @classmethod
    def check_import(
        cls,
        import_statement: str,
        module_path: str,
        log_violation: bool = True,
        detected_by: str = 'runtime',
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Check if an import is allowed.
        
        Returns:
            Tuple of (allowed, message, alternative_fqn)
        """
        rules = ImportRule.objects.filter(is_active=True).select_related('enforcement')
        
        for rule in rules:
            if rule.import_pattern and re.search(rule.import_pattern, import_statement):
                if module_path in (rule.exceptions or []):
                    continue
                
                if rule.applies_to != ['*']:
                    in_scope = any(
                        module_path.startswith(scope.replace('*', ''))
                        for scope in rule.applies_to
                    )
                    if not in_scope:
                        continue
                
                enforcement = rule.enforcement.code
                message = f"Import '{rule.forbidden_import}' is not allowed. Use {rule.alternative_fqn} instead."
                
                if log_violation:
                    EnforcementLog.objects.create(
                        rule_type='import',
                        rule_code=rule.code,
                        file_path=module_path,
                        code_snippet=import_statement,
                        action_taken='blocked' if enforcement == 'block' else 'warned',
                        message=message,
                        detected_by=detected_by,
                    )
                
                if enforcement == 'block':
                    return False, message, rule.alternative_fqn
                else:
                    return True, message, rule.alternative_fqn
        
        return True, None, None
    
    @classmethod
    def check_access(
        cls,
        target: str,
        accessor: str,
        log_violation: bool = True,
        detected_by: str = 'runtime',
    ) -> Tuple[bool, Optional[str]]:
        """Check if an accessor can access a target."""
        rules = AccessRule.objects.filter(is_active=True).select_related('enforcement')
        
        for rule in rules:
            pattern = rule.target_pattern.replace('.', r'\.').replace('*', '.*')
            if re.match(pattern, target):
                if accessor not in rule.allowed_accessors:
                    enforcement = rule.enforcement.code
                    message = f"Access to '{target}' not allowed from '{accessor}'. {rule.access_method}"
                    
                    if log_violation:
                        EnforcementLog.objects.create(
                            rule_type='access',
                            rule_code=rule.code,
                            code_snippet=f"{accessor} -> {target}",
                            action_taken='blocked' if enforcement == 'block' else 'warned',
                            message=message,
                            detected_by=detected_by,
                        )
                    
                    if enforcement == 'block':
                        return False, message
                    return True, message
        
        return True, None
    
    @classmethod
    def check_naming(
        cls,
        name: str,
        entity_type: str,
        log_violation: bool = True,
        detected_by: str = 'ci_cd',
    ) -> Tuple[bool, Optional[str]]:
        """Check if a name follows naming conventions."""
        rules = NamingRule.objects.filter(
            applies_to=entity_type, is_active=True
        ).select_related('enforcement')
        
        for rule in rules:
            if not re.match(rule.naming_pattern, name):
                enforcement = rule.enforcement.code
                message = f"Name '{name}' violates {rule.name}. Example: {rule.naming_example}"
                
                if log_violation:
                    EnforcementLog.objects.create(
                        rule_type='naming',
                        rule_code=rule.code,
                        code_snippet=name,
                        action_taken='blocked' if enforcement == 'block' else 'warned',
                        message=message,
                        detected_by=detected_by,
                    )
                
                if enforcement == 'block':
                    return False, message
                return True, message
        
        return True, None
```

### 6.3 LLMGateway

```python
# platform/apps/governance/services/llm_gateway.py
"""
LLMGateway - Centralized LLM access.

ALL LLM calls MUST go through this gateway!

Example:
    # ❌ WRONG - Don't do this:
    from openai import OpenAI
    client = OpenAI()
    response = client.chat.completions.create(...)
    
    # ✅ RIGHT - Do this:
    from governance.services import LLMGateway
    
    response = await LLMGateway.generate(
        prompt="Hello!",
        model_code="claude-sonnet-4-5"
    )
"""

import logging
from typing import Optional
from dataclasses import dataclass

from .lookup_service import LookupService

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Standardized LLM response."""
    content: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    cost: float
    duration_ms: int
    request_id: str


@dataclass
class LLMUsage:
    """Token usage tracking."""
    input_tokens: int
    output_tokens: int
    
    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class LLMGateway:
    """
    Centralized LLM access - ALL LLM calls MUST go through here.
    
    Features:
    - Consistent error handling
    - Cost tracking
    - Rate limiting
    - Model selection from lookup tables
    - Audit logging
    """
    
    _anthropic_client = None
    _openai_client = None
    
    @classmethod
    def get_available_models(cls) -> list[dict]:
        """Get all available LLM models from lookup table."""
        return LookupService.get_choices('llm_model')
    
    @classmethod
    def get_model_config(cls, model_code: str) -> Optional[dict]:
        """Get configuration for a specific model."""
        return LookupService.get_choice('llm_model', model_code)
    
    @classmethod
    def calculate_cost(cls, model_code: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for a request (in USD)."""
        config = cls.get_model_config(model_code)
        if not config or not config.get('metadata'):
            return 0.0
        
        metadata = config['metadata']
        cost_input = metadata.get('cost_input', 0)
        cost_output = metadata.get('cost_output', 0)
        
        return (
            (input_tokens / 1_000_000) * cost_input +
            (output_tokens / 1_000_000) * cost_output
        )
    
    @classmethod
    async def generate(
        cls,
        prompt: str,
        model_code: str = 'claude-sonnet-4-5',
        max_tokens: int = 4096,
        temperature: float = 0.5,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate text using LLM.
        
        Args:
            prompt: The user prompt
            model_code: Model code from llm_model lookup
            max_tokens: Maximum tokens to generate
            temperature: Temperature (0.0-1.0)
            system_prompt: Optional system prompt
        
        Returns:
            LLMResponse with content, usage, and cost
        """
        import time
        import uuid
        
        start_time = time.time()
        request_id = str(uuid.uuid4())[:8]
        
        model_config = cls.get_model_config(model_code)
        if not model_config:
            raise ValueError(f"Model '{model_code}' not found in llm_model lookup")
        
        metadata = model_config.get('metadata', {})
        provider = metadata.get('provider')
        model_id = metadata.get('model_id', model_code)
        
        logger.info(f"LLM request {request_id}: model={model_code}, provider={provider}")
        
        try:
            if provider == 'anthropic':
                content, usage = await cls._call_anthropic(
                    prompt, model_id, max_tokens, temperature, system_prompt, **kwargs
                )
            elif provider == 'openai':
                content, usage = await cls._call_openai(
                    prompt, model_id, max_tokens, temperature, system_prompt, **kwargs
                )
            else:
                raise ValueError(f"Unknown provider: {provider}")
            
            cost = cls.calculate_cost(model_code, usage.input_tokens, usage.output_tokens)
            duration_ms = int((time.time() - start_time) * 1000)
            
            logger.info(
                f"LLM response {request_id}: "
                f"tokens={usage.total_tokens}, cost=${cost:.4f}, duration={duration_ms}ms"
            )
            
            return LLMResponse(
                content=content,
                model=model_code,
                provider=provider,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cost=cost,
                duration_ms=duration_ms,
                request_id=request_id,
            )
            
        except Exception as e:
            logger.error(f"LLM error {request_id}: {e}")
            raise RuntimeError(f"LLM call failed: {e}") from e
    
    @classmethod
    def _get_anthropic_client(cls):
        if cls._anthropic_client is None:
            from anthropic import Anthropic
            cls._anthropic_client = Anthropic()
        return cls._anthropic_client
    
    @classmethod
    def _get_openai_client(cls):
        if cls._openai_client is None:
            from openai import OpenAI
            cls._openai_client = OpenAI()
        return cls._openai_client
    
    @classmethod
    async def _call_anthropic(cls, prompt, model_id, max_tokens, temperature, system_prompt, **kwargs):
        client = cls._get_anthropic_client()
        request_kwargs = {
            "model": model_id,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            request_kwargs["system"] = system_prompt
        
        response = client.messages.create(**request_kwargs, **kwargs)
        return (
            response.content[0].text,
            LLMUsage(response.usage.input_tokens, response.usage.output_tokens)
        )
    
    @classmethod
    async def _call_openai(cls, prompt, model_id, max_tokens, temperature, system_prompt, **kwargs):
        client = cls._get_openai_client()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = client.chat.completions.create(
            model=model_id,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=messages,
            **kwargs,
        )
        return (
            response.choices[0].message.content,
            LLMUsage(response.usage.prompt_tokens, response.usage.completion_tokens)
        )
```

---

## 7. Registry MCP Server

### 7.1 Server Implementation

```python
# mcp-hub/registry_mcp/server.py
"""
Platform Registry MCP Server

AI agents MUST use this to check for existing functionality before implementing.
"""

import json
import os
from typing import Optional
from mcp.server import Server

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'platform.settings')
import django
django.setup()

from django.contrib.postgres.search import SearchQuery, SearchRank
from governance.models import *
from governance.services import LookupService

app = Server("registry-mcp")


@app.tool()
async def search_existing_functionality(
    query: str,
    entity_types: Optional[list[str]] = None,
    limit: int = 20,
) -> str:
    """
    Search for existing functionality in the platform.
    
    MANDATORY: Call this BEFORE implementing any new functionality!
    
    Args:
        query: What you're looking for (e.g., "rate limiting", "caching")
        entity_types: Filter by types or None for all
        limit: Maximum results
    
    Returns:
        JSON with matching existing functionality
    """
    search_query = SearchQuery(query, config='english')
    results = []
    
    # Search all entity types
    if not entity_types or 'class' in entity_types:
        for cls in Class.objects.annotate(
            rank=SearchRank('search_vector', search_query)
        ).filter(search_vector=search_query).select_related('module__package')[:limit]:
            results.append({
                "entity_type": "class",
                "fqn": cls.fqn,
                "name": cls.name,
                "description": cls.description,
                "usage": cls.usage_example,
                "rank": float(cls.rank),
            })
    
    if not entity_types or 'mcp_server' in entity_types:
        for server in MCPServer.objects.annotate(
            rank=SearchRank('search_vector', search_query)
        ).filter(search_vector=search_query)[:limit]:
            results.append({
                "entity_type": "mcp_server",
                "name": server.name,
                "description": server.description,
                "when_to_use": server.when_to_use,
                "rank": float(server.rank),
            })
    
    if not entity_types or 'service' in entity_types:
        for svc in Service.objects.annotate(
            rank=SearchRank('search_vector', search_query)
        ).filter(search_vector=search_query)[:limit]:
            results.append({
                "entity_type": "service",
                "fqn": svc.fqn,
                "name": svc.name,
                "description": svc.description,
                "access_via": svc.access_via_fqn,
                "rank": float(svc.rank),
            })
    
    results.sort(key=lambda x: x.get('rank', 0), reverse=True)
    results = results[:limit]
    
    if not results:
        return json.dumps({
            "found": False,
            "message": f"No existing functionality found for '{query}'.",
            "proceed": True,
        }, indent=2)
    
    return json.dumps({
        "found": True,
        "count": len(results),
        "message": "⚠️ EXISTING IMPLEMENTATION FOUND - DO NOT REIMPLEMENT!",
        "proceed": False,
        "results": results,
    }, indent=2)


@app.tool()
async def check_before_implement(functionality: str, description: str) -> str:
    """
    MANDATORY check before implementing new functionality.
    
    This tool MUST be called before writing any new service, utility, or handler.
    """
    search_result = await search_existing_functionality(
        f"{functionality} {description}", limit=5
    )
    result = json.loads(search_result)
    
    if result["found"]:
        return json.dumps({
            "proceed": False,
            "reason": "EXISTING IMPLEMENTATION FOUND",
            "message": "⛔ DO NOT REIMPLEMENT! Use the existing functionality.",
            "existing": result["results"],
        }, indent=2)
    
    return json.dumps({
        "proceed": True,
        "message": f"✅ You may implement '{functionality}'.",
        "requirements": [
            "Follow ADR-012 quality standards",
            "Follow ADR-015 naming conventions",
            "Use LookupService for choices (no Enums)",
            "Use LLMGateway for LLM calls",
            "Register in platform.reg_* after implementation",
        ],
    }, indent=2)


@app.tool()
async def get_lookup_choices(domain: str) -> str:
    """
    Get available choices from a lookup domain.
    
    Use this instead of hardcoded Enums!
    """
    choices = LookupService.get_choices(domain)
    
    if not choices:
        return json.dumps({
            "found": False,
            "domain": domain,
            "available_domains": [d['code'] for d in LookupService.get_domains()],
        }, indent=2)
    
    return json.dumps({
        "found": True,
        "domain": domain,
        "count": len(choices),
        "choices": choices,
        "usage": f"LookupService.get_choice('{domain}', '<code>')",
    }, indent=2)


@app.tool()
async def get_llm_models() -> str:
    """Get available LLM models with configurations."""
    models = LookupService.get_choices('llm_model')
    
    formatted = []
    for model in models:
        metadata = model.get('metadata', {})
        formatted.append({
            "code": model['code'],
            "name": model['name'],
            "provider": metadata.get('provider'),
            "cost_input": metadata.get('cost_input'),
            "cost_output": metadata.get('cost_output'),
            "tier": metadata.get('tier'),
        })
    
    return json.dumps({
        "models": formatted,
        "usage": "LLMGateway.generate(prompt, model_code='<code>')",
        "warning": "DO NOT use OpenAI or Anthropic SDKs directly!",
    }, indent=2)
```

### 7.2 MCP Server Tools Summary

| Tool | Zweck | Mandatory |
|------|-------|-----------|
| `search_existing_functionality` | Suche nach existierenden Komponenten | ✅ Ja |
| `check_before_implement` | Prüfung vor Implementation | ✅ Ja |
| `get_lookup_choices` | Lookup-Werte abrufen | Für Choices |
| `get_llm_models` | LLM-Modelle abrufen | Für LLM-Calls |
| `list_packages` | Packages auflisten | Optional |
| `list_mcp_servers` | MCP Servers auflisten | Optional |

---

## 8. CI/CD Integration

### 8.1 Governance Check Script

```python
#!/usr/bin/env python
# scripts/governance_check.py
"""
CI/CD Governance Checker - Runs on every PR
"""

import ast
import re
import sys
import json
from pathlib import Path
from dataclasses import dataclass, field

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'platform.settings')
import django
django.setup()

from governance.models import ImportRule, NamingRule, PatternRule, EnforcementLog


@dataclass
class Violation:
    rule_type: str
    rule_code: str
    file_path: str
    line_number: int
    message: str
    severity: str
    suggestion: str = ""


@dataclass
class CheckResult:
    violations: list[Violation] = field(default_factory=list)
    warnings: list[Violation] = field(default_factory=list)
    files_checked: int = 0
    
    @property
    def passed(self) -> bool:
        return len(self.violations) == 0
    
    def add(self, violation: Violation):
        if violation.severity == 'block':
            self.violations.append(violation)
        else:
            self.warnings.append(violation)


class GovernanceChecker:
    def __init__(self, commit_sha: str = None, pr_number: int = None):
        self.commit_sha = commit_sha
        self.pr_number = pr_number
        self.result = CheckResult()
        self.import_rules = list(ImportRule.objects.filter(is_active=True))
        self.naming_rules = list(NamingRule.objects.filter(is_active=True))
        self.pattern_rules = list(PatternRule.objects.filter(is_active=True))
    
    def check_file(self, file_path: Path) -> None:
        if not file_path.suffix == '.py':
            return
        
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content)
        except Exception as e:
            print(f"  ⚠️  Could not process {file_path}: {e}")
            return
        
        self.result.files_checked += 1
        module_path = str(file_path).replace('/', '.').replace('.py', '')
        
        self._check_imports(tree, file_path, module_path)
        self._check_class_names(tree, file_path)
        self._check_function_names(tree, file_path)
        self._check_no_enums(tree, file_path)
        self._check_patterns(content, file_path)
    
    def _check_imports(self, tree, file_path, module_path):
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self._validate_import(f"import {alias.name}", file_path, module_path, node.lineno)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = ', '.join(a.name for a in node.names)
                self._validate_import(f"from {node.module} import {names}", file_path, module_path, node.lineno)
    
    def _validate_import(self, import_str, file_path, module_path, lineno):
        for rule in self.import_rules:
            if rule.import_pattern and re.search(rule.import_pattern, import_str):
                if module_path in (rule.exceptions or []):
                    continue
                if rule.applies_to != ['*']:
                    if not any(module_path.startswith(s.replace('*', '')) for s in rule.applies_to):
                        continue
                
                self.result.add(Violation(
                    rule_type='import',
                    rule_code=rule.code,
                    file_path=str(file_path),
                    line_number=lineno,
                    message=f"Forbidden import: {import_str}",
                    severity=rule.enforcement.code,
                    suggestion=f"Use {rule.alternative_fqn} instead",
                ))
    
    def _check_class_names(self, tree, file_path):
        rules = [r for r in self.naming_rules if r.applies_to == 'class']
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for rule in rules:
                    if not re.match(rule.naming_pattern, node.name):
                        self.result.add(Violation(
                            rule_type='naming',
                            rule_code=rule.code,
                            file_path=str(file_path),
                            line_number=node.lineno,
                            message=f"Class '{node.name}' violates {rule.name}",
                            severity=rule.enforcement.code,
                            suggestion=f"Example: {rule.naming_example}",
                        ))
    
    def _check_function_names(self, tree, file_path):
        rules = [r for r in self.naming_rules if r.applies_to == 'function']
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith('__') and node.name.endswith('__'):
                    continue
                for rule in rules:
                    if not re.match(rule.naming_pattern, node.name):
                        self.result.add(Violation(
                            rule_type='naming',
                            rule_code=rule.code,
                            file_path=str(file_path),
                            line_number=node.lineno,
                            message=f"Function '{node.name}' violates {rule.name}",
                            severity=rule.enforcement.code,
                            suggestion=f"Example: {rule.naming_example}",
                        ))
    
    def _check_no_enums(self, tree, file_path):
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    base_name = getattr(base, 'name', None) or getattr(base, 'attr', None)
                    if base_name == 'Enum':
                        self.result.add(Violation(
                            rule_type='pattern',
                            rule_code='no_enum_choices',
                            file_path=str(file_path),
                            line_number=node.lineno,
                            message=f"Class '{node.name}' inherits from Enum",
                            severity='warn',
                            suggestion="Use LookupService.get_choices() instead",
                        ))
    
    def _check_patterns(self, content, file_path):
        for rule in self.pattern_rules:
            if rule.antipattern_regex:
                for match in re.finditer(rule.antipattern_regex, content):
                    lineno = content[:match.start()].count('\n') + 1
                    self.result.add(Violation(
                        rule_type='pattern',
                        rule_code=rule.code,
                        file_path=str(file_path),
                        line_number=lineno,
                        message=f"Antipattern: {rule.name}",
                        severity=rule.enforcement.code,
                        suggestion=f"Use {rule.pattern_fqn} instead",
                    ))
    
    def check_directory(self, directory: Path) -> None:
        skip = ['migrations', '__pycache__', '.venv', 'node_modules', '.git']
        for py_file in directory.rglob('*.py'):
            if any(s in str(py_file) for s in skip):
                continue
            self.check_file(py_file)
    
    def report(self) -> int:
        print("\n" + "=" * 70)
        print("PLATFORM GOVERNANCE CHECK RESULTS")
        print("=" * 70)
        print(f"\nFiles checked: {self.result.files_checked}")
        
        if self.result.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.result.warnings)}):")
            for w in self.result.warnings[:10]:
                print(f"  {w.file_path}:{w.line_number} [{w.rule_code}] {w.message}")
        
        if self.result.violations:
            print(f"\n❌ BLOCKING VIOLATIONS ({len(self.result.violations)}):")
            for v in self.result.violations:
                print(f"  {v.file_path}:{v.line_number} [{v.rule_code}] {v.message}")
            print("\n❌ FAILED: PR cannot be merged until violations are fixed.")
            return 1
        
        print("\n✅ PASSED: All governance checks passed!")
        return 0


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('path')
    parser.add_argument('--commit')
    parser.add_argument('--pr', type=int)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    
    checker = GovernanceChecker(args.commit, args.pr)
    path = Path(args.path)
    
    if path.is_file():
        checker.check_file(path)
    else:
        checker.check_directory(path)
    
    if args.json:
        print(json.dumps({
            "passed": checker.result.passed,
            "files_checked": checker.result.files_checked,
            "violations": [vars(v) for v in checker.result.violations],
            "warnings": [vars(w) for w in checker.result.warnings],
        }, indent=2))
        sys.exit(0 if checker.result.passed else 1)
    else:
        sys.exit(checker.report())
```

### 8.2 GitHub Actions Workflow

```yaml
# .github/workflows/governance-check.yml
name: "🔍 Governance Check"

on:
  pull_request:
    branches: [main, develop]
    paths:
      - '**.py'
      - 'mcp-hub/**'
      - 'platform/**'

jobs:
  governance-check:
    name: "Governance Validation"
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: platform_test
        ports:
          - 5432:5432
    
    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
      
      - name: "📦 Install Dependencies"
        run: pip install -r requirements.txt -r requirements-dev.txt
      
      - name: "🗃️ Setup Database"
        env:
          DATABASE_URL: postgres://postgres:postgres@localhost:5432/platform_test
        run: |
          python manage.py migrate --settings=platform.settings.test
          python manage.py loaddata governance/fixtures/governance_rules.json
      
      - name: "🔍 Run Governance Check"
        id: governance
        env:
          DATABASE_URL: postgres://postgres:postgres@localhost:5432/platform_test
        run: |
          python scripts/governance_check.py . \
            --commit ${{ github.sha }} \
            --pr ${{ github.event.pull_request.number }} \
            --json > result.json
          
          echo "passed=$(jq -r '.passed' result.json)" >> $GITHUB_OUTPUT
          echo "violations=$(jq -r '.violations | length' result.json)" >> $GITHUB_OUTPUT
      
      - name: "📝 Post PR Comment"
        if: always()
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const result = JSON.parse(fs.readFileSync('result.json', 'utf8'));
            
            let body = '## 🔍 Governance Check Results\n\n';
            body += result.passed ? '✅ **All checks passed!**\n' : '❌ **Violations found!**\n';
            body += `\n- Files: ${result.files_checked}\n`;
            body += `- Violations: ${result.violations.length}\n`;
            body += `- Warnings: ${result.warnings.length}\n`;
            
            if (result.violations.length > 0) {
              body += '\n### ❌ Blocking Violations\n\n';
              body += '| File | Line | Rule | Message |\n|------|------|------|--------|\n';
              for (const v of result.violations.slice(0, 15)) {
                body += `| \`${v.file_path}\` | ${v.line_number} | \`${v.rule_code}\` | ${v.message} |\n`;
              }
            }
            
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: body,
            });
      
      - name: "🚫 Fail on Violations"
        if: steps.governance.outputs.passed == 'false'
        run: exit 1
```

---

## 9. System Prompt Updates

### 9.1 AI Agent System Prompt (Windsurf/Cursor)

```markdown
## PLATFORM GOVERNANCE (ADR-015)

### MANDATORY CHECKS BEFORE IMPLEMENTATION

Before implementing ANY new functionality:

1. **ALWAYS call `registry_mcp:check_before_implement`**
   ```
   check_before_implement("rate limiter", "Limit API requests per minute")
   ```

2. **If existing implementation found → DO NOT REIMPLEMENT**
   - Use the existing component
   - Follow its usage examples

3. **If no existing implementation → Proceed with requirements**

### FORBIDDEN ACTIONS

| ❌ DON'T | ✅ DO INSTEAD |
|----------|--------------|
| `import openai` | Use `llm_mcp:generate_text` |
| `import anthropic` | Use `llm_mcp:chat_completion` |
| `import redis` | Use `CacheService` |
| `class Status(Enum)` | Use `LookupService.get_choices('status')` |
| `logging.getLogger()` | Use `get_logger(__name__)` |
| `except Exception: pass` | Use `@error_handler` decorator |

### LOOKUP SERVICE USAGE

```python
# ❌ WRONG - Hardcoded Enum
class Priority(Enum):
    HIGH = 'high'
    LOW = 'low'

# ✅ RIGHT - Database Lookup
from governance.services import LookupService

priorities = LookupService.get_choices('priority')
priority = LookupService.get_choice('priority', 'high')
priority_id = LookupService.get_choice_id('priority', 'high')  # For FK
```

### LLM GATEWAY USAGE

```python
# ❌ WRONG - Direct SDK
from openai import OpenAI
client = OpenAI()
response = client.chat.completions.create(...)

# ✅ RIGHT - LLM Gateway
from governance.services import LLMGateway

response = await LLMGateway.generate(
    prompt="Your prompt",
    model_code="claude-sonnet-4-5",
    max_tokens=1000
)
print(response.content)
print(f"Cost: ${response.cost:.4f}")
```

### NAMING CONVENTIONS

| Element | Format | Example |
|---------|--------|---------|
| Classes | PascalCase | `CacheService` |
| Functions | snake_case | `get_user` |
| Constants | UPPER_SNAKE | `MAX_RETRIES` |
| MCP Servers | snake_case + `_mcp` | `llm_mcp` |

### REGISTRATION AFTER IMPLEMENTATION

After implementing a new component, register it:

```sql
INSERT INTO platform.reg_service (name, code, fqn, ...) VALUES (...);
```

Or use the Django admin / management command.
```

---

## 10. Enforcement Matrix

### 10.1 Enforcement Layers

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        ENFORCEMENT LAYERS                                │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Layer 1: AI DISCOVERY (registry_mcp)                                   │
│  ══════════════════════════════════                                      │
│  • check_before_implement() BEFORE coding                               │
│  • Blocks duplicate implementations at source                           │
│  • Provides usage examples for existing components                      │
│                                                                          │
│  ────────────────────────────────────────────────────────────────────── │
│                                                                          │
│  Layer 2: PRE-COMMIT (local)                                            │
│  ═══════════════════════════                                             │
│  • Fast feedback during development                                     │
│  • Catches obvious violations before commit                             │
│  • Optional but recommended                                              │
│                                                                          │
│  ────────────────────────────────────────────────────────────────────── │
│                                                                          │
│  Layer 3: CI/CD (governance_check.py)                                   │
│  ════════════════════════════════════                                    │
│  • Runs on every PR                                                     │
│  • BLOCKS merge for 'block' enforcement rules                           │
│  • Comments violations on PR                                            │
│  • Logs to gov_enforcement_log                                          │
│                                                                          │
│  ────────────────────────────────────────────────────────────────────── │
│                                                                          │
│  Layer 4: RUNTIME (GovernanceService)                                   │
│  ════════════════════════════════════                                    │
│  • Validates at execution time                                          │
│  • Last line of defense                                                 │
│  • Can block or warn based on rules                                     │
│                                                                          │
│  ────────────────────────────────────────────────────────────────────── │
│                                                                          │
│  Layer 5: AUDIT (gov_enforcement_log)                                   │
│  ════════════════════════════════════                                    │
│  • Complete audit trail                                                 │
│  • All violations logged with context                                   │
│  • Enables trend analysis and reporting                                 │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 10.2 Complete Governance Matrix

| Problem | Detection | Enforcement | Action |
|---------|-----------|-------------|--------|
| Duplicate Handler | registry_mcp | AI Discovery | Show existing |
| Duplicate Service | registry_mcp | AI Discovery | Show existing |
| Duplicate Agent | registry_mcp | AI Discovery | Show existing |
| Direct OpenAI import | CI/CD | **BLOCK** | Fail PR |
| Direct Anthropic import | CI/CD | **BLOCK** | Fail PR |
| Direct Redis import | CI/CD | WARN | Comment on PR |
| Hardcoded Enum | CI/CD | WARN | Comment on PR |
| Wrong class naming | CI/CD | WARN | Comment on PR |
| MCP without _mcp suffix | CI/CD | **BLOCK** | Fail PR |
| Antipattern (bare except) | CI/CD | WARN | Comment on PR |
| Runtime access violation | Runtime | Based on rule | Block or Log |

---

## 11. Implementation Plan

### 11.1 Phase 1: Foundation (Week 1-2)

| Task | Owner | Status |
|------|-------|--------|
| Create platform schema | Architect | ⬜ |
| Create lookup tables (lkp_domain, lkp_choice) | Architect | ⬜ |
| Seed lookup data (status, priority, llm_model, etc.) | Architect | ⬜ |
| Implement LookupService | Architect | ⬜ |
| Write LookupService tests | Architect | ⬜ |
| Create Django admin for lookups | Architect | ⬜ |

### 11.2 Phase 2: Registry (Week 3-4)

| Task | Owner | Status |
|------|-------|--------|
| Create registry tables (reg_*) | Architect | ⬜ |
| Add full-text search indexes | Architect | ⬜ |
| Seed initial registry data | All Teams | ⬜ |
| Implement registry_mcp server | Architect | ⬜ |
| Write registry_mcp tests | Architect | ⬜ |
| Update AI agent system prompts | Architect | ⬜ |

### 11.3 Phase 3: Governance Rules (Week 5-6)

| Task | Owner | Status |
|------|-------|--------|
| Create governance tables (gov_*) | Architect | ⬜ |
| Seed governance rules | Architect | ⬜ |
| Implement GovernanceService | Architect | ⬜ |
| Implement LLMGateway | Architect | ⬜ |
| Write governance_check.py | Architect | ⬜ |
| Create GitHub Actions workflow | Architect | ⬜ |

### 11.4 Phase 4: Rollout (Week 7-8)

| Task | Owner | Status |
|------|-------|--------|
| Enable CI/CD checks (warn only) | Architect | ⬜ |
| Fix existing violations | All Teams | ⬜ |
| Enable blocking enforcement | Architect | ⬜ |
| Team training on governance | Architect | ⬜ |
| Documentation finalization | Architect | ⬜ |
| Monitoring dashboard | Architect | ⬜ |

---

## 12. Consequences

### 12.1 Positive

| Consequence | Impact |
|-------------|--------|
| **No more duplicate implementations** | Reduced code, consistent behavior |
| **Database-driven choices** | No deployments for new options |
| **Controlled LLM access** | Cost tracking, consistent error handling |
| **Enforced naming conventions** | More readable, maintainable code |
| **Complete audit trail** | Compliance, debugging, trend analysis |
| **AI agents discover existing code** | Reduced technical debt |

### 12.2 Negative

| Consequence | Mitigation |
|-------------|------------|
| Additional complexity | Comprehensive documentation, training |
| CI/CD overhead | Optimized checks, caching |
| Learning curve | System prompts, examples |
| Database dependency for lookups | Caching, fallback defaults |

### 12.3 Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Over-enforcement blocks legitimate code | Medium | High | Start with warnings, gradual enforcement |
| Registry becomes outdated | Medium | Medium | Regular audits, automated sync |
| Performance impact | Low | Medium | Caching, async checks |
| Resistance from developers | Medium | Medium | Clear benefits, training |

---

## 13. Appendix

### 13.1 Available Lookup Domains

```
status          - Component lifecycle (planned, production, deprecated)
priority        - Task priorities (critical, high, medium, low)
owner           - Team ownership (architect, alpha, bravo, guild)
category        - Component categories
environment     - Environments (local, staging, production)
llm_model       - LLM models with costs and capabilities
llm_provider    - LLM providers (anthropic, openai)
gate_level      - Approval gates (G0-G4 from ADR-014)
enforcement     - Rule enforcement (block, warn, log)
handler_type    - Handler types (event, request, signal)
service_type    - Service types (internal, external, hybrid)
class_type      - Class types (class, function, decorator)
document_type   - Document types
currency        - Currencies
country         - Countries (ISO 3166)
language        - Languages (ISO 639)
```

### 13.2 Quick Reference

```python
# Get all choices for a domain
statuses = LookupService.get_choices('status')

# Get single choice
status = LookupService.get_choice('status', 'production')

# Get ID for FK
status_id = LookupService.get_choice_id('status', 'production')

# Get for Django model choices
STATUS_CHOICES = LookupService.get_for_django_choices('status')

# Validate
if not LookupService.validate('status', user_input):
    raise ValidationError("Invalid status")

# Get metadata (e.g., LLM costs)
cost = LookupService.get_metadata('llm_model', 'claude-opus-4-5', 'cost_input')

# LLM calls
response = await LLMGateway.generate(
    prompt="Hello",
    model_code="claude-sonnet-4-5"
)
```

### 13.3 Related ADRs

| ADR | Relationship |
|-----|--------------|
| ADR-012 | MCP Quality Standards - quality gates for MCP servers |
| ADR-013 | Team Organization - team ownership codes used in registry |
| ADR-014 | AI-Native Teams - gate levels, orchestrator integration |

---

## 14. Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-03 | Achim Dehnert | Initial version |

---

## 15. Approval

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Author | Achim Dehnert | 2026-02-03 | ✍️ |
| Reviewer | | | |
| Approver | | | |
