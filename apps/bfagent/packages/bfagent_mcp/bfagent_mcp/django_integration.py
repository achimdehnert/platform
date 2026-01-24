"""
BF Agent MCP Server - Django ORM Integration
=============================================

Provides Django ORM support for repositories.

This module:
- Initializes Django if not already configured
- Provides Model → DTO conversion
- Implements async database queries via sync_to_async
- Handles connection management

Usage:
    from bfagent_mcp.django_integration import (
        ensure_django_setup,
        get_domain_model,
        model_to_dto,
    )
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, TypeVar

from ..core import (
    DomainDTO,
    PhaseDTO,
    HandlerDTO,
    TagDTO,
    DomainStatus,
    HandlerType,
    AIProvider,
)

logger = logging.getLogger(__name__)

# Type variable for generic model conversion
T = TypeVar('T')

# Flag to track Django initialization
_django_initialized = False


# =============================================================================
# DJANGO SETUP
# =============================================================================

def ensure_django_setup() -> bool:
    """
    Ensure Django is properly configured.
    
    Returns:
        True if Django is ready, False otherwise
    """
    global _django_initialized
    
    if _django_initialized:
        return True
    
    # Check if Django is already configured
    try:
        import django
        from django.conf import settings
        
        if settings.configured:
            _django_initialized = True
            logger.info("Django already configured")
            return True
    except ImportError:
        logger.warning("Django not installed")
        return False
    except Exception as e:
        logger.warning(f"Django check failed: {e}")
    
    # Try to configure Django
    settings_module = os.environ.get(
        'DJANGO_SETTINGS_MODULE',
        'config.settings'
    )
    
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)
        django.setup()
        _django_initialized = True
        logger.info(f"Django configured with {settings_module}")
        return True
    except Exception as e:
        logger.error(f"Failed to setup Django: {e}")
        return False


def is_django_available() -> bool:
    """Check if Django is available and configured."""
    return _django_initialized or ensure_django_setup()


# =============================================================================
# MODEL IMPORTS (Lazy)
# =============================================================================

@lru_cache()
def get_domain_model():
    """Get Domain model class (lazy import)."""
    ensure_django_setup()
    from bfagent_mcp.models import Domain
    return Domain


@lru_cache()
def get_phase_model():
    """Get Phase model class (lazy import)."""
    ensure_django_setup()
    from bfagent_mcp.models import Phase
    return Phase


@lru_cache()
def get_handler_model():
    """Get Handler model class (lazy import)."""
    ensure_django_setup()
    from bfagent_mcp.models import Handler
    return Handler


@lru_cache()
def get_tag_model():
    """Get Tag model class (lazy import)."""
    ensure_django_setup()
    from bfagent_mcp.models import Tag
    return Tag


@lru_cache()
def get_best_practice_model():
    """Get BestPractice model class (lazy import)."""
    ensure_django_setup()
    from bfagent_mcp.models import BestPractice
    return BestPractice


# =============================================================================
# MODEL → DTO CONVERTERS
# =============================================================================

def domain_to_dto(domain) -> DomainDTO:
    """
    Convert Django Domain model to DomainDTO.
    
    Args:
        domain: Django Domain model instance
        
    Returns:
        DomainDTO with all fields
    """
    return DomainDTO(
        id=domain.id,
        domain_id=domain.domain_id,
        display_name=domain.display_name,
        description=domain.description,
        status=DomainStatus(domain.status),
        icon=domain.icon,
        color=domain.color,
        created_at=domain.created_at,
        updated_at=domain.updated_at,
    )


def phase_to_dto(phase) -> PhaseDTO:
    """
    Convert Django Phase model to PhaseDTO.
    
    Args:
        phase: Django Phase model instance
        
    Returns:
        PhaseDTO with all fields
    """
    return PhaseDTO(
        id=phase.id,
        name=phase.name,
        display_name=phase.display_name,
        order=phase.order,
        description=phase.description or "",
        color=phase.color,
        icon=phase.icon,
        estimated_duration_seconds=phase.estimated_duration_seconds,
    )


def handler_to_dto(handler) -> HandlerDTO:
    """
    Convert Django Handler model to HandlerDTO.
    
    Args:
        handler: Django Handler model instance
        
    Returns:
        HandlerDTO with all fields
    """
    # Get tags as list of names
    tags = []
    if hasattr(handler, 'tags'):
        try:
            tags = list(handler.tags.values_list('name', flat=True))
        except Exception:
            pass
    
    return HandlerDTO(
        id=handler.id,
        name=handler.name,
        domain_id=handler.domain.domain_id if handler.domain else "",
        handler_type=HandlerType(handler.handler_type),
        description=handler.description,
        ai_provider=AIProvider(handler.ai_provider) if handler.ai_provider else AIProvider.NONE,
        estimated_duration_seconds=handler.estimated_duration_seconds,
        is_active=handler.is_active,
        version=handler.version,
        input_schema=handler.input_schema or {},
        output_schema=handler.output_schema or {},
        tags=tags,
    )


def tag_to_dto(tag) -> TagDTO:
    """
    Convert Django Tag model to TagDTO.
    
    Args:
        tag: Django Tag model instance
        
    Returns:
        TagDTO with all fields
    """
    return TagDTO(
        id=tag.id,
        name=tag.name,
        category=tag.category,
        description=tag.description or "",
    )


# =============================================================================
# ASYNC DATABASE ACCESS (sync_to_async wrappers)
# =============================================================================

async def async_get_all_domains(
    status_filter: Optional[DomainStatus] = None,
    limit: int = 20,
    offset: int = 0,
) -> List[DomainDTO]:
    """
    Get all domains asynchronously.
    
    Args:
        status_filter: Optional status filter
        limit: Maximum results
        offset: Pagination offset
        
    Returns:
        List of DomainDTO
    """
    from asgiref.sync import sync_to_async
    
    @sync_to_async
    def _query():
        Domain = get_domain_model()
        queryset = Domain.objects.filter(is_active=True)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter.value)
        
        queryset = queryset.order_by('display_name')[offset:offset + limit]
        return [domain_to_dto(d) for d in queryset]
    
    return await _query()


async def async_get_domain_by_id(domain_id: str) -> Optional[DomainDTO]:
    """
    Get domain by domain_id asynchronously.
    
    Args:
        domain_id: Domain identifier
        
    Returns:
        DomainDTO or None
    """
    from asgiref.sync import sync_to_async
    
    @sync_to_async
    def _query():
        Domain = get_domain_model()
        try:
            domain = Domain.objects.get(domain_id=domain_id, is_active=True)
            return domain_to_dto(domain)
        except Domain.DoesNotExist:
            return None
    
    return await _query()


async def async_get_domain_with_details(domain_id: str) -> Optional[Dict[str, Any]]:
    """
    Get domain with all related data.
    
    Args:
        domain_id: Domain identifier
        
    Returns:
        Dict with domain, phases, handlers, tags
    """
    from asgiref.sync import sync_to_async
    
    @sync_to_async
    def _query():
        Domain = get_domain_model()
        Phase = get_phase_model()
        Handler = get_handler_model()
        
        try:
            domain = Domain.objects.prefetch_related('tags').get(
                domain_id=domain_id, 
                is_active=True
            )
        except Domain.DoesNotExist:
            return None
        
        phases = Phase.objects.filter(domain=domain).order_by('order')
        handlers = Handler.objects.filter(
            domain=domain, 
            is_active=True
        ).prefetch_related('tags')
        
        return {
            "domain": domain_to_dto(domain),
            "phases": [phase_to_dto(p) for p in phases],
            "handlers": [handler_to_dto(h) for h in handlers],
            "tags": [tag_to_dto(t) for t in domain.tags.all()],
            "handler_count": handlers.count(),
            "phase_count": phases.count(),
        }
    
    return await _query()


async def async_count_domains(status_filter: Optional[DomainStatus] = None) -> int:
    """Count domains."""
    from asgiref.sync import sync_to_async
    
    @sync_to_async
    def _query():
        Domain = get_domain_model()
        queryset = Domain.objects.filter(is_active=True)
        if status_filter:
            queryset = queryset.filter(status=status_filter.value)
        return queryset.count()
    
    return await _query()


async def async_get_phases_by_domain(domain_id: str) -> List[PhaseDTO]:
    """Get phases for a domain."""
    from asgiref.sync import sync_to_async
    
    @sync_to_async
    def _query():
        Phase = get_phase_model()
        Domain = get_domain_model()
        
        try:
            domain = Domain.objects.get(domain_id=domain_id)
        except Domain.DoesNotExist:
            return []
        
        phases = Phase.objects.filter(domain=domain).order_by('order')
        return [phase_to_dto(p) for p in phases]
    
    return await _query()


async def async_get_handlers_by_domain(
    domain_id: str,
    include_inactive: bool = False,
) -> List[HandlerDTO]:
    """Get handlers for a domain."""
    from asgiref.sync import sync_to_async
    
    @sync_to_async
    def _query():
        Handler = get_handler_model()
        Domain = get_domain_model()
        
        try:
            domain = Domain.objects.get(domain_id=domain_id)
        except Domain.DoesNotExist:
            return []
        
        queryset = Handler.objects.filter(domain=domain).prefetch_related('tags')
        if not include_inactive:
            queryset = queryset.filter(is_active=True)
        
        return [handler_to_dto(h) for h in queryset]
    
    return await _query()


async def async_search_handlers(
    query: str,
    domain_filter: Optional[str] = None,
    handler_type_filter: Optional[HandlerType] = None,
    tags_filter: Optional[List[str]] = None,
    limit: int = 10,
) -> List[tuple]:
    """
    Search handlers with relevance scoring.
    
    Returns:
        List of (HandlerDTO, score) tuples
    """
    from asgiref.sync import sync_to_async
    from django.db.models import Q, Value, F
    from django.db.models.functions import Concat
    
    @sync_to_async
    def _query():
        Handler = get_handler_model()
        
        queryset = Handler.objects.filter(is_active=True).prefetch_related('tags', 'domain')
        
        # Apply filters
        if domain_filter:
            queryset = queryset.filter(domain__domain_id=domain_filter)
        
        if handler_type_filter:
            queryset = queryset.filter(handler_type=handler_type_filter.value)
        
        if tags_filter:
            queryset = queryset.filter(tags__name__in=tags_filter).distinct()
        
        # Search in name and description
        search_q = Q(name__icontains=query) | Q(description__icontains=query)
        queryset = queryset.filter(search_q)
        
        results = []
        query_lower = query.lower()
        
        for handler in queryset[:limit]:
            # Calculate relevance score
            score = 0.0
            
            # Name match (highest weight)
            if query_lower in handler.name.lower():
                score += 3.0
                if handler.name.lower().startswith(query_lower):
                    score += 1.0
            
            # Description match
            if query_lower in handler.description.lower():
                score += 1.0
            
            # Tag match
            handler_tags = [t.name.lower() for t in handler.tags.all()]
            if query_lower in handler_tags:
                score += 2.0
            
            results.append((handler_to_dto(handler), score))
        
        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results
    
    return await _query()


async def async_get_handler_by_id(handler_id: int) -> Optional[HandlerDTO]:
    """Get handler by ID."""
    from asgiref.sync import sync_to_async
    
    @sync_to_async
    def _query():
        Handler = get_handler_model()
        try:
            handler = Handler.objects.prefetch_related('tags', 'domain').get(id=handler_id)
            return handler_to_dto(handler)
        except Handler.DoesNotExist:
            return None
    
    return await _query()


async def async_count_handlers(domain_id: Optional[str] = None) -> int:
    """Count handlers."""
    from asgiref.sync import sync_to_async
    
    @sync_to_async
    def _query():
        Handler = get_handler_model()
        queryset = Handler.objects.filter(is_active=True)
        if domain_id:
            queryset = queryset.filter(domain__domain_id=domain_id)
        return queryset.count()
    
    return await _query()


async def async_get_all_tags() -> List[TagDTO]:
    """Get all tags."""
    from asgiref.sync import sync_to_async
    
    @sync_to_async
    def _query():
        Tag = get_tag_model()
        return [tag_to_dto(t) for t in Tag.objects.all()]
    
    return await _query()


async def async_get_best_practice(topic: str) -> Optional[Dict[str, Any]]:
    """Get best practice by topic."""
    from asgiref.sync import sync_to_async
    
    @sync_to_async
    def _query():
        BestPractice = get_best_practice_model()
        try:
            bp = BestPractice.objects.prefetch_related('related_topics').get(
                topic=topic,
                is_active=True
            )
            return {
                "topic": bp.topic,
                "display_name": bp.display_name,
                "content": bp.content,
                "related_topics": [r.topic for r in bp.related_topics.all()],
            }
        except BestPractice.DoesNotExist:
            return None
    
    return await _query()


async def async_get_all_best_practice_topics() -> List[str]:
    """Get all best practice topics."""
    from asgiref.sync import sync_to_async
    
    @sync_to_async
    def _query():
        BestPractice = get_best_practice_model()
        return list(
            BestPractice.objects.filter(is_active=True)
            .order_by('order')
            .values_list('topic', flat=True)
        )
    
    return await _query()


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Setup
    "ensure_django_setup",
    "is_django_available",
    # Model getters
    "get_domain_model",
    "get_phase_model",
    "get_handler_model",
    "get_tag_model",
    "get_best_practice_model",
    # Converters
    "domain_to_dto",
    "phase_to_dto",
    "handler_to_dto",
    "tag_to_dto",
    # Async queries
    "async_get_all_domains",
    "async_get_domain_by_id",
    "async_get_domain_with_details",
    "async_count_domains",
    "async_get_phases_by_domain",
    "async_get_handlers_by_domain",
    "async_search_handlers",
    "async_get_handler_by_id",
    "async_count_handlers",
    "async_get_all_tags",
    "async_get_best_practice",
    "async_get_all_best_practice_topics",
]
