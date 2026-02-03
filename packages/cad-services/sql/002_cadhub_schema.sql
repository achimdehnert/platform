-- ============================================================================
-- ADR-009: CAD-Hub Schema Migration
-- Vollständig normalisiert, KEIN JSONB für kritische Daten
-- ============================================================================

BEGIN;

-- Unit (Stammdaten)
CREATE TABLE IF NOT EXISTS cadhub_unit (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    unit_type VARCHAR(50) NOT NULL,
    
    CONSTRAINT chk_unit_type CHECK (
        unit_type IN ('length', 'area', 'volume', 'mass', 'temperature', 'thermal', 'angle', 'other')
    )
);

-- Usage Category (DIN 277 Stammdaten)
CREATE TABLE IF NOT EXISTS cadhub_usage_category (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    din_category VARCHAR(10) NOT NULL,
    description TEXT,
    
    CONSTRAINT chk_usage_din CHECK (din_category IN ('NF', 'TF', 'VF', 'BGF', 'KGF', 'BRI'))
);

-- Property Definition (IFC PropertySets - Stammdaten)
CREATE TABLE IF NOT EXISTS cadhub_property_definition (
    id SERIAL PRIMARY KEY,
    code VARCHAR(150) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    data_type VARCHAR(20) NOT NULL,
    default_unit_id INTEGER REFERENCES cadhub_unit(id),
    ifc_property_set VARCHAR(100),
    ifc_property_name VARCHAR(100),
    
    CONSTRAINT chk_property_data_type CHECK (
        data_type IN ('text', 'numeric', 'boolean', 'date')
    )
);

CREATE INDEX IF NOT EXISTS idx_property_def_pset ON cadhub_property_definition(ifc_property_set);

-- Project
CREATE TABLE IF NOT EXISTS cadhub_project (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES core_tenant(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by_id INTEGER NOT NULL REFERENCES core_user(id) ON DELETE RESTRICT,
    
    CONSTRAINT uq_project_tenant_name UNIQUE (tenant_id, name)
);

CREATE INDEX IF NOT EXISTS idx_project_tenant ON cadhub_project(tenant_id);

-- CAD Model
CREATE TABLE IF NOT EXISTS cadhub_cad_model (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES cadhub_project(id) ON DELETE CASCADE,
    version INTEGER NOT NULL DEFAULT 1,
    name VARCHAR(255) NOT NULL,
    source_file_path VARCHAR(500),
    source_format VARCHAR(20) NOT NULL,
    file_size_bytes BIGINT,
    ifc_schema VARCHAR(20),
    ifc_application VARCHAR(100),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    created_by_id INTEGER NOT NULL REFERENCES core_user(id) ON DELETE RESTRICT,
    
    CONSTRAINT uq_model_project_version UNIQUE (project_id, version),
    CONSTRAINT chk_model_source_format CHECK (
        source_format IN ('ifc', 'dxf', 'dwg', 'step', 'stl', 'fbx', 'gltf')
    ),
    CONSTRAINT chk_model_status CHECK (
        status IN ('pending', 'processing', 'ready', 'error')
    )
);

CREATE INDEX IF NOT EXISTS idx_model_project ON cadhub_cad_model(project_id);
CREATE INDEX IF NOT EXISTS idx_model_status ON cadhub_cad_model(status);

-- Floor (IfcBuildingStorey)
CREATE TABLE IF NOT EXISTS cadhub_floor (
    id SERIAL PRIMARY KEY,
    cad_model_id INTEGER NOT NULL REFERENCES cadhub_cad_model(id) ON DELETE CASCADE,
    ifc_guid VARCHAR(36) NOT NULL,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(20),
    elevation_m DECIMAL(10, 3) NOT NULL DEFAULT 0,
    sort_order INTEGER NOT NULL DEFAULT 0,
    
    CONSTRAINT uq_floor_model_guid UNIQUE (cad_model_id, ifc_guid)
);

CREATE INDEX IF NOT EXISTS idx_floor_model ON cadhub_floor(cad_model_id);

-- Room (IfcSpace) - NORMALISIERT
CREATE TABLE IF NOT EXISTS cadhub_room (
    id SERIAL PRIMARY KEY,
    cad_model_id INTEGER NOT NULL REFERENCES cadhub_cad_model(id) ON DELETE CASCADE,
    floor_id INTEGER REFERENCES cadhub_floor(id) ON DELETE SET NULL,
    ifc_guid VARCHAR(36) NOT NULL,
    number VARCHAR(20) NOT NULL,
    name VARCHAR(100) NOT NULL,
    long_name VARCHAR(255),
    -- Geometrie NORMALISIERT (KEIN JSONB!)
    area_m2 DECIMAL(12, 3) NOT NULL DEFAULT 0,
    height_m DECIMAL(10, 3) NOT NULL DEFAULT 0,
    volume_m3 DECIMAL(12, 3) NOT NULL DEFAULT 0,
    perimeter_m DECIMAL(12, 3) NOT NULL DEFAULT 0,
    -- DIN 277 (FK Integer)
    usage_category_id INTEGER REFERENCES cadhub_usage_category(id),
    
    CONSTRAINT uq_room_model_guid UNIQUE (cad_model_id, ifc_guid),
    CONSTRAINT chk_room_area_positive CHECK (area_m2 >= 0),
    CONSTRAINT chk_room_volume_positive CHECK (volume_m3 >= 0)
);

CREATE INDEX IF NOT EXISTS idx_room_model ON cadhub_room(cad_model_id);
CREATE INDEX IF NOT EXISTS idx_room_floor ON cadhub_room(floor_id);
CREATE INDEX IF NOT EXISTS idx_room_usage ON cadhub_room(usage_category_id);

-- Window (IfcWindow) - NORMALISIERT
CREATE TABLE IF NOT EXISTS cadhub_window (
    id SERIAL PRIMARY KEY,
    cad_model_id INTEGER NOT NULL REFERENCES cadhub_cad_model(id) ON DELETE CASCADE,
    floor_id INTEGER REFERENCES cadhub_floor(id) ON DELETE SET NULL,
    room_id INTEGER REFERENCES cadhub_room(id) ON DELETE SET NULL,
    ifc_guid VARCHAR(36) NOT NULL,
    number VARCHAR(50),
    name VARCHAR(100),
    -- Geometrie NORMALISIERT
    width_m DECIMAL(10, 3),
    height_m DECIMAL(10, 3),
    area_m2 DECIMAL(10, 3),
    -- Physikalische Eigenschaften NORMALISIERT (KEIN JSONB!)
    u_value_w_m2k DECIMAL(5, 2),
    material VARCHAR(100),
    glazing_type VARCHAR(100),
    
    CONSTRAINT uq_window_model_guid UNIQUE (cad_model_id, ifc_guid),
    CONSTRAINT chk_window_dimensions CHECK (
        (width_m IS NULL OR width_m > 0) AND
        (height_m IS NULL OR height_m > 0)
    )
);

CREATE INDEX IF NOT EXISTS idx_window_model ON cadhub_window(cad_model_id);
CREATE INDEX IF NOT EXISTS idx_window_floor ON cadhub_window(floor_id);

-- Door (IfcDoor) - NORMALISIERT
CREATE TABLE IF NOT EXISTS cadhub_door (
    id SERIAL PRIMARY KEY,
    cad_model_id INTEGER NOT NULL REFERENCES cadhub_cad_model(id) ON DELETE CASCADE,
    floor_id INTEGER REFERENCES cadhub_floor(id) ON DELETE SET NULL,
    from_room_id INTEGER REFERENCES cadhub_room(id) ON DELETE SET NULL,
    to_room_id INTEGER REFERENCES cadhub_room(id) ON DELETE SET NULL,
    ifc_guid VARCHAR(36) NOT NULL,
    number VARCHAR(50),
    name VARCHAR(100),
    -- Geometrie NORMALISIERT
    width_m DECIMAL(10, 3),
    height_m DECIMAL(10, 3),
    -- Eigenschaften NORMALISIERT (KEIN JSONB!)
    door_type VARCHAR(50),
    material VARCHAR(100),
    fire_rating VARCHAR(20),
    
    CONSTRAINT uq_door_model_guid UNIQUE (cad_model_id, ifc_guid)
);

CREATE INDEX IF NOT EXISTS idx_door_model ON cadhub_door(cad_model_id);
CREATE INDEX IF NOT EXISTS idx_door_fire_rating ON cadhub_door(fire_rating) WHERE fire_rating IS NOT NULL;

-- Wall (IfcWall) - NORMALISIERT
CREATE TABLE IF NOT EXISTS cadhub_wall (
    id SERIAL PRIMARY KEY,
    cad_model_id INTEGER NOT NULL REFERENCES cadhub_cad_model(id) ON DELETE CASCADE,
    floor_id INTEGER REFERENCES cadhub_floor(id) ON DELETE SET NULL,
    ifc_guid VARCHAR(36) NOT NULL,
    name VARCHAR(100),
    -- Geometrie NORMALISIERT (KEIN JSONB!)
    length_m DECIMAL(10, 3),
    height_m DECIMAL(10, 3),
    thickness_m DECIMAL(10, 3),
    gross_area_m2 DECIMAL(10, 3),
    net_area_m2 DECIMAL(10, 3),
    volume_m3 DECIMAL(10, 3),
    -- Eigenschaften NORMALISIERT
    is_external BOOLEAN NOT NULL DEFAULT false,
    is_load_bearing BOOLEAN NOT NULL DEFAULT false,
    material VARCHAR(100),
    
    CONSTRAINT uq_wall_model_guid UNIQUE (cad_model_id, ifc_guid)
);

CREATE INDEX IF NOT EXISTS idx_wall_model ON cadhub_wall(cad_model_id);
CREATE INDEX IF NOT EXISTS idx_wall_external ON cadhub_wall(cad_model_id, is_external);

-- Slab (IfcSlab) - NORMALISIERT
CREATE TABLE IF NOT EXISTS cadhub_slab (
    id SERIAL PRIMARY KEY,
    cad_model_id INTEGER NOT NULL REFERENCES cadhub_cad_model(id) ON DELETE CASCADE,
    floor_id INTEGER REFERENCES cadhub_floor(id) ON DELETE SET NULL,
    ifc_guid VARCHAR(36) NOT NULL,
    name VARCHAR(100),
    slab_type VARCHAR(20) NOT NULL DEFAULT 'FLOOR',
    -- Geometrie NORMALISIERT (KEIN JSONB!)
    area_m2 DECIMAL(10, 3),
    thickness_m DECIMAL(10, 3),
    volume_m3 DECIMAL(10, 3),
    perimeter_m DECIMAL(10, 3),
    material VARCHAR(100),
    
    CONSTRAINT uq_slab_model_guid UNIQUE (cad_model_id, ifc_guid),
    CONSTRAINT chk_slab_type CHECK (
        slab_type IN ('FLOOR', 'ROOF', 'BASESLAB', 'LANDING')
    )
);

CREATE INDEX IF NOT EXISTS idx_slab_model ON cadhub_slab(cad_model_id);
CREATE INDEX IF NOT EXISTS idx_slab_type ON cadhub_slab(slab_type);

-- Element Property (NORMALISIERT statt JSONB)
CREATE TABLE IF NOT EXISTS cadhub_element_property (
    id SERIAL PRIMARY KEY,
    element_type VARCHAR(20) NOT NULL,
    element_id INTEGER NOT NULL,
    property_definition_id INTEGER NOT NULL REFERENCES cadhub_property_definition(id),
    value_text TEXT,
    value_numeric DECIMAL(20, 6),
    value_boolean BOOLEAN,
    value_date DATE,
    unit_id INTEGER REFERENCES cadhub_unit(id),
    
    CONSTRAINT uq_element_property UNIQUE (element_type, element_id, property_definition_id),
    CONSTRAINT chk_property_has_value CHECK (
        value_text IS NOT NULL OR 
        value_numeric IS NOT NULL OR 
        value_boolean IS NOT NULL OR
        value_date IS NOT NULL
    ),
    CONSTRAINT chk_property_element_type CHECK (
        element_type IN ('room', 'window', 'door', 'wall', 'slab', 'floor')
    )
);

CREATE INDEX IF NOT EXISTS idx_element_property_element ON cadhub_element_property(element_type, element_id);
CREATE INDEX IF NOT EXISTS idx_element_property_numeric ON cadhub_element_property(property_definition_id, value_numeric)
    WHERE value_numeric IS NOT NULL;

-- Stammdaten: Units
INSERT INTO cadhub_unit (code, name, symbol, unit_type) VALUES
    ('m', 'Meter', 'm', 'length'),
    ('cm', 'Zentimeter', 'cm', 'length'),
    ('mm', 'Millimeter', 'mm', 'length'),
    ('m2', 'Quadratmeter', 'm²', 'area'),
    ('m3', 'Kubikmeter', 'm³', 'volume'),
    ('kg', 'Kilogramm', 'kg', 'mass'),
    ('w_m2k', 'W/m²K', 'W/(m²·K)', 'thermal'),
    ('deg', 'Grad', '°', 'angle')
ON CONFLICT (code) DO NOTHING;

-- Stammdaten: DIN 277 Nutzungskategorien
INSERT INTO cadhub_usage_category (code, name, din_category, description) VALUES
    ('NF1.1', 'Wohnen und Aufenthalt', 'NF', 'Wohn- und Schlafräume'),
    ('NF1.2', 'Büroarbeit', 'NF', 'Büro- und Besprechungsräume'),
    ('NF1.3', 'Produktion', 'NF', 'Produktions- und Werkstätten'),
    ('NF2', 'Büroflächen', 'NF', 'Allgemeine Büroflächen'),
    ('NF3', 'Lager und Verteilen', 'NF', 'Lager- und Abstellräume'),
    ('NF4', 'Bildung und Kultur', 'NF', 'Unterrichts- und Kulturräume'),
    ('NF5', 'Heilen und Pflegen', 'NF', 'Medizinische Räume'),
    ('NF6', 'Sonstige Nutzflächen', 'NF', 'Sonstige'),
    ('TF7', 'Technikflächen', 'TF', 'Heizung, Lüftung, Elektro'),
    ('VF8', 'Verkehrsflächen', 'VF', 'Flure, Treppen, Aufzüge')
ON CONFLICT (code) DO NOTHING;

-- Stammdaten: Common Property Definitions
INSERT INTO cadhub_property_definition (code, name, data_type, ifc_property_set, ifc_property_name) VALUES
    ('Pset_SpaceCommon.Reference', 'Raumnummer', 'text', 'Pset_SpaceCommon', 'Reference'),
    ('Pset_SpaceCommon.PubliclyAccessible', 'Öffentlich zugänglich', 'boolean', 'Pset_SpaceCommon', 'PubliclyAccessible'),
    ('Pset_WindowCommon.ThermalTransmittance', 'U-Wert', 'numeric', 'Pset_WindowCommon', 'ThermalTransmittance'),
    ('Pset_WindowCommon.GlazingAreaFraction', 'Glasflächenanteil', 'numeric', 'Pset_WindowCommon', 'GlazingAreaFraction'),
    ('Pset_DoorCommon.FireRating', 'Feuerwiderstand', 'text', 'Pset_DoorCommon', 'FireRating'),
    ('Pset_DoorCommon.AcousticRating', 'Schallschutz', 'text', 'Pset_DoorCommon', 'AcousticRating'),
    ('Pset_WallCommon.IsExternal', 'Außenwand', 'boolean', 'Pset_WallCommon', 'IsExternal'),
    ('Pset_WallCommon.LoadBearing', 'Tragend', 'boolean', 'Pset_WallCommon', 'LoadBearing'),
    ('Pset_SlabCommon.IsExternal', 'Außendecke', 'boolean', 'Pset_SlabCommon', 'IsExternal')
ON CONFLICT (code) DO NOTHING;

COMMIT;
