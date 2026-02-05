ALTER TABLE platform.dom_business_case ADD COLUMN IF NOT EXISTS owner_id INTEGER;
ALTER TABLE platform.dom_use_case ADD COLUMN IF NOT EXISTS exception_flows JSONB DEFAULT '[]'::jsonb;
ALTER TABLE platform.dom_use_case ADD COLUMN IF NOT EXISTS estimated_effort VARCHAR(50);
ALTER TABLE platform.lkp_choice ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE platform.lkp_choice ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;

INSERT INTO platform.lkp_domain (code, name, name_de, description) 
VALUES ('uc_priority', 'UC Priority', 'UC Priorität', 'Use Case priority')
ON CONFLICT (code) DO NOTHING;

INSERT INTO platform.lkp_domain (code, name, name_de, description)
VALUES ('uc_complexity', 'UC Complexity', 'UC Komplexität', 'Use Case complexity')
ON CONFLICT (code) DO NOTHING;
