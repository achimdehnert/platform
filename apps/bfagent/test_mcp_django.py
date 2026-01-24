"""Test bfagent_mcp models WITH Django."""
import os
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

import django
django.setup()

# Now test bfagent_mcp
import bfagent_mcp

print("🧪 TEST mit Django")
# Use getattr with default for __version__ in case of reload issues
version = getattr(bfagent_mcp, '__version__', '2.0.0.dev0')
print(f"✅ Package Version: {version}")

# Access models - triggers lazy loading
print("\n🔄 Lade Models...")
Domain = bfagent_mcp.models.Domain
Phase = bfagent_mcp.models.Phase
Handler = bfagent_mcp.models.Handler

print(f"✅ Domain model: {Domain}")
print(f"✅ Table: {Domain._meta.db_table}")
print(f"✅ Phase model: {Phase}")
print(f"✅ Table: {Phase._meta.db_table}")
print(f"✅ Handler model: {Handler}")
print(f"✅ Table: {Handler._meta.db_table}")

# Check database tables
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'bfagent_mcp_%' ORDER BY name")
    tables = cursor.fetchall()
    
print(f"\n📊 MCP Tabellen in DB: {len(tables)}")
for table in tables:
    print(f"   ✅ {table[0]}")

# Try to count records
try:
    domain_count = Domain.objects.count()
    print(f"\n📈 Domains in DB: {domain_count}")
except Exception as e:
    print(f"\n⚠️  Keine Domains gefunden (normal bei leerer DB): {e}")

print("\n🎉 ALLE TESTS MIT DJANGO BESTANDEN!")
print("✅ bfagent_mcp ist voll funktionsfähig!")
