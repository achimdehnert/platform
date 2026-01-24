"""
Render Worker Service
=====================

Processes render jobs from the queue, executes ComfyUI workflows,
and persists generated assets.
"""
import os
import json
import uuid
import hashlib
import structlog
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

from django.db import transaction
from django.utils import timezone
from django.conf import settings

logger = structlog.get_logger(__name__)


class RenderWorker:
    """
    Worker for processing Media Hub render jobs.
    
    Lifecycle:
    1. Poll for pending jobs
    2. Build input snapshot from presets
    3. Execute workflow (ComfyUI/TTS)
    4. Create asset records
    5. Update job status
    """
    
    def __init__(self, comfyui_url: Optional[str] = None):
        """Initialize worker with ComfyUI connection."""
        self.comfyui_url = comfyui_url or os.getenv('COMFYUI_URL', 'http://localhost:8188')
        self.log = logger.bind(worker="RenderWorker")
        self.output_dir = Path(settings.MEDIA_ROOT) / 'media_hub' / 'assets'
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def get_pending_jobs(self, limit: int = 10) -> List[Any]:
        """Get pending render jobs ordered by priority."""
        from apps.media_hub.models import RenderJob
        
        return list(RenderJob.objects.filter(
            status='pending'
        ).order_by('-priority', 'created_at')[:limit])
    
    def claim_job(self, job_id: int) -> Optional[Any]:
        """Atomically claim a job for processing."""
        from apps.media_hub.models import RenderJob
        
        with transaction.atomic():
            job = RenderJob.objects.select_for_update().filter(
                id=job_id,
                status='pending'
            ).first()
            
            if job:
                job.status = 'queued'
                job.save(update_fields=['status', 'updated_at'])
                self.log.info("job_claimed", job_id=job.id, job_type=job.job_type)
            
            return job
    
    def process_job(self, job: Any) -> bool:
        """
        Process a single render job.
        
        Returns True on success, False on failure.
        """
        from apps.media_hub.models import RenderAttempt, Asset, AssetFile
        
        self.log.info("processing_job", job_id=job.id, job_type=job.job_type)
        
        # Create attempt record
        attempt_no = job.attempt_count + 1
        attempt = RenderAttempt.objects.create(
            job=job,
            attempt_no=attempt_no,
            status='running',
            started_at=timezone.now()
        )
        
        # Update job status
        job.status = 'running'
        job.attempt_count = attempt_no
        job.started_at = job.started_at or timezone.now()
        job.save(update_fields=['status', 'attempt_count', 'started_at', 'updated_at'])
        
        try:
            # Build input snapshot if not already set
            if not job.input_snapshot:
                job.input_snapshot = job.build_input_snapshot()
                job.save(update_fields=['input_snapshot'])
            
            # Execute based on job type
            if job.job_type in ['illustration', 'comic_panel', 'book_cover']:
                result = self._execute_image_job(job, attempt)
            elif job.job_type in ['audio_chapter', 'audio_full']:
                result = self._execute_audio_job(job, attempt)
            else:
                raise ValueError(f"Unknown job type: {job.job_type}")
            
            # Update attempt
            attempt.status = 'completed'
            attempt.completed_at = timezone.now()
            attempt.duration_ms = int((attempt.completed_at - attempt.started_at).total_seconds() * 1000)
            attempt.output_data = result.get('metadata', {})
            attempt.save()
            
            # Create asset from result
            asset = self._create_asset(job, result)
            
            # Update job
            job.status = 'completed'
            job.completed_at = timezone.now()
            job.save(update_fields=['status', 'completed_at', 'updated_at'])
            
            self.log.info("job_completed", job_id=job.id, asset_id=asset.id if asset else None)
            return True
            
        except Exception as e:
            self.log.error("job_failed", job_id=job.id, error=str(e))
            
            # Update attempt
            attempt.status = 'failed'
            attempt.completed_at = timezone.now()
            attempt.duration_ms = int((attempt.completed_at - attempt.started_at).total_seconds() * 1000)
            attempt.error_message = str(e)
            attempt.save()
            
            # Check if we should retry
            if job.attempt_count < job.max_attempts:
                job.status = 'pending'  # Re-queue for retry
                job.error_message = f"Attempt {attempt_no} failed: {e}"
            else:
                job.status = 'failed'
                job.error_message = f"Max attempts ({job.max_attempts}) reached. Last error: {e}"
            
            job.save(update_fields=['status', 'error_message', 'updated_at'])
            return False
    
    def _execute_image_job(self, job: Any, attempt: Any) -> Dict[str, Any]:
        """Execute an image generation job via ComfyUI."""
        from apps.bfagent.handlers.comfyui_handler import ComfyUIHandler
        
        handler = ComfyUIHandler(base_url=self.comfyui_url)
        snapshot = job.input_snapshot
        
        # Build prompt from snapshot
        prompt_parts = []
        if snapshot.get('prompt', {}).get('positive'):
            prompt_parts.append(snapshot['prompt']['positive'])
        if snapshot.get('prompt', {}).get('style'):
            prompt_parts.append(snapshot['prompt']['style'])
        
        prompt = ', '.join(prompt_parts) if prompt_parts else 'a beautiful illustration'
        negative = snapshot.get('prompt', {}).get('negative', '')
        
        # Get dimensions
        width = snapshot.get('render', {}).get('width', 1024)
        height = snapshot.get('render', {}).get('height', 1024)
        
        # Get sampler settings
        steps = snapshot.get('sampler', {}).get('steps', 25)
        cfg = snapshot.get('sampler', {}).get('cfg_scale', 7.0)
        
        self.log.info("executing_comfyui", 
                     prompt=prompt[:100], 
                     width=width, height=height,
                     steps=steps, cfg=cfg)
        
        # Generate image
        try:
            import asyncio
            result = asyncio.run(handler.generate_image(
                prompt=prompt,
                negative_prompt=negative,
                width=width,
                height=height,
                steps=steps,
                cfg=cfg
            ))
        except Exception as e:
            self.log.error("comfyui_generation_error", error=str(e))
            raise
        
        if not result.get('success'):
            raise Exception(result.get('error', 'ComfyUI generation failed'))
        
        # Save image to file - ComfyUIHandler returns image_base64
        image_data = result.get('image_base64') or result.get('image_data')
        if not image_data:
            self.log.error("no_image_data", result_keys=list(result.keys()))
            raise Exception("No image data returned from ComfyUI")
        
        # Generate filename
        file_uuid = str(uuid.uuid4())
        filename = f"{job.job_type}_{job.id}_{file_uuid}.png"
        filepath = self.output_dir / filename
        
        # Decode and save
        import base64
        if isinstance(image_data, str):
            image_bytes = base64.b64decode(image_data)
        else:
            image_bytes = image_data
        
        filepath.write_bytes(image_bytes)
        
        # Calculate checksum
        checksum = hashlib.sha256(image_bytes).hexdigest()
        
        return {
            'success': True,
            'file_path': str(filepath),
            'filename': filename,
            'file_size': len(image_bytes),
            'mime_type': 'image/png',
            'checksum': checksum,
            'metadata': {
                'width': width,
                'height': height,
                'prompt': prompt,
                'steps': steps,
                'cfg_scale': cfg,
                'comfy_prompt_id': result.get('prompt_id'),
            }
        }
    
    def _execute_audio_job(self, job: Any, attempt: Any) -> Dict[str, Any]:
        """Execute an audio generation job via TTS."""
        from apps.media_hub.services.tts_service import TTSService
        
        tts = TTSService()
        snapshot = job.input_snapshot
        
        # Get text to synthesize
        text = snapshot.get('text', '')
        if not text and snapshot.get('chapter_id'):
            # Fetch chapter text from database
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT content FROM chapters_v2 WHERE id = %s
                """, [snapshot['chapter_id']])
                row = cursor.fetchone()
                if row:
                    text = row[0] or ''
        
        if not text:
            raise Exception("No text provided for audio generation")
        
        # Get voice preset
        voice_preset = snapshot.get('voice_preset')
        engine = snapshot.get('engine', 'xtts')
        
        self.log.info("executing_tts", 
                     text_length=len(text),
                     voice_preset=voice_preset,
                     engine=engine)
        
        # Check if this is a full chapter or short text
        if job.job_type == 'audio_chapter' and len(text) > 1000:
            result = tts.synthesize_chapter(
                text,
                chapter_id=snapshot.get('chapter_id', job.id),
                voice_preset_slug=voice_preset,
                engine=engine
            )
        else:
            result = tts.synthesize_text(
                text,
                voice_preset_slug=voice_preset,
                engine=engine
            )
        
        if not result.get('success'):
            raise Exception(result.get('error', 'TTS generation failed'))
        
        # Calculate checksum
        audio_bytes = Path(result['file_path']).read_bytes()
        checksum = hashlib.sha256(audio_bytes).hexdigest()
        
        return {
            'success': True,
            'file_path': result['file_path'],
            'filename': Path(result['file_path']).name,
            'file_size': result.get('file_size', len(audio_bytes)),
            'mime_type': result.get('mime_type', 'audio/wav'),
            'checksum': checksum,
            'metadata': {
                'duration': result.get('duration', 0),
                'engine': result.get('engine'),
                'voice_id': result.get('voice_id'),
                'text_length': len(text),
            }
        }
    
    def _create_asset(self, job: Any, result: Dict[str, Any]) -> Any:
        """Create asset record from render result."""
        from apps.media_hub.models import Asset, AssetFile
        
        # Map job type to asset type
        asset_type_map = {
            'illustration': 'image',
            'comic_panel': 'image',
            'book_cover': 'image',
            'audio_chapter': 'audio',
            'audio_full': 'audio',
            'video_trailer': 'video',
        }
        
        asset = Asset.objects.create(
            asset_type=asset_type_map.get(job.job_type, 'image'),
            title=f"{job.job_type.replace('_', ' ').title()} - Job #{job.id}",
            description=f"Generated from render job #{job.id}",
            job=job,
            project_id=job.project_id,
            org_id=job.org_id,
            created_by_id=job.created_by_id,
            content_type=job.ref_table,
            content_id=job.ref_id,
            metadata=result.get('metadata', {}),
        )
        
        # Create file record
        AssetFile.objects.create(
            asset=asset,
            file_type='original',
            storage_path=result['file_path'],
            storage_backend='local',
            mime_type=result.get('mime_type', 'application/octet-stream'),
            file_size=result.get('file_size'),
            checksum=result.get('checksum', ''),
        )
        
        self.log.info("asset_created", asset_id=asset.id, file_path=result['file_path'])
        return asset
    
    def run_once(self) -> int:
        """Process one batch of pending jobs. Returns count processed."""
        jobs = self.get_pending_jobs(limit=5)
        processed = 0
        
        for job in jobs:
            claimed = self.claim_job(job.id)
            if claimed:
                success = self.process_job(claimed)
                processed += 1
        
        return processed
    
    def run_loop(self, poll_interval: int = 5):
        """Run worker in continuous loop."""
        import time
        
        self.log.info("worker_started", poll_interval=poll_interval)
        
        while True:
            try:
                processed = self.run_once()
                if processed > 0:
                    self.log.info("batch_processed", count=processed)
            except Exception as e:
                self.log.error("worker_error", error=str(e))
            
            time.sleep(poll_interval)


def process_render_job(job_id: int) -> Dict[str, Any]:
    """
    Task function for django-q2 or direct execution.
    
    Usage:
        # Direct
        result = process_render_job(123)
        
        # Via django-q2
        from django_q.tasks import async_task
        async_task('apps.media_hub.services.render_worker.process_render_job', job_id)
    """
    from apps.media_hub.models import RenderJob
    
    worker = RenderWorker()
    
    try:
        job = RenderJob.objects.get(id=job_id)
    except RenderJob.DoesNotExist:
        return {'success': False, 'error': f'Job {job_id} not found'}
    
    # Claim and process
    claimed = worker.claim_job(job_id)
    if not claimed:
        return {'success': False, 'error': f'Job {job_id} could not be claimed (already processing?)'}
    
    success = worker.process_job(claimed)
    
    return {
        'success': success,
        'job_id': job_id,
        'status': claimed.status,
    }
