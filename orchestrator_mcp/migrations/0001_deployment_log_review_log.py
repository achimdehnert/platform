"""
orchestrator_mcp/migrations/0001_deployment_log_review_log.py

Idempotente Migration für DeploymentLog + ReviewLog.

Platform-standards:
  - SeparateDatabaseAndState nicht nötig (neue Tabellen, kein State-Transfer)
  - Idempotent: keine RunPython, nur DDL
  - Partial Index via UniqueConstraint(condition=Q(...))
"""

from __future__ import annotations

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies: list[tuple[str, str]] = []

    operations = [
        # ------------------------------------------------------------------
        # DeploymentLog
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="DeploymentLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(primary_key=True, serialize=False),
                ),
                (
                    "public_id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        unique=True,
                        editable=False,
                        verbose_name="Public ID",
                    ),
                ),
                (
                    "tenant_id",
                    models.BigIntegerField(
                        db_index=True, verbose_name="Tenant ID"
                    ),
                ),
                (
                    "repository",
                    models.CharField(
                        max_length=255,
                        verbose_name="Repository",
                        help_text="e.g. org/repo-name",
                    ),
                ),
                (
                    "service_name",
                    models.CharField(
                        max_length=100,
                        verbose_name="Service Name",
                        help_text="Docker Compose service identifier",
                    ),
                ),
                (
                    "image_tag",
                    models.CharField(
                        max_length=255,
                        verbose_name="Image Tag",
                        help_text="GHCR image tag deployed",
                    ),
                ),
                (
                    "previous_image_tag",
                    models.CharField(
                        max_length=255,
                        blank=True,
                        default="",
                        verbose_name="Previous Image Tag",
                        help_text="Tag before this deployment \u2014 used for rollback",
                    ),
                ),
                (
                    "git_sha",
                    models.CharField(max_length=40, verbose_name="Git SHA"),
                ),
                (
                    "git_branch",
                    models.CharField(
                        max_length=255, default="main", verbose_name="Git Branch"
                    ),
                ),
                (
                    "pr_number",
                    models.PositiveIntegerField(
                        null=True,
                        blank=True,
                        verbose_name="PR Number",
                        help_text="GitHub PR that triggered this deployment",
                    ),
                ),
                (
                    "triggered_by",
                    models.CharField(
                        max_length=100,
                        verbose_name="Triggered By",
                        help_text="GitHub Actions runner or manual user",
                    ),
                ),
                (
                    "trigger",
                    models.CharField(
                        max_length=20,
                        choices=[
                            ("git_push_main", "Git Push to main"),
                            ("manual", "Manual Trigger"),
                            ("rollback", "Rollback Trigger"),
                        ],
                        default="git_push_main",
                        verbose_name="Trigger",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=20,
                        choices=[
                            ("pending", "Pending"),
                            ("pre_check", "Pre-Check"),
                            ("migrating", "Migrating"),
                            ("deploying", "Deploying"),
                            ("health_checking", "Health Checking"),
                            ("deployed", "Deployed"),
                            ("rolling_back", "Rolling Back"),
                            ("failed", "Failed"),
                            ("rolled_back", "Rolled Back"),
                        ],
                        default="pending",
                        db_index=True,
                        verbose_name="Status",
                    ),
                ),
                (
                    "started_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Started At"
                    ),
                ),
                (
                    "completed_at",
                    models.DateTimeField(
                        null=True, blank=True, verbose_name="Completed At"
                    ),
                ),
                (
                    "had_pending_migrations",
                    models.BooleanField(
                        default=False, verbose_name="Had Pending Migrations"
                    ),
                ),
                (
                    "had_breaking_migrations",
                    models.BooleanField(
                        default=False, verbose_name="Had Breaking Migrations"
                    ),
                ),
                (
                    "migration_names",
                    models.JSONField(
                        default=list,
                        verbose_name="Migration Names",
                        help_text="List of applied migration identifiers",
                    ),
                ),
                (
                    "health_check_attempts",
                    models.PositiveSmallIntegerField(
                        default=0, verbose_name="Health Check Attempts"
                    ),
                ),
                (
                    "health_check_passed",
                    models.BooleanField(
                        null=True, verbose_name="Health Check Passed"
                    ),
                ),
                (
                    "gate_level",
                    models.PositiveSmallIntegerField(
                        default=2,
                        verbose_name="Gate Level",
                        help_text="0=Auto, 1=Agent, 2=Human-Approval, 3=Tech-Lead",
                    ),
                ),
                (
                    "approved_by",
                    models.CharField(
                        max_length=100,
                        blank=True,
                        default="",
                        verbose_name="Approved By",
                        help_text="GitHub username who gave Gate-2 approval",
                    ),
                ),
                (
                    "error_message",
                    models.TextField(
                        blank=True, default="", verbose_name="Error Message"
                    ),
                ),
                (
                    "rollback_reason",
                    models.TextField(
                        blank=True, default="", verbose_name="Rollback Reason"
                    ),
                ),
                (
                    "duration_seconds",
                    models.PositiveIntegerField(
                        null=True, blank=True, verbose_name="Duration (seconds)"
                    ),
                ),
                (
                    "deleted_at",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        db_index=True,
                        verbose_name="Deleted At",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Created At"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True, verbose_name="Updated At"
                    ),
                ),
            ],
            options={
                "verbose_name": "Deployment Log",
                "verbose_name_plural": "Deployment Logs",
                "ordering": ["-started_at"],
            },
        ),
        migrations.AddIndex(
            model_name="deploymentlog",
            index=models.Index(
                fields=["tenant_id", "status"],
                name="orchestrator_deplog_tenant_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="deploymentlog",
            index=models.Index(
                fields=["repository", "git_sha"],
                name="orchestrator_deplog_repo_sha_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="deploymentlog",
            index=models.Index(
                fields=["tenant_id", "-started_at"],
                name="orchestrator_deplog_tenant_started_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="deploymentlog",
            constraint=models.UniqueConstraint(
                condition=models.Q(
                    status__in=[
                        "pending",
                        "pre_check",
                        "migrating",
                        "deploying",
                        "health_checking",
                    ]
                ),
                fields=["tenant_id", "service_name"],
                name="unique_active_deployment_per_service",
            ),
        ),
        # ------------------------------------------------------------------
        # ReviewLog
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="ReviewLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(primary_key=True, serialize=False),
                ),
                (
                    "public_id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        unique=True,
                        editable=False,
                        verbose_name="Public ID",
                    ),
                ),
                (
                    "tenant_id",
                    models.BigIntegerField(
                        db_index=True, verbose_name="Tenant ID"
                    ),
                ),
                (
                    "repository",
                    models.CharField(
                        max_length=255, verbose_name="Repository"
                    ),
                ),
                (
                    "pr_number",
                    models.PositiveIntegerField(verbose_name="PR Number"),
                ),
                (
                    "pr_author",
                    models.CharField(
                        max_length=100, verbose_name="PR Author"
                    ),
                ),
                (
                    "git_sha",
                    models.CharField(max_length=40, verbose_name="Git SHA"),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=20,
                        choices=[
                            ("pending", "Pending"),
                            ("running", "Running"),
                            ("passed", "Passed"),
                            ("failed", "Failed"),
                            ("overridden", "Overridden"),
                        ],
                        default="pending",
                        db_index=True,
                        verbose_name="Status",
                    ),
                ),
                (
                    "blocking_issues",
                    models.JSONField(
                        default=list, verbose_name="Blocking Issues"
                    ),
                ),
                (
                    "warning_issues",
                    models.JSONField(
                        default=list, verbose_name="Warning Issues"
                    ),
                ),
                (
                    "check_results",
                    models.JSONField(
                        default=dict, verbose_name="Check Results"
                    ),
                ),
                (
                    "override_by",
                    models.CharField(
                        max_length=100,
                        blank=True,
                        default="",
                        verbose_name="Override By",
                        help_text="GitHub username who invoked /override-review",
                    ),
                ),
                (
                    "override_reason",
                    models.TextField(
                        blank=True, default="", verbose_name="Override Reason"
                    ),
                ),
                (
                    "override_at",
                    models.DateTimeField(
                        null=True, blank=True, verbose_name="Override At"
                    ),
                ),
                (
                    "started_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Started At"
                    ),
                ),
                (
                    "completed_at",
                    models.DateTimeField(
                        null=True, blank=True, verbose_name="Completed At"
                    ),
                ),
                (
                    "deleted_at",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        db_index=True,
                        verbose_name="Deleted At",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Created At"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True, verbose_name="Updated At"
                    ),
                ),
            ],
            options={
                "verbose_name": "Review Log",
                "verbose_name_plural": "Review Logs",
                "ordering": ["-started_at"],
            },
        ),
        migrations.AddIndex(
            model_name="reviewlog",
            index=models.Index(
                fields=["tenant_id", "status"],
                name="orchestrator_revlog_tenant_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="reviewlog",
            index=models.Index(
                fields=["repository", "pr_number"],
                name="orchestrator_revlog_repo_pr_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="reviewlog",
            index=models.Index(
                fields=["tenant_id", "-started_at"],
                name="orchestrator_revlog_tenant_started_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="reviewlog",
            constraint=models.UniqueConstraint(
                condition=models.Q(status__in=["pending", "running"]),
                fields=["tenant_id", "repository", "pr_number"],
                name="unique_active_review_per_pr",
            ),
        ),
    ]
