"""
Creative Services - Shared AI-powered creative writing services.

This package provides modular, reusable creative AI services for:
- Character generation
- World building
- Story writing (outlines, chapters)
- Scene analysis
- Illustration configuration
- Quality review
"""

__version__ = "0.1.0"

from creative_services.core.base_handler import BaseHandler
from creative_services.core.llm_client import LLMClient
from creative_services.core.context import BaseContext

__all__ = [
    "BaseHandler",
    "LLMClient", 
    "BaseContext",
    "__version__",
]
