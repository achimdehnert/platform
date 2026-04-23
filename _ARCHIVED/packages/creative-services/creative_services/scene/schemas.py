"""Schemas for scene analysis."""

from typing import Optional
from pydantic import BaseModel, Field


class Scene(BaseModel):
    """An extracted scene suitable for illustration."""
    
    title: str = Field(..., description="Scene title")
    description: str = Field(..., description="Scene description")
    
    # Location & Setting
    location: str = Field(default="", description="Where the scene takes place")
    time_of_day: Optional[str] = Field(default=None, description="Time of day")
    weather: Optional[str] = Field(default=None, description="Weather/atmosphere")
    
    # Characters
    characters: list[str] = Field(default_factory=list, description="Characters present")
    character_actions: list[str] = Field(default_factory=list, description="What characters are doing")
    
    # Mood & Emotion
    mood: str = Field(default="neutral", description="Emotional mood of scene")
    tension_level: Optional[str] = Field(default=None, description="low/medium/high")
    
    # Visual Elements
    key_visual_elements: list[str] = Field(default_factory=list, description="Important visual elements")
    colors: list[str] = Field(default_factory=list, description="Dominant colors")
    lighting: Optional[str] = Field(default=None, description="Lighting description")
    
    # For Illustration
    illustration_prompt: str = Field(default="", description="Detailed prompt for image generation")
    style_suggestions: list[str] = Field(default_factory=list, description="Art style suggestions")
    
    # Metadata
    text_excerpt: Optional[str] = Field(default=None, description="Original text excerpt")
    importance_score: float = Field(default=0.5, ge=0, le=1, description="How important for illustration")


class SceneAnalysisResult(BaseModel):
    """Result of scene analysis."""
    
    scenes: list[Scene] = Field(default_factory=list, description="Extracted scenes")
    best_scene_index: int = Field(default=0, description="Index of best scene for illustration")
    analysis_notes: Optional[str] = None
