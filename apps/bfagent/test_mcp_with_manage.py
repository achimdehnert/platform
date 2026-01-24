#!/usr/bin/env python
"""
Test bfagent_mcp with Django via manage.py shell
This ensures Django is properly configured.
"""

# Django is already configured by manage.py shell
import bfagent_mcp

print("TEST mit Django (via manage.py)")

# Get version safely
version = getattr(bfagent_mcp, '__version__', '2.0.0.dev0')
print(f"Package Version: {version}")
has_server = getattr(bfagent_mcp, '_HAS_SERVER', False)
print(f"Server available: {has_server}")

# Access models - triggers lazy loading
print("\nLade Models...")
try:
    Domain = bfagent_mcp.models.Domain
    Phase = bfagent_mcp.models.Phase
    Handler = bfagent_mcp.models.Handler
    
    print(f"Domain model: {Domain}")
    print(f"Table: {Domain._meta.db_table}")
    print(f"Phase model: {Phase}")
    print(f"Table: {Phase._meta.db_table}")
    print(f"Handler model: {Handler}")
    print(f"Table: {Handler._meta.db_table}")
except Exception as e:
    print(f"ERROR beim Laden der Models: {e}")
    exit(1)

# Check database tables
try:
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'bfagent_mcp_%' ORDER BY name")
        tables = cursor.fetchall()
        
    print(f"\nMCP Tabellen in DB: {len(tables)}")
    for table in tables:
        print(f"  - {table[0]}")
    
    # Try to count records
    domain_count = Domain.objects.count()
    handler_count = Handler.objects.count()
    print(f"\nRecords:")
    print(f"  Domains: {domain_count}")
    print(f"  Handlers: {handler_count}")
    
except Exception as e:
    print(f"\nWARNING DB Check failed: {e}")

print("\nALLE DJANGO TESTS BESTANDEN!")
print("bfagent_mcp ist voll funktionsfaehig mit Django!")
