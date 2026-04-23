"""Schemas for character generation."""

from typing import Optional
from pydantic import BaseModel, Field


class Character(BaseModel):
    """Generated character data."""
    
    name: str = Field(..., description="Character's full name")
    age: Optional[int] = Field(default=None, description="Character's age")
    gender: Optional[str] = Field(default=None, description="Character's gender")
    role: str = Field(default="supporting", description="Role in story")
    
    # Personality
    personality: str = Field(..., description="Personality description")
    traits: list[str] = Field(default_factory=list, description="Key personality traits")
    strengths: list[str] = Field(default_factory=list, description="Character strengths")
    weaknesses: list[str] = Field(default_factory=list, description="Character flaws/weaknesses")
    
    # Background
    backstory: str = Field(default="", description="Character backstory")
    motivation: str = Field(default="", description="Core motivation")
    goals: list[str] = Field(default_factory=list, description="Character goals")
    fears: list[str] = Field(default_factory=list, description="Character fears")
    
    # Appearance
    appearance: str = Field(default="", description="Physical appearance description")
    distinctive_features: list[str] = Field(default_factory=list, description="Notable features")
    
    # Speech & Behavior
    speech_pattern: Optional[str] = Field(default=None, description="How they speak")
    mannerisms: list[str] = Field(default_factory=list, description="Behavioral quirks")
    
    # Relationships
    relationships: list[dict] = Field(default_factory=list, description="Key relationships")
    
    # For illustration
    portrait_prompt: Optional[str] = Field(default=None, description="Prompt for portrait generation")


class CharacterResult(BaseModel):
    """Result of character generation."""
    
    character: Character
    generation_notes: Optional[str] = Field(default=None, description="Notes from generation")
