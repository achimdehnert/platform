#!/usr/bin/env python
"""List all tables in the database"""
import sqlite3

conn = sqlite3.connect('bfagent.db')
cursor = conn.cursor()

print("=" * 70)
print("DATABASE TABLES")
print("=" * 70)
print()

cursor.execute("""
    SELECT name, type 
    FROM sqlite_master 
    WHERE type='table' 
    ORDER BY name
""")

tables = cursor.fetchall()
print(f"Total Tables: {len(tables)}")
print()

# Look for anything with "template" or "prompt" in name
print("TEMPLATE/PROMPT RELATED TABLES:")
for name, ttype in tables:
    if 'template' in name.lower() or 'prompt' in name.lower():
        # Count records
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {name}")
            count = cursor.fetchone()[0]
            print(f"  • {name:40} ({count} records)")
        except:
            print(f"  • {name:40} (ERROR)")

print()
print("ALL TABLES:")
for name, ttype in tables:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {name}")
        count = cursor.fetchone()[0]
        print(f"  • {name:40} ({count} records)")
    except:
        print(f"  • {name:40} (ERROR)")

conn.close()
