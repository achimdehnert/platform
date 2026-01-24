"""
Management command to reset workflow tables
Drops all workflow tables and migration record
"""

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Reset workflow tables (drop and prepare for fresh migration)"

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("\n⚠️  Resetting Workflow Tables...\n"))

        with connection.cursor() as cursor:
            # CRITICAL: First disable foreign key constraints for SQLite
            cursor.execute("PRAGMA foreign_keys = OFF")
            self.stdout.write("   ⚙️  Disabled foreign key constraints")

            # Drop tables in correct order (foreign keys first)
            tables = [
                "project_phase_history",
                "phase_action_configs",
                "workflow_phase_steps",
                "structured_workflow_tasks",  # Also references workflow_phases
                "workflow_templates",
                "workflow_phases",
            ]

            for table in tables:
                try:
                    cursor.execute(f"DROP TABLE IF EXISTS {table}")
                    self.stdout.write(f"   🗑️  Dropped table: {table}")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"   ❌ Error dropping {table}: {e}"))

            # Re-enable foreign key constraints
            cursor.execute("PRAGMA foreign_keys = ON")
            self.stdout.write("   ⚙️  Re-enabled foreign key constraints")

            # Remove migration record
            try:
                cursor.execute(
                    "DELETE FROM django_migrations WHERE name = '0015_add_workflow_engine_system'"
                )
                self.stdout.write("   🗑️  Removed migration record")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"   ❌ Error removing migration: {e}"))

            # Also remove BookProjects workflow fields (will be re-added)
            try:
                cursor.execute("PRAGMA table_info(book_projects)")
                columns = [row[1] for row in cursor.fetchall()]

                if "workflow_template_id" in columns:
                    # SQLite doesn't support DROP COLUMN, so we note it
                    self.stdout.write(
                        self.style.WARNING(
                            "   ⚠️  Note: BookProjects workflow fields exist (will be handled by migration)"
                        )
                    )
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"   ⚠️  Could not check BookProjects: {e}"))

        self.stdout.write(
            self.style.SUCCESS(
                "\n✅ Workflow tables reset complete!\n\nNext steps:\n"
                "1. python manage.py migrate bfagent\n"
                "2. python manage.py setup_workflow_system\n"
            )
        )
