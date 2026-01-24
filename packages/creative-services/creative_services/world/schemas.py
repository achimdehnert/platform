"""Schemas for world and location generation."""

from typing import Optional
from pydantic import BaseModel, Field


class World(BaseModel):
    """Generated fictional world data."""
    
    name: str = Field(..., description="World name")
    description: str = Field(..., description="Overall world description")
    
    # Geography
    geography: str = Field(default="", description="Geographic description")
    climate: Optional[str] = Field(default=None, description="Climate description")
    regions: list[dict] = Field(default_factory=list, description="Major regions")
    
    # Culture & Society
    cultures: list[dict] = Field(default_factory=list, description="Major cultures")
    languages: list[str] = Field(default_factory=list, description="Languages spoken")
    religions: list[dict] = Field(default_factory=list, description="Religions/belief systems")
    social_structure: Optional[str] = Field(default=None, description="Social hierarchy")
    
    # History
    history_summary: str = Field(default="", description="Historical overview")
    key_events: list[dict] = Field(default_factory=list, description="Major historical events")
    
    # Magic/Technology
    magic_system: Optional[str] = Field(default=None, description="Magic system if applicable")
    technology_level: Optional[str] = Field(default=None, description="Technology level")
    
    # Story opportunities
    conflicts: list[str] = Field(default_factory=list, description="Ongoing conflicts")
    mysteries: list[str] = Field(default_factory=list, description="Unsolved mysteries")
    story_hooks: list[str] = Field(default_factory=list, description="Potential story hooks")


class Location(BaseModel):
    """Real-world location profile for travel stories."""
    
    name: str = Field(..., description="Location name")
    country: Optional[str] = Field(default=None, description="Country")
    region: Optional[str] = Field(default=None, description="Region/state")
    
    # Description
    description: str = Field(..., description="Overall location description")
    atmosphere: str = Field(default="", description="Atmosphere and vibe")
    
    # Highlights
    highlights: list[str] = Field(default_factory=list, description="Must-see attractions")
    hidden_gems: list[str] = Field(default_factory=list, description="Lesser-known spots")
    
    # Culture
    local_culture: str = Field(default="", description="Local culture description")
    customs: list[str] = Field(default_factory=list, description="Local customs to know")
    local_phrases: list[dict] = Field(default_factory=list, description="Useful local phrases")
    
    # Food
    culinary_highlights: list[dict] = Field(default_factory=list, description="Must-try foods")
    restaurant_types: list[str] = Field(default_factory=list, description="Types of eateries")
    
    # Activities
    activities: list[dict] = Field(default_factory=list, description="Suggested activities")
    best_time_to_visit: Optional[str] = Field(default=None, description="Best season/time")
    
    # Story opportunities
    story_opportunities: list[str] = Field(default_factory=list, description="Potential story moments")
    character_encounters: list[str] = Field(default_factory=list, description="Possible character meetings")
    
    # For illustration
    visual_elements: list[str] = Field(default_factory=list, description="Key visual elements")
    illustration_prompts: list[str] = Field(default_factory=list, description="Scene prompts")


class WorldResult(BaseModel):
    """Result of world generation."""
    
    world: World
    generation_notes: Optional[str] = None


class LocationResult(BaseModel):
    """Result of location profile generation."""
    
    location: Location
    generation_notes: Optional[str] = None
