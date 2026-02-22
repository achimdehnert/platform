"""Create content_store schema: items, relations, views (ADR-062 Phase 1).

Revision ID: 0001
Revises: 
Create Date: 2026-02-22
"""

from __future__ import annotations

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS content_store")

    op.execute("""
        CREATE TABLE IF NOT EXISTS content_store.items (
            id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            source_svc    TEXT        NOT NULL,
            source_type   TEXT        NOT NULL,
            source_id     TEXT        NOT NULL,
            tenant_id     UUID,
            content       TEXT        NOT NULL,
            content_hash  TEXT        NOT NULL,
            prompt_key    TEXT,
            model_used    TEXT        NOT NULL,
            version       INT         NOT NULL DEFAULT 1,
            parent_id     UUID        REFERENCES content_store.items(id) ON DELETE SET NULL,
            tags          TEXT[]      NOT NULL DEFAULT '{}',
            properties    JSONB       NOT NULL DEFAULT '{}',
            created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS content_store.relations (
            id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            source_item   UUID        NOT NULL
                              REFERENCES content_store.items(id) ON DELETE CASCADE,
            target_ref    TEXT        NOT NULL,
            relation_type TEXT        NOT NULL,
            tenant_id     UUID,
            weight        FLOAT       NOT NULL DEFAULT 1.0,
            properties    JSONB       NOT NULL DEFAULT '{}',
            created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_items_svc_type_src "
        "ON content_store.items (source_svc, source_type, source_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_items_tenant "
        "ON content_store.items (tenant_id) WHERE tenant_id IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_items_parent "
        "ON content_store.items (parent_id) WHERE parent_id IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_items_tags "
        "ON content_store.items USING GIN (tags)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_relations_source "
        "ON content_store.relations (source_item, relation_type)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_relations_target "
        "ON content_store.relations (target_ref)"
    )

    op.execute("""
        CREATE OR REPLACE VIEW content_store.v_decisions AS
            SELECT * FROM content_store.items
            WHERE source_svc = 'agent-team' AND tenant_id IS NULL
    """)

    op.execute("""
        CREATE OR REPLACE VIEW content_store.v_narrative AS
            SELECT * FROM content_store.items
            WHERE source_svc = 'travel-beat' AND tenant_id IS NOT NULL
    """)

    op.execute("""
        CREATE OR REPLACE VIEW content_store.v_drafts AS
            SELECT *,
                   ROW_NUMBER() OVER (
                       PARTITION BY source_id ORDER BY version DESC
                   ) AS version_rank
            FROM content_store.items
            WHERE source_svc = 'bfagent'
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS content_store.v_drafts")
    op.execute("DROP VIEW IF EXISTS content_store.v_narrative")
    op.execute("DROP VIEW IF EXISTS content_store.v_decisions")
    op.execute("DROP TABLE IF EXISTS content_store.relations")
    op.execute("DROP TABLE IF EXISTS content_store.items")
    op.execute("DROP SCHEMA IF EXISTS content_store")
