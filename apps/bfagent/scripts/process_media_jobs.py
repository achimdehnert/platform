#!/usr/bin/env python
"""
Process Media Hub Jobs
======================
Run the render worker to process pending jobs.
"""
import os
import sys

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.db import connection
from apps.media_hub.services.render_worker import RenderWorker

def main():
    # Show pending jobs
    print("\n📋 Current Jobs:")
    print("-" * 50)
    with connection.cursor() as cursor:
        cursor.execute('''
            SELECT id, job_type, status, created_at 
            FROM media_hub_render_job 
            ORDER BY created_at DESC LIMIT 10
        ''')
        for row in cursor.fetchall():
            print(f"  Job #{row[0]}: {row[1]} - {row[2]} ({row[3]})")
    
    # Initialize worker
    comfyui_url = os.getenv('COMFYUI_URL', 'http://localhost:8188')
    print(f"\n🔧 ComfyUI URL: {comfyui_url}")
    
    worker = RenderWorker(comfyui_url=comfyui_url)
    
    # Process jobs
    print("\n⚙️  Processing pending jobs...")
    try:
        pending = worker.get_pending_jobs(limit=2)
        print(f"   Found {len(pending)} pending jobs")
        
        processed = 0
        for job in pending:
            print(f"\n   Processing Job #{job.id} ({job.job_type})...")
            claimed = worker.claim_job(job.id)
            if claimed:
                success = worker.process_job(claimed)
                if success:
                    print(f"   ✅ Job #{job.id} completed!")
                    processed += 1
                else:
                    print(f"   ❌ Job #{job.id} failed")
            else:
                print(f"   ⚠️  Could not claim job #{job.id}")
        
        print(f"\n✅ Processed {processed} jobs")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
