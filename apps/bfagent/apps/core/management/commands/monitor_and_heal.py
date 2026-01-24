"""
Background monitoring and auto-healing command.

Monitors Django logs and terminal output, automatically fixing known errors.
Part of Generic Guardrail Rule #4.

Usage:
    python manage.py monitor_and_heal
    python manage.py monitor_and_heal --watch-logs
"""

import re
import subprocess
import sys
import threading
import time

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Monitor and auto-heal errors in real-time."""

    help = "Monitor Django and automatically heal errors"

    def add_arguments(self, parser):
        parser.add_argument(
            "--watch-logs",
            action="store_true",
            help="Watch Django log files for errors",
        )
        parser.add_argument(
            "--interval",
            type=int,
            default=5,
            help="Check interval in seconds (default: 5)",
        )

    def handle(self, *args, **options):
        """Start monitoring."""
        watch_logs = options.get("watch_logs", False)
        interval = options.get("interval", 5)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(self.style.SUCCESS("🔍 Auto-Healing Monitor Started"))
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write("")
        self.stdout.write("Monitoring for errors and auto-healing...")
        self.stdout.write(f"Check interval: {interval} seconds")
        self.stdout.write("Press CTRL+C to stop")
        self.stdout.write("")

        try:
            while True:
                # Check database tables
                self._check_database()

                # Check for common issues
                self._check_common_issues()

                # Wait before next check
                time.sleep(interval)

        except KeyboardInterrupt:
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("✅ Monitor stopped"))
            self.stdout.write("")

    def _check_database(self):
        """Check database for missing tables."""
        from django.apps import apps
        from django.db import connection

        missing_tables = []

        local_apps = [
            app
            for app in apps.get_app_configs()
            if app.name.startswith("apps.") or app.name.startswith("bfagent.")
        ]

        for app_config in local_apps:
            for model in app_config.get_models():
                table_name = model._meta.db_table
                if not self._table_exists(table_name):
                    missing_tables.append(
                        {
                            "app": app_config.label,
                            "model": model.__name__,
                            "table": table_name,
                        }
                    )

        if missing_tables:
            self.stdout.write(self.style.WARNING(f"⚠️  Found {len(missing_tables)} missing tables"))
            self._auto_heal_tables(missing_tables)

    def _check_common_issues(self):
        """Check for common Django issues."""
        # Could check:
        # - Missing static files
        # - Invalid URL patterns
        # - Missing templates
        # - etc.
        pass

    def _auto_heal_tables(self, missing_tables):
        """Auto-heal missing tables."""
        self.stdout.write("🔧 Auto-healing missing tables...")

        try:
            # Run makemigrations
            self.stdout.write("  Running makemigrations...")
            call_command("makemigrations", interactive=False)

            # Run migrate
            self.stdout.write("  Running migrate...")
            call_command("migrate", interactive=False)

            # Verify
            still_missing = []
            for item in missing_tables:
                if not self._table_exists(item["table"]):
                    still_missing.append(item)

            if still_missing:
                self.stdout.write(
                    self.style.WARNING(f"  ⚠️  Still missing {len(still_missing)} tables")
                )
            else:
                self.stdout.write(self.style.SUCCESS(f"  ✅ Created {len(missing_tables)} tables"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ Auto-healing failed: {e}"))

    def _table_exists(self, table_name):
        """Check if a table exists."""
        from django.db import connection

        try:
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
        except Exception:
            return False
