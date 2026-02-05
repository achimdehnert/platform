-- =============================================================================
-- DDL Governance Seed Data (ADR-017)
-- =============================================================================
-- Idempotent: Uses INSERT ... ON CONFLICT DO UPDATE
-- Run with: psql -f seed_lookups.sql
-- =============================================================================

-- Ensure platform schema exists
CREATE SCHEMA IF NOT EXISTS platform;

-- =============================================================================
-- LOOKUP DOMAINS
-- =============================================================================

INSERT INTO platform.lkp_domain (code, name, name_de, description, is_active, created_at, updated_at)
VALUES
    -- Business Case domains
    ('bc_status', 'Business Case Status', 'Business Case Status', 'Status values for Business Cases', true, NOW(), NOW()),
    ('bc_category', 'Business Case Category', 'Business Case Kategorie', 'Categories for Business Cases', true, NOW(), NOW()),
    ('bc_priority', 'Business Case Priority', 'Business Case Priorität', 'Priority levels for Business Cases', true, NOW(), NOW()),
    
    -- Use Case domains
    ('uc_status', 'Use Case Status', 'Use Case Status', 'Status values for Use Cases', true, NOW(), NOW()),
    ('uc_priority', 'Use Case Priority', 'Use Case Priorität', 'Priority levels for Use Cases', true, NOW(), NOW()),
    ('uc_complexity', 'Use Case Complexity', 'Use Case Komplexität', 'Complexity levels for Use Cases', true, NOW(), NOW()),
    
    -- ADR domains
    ('adr_status', 'ADR Status', 'ADR Status', 'Status values for ADRs', true, NOW(), NOW()),
    ('adr_uc_relationship', 'ADR-UC Relationship', 'ADR-UC Beziehung', 'Relationship types between ADRs and Use Cases', true, NOW(), NOW()),
    
    -- Conversation domains
    ('conversation_status', 'Conversation Status', 'Konversation Status', 'Status of inception conversations', true, NOW(), NOW()),
    ('conversation_role', 'Conversation Role', 'Konversation Rolle', 'Role in conversation (user/assistant/system)', true, NOW(), NOW()),
    
    -- Review domains
    ('review_entity_type', 'Review Entity Type', 'Review Entity Typ', 'Type of entity being reviewed', true, NOW(), NOW()),
    ('review_decision', 'Review Decision', 'Review Entscheidung', 'Review decision outcomes', true, NOW(), NOW())
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    name_de = EXCLUDED.name_de,
    description = EXCLUDED.description,
    updated_at = NOW();

-- =============================================================================
-- LOOKUP CHOICES: Business Case Status
-- =============================================================================

INSERT INTO platform.lkp_choice (domain_id, code, name, name_de, description, sort_order, color, icon, metadata, is_active, created_at, updated_at)
SELECT d.id, v.code, v.name, v.name_de, v.name, v.sort_order, v.color, v.icon, '{}', true, NOW(), NOW()
FROM platform.lkp_domain d
CROSS JOIN (VALUES
    ('draft', 'Draft', 'Entwurf', 10, '#6c757d', 'bi-pencil'),
    ('submitted', 'Submitted', 'Eingereicht', 20, '#17a2b8', 'bi-send'),
    ('in_review', 'In Review', 'In Prüfung', 30, '#ffc107', 'bi-eye'),
    ('approved', 'Approved', 'Genehmigt', 40, '#28a745', 'bi-check-circle'),
    ('rejected', 'Rejected', 'Abgelehnt', 50, '#dc3545', 'bi-x-circle'),
    ('on_hold', 'On Hold', 'Pausiert', 60, '#6c757d', 'bi-pause-circle'),
    ('archived', 'Archived', 'Archiviert', 70, '#6c757d', 'bi-archive')
) AS v(code, name, name_de, sort_order, color, icon)
WHERE d.code = 'bc_status'
ON CONFLICT (domain_id, code) DO UPDATE SET
    name = EXCLUDED.name,
    name_de = EXCLUDED.name_de,
    sort_order = EXCLUDED.sort_order,
    color = EXCLUDED.color,
    icon = EXCLUDED.icon,
    updated_at = NOW();

-- =============================================================================
-- LOOKUP CHOICES: Business Case Category
-- =============================================================================

INSERT INTO platform.lkp_choice (domain_id, code, name, name_de, description, sort_order, color, icon, metadata, is_active, created_at, updated_at)
SELECT d.id, v.code, v.name, v.name_de, v.name, v.sort_order, v.color, v.icon, '{}', true, NOW(), NOW()
FROM platform.lkp_domain d
CROSS JOIN (VALUES
    ('feature', 'New Feature', 'Neue Funktion', 10, '#007bff', 'bi-plus-circle'),
    ('enhancement', 'Enhancement', 'Verbesserung', 20, '#17a2b8', 'bi-arrow-up-circle'),
    ('bugfix', 'Bug Fix', 'Fehlerbehebung', 30, '#dc3545', 'bi-bug'),
    ('refactoring', 'Refactoring', 'Refactoring', 40, '#6f42c1', 'bi-recycle'),
    ('infrastructure', 'Infrastructure', 'Infrastruktur', 50, '#fd7e14', 'bi-server'),
    ('documentation', 'Documentation', 'Dokumentation', 60, '#20c997', 'bi-file-text'),
    ('security', 'Security', 'Sicherheit', 70, '#dc3545', 'bi-shield-check')
) AS v(code, name, name_de, sort_order, color, icon)
WHERE d.code = 'bc_category'
ON CONFLICT (domain_id, code) DO UPDATE SET
    name = EXCLUDED.name,
    name_de = EXCLUDED.name_de,
    sort_order = EXCLUDED.sort_order,
    color = EXCLUDED.color,
    icon = EXCLUDED.icon,
    updated_at = NOW();

-- =============================================================================
-- LOOKUP CHOICES: Business Case Priority
-- =============================================================================

INSERT INTO platform.lkp_choice (domain_id, code, name, name_de, description, sort_order, color, icon, metadata, is_active, created_at, updated_at)
SELECT d.id, v.code, v.name, v.name_de, v.name, v.sort_order, v.color, v.icon, '{}', true, NOW(), NOW()
FROM platform.lkp_domain d
CROSS JOIN (VALUES
    ('critical', 'Critical', 'Kritisch', 10, '#dc3545', 'bi-exclamation-triangle'),
    ('high', 'High', 'Hoch', 20, '#fd7e14', 'bi-arrow-up'),
    ('medium', 'Medium', 'Mittel', 30, '#ffc107', 'bi-dash'),
    ('low', 'Low', 'Niedrig', 40, '#28a745', 'bi-arrow-down')
) AS v(code, name, name_de, sort_order, color, icon)
WHERE d.code = 'bc_priority'
ON CONFLICT (domain_id, code) DO UPDATE SET
    name = EXCLUDED.name,
    name_de = EXCLUDED.name_de,
    sort_order = EXCLUDED.sort_order,
    color = EXCLUDED.color,
    icon = EXCLUDED.icon,
    updated_at = NOW();

-- =============================================================================
-- LOOKUP CHOICES: Use Case Status
-- =============================================================================

INSERT INTO platform.lkp_choice (domain_id, code, name, name_de, description, sort_order, color, icon, metadata, is_active, created_at, updated_at)
SELECT d.id, v.code, v.name, v.name_de, v.name, v.sort_order, v.color, v.icon, '{}', true, NOW(), NOW()
FROM platform.lkp_domain d
CROSS JOIN (VALUES
    ('draft', 'Draft', 'Entwurf', 10, '#6c757d', 'bi-pencil'),
    ('defined', 'Defined', 'Definiert', 20, '#17a2b8', 'bi-check'),
    ('approved', 'Approved', 'Genehmigt', 30, '#28a745', 'bi-check-circle'),
    ('implemented', 'Implemented', 'Implementiert', 40, '#007bff', 'bi-code'),
    ('tested', 'Tested', 'Getestet', 50, '#20c997', 'bi-clipboard-check'),
    ('deployed', 'Deployed', 'Deployed', 60, '#6f42c1', 'bi-rocket'),
    ('deprecated', 'Deprecated', 'Veraltet', 70, '#6c757d', 'bi-archive')
) AS v(code, name, name_de, sort_order, color, icon)
WHERE d.code = 'uc_status'
ON CONFLICT (domain_id, code) DO UPDATE SET
    name = EXCLUDED.name,
    name_de = EXCLUDED.name_de,
    sort_order = EXCLUDED.sort_order,
    color = EXCLUDED.color,
    icon = EXCLUDED.icon,
    updated_at = NOW();

-- =============================================================================
-- LOOKUP CHOICES: Use Case Priority (same as BC Priority)
-- =============================================================================

INSERT INTO platform.lkp_choice (domain_id, code, name, name_de, description, sort_order, color, icon, metadata, is_active, created_at, updated_at)
SELECT d.id, v.code, v.name, v.name_de, v.name, v.sort_order, v.color, v.icon, '{}', true, NOW(), NOW()
FROM platform.lkp_domain d
CROSS JOIN (VALUES
    ('critical', 'Critical', 'Kritisch', 10, '#dc3545', 'bi-exclamation-triangle'),
    ('high', 'High', 'Hoch', 20, '#fd7e14', 'bi-arrow-up'),
    ('medium', 'Medium', 'Mittel', 30, '#ffc107', 'bi-dash'),
    ('low', 'Low', 'Niedrig', 40, '#28a745', 'bi-arrow-down')
) AS v(code, name, name_de, sort_order, color, icon)
WHERE d.code = 'uc_priority'
ON CONFLICT (domain_id, code) DO UPDATE SET
    name = EXCLUDED.name,
    name_de = EXCLUDED.name_de,
    sort_order = EXCLUDED.sort_order,
    color = EXCLUDED.color,
    icon = EXCLUDED.icon,
    updated_at = NOW();

-- =============================================================================
-- LOOKUP CHOICES: Use Case Complexity
-- =============================================================================

INSERT INTO platform.lkp_choice (domain_id, code, name, name_de, description, sort_order, color, icon, metadata, is_active, created_at, updated_at)
SELECT d.id, v.code, v.name, v.name_de, v.name, v.sort_order, v.color, v.icon, '{}', true, NOW(), NOW()
FROM platform.lkp_domain d
CROSS JOIN (VALUES
    ('trivial', 'Trivial', 'Trivial', 10, '#28a745', 'bi-1-circle'),
    ('simple', 'Simple', 'Einfach', 20, '#20c997', 'bi-2-circle'),
    ('moderate', 'Moderate', 'Moderat', 30, '#ffc107', 'bi-3-circle'),
    ('complex', 'Complex', 'Komplex', 40, '#fd7e14', 'bi-4-circle'),
    ('very_complex', 'Very Complex', 'Sehr Komplex', 50, '#dc3545', 'bi-5-circle')
) AS v(code, name, name_de, sort_order, color, icon)
WHERE d.code = 'uc_complexity'
ON CONFLICT (domain_id, code) DO UPDATE SET
    name = EXCLUDED.name,
    name_de = EXCLUDED.name_de,
    sort_order = EXCLUDED.sort_order,
    color = EXCLUDED.color,
    icon = EXCLUDED.icon,
    updated_at = NOW();

-- =============================================================================
-- LOOKUP CHOICES: ADR Status
-- =============================================================================

INSERT INTO platform.lkp_choice (domain_id, code, name, name_de, description, sort_order, color, icon, metadata, is_active, created_at, updated_at)
SELECT d.id, v.code, v.name, v.name_de, v.name, v.sort_order, v.color, v.icon, '{}', true, NOW(), NOW()
FROM platform.lkp_domain d
CROSS JOIN (VALUES
    ('draft', 'Draft', 'Entwurf', 10, '#6c757d', 'bi-pencil'),
    ('proposed', 'Proposed', 'Vorgeschlagen', 20, '#17a2b8', 'bi-send'),
    ('accepted', 'Accepted', 'Akzeptiert', 30, '#28a745', 'bi-check-circle'),
    ('deprecated', 'Deprecated', 'Veraltet', 40, '#ffc107', 'bi-exclamation-triangle'),
    ('superseded', 'Superseded', 'Ersetzt', 50, '#6c757d', 'bi-arrow-repeat')
) AS v(code, name, name_de, sort_order, color, icon)
WHERE d.code = 'adr_status'
ON CONFLICT (domain_id, code) DO UPDATE SET
    name = EXCLUDED.name,
    name_de = EXCLUDED.name_de,
    sort_order = EXCLUDED.sort_order,
    color = EXCLUDED.color,
    icon = EXCLUDED.icon,
    updated_at = NOW();

-- =============================================================================
-- LOOKUP CHOICES: ADR-UC Relationship
-- =============================================================================

INSERT INTO platform.lkp_choice (domain_id, code, name, name_de, description, sort_order, color, icon, metadata, is_active, created_at, updated_at)
SELECT d.id, v.code, v.name, v.name_de, v.name, v.sort_order, v.color, v.icon, '{}', true, NOW(), NOW()
FROM platform.lkp_domain d
CROSS JOIN (VALUES
    ('implements', 'Implements', 'Implementiert', 10, '#007bff', 'bi-code'),
    ('affects', 'Affects', 'Beeinflusst', 20, '#ffc107', 'bi-lightning'),
    ('references', 'References', 'Referenziert', 30, '#6c757d', 'bi-link')
) AS v(code, name, name_de, sort_order, color, icon)
WHERE d.code = 'adr_uc_relationship'
ON CONFLICT (domain_id, code) DO UPDATE SET
    name = EXCLUDED.name,
    name_de = EXCLUDED.name_de,
    sort_order = EXCLUDED.sort_order,
    color = EXCLUDED.color,
    icon = EXCLUDED.icon,
    updated_at = NOW();

-- =============================================================================
-- LOOKUP CHOICES: Conversation Status
-- =============================================================================

INSERT INTO platform.lkp_choice (domain_id, code, name, name_de, description, sort_order, color, icon, metadata, is_active, created_at, updated_at)
SELECT d.id, v.code, v.name, v.name_de, v.name, v.sort_order, v.color, v.icon, '{}', true, NOW(), NOW()
FROM platform.lkp_domain d
CROSS JOIN (VALUES
    ('active', 'Active', 'Aktiv', 10, '#28a745', 'bi-chat-dots'),
    ('paused', 'Paused', 'Pausiert', 20, '#ffc107', 'bi-pause-circle'),
    ('completed', 'Completed', 'Abgeschlossen', 30, '#007bff', 'bi-check-circle'),
    ('abandoned', 'Abandoned', 'Abgebrochen', 40, '#6c757d', 'bi-x-circle')
) AS v(code, name, name_de, sort_order, color, icon)
WHERE d.code = 'conversation_status'
ON CONFLICT (domain_id, code) DO UPDATE SET
    name = EXCLUDED.name,
    name_de = EXCLUDED.name_de,
    sort_order = EXCLUDED.sort_order,
    color = EXCLUDED.color,
    icon = EXCLUDED.icon,
    updated_at = NOW();

-- =============================================================================
-- LOOKUP CHOICES: Conversation Role
-- =============================================================================

INSERT INTO platform.lkp_choice (domain_id, code, name, name_de, description, sort_order, color, icon, metadata, is_active, created_at, updated_at)
SELECT d.id, v.code, v.name, v.name_de, v.name, v.sort_order, v.color, v.icon, '{}', true, NOW(), NOW()
FROM platform.lkp_domain d
CROSS JOIN (VALUES
    ('user', 'User', 'Benutzer', 10, '#007bff', 'bi-person'),
    ('assistant', 'Assistant', 'Assistent', 20, '#28a745', 'bi-robot'),
    ('system', 'System', 'System', 30, '#6c757d', 'bi-gear')
) AS v(code, name, name_de, sort_order, color, icon)
WHERE d.code = 'conversation_role'
ON CONFLICT (domain_id, code) DO UPDATE SET
    name = EXCLUDED.name,
    name_de = EXCLUDED.name_de,
    sort_order = EXCLUDED.sort_order,
    color = EXCLUDED.color,
    icon = EXCLUDED.icon,
    updated_at = NOW();

-- =============================================================================
-- LOOKUP CHOICES: Review Entity Type
-- =============================================================================

INSERT INTO platform.lkp_choice (domain_id, code, name, name_de, description, sort_order, color, icon, metadata, is_active, created_at, updated_at)
SELECT d.id, v.code, v.name, v.name_de, v.name, v.sort_order, v.color, v.icon, '{}', true, NOW(), NOW()
FROM platform.lkp_domain d
CROSS JOIN (VALUES
    ('business_case', 'Business Case', 'Business Case', 10, '#007bff', 'bi-briefcase'),
    ('use_case', 'Use Case', 'Use Case', 20, '#17a2b8', 'bi-person-workspace'),
    ('adr', 'ADR', 'ADR', 30, '#6f42c1', 'bi-file-earmark-text')
) AS v(code, name, name_de, sort_order, color, icon)
WHERE d.code = 'review_entity_type'
ON CONFLICT (domain_id, code) DO UPDATE SET
    name = EXCLUDED.name,
    name_de = EXCLUDED.name_de,
    sort_order = EXCLUDED.sort_order,
    color = EXCLUDED.color,
    icon = EXCLUDED.icon,
    updated_at = NOW();

-- =============================================================================
-- LOOKUP CHOICES: Review Decision
-- =============================================================================

INSERT INTO platform.lkp_choice (domain_id, code, name, name_de, description, sort_order, color, icon, metadata, is_active, created_at, updated_at)
SELECT d.id, v.code, v.name, v.name_de, v.name, v.sort_order, v.color, v.icon, '{}', true, NOW(), NOW()
FROM platform.lkp_domain d
CROSS JOIN (VALUES
    ('approved', 'Approved', 'Genehmigt', 10, '#28a745', 'bi-check-circle'),
    ('rejected', 'Rejected', 'Abgelehnt', 20, '#dc3545', 'bi-x-circle'),
    ('changes_requested', 'Changes Requested', 'Änderungen angefordert', 30, '#ffc107', 'bi-pencil-square')
) AS v(code, name, name_de, sort_order, color, icon)
WHERE d.code = 'review_decision'
ON CONFLICT (domain_id, code) DO UPDATE SET
    name = EXCLUDED.name,
    name_de = EXCLUDED.name_de,
    sort_order = EXCLUDED.sort_order,
    color = EXCLUDED.color,
    icon = EXCLUDED.icon,
    updated_at = NOW();

-- =============================================================================
-- VERIFICATION
-- =============================================================================

SELECT 
    d.code AS domain,
    COUNT(c.id) AS choice_count
FROM platform.lkp_domain d
LEFT JOIN platform.lkp_choice c ON c.domain_id = d.id
GROUP BY d.code
ORDER BY d.code;
