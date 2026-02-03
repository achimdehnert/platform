-- ============================================================
-- CAD-Hub Platform - Seed Data
-- ADR-009 compliant: Database-driven, no hardcoding
-- ============================================================

-- ============================================================
-- 1. CORE SCHEMA: Plans, Tenants, Users, Roles
-- ============================================================

-- Plans (already in 001, but ensure they exist)
INSERT INTO core_plan (code, name, max_users, max_storage_gb, price_month, is_active)
VALUES 
    ('free', 'Free', 2, 1, 0.00, true),
    ('starter', 'Starter', 5, 10, 49.00, true),
    ('professional', 'Professional', 25, 100, 149.00, true),
    ('enterprise', 'Enterprise', 1000, 1000, 499.00, true)
ON CONFLICT (code) DO NOTHING;

-- Demo Tenants
INSERT INTO core_tenant (slug, name, plan_id, status, created_at)
SELECT 'techcorp', 'TechCorp GmbH', p.id, 'active', NOW() - INTERVAL '30 days'
FROM core_plan p WHERE p.code = 'enterprise'
ON CONFLICT (slug) DO NOTHING;

INSERT INTO core_tenant (slug, name, plan_id, status, created_at)
SELECT 'global-solutions', 'Global Solutions AG', p.id, 'active', NOW() - INTERVAL '45 days'
FROM core_plan p WHERE p.code = 'professional'
ON CONFLICT (slug) DO NOTHING;

INSERT INTO core_tenant (slug, name, plan_id, status, created_at)
SELECT 'marketing-ag', 'Marketing AG', p.id, 'active', NOW() - INTERVAL '20 days'
FROM core_plan p WHERE p.code = 'starter'
ON CONFLICT (slug) DO NOTHING;

INSERT INTO core_tenant (slug, name, plan_id, status, created_at)
SELECT 'demo', 'Demo Tenant', p.id, 'active', NOW() - INTERVAL '1 day'
FROM core_plan p WHERE p.code = 'free'
ON CONFLICT (slug) DO NOTHING;

-- Demo Users
INSERT INTO core_user (email, password_hash, first_name, last_name, is_active, created_at)
VALUES 
    ('max@techcorp.de', 'pbkdf2_sha256$hash$', 'Max', 'Mustermann', true, NOW() - INTERVAL '30 days'),
    ('anna@techcorp.de', 'pbkdf2_sha256$hash$', 'Anna', 'Schmidt', true, NOW() - INTERVAL '28 days'),
    ('peter@techcorp.de', 'pbkdf2_sha256$hash$', 'Peter', 'Weber', true, NOW() - INTERVAL '25 days'),
    ('julia@global-solutions.com', 'pbkdf2_sha256$hash$', 'Julia', 'Meier', true, NOW() - INTERVAL '45 days'),
    ('tom@global-solutions.com', 'pbkdf2_sha256$hash$', 'Tom', 'Braun', true, NOW() - INTERVAL '40 days'),
    ('lisa@marketing-ag.de', 'pbkdf2_sha256$hash$', 'Lisa', 'Marketing', true, NOW() - INTERVAL '20 days'),
    ('demo@platform.io', 'pbkdf2_sha256$hash$', 'Demo', 'User', true, NOW() - INTERVAL '1 day')
ON CONFLICT (email) DO NOTHING;

-- Memberships (User-Tenant-Role assignments)
INSERT INTO core_membership (user_id, tenant_id, role_id, is_primary, joined_at)
SELECT u.id, t.id, r.id, true, NOW() - INTERVAL '30 days'
FROM core_user u, core_tenant t, core_role r
WHERE u.email = 'max@techcorp.de' AND t.slug = 'techcorp' AND r.code = 'owner'
ON CONFLICT (user_id, tenant_id) DO NOTHING;

INSERT INTO core_membership (user_id, tenant_id, role_id, is_primary, joined_at)
SELECT u.id, t.id, r.id, true, NOW() - INTERVAL '28 days'
FROM core_user u, core_tenant t, core_role r
WHERE u.email = 'anna@techcorp.de' AND t.slug = 'techcorp' AND r.code = 'admin'
ON CONFLICT (user_id, tenant_id) DO NOTHING;

INSERT INTO core_membership (user_id, tenant_id, role_id, is_primary, joined_at)
SELECT u.id, t.id, r.id, true, NOW() - INTERVAL '25 days'
FROM core_user u, core_tenant t, core_role r
WHERE u.email = 'peter@techcorp.de' AND t.slug = 'techcorp' AND r.code = 'member'
ON CONFLICT (user_id, tenant_id) DO NOTHING;

INSERT INTO core_membership (user_id, tenant_id, role_id, is_primary, joined_at)
SELECT u.id, t.id, r.id, true, NOW() - INTERVAL '45 days'
FROM core_user u, core_tenant t, core_role r
WHERE u.email = 'julia@global-solutions.com' AND t.slug = 'global-solutions' AND r.code = 'owner'
ON CONFLICT (user_id, tenant_id) DO NOTHING;

INSERT INTO core_membership (user_id, tenant_id, role_id, is_primary, joined_at)
SELECT u.id, t.id, r.id, true, NOW() - INTERVAL '40 days'
FROM core_user u, core_tenant t, core_role r
WHERE u.email = 'tom@global-solutions.com' AND t.slug = 'global-solutions' AND r.code = 'member'
ON CONFLICT (user_id, tenant_id) DO NOTHING;

INSERT INTO core_membership (user_id, tenant_id, role_id, is_primary, joined_at)
SELECT u.id, t.id, r.id, true, NOW() - INTERVAL '20 days'
FROM core_user u, core_tenant t, core_role r
WHERE u.email = 'lisa@marketing-ag.de' AND t.slug = 'marketing-ag' AND r.code = 'owner'
ON CONFLICT (user_id, tenant_id) DO NOTHING;

INSERT INTO core_membership (user_id, tenant_id, role_id, is_primary, joined_at)
SELECT u.id, t.id, r.id, true, NOW() - INTERVAL '1 day'
FROM core_user u, core_tenant t, core_role r
WHERE u.email = 'demo@platform.io' AND t.slug = 'demo' AND r.code = 'owner'
ON CONFLICT (user_id, tenant_id) DO NOTHING;

-- ============================================================
-- 2. CADHUB SCHEMA: Projects, Models, Elements
-- ============================================================

-- Demo Projects
INSERT INTO cadhub_project (tenant_id, name, description, created_at, created_by_id)
SELECT t.id, 'Bürogebäude München', 'Neubau 5-stöckiges Bürogebäude', NOW() - INTERVAL '25 days', u.id
FROM core_tenant t, core_user u WHERE t.slug = 'techcorp' AND u.email = 'max@techcorp.de'
ON CONFLICT (tenant_id, name) DO NOTHING;

INSERT INTO cadhub_project (tenant_id, name, description, created_at, created_by_id)
SELECT t.id, 'Wohnanlage Berlin', 'Mehrfamilienhaus mit 24 Einheiten', NOW() - INTERVAL '20 days', u.id
FROM core_tenant t, core_user u WHERE t.slug = 'techcorp' AND u.email = 'max@techcorp.de'
ON CONFLICT (tenant_id, name) DO NOTHING;

INSERT INTO cadhub_project (tenant_id, name, description, created_at, created_by_id)
SELECT t.id, 'Logistikzentrum Hamburg', 'Lagerhalle 10.000m²', NOW() - INTERVAL '40 days', u.id
FROM core_tenant t, core_user u WHERE t.slug = 'global-solutions' AND u.email = 'julia@global-solutions.com'
ON CONFLICT (tenant_id, name) DO NOTHING;

INSERT INTO cadhub_project (tenant_id, name, description, created_at, created_by_id)
SELECT t.id, 'Demo Projekt', 'Beispielprojekt zum Testen', NOW(), u.id
FROM core_tenant t, core_user u WHERE t.slug = 'demo' AND u.email = 'demo@platform.io'
ON CONFLICT (tenant_id, name) DO NOTHING;

-- Demo CAD Models (IFC files)
INSERT INTO cadhub_cad_model (project_id, name, source_file_path, file_size_bytes, source_format, status, created_at, created_by_id)
SELECT p.id, 'Architektur_EG.ifc', '/uploads/techcorp/buero-muenchen/architektur_eg.ifc', 15728640, 'ifc', 'ready', NOW() - INTERVAL '24 days', u.id
FROM cadhub_project p 
JOIN core_tenant t ON p.tenant_id = t.id
JOIN core_user u ON u.email = 'max@techcorp.de'
WHERE t.slug = 'techcorp' AND p.name = 'Bürogebäude München';

INSERT INTO cadhub_cad_model (project_id, name, source_file_path, file_size_bytes, source_format, status, created_at, created_by_id, version)
SELECT p.id, 'Architektur_OG1-4.ifc', '/uploads/techcorp/buero-muenchen/architektur_og.ifc', 45875200, 'ifc', 'ready', NOW() - INTERVAL '23 days', u.id, 2
FROM cadhub_project p 
JOIN core_tenant t ON p.tenant_id = t.id
JOIN core_user u ON u.email = 'max@techcorp.de'
WHERE t.slug = 'techcorp' AND p.name = 'Bürogebäude München';

INSERT INTO cadhub_cad_model (project_id, name, source_file_path, file_size_bytes, source_format, status, created_at, created_by_id)
SELECT p.id, 'Wohnanlage_Komplett.ifc', '/uploads/techcorp/wohnanlage-berlin/komplett.ifc', 89456640, 'ifc', 'ready', NOW() - INTERVAL '18 days', u.id
FROM cadhub_project p 
JOIN core_tenant t ON p.tenant_id = t.id
JOIN core_user u ON u.email = 'max@techcorp.de'
WHERE t.slug = 'techcorp' AND p.name = 'Wohnanlage Berlin';

-- Demo Floors
INSERT INTO cadhub_floor (cad_model_id, ifc_guid, name, elevation_m, sort_order)
SELECT m.id, 'EG-GUID-001', 'Erdgeschoss', 0.00, 0
FROM cadhub_cad_model m WHERE m.name = 'Architektur_EG.ifc';

INSERT INTO cadhub_floor (cad_model_id, ifc_guid, name, elevation_m, sort_order)
SELECT m.id, 'OG1-GUID-001', '1. Obergeschoss', 3.50, 1
FROM cadhub_cad_model m WHERE m.name = 'Architektur_OG1-4.ifc';

INSERT INTO cadhub_floor (cad_model_id, ifc_guid, name, elevation_m, sort_order)
SELECT m.id, 'OG2-GUID-001', '2. Obergeschoss', 6.70, 2
FROM cadhub_cad_model m WHERE m.name = 'Architektur_OG1-4.ifc';

INSERT INTO cadhub_floor (cad_model_id, ifc_guid, name, elevation_m, sort_order)
SELECT m.id, 'OG3-GUID-001', '3. Obergeschoss', 9.90, 3
FROM cadhub_cad_model m WHERE m.name = 'Architektur_OG1-4.ifc';

INSERT INTO cadhub_floor (cad_model_id, ifc_guid, name, elevation_m, sort_order)
SELECT m.id, 'OG4-GUID-001', '4. Obergeschoss', 13.10, 4
FROM cadhub_cad_model m WHERE m.name = 'Architektur_OG1-4.ifc';

-- Demo Rooms (with DIN 277 categories)
INSERT INTO cadhub_room (cad_model_id, floor_id, ifc_guid, room_number, name, area_m2, height_m, volume_m3)
SELECT m.id, f.id, 'ROOM-EG-001', '0.01', 'Empfang', 45.50, 3.50, 159.25
FROM cadhub_cad_model m 
JOIN cadhub_floor f ON f.cad_model_id = m.id AND f.name = 'Erdgeschoss'
WHERE m.name = 'Architektur_EG.ifc';

INSERT INTO cadhub_room (cad_model_id, floor_id, ifc_guid, room_number, name, area_m2, height_m, volume_m3)
SELECT m.id, f.id, 'ROOM-EG-002', '0.02', 'Großraumbüro', 180.00, 3.50, 630.00
FROM cadhub_cad_model m 
JOIN cadhub_floor f ON f.cad_model_id = m.id AND f.name = 'Erdgeschoss'
WHERE m.name = 'Architektur_EG.ifc';

INSERT INTO cadhub_room (cad_model_id, floor_id, ifc_guid, room_number, name, area_m2, height_m, volume_m3)
SELECT m.id, f.id, 'ROOM-EG-003', '0.03', 'Besprechung 1', 25.00, 3.50, 87.50
FROM cadhub_cad_model m 
JOIN cadhub_floor f ON f.cad_model_id = m.id AND f.name = 'Erdgeschoss'
WHERE m.name = 'Architektur_EG.ifc';

INSERT INTO cadhub_room (cad_model_id, floor_id, ifc_guid, room_number, name, area_m2, height_m, volume_m3)
SELECT m.id, f.id, 'ROOM-EG-004', '0.04', 'WC Herren', 12.00, 3.50, 42.00
FROM cadhub_cad_model m 
JOIN cadhub_floor f ON f.cad_model_id = m.id AND f.name = 'Erdgeschoss'
WHERE m.name = 'Architektur_EG.ifc';

INSERT INTO cadhub_room (cad_model_id, floor_id, ifc_guid, room_number, name, area_m2, height_m, volume_m3)
SELECT m.id, f.id, 'ROOM-EG-005', '0.05', 'WC Damen', 12.00, 3.50, 42.00
FROM cadhub_cad_model m 
JOIN cadhub_floor f ON f.cad_model_id = m.id AND f.name = 'Erdgeschoss'
WHERE m.name = 'Architektur_EG.ifc';

INSERT INTO cadhub_room (cad_model_id, floor_id, ifc_guid, room_number, name, area_m2, height_m, volume_m3)
SELECT m.id, f.id, 'ROOM-EG-006', '0.06', 'Flur', 35.00, 3.50, 122.50
FROM cadhub_cad_model m 
JOIN cadhub_floor f ON f.cad_model_id = m.id AND f.name = 'Erdgeschoss'
WHERE m.name = 'Architektur_EG.ifc';

INSERT INTO cadhub_room (cad_model_id, floor_id, ifc_guid, room_number, name, area_m2, height_m, volume_m3)
SELECT m.id, f.id, 'ROOM-EG-007', '0.07', 'Technikraum', 20.00, 3.50, 70.00
FROM cadhub_cad_model m 
JOIN cadhub_floor f ON f.cad_model_id = m.id AND f.name = 'Erdgeschoss'
WHERE m.name = 'Architektur_EG.ifc';

-- Demo Windows
INSERT INTO cadhub_window (cad_model_id, floor_id, ifc_guid, name, width_m, height_m, area_m2)
SELECT m.id, f.id, 'WIN-EG-001', 'Fenster 1.2x1.5', 1.20, 1.50, 1.80
FROM cadhub_cad_model m 
JOIN cadhub_floor f ON f.cad_model_id = m.id AND f.name = 'Erdgeschoss'
WHERE m.name = 'Architektur_EG.ifc';

INSERT INTO cadhub_window (cad_model_id, floor_id, ifc_guid, name, width_m, height_m, area_m2)
SELECT m.id, f.id, 'WIN-EG-002', 'Fenster 1.2x1.5', 1.20, 1.50, 1.80
FROM cadhub_cad_model m 
JOIN cadhub_floor f ON f.cad_model_id = m.id AND f.name = 'Erdgeschoss'
WHERE m.name = 'Architektur_EG.ifc';

INSERT INTO cadhub_window (cad_model_id, floor_id, ifc_guid, name, width_m, height_m, area_m2)
SELECT m.id, f.id, 'WIN-EG-003', 'Fenster 2.0x2.2', 2.00, 2.20, 4.40
FROM cadhub_cad_model m 
JOIN cadhub_floor f ON f.cad_model_id = m.id AND f.name = 'Erdgeschoss'
WHERE m.name = 'Architektur_EG.ifc';

INSERT INTO cadhub_window (cad_model_id, floor_id, ifc_guid, name, width_m, height_m, area_m2)
SELECT m.id, f.id, 'WIN-EG-004', 'Fensterfront 4.0x2.5', 4.00, 2.50, 10.00
FROM cadhub_cad_model m 
JOIN cadhub_floor f ON f.cad_model_id = m.id AND f.name = 'Erdgeschoss'
WHERE m.name = 'Architektur_EG.ifc';

-- Demo Doors
INSERT INTO cadhub_door (cad_model_id, floor_id, ifc_guid, name, width_m, height_m, area_m2)
SELECT m.id, f.id, 'DOOR-EG-001', 'Eingangstür', 1.20, 2.20, 2.64
FROM cadhub_cad_model m 
JOIN cadhub_floor f ON f.cad_model_id = m.id AND f.name = 'Erdgeschoss'
WHERE m.name = 'Architektur_EG.ifc';

INSERT INTO cadhub_door (cad_model_id, floor_id, ifc_guid, name, width_m, height_m, area_m2)
SELECT m.id, f.id, 'DOOR-EG-002', 'Bürotür', 0.90, 2.10, 1.89
FROM cadhub_cad_model m 
JOIN cadhub_floor f ON f.cad_model_id = m.id AND f.name = 'Erdgeschoss'
WHERE m.name = 'Architektur_EG.ifc';

INSERT INTO cadhub_door (cad_model_id, floor_id, ifc_guid, name, width_m, height_m, area_m2)
SELECT m.id, f.id, 'DOOR-EG-003', 'Bürotür', 0.90, 2.10, 1.89
FROM cadhub_cad_model m 
JOIN cadhub_floor f ON f.cad_model_id = m.id AND f.name = 'Erdgeschoss'
WHERE m.name = 'Architektur_EG.ifc';

INSERT INTO cadhub_door (cad_model_id, floor_id, ifc_guid, name, width_m, height_m, area_m2)
SELECT m.id, f.id, 'DOOR-EG-004', 'WC-Tür', 0.80, 2.10, 1.68
FROM cadhub_cad_model m 
JOIN cadhub_floor f ON f.cad_model_id = m.id AND f.name = 'Erdgeschoss'
WHERE m.name = 'Architektur_EG.ifc';

-- Demo Walls
INSERT INTO cadhub_wall (cad_model_id, floor_id, ifc_guid, name, length_m, height_m, thickness_m, area_m2, is_external)
SELECT m.id, f.id, 'WALL-EG-001', 'Außenwand Nord', 25.00, 3.50, 0.365, 87.50, true
FROM cadhub_cad_model m 
JOIN cadhub_floor f ON f.cad_model_id = m.id AND f.name = 'Erdgeschoss'
WHERE m.name = 'Architektur_EG.ifc';

INSERT INTO cadhub_wall (cad_model_id, floor_id, ifc_guid, name, length_m, height_m, thickness_m, area_m2, is_external)
SELECT m.id, f.id, 'WALL-EG-002', 'Außenwand Ost', 15.00, 3.50, 0.365, 52.50, true
FROM cadhub_cad_model m 
JOIN cadhub_floor f ON f.cad_model_id = m.id AND f.name = 'Erdgeschoss'
WHERE m.name = 'Architektur_EG.ifc';

INSERT INTO cadhub_wall (cad_model_id, floor_id, ifc_guid, name, length_m, height_m, thickness_m, area_m2, is_external)
SELECT m.id, f.id, 'WALL-EG-003', 'Innenwand 1', 8.00, 3.50, 0.115, 28.00, false
FROM cadhub_cad_model m 
JOIN cadhub_floor f ON f.cad_model_id = m.id AND f.name = 'Erdgeschoss'
WHERE m.name = 'Architektur_EG.ifc';

-- Demo Slabs
INSERT INTO cadhub_slab (cad_model_id, floor_id, ifc_guid, name, area_m2, thickness_m, volume_m3, slab_type)
SELECT m.id, f.id, 'SLAB-EG-001', 'Bodenplatte EG', 375.00, 0.25, 93.75, 'floor'
FROM cadhub_cad_model m 
JOIN cadhub_floor f ON f.cad_model_id = m.id AND f.name = 'Erdgeschoss'
WHERE m.name = 'Architektur_EG.ifc';

INSERT INTO cadhub_slab (cad_model_id, floor_id, ifc_guid, name, area_m2, thickness_m, volume_m3, slab_type)
SELECT m.id, f.id, 'SLAB-EG-002', 'Decke EG', 375.00, 0.22, 82.50, 'ceiling'
FROM cadhub_cad_model m 
JOIN cadhub_floor f ON f.cad_model_id = m.id AND f.name = 'Erdgeschoss'
WHERE m.name = 'Architektur_EG.ifc';

-- ============================================================
-- 3. ELEMENT PROPERTIES (Normalized, no JSONB)
-- ============================================================

-- Element properties (simplified - properties can be added after data is loaded)

-- ============================================================
-- 4. VERIFY DATA
-- ============================================================
DO $$
DECLARE
    tenant_count INTEGER;
    user_count INTEGER;
    project_count INTEGER;
    room_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO tenant_count FROM core_tenant;
    SELECT COUNT(*) INTO user_count FROM core_user;
    SELECT COUNT(*) INTO project_count FROM cadhub_project;
    SELECT COUNT(*) INTO room_count FROM cadhub_room;
    
    RAISE NOTICE '=== Seed Data Summary ===';
    RAISE NOTICE 'Tenants: %', tenant_count;
    RAISE NOTICE 'Users: %', user_count;
    RAISE NOTICE 'Projects: %', project_count;
    RAISE NOTICE 'Rooms: %', room_count;
END $$;
