-- ============================================================================
-- ADR-009: Infrastructure Schema Migration
-- Database-Driven Service Registry & Self-Healing
-- ============================================================================

BEGIN;

-- Service Definition (Database-Driven Registry)
CREATE TABLE IF NOT EXISTS infra_service (
    id SERIAL PRIMARY KEY,
    code VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    service_type VARCHAR(50) NOT NULL,
    domain VARCHAR(255) NOT NULL UNIQUE,
    repo_url VARCHAR(500) NOT NULL,
    default_branch VARCHAR(100) NOT NULL DEFAULT 'main',
    health_endpoint VARCHAR(255) NOT NULL DEFAULT '/health/',
    cpu_cores INTEGER NOT NULL DEFAULT 1,
    memory_mb INTEGER NOT NULL DEFAULT 512,
    is_active BOOLEAN NOT NULL DEFAULT true,
    tier VARCHAR(20) NOT NULL DEFAULT 'production',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_service_type CHECK (
        service_type IN ('django', 'fastapi', 'static', 'worker', 'mcp')
    ),
    CONSTRAINT chk_service_tier CHECK (
        tier IN ('production', 'staging', 'development')
    ),
    CONSTRAINT chk_service_cpu CHECK (cpu_cores >= 1 AND cpu_cores <= 32),
    CONSTRAINT chk_service_memory CHECK (memory_mb >= 128 AND memory_mb <= 65536)
);

-- Service Dependencies
CREATE TABLE IF NOT EXISTS infra_service_dependency (
    id SERIAL PRIMARY KEY,
    service_id INTEGER NOT NULL REFERENCES infra_service(id) ON DELETE CASCADE,
    depends_on_id INTEGER NOT NULL REFERENCES infra_service(id) ON DELETE RESTRICT,
    dependency_type VARCHAR(20) NOT NULL DEFAULT 'required',
    
    CONSTRAINT uq_service_dependency UNIQUE (service_id, depends_on_id),
    CONSTRAINT chk_no_self_dependency CHECK (service_id != depends_on_id),
    CONSTRAINT chk_dependency_type CHECK (dependency_type IN ('required', 'optional'))
);

CREATE INDEX IF NOT EXISTS idx_dependency_service ON infra_service_dependency(service_id);

-- Auto-Fix Rules (Database-Driven)
CREATE TABLE IF NOT EXISTS infra_auto_fix_rule (
    id SERIAL PRIMARY KEY,
    code VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    error_pattern TEXT NOT NULL,
    error_category VARCHAR(100) NOT NULL,
    fix_type VARCHAR(50) NOT NULL,
    fix_script TEXT,
    confidence_threshold INTEGER NOT NULL DEFAULT 85,
    requires_approval BOOLEAN NOT NULL DEFAULT false,
    max_auto_attempts INTEGER NOT NULL DEFAULT 3,
    allowed_in_production BOOLEAN NOT NULL DEFAULT false,
    allowed_in_staging BOOLEAN NOT NULL DEFAULT true,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by_id INTEGER REFERENCES core_user(id) ON DELETE SET NULL,
    
    CONSTRAINT chk_autofix_type CHECK (
        fix_type IN ('restart_service', 'clear_cache', 'rollback', 'scale_up', 'run_migration')
    ),
    CONSTRAINT chk_autofix_confidence CHECK (
        confidence_threshold >= 50 AND confidence_threshold <= 100
    )
);

CREATE INDEX IF NOT EXISTS idx_autofix_active ON infra_auto_fix_rule(is_active, error_category);

-- Deployment Event (Audit Trail)
CREATE TABLE IF NOT EXISTS infra_deployment_event (
    id SERIAL PRIMARY KEY,
    service_id INTEGER NOT NULL REFERENCES infra_service(id) ON DELETE RESTRICT,
    environment VARCHAR(20) NOT NULL,
    git_sha VARCHAR(40) NOT NULL,
    git_ref VARCHAR(255) NOT NULL,
    image_tag VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    error_message TEXT,
    auto_fix_applied BOOLEAN NOT NULL DEFAULT false,
    auto_fix_rule_id INTEGER REFERENCES infra_auto_fix_rule(id),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    triggered_by_id INTEGER REFERENCES core_user(id) ON DELETE SET NULL,
    trigger_source VARCHAR(20) NOT NULL DEFAULT 'manual',
    
    CONSTRAINT chk_deployment_status CHECK (
        status IN ('pending', 'running', 'success', 'failed', 'rolled_back')
    ),
    CONSTRAINT chk_deployment_trigger CHECK (
        trigger_source IN ('manual', 'ci_cd', 'self_healing', 'rollback', 'scheduled')
    )
);

CREATE INDEX IF NOT EXISTS idx_deployment_service ON infra_deployment_event(service_id);
CREATE INDEX IF NOT EXISTS idx_deployment_status ON infra_deployment_event(status, started_at DESC);

-- Stammdaten: Services
INSERT INTO infra_service (code, name, service_type, domain, repo_url) VALUES
    ('bfagent-web', 'BF Agent Web', 'django', 'bfagent.iil.pet', 'https://github.com/achimdehnert/bfagent'),
    ('cadhub-api', 'CAD-Hub API', 'fastapi', 'cadhub.iil.pet', 'https://github.com/achimdehnert/platform'),
    ('cadhub-mcp', 'CAD-Hub MCP', 'mcp', 'mcp.cadhub.iil.pet', 'https://github.com/achimdehnert/platform')
ON CONFLICT (code) DO NOTHING;

-- Stammdaten: Auto-Fix Rules
INSERT INTO infra_auto_fix_rule (code, name, error_pattern, error_category, fix_type, confidence_threshold, allowed_in_production) VALUES
    ('restart_oom', 'Restart on OOM', 'Out of memory|OOMKilled|Cannot allocate memory', 'memory', 'restart_service', 90, true),
    ('restart_connection', 'Restart on Connection Error', 'Connection refused|Connection reset|ECONNREFUSED', 'network', 'restart_service', 85, true),
    ('clear_cache_disk', 'Clear Cache on Disk Full', 'No space left on device|Disk quota exceeded', 'disk', 'clear_cache', 80, false),
    ('rollback_migration', 'Rollback on Migration Error', 'Migration failed|IntegrityError|ProgrammingError', 'database', 'rollback', 75, false)
ON CONFLICT (code) DO NOTHING;

COMMIT;
