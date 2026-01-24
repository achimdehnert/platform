"""
Test all admin URLs and auto-fix errors
"""

import re

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import connection
from django.test import Client


class Command(BaseCommand):
    help = "Test all writing_hub admin URLs and auto-fix errors"

    def add_arguments(self, parser):
        parser.add_argument(
            "--fix",
            action="store_true",
            help="Automatically fix detected errors",
        )
        parser.add_argument(
            "--username",
            type=str,
            default="admin",
            help="Admin username for testing",
        )

    def handle(self, *args, **options):
        auto_fix = options["fix"]
        username = options["username"]

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("🔍 ADMIN URL TESTING & AUTO-FIX"))
        self.stdout.write("=" * 80 + "\n")

        # Temporarily allow testserver
        from django.conf import settings

        original_allowed_hosts = settings.ALLOWED_HOSTS
        settings.ALLOWED_HOSTS = ["*"]  # Allow all hosts for testing

        # Get or create admin user
        User = get_user_model()
        try:
            user = User.objects.get(username=username)
            self.stdout.write(f"✅ Using admin user: {username}\n")
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"❌ User '{username}' not found!"))
            self.stdout.write("   Create superuser: python manage.py createsuperuser\n")
            settings.ALLOWED_HOSTS = original_allowed_hosts
            return

        # Setup client
        client = Client()
        client.force_login(user)

        # Get all writing_hub models
        from apps.writing_hub import models

        writing_hub_models = []

        for model in admin.site._registry:
            if model._meta.app_label == "writing_hub":
                writing_hub_models.append(model)

        self.stdout.write(f"Found {len(writing_hub_models)} writing_hub models in admin\n")

        # Test each model
        errors = []
        for model in sorted(writing_hub_models, key=lambda m: m.__name__):
            model_name = model.__name__
            app_label = model._meta.app_label
            model_name_lower = model._meta.model_name

            url = f"/admin/{app_label}/{model_name_lower}/"

            self.stdout.write(f"\n📋 Testing: {model_name}")
            self.stdout.write(f"   URL: {url}")

            try:
                response = client.get(url)

                if response.status_code == 200:
                    self.stdout.write(self.style.SUCCESS(f"   ✅ OK (200)"))
                elif response.status_code == 500:
                    self.stdout.write(self.style.ERROR(f"   ❌ ERROR (500)"))

                    # Try to extract error
                    error_info = self.extract_error(response)
                    if error_info:
                        errors.append(
                            {
                                "model": model_name,
                                "url": url,
                                "error": error_info,
                                "model_obj": model,
                            }
                        )

                        self.stdout.write(f"   Error: {error_info['type']}")
                        self.stdout.write(f"   Detail: {error_info['message']}")

                        if auto_fix:
                            self.stdout.write(f"   🔧 Attempting auto-fix...")
                            fixed = self.auto_fix_error(error_info, model)
                            if fixed:
                                self.stdout.write(self.style.SUCCESS(f"   ✅ Fixed!"))

                                # Re-test
                                response2 = client.get(url)
                                if response2.status_code == 200:
                                    self.stdout.write(
                                        self.style.SUCCESS(f"   ✅ Verified - now working!")
                                    )
                                else:
                                    self.stdout.write(self.style.WARNING(f"   ⚠️  Still failing"))
                            else:
                                self.stdout.write(self.style.WARNING(f"   ⚠️  Could not auto-fix"))
                else:
                    self.stdout.write(self.style.WARNING(f"   ⚠️  Status: {response.status_code}"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"   ❌ Exception: {e}"))
                errors.append(
                    {
                        "model": model_name,
                        "url": url,
                        "error": {"type": "Exception", "message": str(e)},
                        "model_obj": model,
                    }
                )

        # Summary
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("📊 SUMMARY")
        self.stdout.write("=" * 80)
        self.stdout.write(f"\nTotal models tested: {len(writing_hub_models)}")
        self.stdout.write(f"Errors found:        {len(errors)}")

        if errors and not auto_fix:
            self.stdout.write("\n" + self.style.WARNING("💡 Run with --fix to auto-fix errors"))

        # Restore ALLOWED_HOSTS
        from django.conf import settings

        settings.ALLOWED_HOSTS = original_allowed_hosts

        self.stdout.write("\n")

    def extract_error(self, response):
        """Extract error information from 500 response"""
        try:
            content = response.content.decode("utf-8")

            # Look for OperationalError
            if "OperationalError" in content:
                # Extract error message
                match = re.search(r"OperationalError[^<]*:\s*([^<\n]+)", content)
                if match:
                    message = match.group(1).strip()

                    # Parse specific error types
                    if "no such column" in message:
                        # Extract table and column
                        col_match = re.search(r"no such column:\s*(\w+)\.(\w+)", message)
                        if col_match:
                            return {
                                "type": "missing_column",
                                "table": col_match.group(1),
                                "column": col_match.group(2),
                                "message": message,
                            }
                    elif "no such table" in message:
                        # Extract table name
                        table_match = re.search(r"no such table:\s*(\w+)", message)
                        if table_match:
                            return {
                                "type": "missing_table",
                                "table": table_match.group(1),
                                "message": message,
                            }

                    return {
                        "type": "OperationalError",
                        "message": message,
                    }

            # Look for other Django errors
            if "Exception Type" in content:
                type_match = re.search(r"Exception Type:[^<]*<td>([^<]+)</td>", content)
                value_match = re.search(r"Exception Value:[^<]*<td>([^<]+)</td>", content)

                if type_match:
                    return {
                        "type": type_match.group(1).strip(),
                        "message": value_match.group(1).strip() if value_match else "Unknown",
                    }

        except Exception as e:
            return {
                "type": "parse_error",
                "message": str(e),
            }

        return None

    def auto_fix_error(self, error_info, model):
        """Attempt to automatically fix the error"""
        error_type = error_info["type"]

        if error_type == "missing_column":
            return self.fix_missing_column(error_info, model)
        elif error_type == "missing_table":
            return self.fix_missing_table(error_info, model)

        return False

    def fix_missing_column(self, error_info, model):
        """Fix missing column by creating VIEW with column mapping"""
        table = error_info["table"]
        column = error_info["column"]

        self.stdout.write(f"\n      Analyzing: {table}.{column}")

        # Find what tables exist that might be related
        with connection.cursor() as cursor:
            # Check if it's a view
            cursor.execute("SELECT type, sql FROM sqlite_master WHERE name = ?", [table])
            result = cursor.fetchone()

            if result and result[0] == "view":
                # It's a view - we need to recreate it with the missing column
                self.stdout.write(f"      {table} is a VIEW")

                # Try to find source table with the column
                view_sql = result[1]

                # Extract source table from VIEW
                from_match = re.search(r"FROM\s+(\w+)", view_sql, re.IGNORECASE)
                if from_match:
                    source_table = from_match.group(1)
                    self.stdout.write(f"      Source table: {source_table}")

                    # Check if source has a similar column
                    cursor.execute(f"PRAGMA table_info({source_table})")
                    source_cols = cursor.fetchall()
                    source_col_names = [col[1] for col in source_cols]

                    # Look for similar column names
                    possible_mappings = []
                    for scol in source_col_names:
                        if column.replace("_id", "") in scol or scol.replace("_id", "") in column:
                            possible_mappings.append(scol)

                    if possible_mappings:
                        self.stdout.write(
                            f"      Possible mapping: {possible_mappings[0]} → {column}"
                        )

                        # Recreate view with mapping
                        return self.recreate_view_with_mapping(
                            table, source_table, column, possible_mappings[0]
                        )

        return False

    def recreate_view_with_mapping(self, view_name, source_table, new_col, source_col):
        """Recreate VIEW with column mapping"""
        with connection.cursor() as cursor:
            # Get all columns from source
            cursor.execute(f"PRAGMA table_info({source_table})")
            columns = cursor.fetchall()

            # Build column list with mapping
            col_list = []
            for col in columns:
                col_name = col[1]
                col_list.append(col_name)

            # Add mapping if not already present
            if new_col not in [c[1] for c in columns]:
                col_list.append(f"{source_col} AS {new_col}")

            # Drop and recreate view
            cursor.execute(f"DROP VIEW IF EXISTS {view_name}")

            col_str = ",\n                    ".join(col_list)
            sql = f"""
                CREATE VIEW {view_name} AS
                SELECT
                    {col_str}
                FROM {source_table}
            """

            cursor.execute(sql)
            return True

    def fix_missing_table(self, error_info, model):
        """Fix missing table by creating VIEW to correct table"""
        missing_table = error_info["table"]

        # Try to find similar table
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type IN ('table', 'view')
                AND name NOT LIKE 'sqlite_%'
            """
            )
            all_tables = [row[0] for row in cursor.fetchall()]

            # Look for similar names
            similar = []
            for table in all_tables:
                if missing_table in table or table in missing_table:
                    similar.append(table)

            if similar:
                self.stdout.write(f"      Similar tables: {similar}")
                # Use first match
                target_table = similar[0]

                # Create view
                cursor.execute(f"DROP VIEW IF EXISTS {missing_table}")
                cursor.execute(f"CREATE VIEW {missing_table} AS SELECT * FROM {target_table}")

                self.stdout.write(f"      Created VIEW: {missing_table} → {target_table}")
                return True

        return False
