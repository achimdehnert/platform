#!/usr/bin/env python
import psycopg2

conn = psycopg2.connect('postgresql://bfagent:bfagent_dev_2024@localhost:5432/bfagent_dev')
cur = conn.cursor()

# Check table columns
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'llms' ORDER BY ordinal_position")
print("Columns in llms table:")
for r in cur.fetchall():
    print(f"  - {r[0]}")

# Check if data exists
cur.execute("SELECT id, name, provider, is_active FROM llms LIMIT 5")
print("\nSample data:")
for r in cur.fetchall():
    print(f"  {r}")

conn.close()
