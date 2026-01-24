import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.db import connection

cursor = connection.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [row[0] for row in cursor.fetchall()]

print("\n📊 ALL TABLES IN DATABASE:\n")
for table in tables:
    print(f"  - {table}")

print("\n🔍 AGENT-RELATED TABLES:\n")
agent_tables = [t for t in tables if 'agent' in t.lower()]
for table in agent_tables:
    print(f"  - {table}")
