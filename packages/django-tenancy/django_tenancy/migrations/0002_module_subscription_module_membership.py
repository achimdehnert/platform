"""Migration: ModuleSubscription and ModuleMembership tables."""

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("django_tenancy", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ModuleSubscription",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("tenant_id", models.UUIDField(db_index=True)),
                (
                    "module",
                    models.CharField(
                        db_index=True,
                        help_text="Module code, e.g. 'risk', 'dsb', 'worlds'.",
                        max_length=50,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("trial", "Trial"),
                            ("active", "Active"),
                            ("suspended", "Suspended"),
                        ],
                        default="trial",
                        max_length=20,
                    ),
                ),
                (
                    "plan_code",
                    models.CharField(default="free", max_length=50),
                ),
                (
                    "trial_ends_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "activated_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "expires_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="module_subscriptions",
                        to="django_tenancy.organization",
                    ),
                ),
            ],
            options={
                "verbose_name": "Module Subscription",
                "verbose_name_plural": "Module Subscriptions",
                "db_table": "tenancy_module_subscription",
            },
        ),
        migrations.AddConstraint(
            model_name="modulesubscription",
            constraint=models.UniqueConstraint(
                fields=("tenant_id", "module"),
                name="uq_module_subscription_tenant_module",
            ),
        ),
        migrations.AddConstraint(
            model_name="modulesubscription",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    status__in=["trial", "active", "suspended"],
                ),
                name="ck_module_subscription_status",
            ),
        ),
        migrations.AddIndex(
            model_name="modulesubscription",
            index=models.Index(
                fields=["tenant_id", "status"],
                name="idx_module_sub_tenant_status",
            ),
        ),
        migrations.CreateModel(
            name="ModuleMembership",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("tenant_id", models.UUIDField(db_index=True)),
                (
                    "module",
                    models.CharField(
                        db_index=True,
                        help_text="Module code, e.g. 'risk', 'dsb', 'worlds'.",
                        max_length=50,
                    ),
                ),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("admin", "Admin"),
                            ("manager", "Manager"),
                            ("member", "Member"),
                            ("viewer", "Viewer"),
                        ],
                        default="viewer",
                        max_length=20,
                    ),
                ),
                (
                    "granted_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "expires_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="module_memberships",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "granted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Module Membership",
                "verbose_name_plural": "Module Memberships",
                "db_table": "tenancy_module_membership",
            },
        ),
        migrations.AddConstraint(
            model_name="modulemembership",
            constraint=models.UniqueConstraint(
                fields=("tenant_id", "user", "module"),
                name="uq_module_membership_tenant_user_module",
            ),
        ),
        migrations.AddConstraint(
            model_name="modulemembership",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    role__in=["admin", "manager", "member", "viewer"],
                ),
                name="ck_module_membership_role",
            ),
        ),
        migrations.AddIndex(
            model_name="modulemembership",
            index=models.Index(
                fields=["tenant_id", "module"],
                name="idx_module_mem_tenant_module",
            ),
        ),
        migrations.AddIndex(
            model_name="modulemembership",
            index=models.Index(
                fields=["tenant_id", "user"],
                name="idx_module_mem_tenant_user",
            ),
        ),
    ]
