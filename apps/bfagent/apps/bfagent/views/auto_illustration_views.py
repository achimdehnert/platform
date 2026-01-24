"""
Auto-Illustration Views
Synchronous MVP version (no Celery required for testing)
"""
import json
import asyncio
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import structlog

from apps.bfagent.models import BookChapters
from apps.bfagent.models_illustration import IllustrationImage, ImageStatus, ImageType
from apps.bfagent.handlers.chapter_illustration_handler import ChapterIllustrationHandler

logger = structlog.get_logger(__name__)


@login_required
@require_http_methods(["POST"])
def auto_illustrate_chapter_sync(request, chapter_id):
    """
    Synchronous auto-illustration endpoint (MVP version)
    
    For production: Use celery task (apps.bfagent.tasks.auto_illustrate_chapter_task)
    For testing: Direct synchronous call
    """
    try:
        # Parse request data
        data = json.loads(request.body)
        max_illustrations = int(data.get('max_illustrations', 3))
        style_profile = data.get('style_profile')
        provider = data.get('provider', 'stability')  # Use Stability AI by default
        
        logger.info("auto_illustrate_request_parsed", data=data)
        
        logger.info("auto_illustrate_request", 
                   chapter_id=chapter_id,
                   user_id=request.user.id,
                   max_illustrations=max_illustrations)
        
        # Get chapter
        try:
            chapter = BookChapters.objects.get(pk=chapter_id, project__user=request.user)
        except BookChapters.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'error': 'Chapter not found or access denied'
            }, status=404)
        
        # Initialize handler (REAL AI MODE - Stability AI is configured!)
        mock_mode = False  # Using real Stability AI
        handler = ChapterIllustrationHandler(mock_mode=mock_mode)
        
        # Run auto-illustration (sync wrapper for async)
        result = asyncio.run(handler.auto_illustrate_chapter(
            chapter_id=chapter.id,
            chapter_text=chapter.content or "",
            max_illustrations=max_illustrations,
            style_profile=style_profile,
            provider=provider,
            quality='standard'
        ))
        
        logger.info("auto_illustrate_complete",
                   chapter_id=chapter_id,
                   images_generated=result.images_generated,
                   cost=result.total_cost_usd)
        
        # Save generated images to database
        saved_images = []
        logger.info("saving_images", count=len(result.generated_images), images=result.generated_images)
        
        for idx, img_data in enumerate(result.generated_images):
            import uuid
            logger.info("saving_image", idx=idx, img_data=img_data)
            
            generated_img = IllustrationImage.objects.create(
                # Required fields
                image_id=f"auto-{chapter.id}-{uuid.uuid4().hex[:8]}",
                user=request.user,
                chapter=chapter,
                project=chapter.project,
                image_url=img_data.get('image_url', ''),
                provider_used=provider,
                prompt_used=img_data.get('revised_prompt', img_data.get('prompt', '')),
                resolution="1024x1024",
                quality="standard",
                # Optional fields
                image_type=ImageType.SCENE,
                generation_time_seconds=img_data.get('generation_time_seconds', 0),
                status=ImageStatus.GENERATED,
                content_context={'position': img_data.get('position', {})}
            )
            saved_images.append(generated_img.id)
        
        logger.info("images_saved_to_db", count=len(saved_images), ids=saved_images)
        
        return JsonResponse({
            'status': 'success',
            'chapter_id': chapter_id,
            'images_generated': result.images_generated,
            'total_cost_usd': result.total_cost_usd,
            'duration_seconds': result.duration_seconds,
            'positions': [p.dict() for p in result.positions],
            'images': result.generated_images,
            'mock_mode': mock_mode
        })
    
    except Exception as e:
        logger.error("auto_illustrate_failed", 
                    chapter_id=chapter_id,
                    error=str(e),
                    error_type=type(e).__name__)
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def auto_illustrate_chapter_async(request, chapter_id):
    """
    Async auto-illustration endpoint (requires Celery + Redis)
    
    Use this once Celery is set up
    """
    try:
        # Import here to avoid errors if Celery not configured
        from apps.bfagent.tasks import auto_illustrate_chapter_task
        
        # Parse request
        data = json.loads(request.body)
        max_illustrations = data.get('max_illustrations', 3)
        
        # Start Celery task
        task = auto_illustrate_chapter_task.delay(
            chapter_id=chapter_id,
            user_id=request.user.id,
            max_illustrations=max_illustrations
        )
        
        return JsonResponse({
            'status': 'started',
            'task_id': task.id
        })
    
    except Exception as e:
        logger.error("async_task_failed", error=str(e))
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def auto_illustrate_task_status(request, task_id):
    """
    Check Celery task status (requires Celery + Redis)
    """
    try:
        from celery.result import AsyncResult
        
        result = AsyncResult(task_id)
        
        response_data = {
            'state': result.state,
            'info': result.info if isinstance(result.info, dict) else {}
        }
        
        if result.successful():
            response_data['result'] = result.result
        elif result.failed():
            response_data['error'] = str(result.info)
        
        return JsonResponse(response_data)
    
    except Exception as e:
        return JsonResponse({
            'state': 'FAILURE',
            'error': str(e)
        }, status=500)
