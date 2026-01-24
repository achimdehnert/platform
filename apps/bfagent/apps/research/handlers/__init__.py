"""
Research Hub - Handlers
=======================

Handler-Module für die Research-Domain.
"""

from .web_search_handler import WebSearchHandler
from .knowledge_base_handler import KnowledgeBaseHandler
from .fact_check_handler import FactCheckHandler
from .summary_handler import SummaryHandler
from .academic_search_handler import AcademicSearchHandler
from .deep_dive_handler import DeepDiveHandler

__all__ = [
    'WebSearchHandler',
    'KnowledgeBaseHandler',
    'FactCheckHandler',
    'SummaryHandler',
    'AcademicSearchHandler',
    'DeepDiveHandler',
]
