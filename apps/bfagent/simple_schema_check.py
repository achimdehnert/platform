import sqlite3
conn = sqlite3.connect('bfagent.db')
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(action_templates)")
print("COLUMNS:")
for col in cursor.fetchall():
    print(f"  - {col[1]} ({col[2]})")
conn.close()
