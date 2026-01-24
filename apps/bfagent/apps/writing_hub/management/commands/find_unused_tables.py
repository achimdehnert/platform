"""
Find Unused Database Tables
Analyzes which tables exist but are not used by any models, views, or handlers
"""

import os
import re
from pathlib import Path

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Find database tables that are not used by any code"

    def add_arguments(self, parser):
        parser.add_argument(
            "--include-django",
            action="store_true",
            help="Include Django internal tables",
        )
        parser.add_argument(
            "--show-references",
            action="store_true",
            help="Show where tables are referenced",
        )

    def handle(self, *args, **options):
        include_django = options["include_django"]
        show_references = options["show_references"]

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("🔍 UNUSED TABLES ANALYZER"))
        self.stdout.write("=" * 80 + "\n")

        # Step 1: Get all tables
        self.stdout.write("📊 Step 1: Collecting database tables...")
        all_tables = self.get_all_tables()
        self.stdout.write(f"   Found {len(all_tables)} tables\n")

        # Step 2: Get tables used by models
        self.stdout.write("📝 Step 2: Scanning Django models...")
        model_tables = self.get_model_tables()
        self.stdout.write(f"   Found {len(model_tables)} model tables\n")

        # Step 3: Search code for direct SQL references
        self.stdout.write("🔎 Step 3: Scanning code for SQL references...")
        code_references = self.scan_code_for_table_references()
        self.stdout.write(f"   Found {len(code_references)} code references\n")

        # Step 4: Categorize tables
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("📋 ANALYSIS RESULTS")
        self.stdout.write("=" * 80 + "\n")

        # Filter out Django tables if requested
        if not include_django:
            django_tables = {
                "auth_group",
                "auth_group_permissions",
                "auth_permission",
                "auth_user",
                "auth_user_groups",
                "auth_user_user_permissions",
                "django_admin_log",
                "django_content_type",
                "django_migrations",
                "django_session",
            }
            all_tables = [t for t in all_tables if t not in django_tables]

        # Categorize
        used_tables = set(model_tables.keys()) | set(code_references.keys())
        unused_tables = [t for t in all_tables if t not in used_tables]

        # Report
        self.report_used_tables(model_tables, code_references, show_references)
        self.report_unused_tables(unused_tables)
        self.report_statistics(all_tables, used_tables, unused_tables)

    def get_all_tables(self):
        """Get all tables in database"""
        with connection.cursor() as cursor:
            if connection.vendor == "sqlite":
                cursor.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type IN ('table', 'view')
                    AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                """
                )
            elif connection.vendor == "postgresql":
                cursor.execute(
                    """
                    SELECT tablename FROM pg_tables
                    WHERE schemaname = 'public'
                    UNION
                    SELECT viewname FROM pg_views
                    WHERE schemaname = 'public'
                    ORDER BY tablename
                """
                )
            else:
                cursor.execute("SHOW TABLES")

            return [row[0] for row in cursor.fetchall()]

    def get_model_tables(self):
        """Get all tables defined in Django models"""
        tables = {}

        for model in apps.get_models():
            table_name = model._meta.db_table
            app_label = model._meta.app_label
            model_name = model.__name__

            if table_name not in tables:
                tables[table_name] = []

            tables[table_name].append(
                {
                    "app": app_label,
                    "model": model_name,
                    "managed": model._meta.managed,
                }
            )

        return tables

    def scan_code_for_table_references(self):
        """Scan Python code for direct table references"""
        references = {}

        # Get project root
        base_dir = Path(os.getcwd())

        # Patterns to search for
        patterns = [
            r'FROM\s+["`]?(\w+)["`]?',  # SQL FROM
            r'JOIN\s+["`]?(\w+)["`]?',  # SQL JOIN
            r'INSERT\s+INTO\s+["`]?(\w+)["`]?',  # SQL INSERT
            r'UPDATE\s+["`]?(\w+)["`]?',  # SQL UPDATE
            r'db_table\s*=\s*["\'](\w+)["\']',  # Meta db_table
        ]

        # Search in Python files
        python_files = list(base_dir.glob("apps/**/*.py"))

        for py_file in python_files:
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")

                for pattern in patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        table_name = match.group(1)

                        if table_name not in references:
                            references[table_name] = []

                        references[table_name].append(
                            {
                                "file": str(py_file.relative_to(base_dir)),
                                "type": "sql" if "FROM" in pattern or "JOIN" in pattern else "meta",
                            }
                        )
            except Exception:
                pass  # Skip files that can't be read

        return references

    def report_used_tables(self, model_tables, code_references, show_references):
        """Report tables that are in use"""
        self.stdout.write("\n✅ USED TABLES:")
        self.stdout.write("-" * 80)

        all_used = set(model_tables.keys()) | set(code_references.keys())

        for table in sorted(all_used):
            models = model_tables.get(table, [])
            refs = code_references.get(table, [])

            if models:
                model_info = models[0]
                status = "📦 Model" if model_info["managed"] else "🔗 Unmanaged"
                self.stdout.write(f"\n{status} {table}")

                if show_references:
                    for m in models:
                        self.stdout.write(f"   → {m['app']}.{m['model']}")

            if refs and show_references:
                self.stdout.write(f"   Code references: {len(refs)} file(s)")
                for ref in refs[:3]:  # Show first 3
                    self.stdout.write(f"      - {ref['file']}")

    def report_unused_tables(self, unused_tables):
        """Report tables that appear unused"""
        if not unused_tables:
            self.stdout.write("\n" + self.style.SUCCESS("\n✅ No unused tables found!"))
            return

        self.stdout.write(
            "\n" + self.style.WARNING(f"\n⚠️  POTENTIALLY UNUSED TABLES ({len(unused_tables)}):")
        )
        self.stdout.write("-" * 80)

        # Categorize by prefix
        categorized = {}
        for table in unused_tables:
            prefix = table.split("_")[0] if "_" in table else "other"
            if prefix not in categorized:
                categorized[prefix] = []
            categorized[prefix].append(table)

        for prefix, tables in sorted(categorized.items()):
            self.stdout.write(f"\n📁 {prefix.upper()}:")
            for table in sorted(tables):
                # Check if it's a view
                is_view = self.is_view(table)
                table_type = "VIEW" if is_view else "TABLE"

                # Get row count
                row_count = self.get_row_count(table)

                self.stdout.write(f"   • {table:40s} [{table_type:5s}] {row_count:>8d} rows")

    def report_statistics(self, all_tables, used_tables, unused_tables):
        """Report summary statistics"""
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("📊 STATISTICS")
        self.stdout.write("=" * 80)

        total = len(all_tables)
        used = len(used_tables)
        unused = len(unused_tables)

        self.stdout.write(f"\nTotal tables:        {total}")
        self.stdout.write(f"Used tables:         {used} ({used/total*100:.1f}%)")
        self.stdout.write(f"Unused tables:       {unused} ({unused/total*100:.1f}%)")

        # Space analysis
        total_rows = sum(self.get_row_count(t) for t in all_tables)
        unused_rows = sum(self.get_row_count(t) for t in unused_tables)

        self.stdout.write(f"\nTotal rows:          {total_rows:,}")
        self.stdout.write(f"Unused table rows:   {unused_rows:,}")

        if unused_tables:
            self.stdout.write("\n" + "=" * 80)
            self.stdout.write("💡 RECOMMENDATIONS:")
            self.stdout.write("=" * 80)
            self.stdout.write("\n1. Review unused tables before deleting")
            self.stdout.write("2. Check if they contain important data")
            self.stdout.write("3. Create backup before cleanup:")
            self.stdout.write("   sqlite3 db.sqlite3 .dump > backup.sql")
            self.stdout.write("\n4. To see which tables to drop, use:")
            self.stdout.write("   python manage.py find_unused_tables --show-references")

        self.stdout.write("\n")

    def is_view(self, table_name):
        """Check if a table is actually a view"""
        try:
            with connection.cursor() as cursor:
                if connection.vendor == "sqlite":
                    cursor.execute("SELECT type FROM sqlite_master WHERE name = ?", [table_name])
                    result = cursor.fetchone()
                    return result and result[0] == "view"
        except Exception:
            pass
        return False

    def get_row_count(self, table_name):
        """Get row count for a table"""
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                return cursor.fetchone()[0]
        except Exception:
            return 0
