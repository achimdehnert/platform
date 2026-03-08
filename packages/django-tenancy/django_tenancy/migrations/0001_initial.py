"""
django_tenancy/migrations/0001_initial.py

Initial migration: Organization model.
"""
from __future__ import annotations

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Organization",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="Public ID")),
                ("name", models.CharField(max_length=200, verbose_name="Name")),
                ("slug", models.SlugField(max_length=100, unique=True, verbose_name="Slug")),
                ("subdomain", models.CharField(blank=True, max_length=100, verbose_name="Subdomain override")),
                ("language", models.CharField(default="de", max_length=8, verbose_name="Language")),
                ("is_active", models.BooleanField(default=True, verbose_name="Active")),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True, verbose_name="Deleted At")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created At")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Updated At")),
            ],
            options={
                "verbose_name": "Organization",
                "verbose_name_plural": "Organizations",
                "ordering": ["name"],
            },
        ),
        migrations.AddConstraint(
            model_name="organization",
            constraint=models.UniqueConstraint(
                condition=models.Q(deleted_at__isnull=True),
                fields=["slug"],
                name="unique_active_org_slug",
            ),
        ),
    ]
