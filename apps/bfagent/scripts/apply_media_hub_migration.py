#!/usr/bin/env python
"""
Script to manually apply media_hub migration.
Run: python scripts/apply_media_hub_migration.py
"""
import os
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
django.setup()

from django.db import connection
from django.db.migrations.state import ProjectState
import importlib.util

def main():
    # Check existing tables
    with connection.cursor() as cursor:
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'media_hub%'")
        existing = [row[0] for row in cursor.fetchall()]
        
    if existing:
        print(f"Found existing tables: {existing}")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Aborted.")
            return
    
    # Import the migration module
    migration_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'apps', 'media_hub', 'migrations', '0001_initial.py'
    )
    
    spec = importlib.util.spec_from_file_location('migration', migration_path)
    mig_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mig_module)
    
    migration = mig_module.Migration
    
    print(f"\nApplying {len(migration.operations)} operations...")
    
    # Execute operations
    with connection.schema_editor() as schema_editor:
        state = ProjectState()
        for i, op in enumerate(migration.operations):
            op_name = type(op).__name__
            if hasattr(op, 'name'):
                op_name += f" ({op.name})"
            elif hasattr(op, 'model_name'):
                op_name += f" ({op.model_name})"
            
            print(f"  {i+1:2d}. {op_name}...", end=" ")
            try:
                op.state_forwards('media_hub', state)
                op.database_forwards('media_hub', schema_editor, ProjectState(), state)
                print("OK")
            except Exception as e:
                print(f"ERROR: {e}")
                raise
    
    # Record migration in django_migrations
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, NOW())",
            ['media_hub', '0001_initial']
        )
    
    print("\n✅ Migration applied successfully!")
    
    # Verify tables created
    with connection.cursor() as cursor:
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'media_hub%' ORDER BY table_name")
        tables = [row[0] for row in cursor.fetchall()]
    
    print(f"\nCreated tables ({len(tables)}):")
    for t in tables:
        print(f"  - {t}")

if __name__ == '__main__':
    main()
