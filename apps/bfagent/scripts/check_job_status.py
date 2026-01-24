#!/usr/bin/env python
"""Check job status and errors."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.db import connection

print("\nJob Status:")
print("-" * 60)
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT id, status, error_message 
        FROM media_hub_render_job 
        ORDER BY id
    """)
    for row in cursor.fetchall():
        print(f"Job #{row[0]}: {row[1]}")
        if row[2]:
            print(f"   Error: {row[2]}")

print("\n\nChecking ComfyUI at localhost:8188...")
import requests
try:
    r = requests.get("http://localhost:8188/system_stats", timeout=3)
    print(f"   ✅ ComfyUI is running! Status: {r.status_code}")
except Exception as e:
    print(f"   ❌ ComfyUI not reachable: {e}")
