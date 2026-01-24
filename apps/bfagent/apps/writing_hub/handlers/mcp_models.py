"""
Pydantic Models for MCP Integration
Request/Response models for exposing handlers via MCP server
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# ============================================================================
# PHASE 1: CONCEPT & IDEA MODELS
# ============================================================================


class PremiseGeneratorRequest(BaseModel):
    """Request model for premise generation"""

    project_id: int = Field(..., description="BookProjects ID")
    title: Optional[str] = Field(None, description="Override project title")
    genre: Optional[str] = Field(None, description="Override project genre")
    inspiration: Optional[str] = Field(None, description="User's initial ideas or inspiration")
    target_length: Optional[str] = Field(
        "novel", description="Target length: short_story, novella, novel, series"
    )


class PremiseGeneratorResponse(BaseModel):
    """Response model for premise generation"""

    success: bool
    premise: Optional[str] = Field(None, description="Full 2-3 paragraph premise")
    premise_short: Optional[str] = Field(None, description="One sentence version")
    premise_elevator: Optional[str] = Field(None, description="30 second pitch")
    key_conflict: Optional[str] = Field(None, description="Central conflict")
    protagonist_sketch: Optional[str] = Field(None, description="Main character sketch")
    antagonist_sketch: Optional[str] = Field(None, description="Opposing force sketch")
    cost: Optional[float] = Field(None, description="LLM API cost in USD")
    error: Optional[str] = Field(None, description="Error message if failed")


class ThemeIdentifierRequest(BaseModel):
    """Request model for theme identification"""

    project_id: int = Field(..., description="BookProjects ID")
    premise: Optional[str] = Field(
        None, description="Story premise (uses project.premise if not provided)"
    )
    additional_context: Optional[str] = Field(
        None, description="Extra context for theme identification"
    )


class ThemeIdentifierResponse(BaseModel):
    """Response model for theme identification"""

    success: bool
    primary_theme: Optional[str] = Field(None, description="Main theme")
    secondary_themes: Optional[List[str]] = Field(None, description="Supporting themes")
    themes: Optional[List[Dict[str, str]]] = Field(None, description="Detailed theme analysis")
    cost: Optional[float] = Field(None, description="LLM API cost in USD")
    error: Optional[str] = Field(None, description="Error message if failed")


class LoglineGeneratorRequest(BaseModel):
    """Request model for logline generation"""

    project_id: int = Field(..., description="BookProjects ID")
    premise: Optional[str] = Field(None, description="Story premise")
    style: Optional[str] = Field(
        "concise", description="Style: concise, dramatic, mysterious, action"
    )


class LoglineGeneratorResponse(BaseModel):
    """Response model for logline generation"""

    success: bool
    logline: Optional[str] = Field(None, description="Main logline (one sentence, ~25 words)")
    logline_variations: Optional[List[str]] = Field(None, description="3 alternative versions")
    hook_analysis: Optional[str] = Field(None, description="What makes this logline compelling")
    cost: Optional[float] = Field(None, description="LLM API cost in USD")
    error: Optional[str] = Field(None, description="Error message if failed")


# ============================================================================
# PHASE 5: CHAPTER PLANNING MODELS
# ============================================================================


class ChapterStructureRequest(BaseModel):
    """Request model for chapter structure planning"""

    project_id: int = Field(..., description="BookProjects ID")
    chapter_number: int = Field(..., description="Which chapter to plan")
    outline: Optional[Dict[str, Any]] = Field(None, description="Story outline/beats")
    previous_chapters: Optional[List[Dict[str, Any]]] = Field(
        None, description="Previous chapter summaries"
    )


class ChapterStructureResponse(BaseModel):
    """Response model for chapter structure"""

    success: bool
    structure: Optional[Dict[str, str]] = Field(
        None, description="Opening, middle, ending, POV, setting, time"
    )
    scene_count: Optional[int] = Field(None, description="Recommended number of scenes")
    estimated_word_count: Optional[int] = Field(None, description="Target word count")
    chapter_number: Optional[int] = Field(None, description="Chapter number")
    cost: Optional[float] = Field(None, description="LLM API cost in USD")
    error: Optional[str] = Field(None, description="Error message if failed")


class ChapterHookRequest(BaseModel):
    """Request model for chapter hook generation"""

    project_id: int = Field(..., description="BookProjects ID")
    chapter_number: int = Field(..., description="Chapter number")
    chapter_structure: Optional[Dict[str, Any]] = Field(
        None, description="Chapter structure from ChapterStructureHandler"
    )
    hook_type: Optional[str] = Field(
        "action", description="Hook type: action, mystery, emotion, dialogue"
    )


class ChapterHookResponse(BaseModel):
    """Response model for chapter hook"""

    success: bool
    hook: Optional[str] = Field(None, description="Main hook (1-2 paragraphs, ~150 words)")
    hook_variations: Optional[List[str]] = Field(None, description="3 alternative hooks")
    hook_analysis: Optional[str] = Field(None, description="Why this hook is effective")
    opening_image: Optional[str] = Field(None, description="Visual description of opening")
    chapter_number: Optional[int] = Field(None, description="Chapter number")
    cost: Optional[float] = Field(None, description="LLM API cost in USD")
    error: Optional[str] = Field(None, description="Error message if failed")


class ChapterGoalRequest(BaseModel):
    """Request model for chapter goal definition"""

    project_id: int = Field(..., description="BookProjects ID")
    chapter_number: int = Field(..., description="Chapter number")
    chapter_structure: Optional[Dict[str, Any]] = Field(None, description="Chapter structure")
    story_goal: Optional[str] = Field(None, description="Overall story objective")


class ChapterGoalResponse(BaseModel):
    """Response model for chapter goal"""

    success: bool
    chapter_goal: Optional[str] = Field(None, description="What must be accomplished")
    plot_progression: Optional[str] = Field(None, description="How story advances")
    character_development: Optional[str] = Field(None, description="How characters change")
    conflicts: Optional[List[str]] = Field(None, description="Conflicts in this chapter")
    stakes: Optional[str] = Field(None, description="What's at risk")
    next_chapter_setup: Optional[str] = Field(None, description="What this sets up")
    chapter_number: Optional[int] = Field(None, description="Chapter number")
    cost: Optional[float] = Field(None, description="LLM API cost in USD")
    error: Optional[str] = Field(None, description="Error message if failed")


# ============================================================================
# PHASE 6: QUALITY FEEDBACK MODELS
# ============================================================================


class ChapterReviewRequest(BaseModel):
    """Request model for chapter review"""

    chapter_id: int = Field(..., description="BookChapters ID")
    review_type: Optional[str] = Field(
        "standard", description="Review depth: quick, standard, deep"
    )
    focus_areas: Optional[List[str]] = Field(
        ["structure", "prose", "dialogue", "pacing"],
        description="Areas to focus on: structure, prose, dialogue, pacing, consistency",
    )


class ReviewSuggestion(BaseModel):
    """Individual review suggestion"""

    issue: str = Field(..., description="Specific problem identified")
    location: str = Field(..., description="Where in chapter")
    severity: str = Field(..., description="Severity: low, medium, high")
    fix: str = Field(..., description="How to fix the issue")


class ChapterReviewResponse(BaseModel):
    """Response model for chapter review"""

    success: bool
    overall_score: Optional[int] = Field(None, description="Overall quality score 1-10")
    strengths: Optional[List[str]] = Field(None, description="What works well")
    weaknesses: Optional[List[str]] = Field(None, description="Areas for improvement")
    suggestions: Optional[List[ReviewSuggestion]] = Field(
        None, description="Actionable suggestions"
    )
    detailed_feedback: Optional[Dict[str, str]] = Field(
        None, description="Detailed area-specific feedback"
    )
    chapter_id: Optional[int] = Field(None, description="Chapter ID reviewed")
    review_type: Optional[str] = Field(None, description="Type of review performed")
    cost: Optional[float] = Field(None, description="LLM API cost in USD")
    error: Optional[str] = Field(None, description="Error message if failed")
