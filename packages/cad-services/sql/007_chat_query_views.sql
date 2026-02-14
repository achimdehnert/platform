-- ============================================================================
-- ADR-034 §2: SQL Views for Chat-Agent Queries
-- Aggregation views optimized for natural language query tool results
-- ============================================================================

BEGIN;

-- Room summary per floor (for "Welche Räume im 2.OG sind über 20m²?")
CREATE OR REPLACE VIEW cadhub_v_room_summary AS
SELECT
    r.id,
    r.cad_model_id,
    p.tenant_id,
    f.name AS floor_name,
    r.number AS room_number,
    r.name AS room_name,
    r.long_name,
    r.area_m2,
    r.height_m,
    r.volume_m3,
    r.perimeter_m,
    uc.code AS usage_code,
    uc.name AS usage_name,
    uc.din_category
FROM cadhub_room r
JOIN cadhub_cad_model m ON m.id = r.cad_model_id
JOIN cadhub_project p ON p.id = m.project_id
LEFT JOIN cadhub_floor f ON f.id = r.floor_id
LEFT JOIN cadhub_usage_category uc ON uc.id = r.usage_category_id
WHERE m.status = 'ready';

-- Wall summary per floor (for "Wie viele tragende Wände im 2.OG?")
CREATE OR REPLACE VIEW cadhub_v_wall_summary AS
SELECT
    w.id,
    w.cad_model_id,
    p.tenant_id,
    f.name AS floor_name,
    w.name AS wall_name,
    w.length_m,
    w.height_m,
    w.thickness_m,
    w.gross_area_m2,
    w.net_area_m2,
    w.volume_m3,
    w.is_external,
    w.is_load_bearing,
    w.material
FROM cadhub_wall w
JOIN cadhub_cad_model m ON m.id = w.cad_model_id
JOIN cadhub_project p ON p.id = m.project_id
LEFT JOIN cadhub_floor f ON f.id = w.floor_id
WHERE m.status = 'ready';

-- Window summary (for "Zeige alle Fenster mit U-Wert über 1.3")
CREATE OR REPLACE VIEW cadhub_v_window_summary AS
SELECT
    win.id,
    win.cad_model_id,
    p.tenant_id,
    f.name AS floor_name,
    r.number AS room_number,
    r.name AS room_name,
    win.number AS window_number,
    win.name AS window_name,
    win.width_m,
    win.height_m,
    win.area_m2,
    win.u_value_w_m2k,
    win.material,
    win.glazing_type
FROM cadhub_window win
JOIN cadhub_cad_model m ON m.id = win.cad_model_id
JOIN cadhub_project p ON p.id = m.project_id
LEFT JOIN cadhub_floor f ON f.id = win.floor_id
LEFT JOIN cadhub_room r ON r.id = win.room_id
WHERE m.status = 'ready';

-- Floor-level aggregation (for "Übersicht aller Stockwerke")
CREATE OR REPLACE VIEW cadhub_v_floor_aggregation AS
SELECT
    f.id AS floor_id,
    f.cad_model_id,
    p.tenant_id,
    f.name AS floor_name,
    f.elevation_m,
    f.sort_order,
    (SELECT COUNT(*) FROM cadhub_room WHERE floor_id = f.id) AS room_count,
    (SELECT COALESCE(SUM(area_m2), 0) FROM cadhub_room WHERE floor_id = f.id) AS total_room_area_m2,
    (SELECT COUNT(*) FROM cadhub_wall WHERE floor_id = f.id) AS wall_count,
    (SELECT COUNT(*) FROM cadhub_wall WHERE floor_id = f.id AND is_load_bearing) AS load_bearing_wall_count,
    (SELECT COUNT(*) FROM cadhub_window WHERE floor_id = f.id) AS window_count,
    (SELECT COUNT(*) FROM cadhub_door WHERE floor_id = f.id) AS door_count
FROM cadhub_floor f
JOIN cadhub_cad_model m ON m.id = f.cad_model_id
JOIN cadhub_project p ON p.id = m.project_id
WHERE m.status = 'ready';

-- Door summary (for fire safety queries)
CREATE OR REPLACE VIEW cadhub_v_door_summary AS
SELECT
    d.id,
    d.cad_model_id,
    p.tenant_id,
    f.name AS floor_name,
    d.number AS door_number,
    d.name AS door_name,
    d.width_m,
    d.height_m,
    d.door_type,
    d.material,
    d.fire_rating
FROM cadhub_door d
JOIN cadhub_cad_model m ON m.id = d.cad_model_id
JOIN cadhub_project p ON p.id = m.project_id
LEFT JOIN cadhub_floor f ON f.id = d.floor_id
WHERE m.status = 'ready';

COMMIT;
