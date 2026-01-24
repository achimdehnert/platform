#!/usr/bin/env python3
"""
Database analysis script for bfagent.db
"""
import os
import sqlite3
from datetime import datetime


def analyze_database():
    db_path = "bfagent.db"

    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return

    print(f"🔍 Analyzing database: {db_path}")
    print(f"📊 File size: {os.path.getsize(db_path)} bytes")
    print(f"🕐 Last modified: {datetime.fromtimestamp(os.path.getmtime(db_path))}")
    print("-" * 50)

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        print(f"📋 Found {len(tables)} tables:")
        for table in tables:
            table_name = table[0]
            print(f"  - {table_name}")

            # Get table info
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()

            print(f"    Columns ({len(columns)}):")
            for col in columns:
                col_id, name, data_type, not_null, default_val, pk = col
                pk_str = " (PK)" if pk else ""
                null_str = " NOT NULL" if not_null else ""
                default_str = f" DEFAULT {default_val}" if default_val else ""
                print(f"      {name}: {data_type}{pk_str}{null_str}{default_str}")

            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"    Records: {count}")
            print()

        # Get schema
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table'")
        schemas = cursor.fetchall()

        print("📝 Table Schemas:")
        for schema in schemas:
            if schema[0]:
                print(schema[0])
                print()

        conn.close()
        print("✅ Database analysis complete")

    except Exception as e:
        print(f"❌ Error analyzing database: {e}")


if __name__ == "__main__":
    analyze_database()
