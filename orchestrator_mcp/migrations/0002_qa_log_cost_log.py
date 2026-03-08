"""
orchestrator_mcp/migrations/0002_qa_log_cost_log.py

Idempotente Migration für QALog + CostLog per ADR-108.
"""

from __future__ import annotations

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orchestrator_mcp", "0001_deployment_log_review_log"),
    ]

    operations = [
        # ------------------------------------------------------------------
        # QALog
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="QALog",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, unique=True, editable=False, verbose_name="Public ID")),
                ("tenant_id", models.BigIntegerField(db_index=True, default=1, verbose_name="Tenant ID")),
                ("task_id", models.CharField(max_length=255, unique=True, db_index=True, verbose_name="Task ID")),
                ("task_type", models.CharField(max_length=50, verbose_name="Task Type")),
                ("agent_role", models.CharField(max_length=50, verbose_name="Agent Role")),
                ("model_tier", models.CharField(max_length=50, verbose_name="Model Tier")),
                ("repository", models.CharField(max_length=255, blank=True, default="", verbose_name="Repository")),
                ("completion_score", models.FloatField(default=0.0, verbose_name="Completion Score")),
                ("guardian_passed", models.BooleanField(default=False, verbose_name="Guardian Passed")),
                ("coverage_delta", models.FloatField(default=0.0, verbose_name="Coverage Delta")),
                ("adr_compliance", models.BooleanField(default=True, verbose_name="ADR Compliance")),
                ("iteration_count", models.PositiveSmallIntegerField(default=1, verbose_name="Iteration Count")),
                ("composite_score", models.FloatField(default=0.0, db_index=True, verbose_name="Composite Score")),
                ("rollback_level", models.PositiveSmallIntegerField(choices=[(0, "None"), (1, "L1 Re-Engineer"), (2, "L2 Tech Lead"), (3, "L3 User Notify"), (4, "L4 Abort")], default=0, verbose_name="Rollback Level")),
                ("passed", models.BooleanField(default=False, db_index=True, verbose_name="Passed")),
                ("tokens_used", models.PositiveIntegerField(default=0, verbose_name="Tokens Used")),
                ("tokens_budget", models.PositiveIntegerField(default=0, verbose_name="Tokens Budget")),
                ("details", models.JSONField(default=dict, verbose_name="Details")),
                ("evaluated_at", models.DateTimeField(null=True, blank=True, verbose_name="Evaluated At")),
                ("deleted_at", models.DateTimeField(null=True, blank=True, db_index=True, verbose_name="Deleted At")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created At")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Updated At")),
            ],
            options={"verbose_name": "QA Log", "verbose_name_plural": "QA Logs", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="qalog",
            index=models.Index(fields=["tenant_id", "passed"], name="orc_qalog_tenant_passed_idx"),
        ),
        migrations.AddIndex(
            model_name="qalog",
            index=models.Index(fields=["agent_role", "composite_score"], name="orc_qalog_role_score_idx"),
        ),
        migrations.AddIndex(
            model_name="qalog",
            index=models.Index(fields=["repository", "-created_at"], name="orc_qalog_repo_created_idx"),
        ),
        # ------------------------------------------------------------------
        # CostLog
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="CostLog",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, unique=True, editable=False, verbose_name="Public ID")),
                ("tenant_id", models.BigIntegerField(db_index=True, default=1, verbose_name="Tenant ID")),
                ("task_id", models.CharField(max_length=255, unique=True, db_index=True, verbose_name="Task ID")),
                ("task_type", models.CharField(max_length=50, verbose_name="Task Type")),
                ("agent_role", models.CharField(max_length=50, verbose_name="Agent Role")),
                ("model_tier", models.CharField(max_length=50, verbose_name="Model Tier")),
                ("repository", models.CharField(max_length=255, blank=True, default="", verbose_name="Repository")),
                ("tokens_used", models.PositiveIntegerField(default=0, verbose_name="Tokens Used")),
                ("tokens_budget", models.PositiveIntegerField(default=0, verbose_name="Tokens Budget")),
                ("overrun", models.BooleanField(default=False, db_index=True, verbose_name="Budget Overrun")),
                ("logged_at", models.DateTimeField(null=True, blank=True, verbose_name="Logged At")),
                ("deleted_at", models.DateTimeField(null=True, blank=True, db_index=True, verbose_name="Deleted At")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created At")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Updated At")),
            ],
            options={"verbose_name": "Cost Log", "verbose_name_plural": "Cost Logs", "ordering": ["-logged_at"]},
        ),
        migrations.AddIndex(
            model_name="costlog",
            index=models.Index(fields=["tenant_id", "overrun"], name="orc_costlog_tenant_overrun_idx"),
        ),
        migrations.AddIndex(
            model_name="costlog",
            index=models.Index(fields=["agent_role", "-logged_at"], name="orc_costlog_role_logged_idx"),
        ),
        migrations.AddIndex(
            model_name="costlog",
            index=models.Index(fields=["repository", "-logged_at"], name="orc_costlog_repo_logged_idx"),
        ),
        migrations.AddIndex(
            model_name="costlog",
            index=models.Index(fields=["model_tier", "-logged_at"], name="orc_costlog_tier_logged_idx"),
        ),
    ]
