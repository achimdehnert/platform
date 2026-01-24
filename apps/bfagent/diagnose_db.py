import sqlite3

conn = sqlite3.connect('bfagent.db')
cursor = conn.cursor()

print("=" * 70)
print("📊 ACTION_TEMPLATES TABLE DIAGNOSTIC")
print("=" * 70)
print()

# 1. Check table structure
print("1️⃣  TABLE STRUCTURE:")
cursor.execute("PRAGMA table_info(action_templates)")
columns = cursor.fetchall()
for col in columns:
    print(f"   {col[1]:<30} {col[2]:<15} NOT NULL: {bool(col[3])}")

print()

# 2. Check table schema (to see CHECK constraints)
print("2️⃣  CREATE TABLE STATEMENT:")
cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='action_templates'")
create_stmt = cursor.fetchone()
if create_stmt:
    print(create_stmt[0])

print()

# 3. Count records with pipeline_config
print("3️⃣  PIPELINE_CONFIG DATA:")
try:
    cursor.execute("SELECT COUNT(*) FROM action_templates WHERE pipeline_config IS NOT NULL")
    count = cursor.fetchone()[0]
    print(f"   Records with pipeline_config: {count}")
    
    if count > 0:
        cursor.execute("SELECT id, pipeline_config FROM action_templates WHERE pipeline_config IS NOT NULL LIMIT 5")
        rows = cursor.fetchall()
        print()
        print("   Sample values:")
        for row_id, val in rows:
            print(f"   ID {row_id}: {repr(val)[:100]}")
except Exception as e:
    print(f"   ❌ Error: {e}")

conn.close()
