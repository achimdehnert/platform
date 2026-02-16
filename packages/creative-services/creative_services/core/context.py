"""Base context classes for creative services."""

from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class BaseContext(BaseModel):
    """Base context for all creative service operations."""

    model_config = ConfigDict(extra="allow")

    genre: Optional[str] = Field(default=None, description="Genre (fantasy, sci-fi, romance, travel, etc.)")
    tone: Optional[str] = Field(default=None, description="Tone (serious, humorous, dramatic, etc.)")
    language: str = Field(default="en", description="Output language code")
    style_notes: Optional[str] = Field(default=None, description="Additional style guidance")


class CharacterContext(BaseContext):
    """Context for character generation."""
    
    role: str = Field(default="protagonist", description="Character role in story")
    traits: list[str] = Field(default_factory=list, description="Personality traits")
    age_range: Optional[str] = Field(default=None, description="Age range (child, teen, adult, elder)")
    gender: Optional[str] = Field(default=None, description="Gender if specified")
    occupation: Optional[str] = Field(default=None, description="Occupation or role")
    backstory_hints: Optional[str] = Field(default=None, description="Backstory elements to include")


class WorldContext(BaseContext):
    """Context for world/location generation."""
    
    world_type: str = Field(default="fantasy", description="Type: fantasy, sci-fi, historical, real-world")
    scale: str = Field(default="region", description="Scale: city, region, continent, planet")
    time_period: Optional[str] = Field(default=None, description="Time period or era")
    climate: Optional[str] = Field(default=None, description="Climate type")
    culture_notes: Optional[str] = Field(default=None, description="Cultural elements to include")


class LocationContext(BaseContext):
    """Context for real-world location profiles (Travel Beat)."""
    
    location_name: str = Field(..., description="Name of the location")
    country: Optional[str] = Field(default=None, description="Country")
    region: Optional[str] = Field(default=None, description="Region or state")
    season: Optional[str] = Field(default=None, description="Season for the visit")
    include_food: bool = Field(default=True, description="Include culinary highlights")
    include_culture: bool = Field(default=True, description="Include cultural details")
    include_activities: bool = Field(default=True, description="Include suggested activities")


class StoryContext(BaseContext):
    """Context for story/chapter generation."""
    
    title: Optional[str] = Field(default=None, description="Story or chapter title")
    premise: Optional[str] = Field(default=None, description="Story premise or logline")
    characters: list[dict[str, Any]] = Field(default_factory=list, description="Character summaries")
    world_summary: Optional[str] = Field(default=None, description="World/setting summary")
    previous_summary: Optional[str] = Field(default=None, description="Summary of previous content")
    target_word_count: int = Field(default=1500, description="Target word count")
    chapter_number: Optional[int] = Field(default=None, description="Chapter number if applicable")


class SceneContext(BaseContext):
    """Context for scene analysis."""
    
    text: str = Field(..., description="Text to analyze for scenes")
    max_scenes: int = Field(default=3, description="Maximum scenes to extract")
    characters: list[str] = Field(default_factory=list, description="Known character names")
    locations: list[str] = Field(default_factory=list, description="Known location names")
    for_illustration: bool = Field(default=True, description="Optimize for illustration prompts")
