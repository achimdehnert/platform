"""Initial migration: Organization and Membership tables."""

import uuid

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
            name="Organization",
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
                (
                    "tenant_id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        unique=True,
                    ),
                ),
                ("slug", models.SlugField(max_length=63, unique=True)),
                ("name", models.CharField(max_length=200)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("trial", "Trial"),
                            ("active", "Active"),
                            ("suspended", "Suspended"),
                            ("deleted", "Deleted"),
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
                    "suspended_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "suspended_reason",
                    models.TextField(blank=True, default=""),
                ),
                (
                    "deleted_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "settings",
                    models.JSONField(blank=True, default=dict),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "tenancy_organization",
            },
        ),
        migrations.AddConstraint(
            model_name="organization",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    status__in=[
                        "trial", "active", "suspended", "deleted",
                    ]
                ),
                name="org_status_chk",
            ),
        ),
        migrations.AddIndex(
            model_name="organization",
            index=models.Index(
                fields=["status"], name="idx_org_status",
            ),
        ),
        migrations.CreateModel(
            name="Membership",
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
                (
                    "tenant_id",
                    models.UUIDField(db_index=True),
                ),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("owner", "Owner"),
                            ("admin", "Admin"),
                            ("member", "Member"),
                            ("viewer", "Viewer"),
                            ("external", "External"),
                        ],
                        default="member",
                        max_length=20,
                    ),
                ),
                (
                    "invited_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "accepted_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="memberships",
                        to="django_tenancy.organization",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="memberships",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "invited_by",
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
                "db_table": "tenancy_membership",
            },
        ),
        migrations.AddConstraint(
            model_name="membership",
            constraint=models.UniqueConstraint(
                fields=("tenant_id", "user"),
                name="membership_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="membership",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    role__in=[
                        "owner", "admin", "member",
                        "viewer", "external",
                    ]
                ),
                name="membership_role_chk",
            ),
        ),
        migrations.AddIndex(
            model_name="membership",
            index=models.Index(
                fields=["tenant_id", "role"],
                name="idx_membership_tenant_role",
            ),
        ),
    ]
