"""
Auto-migration check command.

Guardrail Rule #4: Proactive table detection and migration.
Automatically detects missing tables and runs migrations.
"""

import sys

from django.apps import apps
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import ProgrammingError, connection


class Command(BaseCommand):
    """Check for missing tables and auto-migrate if needed."""

    help = "Proactively check for missing tables and run migrations"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only check, do not auto-migrate",
        )
        parser.add_argument(
            "--app",
            type=str,
            help="Check specific app only",
        )

    def handle(self, *args, **options):
        """Check and migrate."""
        dry_run = options.get("dry_run", False)
        app_label = options.get("app")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(self.style.SUCCESS("🔍 Guardrail Rule #4: Auto-Migration Check"))
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write("")

        # Get apps to check
        if app_label:
            try:
                app_config = apps.get_app_config(app_label)
                apps_to_check = [app_config]
            except LookupError:
                self.stdout.write(self.style.ERROR(f'❌ App "{app_label}" not found'))
                return
        else:
            # Check all local apps (not Django built-ins)
            apps_to_check = [
                app
                for app in apps.get_app_configs()
                if app.name.startswith("apps.") or app.name.startswith("bfagent.")
            ]

        missing_tables = []
        total_models = 0

        # Check each app
        for app_config in apps_to_check:
            app_models = app_config.get_models()
            if not app_models:
                continue

            self.stdout.write(f"Checking app: {app_config.label}")

            for model in app_models:
                total_models += 1
                table_name = model._meta.db_table

                # Check if table exists
                if not self._table_exists(table_name):
                    missing_tables.append(
                        {
                            "app": app_config.label,
                            "model": model.__name__,
                            "table": table_name,
                        }
                    )
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ⚠️  Missing table: {table_name} (model: {model.__name__})"
                        )
                    )

        # Summary
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("📊 Summary:"))
        self.stdout.write(f"  Total models checked: {total_models}")
        self.stdout.write(f"  Missing tables: {len(missing_tables)}")
        self.stdout.write("")

        if not missing_tables:
            self.stdout.write(self.style.SUCCESS("✅ All tables exist - no action needed"))
            return

        # Show missing tables grouped by app
        apps_with_missing = {}
        for item in missing_tables:
            app = item["app"]
            if app not in apps_with_missing:
                apps_with_missing[app] = []
            apps_with_missing[app].append(item)

        self.stdout.write(self.style.WARNING("🔴 Missing tables by app:"))
        for app, items in apps_with_missing.items():
            self.stdout.write(f"  • {app}: {len(items)} tables")
            for item in items:
                self.stdout.write(f'    - {item["table"]} ({item["model"]})')
        self.stdout.write("")

        # Auto-migrate if not dry-run
        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 Dry-run mode - skipping auto-migration"))
            self.stdout.write("")
            self.stdout.write("To fix, run:")
            self.stdout.write("  python manage.py makemigrations")
            self.stdout.write("  python manage.py migrate")
            return

        # Run makemigrations
        self.stdout.write(self.style.SUCCESS("🔧 Auto-fixing: Running makemigrations..."))
        self.stdout.write("")

        try:
            call_command("makemigrations", interactive=False)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ makemigrations failed: {e}"))
            return

        # Run migrate
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("🔧 Auto-fixing: Running migrate..."))
        self.stdout.write("")

        try:
            call_command("migrate", interactive=False)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ migrate failed: {e}"))
            return

        # Verify fix
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("✅ Migrations complete - verifying..."))
        still_missing = []

        for item in missing_tables:
            if not self._table_exists(item["table"]):
                still_missing.append(item)

        if still_missing:
            self.stdout.write(self.style.WARNING(f"⚠️  Still missing {len(still_missing)} tables"))
            for item in still_missing:
                self.stdout.write(f'  - {item["table"]}')
        else:
            self.stdout.write(self.style.SUCCESS("✅ All tables created successfully!"))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(self.style.SUCCESS("✅ Auto-Migration Check Complete"))
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write("")

    def _table_exists(self, table_name):
        """Check if a table exists in the database."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = %s
                )
            """,
                [table_name],
            )
            return cursor.fetchone()[0]
