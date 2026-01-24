#!/usr/bin/env python
"""Reset failed media hub jobs."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    # Delete old attempts first
    cursor.execute("DELETE FROM media_hub_render_attempt")
    print(f"Deleted {cursor.rowcount} old attempts")
    
    # Reset jobs
    cursor.execute("""
        UPDATE media_hub_render_job 
        SET status = 'pending', error_message = '', attempt_count = 0 
        WHERE status IN ('failed', 'queued', 'running')
    """)
    print(f"Reset {cursor.rowcount} jobs to pending")
