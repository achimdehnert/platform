"""
Chapter Analyzer Service
========================

Analyzes chapter content using LLM to extract visual scenes for illustration.
Uses the SceneAnalyzerHandler for actual analysis and provides caching/persistence.

Usage:
    service = ChapterAnalyzerService()
    analysis = service.analyze_chapter(chapter)
    best_scene = analysis.get_best_scene()
"""

import logging
from typing import Optional, List

from apps.bfagent.models import BookChapters
from apps.writing_hub.models import ChapterSceneAnalysis
from apps.writing_hub.handlers.scene_analyzer_handler import SceneAnalyzerHandler

logger = logging.getLogger(__name__)


class ChapterAnalyzerService:
    """
    Service for analyzing chapter content and extracting visual scenes.
    
    Uses SceneAnalyzerHandler for LLM-based analysis and provides
    caching through the ChapterSceneAnalysis model.
    """
    
    def __init__(self, llm_id=None):
        """
        Initialize the analyzer service.
        
        Args:
            llm_id: LLM ID or None (auto-select)
        """
        self.handler = SceneAnalyzerHandler(llm_id=llm_id)
    
    def analyze_chapter(
        self, 
        chapter: BookChapters,
        force_reanalyze: bool = False
    ) -> ChapterSceneAnalysis:
        """
        Analyze a chapter and extract visual scenes.
        
        Args:
            chapter: The chapter to analyze
            force_reanalyze: If True, ignore cached analysis
            
        Returns:
            ChapterSceneAnalysis with extracted scenes
            
        Raises:
            ValueError: If analysis fails (no LLM available, etc.)
        """
        # Check for existing valid analysis (only if it has enough scenes)
        if not force_reanalyze:
            existing = self._get_cached_analysis(chapter)
            if existing and existing.is_valid() and len(existing.scenes) >= 2:
                logger.info(f"Using cached analysis for chapter {chapter.id} ({len(existing.scenes)} scenes)")
                return existing
            elif existing and len(existing.scenes) < 2:
                logger.info(f"Cached analysis has only {len(existing.scenes)} scene(s), re-analyzing chapter {chapter.id}")
        
        # Validate chapter has content
        if not chapter.content or len(chapter.content) < 100:
            raise ValueError(f"Kapitel {chapter.id} hat nicht genug Inhalt für Analyse (min. 100 Zeichen)")
        
        # Perform LLM analysis using handler
        result = self.handler.analyze_chapter(chapter.id)
        
        if not result.get('success'):
            raise ValueError(result.get('error') or "Analyse fehlgeschlagen")
        
        # Save to database
        return self._save_analysis(chapter, result)
    
    def get_or_create_analysis(
        self, 
        chapter: BookChapters
    ) -> ChapterSceneAnalysis:
        """
        Get existing analysis or create new one if needed.
        
        Args:
            chapter: The chapter to get analysis for
            
        Returns:
            ChapterSceneAnalysis (cached or newly created)
        """
        existing = self._get_cached_analysis(chapter)
        
        if existing:
            if existing.is_valid():
                return existing
            else:
                # Content changed, re-analyze
                logger.info(f"Chapter {chapter.id} content changed, re-analyzing")
                return self.analyze_chapter(chapter, force_reanalyze=True)
        
        return self.analyze_chapter(chapter)
    
    def invalidate_analysis(self, chapter: BookChapters) -> bool:
        """
        Invalidate cached analysis for a chapter.
        
        Args:
            chapter: The chapter to invalidate
            
        Returns:
            True if analysis was deleted, False if none existed
        """
        try:
            analysis = ChapterSceneAnalysis.objects.get(chapter=chapter)
            analysis.delete()
            logger.info(f"Invalidated analysis for chapter {chapter.id}")
            return True
        except ChapterSceneAnalysis.DoesNotExist:
            return False
    
    def _get_cached_analysis(
        self, 
        chapter: BookChapters
    ) -> Optional[ChapterSceneAnalysis]:
        """Get existing analysis if available."""
        try:
            return ChapterSceneAnalysis.objects.get(chapter=chapter)
        except ChapterSceneAnalysis.DoesNotExist:
            return None
    
    def _save_analysis(
        self, 
        chapter: BookChapters, 
        result: dict
    ) -> ChapterSceneAnalysis:
        """Save analysis result from handler to database."""
        content_hash = ChapterSceneAnalysis.compute_content_hash(
            chapter.content or ''
        )
        
        scenes_data = result.get('scenes', [])
        logger.info(f"Saving {len(scenes_data)} scenes for chapter {chapter.id}")
        logger.debug(f"Scenes to save: {scenes_data}")
        
        analysis, created = ChapterSceneAnalysis.objects.update_or_create(
            chapter=chapter,
            defaults={
                'scenes': scenes_data,
                'best_scene_index': result.get('best_scene_index', 0),
                'best_scene_reason': result.get('best_scene_reason', ''),
                'overall_color_mood': result.get('color_mood', ''),
                'chapter_atmosphere': result.get('atmosphere', ''),
                'analysis_model': 'handler',
                'analysis_tokens_used': result.get('tokens_used', 0),
                'content_hash': content_hash,
            }
        )
        
        # Verify save
        analysis.refresh_from_db()
        logger.info(f"After save: analysis.scenes has {len(analysis.scenes)} scenes, type: {type(analysis.scenes)}")
        
        action = "Created" if created else "Updated"
        logger.info(f"{action} analysis for chapter {chapter.id}")
        
        return analysis


# Convenience function for simple usage
def analyze_chapter_for_illustration(
    chapter_id: int,
    force: bool = False
) -> ChapterSceneAnalysis:
    """
    Convenience function to analyze a chapter by ID.
    
    Args:
        chapter_id: ID of the chapter to analyze
        force: Force re-analysis even if cached
        
    Returns:
        ChapterSceneAnalysis with scene data
        
    Raises:
        ValueError: If analysis fails
    """
    chapter = BookChapters.objects.get(id=chapter_id)
    service = ChapterAnalyzerService()
    return service.analyze_chapter(chapter, force_reanalyze=force)
