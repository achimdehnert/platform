import sqlite3
import sys

conn = sqlite3.connect('db.sqlite3')
c = conn.cursor()

sys.stdout.write("\n=== BFAGENT MIGRATIONS ===\n")
sys.stdout.flush()

c.execute("SELECT id, name, applied FROM django_migrations WHERE app='bfagent' ORDER BY id")
for row in c.fetchall():
    sys.stdout.write(f"  {row[0]:3d}: {row[1]} ({row[2]})\n")
    sys.stdout.flush()

sys.stdout.write("\n=== WRITING_HUB MIGRATIONS ===\n")
sys.stdout.flush()

c.execute("SELECT id, name, applied FROM django_migrations WHERE app='writing_hub' ORDER BY id")
rows = c.fetchall()
if rows:
    for row in rows:
        sys.stdout.write(f"  {row[0]:3d}: {row[1]} ({row[2]})\n")
        sys.stdout.flush()
else:
    sys.stdout.write("  (keine)\n")
    sys.stdout.flush()

conn.close()
sys.stdout.write("\n✅ Fertig\n")
sys.stdout.flush()
