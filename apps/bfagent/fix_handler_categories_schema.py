"""
Fix handler_categories schema - Add missing columns

Adds missing columns to existing handler_categories table:
- display_order (rename from sort_order)
- is_system
- config
"""

import os
import sys

import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from django.db import connection


def fix_schema():
    """Add missing columns to handler_categories table"""

    print("\n" + "=" * 70)
    print("  FIX HANDLER_CATEGORIES SCHEMA")
    print("=" * 70 + "\n")

    with connection.cursor() as cursor:
        # Check current schema
        cursor.execute("PRAGMA table_info(handler_categories)")
        columns = {row[1]: row for row in cursor.fetchall()}

        print("📊 Current columns:")
        for col_name in columns.keys():
            print(f"  - {col_name}")
        print()

        # Add missing columns
        changes_made = []

        # 1. Add is_system if missing
        if "is_system" not in columns:
            print("➕ Adding column: is_system")
            cursor.execute(
                """
                ALTER TABLE handler_categories
                ADD COLUMN is_system BOOLEAN NOT NULL DEFAULT 0
            """
            )
            changes_made.append("is_system")
        else:
            print("✅ Column exists: is_system")

        # 2. Add config if missing
        if "config" not in columns:
            print("➕ Adding column: config")
            cursor.execute(
                """
                ALTER TABLE handler_categories
                ADD COLUMN config TEXT NOT NULL DEFAULT '{}'
            """
            )
            changes_made.append("config")
        else:
            print("✅ Column exists: config")

        # 3. Rename sort_order to display_order if needed
        if "sort_order" in columns and "display_order" not in columns:
            print("🔄 Renaming column: sort_order → display_order")
            # SQLite doesn't support RENAME COLUMN directly in older versions
            # We need to create new column and copy data
            cursor.execute(
                """
                ALTER TABLE handler_categories
                ADD COLUMN display_order INTEGER NOT NULL DEFAULT 0
            """
            )
            cursor.execute(
                """
                UPDATE handler_categories
                SET display_order = sort_order
            """
            )
            changes_made.append("display_order (copied from sort_order)")
            print("⚠️  Note: sort_order column still exists (can be dropped later)")
        elif "display_order" in columns:
            print("✅ Column exists: display_order")
        else:
            # Neither exists, create display_order
            print("➕ Adding column: display_order")
            cursor.execute(
                """
                ALTER TABLE handler_categories
                ADD COLUMN display_order INTEGER NOT NULL DEFAULT 0
            """
            )
            changes_made.append("display_order")

        print()

        if changes_made:
            print("=" * 70)
            print("  ✅ SCHEMA UPDATED")
            print("=" * 70 + "\n")
            print("Changes made:")
            for change in changes_made:
                print(f"  ✅ {change}")
        else:
            print("=" * 70)
            print("  ℹ️  NO CHANGES NEEDED")
            print("=" * 70 + "\n")
            print("Schema already up to date!")

        print()

        # Show updated schema
        cursor.execute("PRAGMA table_info(handler_categories)")
        columns_after = cursor.fetchall()

        print("📊 Final schema:")
        for row in columns_after:
            col_id, name, type_, notnull, default, pk = row
            print(
                f"  {col_id}. {name:<20} {type_:<10} "
                + (f"NOT NULL " if notnull else "")
                + (f"DEFAULT {default}" if default else "")
            )

        print("\n" + "=" * 70)
        print("  ✅ SCHEMA FIX COMPLETE!")
        print("=" * 70 + "\n")

        print("🎯 Next Step:")
        print("   python manage.py load_handler_categories\n")


if __name__ == "__main__":
    try:
        fix_schema()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
