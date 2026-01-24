"""
Writing Hub Services
====================

Core services for the Writing Hub including:
- Project context management
- Import services
- Research integration (uses Research Hub as service layer)
"""

from .project_context import ProjectContextService, ProjectContext, project_context_service
from .import_service import ImportService, ImportStats
from .research_integration import (
    WritingResearchService,
    LiteratureSearchResult,
    get_writing_research,
)
from .quality_gate_service import QualityGateService, quality_gate_service
from .chapter_production_service import (
    ChapterProductionService,
    ProductionResult,
    ProductionStage,
    get_chapter_production_service,
)

__all__ = [
    # Project Context
    'ProjectContextService',
    'ProjectContext', 
    'project_context_service',
    # Import
    'ImportService',
    'ImportStats',
    # Research Integration
    'WritingResearchService',
    'LiteratureSearchResult',
    'get_writing_research',
    # Quality Gate
    'QualityGateService',
    'quality_gate_service',
    # Chapter Production
    'ChapterProductionService',
    'ProductionResult',
    'ProductionStage',
    'get_chapter_production_service',
]
