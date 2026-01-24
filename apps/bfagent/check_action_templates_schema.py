#!/usr/bin/env python
"""Check action_templates table schema."""
import sqlite3

db_path = 'bfagent.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("📊 action_templates TABLE SCHEMA:")
print("=" * 60)

cursor.execute("PRAGMA table_info(action_templates)")
columns = cursor.fetchall()

for col in columns:
    print(f"  {col[1]:<30} {col[2]:<15} NOT NULL: {bool(col[3])}")

print("\n📋 CURRENT DATA:")
print("=" * 60)

cursor.execute("SELECT * FROM action_templates LIMIT 3")
rows = cursor.fetchall()

if rows:
    # Get column names
    col_names = [description[0] for description in cursor.description]
    print(f"Columns: {', '.join(col_names)}")
    print()
    
    for row in rows:
        print(f"ID {row[0]}:")
        for i, val in enumerate(row):
            if val:
                print(f"  {col_names[i]}: {repr(val)[:100]}")
else:
    print("  No data found")

conn.close()
