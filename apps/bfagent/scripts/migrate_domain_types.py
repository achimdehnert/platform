"""Migrate domain_types from SQLite to Postgres"""
import sqlite3
import subprocess

conn = sqlite3.connect(r"c:\Users\achim\github\bfagent\bfagent_20251206.db")
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("SELECT * FROM domain_types ORDER BY id")
rows = c.fetchall()

print(f"Found {len(rows)} domain_types to migrate")

def escape(v):
    if v is None:
        return "NULL"
    s = str(v).replace("'", "''")
    return f"'{s}'"

def run_psql(sql):
    result = subprocess.run(
        ["docker", "exec", "-i", "bfagent_db", "psql", "-U", "bfagent", "-d", "bfagent_dev", "-c", sql],
        capture_output=True, text=True, encoding="utf-8"
    )
    return result.returncode, result.stderr

migrated = 0
for row in rows:
    config = row["config"] if row["config"] else "{}"
    sql = (
        f"INSERT INTO domain_types (id, domain_art_id, name, slug, display_name, description, icon, color, config, is_active, sort_order, created_at, updated_at) "
        f"VALUES ({row['id']}, {row['domain_art_id']}, {escape(row['name'])}, {escape(row['slug'])}, "
        f"{escape(row['display_name'])}, {escape(row['description'] or '')}, "
        f"{escape(row['icon'] or 'bi-folder')}, {escape(row['color'] or 'primary')}, "
        f"{escape(config)}::jsonb, {str(bool(row['is_active'])).lower()}, {row['sort_order'] or 0}, "
        f"{escape(row['created_at'])}, {escape(row['updated_at'])});"
    )
    rc, err = run_psql(sql)
    if rc == 0:
        print(f"  OK: {row['name']}")
        migrated += 1
    else:
        print(f"  ERR: {row['name']} - {err}")

# Reset sequence
run_psql("SELECT setval(pg_get_serial_sequence('domain_types', 'id'), (SELECT COALESCE(MAX(id), 1) FROM domain_types));")

print(f"\nMigrated {migrated}/{len(rows)} domain_types")
conn.close()
