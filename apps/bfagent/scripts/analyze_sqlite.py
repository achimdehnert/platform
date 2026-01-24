#!/usr/bin/env python
"""
Analyze SQLite database for migration to PostgreSQL
"""
import sqlite3
import sys
from pathlib import Path


def analyze_sqlite_db(db_path):
    """Analyze SQLite database structure and content"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()

        print(f"\n{'='*60}")
        print(f"SQLite Database Analysis: {db_path}")
        print(f"{'='*60}\n")
        print(f"Total Tables: {len(tables)}\n")

        # Analyze each table
        total_rows = 0
        table_stats = []

        for (table_name,) in tables:
            if table_name.startswith("sqlite_"):
                continue

            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            total_rows += row_count

            if row_count > 0:
                table_stats.append((table_name, row_count))

        # Sort by row count descending
        table_stats.sort(key=lambda x: x[1], reverse=True)

        print(f"Tables with Data (Top 20):")
        print(f"{'-'*60}")
        for table_name, row_count in table_stats[:20]:
            print(f"  {table_name:<40} {row_count:>10,} rows")

        print(f"\n{'='*60}")
        print(f"Total Rows to Migrate: {total_rows:,}")
        print(f"{'='*60}\n")

        conn.close()
        return len(tables), total_rows, table_stats

    except Exception as e:
        print(f"Error analyzing database: {e}", file=sys.stderr)
        return 0, 0, []


if __name__ == "__main__":
    db_path = Path(__file__).parent.parent / "bfagent.db"

    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)

    analyze_sqlite_db(db_path)
