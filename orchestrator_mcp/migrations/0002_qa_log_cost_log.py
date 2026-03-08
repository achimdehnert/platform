"""
orchestrator_mcp/migrations/0002_qa_log_cost_log.py

Idempotent Django migration for QALog and CostLog models per ADR-108.
"""
from __future__ import annotations

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orchestrator_mcp", "0001_deployment_log_review_log"),
    ]

    operations = [
        migrations.CreateModel(
            name="QALog",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="Public ID")),
                ("tenant_id", models.BigIntegerField(db_index=True, default=0, verbose_name="Tenant ID")),
                ("task_id", models.CharField(db_index=True, max_length=200, verbose_name="Task ID")),
                ("task_type", models.CharField(blank=True, max_length=50, verbose_name="Task Type")),
                ("repo", models.CharField(blank=True, max_length=100, verbose_name="Repo")),
                ("branch", models.CharField(blank=True, max_length=200, verbose_name="Branch")),
                ("agent_role", models.CharField(blank=True, max_length=50, verbose_name="Agent Role")),
                ("complexity", models.CharField(default="moderate", max_length=20, verbose_name="Complexity")),
                ("composite_score", models.FloatField(default=0.0, verbose_name="Composite Score")),
                ("completion_score", models.FloatField(default=0.0, verbose_name="Completion Score")),
                ("guardian_score", models.FloatField(default=0.0, verbose_name="Guardian Score")),
                ("adr_compliance_score", models.FloatField(default=0.0, verbose_name="ADR Compliance Score")),
                ("iteration_score", models.FloatField(default=1.0, verbose_name="Iteration Score")),
                ("token_score", models.FloatField(default=1.0, verbose_name="Token Score")),
                ("rollback_level", models.CharField(db_index=True, default="none", max_length=20, verbose_name="Rollback Level")),
                ("is_complete", models.BooleanField(default=False, verbose_name="Is Complete")),
                ("blocking_open", models.JSONField(default=list, verbose_name="Blocking Open Criteria")),
                ("iterations_used", models.IntegerField(default=0, verbose_name="Iterations Used")),
                ("tokens_used", models.IntegerField(default=0, verbose_name="Tokens Used")),
                ("token_budget", models.IntegerField(default=60000, verbose_name="Token Budget")),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True, verbose_name="Deleted At")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created At")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Updated At")),
            ],
            options={
                "verbose_name": "QA Log",
                "verbose_name_plural": "QA Logs",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["task_id"], name="qalog_task_id_idx"),
                    models.Index(fields=["rollback_level"], name="qalog_rollback_idx"),
                    models.Index(fields=["created_at"], name="qalog_created_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="CostLog",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="Public ID")),
                ("tenant_id", models.BigIntegerField(db_index=True, default=0, verbose_name="Tenant ID")),
                ("task_id", models.CharField(db_index=True, max_length=200, verbose_name="Task ID")),
                ("model", models.CharField(blank=True, max_length=100, verbose_name="Model")),
                ("complexity", models.CharField(default="moderate", max_length=20, verbose_name="Complexity")),
                ("agent_role", models.CharField(blank=True, max_length=50, verbose_name="Agent Role")),
                ("tokens_used", models.IntegerField(default=0, verbose_name="Tokens Used")),
                ("token_budget", models.IntegerField(default=60000, verbose_name="Token Budget")),
                ("over_budget", models.BooleanField(db_index=True, default=False, verbose_name="Over Budget")),
                ("utilization", models.FloatField(default=0.0, verbose_name="Utilization")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created At")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Updated At")),
            ],
            options={
                "verbose_name": "Cost Log",
                "verbose_name_plural": "Cost Logs",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["task_id"], name="costlog_task_id_idx"),
                    models.Index(fields=["over_budget"], name="costlog_overbudget_idx"),
                    models.Index(fields=["created_at"], name="costlog_created_idx"),
                ],
            },
        ),
    ]
