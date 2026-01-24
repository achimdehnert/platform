"""
Chapter Data Input Handler

Collects chapter information for context building in AI actions.
"""

from typing import Any, Dict, List
import structlog

from ..base.input import BaseInputHandler
from ..exceptions import InputHandlerException
from ..decorators import with_logging, with_performance_monitoring
from ..schemas import ChapterDataConfig

logger = structlog.get_logger()


class ChapterDataHandler(BaseInputHandler):
    """
    Collect chapter data for context building.
    
    Useful for actions that need chapter context like:
    - Generating subsequent chapters
    - Analyzing story progression
    - Creating character arcs
    - World-building consistency
    
    Configuration:
        include_outline (bool): Include chapter outlines. Defaults to False.
        include_characters (bool): Include featured characters. Defaults to False.
        include_content (bool): Include chapter content. Defaults to False.
        include_ai_content (bool): Include AI-generated content. Defaults to False.
        chapter_ids (list, optional): Specific chapter IDs to include
        limit (int, optional): Maximum number of chapters to return
        order_by (str): Sort order. Defaults to "chapter_number"
    
    Input Context:
        project (BookProjects): Required
    
    Returns:
        Dict with keys:
            - chapters (list): List of chapter data dicts
            - chapter_count (int): Total number of chapters
            - total_word_count (int): Combined word count
    
    Example:
        >>> handler = ChapterDataHandler({
        ...     "include_outline": True,
        ...     "include_characters": True,
        ...     "limit": 5
        ... })
        >>> result = handler.collect(context)
        >>> # {
        >>> #   "chapters": [...],
        >>> #   "chapter_count": 5,
        >>> #   "total_word_count": 15000
        >>> # }
    """
    
    handler_name = "chapter_data"
    handler_version = "1.0.0"
    description = "Collects chapter information for AI context"
    
    def validate_config(self) -> None:
        """Validate configuration using Pydantic."""
        try:
            ChapterDataConfig(**self.config)
        except Exception as e:
            raise InputHandlerException(
                message="Invalid configuration for ChapterDataHandler",
                handler_name=self.handler_name,
                context={"config": self.config, "error": str(e)}
            )
    
    @with_logging
    @with_performance_monitoring
    def collect(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect chapter information.
        
        Args:
            context: Runtime context with project
            
        Returns:
            Dictionary with chapter data
        """
        project = context.get("project")
        if not project:
            raise ValueError("Context missing 'project'")
        
        # Get configuration
        include_outline = self.config.get("include_outline", False)
        include_characters = self.config.get("include_characters", False)
        include_content = self.config.get("include_content", False)
        include_ai_content = self.config.get("include_ai_content", False)
        chapter_ids = self.config.get("chapter_ids")
        limit = self.config.get("limit")
        order_by = self.config.get("order_by", "chapter_number")
        
        # Query chapters
        chapters_qs = project.book_chapters.all()
        
        if chapter_ids:
            chapters_qs = chapters_qs.filter(id__in=chapter_ids)
        
        chapters_qs = chapters_qs.order_by(order_by)
        
        if limit:
            chapters_qs = chapters_qs[:limit]
        
        # Collect chapter data
        result = {
            "chapters": [],
            "chapter_count": 0,
            "total_word_count": 0
        }
        
        for chapter in chapters_qs:
            chapter_data = {
                "id": chapter.id,
                "number": chapter.chapter_number,
                "title": chapter.title,
                "word_count": chapter.word_count or 0,
                "status": chapter.status or "draft"
            }
            
            # Optional fields
            if include_outline and chapter.outline:
                chapter_data["outline"] = chapter.outline
            
            if include_content and chapter.content:
                chapter_data["content"] = chapter.content
            
            if include_ai_content and chapter.ai_content:
                chapter_data["ai_content"] = chapter.ai_content
            
            if include_characters:
                chapter_data["characters"] = list(
                    chapter.featured_characters.values_list("name", flat=True)
                )
            
            result["chapters"].append(chapter_data)
            result["total_word_count"] += chapter_data["word_count"]
        
        result["chapter_count"] = len(result["chapters"])
        
        return result
