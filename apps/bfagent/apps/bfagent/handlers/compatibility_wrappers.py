"""
Backward Compatibility Wrappers
================================

Provides backward-compatible function signatures for legacy code
that calls the old handler methods directly.

These wrappers adapt the new Handler V2.0 architecture to the old
function-based API, allowing gradual migration.

Author: BF Agent Framework
Date: 2025-11-02
"""

from typing import Dict, Any, Optional, List
import logging

from apps.bfagent.handlers.chapter_regenerate_handler_v2 import ChapterRegenerateHandlerV2
from apps.bfagent.handlers.chapter_auto_illustrate_handler_v2 import ChapterAutoIllustrateHandlerV2

logger = logging.getLogger(__name__)


# ==================== REVIEW SYSTEM WRAPPERS ====================

def regenerate_chapter_with_feedback(
    context: Dict[str, Any],
    project,
) -> Dict[str, Any]:
    """
    LEGACY WRAPPER for chapter regeneration
    
    Maintains backward compatibility with old function signature
    from ChapterGenerateHandler._regenerate_chapter_with_feedback()
    
    Args:
        context: Legacy context dict with 'chapter_id', 'parameters', etc.
        project: BookProjects instance (for compatibility)
        
    Returns:
        Result dict in legacy format
        
    Example:
        >>> context = {
        ...     'chapter_id': 5,
        ...     'parameters': {
        ...         'style_notes': 'More suspenseful',
        ...         'include_feedback_types': ['suggestion']
        ...     }
        ... }
        >>> result = regenerate_chapter_with_feedback(context, project)
    """
    logger.info(
        "Using backward compatibility wrapper for regenerate_chapter_with_feedback"
    )
    
    # Extract parameters from legacy context
    chapter_id = context.get('chapter_id')
    if not chapter_id:
        return {
            'success': False,
            'action': 'regenerate_chapter_with_feedback',
            'message': 'chapter_id is required',
            'data': {}
        }
    
    parameters = context.get('parameters', {})
    
    # Map legacy parameters to new handler input
    handler_input = {
        'project_id': project.id,
        'chapter_id': chapter_id,
        'include_feedback_types': parameters.get(
            'include_feedback_types',
            ['suggestion', 'concern', 'general']
        ),
        'style_notes': parameters.get('style_notes'),
        'include_dialogue': parameters.get('include_dialogue'),
        'target_word_count': parameters.get('target_word_count'),
        'agent_id': context.get('agent_id'),
        'detect_conflicts': parameters.get('detect_conflicts', False),
        'force_regenerate': parameters.get('force_regenerate', False),
        'test_mode': parameters.get('test_mode', False),
    }
    
    # Execute new handler
    handler = ChapterRegenerateHandlerV2()
    result = handler.execute(handler_input)
    
    # Map new result format to legacy format
    if result['success']:
        legacy_result = {
            'success': True,
            'action': 'regenerate_chapter_with_feedback',
            'data': {
                'chapter_id': result['data']['chapter_id'],
                'content': result['data']['content'],
                'word_count': result['data']['word_count'],
                'feedback_integrated': result['data']['feedback_integrated'],
                'saved_path': result['data'].get('saved_path'),
                'metadata': result['data'].get('metadata', {})
            },
            'message': result['message']
        }
    else:
        # Error case
        legacy_result = {
            'success': False,
            'action': 'regenerate_chapter_with_feedback',
            'message': result['message'],
            'error_type': result.get('error_type', 'unknown_error'),
            'data': {}
        }
    
    return legacy_result


# ==================== ILLUSTRATION SYSTEM WRAPPERS ====================

def auto_illustrate_chapter_sync(
    chapter_id: int,
    chapter_text: str,
    max_illustrations: int = 3,
    style_profile: Optional[str] = None,
    provider: str = 'dalle3',
    quality: str = 'standard',
    user = None,
) -> Dict[str, Any]:
    """
    LEGACY WRAPPER for auto-illustration
    
    Maintains backward compatibility with old function signature
    from views/auto_illustration_views.py
    
    Args:
        chapter_id: Chapter ID to illustrate
        chapter_text: Chapter content (not used in V2, loaded from DB)
        max_illustrations: Maximum number of illustrations
        style_profile: Style profile prompt
        provider: Image provider
        quality: Image quality
        user: User instance (for DB operations)
        
    Returns:
        Result dict in legacy format
        
    Example:
        >>> result = auto_illustrate_chapter_sync(
        ...     chapter_id=5,
        ...     chapter_text="Once upon a time...",
        ...     max_illustrations=3,
        ...     provider='mock'
        ... )
    """
    logger.info(
        f"Using backward compatibility wrapper for auto_illustrate_chapter_sync "
        f"(chapter_id={chapter_id})"
    )
    
    # Map legacy parameters to new handler input
    handler_input = {
        'chapter_id': chapter_id,
        'max_illustrations': max_illustrations,
        'provider': provider if provider in ['mock', 'dalle3', 'stable-diffusion'] else 'mock',
        'style_profile_prompt': style_profile,
        'quality': quality,
        'save_to_chapter': True,
    }
    
    # Execute new handler
    handler = ChapterAutoIllustrateHandlerV2()
    result = handler.execute(handler_input)
    
    # Map new result format to legacy format
    if result['success']:
        legacy_result = {
            'status': 'success',
            'chapter_id': result['chapter_id'],
            'images_generated': result['images_generated'],
            'total_cost_usd': result['total_cost_usd'],
            'duration_seconds': result['duration_seconds'],
            'mock_mode': result['mock_mode'],
            'images': result['generated_images'],
            # Legacy format compatibility
            'positions': [
                {
                    'paragraph_index': img['paragraph_index'],
                    'illustration_type': img['illustration_type']
                }
                for img in result['generated_images']
            ],
        }
    else:
        # Error case
        legacy_result = {
            'status': 'error',
            'error': result['message'],
            'error_type': result.get('error_type', 'unknown_error')
        }
    
    return legacy_result


def auto_illustrate_chapter_task(
    chapter_id: int,
    user_id: int,
    max_illustrations: int = 3,
    style_profile: Optional[str] = None,
    provider: str = 'dalle3',
) -> Dict[str, Any]:
    """
    LEGACY WRAPPER for Celery task
    
    Maintains backward compatibility with old task signature
    from tasks.py
    
    Args:
        chapter_id: Chapter ID
        user_id: User ID (for permissions)
        max_illustrations: Maximum illustrations
        style_profile: Style profile
        provider: Image provider
        
    Returns:
        Result dict in Celery task format
    """
    logger.info(
        f"Using backward compatibility wrapper for auto_illustrate_chapter_task "
        f"(chapter_id={chapter_id}, user_id={user_id})"
    )
    
    # Load chapter to verify user access
    from apps.bfagent.models import BookChapters
    
    try:
        chapter = BookChapters.objects.select_related('project__user').get(
            id=chapter_id,
            project__user_id=user_id
        )
    except Exception as e:
        # Catch any exception (DoesNotExist, PermissionDenied, etc.)
        return {
            'status': 'FAILURE',
            'error': f"Chapter {chapter_id} not found or access denied: {str(e)}"
        }
    
    # Map to new handler input
    handler_input = {
        'chapter_id': chapter_id,
        'max_illustrations': max_illustrations,
        'provider': provider,
        'style_profile_prompt': style_profile,
        'save_to_chapter': True,
    }
    
    # Execute handler
    handler = ChapterAutoIllustrateHandlerV2()
    result = handler.execute(handler_input)
    
    # Map to Celery task format
    if result['success']:
        return {
            'status': 'SUCCESS',
            'chapter_id': result['chapter_id'],
            'images_generated': result['images_generated'],
            'total_cost_usd': result['total_cost_usd'],
            'duration_seconds': result['duration_seconds'],
            'positions': [
                {
                    'paragraph_index': img['paragraph_index'],
                    'illustration_type': img['illustration_type']
                }
                for img in result['generated_images']
            ],
            'images': result['generated_images']
        }
    else:
        return {
            'status': 'FAILURE',
            'error': result['message'],
            'error_type': result.get('error_type', 'unknown_error')
        }


# ==================== HELPER FUNCTIONS ====================

def is_using_v2_handlers() -> bool:
    """
    Check if V2 handlers are enabled
    
    Can be used for feature flags or gradual rollout
    """
    import os
    return os.getenv('USE_HANDLER_V2', 'true').lower() == 'true'


def get_handler_version() -> str:
    """Get current handler framework version"""
    return '2.0.0'


# ==================== MIGRATION HELPERS ====================

def migrate_context_to_handler_input(
    context: Dict[str, Any],
    handler_name: str
) -> Dict[str, Any]:
    """
    Helper to migrate legacy context dict to handler input format
    
    Args:
        context: Legacy context dict
        handler_name: Name of handler ('regenerate' or 'illustrate')
        
    Returns:
        Handler input dict
    """
    if handler_name == 'regenerate':
        return {
            'project_id': context.get('project_id'),
            'chapter_id': context.get('chapter_id'),
            'include_feedback_types': context.get('parameters', {}).get(
                'include_feedback_types',
                ['suggestion', 'concern']
            ),
            'style_notes': context.get('parameters', {}).get('style_notes'),
            'agent_id': context.get('agent_id'),
        }
    
    elif handler_name == 'illustrate':
        return {
            'chapter_id': context.get('chapter_id'),
            'max_illustrations': context.get('max_illustrations', 3),
            'provider': context.get('provider', 'mock'),
            'style_profile_prompt': context.get('style_profile'),
            'quality': context.get('quality', 'standard'),
        }
    
    else:
        raise ValueError(f"Unknown handler name: {handler_name}")
