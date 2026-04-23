-- ============================================================================
-- GOVERNANCE RULES TABLES (ADR-015 Phase 3)
-- ============================================================================

-- Access Rules (What can access what)
CREATE TABLE IF NOT EXISTS platform.gov_access_rule (
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
CREATE TABLE IF NOT EXISTS platform.gov_import_rule (
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
CREATE TABLE IF NOT EXISTS platform.gov_naming_rule (
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
CREATE TABLE IF NOT EXISTS platform.gov_pattern_rule (
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
CREATE TABLE IF NOT EXISTS platform.gov_enforcement_log (
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

-- Indexes
CREATE INDEX IF NOT EXISTS idx_gov_enforcement_log_time ON platform.gov_enforcement_log (detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_gov_enforcement_log_rule ON platform.gov_enforcement_log (rule_type, rule_code);
CREATE INDEX IF NOT EXISTS idx_gov_enforcement_log_pr ON platform.gov_enforcement_log (pr_number) WHERE pr_number IS NOT NULL;
