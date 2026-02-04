-- Add missing columns to match Django models (ADR-017)

-- Business Case: add owner_id (nullable FK to auth_user)
ALTER TABLE platform.dom_business_case 
ADD COLUMN IF NOT EXISTS owner_id INTEGER;

-- Use Case: add missing columns
ALTER TABLE platform.dom_use_case 
ADD COLUMN IF NOT EXISTS exception_flows JSONB DEFAULT '[]'::jsonb;

ALTER TABLE platform.dom_use_case 
ADD COLUMN IF NOT EXISTS estimated_effort VARCHAR(50);

-- lkp_choice: add description column
ALTER TABLE platform.lkp_choice
ADD COLUMN IF NOT EXISTS description TEXT;

-- Seed uc_priority if missing
INSERT INTO platform.lkp_domain (code, name, name_de, description) 
VALUES ('uc_priority', 'UC Priority', 'UC Priorität', 'Use Case priority')
ON CONFLICT (code) DO NOTHING;

INSERT INTO platform.lkp_choice (domain_id, code, name, name_de, sort_order, color)
SELECT d.id, v.code, v.name, v.name_de, v.sort_order, v.color
FROM platform.lkp_domain d, (VALUES
    ('high', 'High', 'Hoch', 1, '#dc3545'),
    ('medium', 'Medium', 'Mittel', 2, '#ffc107'),
    ('low', 'Low', 'Niedrig', 3, '#198754')
) AS v(code, name, name_de, sort_order, color)
WHERE d.code = 'uc_priority'
ON CONFLICT (domain_id, code) DO NOTHING;

-- Seed uc_complexity if missing  
INSERT INTO platform.lkp_domain (code, name, name_de, description)
VALUES ('uc_complexity', 'UC Complexity', 'UC Komplexität', 'Use Case complexity')
ON CONFLICT (code) DO NOTHING;

INSERT INTO platform.lkp_choice (domain_id, code, name, name_de, sort_order, color)
SELECT d.id, v.code, v.name, v.name_de, v.sort_order, v.color
FROM platform.lkp_domain d, (VALUES
    ('simple', 'Simple', 'Einfach', 1, '#198754'),
    ('moderate', 'Moderate', 'Mittel', 2, '#ffc107'),
    ('complex', 'Complex', 'Komplex', 3, '#dc3545')
) AS v(code, name, name_de, sort_order, color)
WHERE d.code = 'uc_complexity'
ON CONFLICT (domain_id, code) DO NOTHING;

-- Seed bc_priority if missing
INSERT INTO platform.lkp_domain (code, name, name_de, description)
VALUES ('bc_priority', 'BC Priority', 'BC Priorität', 'Business Case priority')
ON CONFLICT (code) DO NOTHING;

INSERT INTO platform.lkp_choice (domain_id, code, name, name_de, sort_order, color)
SELECT d.id, v.code, v.name, v.name_de, v.sort_order, v.color
FROM platform.lkp_domain d, (VALUES
    ('critical', 'Critical', 'Kritisch', 1, '#dc3545'),
    ('high', 'High', 'Hoch', 2, '#fd7e14'),
    ('medium', 'Medium', 'Mittel', 3, '#ffc107'),
    ('low', 'Low', 'Niedrig', 4, '#198754')
) AS v(code, name, name_de, sort_order, color)
WHERE d.code = 'bc_priority'
ON CONFLICT (domain_id, code) DO NOTHING;
