"""
hub_template/apps/core/migrations/0002_add_tenant_id.py

Idempotente Migration für tenant_id Rollout auf bestehenden Modellen.

Fixes B-3 (ADR-109):
  - SeparateDatabaseAndState für bestehende Prod-DB-Zeilen
  - RunPython mit reverse_func für vollständigen Rollback
  - Default-Tenant-Zuweisung für bestehende Rows

Verwendung:
  1. Dieses File als Template in das jeweilige Hub-Repo kopieren
  2. `MyModel` durch den tatsächlichen Model-Namen ersetzen
  3. DEFAULT_TENANT_ID auf die ID des Default-Tenants setzen
  4. python manage.py migrate core 0002

Rollback:
  python manage.py migrate core 0001
"""

from __future__ import annotations

import django.db.models.deletion
from django.db import migrations, models

# Tenant-ID für bestehende Rows (muss existieren vor Migration)
# Wird über Management Command oder Admin angelegt:
# python manage.py create_default_tenant --name="Default" --slug="default"
DEFAULT_TENANT_ID = 1


def assign_default_tenant(apps, schema_editor):
    """
    Assign DEFAULT_TENANT_ID to all existing rows that have NULL tenant_id.
    Idempotent: safe to run multiple times.
    """
    MyModel = apps.get_model("core", "MyModel")
    updated = MyModel.objects.filter(tenant_id__isnull=True).update(
        tenant_id=DEFAULT_TENANT_ID
    )
    if updated:
        print(f"  Assigned tenant_id={DEFAULT_TENANT_ID} to {updated} existing MyModel rows")


def remove_tenant_assignment(apps, schema_editor):
    """Reverse: set tenant_id back to NULL (reversible migration)."""
    MyModel = apps.get_model("core", "MyModel")
    MyModel.objects.filter(tenant_id=DEFAULT_TENANT_ID).update(tenant_id=None)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        # Step 1: Add column as NULLABLE first (avoids NOT NULL constraint on existing rows)
        migrations.AddField(
            model_name="mymodel",
            name="tenant_id",
            field=models.BigIntegerField(
                null=True,          # Temporarily nullable
                blank=True,
                db_index=True,
                verbose_name="Tenant ID",
            ),
        ),

        # Step 2: Populate existing rows with DEFAULT_TENANT_ID
        migrations.RunPython(
            assign_default_tenant,
            reverse_code=remove_tenant_assignment,
        ),

        # Step 3: Make NOT NULL now that all rows have a value
        # SeparateDatabaseAndState: Django state sees NOT NULL, DB gets the ALTER
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql='ALTER TABLE "core_mymodel" ALTER COLUMN "tenant_id" SET NOT NULL',
                    reverse_sql='ALTER TABLE "core_mymodel" ALTER COLUMN "tenant_id" DROP NOT NULL',
                ),
            ],
            state_operations=[
                migrations.AlterField(
                    model_name="mymodel",
                    name="tenant_id",
                    field=models.BigIntegerField(
                        db_index=True,
                        verbose_name="Tenant ID",
                        # NOT NULL in state
                    ),
                ),
            ],
        ),
    ]
