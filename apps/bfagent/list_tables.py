import sqlite3
conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
print("\n=== ALLE TABELLEN IN DB ===\n")
for row in cursor.fetchall():
    print(f"  • {row[0]}")
conn.close()
