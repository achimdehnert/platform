"""
Celery Tasks for Story Generation

Async tasks for:
- Story generation (long-running)
- Location research
- Progress updates via WebSocket/polling
"""

import logging
from celery import shared_task
from django.core.cache import cache

from .models import Story
from .services import StoryGenerator

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_story_task(self, story_id: int):
    """
    Async task for story generation.
    
    Updates progress in cache for polling.
    """
    try:
        story = Story.objects.get(id=story_id)
        trip = story.trip
        user = story.user
        
        generator = StoryGenerator(trip, user)
        
        # Generate with progress updates
        for progress in generator.generate_story(story):
            # Store progress in cache for polling
            cache_key = f"story_progress:{story_id}"
            cache.set(cache_key, progress, timeout=3600)
            
            logger.info(f"Story {story_id}: {progress}")
            
            # Update task state
            self.update_state(
                state='PROGRESS',
                meta=progress
            )
            
            if progress.get('phase') == 'error':
                raise Exception(progress.get('message', 'Unknown error'))
        
        return {
            'status': 'complete',
            'story_id': story_id,
            'chapters': story.chapters.count(),
        }
        
    except Story.DoesNotExist:
        logger.error(f"Story {story_id} not found")
        return {'status': 'error', 'message': 'Story not found'}
        
    except Exception as e:
        logger.exception(f"Story generation failed: {story_id}")
        
        # Update story status
        try:
            story = Story.objects.get(id=story_id)
            story.status = Story.Status.FAILED
            story.save()
        except:
            pass
        
        # Retry or fail
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        return {'status': 'error', 'message': str(e)}


@shared_task
def cleanup_failed_generations():
    """
    Periodic task to cleanup stuck generations.
    
    Marks stories stuck in 'generating' for >1 hour as failed.
    """
    from datetime import timedelta
    from django.utils import timezone
    
    cutoff = timezone.now() - timedelta(hours=1)
    
    stuck = Story.objects.filter(
        status=Story.Status.GENERATING,
        updated_at__lt=cutoff,
    )
    
    count = stuck.update(status=Story.Status.FAILED)
    
    if count:
        logger.warning(f"Marked {count} stuck stories as failed")
    
    return {'cleaned': count}


@shared_task
def pregenerate_location_data(city: str, country: str, genres: list[str] = None):
    """
    Pre-generate location data for common destinations.
    
    Useful for warming cache before users need it.
    """
    from apps.locations.services import LocationGenerator
    
    if genres is None:
        genres = ['romance', 'thriller', 'mystery', 'adventure']
    
    generator = LocationGenerator()
    results = {}
    
    for genre in genres:
        result = generator.get_or_generate(city, country, genre)
        results[genre] = {
            'success': result.success,
            'from_cache': result.from_cache,
            'error': result.error,
        }
    
    return {
        'city': city,
        'country': country,
        'results': results,
    }


@shared_task
def cleanup_expired_cache():
    """Periodic task to cleanup expired research cache."""
    from apps.locations.services import LocationCache
    
    deleted = LocationCache.cleanup_expired()
    
    return {'deleted': deleted}


# ============================================================================
# Task Registration for Celery Beat
# ============================================================================

# Add to celery beat schedule in settings:
# CELERY_BEAT_SCHEDULE = {
#     'cleanup-failed-generations': {
#         'task': 'apps.stories.tasks.cleanup_failed_generations',
#         'schedule': crontab(minute=0, hour='*/2'),  # Every 2 hours
#     },
#     'cleanup-expired-cache': {
#         'task': 'apps.stories.tasks.cleanup_expired_cache',
#         'schedule': crontab(minute=0, hour=4),  # Daily at 4 AM
#     },
# }
