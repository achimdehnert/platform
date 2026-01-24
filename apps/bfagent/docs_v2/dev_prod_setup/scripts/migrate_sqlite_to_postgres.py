"""
SQLite to PostgreSQL Migration Script

Migrates data from existing SQLite database to new PostgreSQL database.

Usage:
    1. Make sure PostgreSQL is running (docker-compose up -d)
    2. Run: python scripts/migrate_sqlite_to_postgres.py

Options:
    --dry-run    Show what would be migrated without doing it
    --tables     Only migrate specific tables (comma-separated)
"""

import argparse
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

import django

django.setup()

from django.apps import apps
from django.core.management import call_command
from django.db import connection


def get_sqlite_path():
    """Find SQLite database file."""
    possible_paths = [
        PROJECT_ROOT / "db.sqlite3",
        PROJECT_ROOT / "database.sqlite3",
        PROJECT_ROOT / "data" / "db.sqlite3",
    ]

    for path in possible_paths:
        if path.exists():
            return path

    return None


def get_sqlite_tables(sqlite_path):
    """Get list of tables in SQLite database."""
    conn = sqlite3.connect(sqlite_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type='table'
        AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """
    )

    tables = [row[0] for row in cursor.fetchall()]
    conn.close()

    return tables


def get_table_row_count(sqlite_path, table_name):
    """Get row count for a table."""
    conn = sqlite3.connect(sqlite_path)
    cursor = conn.cursor()

    try:
        cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
        count = cursor.fetchone()[0]
    except Exception:
        count = 0

    conn.close()
    return count


def check_postgres_connection():
    """Verify PostgreSQL connection."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            print(f"✅ Connected to PostgreSQL")
            print(f"   Version: {version[:50]}...")
            return True
    except Exception as e:
        print(f"❌ Cannot connect to PostgreSQL: {e}")
        return False


def run_migrations():
    """Run Django migrations on PostgreSQL."""
    print("\n📦 Running Django migrations...")
    try:
        call_command("migrate", "--verbosity", "1")
        print("✅ Migrations complete")
        return True
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False


def export_data_from_sqlite(sqlite_path, output_dir):
    """Export data from SQLite to JSON fixtures."""
    print(f"\n📤 Exporting data from SQLite...")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Temporarily use SQLite
    from django.conf import settings

    original_db = settings.DATABASES["default"].copy()

    settings.DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(sqlite_path),
    }

    # Reset connection
    from django import db

    db.connections.close_all()

    # Export each app
    exported_files = []
    for app_config in apps.get_app_configs():
        if app_config.name.startswith("django."):
            continue

        app_name = app_config.label
        output_file = output_dir / f"{app_name}.json"

        try:
            call_command(
                "dumpdata",
                app_name,
                "--output",
                str(output_file),
                "--indent",
                "2",
                "--verbosity",
                "0",
            )

            if output_file.exists() and output_file.stat().st_size > 10:
                exported_files.append(output_file)
                print(f"   ✅ {app_name}: {output_file.stat().st_size} bytes")
            else:
                output_file.unlink(missing_ok=True)

        except Exception as e:
            print(f"   ⚠️ {app_name}: {str(e)[:50]}")

    # Restore PostgreSQL
    settings.DATABASES["default"] = original_db
    db.connections.close_all()

    return exported_files


def import_data_to_postgres(fixture_files):
    """Import data into PostgreSQL from fixtures."""
    print(f"\n📥 Importing data to PostgreSQL...")

    for fixture_file in fixture_files:
        try:
            call_command("loaddata", str(fixture_file), "--verbosity", "0")
            print(f"   ✅ Loaded: {fixture_file.name}")
        except Exception as e:
            print(f"   ❌ Failed: {fixture_file.name} - {str(e)[:50]}")


def main():
    parser = argparse.ArgumentParser(description="Migrate SQLite to PostgreSQL")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    parser.add_argument(
        "--skip-export", action="store_true", help="Skip SQLite export, use existing fixtures"
    )
    parser.add_argument(
        "--fixtures-dir", default="migration_fixtures", help="Directory for fixtures"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("SQLite to PostgreSQL Migration")
    print("=" * 60)
    print(f"Started: {datetime.now()}")

    # Find SQLite database
    sqlite_path = get_sqlite_path()
    if not sqlite_path:
        print("\n❌ SQLite database not found!")
        print("   Expected: db.sqlite3 in project root")
        sys.exit(1)

    print(f"\n📂 SQLite database: {sqlite_path}")

    # Show SQLite stats
    tables = get_sqlite_tables(sqlite_path)
    print(f"   Tables: {len(tables)}")

    total_rows = 0
    for table in tables[:10]:  # Show first 10
        count = get_table_row_count(sqlite_path, table)
        total_rows += count
        if count > 0:
            print(f"   - {table}: {count} rows")

    if len(tables) > 10:
        print(f"   ... and {len(tables) - 10} more tables")

    print(f"   Total rows: {total_rows}")

    if args.dry_run:
        print("\n⚠️ DRY RUN - No changes will be made")
        return

    # Check PostgreSQL
    if not check_postgres_connection():
        print("\n💡 Start PostgreSQL with: docker-compose up -d")
        sys.exit(1)

    # Run migrations
    if not run_migrations():
        sys.exit(1)

    # Export from SQLite
    fixtures_dir = PROJECT_ROOT / args.fixtures_dir

    if not args.skip_export:
        fixture_files = export_data_from_sqlite(sqlite_path, fixtures_dir)
    else:
        fixture_files = list(fixtures_dir.glob("*.json"))
        print(f"\n📂 Using existing fixtures: {len(fixture_files)} files")

    # Import to PostgreSQL
    if fixture_files:
        import_data_to_postgres(fixture_files)

    print("\n" + "=" * 60)
    print("✅ Migration complete!")
    print("=" * 60)
    print(f"\nNext steps:")
    print("1. Verify data: python manage.py shell")
    print("2. Test application: python manage.py runserver")
    print(f"3. Backup fixtures: {fixtures_dir}")
    print(f"4. (Optional) Remove SQLite: rm {sqlite_path}")


if __name__ == "__main__":
    main()
