"""
Initial migration for bfagent_llm.django_app (ADR-089).

Creates tables:
- bfllm_providers
- bfllm_models
- bfllm_action_types (with tenant_id)
- bfllm_usage_logs (with tenant_id)
"""

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="LLMProvider",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        max_length=50,
                        unique=True,
                        validators=[
                            django.core.validators.RegexValidator(
                                "^[a-z][a-z0-9_-]*$",
                                "Name muss lowercase sein (a-z, 0-9, -, _).",
                            )
                        ],
                    ),
                ),
                ("display_name", models.CharField(max_length=100)),
                ("api_key_env_var", models.CharField(default="", max_length=100)),
                ("base_url", models.URLField(blank=True, default="")),
                ("is_active", models.BooleanField(db_index=True, default=True)),
            ],
            options={
                "db_table": "bfllm_providers",
                "verbose_name": "LLM Provider",
                "verbose_name_plural": "LLM Providers",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="LLMModel",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100)),
                ("display_name", models.CharField(max_length=150)),
                ("max_tokens", models.IntegerField(default=4096)),
                ("context_window", models.IntegerField(default=128000)),
                ("supports_vision", models.BooleanField(default=False)),
                ("supports_tools", models.BooleanField(default=True)),
                (
                    "input_cost_per_million",
                    models.DecimalField(
                        decimal_places=4, default=0, max_digits=10
                    ),
                ),
                (
                    "output_cost_per_million",
                    models.DecimalField(
                        decimal_places=4, default=0, max_digits=10
                    ),
                ),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("is_default", models.BooleanField(default=False)),
                (
                    "provider",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="models",
                        to="django_app.llmprovider",
                    ),
                ),
            ],
            options={
                "db_table": "bfllm_models",
                "verbose_name": "LLM Model",
                "verbose_name_plural": "LLM Models",
                "ordering": ["provider__name", "name"],
                "unique_together": {("provider", "name")},
            },
        ),
        migrations.CreateModel(
            name="AIActionType",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("tenant_id", models.UUIDField(db_index=True)),
                (
                    "code",
                    models.CharField(
                        max_length=50,
                        validators=[
                            django.core.validators.RegexValidator(
                                "^[a-z][a-z0-9_]{2,49}$",
                                "Code muss snake_case sein (3-50 Zeichen, a-z/0-9/_).",
                            )
                        ],
                    ),
                ),
                ("name", models.CharField(max_length=100)),
                ("description", models.TextField(blank=True, default="")),
                ("max_tokens", models.IntegerField(default=2000)),
                ("temperature", models.FloatField(default=0.7)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                (
                    "default_model",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="default_for_actions",
                        to="django_app.llmmodel",
                    ),
                ),
                (
                    "fallback_model",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="fallback_for_actions",
                        to="django_app.llmmodel",
                    ),
                ),
            ],
            options={
                "db_table": "bfllm_action_types",
                "verbose_name": "AI Action Type",
                "verbose_name_plural": "AI Action Types",
                "unique_together": {("tenant_id", "code")},
            },
        ),
        migrations.AddIndex(
            model_name="aiactiontype",
            index=models.Index(
                fields=["tenant_id", "code", "is_active"],
                name="bfllm_action_tenant_code_idx",
            ),
        ),
        migrations.CreateModel(
            name="AIUsageLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("tenant_id", models.UUIDField(db_index=True)),
                ("input_tokens", models.IntegerField(default=0)),
                ("output_tokens", models.IntegerField(default=0)),
                ("total_tokens", models.IntegerField(default=0)),
                (
                    "estimated_cost",
                    models.DecimalField(
                        decimal_places=6, default=0, max_digits=10
                    ),
                ),
                ("latency_ms", models.IntegerField(default=0)),
                ("success", models.BooleanField(default=True)),
                ("error_message", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "action_type",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="django_app.aiactiontype",
                    ),
                ),
                (
                    "model_used",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="django_app.llmmodel",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "bfllm_usage_logs",
                "verbose_name": "AI Usage Log",
                "verbose_name_plural": "AI Usage Logs",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="aiusagelog",
            index=models.Index(
                fields=["tenant_id", "-created_at"],
                name="bfllm_usage_tenant_date_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="aiusagelog",
            index=models.Index(
                fields=["action_type", "-created_at"],
                name="bfllm_usage_action_date_idx",
            ),
        ),
    ]
