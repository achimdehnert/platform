#!/usr/bin/env python
"""Fix invalid JSON in action_templates.pipeline_config using direct SQL."""
import sqlite3
import json

db_path = 'bfagent.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("🔍 Checking action_templates.pipeline_config...")

# Get all action_templates
cursor.execute("SELECT id, pipeline_config FROM action_templates")
rows = cursor.fetchall()

fixed_count = 0
for row_id, pipeline_config in rows:
    if pipeline_config:
        try:
            # Try to parse as JSON
            json.loads(pipeline_config)
            print(f"✅ ID {row_id}: Valid JSON")
        except (json.JSONDecodeError, TypeError):
            print(f"❌ ID {row_id}: Invalid JSON - Setting to NULL")
            cursor.execute("UPDATE action_templates SET pipeline_config = NULL WHERE id = ?", (row_id,))
            fixed_count += 1
    else:
        print(f"⚪ ID {row_id}: Empty/NULL (OK)")

conn.commit()
conn.close()

print(f"\n✅ Fixed {fixed_count} records!")
print("🚀 Jetzt kannst du 'python manage.py migrate' ausführen!")
