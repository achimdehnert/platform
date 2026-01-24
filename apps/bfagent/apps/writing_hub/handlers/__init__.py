"""
Writing Hub Handlers
Organized handlers for bookwriting workflow
"""

# Phase 5: Chapter Breakdown
from .chapter_planning_handlers import (
    ChapterGoalHandler,
    ChapterHookHandler,
    ChapterStructureHandler,
)

# Phase 6: Quality Feedback
from .chapter_review_handler import ChapterReviewHandler, review_chapter

# LLM Handler for Content Types
from .writing_llm_handler import WritingLLMHandler, generate_content

# Phase 1: Konzept & Idee
from .concept_handlers import (
    LoglineGeneratorHandler,
    PremiseGeneratorHandler,
    ThemeIdentifierHandler,
)

# Planning Handler (mit LLM)
from .planning_handler import PlanningGenerationHandler, PlanningContext, planning_handler

# Character Handler (mit LLM)
from .character_handler import CharacterGenerationHandler, CharacterContext, character_handler

# Outline Handler (mit LLM)
from .outline_handler import OutlineGenerationHandler, OutlineContext, outline_handler

# Chapter Writer Handler (mit LLM)
from .chapter_writer_handler import ChapterWriterHandler, ChapterContext, chapter_writer_handler

# Phase 4: Storyline & Outline (Enhanced)
from .enhanced_outline_handlers import (
    EnhancedSaveTheCatOutlineHandler,
    HerosJourneyOutlineHandler,
    KishotenketsuOutlineHandler,
    SevenPointOutlineHandler,
    ThreeActOutlineHandler,
)

__all__ = [
    # Phase 1
    "PremiseGeneratorHandler",
    "ThemeIdentifierHandler",
    "LoglineGeneratorHandler",
    # Planning Handler
    "PlanningGenerationHandler",
    "PlanningContext",
    "planning_handler",
    # Character Handler
    "CharacterGenerationHandler",
    "CharacterContext",
    "character_handler",
    # Outline Handler
    "OutlineGenerationHandler",
    "OutlineContext",
    "outline_handler",
    # Chapter Writer Handler
    "ChapterWriterHandler",
    "ChapterContext",
    "chapter_writer_handler",
    # Phase 4
    "EnhancedSaveTheCatOutlineHandler",
    "HerosJourneyOutlineHandler",
    "KishotenketsuOutlineHandler",
    "SevenPointOutlineHandler",
    "ThreeActOutlineHandler",
    # Phase 5
    "ChapterStructureHandler",
    "ChapterHookHandler",
    "ChapterGoalHandler",
    # Phase 6
    "ChapterReviewHandler",
    "review_chapter",
    # LLM Handler
    "WritingLLMHandler",
    "generate_content",
]
