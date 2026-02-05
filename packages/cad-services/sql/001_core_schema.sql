-- ============================================================================
-- ADR-009: Core Schema Migration
-- Database-First, Normalisiert, FK Integer
-- ============================================================================

BEGIN;

-- Plan (Stammdaten)
CREATE TABLE IF NOT EXISTS core_plan (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    max_users INTEGER NOT NULL DEFAULT 5,
    max_storage_gb INTEGER NOT NULL DEFAULT 10,
    is_public BOOLEAN NOT NULL DEFAULT true,
    sort_order INTEGER NOT NULL DEFAULT 0,
    
    CONSTRAINT chk_plan_max_users CHECK (max_users > 0 AND max_users <= 10000),
    CONSTRAINT chk_plan_max_storage CHECK (max_storage_gb > 0 AND max_storage_gb <= 10000)
);

CREATE INDEX IF NOT EXISTS idx_plan_is_public ON core_plan(is_public) WHERE is_public = true;

-- Tenant
CREATE TABLE IF NOT EXISTS core_tenant (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    plan_id INTEGER NOT NULL REFERENCES core_plan(id) ON DELETE RESTRICT,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    
    CONSTRAINT chk_tenant_status CHECK (status IN ('active', 'suspended', 'deleted')),
    CONSTRAINT chk_tenant_slug_format CHECK (slug ~ '^[a-z0-9]([a-z0-9-]*[a-z0-9])?$')
);

CREATE INDEX IF NOT EXISTS idx_tenant_slug ON core_tenant(slug);
CREATE INDEX IF NOT EXISTS idx_tenant_status ON core_tenant(status) WHERE status = 'active';

-- User
CREATE TABLE IF NOT EXISTS core_user (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL DEFAULT '',
    last_name VARCHAR(100) NOT NULL DEFAULT '',
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_superuser BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMPTZ,
    
    CONSTRAINT chk_user_email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

CREATE INDEX IF NOT EXISTS idx_user_email ON core_user(email);
CREATE INDEX IF NOT EXISTS idx_user_active ON core_user(is_active) WHERE is_active = true;

-- Role (Stammdaten)
CREATE TABLE IF NOT EXISTS core_role (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_system_role BOOLEAN NOT NULL DEFAULT false,
    
    CONSTRAINT chk_role_code_format CHECK (code ~ '^[a-z_]+$')
);

-- Permission (Stammdaten)
CREATE TABLE IF NOT EXISTS core_permission (
    id SERIAL PRIMARY KEY,
    code VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(50) NOT NULL,
    
    CONSTRAINT chk_permission_code_format CHECK (code ~ '^[a-z_]+:[a-z_]+$')
);

CREATE INDEX IF NOT EXISTS idx_permission_category ON core_permission(category);

-- Role-Permission (M:N)
CREATE TABLE IF NOT EXISTS core_role_permission (
    id SERIAL PRIMARY KEY,
    role_id INTEGER NOT NULL REFERENCES core_role(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES core_permission(id) ON DELETE CASCADE,
    
    CONSTRAINT uq_role_permission UNIQUE (role_id, permission_id)
);

CREATE INDEX IF NOT EXISTS idx_role_permission_role ON core_role_permission(role_id);

-- Tenant Membership
CREATE TABLE IF NOT EXISTS core_tenant_membership (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES core_tenant(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES core_user(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES core_role(id) ON DELETE RESTRICT,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    invited_by_id INTEGER REFERENCES core_user(id) ON DELETE SET NULL,
    
    CONSTRAINT uq_membership_tenant_user UNIQUE (tenant_id, user_id),
    CONSTRAINT chk_membership_status CHECK (status IN ('pending', 'active', 'suspended'))
);

CREATE INDEX IF NOT EXISTS idx_membership_tenant ON core_tenant_membership(tenant_id);
CREATE INDEX IF NOT EXISTS idx_membership_user ON core_tenant_membership(user_id);
CREATE INDEX IF NOT EXISTS idx_membership_active ON core_tenant_membership(tenant_id, user_id) 
    WHERE status = 'active';

-- Permission Override
CREATE TABLE IF NOT EXISTS core_permission_override (
    id SERIAL PRIMARY KEY,
    membership_id INTEGER NOT NULL REFERENCES core_tenant_membership(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES core_permission(id) ON DELETE CASCADE,
    is_granted BOOLEAN NOT NULL,
    valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by_id INTEGER NOT NULL REFERENCES core_user(id) ON DELETE RESTRICT,
    reason TEXT,
    
    CONSTRAINT uq_permission_override UNIQUE (membership_id, permission_id),
    CONSTRAINT chk_override_validity CHECK (valid_until IS NULL OR valid_until > valid_from)
);

CREATE INDEX IF NOT EXISTS idx_override_membership ON core_permission_override(membership_id);

-- Stammdaten: Plans
INSERT INTO core_plan (code, name, max_users, max_storage_gb, sort_order) VALUES
    ('free', 'Free', 2, 1, 1),
    ('starter', 'Starter', 5, 10, 2),
    ('professional', 'Professional', 25, 100, 3),
    ('enterprise', 'Enterprise', 1000, 1000, 4)
ON CONFLICT (code) DO NOTHING;

-- Stammdaten: Roles
INSERT INTO core_role (code, name, is_system_role) VALUES
    ('owner', 'Owner', true),
    ('admin', 'Administrator', true),
    ('member', 'Member', true),
    ('viewer', 'Viewer', true)
ON CONFLICT (code) DO NOTHING;

-- Stammdaten: Permissions
INSERT INTO core_permission (code, name, category) VALUES
    ('project:create', 'Create Project', 'project'),
    ('project:read', 'Read Project', 'project'),
    ('project:update', 'Update Project', 'project'),
    ('project:delete', 'Delete Project', 'project'),
    ('model:create', 'Create Model', 'model'),
    ('model:read', 'Read Model', 'model'),
    ('model:update', 'Update Model', 'model'),
    ('model:delete', 'Delete Model', 'model'),
    ('model:parse', 'Parse IFC', 'model'),
    ('model:generate', 'Generate CAD', 'model'),
    ('member:invite', 'Invite Member', 'member'),
    ('member:remove', 'Remove Member', 'member'),
    ('tenant:settings', 'Manage Settings', 'tenant')
ON CONFLICT (code) DO NOTHING;

COMMIT;
