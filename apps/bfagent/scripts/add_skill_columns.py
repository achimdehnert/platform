#!/usr/bin/env python
"""Add AgentSkills.io columns to prompt_templates table."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.db import connection

print("Adding AgentSkills.io columns to prompt_templates...")

with connection.cursor() as cursor:
    # Check existing columns
    cursor.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'prompt_templates'
    """)
    existing = [row[0] for row in cursor.fetchall()]
    print(f"Existing columns count: {len(existing)}")
    
    # Columns to add
    columns = [
        ("skill_description", "TEXT DEFAULT ''"),
        ("compatibility", "VARCHAR(500) DEFAULT ''"),
        ("license", "VARCHAR(100) DEFAULT 'Proprietary'"),
        ("author", "VARCHAR(100) DEFAULT ''"),
        ("allowed_tools", "JSONB DEFAULT '[]'::jsonb"),
        ("references", "JSONB DEFAULT '{}'::jsonb"),
        ("agent_class", "VARCHAR(200) DEFAULT ''"),
    ]
    
    for col_name, col_type in columns:
        if col_name not in existing:
            try:
                sql = f"ALTER TABLE prompt_templates ADD COLUMN {col_name} {col_type}"
                cursor.execute(sql)
                print(f"✅ Added: {col_name}")
            except Exception as e:
                print(f"❌ Error {col_name}: {e}")
        else:
            print(f"⏭️  Exists: {col_name}")

print("\nDone!")
