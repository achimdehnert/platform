import sqlite3
conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'mcp_%' ORDER BY name")
tables = [r[0] for r in cursor.fetchall()]
print(f"Found {len(tables)} MCP tables:")
for t in tables:
    cursor.execute(f"SELECT COUNT(*) FROM {t}")
    count = cursor.fetchone()[0]
    print(f"  - {t}: {count} rows")
conn.close()
