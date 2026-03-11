"""Setup PostgreSQL roles for RLS (ADR-137 Phase 2.3).

Creates a separate app-user role that is NOT the table owner,
so RLS policies apply to it. The migrations-user (table owner)
remains RLS-exempt without needing FORCE ROW LEVEL SECURITY.

Usage::

    python manage.py setup_rls_roles --dry-run
    python manage.py setup_rls_roles
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection

logger = logging.getLogger(__name__)

SETUP_SQL = """
-- 1. Create app role (if not exists)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM pg_roles WHERE rolname = '{app_user}'
    ) THEN
        CREATE ROLE {app_user} LOGIN PASSWORD '{app_password}';
    END IF;
END
$$;

-- 2. Grant connect + usage
GRANT CONNECT ON DATABASE {db_name} TO {app_user};
GRANT USAGE ON SCHEMA public TO {app_user};

-- 3. Grant DML on all existing tables
GRANT SELECT, INSERT, UPDATE, DELETE
    ON ALL TABLES IN SCHEMA public TO {app_user};

-- 4. Grant usage on sequences
GRANT USAGE, SELECT
    ON ALL SEQUENCES IN SCHEMA public TO {app_user};

-- 5. Default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE
    ON TABLES TO {app_user};

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT
    ON SEQUENCES TO {app_user};
"""


class Command(BaseCommand):
    help = "Setup PostgreSQL roles for RLS (ADR-137)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show SQL without executing.",
        )
        parser.add_argument(
            "--app-user",
            type=str,
            default=None,
            help="App-user role name (default: <db_name>_app).",
        )
        parser.add_argument(
            "--app-password",
            type=str,
            default=None,
            help="Password for app-user role.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if connection.vendor != "postgresql":
            self.stderr.write(
                self.style.ERROR(
                    "RLS roles require PostgreSQL. "
                    f"Current: {connection.vendor}"
                )
            )
            return

        db_settings = settings.DATABASES["default"]
        db_name = db_settings["NAME"]
        migrations_user = db_settings["USER"]

        app_user = options["app_user"] or f"{db_name}_app"
        app_password = options["app_password"] or f"{app_user}_rls"

        sql = SETUP_SQL.format(
            app_user=app_user,
            app_password=app_password,
            db_name=db_name,
        )

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"RLS Role Setup"
                f"{' (DRY RUN)' if dry_run else ''}"
            )
        )
        self.stdout.write(
            f"  Database:        {db_name}\n"
            f"  Migrations-user: {migrations_user} "
            f"(table owner, RLS-exempt)\n"
            f"  App-user:        {app_user} "
            f"(RLS applies)\n"
        )

        if dry_run:
            self.stdout.write(self.style.SQL_KEYWORD(sql))
            self.stdout.write(
                self.style.WARNING(
                    "\nAfter running this command:\n"
                    f"  1. Update DATABASE_URL to use "
                    f"'{app_user}' for gunicorn/celery\n"
                    f"  2. Keep '{migrations_user}' for "
                    f"migrate/createsuperuser\n"
                    f"  3. Run: python manage.py enable_rls"
                )
            )
        else:
            self._execute_sql(sql)
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nRole '{app_user}' created/updated."
                )
            )

    def _execute_sql(self, sql):
        """Execute SQL statements."""
        stmts = [
            s.strip()
            for s in sql.split(";")
            if s.strip() and not s.strip().startswith("--")
        ]
        with connection.cursor() as cursor:
            for stmt in stmts:
                try:
                    cursor.execute(stmt)
                except Exception as exc:
                    self.stderr.write(
                        self.style.ERROR(f"  ERROR: {exc}")
                    )
                    logger.exception("RLS role setup failed")
