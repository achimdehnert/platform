#!/usr/bin/env python
"""Clear error messages from completed jobs."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("UPDATE media_hub_render_job SET error_message = '' WHERE status = 'completed'")
    print(f"Cleared errors from {cursor.rowcount} completed jobs")
    
    # Also check for assets
    cursor.execute("SELECT COUNT(*) FROM media_hub_asset")
    count = cursor.fetchone()[0]
    print(f"Total assets: {count}")
