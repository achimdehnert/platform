"""
orchestrator_mcp/migrations/versions/0043_model_route_config.py

Alembic-Migration: model_route_configs + routing_reason in llm_calls

Idempotent: IF NOT EXISTS auf allen Statements.
Rollback: Tabelle droppen + Spalte aus llm_calls entfernen.

Revision: 0043
Depends on: 0042 (llm_calls Tabelle aus ADR-115)
"""
from __future__ import annotations

from alembic import op

revision = "0043_model_route_config"
down_revision = "0042_llm_calls_pricing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # 1. model_route_configs Tabelle (ADR-116)                            #
    # ------------------------------------------------------------------ #
    op.execute("""
        CREATE TABLE IF NOT EXISTS model_route_configs (
            id              BIGSERIAL       PRIMARY KEY,
            public_id       UUID            NOT NULL DEFAULT gen_random_uuid(),
            agent_role      TEXT            NOT NULL,
            complexity_hint TEXT            NOT NULL,
            model           TEXT            NOT NULL,
            tier            TEXT            NOT NULL,
            provider        TEXT,
            budget_model    TEXT,
            budget_tier     TEXT,
            description     TEXT,
            is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
            created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
            deleted_at      TIMESTAMPTZ
        )
    """)

    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS model_route_configs_public_id_idx
            ON model_route_configs (public_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS model_route_configs_role_idx
            ON model_route_configs (agent_role)
    """)
    # Partial Unique: nur eine aktive Route pro (role, complexity)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_model_route_configs_active
            ON model_route_configs (agent_role, complexity_hint)
            WHERE deleted_at IS NULL AND is_active = TRUE
    """)

    # ------------------------------------------------------------------ #
    # 2. Seed-Daten (Idempotent via ON CONFLICT DO NOTHING)               #
    # Discord-Rollen NICHT enthalten — Discord nutzt ENV-Config           #
    # ------------------------------------------------------------------ #
    op.execute("""
        INSERT INTO model_route_configs
            (agent_role, complexity_hint, model, tier, provider, budget_model, budget_tier, description)
        VALUES
            ('developer', 'simple',       'openai/gpt-4o-mini',           'budget',   'openai',    'meta-llama/llama-3.1-8b-instruct', 'local',    'Einfache Dev-Tasks'),
            ('developer', 'moderate',     'openai/gpt-4o',                'standard', 'openai',    'openai/gpt-4o-mini',               'budget',   'Standard Dev-Tasks'),
            ('developer', 'complex',      'anthropic/claude-3.5-sonnet',  'premium',  'anthropic', 'openai/gpt-4o',                    'standard', 'Komplexe Dev-Tasks'),
            ('tester',    'simple',       'openai/gpt-4o-mini',           'budget',   'openai',    'meta-llama/llama-3.1-8b-instruct', 'local',    'Einfache Test-Generierung'),
            ('tester',    'moderate',     'openai/gpt-4o-mini',           'budget',   'openai',    'meta-llama/llama-3.1-8b-instruct', 'local',    'Standard Test-Generierung'),
            ('tester',    'complex',      'openai/gpt-4o',                'standard', 'openai',    'openai/gpt-4o-mini',               'budget',   'Komplexe Test-Suites'),
            ('guardian',  'moderate',     'openai/gpt-4o',                'standard', 'openai',    'openai/gpt-4o-mini',               'budget',   'Guardian Code Review'),
            ('guardian',  'complex',      'anthropic/claude-3.5-sonnet',  'premium',  'anthropic', 'openai/gpt-4o',                    'standard', 'Guardian kritischer Code'),
            ('tech_lead', 'complex',      'anthropic/claude-3.5-sonnet',  'premium',  'anthropic', 'openai/gpt-4o',                    'standard', 'Tech Lead Review'),
            ('tech_lead', 'architectural','anthropic/claude-3.5-sonnet',  'premium',  'anthropic', 'openai/gpt-4o',                    'standard', 'Architektur-Entscheidungen'),
            ('planner',   'complex',      'anthropic/claude-3.5-sonnet',  'premium',  'anthropic', 'openai/gpt-4o',                    'standard', 'Task-Planung'),
            ('re_engineer','moderate',    'openai/gpt-4o',                'standard', 'openai',    'openai/gpt-4o-mini',               'budget',   'Refactoring Standard'),
            ('re_engineer','complex',     'anthropic/claude-3.5-sonnet',  'premium',  'anthropic', 'openai/gpt-4o',                    'standard', 'Komplexes Re-Engineering'),
            -- UC-SE-2: Guardian trivial (Whitespace/Format-Checks)
            ('guardian',  'trivial',      'openai/gpt-4o-mini',           'budget',   'openai',    'meta-llama/llama-3.1-8b-instruct', 'local',    'Guardian Format-Checks'),
            -- UC-SE-5: Security Auditor — budget_model == model (kein Downgrade!)
            ('security_auditor','moderate','anthropic/claude-3.5-sonnet', 'premium',  'anthropic', 'anthropic/claude-3.5-sonnet',      'premium',  'Security Audit Standard'),
            ('security_auditor','complex', 'anthropic/claude-3.5-sonnet', 'premium',  'anthropic', 'anthropic/claude-3.5-sonnet',      'premium',  'Security Audit komplex')
        ON CONFLICT DO NOTHING
    """)

    # ------------------------------------------------------------------ #
    # 3. routing_reason Spalte zu llm_calls hinzufügen (ADR-115 Extension)#
    # ------------------------------------------------------------------ #
    op.execute("""
        ALTER TABLE llm_calls
        ADD COLUMN IF NOT EXISTS routing_reason TEXT
            DEFAULT NULL
    """)

    op.execute("""
        COMMENT ON COLUMN llm_calls.routing_reason IS
            'ADR-116: Begründung der Routing-Entscheidung. '
            'Format: rule:role+complexity→tier | budget_downgrade:80%|... | '
            'adr068_router:confidence=0.85 | emergency:budget>100%'
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS model_route_configs CASCADE")
    op.execute("""
        ALTER TABLE llm_calls
        DROP COLUMN IF EXISTS routing_reason
    """)
