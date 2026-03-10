"""
llm_mcp_service/migrations/versions/0042_llm_calls_and_pricing.py

Alembic-Migration: llm_calls + llm_model_pricing + Grafana-RO-User

Idempotent: IF NOT EXISTS auf allen Statements.
Rollback: Tabellen droppen (kein Datenverlust bei neuen Tabellen).

Revision: 0042
"""
from __future__ import annotations

import textwrap

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TIMESTAMPTZ, UUID

# revision identifiers
revision = "0042_llm_calls_pricing"
down_revision = "0041"  # Vorherige Migration anpassen
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # 1. llm_calls Tabelle                                                 #
    # ------------------------------------------------------------------ #
    op.execute("""
        CREATE TABLE IF NOT EXISTS llm_calls (
            id                BIGSERIAL       PRIMARY KEY,
            public_id         UUID            NOT NULL DEFAULT gen_random_uuid(),
            tenant_id         BIGINT          NOT NULL,
            task_id           TEXT,
            repo              TEXT,
            source            TEXT,
            call_type         TEXT            NOT NULL DEFAULT 'chat',
            request_id        TEXT,
            model             TEXT            NOT NULL,
            prompt_tokens     INTEGER         NOT NULL DEFAULT 0,
            completion_tokens INTEGER         NOT NULL DEFAULT 0,
            total_tokens      INTEGER         NOT NULL DEFAULT 0,
            cost_usd          NUMERIC(12,8)   NOT NULL DEFAULT 0,
            duration_ms       INTEGER,
            latency_p95_ms    INTEGER,
            error             BOOLEAN         NOT NULL DEFAULT FALSE,
            error_code        TEXT,
            error_message     TEXT,
            created_at        TIMESTAMPTZ     NOT NULL DEFAULT now(),
            deleted_at        TIMESTAMPTZ
        )
    """)

    # Indices (IF NOT EXISTS für Idempotenz)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS llm_calls_public_id_idx
            ON llm_calls (public_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS llm_calls_created_at_desc_idx
            ON llm_calls (created_at DESC)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS llm_calls_tenant_id_idx
            ON llm_calls (tenant_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS llm_calls_task_id_idx
            ON llm_calls (task_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS llm_calls_repo_idx
            ON llm_calls (repo)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS llm_calls_model_created_idx
            ON llm_calls (model, created_at)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS llm_calls_tenant_task_idx
            ON llm_calls (tenant_id, task_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS llm_calls_active_idx
            ON llm_calls (tenant_id, created_at)
            WHERE deleted_at IS NULL
    """)

    # ------------------------------------------------------------------ #
    # 2. llm_model_pricing Tabelle                                         #
    # ------------------------------------------------------------------ #
    op.execute("""
        CREATE TABLE IF NOT EXISTS llm_model_pricing (
            id                BIGSERIAL       PRIMARY KEY,
            public_id         UUID            NOT NULL DEFAULT gen_random_uuid(),
            model             TEXT            NOT NULL,
            provider          TEXT,
            input_per_1m_usd  NUMERIC(12,8)   NOT NULL,
            output_per_1m_usd NUMERIC(12,8)   NOT NULL,
            valid_from        TIMESTAMPTZ     NOT NULL DEFAULT now(),
            valid_until       TIMESTAMPTZ,
            created_at        TIMESTAMPTZ     NOT NULL DEFAULT now(),
            deleted_at        TIMESTAMPTZ
        )
    """)

    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS llm_model_pricing_public_id_idx
            ON llm_model_pricing (public_id)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS llm_model_pricing_model_idx
            ON llm_model_pricing (model)
    """)
    # Partial-Unique: nur ein aktuell gültiger Preis pro Modell
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_llm_model_pricing_current
            ON llm_model_pricing (model)
            WHERE valid_until IS NULL AND deleted_at IS NULL
    """)

    # ------------------------------------------------------------------ #
    # 3. Seed-Daten (Idempotent via ON CONFLICT DO NOTHING)                #
    # ------------------------------------------------------------------ #
    op.execute("""
        INSERT INTO llm_model_pricing
            (model, provider, input_per_1m_usd, output_per_1m_usd)
        VALUES
            ('openai/gpt-4o',                    'openai',    2.50,  10.00),
            ('openai/gpt-4o-mini',               'openai',    0.15,   0.60),
            ('anthropic/claude-3.5-sonnet',      'anthropic', 3.00,  15.00),
            ('anthropic/claude-opus-4',          'anthropic',15.00,  75.00),
            ('meta-llama/llama-3.1-70b-instruct','meta',      0.52,   0.75),
            ('google/gemini-2.0-flash-001',      'google',    0.10,   0.40)
        ON CONFLICT DO NOTHING
    """)

    # ------------------------------------------------------------------ #
    # 4. Grafana Read-Only DB User                                         #
    # (Ausführung nur wenn User noch nicht existiert)                      #
    # Achtung: Passwort via Umgebungsvariable, nicht hardcodiert!          #
    # Für Produktion: via setup_grafana_db_user Management Command         #
    # ------------------------------------------------------------------ #
    # NICHT in Alembic ausführen (benötigt SUPERUSER-Rechte außerhalb der
    # App-DB-Verbindung). Stattdessen in setup_grafana_db_user.py.


def downgrade() -> None:
    # Reihenfolge beachten (keine FK-Abhängigkeiten, aber trotzdem sauber)
    op.execute("DROP TABLE IF EXISTS llm_calls CASCADE")
    op.execute("DROP TABLE IF EXISTS llm_model_pricing CASCADE")
