"""
orchestrator_mcp/migrations/0003_model_route_config.py

Django-Migration: ModelRouteConfig + routing_reason in llm_calls

Idempotent: IF NOT EXISTS auf allen Raw-SQL-Statements.
Rollback: Tabelle droppen + Spalte aus llm_calls entfernen.

Depends on: 0002_qa_log_cost_log (ADR-108)
"""
from __future__ import annotations

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orchestrator_mcp", "0002_qa_log_cost_log"),
    ]

    operations = [
        # ------------------------------------------------------------------ #
        # 1. ModelRouteConfig Tabelle (ADR-116)                              #
        # ------------------------------------------------------------------ #
        migrations.CreateModel(
            name="ModelRouteConfig",
            fields=[
                (
                    "id",
                    models.BigAutoField(primary_key=True, serialize=False),
                ),
                (
                    "public_id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        unique=True,
                        verbose_name="Public ID",
                    ),
                ),
                (
                    "agent_role",
                    models.CharField(
                        db_index=True,
                        max_length=50,
                        verbose_name="Agent Role",
                    ),
                ),
                (
                    "complexity_hint",
                    models.CharField(
                        max_length=20,
                        verbose_name="Complexity Hint",
                    ),
                ),
                (
                    "model",
                    models.CharField(
                        max_length=200,
                        verbose_name="Model",
                    ),
                ),
                (
                    "tier",
                    models.CharField(
                        max_length=20,
                        verbose_name="Tier",
                    ),
                ),
                (
                    "provider",
                    models.CharField(
                        blank=True,
                        max_length=50,
                        verbose_name="Provider",
                    ),
                ),
                (
                    "budget_model",
                    models.CharField(
                        blank=True,
                        max_length=200,
                        verbose_name="Budget Model",
                    ),
                ),
                (
                    "budget_tier",
                    models.CharField(
                        blank=True,
                        max_length=20,
                        verbose_name="Budget Tier",
                    ),
                ),
                (
                    "description",
                    models.TextField(blank=True, verbose_name="Description"),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        db_index=True,
                        default=True,
                        verbose_name="Is Active",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Created At"
                    ),
                ),
                (
                    "deleted_at",
                    models.DateTimeField(
                        blank=True,
                        db_index=True,
                        null=True,
                        verbose_name="Deleted At",
                    ),
                ),
            ],
            options={
                "verbose_name": "Model Route Config",
                "verbose_name_plural": "Model Route Configs",
                "ordering": ["agent_role", "complexity_hint"],
                "indexes": [
                    models.Index(
                        fields=["agent_role", "complexity_hint"],
                        name="modelroute_role_complexity_idx",
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=["agent_role", "complexity_hint"],
                        condition=models.Q(
                            deleted_at__isnull=True, is_active=True
                        ),
                        name="uq_model_route_active",
                    ),
                ],
            },
        ),
        # ------------------------------------------------------------------ #
        # 2. routing_reason Spalte zu llm_calls (ADR-115 Extension, K-01)   #
        # Idempotent via Raw-SQL (Django hat kein IF NOT EXISTS in AddField) #
        # ------------------------------------------------------------------ #
        migrations.RunSQL(
            sql="""
                ALTER TABLE llm_calls
                ADD COLUMN IF NOT EXISTS routing_reason TEXT DEFAULT NULL;

                COMMENT ON COLUMN llm_calls.routing_reason IS
                    'ADR-116: Begründung der Routing-Entscheidung. '
                    'Format: rule:role+complexity->tier | '
                    'budget_downgrade:80% | emergency:budget>100%';
            """,
            reverse_sql="""
                ALTER TABLE llm_calls
                DROP COLUMN IF EXISTS routing_reason;
            """,
        ),
        # ------------------------------------------------------------------ #
        # 3. Seed-Daten (Idempotent via ON CONFLICT DO NOTHING)              #
        # Discord-Rollen NICHT enthalten — Discord nutzt ENV-Config          #
        # ------------------------------------------------------------------ #
        migrations.RunSQL(
            sql="""
                INSERT INTO orchestrator_mcp_modelrouteconfig
                    (public_id, agent_role, complexity_hint, model, tier,
                     provider, budget_model, budget_tier, description,
                     is_active, created_at)
                VALUES
                    -- Developer
                    (gen_random_uuid(), 'developer', 'simple',
                     'openai/gpt-4o-mini', 'budget', 'openai',
                     'meta-llama/llama-3.1-8b-instruct', 'local',
                     'Einfache Dev-Tasks', TRUE, NOW()),
                    (gen_random_uuid(), 'developer', 'moderate',
                     'openai/gpt-4o', 'standard', 'openai',
                     'openai/gpt-4o-mini', 'budget',
                     'Standard Dev-Tasks', TRUE, NOW()),
                    (gen_random_uuid(), 'developer', 'complex',
                     'anthropic/claude-3.5-sonnet', 'premium', 'anthropic',
                     'openai/gpt-4o', 'standard',
                     'Komplexe Dev-Tasks', TRUE, NOW()),
                    -- Tester
                    (gen_random_uuid(), 'tester', 'simple',
                     'openai/gpt-4o-mini', 'budget', 'openai',
                     'meta-llama/llama-3.1-8b-instruct', 'local',
                     'Einfache Test-Generierung', TRUE, NOW()),
                    (gen_random_uuid(), 'tester', 'moderate',
                     'openai/gpt-4o-mini', 'budget', 'openai',
                     'meta-llama/llama-3.1-8b-instruct', 'local',
                     'Standard Test-Generierung', TRUE, NOW()),
                    (gen_random_uuid(), 'tester', 'complex',
                     'openai/gpt-4o', 'standard', 'openai',
                     'openai/gpt-4o-mini', 'budget',
                     'Komplexe Test-Suites', TRUE, NOW()),
                    -- Guardian
                    (gen_random_uuid(), 'guardian', 'trivial',
                     'openai/gpt-4o-mini', 'budget', 'openai',
                     'meta-llama/llama-3.1-8b-instruct', 'local',
                     'Guardian Format-Checks (UC-SE-2)', TRUE, NOW()),
                    (gen_random_uuid(), 'guardian', 'moderate',
                     'openai/gpt-4o', 'standard', 'openai',
                     'openai/gpt-4o-mini', 'budget',
                     'Guardian Code Review', TRUE, NOW()),
                    (gen_random_uuid(), 'guardian', 'complex',
                     'anthropic/claude-3.5-sonnet', 'premium', 'anthropic',
                     'openai/gpt-4o', 'standard',
                     'Guardian kritischer Code', TRUE, NOW()),
                    -- Tech Lead
                    (gen_random_uuid(), 'tech_lead', 'complex',
                     'anthropic/claude-3.5-sonnet', 'premium', 'anthropic',
                     'openai/gpt-4o', 'standard',
                     'Tech Lead Review', TRUE, NOW()),
                    (gen_random_uuid(), 'tech_lead', 'architectural',
                     'anthropic/claude-3.5-sonnet', 'premium', 'anthropic',
                     'openai/gpt-4o', 'standard',
                     'Architektur-Entscheidungen', TRUE, NOW()),
                    -- Planner
                    (gen_random_uuid(), 'planner', 'complex',
                     'anthropic/claude-3.5-sonnet', 'premium', 'anthropic',
                     'openai/gpt-4o', 'standard',
                     'Task-Planung', TRUE, NOW()),
                    -- Re-Engineer
                    (gen_random_uuid(), 're_engineer', 'moderate',
                     'openai/gpt-4o', 'standard', 'openai',
                     'openai/gpt-4o-mini', 'budget',
                     'Refactoring Standard', TRUE, NOW()),
                    (gen_random_uuid(), 're_engineer', 'complex',
                     'anthropic/claude-3.5-sonnet', 'premium', 'anthropic',
                     'openai/gpt-4o', 'standard',
                     'Komplexes Re-Engineering', TRUE, NOW()),
                    -- Security Auditor (UC-SE-5) — kein Downgrade
                    (gen_random_uuid(), 'security_auditor', 'moderate',
                     'anthropic/claude-3.5-sonnet', 'premium', 'anthropic',
                     'anthropic/claude-3.5-sonnet', 'premium',
                     'Security Audit Standard — niemals downgegradet',
                     TRUE, NOW()),
                    (gen_random_uuid(), 'security_auditor', 'complex',
                     'anthropic/claude-3.5-sonnet', 'premium', 'anthropic',
                     'anthropic/claude-3.5-sonnet', 'premium',
                     'Security Audit komplex — niemals downgegradet',
                     TRUE, NOW())
                ON CONFLICT DO NOTHING;
            """,
            reverse_sql="DELETE FROM orchestrator_mcp_modelrouteconfig;",
        ),
    ]
