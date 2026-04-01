"""
orchestrator_mcp/migrations/0001_initial.py

Idempotente Migration für AgentMemoryEntry + AgentSession.

Platform Standards:
  - SeparateDatabaseAndState für pgvector-Extension (idempotent)
  - VectorField via pgvector.django
"""
from __future__ import annotations

import uuid
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models
import pgvector.django


class Migration(migrations.Migration):

    initial = True

    dependencies: list = []

    operations = [
        # ------------------------------------------------------------------
        # Schritt 1: pgvector Extension (idempotent via SeparateDatabaseAndState)
        # ------------------------------------------------------------------
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="CREATE EXTENSION IF NOT EXISTS vector;",
                    reverse_sql="-- Extension nicht entfernen (shared resource)",
                    hints={"target_db": "default"},
                ),
            ],
            state_operations=[],
        ),

        # ------------------------------------------------------------------
        # Schritt 2: AgentMemoryEntry
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="AgentMemoryEntry",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
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
                    "tenant_id",
                    models.BigIntegerField(
                        db_index=True,
                        verbose_name="Tenant ID",
                    ),
                ),
                (
                    "entry_key",
                    models.CharField(
                        max_length=512,
                        verbose_name="Entry Key",
                    ),
                ),
                (
                    "entry_type",
                    models.CharField(
                        choices=[
                            ("error_pattern", "Error Pattern"),
                            ("lesson_learned", "Lesson Learned"),
                            ("decision", "Decision"),
                            ("context", "Session Context"),
                            ("task_result", "Task Result"),
                            ("rule_violation", "Rule Violation"),
                            ("repo_fact", "Repo Fact"),
                        ],
                        db_index=True,
                        max_length=64,
                        verbose_name="Entry Type",
                    ),
                ),
                (
                    "repo",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        max_length=256,
                        verbose_name="Repository",
                    ),
                ),
                ("title", models.CharField(max_length=512, verbose_name="Title")),
                ("content", models.TextField(verbose_name="Content")),
                ("tags", models.JSONField(default=list, verbose_name="Tags")),
                (
                    "structured_data",
                    models.JSONField(
                        blank=True,
                        null=True,
                        verbose_name="Structured Data",
                    ),
                ),
                (
                    "embedding",
                    pgvector.django.VectorField(
                        blank=True,
                        dimensions=1536,
                        null=True,
                        verbose_name="Embedding",
                    ),
                ),
                (
                    "relevance_score",
                    models.FloatField(default=1.0, verbose_name="Relevance Score"),
                ),
                (
                    "access_count",
                    models.PositiveIntegerField(
                        default=0, verbose_name="Access Count"
                    ),
                ),
                (
                    "last_accessed_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Last Accessed"
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
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
                "verbose_name": "Agent Memory Entry",
                "verbose_name_plural": "Agent Memory Entries",
                "ordering": ["-relevance_score", "-updated_at"],
            },
        ),

        # ------------------------------------------------------------------
        # Schritt 3: AgentSession
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="AgentSession",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                (
                    "public_id",
                    models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
                ),
                ("tenant_id", models.BigIntegerField(db_index=True)),
                ("repo", models.CharField(db_index=True, max_length=256)),
                ("task_description", models.TextField(blank=True)),
                ("started_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "ended_at",
                    models.DateTimeField(blank=True, db_index=True, null=True),
                ),
                ("error_count", models.PositiveIntegerField(default=0)),
                ("correction_count", models.PositiveIntegerField(default=0)),
                ("memory_entries_written", models.PositiveIntegerField(default=0)),
                (
                    "deleted_at",
                    models.DateTimeField(blank=True, db_index=True, null=True),
                ),
            ],
            options={
                "verbose_name": "Agent Session",
                "verbose_name_plural": "Agent Sessions",
                "ordering": ["-started_at"],
            },
        ),

        # ------------------------------------------------------------------
        # Schritt 4: Constraints + Indexes
        # ------------------------------------------------------------------
        migrations.AddConstraint(
            model_name="agentmemoryentry",
            constraint=models.UniqueConstraint(
                condition=models.Q(deleted_at__isnull=True),
                fields=["tenant_id", "entry_key"],
                name="unique_active_entry_key_per_tenant",
            ),
        ),
        migrations.AddIndex(
            model_name="agentmemoryentry",
            index=models.Index(
                fields=["tenant_id", "entry_type", "repo"],
                name="agentmemory_tenant_type_repo_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="agentmemoryentry",
            index=models.Index(
                fields=["tenant_id", "updated_at"],
                name="agentmemory_tenant_updated_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="agentmemoryentry",
            index=models.Index(
                fields=["entry_type", "relevance_score"],
                name="agentmemory_type_relevance_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="agentsession",
            index=models.Index(
                fields=["tenant_id", "repo", "-started_at"],
                name="agentsession_tenant_repo_started_idx",
            ),
        ),

        # ------------------------------------------------------------------
        # Schritt 5: pgvector HNSW-Index für embedding (via RunSQL, idempotent)
        # ------------------------------------------------------------------
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    CREATE INDEX IF NOT EXISTS agentmemory_embedding_hnsw_idx
                    ON orchestrator_mcp_agentmemoryentry
                    USING hnsw (embedding vector_cosine_ops)
                    WITH (m = 16, ef_construction = 64);
                    """,
                    reverse_sql="""
                    DROP INDEX IF EXISTS agentmemory_embedding_hnsw_idx;
                    """,
                ),
            ],
            state_operations=[],
        ),
    ]
