"""
src/dms_archive/migrations/0001_initial.py
SeparateDatabaseAndState-Pattern (Plattform-Standard ADR-050)
"""
from __future__ import annotations

import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True
    dependencies = []

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="DmsArchiveRecord",
                    fields=[
                        ("id",               models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                        ("tenant_id",        models.UUIDField(db_index=True)),
                        ("source_type",      models.CharField(max_length=30)),
                        ("source_id",        models.UUIDField(db_index=True)),
                        ("source_label",     models.CharField(max_length=500)),
                        ("dms_document_id",  models.CharField(max_length=255, blank=True, db_index=True)),
                        ("dms_repository_id",models.CharField(max_length=255, blank=True)),
                        ("dms_category",     models.CharField(max_length=100, blank=True)),
                        ("status",           models.CharField(max_length=10, default="PENDING", db_index=True)),
                        ("retry_count",      models.PositiveSmallIntegerField(default=0)),
                        ("error_message",    models.TextField(blank=True)),
                        ("archived_by_id",   models.UUIDField(null=True, blank=True)),
                        ("celery_task_id",   models.CharField(max_length=255, blank=True)),
                        ("created_at",       models.DateTimeField(auto_now_add=True, db_index=True)),
                        ("updated_at",       models.DateTimeField(auto_now=True)),
                    ],
                    options={
                        "db_table": "dms_archive_record",
                        "ordering": ["-created_at"],
                    },
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    CREATE TABLE IF NOT EXISTS dms_archive_record (
                        id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
                        tenant_id        UUID        NOT NULL,
                        source_type      VARCHAR(30) NOT NULL,
                        source_id        UUID        NOT NULL,
                        source_label     VARCHAR(500) NOT NULL,
                        dms_document_id  VARCHAR(255) NOT NULL DEFAULT '',
                        dms_repository_id VARCHAR(255) NOT NULL DEFAULT '',
                        dms_category     VARCHAR(100) NOT NULL DEFAULT '',
                        status           VARCHAR(10) NOT NULL DEFAULT 'PENDING',
                        retry_count      SMALLINT    NOT NULL DEFAULT 0,
                        error_message    TEXT        NOT NULL DEFAULT '',
                        archived_by_id   UUID,
                        celery_task_id   VARCHAR(255) NOT NULL DEFAULT '',
                        created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
                        updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
                    );

                    CREATE INDEX IF NOT EXISTS idx_dmsarchive_tenant
                        ON dms_archive_record(tenant_id);
                    CREATE INDEX IF NOT EXISTS idx_dmsarchive_source
                        ON dms_archive_record(tenant_id, source_id);
                    CREATE INDEX IF NOT EXISTS idx_dmsarchive_status
                        ON dms_archive_record(tenant_id, source_type, status);
                    CREATE INDEX IF NOT EXISTS idx_dmsarchive_dms_doc
                        ON dms_archive_record(dms_document_id)
                        WHERE dms_document_id != '';

                    -- Genau ein SUCCESS pro Quell-Objekt
                    CREATE UNIQUE INDEX IF NOT EXISTS uq_dmsarchive_one_success
                        ON dms_archive_record(tenant_id, source_id)
                        WHERE status = 'SUCCESS';
                    """,
                    reverse_sql="DROP TABLE IF EXISTS dms_archive_record;",
                ),
            ],
        ),
    ]
