#!/usr/bin/env python
"""Quick table existence checker"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

import django
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='phase_action_configs'")
    result = cursor.fetchall()
    
    if result:
        print("✅ Table 'phase_action_configs' EXISTS!")
    else:
        print("❌ Table 'phase_action_configs' MISSING!")
        print("\nAll tables:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        for row in cursor.fetchall():
            print(f"  - {row[0]}")
