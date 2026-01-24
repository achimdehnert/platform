"""
Django DB Error Diagnostic Tool
Automatically detects and suggests fixes for common database errors
"""

import re

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Diagnose and auto-fix database errors"

    def add_arguments(self, parser):
        parser.add_argument(
            "--fix",
            action="store_true",
            help="Automatically fix detected issues",
        )
        parser.add_argument(
            "--app",
            type=str,
            default="writing_hub",
            help="App to check (default: writing_hub)",
        )

    def handle(self, *args, **options):
        auto_fix = options["fix"]
        app_label = options["app"]

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("🔍 DATABASE ERROR DIAGNOSTIC TOOL"))
        self.stdout.write("=" * 80 + "\n")

        # Get all existing tables
        existing_tables = self.get_existing_tables()
        self.stdout.write(f"Found {len(existing_tables)} tables in database\n")

        # Get all models for the app
        try:
            app_config = apps.get_app_config(app_label)
            models = app_config.get_models()
        except LookupError:
            self.stdout.write(self.style.ERROR(f"❌ App '{app_label}' not found"))
            return

        # Check each model
        issues = []
        for model in models:
            model_issues = self.check_model(model, existing_tables)
            if model_issues:
                issues.extend(model_issues)

        # Report findings
        if not issues:
            self.stdout.write(self.style.SUCCESS("\n✅ No database issues detected!"))
            return

        self.stdout.write(self.style.WARNING(f"\n⚠️  Found {len(issues)} issue(s):\n"))

        for i, issue in enumerate(issues, 1):
            self.stdout.write(f"\n{i}. {issue['type']}")
            self.stdout.write(f"   Model: {issue['model']}")
            self.stdout.write(f"   Field: {issue['field']}")
            self.stdout.write(f"   Issue: {issue['issue']}")

            if "suggestion" in issue:
                self.stdout.write(f"   💡 Suggestion: {issue['suggestion']}")

            if auto_fix and "fix_function" in issue:
                self.stdout.write(f"   🔧 Attempting auto-fix...")
                try:
                    issue["fix_function"]()
                    self.stdout.write(self.style.SUCCESS("   ✅ Fixed!"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"   ❌ Fix failed: {e}"))

        # Final recommendations
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("📋 RECOMMENDATIONS:")
        self.stdout.write("=" * 80)

        if any(i["type"] == "Missing Table" for i in issues):
            self.stdout.write("\n🔧 Run migrations:")
            self.stdout.write("   python manage.py migrate")

        if any(i["type"] == "Missing Related Table" for i in issues):
            self.stdout.write("\n🔧 Check table names in database:")
            self.stdout.write("   python manage.py dbshell")
            self.stdout.write("   .tables  (SQLite)")

        self.stdout.write("\n")

    def get_existing_tables(self):
        """Get all tables in the database"""
        with connection.cursor() as cursor:
            # SQLite
            if connection.vendor == "sqlite":
                cursor.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                """
                )
            # PostgreSQL
            elif connection.vendor == "postgresql":
                cursor.execute(
                    """
                    SELECT tablename FROM pg_tables
                    WHERE schemaname = 'public'
                    ORDER BY tablename
                """
                )
            # MySQL
            elif connection.vendor == "mysql":
                cursor.execute("SHOW TABLES")
            else:
                return []

            return [row[0] for row in cursor.fetchall()]

    def check_model(self, model, existing_tables):
        """Check a model for database issues"""
        issues = []
        model_name = model.__name__
        table_name = model._meta.db_table

        # Check if model's table exists
        if table_name not in existing_tables:
            issues.append(
                {
                    "type": "Missing Table",
                    "model": model_name,
                    "field": "-",
                    "issue": f"Table '{table_name}' does not exist",
                    "suggestion": f"Run: python manage.py migrate {model._meta.app_label}",
                }
            )

        # Check ForeignKey and M2M relationships
        for field in model._meta.get_fields():
            if hasattr(field, "related_model") and field.related_model:
                related_table = field.related_model._meta.db_table

                if related_table not in existing_tables:
                    # Try to find similar table names
                    similar = self.find_similar_tables(related_table, existing_tables)

                    issue = {
                        "type": "Missing Related Table",
                        "model": model_name,
                        "field": field.name,
                        "issue": f"Related table '{related_table}' does not exist",
                    }

                    if similar:
                        issue["suggestion"] = f"Did you mean: {', '.join(similar[:3])}?"
                        issue["possible_tables"] = similar
                    else:
                        issue["suggestion"] = f"Create table via migration or check FK reference"

                    issues.append(issue)

        return issues

    def find_similar_tables(self, target, existing_tables):
        """Find tables with similar names"""
        # Extract key parts from target
        parts = re.findall(r"[a-z]+", target.lower())

        similar = []
        for table in existing_tables:
            table_parts = re.findall(r"[a-z]+", table.lower())

            # Check if any part matches
            if any(part in table_parts for part in parts):
                similar.append(table)

        return similar

    def get_table_info(self, table_name):
        """Get detailed info about a table"""
        with connection.cursor() as cursor:
            if connection.vendor == "sqlite":
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                return [
                    {"name": col[1], "type": col[2], "nullable": not col[3], "pk": col[5]}
                    for col in columns
                ]
        return []
