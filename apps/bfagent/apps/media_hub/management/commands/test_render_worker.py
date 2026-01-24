"""
Test Render Worker Command
==========================

Test the Media Hub render worker with a sample job.

Usage:
    python manage.py test_render_worker --job-type illustration
    python manage.py test_render_worker --job-type comic_panel --style cinematic
    python manage.py test_render_worker --run-worker  # Run continuous worker
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Test the Media Hub render worker'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--job-type',
            type=str,
            default='illustration',
            choices=['illustration', 'comic_panel', 'book_cover'],
            help='Type of render job to create'
        )
        parser.add_argument(
            '--style',
            type=str,
            default='cinematic',
            help='Style preset slug to use'
        )
        parser.add_argument(
            '--prompt',
            type=str,
            default='A magical forest with glowing mushrooms and fairy lights',
            help='Prompt for image generation'
        )
        parser.add_argument(
            '--run-worker',
            action='store_true',
            help='Run the worker in continuous mode'
        )
        parser.add_argument(
            '--process-job',
            type=int,
            help='Process a specific job ID'
        )
    
    def handle(self, *args, **options):
        # Import models using raw SQL since app isn't loaded
        from apps.media_hub.services.render_worker import RenderWorker, process_render_job
        
        if options['run_worker']:
            self.stdout.write("🚀 Starting render worker in continuous mode...")
            self.stdout.write("   Press Ctrl+C to stop\n")
            worker = RenderWorker()
            try:
                worker.run_loop(poll_interval=5)
            except KeyboardInterrupt:
                self.stdout.write("\n⏹️  Worker stopped.")
            return
        
        if options['process_job']:
            job_id = options['process_job']
            self.stdout.write(f"⚙️  Processing job #{job_id}...")
            result = process_render_job(job_id)
            if result['success']:
                self.stdout.write(self.style.SUCCESS(f"✅ Job completed: {result}"))
            else:
                self.stdout.write(self.style.ERROR(f"❌ Job failed: {result}"))
            return
        
        # Create a test job
        self.stdout.write("\n🎨 Creating test render job...\n")
        
        job_type = options['job_type']
        style_slug = options['style']
        prompt = options['prompt']
        
        # Get style preset ID
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, name FROM media_hub_style_preset WHERE slug = %s",
                [style_slug]
            )
            row = cursor.fetchone()
            if row:
                style_id, style_name = row
                self.stdout.write(f"   Style: {style_name} (ID: {style_id})")
            else:
                style_id = None
                self.stdout.write(self.style.WARNING(f"   Style '{style_slug}' not found, using defaults"))
            
            # Get format preset (square)
            cursor.execute(
                "SELECT id, name FROM media_hub_format_preset WHERE slug = 'square-1-1'"
            )
            row = cursor.fetchone()
            format_id = row[0] if row else None
            
            # Get quality preset (standard)
            cursor.execute(
                "SELECT id, name FROM media_hub_quality_preset WHERE slug = 'standard'"
            )
            row = cursor.fetchone()
            quality_id = row[0] if row else None
        
        # Create job using raw SQL
        import uuid
        import json
        
        job_uuid = str(uuid.uuid4())
        input_snapshot = json.dumps({
            'prompt': {
                'positive': prompt,
            },
            'render': {
                'width': 1024,
                'height': 1024,
            },
            'sampler': {
                'steps': 25,
                'cfg_scale': 7.5,
            }
        })
        
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO media_hub_render_job 
                (uuid, job_type, status, priority, ref_table, ref_id, input_snapshot, 
                 error_message, attempt_count, max_attempts, created_at, updated_at,
                 org_id, project_id, created_by_id, 
                 style_preset_id, format_preset_id, quality_preset_id, voice_preset_id, workflow_id)
                VALUES (%s, %s, 'pending', 5, '', NULL, %s, 
                        '', 0, 3, NOW(), NOW(),
                        NULL, NULL, NULL,
                        %s, %s, %s, NULL, NULL)
                RETURNING id
            """, [job_uuid, job_type, input_snapshot, style_id, format_id, quality_id])
            
            job_id = cursor.fetchone()[0]
        
        self.stdout.write(f"   Job ID: {job_id}")
        self.stdout.write(f"   UUID: {job_uuid}")
        self.stdout.write(f"   Type: {job_type}")
        self.stdout.write(f"   Prompt: {prompt[:50]}...")
        
        self.stdout.write("\n⚙️  Processing job...\n")
        
        # Process the job
        result = process_render_job(job_id)
        
        if result['success']:
            self.stdout.write(self.style.SUCCESS(f"\n✅ Job completed successfully!"))
            
            # Show asset info
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT a.id, a.title, af.storage_path, af.file_size
                    FROM media_hub_asset a
                    LEFT JOIN media_hub_asset_file af ON af.asset_id = a.id
                    WHERE a.job_id = %s
                """, [job_id])
                row = cursor.fetchone()
                if row:
                    asset_id, title, path, size = row
                    self.stdout.write(f"   Asset ID: {asset_id}")
                    self.stdout.write(f"   File: {path}")
                    self.stdout.write(f"   Size: {size or 'unknown'} bytes")
        else:
            self.stdout.write(self.style.ERROR(f"\n❌ Job failed: {result.get('error', 'Unknown error')}"))
            
            # Show error details
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT status, error_message FROM media_hub_render_job WHERE id = %s",
                    [job_id]
                )
                row = cursor.fetchone()
                if row:
                    self.stdout.write(f"   Status: {row[0]}")
                    self.stdout.write(f"   Error: {row[1]}")
        
        self.stdout.write("")
