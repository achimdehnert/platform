#!/usr/bin/env python
"""Check media_hub database schema."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.db import connection

tables = ['media_hub_render_job', 'media_hub_render_attempt', 'media_hub_asset', 'media_hub_asset_file']

for table in tables:
    print(f"\nColumns in {table}:")
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = %s
            ORDER BY ordinal_position
        """, [table])
        for row in cursor.fetchall():
            print(f"  - {row[0]}")
