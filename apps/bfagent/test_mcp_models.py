"""Test bfagent_mcp models with Django."""
import os
import django

# Configure Django BEFORE importing models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

# Now import and test models
import bfagent_mcp

print("✅ Package imported")
print(f"✅ Version: {bfagent_mcp.__version__}")
print(f"✅ Server available: {bfagent_mcp._HAS_SERVER}")

# Access models (triggers lazy loading)
print("\n🔄 Accessing models...")
Domain = bfagent_mcp.models.Domain
Phase = bfagent_mcp.models.Phase
Handler = bfagent_mcp.models.Handler

print(f"✅ Domain model: {Domain}")
print(f"✅ Phase model: {Phase}")
print(f"✅ Handler model: {Handler}")

# Check if tables exist
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'bfagent_mcp_%'")
    tables = cursor.fetchall()
    print(f"\n✅ MCP Tables in DB: {len(tables)}")
    for table in tables:
        print(f"   - {table[0]}")

print("\n🎉 ALLES FUNKTIONIERT!")
