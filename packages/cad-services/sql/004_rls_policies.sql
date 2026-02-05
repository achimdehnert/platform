-- ============================================================================
-- ADR-009: Row Level Security Policies
-- Tenant Isolation at Database Level
-- ============================================================================

BEGIN;

-- Enable RLS on all tenant-scoped tables
ALTER TABLE cadhub_project ENABLE ROW LEVEL SECURITY;
ALTER TABLE cadhub_cad_model ENABLE ROW LEVEL SECURITY;
ALTER TABLE cadhub_floor ENABLE ROW LEVEL SECURITY;
ALTER TABLE cadhub_room ENABLE ROW LEVEL SECURITY;
ALTER TABLE cadhub_window ENABLE ROW LEVEL SECURITY;
ALTER TABLE cadhub_door ENABLE ROW LEVEL SECURITY;
ALTER TABLE cadhub_wall ENABLE ROW LEVEL SECURITY;
ALTER TABLE cadhub_slab ENABLE ROW LEVEL SECURITY;
ALTER TABLE cadhub_element_property ENABLE ROW LEVEL SECURITY;

-- Helper function to get current tenant
CREATE OR REPLACE FUNCTION get_current_tenant_id() 
RETURNS INTEGER AS $$
BEGIN
    RETURN NULLIF(current_setting('app.current_tenant_id', true), '')::INTEGER;
END;
$$ LANGUAGE plpgsql STABLE;

-- Project Policy (direct tenant reference)
DROP POLICY IF EXISTS tenant_isolation_project ON cadhub_project;
CREATE POLICY tenant_isolation_project ON cadhub_project
    FOR ALL
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

-- CAD Model Policy (via project)
DROP POLICY IF EXISTS tenant_isolation_model ON cadhub_cad_model;
CREATE POLICY tenant_isolation_model ON cadhub_cad_model
    FOR ALL
    USING (
        project_id IN (
            SELECT id FROM cadhub_project 
            WHERE tenant_id = get_current_tenant_id()
        )
    );

-- Floor Policy (via cad_model -> project)
DROP POLICY IF EXISTS tenant_isolation_floor ON cadhub_floor;
CREATE POLICY tenant_isolation_floor ON cadhub_floor
    FOR ALL
    USING (
        cad_model_id IN (
            SELECT cm.id FROM cadhub_cad_model cm
            JOIN cadhub_project p ON p.id = cm.project_id
            WHERE p.tenant_id = get_current_tenant_id()
        )
    );

-- Room Policy
DROP POLICY IF EXISTS tenant_isolation_room ON cadhub_room;
CREATE POLICY tenant_isolation_room ON cadhub_room
    FOR ALL
    USING (
        cad_model_id IN (
            SELECT cm.id FROM cadhub_cad_model cm
            JOIN cadhub_project p ON p.id = cm.project_id
            WHERE p.tenant_id = get_current_tenant_id()
        )
    );

-- Window Policy
DROP POLICY IF EXISTS tenant_isolation_window ON cadhub_window;
CREATE POLICY tenant_isolation_window ON cadhub_window
    FOR ALL
    USING (
        cad_model_id IN (
            SELECT cm.id FROM cadhub_cad_model cm
            JOIN cadhub_project p ON p.id = cm.project_id
            WHERE p.tenant_id = get_current_tenant_id()
        )
    );

-- Door Policy
DROP POLICY IF EXISTS tenant_isolation_door ON cadhub_door;
CREATE POLICY tenant_isolation_door ON cadhub_door
    FOR ALL
    USING (
        cad_model_id IN (
            SELECT cm.id FROM cadhub_cad_model cm
            JOIN cadhub_project p ON p.id = cm.project_id
            WHERE p.tenant_id = get_current_tenant_id()
        )
    );

-- Wall Policy
DROP POLICY IF EXISTS tenant_isolation_wall ON cadhub_wall;
CREATE POLICY tenant_isolation_wall ON cadhub_wall
    FOR ALL
    USING (
        cad_model_id IN (
            SELECT cm.id FROM cadhub_cad_model cm
            JOIN cadhub_project p ON p.id = cm.project_id
            WHERE p.tenant_id = get_current_tenant_id()
        )
    );

-- Slab Policy
DROP POLICY IF EXISTS tenant_isolation_slab ON cadhub_slab;
CREATE POLICY tenant_isolation_slab ON cadhub_slab
    FOR ALL
    USING (
        cad_model_id IN (
            SELECT cm.id FROM cadhub_cad_model cm
            JOIN cadhub_project p ON p.id = cm.project_id
            WHERE p.tenant_id = get_current_tenant_id()
        )
    );

-- Superuser bypass policy (for admin operations)
DROP POLICY IF EXISTS superuser_bypass_project ON cadhub_project;
CREATE POLICY superuser_bypass_project ON cadhub_project
    FOR ALL
    TO postgres
    USING (true);

COMMIT;
