"""Check database tables"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%handler%' ORDER BY name;")
    tables = cursor.fetchall()
    
    print("\n📊 Handler-related tables in database:")
    print("=" * 60)
    
    if not tables:
        print("❌ No handler tables found!")
    else:
        for (table_name,) in tables:
            print(f"  ✅ {table_name}")
            
            # Show columns
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            for col in columns:
                col_name = col[1]
                col_type = col[2]
                pk = " (PK)" if col[5] else ""
                print(f"      - {col_name}: {col_type}{pk}")
            print()
    
    print("=" * 60)
    
    # Also check Handler model's db_table
    from apps.core.models import Handler
    print(f"\n📋 Handler model expects table: '{Handler._meta.db_table}'")
    print()
