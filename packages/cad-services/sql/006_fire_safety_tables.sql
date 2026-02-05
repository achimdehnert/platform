-- ============================================
-- ADR-009: Brandschutz-Tabellen
-- Datum: 2026-02-02
-- ============================================

-- Brandabschnitte
CREATE TABLE IF NOT EXISTS cadhub_fire_compartment (
    id SERIAL PRIMARY KEY,
    cad_model_id INTEGER NOT NULL REFERENCES cadhub_cad_model(id) ON DELETE CASCADE,
    floor_id INTEGER REFERENCES cadhub_floor(id) ON DELETE SET NULL,
    
    -- Identifikation
    name VARCHAR(255) NOT NULL,
    ifc_zone_guid VARCHAR(36),
    
    -- Eigenschaften
    area_m2 DECIMAL(12,2) NOT NULL DEFAULT 0,
    max_area_m2 DECIMAL(12,2) NOT NULL DEFAULT 1600,
    has_sprinkler BOOLEAN DEFAULT FALSE,
    fire_load_mj_m2 DECIMAL(10,2),
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending'
        CHECK (status IN ('pending', 'compliant', 'warning', 'violation')),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_fire_compartment_model ON cadhub_fire_compartment(cad_model_id);
CREATE INDEX idx_fire_compartment_floor ON cadhub_fire_compartment(floor_id);

-- Elemente mit Brandschutzanforderungen
CREATE TABLE IF NOT EXISTS cadhub_fire_rated_element (
    id SERIAL PRIMARY KEY,
    cad_model_id INTEGER NOT NULL REFERENCES cadhub_cad_model(id) ON DELETE CASCADE,
    compartment_id INTEGER REFERENCES cadhub_fire_compartment(id) ON DELETE SET NULL,
    
    -- Element-Referenz
    element_type VARCHAR(50) NOT NULL,  -- 'wall', 'door', 'slab'
    element_id INTEGER,  -- FK zu cadhub_wall, cadhub_door, etc.
    ifc_guid VARCHAR(36),
    name VARCHAR(255),
    
    -- Anforderung
    required_rating VARCHAR(20),  -- F30, F60, F90, T30, etc.
    required_standard VARCHAR(20) DEFAULT 'din4102'
        CHECK (required_standard IN ('din4102', 'en13501')),
    requirement_source VARCHAR(255),  -- z.B. "MBO §28 Abs. 2"
    
    -- Ist-Zustand (aus IFC)
    actual_rating VARCHAR(20),
    actual_standard VARCHAR(20),
    
    -- Bewertung
    is_compliant BOOLEAN,
    compliance_note TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_fire_rated_model ON cadhub_fire_rated_element(cad_model_id);
CREATE INDEX idx_fire_rated_compartment ON cadhub_fire_rated_element(compartment_id);
CREATE INDEX idx_fire_rated_type ON cadhub_fire_rated_element(element_type);

-- Fluchtwege
CREATE TABLE IF NOT EXISTS cadhub_escape_route (
    id SERIAL PRIMARY KEY,
    cad_model_id INTEGER NOT NULL REFERENCES cadhub_cad_model(id) ON DELETE CASCADE,
    floor_id INTEGER REFERENCES cadhub_floor(id) ON DELETE SET NULL,
    
    -- Start/Ende
    from_room_id INTEGER NOT NULL REFERENCES cadhub_room(id) ON DELETE CASCADE,
    to_exit_type VARCHAR(50) NOT NULL 
        CHECK (to_exit_type IN ('external', 'stairway', 'compartment', 'window')),
    to_element_id INTEGER,  -- Optional: Referenz zum Ausgang
    
    -- Messwerte
    distance_m DECIMAL(8,2) NOT NULL,
    max_distance_m DECIMAL(8,2) NOT NULL DEFAULT 35,
    
    -- Breiten
    min_width_m DECIMAL(5,2),
    required_width_m DECIMAL(5,2) DEFAULT 0.90,
    
    -- Bewertung
    is_compliant BOOLEAN,
    route_type VARCHAR(20) DEFAULT 'primary'
        CHECK (route_type IN ('primary', 'secondary')),
    
    -- Pfad (für Visualisierung)
    path_points TEXT,  -- JSON array of [x,y] coordinates
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_escape_route_model ON cadhub_escape_route(cad_model_id);
CREATE INDEX idx_escape_route_room ON cadhub_escape_route(from_room_id);

-- Stammdaten: Feuerwiderstandsklassen
CREATE TABLE IF NOT EXISTS cadhub_fire_rating_ref (
    code VARCHAR(20) PRIMARY KEY,
    standard VARCHAR(20) NOT NULL,  -- din4102, en13501
    minutes INTEGER NOT NULL,
    description VARCHAR(255),
    element_types TEXT[]  -- ['wall', 'door', 'slab']
);

INSERT INTO cadhub_fire_rating_ref (code, standard, minutes, description, element_types) VALUES
    ('F30', 'din4102', 30, 'Feuerhemmend', ARRAY['wall', 'slab']),
    ('F60', 'din4102', 60, 'Hochfeuerhemmend', ARRAY['wall', 'slab']),
    ('F90', 'din4102', 90, 'Feuerbeständig', ARRAY['wall', 'slab']),
    ('F120', 'din4102', 120, 'Hochfeuerbeständig', ARRAY['wall', 'slab']),
    ('T30', 'din4102', 30, 'Feuerschutztür T30', ARRAY['door']),
    ('T60', 'din4102', 60, 'Feuerschutztür T60', ARRAY['door']),
    ('T90', 'din4102', 90, 'Feuerschutztür T90', ARRAY['door']),
    ('REI30', 'en13501', 30, 'Tragfähigkeit/Raumabschluss/Dämmung 30min', ARRAY['wall', 'slab']),
    ('REI60', 'en13501', 60, 'Tragfähigkeit/Raumabschluss/Dämmung 60min', ARRAY['wall', 'slab']),
    ('REI90', 'en13501', 90, 'Tragfähigkeit/Raumabschluss/Dämmung 90min', ARRAY['wall', 'slab']),
    ('EI30', 'en13501', 30, 'Raumabschluss/Dämmung 30min', ARRAY['door']),
    ('EI60', 'en13501', 60, 'Raumabschluss/Dämmung 60min', ARRAY['door'])
ON CONFLICT (code) DO NOTHING;

-- Stammdaten: Fluchtweg-Parameter
CREATE TABLE IF NOT EXISTS cadhub_escape_params_ref (
    building_type VARCHAR(50) PRIMARY KEY,
    max_distance_m DECIMAL(8,2) NOT NULL,
    max_distance_sprinkler_m DECIMAL(8,2),
    min_door_width_m DECIMAL(5,2) DEFAULT 0.90,
    min_corridor_width_m DECIMAL(5,2) DEFAULT 1.20,
    persons_per_stair_width_m INTEGER DEFAULT 150,
    description VARCHAR(255)
);

INSERT INTO cadhub_escape_params_ref VALUES
    ('standard', 35, 70, 0.90, 1.20, 150, 'Standardgebäude nach MBO'),
    ('industrial', 50, 100, 1.00, 1.50, 200, 'Industriegebäude'),
    ('high_rise', 25, 50, 0.90, 1.20, 150, 'Hochhaus (>22m)'),
    ('assembly', 30, 60, 1.20, 2.00, 100, 'Versammlungsstätte'),
    ('healthcare', 30, 60, 1.20, 2.40, 80, 'Krankenhaus/Pflegeheim')
ON CONFLICT (building_type) DO NOTHING;

-- RLS Policies
ALTER TABLE cadhub_fire_compartment ENABLE ROW LEVEL SECURITY;
ALTER TABLE cadhub_fire_rated_element ENABLE ROW LEVEL SECURITY;
ALTER TABLE cadhub_escape_route ENABLE ROW LEVEL SECURITY;

-- Tenant-basierte Policies (via cad_model -> project -> tenant)
CREATE POLICY fire_compartment_tenant_policy ON cadhub_fire_compartment
    FOR ALL
    USING (
        cad_model_id IN (
            SELECT m.id FROM cadhub_cad_model m
            JOIN cadhub_project p ON m.project_id = p.id
            WHERE p.tenant_id = current_setting('app.tenant_id')::INTEGER
        )
    );

CREATE POLICY fire_rated_tenant_policy ON cadhub_fire_rated_element
    FOR ALL
    USING (
        cad_model_id IN (
            SELECT m.id FROM cadhub_cad_model m
            JOIN cadhub_project p ON m.project_id = p.id
            WHERE p.tenant_id = current_setting('app.tenant_id')::INTEGER
        )
    );

CREATE POLICY escape_route_tenant_policy ON cadhub_escape_route
    FOR ALL
    USING (
        cad_model_id IN (
            SELECT m.id FROM cadhub_cad_model m
            JOIN cadhub_project p ON m.project_id = p.id
            WHERE p.tenant_id = current_setting('app.tenant_id')::INTEGER
        )
    );

-- Hilfsfunktion: Rating-Vergleich
CREATE OR REPLACE FUNCTION fire_rating_minutes(rating VARCHAR) 
RETURNS INTEGER AS $$
BEGIN
    RETURN COALESCE(
        (SELECT minutes FROM cadhub_fire_rating_ref WHERE code = rating),
        CAST(SUBSTRING(rating FROM '[0-9]+') AS INTEGER)
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- View: Brandschutz-Übersicht pro Modell
CREATE OR REPLACE VIEW v_fire_safety_summary AS
SELECT 
    m.id AS model_id,
    m.name AS model_name,
    p.id AS project_id,
    p.name AS project_name,
    COUNT(DISTINCT fc.id) AS compartment_count,
    COUNT(DISTINCT fre.id) AS rated_element_count,
    COUNT(DISTINCT er.id) AS escape_route_count,
    COUNT(DISTINCT CASE WHEN fre.is_compliant = FALSE THEN fre.id END) AS violations,
    COUNT(DISTINCT CASE WHEN er.is_compliant = FALSE THEN er.id END) AS route_violations
FROM cadhub_cad_model m
JOIN cadhub_project p ON m.project_id = p.id
LEFT JOIN cadhub_fire_compartment fc ON fc.cad_model_id = m.id
LEFT JOIN cadhub_fire_rated_element fre ON fre.cad_model_id = m.id
LEFT JOIN cadhub_escape_route er ON er.cad_model_id = m.id
GROUP BY m.id, m.name, p.id, p.name;
