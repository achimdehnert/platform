-- Create DDL tables for Inception MCP (ADR-017)
CREATE SCHEMA IF NOT EXISTS platform;

-- Lookup Domain
CREATE TABLE IF NOT EXISTS platform.lkp_domain (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    name_de VARCHAR(100),
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Lookup Choice
CREATE TABLE IF NOT EXISTS platform.lkp_choice (
    id SERIAL PRIMARY KEY,
    domain_id INTEGER REFERENCES platform.lkp_domain(id),
    code VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    name_de VARCHAR(100),
    sort_order INTEGER DEFAULT 0,
    color VARCHAR(20),
    icon VARCHAR(50),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(domain_id, code)
);

-- Business Case
CREATE TABLE IF NOT EXISTS platform.dom_business_case (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,
    title VARCHAR(200) NOT NULL,
    category_id INTEGER REFERENCES platform.lkp_choice(id),
    status_id INTEGER REFERENCES platform.lkp_choice(id),
    priority_id INTEGER REFERENCES platform.lkp_choice(id),
    problem_statement TEXT,
    target_audience TEXT,
    expected_benefits JSONB,
    scope TEXT,
    out_of_scope JSONB,
    success_criteria JSONB,
    assumptions JSONB,
    risks JSONB,
    requires_adr BOOLEAN DEFAULT false,
    adr_reason TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Use Case
CREATE TABLE IF NOT EXISTS platform.dom_use_case (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,
    title VARCHAR(200) NOT NULL,
    business_case_id INTEGER REFERENCES platform.dom_business_case(id),
    status_id INTEGER REFERENCES platform.lkp_choice(id),
    priority_id INTEGER REFERENCES platform.lkp_choice(id),
    complexity_id INTEGER REFERENCES platform.lkp_choice(id),
    actor VARCHAR(100),
    preconditions JSONB,
    main_flow JSONB,
    alternative_flows JSONB,
    postconditions JSONB,
    business_rules JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Conversation
CREATE TABLE IF NOT EXISTS platform.dom_conversation (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) UNIQUE NOT NULL,
    business_case_id INTEGER REFERENCES platform.dom_business_case(id),
    status_id INTEGER REFERENCES platform.lkp_choice(id),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Conversation Turn
CREATE TABLE IF NOT EXISTS platform.dom_conversation_turn (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER REFERENCES platform.dom_conversation(id),
    role_id INTEGER REFERENCES platform.lkp_choice(id),
    content TEXT,
    extracted_data JSONB,
    turn_number INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Status History
CREATE TABLE IF NOT EXISTS platform.dom_status_history (
    id SERIAL PRIMARY KEY,
    entity_type_id INTEGER REFERENCES platform.lkp_choice(id),
    entity_id INTEGER NOT NULL,
    old_status_id INTEGER REFERENCES platform.lkp_choice(id),
    new_status_id INTEGER REFERENCES platform.lkp_choice(id),
    changed_by VARCHAR(100),
    reason TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Seed lookup domains
INSERT INTO platform.lkp_domain (code, name, name_de, description) VALUES
    ('bc_status', 'BC Status', 'BC Status', 'Business Case status'),
    ('bc_category', 'BC Category', 'BC Kategorie', 'Business Case category'),
    ('bc_priority', 'BC Priority', 'BC Priorität', 'Business Case priority'),
    ('uc_status', 'UC Status', 'UC Status', 'Use Case status'),
    ('conversation_status', 'Conv Status', 'Konv Status', 'Conversation status'),
    ('conversation_role', 'Conv Role', 'Konv Rolle', 'Conversation role'),
    ('review_entity_type', 'Entity Type', 'Entity Typ', 'Review entity type')
ON CONFLICT (code) DO NOTHING;

-- Seed BC status choices
INSERT INTO platform.lkp_choice (domain_id, code, name, name_de, sort_order, color)
SELECT d.id, v.code, v.name, v.name_de, v.sort_order, v.color
FROM platform.lkp_domain d, (VALUES
    ('draft', 'Draft', 'Entwurf', 1, '#6c757d'),
    ('submitted', 'Submitted', 'Eingereicht', 2, '#0d6efd'),
    ('in_review', 'In Review', 'In Prüfung', 3, '#ffc107'),
    ('approved', 'Approved', 'Genehmigt', 4, '#198754'),
    ('rejected', 'Rejected', 'Abgelehnt', 5, '#dc3545'),
    ('archived', 'Archived', 'Archiviert', 6, '#6c757d')
) AS v(code, name, name_de, sort_order, color)
WHERE d.code = 'bc_status'
ON CONFLICT (domain_id, code) DO NOTHING;

-- Seed BC category choices
INSERT INTO platform.lkp_choice (domain_id, code, name, name_de, sort_order, color)
SELECT d.id, v.code, v.name, v.name_de, v.sort_order, v.color
FROM platform.lkp_domain d, (VALUES
    ('feature', 'Feature', 'Funktion', 1, '#0d6efd'),
    ('enhancement', 'Enhancement', 'Verbesserung', 2, '#20c997'),
    ('bugfix', 'Bug Fix', 'Fehlerbehebung', 3, '#dc3545'),
    ('technical', 'Technical', 'Technisch', 4, '#6f42c1'),
    ('compliance', 'Compliance', 'Compliance', 5, '#fd7e14')
) AS v(code, name, name_de, sort_order, color)
WHERE d.code = 'bc_category'
ON CONFLICT (domain_id, code) DO NOTHING;

-- Seed conversation status
INSERT INTO platform.lkp_choice (domain_id, code, name, name_de, sort_order)
SELECT d.id, v.code, v.name, v.name_de, v.sort_order
FROM platform.lkp_domain d, (VALUES
    ('active', 'Active', 'Aktiv', 1),
    ('completed', 'Completed', 'Abgeschlossen', 2),
    ('abandoned', 'Abandoned', 'Abgebrochen', 3)
) AS v(code, name, name_de, sort_order)
WHERE d.code = 'conversation_status'
ON CONFLICT (domain_id, code) DO NOTHING;

-- Seed UC status
INSERT INTO platform.lkp_choice (domain_id, code, name, name_de, sort_order, color)
SELECT d.id, v.code, v.name, v.name_de, v.sort_order, v.color
FROM platform.lkp_domain d, (VALUES
    ('draft', 'Draft', 'Entwurf', 1, '#6c757d'),
    ('detailed', 'Detailed', 'Detailliert', 2, '#0d6efd'),
    ('approved', 'Approved', 'Genehmigt', 3, '#198754')
) AS v(code, name, name_de, sort_order, color)
WHERE d.code = 'uc_status'
ON CONFLICT (domain_id, code) DO NOTHING;

-- Seed review entity type
INSERT INTO platform.lkp_choice (domain_id, code, name, name_de, sort_order)
SELECT d.id, v.code, v.name, v.name_de, v.sort_order
FROM platform.lkp_domain d, (VALUES
    ('business_case', 'Business Case', 'Business Case', 1),
    ('use_case', 'Use Case', 'Use Case', 2),
    ('adr', 'ADR', 'ADR', 3)
) AS v(code, name, name_de, sort_order)
WHERE d.code = 'review_entity_type'
ON CONFLICT (domain_id, code) DO NOTHING;
