-- BF Agent MCP - Create Database Tables
-- Run with: sqlite3 db.sqlite3 < CREATE_MCP_TABLES.sql

-- ============================================================================
-- LOOKUP TABLES
-- ============================================================================

-- MCP Risk Level
CREATE TABLE IF NOT EXISTS mcp_risk_level (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by_id INTEGER,
    updated_by_id INTEGER,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    name VARCHAR(30) NOT NULL UNIQUE,
    display_name VARCHAR(50) NOT NULL,
    severity_score INTEGER NOT NULL CHECK (severity_score >= 0 AND severity_score <= 100),
    color VARCHAR(7) DEFAULT '#6b7280',
    icon VARCHAR(10),
    requires_approval BOOLEAN NOT NULL DEFAULT 0,
    requires_backup BOOLEAN NOT NULL DEFAULT 1,
    description TEXT
);

-- MCP Component Type
CREATE TABLE IF NOT EXISTS mcp_component_type (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by_id INTEGER,
    updated_by_id INTEGER,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    name VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    default_path_pattern VARCHAR(200) NOT NULL,
    default_file_pattern VARCHAR(100) NOT NULL,
    default_class_pattern VARCHAR(100),
    icon VARCHAR(10),
    color VARCHAR(7) DEFAULT '#6b7280',
    is_directory BOOLEAN NOT NULL DEFAULT 1,
    supports_refactoring BOOLEAN NOT NULL DEFAULT 1,
    "order" INTEGER NOT NULL DEFAULT 0,
    description TEXT,
    boilerplate_template TEXT
);

-- MCP Protection Level
CREATE TABLE IF NOT EXISTS mcp_protection_level (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by_id INTEGER,
    updated_by_id INTEGER,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    name VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    severity_score INTEGER NOT NULL CHECK (severity_score >= 0 AND severity_score <= 100),
    blocks_refactoring BOOLEAN NOT NULL DEFAULT 0,
    requires_confirmation BOOLEAN NOT NULL DEFAULT 0,
    color VARCHAR(20),
    icon VARCHAR(50),
    description TEXT
);

-- MCP Path Category
CREATE TABLE IF NOT EXISTS mcp_path_category (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by_id INTEGER,
    updated_by_id INTEGER,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    name VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    icon VARCHAR(50),
    color VARCHAR(20),
    description TEXT,
    "order" INTEGER NOT NULL DEFAULT 0
);

-- ============================================================================
-- MAIN TABLES
-- ============================================================================

-- MCP Domain Config
CREATE TABLE IF NOT EXISTS mcp_domain_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by_id INTEGER,
    updated_by_id INTEGER,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    domain_id INTEGER NOT NULL UNIQUE,
    risk_level_id INTEGER NOT NULL,
    base_path VARCHAR(200) NOT NULL,
    allows_refactoring BOOLEAN NOT NULL DEFAULT 1,
    requires_session_tracking BOOLEAN NOT NULL DEFAULT 0,
    auto_backup_before_refactor BOOLEAN NOT NULL DEFAULT 0,
    config_data TEXT,
    last_refactored_at TIMESTAMP,
    total_refactorings INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (domain_id) REFERENCES bfagent_mcp_domain(id) ON DELETE CASCADE,
    FOREIGN KEY (risk_level_id) REFERENCES mcp_risk_level(id) ON DELETE RESTRICT
);

-- MCP Domain Component
CREATE TABLE IF NOT EXISTS mcp_domain_component (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by_id INTEGER,
    updated_by_id INTEGER,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    domain_config_id INTEGER NOT NULL,
    component_type_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    is_refactorable BOOLEAN NOT NULL DEFAULT 1,
    last_modified_at TIMESTAMP,
    lines_of_code INTEGER,
    complexity_score INTEGER,
    notes TEXT,
    FOREIGN KEY (domain_config_id) REFERENCES mcp_domain_config(id) ON DELETE CASCADE,
    FOREIGN KEY (component_type_id) REFERENCES mcp_component_type(id) ON DELETE RESTRICT
);

-- MCP Protected Path
CREATE TABLE IF NOT EXISTS mcp_protected_path (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by_id INTEGER,
    updated_by_id INTEGER,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    path_pattern VARCHAR(500) NOT NULL,
    reason TEXT NOT NULL,
    protection_level_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    FOREIGN KEY (protection_level_id) REFERENCES mcp_protection_level(id) ON DELETE RESTRICT,
    FOREIGN KEY (category_id) REFERENCES mcp_path_category(id) ON DELETE RESTRICT
);

-- MCP Refactor Session
CREATE TABLE IF NOT EXISTS mcp_refactor_session (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by_id INTEGER,
    updated_by_id INTEGER,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    domain_config_id INTEGER NOT NULL,
    session_id VARCHAR(100) NOT NULL UNIQUE,
    triggered_by VARCHAR(50) NOT NULL DEFAULT 'manual',
    components_affected TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'in_progress',
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    files_changed INTEGER NOT NULL DEFAULT 0,
    lines_added INTEGER NOT NULL DEFAULT 0,
    lines_removed INTEGER NOT NULL DEFAULT 0,
    summary TEXT,
    FOREIGN KEY (domain_config_id) REFERENCES mcp_domain_config(id) ON DELETE CASCADE
);

-- MCP File Change
CREATE TABLE IF NOT EXISTS mcp_file_change (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by_id INTEGER,
    updated_by_id INTEGER,
    session_id INTEGER NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    change_type VARCHAR(50) NOT NULL,
    lines_changed INTEGER NOT NULL DEFAULT 0,
    backup_path VARCHAR(500),
    diff_content TEXT,
    FOREIGN KEY (session_id) REFERENCES mcp_refactor_session(id) ON DELETE CASCADE
);

-- MCP Config History
CREATE TABLE IF NOT EXISTS mcp_config_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by_id INTEGER,
    updated_by_id INTEGER,
    domain_config_id INTEGER NOT NULL,
    changed_by VARCHAR(100),
    change_type VARCHAR(50) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    reason TEXT,
    FOREIGN KEY (domain_config_id) REFERENCES mcp_domain_config(id) ON DELETE CASCADE
);

-- ============================================================================
-- NAMING CONVENTIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS core_naming_convention (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by_id INTEGER,
    updated_by_id INTEGER,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    app_label VARCHAR(50) NOT NULL UNIQUE,
    domain_id INTEGER,
    display_name VARCHAR(100) NOT NULL,
    table_prefix VARCHAR(20),
    class_prefix VARCHAR(20),
    table_pattern VARCHAR(200),
    class_pattern VARCHAR(200),
    file_pattern VARCHAR(200),
    enforce_convention BOOLEAN NOT NULL DEFAULT 0,
    description TEXT,
    example_tables TEXT,
    example_classes TEXT
);

-- ============================================================================
-- SEED DATA
-- ============================================================================

-- Risk Levels
INSERT OR IGNORE INTO mcp_risk_level (name, display_name, severity_score, color, icon, description) VALUES
('low', 'Low Risk', 10, 'green', 'shield-check', 'Safe to refactor'),
('medium', 'Medium Risk', 50, 'yellow', 'shield-exclamation', 'Refactor with caution'),
('high', 'High Risk', 75, 'orange', 'shield-x', 'Review carefully before refactoring'),
('critical', 'Critical', 95, 'red', 'shield-lock', 'Do not refactor without approval');

-- Component Types
INSERT OR IGNORE INTO mcp_component_type (name, display_name, default_path_pattern, default_file_pattern, default_class_pattern, icon, color, is_directory, supports_refactoring, "order", description) VALUES
('handler', 'Handler', 'apps/{domain}/handlers/', '{name}_handler.py', '{Name}Handler', '🔧', '#3b82f6', 1, 1, 10, 'Business logic handlers'),
('service', 'Service', 'apps/{domain}/services/', '{name}_service.py', '{Name}Service', '⚙️', '#10b981', 1, 1, 20, 'Service layer'),
('model', 'Model', 'apps/{domain}/', 'models.py', '{Name}', '💾', '#8b5cf6', 0, 1, 30, 'Database models'),
('view', 'View', 'apps/{domain}/', 'views.py', '{name}_view', '👁️', '#06b6d4', 0, 1, 40, 'Django views'),
('admin', 'Admin', 'apps/{domain}/', 'admin.py', '', '🛡️', '#f59e0b', 0, 1, 50, 'Admin interface'),
('test', 'Test', 'apps/{domain}/tests/', 'test_{name}.py', 'Test{Name}', '✅', '#6b7280', 1, 0, 60, 'Test files');

-- Protection Levels
INSERT OR IGNORE INTO mcp_protection_level (name, display_name, severity_score, blocks_refactoring, requires_confirmation, color, icon, description) VALUES
('none', 'No Protection', 0, 0, 0, 'gray', 'unlock', 'No restrictions'),
('read_only', 'Read Only', 50, 0, 1, 'yellow', 'lock', 'Requires confirmation'),
('protected', 'Protected', 75, 0, 1, 'orange', 'shield', 'Highly sensitive'),
('absolute', 'Absolute', 100, 1, 1, 'red', 'shield-lock', 'Cannot be refactored');

-- Path Categories
INSERT OR IGNORE INTO mcp_path_category (name, display_name, icon, color, description, "order") VALUES
('core', 'Core System', 'cpu', 'red', 'Critical system files', 10),
('config', 'Configuration', 'gear', 'orange', 'Configuration files', 20),
('migration', 'Migration', 'database', 'blue', 'Database migrations', 30),
('dependency', 'Dependency', 'link', 'purple', 'External dependencies', 40);

-- Naming Conventions
INSERT OR IGNORE INTO core_naming_convention (app_label, display_name, table_prefix, class_prefix, table_pattern, class_pattern, file_pattern, description, example_tables, example_classes) VALUES
('bfagent_mcp', 'BF Agent MCP', 'mcp_', 'MCP', 'mcp_{name}', 'MCP{Name}', '{name}.py', 'MCP Server models', '["mcp_domain_config", "mcp_protected_path"]', '["MCPDomainConfig", "MCPProtectedPath"]'),
('core', 'Core System', 'core_', 'Core', 'core_{name}', 'Core{Name}', '{name}.py', 'Core system models', '["core_domain", "core_handler"]', '["CoreDomain", "CoreHandler"]'),
('bfagent', 'BF Agent', '', '', '{name}', '{Name}', '{name}.py', 'BF Agent models', '["handlers", "domains"]', '["Handler", "Domain"]');
