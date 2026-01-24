"""
TypedDict definitions for handler contexts
Provides type safety for input parameters
"""

from typing import TypedDict, Optional, List, Dict, Any


class PreviewContext(TypedDict, total=False):
    """Type-safe context for preview slide operations"""
    presentation_id: str  # Required
    markdown_file: str  # Required for markdown previews
    file_name: str  # Required
    source_type: str  # Optional: 'markdown', 'json', 'pdf'


class ConversionContext(TypedDict, total=False):
    """Type-safe context for preview to PPTX conversion"""
    preview_id: str  # Required
    presentation_id: str  # Required
    design_profile_id: Optional[str]  # Optional


class EnhancementContext(TypedDict, total=False):
    """Type-safe context for presentation enhancement"""
    presentation_id: str  # Required
    concepts: List[Dict[str, Any]]  # Required: List of slide concepts
    enhancement_type: str  # Optional
    mode: str  # Optional: 'append', 'smart'


class MarkdownParseContext(TypedDict):
    """Type-safe context for markdown parsing"""
    markdown_file: str
    file_name: Optional[str]


class DesignExtractionContext(TypedDict):
    """Type-safe context for design extraction from PPTX"""
    pptx_path: str
    presentation_id: str


__all__ = [
    'PreviewContext',
    'ConversionContext',
    'EnhancementContext',
    'MarkdownParseContext',
    'DesignExtractionContext',
]
