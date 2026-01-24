#!/usr/bin/env python
"""
Migrate data from SQLite to PostgreSQL using Django's dumpdata/loaddata
"""
import os
import subprocess
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.apps import apps
from django.core.management import call_command
from django.db import connection


def get_app_models():
    """Get all installed apps with models (excluding some built-in)"""
    exclude_apps = [
        "contenttypes",  # Will be auto-created
        "sessions",  # Not needed to migrate
        "admin",  # Auto-created
    ]

    installed_apps = []
    for app_config in apps.get_app_configs():
        if app_config.models_module is not None:
            app_label = app_config.label
            if app_label not in exclude_apps:
                installed_apps.append(app_label)

    return sorted(installed_apps)


def export_sqlite_data():
    """Export data from SQLite to JSON fixtures"""
    print("\n" + "=" * 60)
    print("STEP 1: Export SQLite Data")
    print("=" * 60 + "\n")

    # Ensure using SQLite
    if "postgresql" in connection.settings_dict["ENGINE"]:
        print("❌ Error: Currently connected to PostgreSQL!")
        print("   Please temporarily set DJANGO_ENV to use SQLite")
        return False

    fixture_dir = project_root / "fixtures"
    fixture_dir.mkdir(exist_ok=True)

    apps_to_export = get_app_models()

    print(f"Found {len(apps_to_export)} apps to export:\n")

    exported_count = 0
    for app_label in apps_to_export:
        fixture_file = fixture_dir / f"{app_label}.json"

        try:
            # Export app data
            with open(fixture_file, "w", encoding="utf-8") as f:
                call_command("dumpdata", app_label, indent=2, output=str(fixture_file), verbosity=0)

            # Check if file has content
            if fixture_file.stat().st_size > 10:
                exported_count += 1
                print(f"  ✅ {app_label:<30} → {fixture_file.name}")
            else:
                fixture_file.unlink()  # Delete empty files

        except Exception as e:
            print(f"  ⚠️  {app_label:<30} → Error: {e}")

    print(f"\n{'='*60}")
    print(f"Exported {exported_count} apps to {fixture_dir}")
    print(f"{'='*60}\n")

    return True


def import_postgres_data():
    """Import data from JSON fixtures to PostgreSQL"""
    print("\n" + "=" * 60)
    print("STEP 2: Import Data to PostgreSQL")
    print("=" * 60 + "\n")

    # Ensure using PostgreSQL
    if "sqlite" in connection.settings_dict["ENGINE"]:
        print("❌ Error: Currently connected to SQLite!")
        print("   Please set DJANGO_ENV to use PostgreSQL")
        return False

    fixture_dir = project_root / "fixtures"

    if not fixture_dir.exists():
        print("❌ Error: fixtures directory not found!")
        return False

    fixture_files = sorted(fixture_dir.glob("*.json"))

    if not fixture_files:
        print("❌ Error: No fixture files found!")
        return False

    print(f"Found {len(fixture_files)} fixture files to import:\n")

    imported_count = 0
    for fixture_file in fixture_files:
        try:
            call_command("loaddata", str(fixture_file), verbosity=0)
            imported_count += 1
            print(f"  ✅ {fixture_file.stem:<30} → Imported")

        except Exception as e:
            print(f"  ⚠️  {fixture_file.stem:<30} → Error: {e}")

    print(f"\n{'='*60}")
    print(f"Imported {imported_count}/{len(fixture_files)} fixtures")
    print(f"{'='*60}\n")

    return True


def verify_migration():
    """Verify migration by comparing row counts"""
    print("\n" + "=" * 60)
    print("STEP 3: Verify Migration")
    print("=" * 60 + "\n")

    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                schemaname,
                tablename,
                n_tup_ins as row_count
            FROM pg_stat_user_tables
            WHERE n_tup_ins > 0
            ORDER BY n_tup_ins DESC
            LIMIT 20
        """
        )

        results = cursor.fetchall()

        print("Top 20 tables in PostgreSQL:\n")
        for schema, table, count in results:
            print(f"  {table:<40} {count:>10,} rows")

    print(f"\n{'='*60}")
    print("Migration verification complete!")
    print(f"{'='*60}\n")


def main():
    """Main migration workflow"""
    print("\n" + "=" * 70)
    print("SQLite → PostgreSQL Migration Tool")
    print("=" * 70)

    # Check current database
    db_engine = connection.settings_dict["ENGINE"]
    print(f"\nCurrent Database Engine: {db_engine}\n")

    if "sqlite" in db_engine:
        print("📤 Exporting from SQLite...")
        if not export_sqlite_data():
            return

        print("\n" + "⚠️" * 30)
        print("IMPORTANT: Switch to PostgreSQL now!")
        print("  1. Set DJANGO_ENV=production (or ensure development.py uses PostgreSQL)")
        print("  2. Run: python scripts/migrate_to_postgres.py import")
        print("⚠️" * 30 + "\n")

    elif "postgresql" in db_engine:
        print("📥 Importing to PostgreSQL...")
        if not import_postgres_data():
            return

        verify_migration()

        print("\n✅ Migration complete! PostgreSQL is now your primary database.\n")

    else:
        print(f"❌ Unknown database engine: {db_engine}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "import":
        # Force import mode
        if "postgresql" not in connection.settings_dict["ENGINE"]:
            print("❌ Error: Not connected to PostgreSQL!")
            sys.exit(1)
        import_postgres_data()
        verify_migration()
    else:
        main()
