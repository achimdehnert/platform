"""Schemas for story generation."""

from typing import Optional
from pydantic import BaseModel, Field


class OutlineSection(BaseModel):
    """A section in the story outline."""
    
    number: int = Field(..., description="Section/chapter number")
    title: str = Field(..., description="Section title")
    summary: str = Field(..., description="What happens in this section")
    key_events: list[str] = Field(default_factory=list, description="Key events")
    characters_involved: list[str] = Field(default_factory=list, description="Characters in this section")
    location: Optional[str] = Field(default=None, description="Primary location")
    emotional_beat: Optional[str] = Field(default=None, description="Emotional tone/beat")


class Outline(BaseModel):
    """Story outline structure."""
    
    title: str = Field(..., description="Story title")
    logline: str = Field(default="", description="One-sentence story summary")
    premise: str = Field(default="", description="Story premise")
    
    # Structure
    structure_type: str = Field(default="three_act", description="Story structure type")
    sections: list[OutlineSection] = Field(default_factory=list, description="Outline sections")
    
    # Themes
    themes: list[str] = Field(default_factory=list, description="Story themes")
    
    # Arc
    protagonist_arc: Optional[str] = Field(default=None, description="Protagonist transformation")
    central_conflict: Optional[str] = Field(default=None, description="Main conflict")


class Chapter(BaseModel):
    """Generated chapter content."""
    
    number: int = Field(..., description="Chapter number")
    title: str = Field(..., description="Chapter title")
    content: str = Field(..., description="Chapter content/prose")
    
    # Metadata
    word_count: int = Field(default=0, description="Word count")
    summary: str = Field(default="", description="Chapter summary")
    
    # Scene info
    scenes: list[dict] = Field(default_factory=list, description="Scenes in chapter")
    locations: list[str] = Field(default_factory=list, description="Locations featured")
    characters: list[str] = Field(default_factory=list, description="Characters featured")
    
    # Continuity
    cliffhanger: Optional[str] = Field(default=None, description="Chapter ending hook")
    setup_for_next: Optional[str] = Field(default=None, description="Setup for next chapter")


class StoryResult(BaseModel):
    """Result of story generation operations."""
    
    outline: Optional[Outline] = None
    chapter: Optional[Chapter] = None
    generation_notes: Optional[str] = None
