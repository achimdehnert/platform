-- ============================================================================
-- REGISTRY TABLES - Platform Component Catalog (ADR-015 Phase 2)
-- ============================================================================

-- Python Packages
CREATE TABLE IF NOT EXISTS platform.reg_package (
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
CREATE TABLE IF NOT EXISTS platform.reg_module (
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
CREATE TABLE IF NOT EXISTS platform.reg_class (
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
CREATE TABLE IF NOT EXISTS platform.reg_mcp_server (
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
CREATE TABLE IF NOT EXISTS platform.reg_mcp_tool (
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
CREATE TABLE IF NOT EXISTS platform.reg_mcp_server_antipattern (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    server_id       BIGINT NOT NULL REFERENCES platform.reg_mcp_server(id) ON DELETE CASCADE,
    description     TEXT NOT NULL,
    reason          TEXT,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Event Handlers
CREATE TABLE IF NOT EXISTS platform.reg_handler (
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
CREATE TABLE IF NOT EXISTS platform.reg_agent (
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
CREATE TABLE IF NOT EXISTS platform.reg_service (
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
CREATE TABLE IF NOT EXISTS platform.reg_pattern (
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

-- Full-text search indexes
CREATE INDEX IF NOT EXISTS idx_reg_package_search ON platform.reg_package USING GIN (search_vector);
CREATE INDEX IF NOT EXISTS idx_reg_module_search ON platform.reg_module USING GIN (search_vector);
CREATE INDEX IF NOT EXISTS idx_reg_class_search ON platform.reg_class USING GIN (search_vector);
CREATE INDEX IF NOT EXISTS idx_reg_mcp_server_search ON platform.reg_mcp_server USING GIN (search_vector);
CREATE INDEX IF NOT EXISTS idx_reg_mcp_tool_search ON platform.reg_mcp_tool USING GIN (search_vector);
CREATE INDEX IF NOT EXISTS idx_reg_handler_search ON platform.reg_handler USING GIN (search_vector);
CREATE INDEX IF NOT EXISTS idx_reg_agent_search ON platform.reg_agent USING GIN (search_vector);
CREATE INDEX IF NOT EXISTS idx_reg_service_search ON platform.reg_service USING GIN (search_vector);
CREATE INDEX IF NOT EXISTS idx_reg_pattern_search ON platform.reg_pattern USING GIN (search_vector);
