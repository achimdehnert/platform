#!/usr/bin/env python
"""Add references column (reserved keyword)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    try:
        cursor.execute('ALTER TABLE prompt_templates ADD COLUMN "references" JSONB DEFAULT \'{}\'::jsonb')
        print("Added: references")
    except Exception as e:
        print(f"Error: {e}")
