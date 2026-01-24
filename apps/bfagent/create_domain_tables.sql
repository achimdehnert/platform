-- Domain Arts Table
CREATE TABLE IF NOT EXISTS domain_arts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL,
    slug VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(200) NOT NULL,
    description TEXT,
    icon VARCHAR(50),
    color VARCHAR(20) DEFAULT 'primary',
    is_active BOOLEAN DEFAULT 1,
    is_experimental BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Domain Types Table
CREATE TABLE IF NOT EXISTS domain_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain_art_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(50) NOT NULL,
    display_name VARCHAR(200) NOT NULL,
    description TEXT,
    icon VARCHAR(50),
    color VARCHAR(20),
    config JSON DEFAULT '{}',
    is_active BOOLEAN DEFAULT 1,
    sort_order INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (domain_art_id) REFERENCES domain_arts(id) ON DELETE CASCADE,
    UNIQUE (domain_art_id, slug)
);

-- Domain Phases Table
CREATE TABLE IF NOT EXISTS domain_phases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain_type_id INTEGER NOT NULL,
    workflow_phase_id INTEGER NOT NULL,
    sort_order INTEGER DEFAULT 0,
    config JSON DEFAULT '{}',
    is_active BOOLEAN DEFAULT 1,
    is_required BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (domain_type_id) REFERENCES domain_types(id) ON DELETE CASCADE,
    FOREIGN KEY (workflow_phase_id) REFERENCES workflow_phases(id) ON DELETE CASCADE,
    UNIQUE (domain_type_id, workflow_phase_id)
);

-- Mark migration as applied
INSERT INTO django_migrations (app, name, applied) 
VALUES ('bfagent', '0056_domainart_domaintype_domainphase', datetime('now'));