"""Enable PostgreSQL Row-Level Security (ADR-137 Phase 2).

Introspects all installed models that have a ``tenant_id`` field and generates
(or executes) RLS policies for each table.

Cast-type detection:
- UUIDField → ``::uuid``
- BigIntegerField / IntegerField → ``::bigint``

Usage::

    python manage.py enable_rls --dry-run          # show SQL
    python manage.py enable_rls                     # execute
    python manage.py enable_rls --table=risk_assessment  # single table
    python manage.py enable_rls --disable           # remove RLS
"""

from __future__ import annotations

import logging

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection

logger = logging.getLogger(__name__)

CAST_MAP = {
    "UUIDField": "uuid",
    "BigIntegerField": "bigint",
    "IntegerField": "bigint",
    "BigAutoField": "bigint",
    "AutoField": "bigint",
}

RLS_POLICY_TEMPLATE = """
-- Enable RLS on {table}
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;

-- Policy: rows visible when app.tenant_id matches or is not set
CREATE POLICY tenant_isolation_{safe_name} ON {table}
    FOR ALL
    USING (
        tenant_id = NULLIF(
            current_setting('app.tenant_id', true), ''
        )::{cast_type}
        OR current_setting('app.tenant_id', true) IS NULL
        OR current_setting('app.tenant_id', true) = ''
    );
"""

DISABLE_TEMPLATE = """
-- Disable RLS on {table}
DROP POLICY IF EXISTS tenant_isolation_{safe_name} ON {table};
ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;
"""


def _get_tenant_models():
    """Yield (model, db_table, cast_type) for models with tenant_id."""
    for model in apps.get_models():
        try:
            field = model._meta.get_field("tenant_id")
        except Exception:
            continue

        field_type = type(field).__name__
        cast_type = CAST_MAP.get(field_type)
        if cast_type is None:
            logger.warning(
                "Skip %s.%s: unknown tenant_id type %s",
                model._meta.app_label,
                model.__name__,
                field_type,
            )
            continue

        yield model, model._meta.db_table, cast_type


def _safe_name(table: str) -> str:
    """Convert table name to a safe policy identifier."""
    return table.replace(".", "_").replace("-", "_")


class Command(BaseCommand):
    help = (
        "Enable/disable PostgreSQL RLS on tenant tables"
        " (ADR-137)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show SQL without executing.",
        )
        parser.add_argument(
            "--table",
            type=str,
            default=None,
            help="Only apply to a specific table.",
        )
        parser.add_argument(
            "--disable",
            action="store_true",
            help="Remove RLS policies instead of creating them.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        target_table = options["table"]
        disable = options["disable"]

        if connection.vendor != "postgresql":
            self.stderr.write(
                self.style.ERROR(
                    "RLS requires PostgreSQL. "
                    f"Current backend: {connection.vendor}"
                )
            )
            return

        tables = list(_get_tenant_models())
        if not tables:
            self.stdout.write(
                self.style.WARNING("No models with tenant_id found.")
            )
            return

        if target_table:
            tables = [
                (m, t, c) for m, t, c in tables if t == target_table
            ]
            if not tables:
                self.stderr.write(
                    self.style.ERROR(
                        f"Table '{target_table}' not found "
                        "among tenant models."
                    )
                )
                return

        template = DISABLE_TEMPLATE if disable else RLS_POLICY_TEMPLATE
        action = "Disable" if disable else "Enable"

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"{action} RLS for {len(tables)} table(s)"
                f"{' (DRY RUN)' if dry_run else ''}"
            )
        )

        for model, table, cast_type in tables:
            safe = _safe_name(table)
            sql = template.format(
                table=table,
                safe_name=safe,
                cast_type=cast_type,
            )

            label = (
                f"{model._meta.app_label}.{model.__name__}"
            )
            self.stdout.write(
                f"  {label} ({table}) "
                f"→ cast ::{cast_type}"
            )

            if dry_run:
                self.stdout.write(
                    self.style.SQL_KEYWORD(sql)
                )
            else:
                self._execute_sql(sql, table, action)

        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n{action}d RLS on {len(tables)} table(s)."
                )
            )

    def _execute_sql(self, sql, table, action):
        """Execute SQL statements one by one."""
        statements = [
            s.strip()
            for s in sql.split(";")
            if s.strip() and not s.strip().startswith("--")
        ]
        with connection.cursor() as cursor:
            for stmt in statements:
                try:
                    cursor.execute(stmt)
                except Exception as exc:
                    self.stderr.write(
                        self.style.ERROR(
                            f"  ERROR on {table}: {exc}"
                        )
                    )
                    logger.exception(
                        "RLS %s failed for %s", action, table
                    )
