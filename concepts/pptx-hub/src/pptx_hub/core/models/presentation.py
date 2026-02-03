"""
Presentation data models.

Pydantic models for representing PowerPoint presentations and their content.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict


class TextType(str, Enum):
    """Type of text content in a slide."""
    
    TITLE = "title"
    SUBTITLE = "subtitle"
    BODY = "body"
    FOOTER = "footer"
    NOTE = "note"
    TABLE = "table"
    CHART = "chart"
    OTHER = "other"


class SlideText(BaseModel):
    """A text element within a slide."""
    
    model_config = ConfigDict(frozen=True)
    
    id: str = Field(default_factory=lambda: str(uuid4())[:8])
    content: str
    text_type: TextType = TextType.BODY
    shape_id: int | None = None
    paragraph_index: int = 0
    run_index: int = 0
    
    # Position info (for repackaging)
    left: int | None = None
    top: int | None = None
    width: int | None = None
    height: int | None = None
    
    # Formatting
    font_name: str | None = None
    font_size: int | None = None
    bold: bool = False
    italic: bool = False
    
    @property
    def is_empty(self) -> bool:
        """Check if text content is empty or whitespace."""
        return not self.content or not self.content.strip()


class Slide(BaseModel):
    """A single slide in a presentation."""
    
    model_config = ConfigDict(frozen=True)
    
    number: int
    title: str | None = None
    texts: list[SlideText] = Field(default_factory=list)
    notes: str | None = None
    layout_name: str | None = None
    
    # Metadata
    has_images: bool = False
    has_tables: bool = False
    has_charts: bool = False
    shape_count: int = 0
    
    @property
    def text_count(self) -> int:
        """Number of text elements in this slide."""
        return len(self.texts)
    
    @property
    def all_text(self) -> str:
        """Concatenated text content from all elements."""
        parts = []
        if self.title:
            parts.append(self.title)
        parts.extend(t.content for t in self.texts if not t.is_empty)
        if self.notes:
            parts.append(self.notes)
        return "\n\n".join(parts)


class Presentation(BaseModel):
    """A PowerPoint presentation."""
    
    model_config = ConfigDict(frozen=True)
    
    id: UUID = Field(default_factory=uuid4)
    filename: str
    title: str | None = None
    author: str | None = None
    subject: str | None = None
    
    slides: list[Slide] = Field(default_factory=list)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    slide_width: int | None = None
    slide_height: int | None = None
    
    @property
    def slide_count(self) -> int:
        """Number of slides in the presentation."""
        return len(self.slides)
    
    @property
    def total_text_count(self) -> int:
        """Total number of text elements across all slides."""
        return sum(s.text_count for s in self.slides)
    
    def get_slide(self, number: int) -> Slide | None:
        """Get slide by number (1-indexed)."""
        for slide in self.slides:
            if slide.number == number:
                return slide
        return None


class ExtractionResult(BaseModel):
    """Result of text extraction from a presentation."""
    
    model_config = ConfigDict(frozen=True)
    
    presentation: Presentation
    source_path: str
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Statistics
    total_slides: int = 0
    total_texts: int = 0
    total_characters: int = 0
    
    # Warnings/errors during extraction
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    
    @property
    def slides(self) -> list[Slide]:
        """Shortcut to presentation slides."""
        return self.presentation.slides
    
    @property
    def success(self) -> bool:
        """Check if extraction was successful (no errors)."""
        return len(self.errors) == 0
