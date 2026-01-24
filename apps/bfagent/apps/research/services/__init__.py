"""
Research Hub - Services
=======================

Service-Module für die Research-Domain.
"""

from .brave_search_service import BraveSearchService, get_brave_search
from .research_service import ResearchService, get_research_service
from .academic_search_service import AcademicSearchService, get_academic_search
from .citation_service import CitationService, get_citation_service, Citation, CitationStyle, Author
from .paper_frameworks import (
    PaperFramework, PaperSection, PaperType,
    get_paper_framework, list_paper_frameworks, generate_paper_outline,
    PAPER_FRAMEWORKS
)
from .outline_generator import (
    OutlineGeneratorService, get_outline_generator,
    GeneratedOutline, OutlineSection
)
from .export_service import ResearchExportService, get_export_service
from .ai_summary_service import AISummaryService, get_ai_summary_service
from .vector_store_service import VectorStoreService, get_vector_store

__all__ = [
    'BraveSearchService',
    'get_brave_search',
    'ResearchService',
    'get_research_service',
    'AcademicSearchService',
    'get_academic_search',
    'CitationService',
    'get_citation_service',
    'Citation',
    'CitationStyle',
    'Author',
    'ResearchExportService',
    'get_export_service',
    'AISummaryService',
    'get_ai_summary_service',
    'VectorStoreService',
    'get_vector_store',
    # Paper Frameworks
    'PaperFramework',
    'PaperSection',
    'PaperType',
    'get_paper_framework',
    'list_paper_frameworks',
    'generate_paper_outline',
    'PAPER_FRAMEWORKS',
    # Outline Generator
    'OutlineGeneratorService',
    'get_outline_generator',
    'GeneratedOutline',
    'OutlineSection',
]
