"""
Event Subscribers for BF Agent Event-Driven Architecture.

This module contains event handlers that respond to events published via the event_bus.
All subscribers are registered automatically when this module is imported.

Enable by setting: FEATURE_FLAG_USE_EVENT_BUS=true
"""

import logging
from typing import Any, Dict

from apps.core.event_bus import event_bus
from apps.core.events import Events

logger = logging.getLogger(__name__)


# =============================================================================
# ILLUSTRATION SUBSCRIBER
# =============================================================================

@event_bus.subscribe(Events.CONTENT_GENERATED)
def auto_queue_illustration(content_type: str, content_id: int, **kwargs) -> bool:
    """
    Automatically queue illustration generation when chapter content is generated.
    
    This subscriber listens for CONTENT_GENERATED events and triggers
    illustration generation for chapters that don't have illustrations yet.
    
    Args:
        content_type: Type of content ('chapter', 'outline', etc.)
        content_id: ID of the generated content
        **kwargs: Additional event data (project_id, word_count, etc.)
    
    Returns:
        True if illustration was queued, False otherwise
    """
    # Only handle chapter content
    if content_type != 'chapter':
        return False
    
    project_id = kwargs.get('project_id')
    chapter_number = kwargs.get('chapter_number')
    
    logger.info(
        f"[AutoIllustration] Chapter {chapter_number} generated for project {project_id}. "
        f"Checking if illustration needed..."
    )
    
    try:
        # Check if chapter already has illustrations
        from apps.writing_hub.models import Chapter, Illustration
        
        chapter = Chapter.objects.filter(id=content_id).first()
        if not chapter:
            logger.warning(f"[AutoIllustration] Chapter {content_id} not found")
            return False
        
        existing_illustrations = Illustration.objects.filter(chapter=chapter).count()
        
        if existing_illustrations > 0:
            logger.info(
                f"[AutoIllustration] Chapter {content_id} already has {existing_illustrations} illustrations"
            )
            return False
        
        # Queue illustration generation (async via Celery if available)
        logger.info(f"[AutoIllustration] Queuing illustration for chapter {content_id}")
        
        # TODO: Integrate with illustration MCP server or Celery task
        # For now, just log the intent
        # from apps.writing_hub.tasks import generate_chapter_illustration
        # generate_chapter_illustration.delay(chapter_id=content_id)
        
        return True
        
    except ImportError:
        logger.debug("[AutoIllustration] Writing Hub models not available")
        return False
    except Exception as e:
        logger.error(f"[AutoIllustration] Error: {e}")
        return False


# =============================================================================
# ANALYTICS SUBSCRIBER
# =============================================================================

@event_bus.subscribe(Events.CONTENT_GENERATED)
def log_content_analytics(content_type: str, content_id: int, **kwargs) -> bool:
    """
    Log content generation analytics for monitoring and reporting.
    
    Args:
        content_type: Type of content generated
        content_id: ID of the content
        **kwargs: Additional event data
    
    Returns:
        True if logged successfully
    """
    source = kwargs.get('source', 'unknown')
    llm_used = kwargs.get('llm_used', 'unknown')
    word_count = kwargs.get('word_count', 0)
    project_id = kwargs.get('project_id')
    
    logger.info(
        f"[Analytics] Content generated: type={content_type}, id={content_id}, "
        f"project={project_id}, source={source}, llm={llm_used}, words={word_count}"
    )
    
    # TODO: Store in analytics table for dashboard
    # ContentGenerationLog.objects.create(
    #     content_type=content_type,
    #     content_id=content_id,
    #     project_id=project_id,
    #     source=source,
    #     llm_used=llm_used,
    #     word_count=word_count,
    # )
    
    return True


@event_bus.subscribe(Events.CHARACTER_CREATED)
def log_character_analytics(project_id: int, character_count: int, **kwargs) -> bool:
    """
    Log character creation analytics.
    
    Args:
        project_id: Project ID
        character_count: Number of characters created
        **kwargs: Additional event data
    
    Returns:
        True if logged successfully
    """
    source = kwargs.get('source', 'unknown')
    llm_used = kwargs.get('llm_used', 'unknown')
    
    logger.info(
        f"[Analytics] Characters created: project={project_id}, count={character_count}, "
        f"source={source}, llm={llm_used}"
    )
    
    return True


# =============================================================================
# HUB LIFECYCLE SUBSCRIBER
# =============================================================================

@event_bus.subscribe(Events.HUB_ACTIVATED)
def on_hub_activated(hub_id: str, **kwargs) -> bool:
    """
    Handle hub activation events.
    
    Args:
        hub_id: ID of the activated hub
        **kwargs: Additional event data
    
    Returns:
        True if handled successfully
    """
    logger.info(f"[HubLifecycle] Hub activated: {hub_id}")
    
    # TODO: Run hub initialization tasks
    # - Create default navigation items
    # - Initialize hub-specific settings
    # - Send notification to admins
    
    return True


@event_bus.subscribe(Events.HUB_DEACTIVATED)
def on_hub_deactivated(hub_id: str, **kwargs) -> bool:
    """
    Handle hub deactivation events.
    
    Args:
        hub_id: ID of the deactivated hub
        **kwargs: Additional event data
    
    Returns:
        True if handled successfully
    """
    logger.info(f"[HubLifecycle] Hub deactivated: {hub_id}")
    
    # TODO: Run hub cleanup tasks
    # - Hide navigation items
    # - Pause scheduled tasks
    # - Send notification to admins
    
    return True


# =============================================================================
# WORKFLOW SUBSCRIBER
# =============================================================================

@event_bus.subscribe(Events.WORKFLOW_COMPLETED)
def on_workflow_completed(workflow_id: int, **kwargs) -> bool:
    """
    Handle workflow completion events.
    
    Args:
        workflow_id: ID of the completed workflow
        **kwargs: Additional event data
    
    Returns:
        True if handled successfully
    """
    status = kwargs.get('status', 'completed')
    duration_ms = kwargs.get('duration_ms', 0)
    
    logger.info(
        f"[Workflow] Workflow {workflow_id} completed: status={status}, duration={duration_ms}ms"
    )
    
    # TODO: Send notification, update dashboard, trigger follow-up tasks
    
    return True


# =============================================================================
# REGISTRATION INFO
# =============================================================================

def get_registered_subscribers() -> Dict[str, Any]:
    """
    Get information about registered event subscribers.
    
    Returns:
        Dict with subscriber info
    """
    return {
        'auto_queue_illustration': {
            'event': 'CONTENT_GENERATED',
            'description': 'Auto-queue illustration for chapters',
        },
        'log_content_analytics': {
            'event': 'CONTENT_GENERATED',
            'description': 'Log content generation analytics',
        },
        'log_character_analytics': {
            'event': 'CHARACTER_CREATED',
            'description': 'Log character creation analytics',
        },
        'on_hub_activated': {
            'event': 'HUB_ACTIVATED',
            'description': 'Handle hub activation',
        },
        'on_hub_deactivated': {
            'event': 'HUB_DEACTIVATED',
            'description': 'Handle hub deactivation',
        },
        'on_workflow_completed': {
            'event': 'WORKFLOW_COMPLETED',
            'description': 'Handle workflow completion',
        },
    }
