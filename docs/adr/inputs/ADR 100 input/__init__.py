"""
outlinefw/src/outlinefw/__init__.py

Public API for iil-outlinefw.

Fixes:
  - HOCH H-1: Explicit __all__ — no implicit star-import surface
  - KRITISCH K-1: py.typed marker lives at src/outlinefw/py.typed (PEP 561)
  - BLOCKER B-3: django_adapter is an abstract base (ABC), not an undefined stub

Stable API (semantic versioning: breaking changes → MAJOR bump):
  Schemas:   ProjectContext, OutlineNode, OutlineResult, ParseResult
  Generator: OutlineGenerator, LLMRouter, LLMRouterError, LLMRouterTimeout
  Parser:    parse_nodes
  Frameworks: FRAMEWORKS, get_framework, list_frameworks
"""

from outlinefw.frameworks import FRAMEWORKS, FrameworkDefinition, get_framework, list_frameworks
from outlinefw.generator import LLMRouter, LLMRouterError, LLMRouterTimeout, OutlineGenerator
from outlinefw.parser import parse_nodes
from outlinefw.schemas import (
    ActPhase,
    BeatDefinition,
    FrameworkDefinition,
    GenerationStatus,
    LLMQuality,
    OutlineGenerationError,
    OutlineNode,
    OutlineResult,
    ParseResult,
    ParseStatus,
    ProjectContext,
    TensionLevel,
)

__version__ = "0.1.0"

__all__ = [
    # Version
    "__version__",
    # Core Generation
    "OutlineGenerator",
    "LLMRouter",
    "LLMRouterError",
    "LLMRouterTimeout",
    "parse_nodes",
    # Schemas
    "ProjectContext",
    "OutlineNode",
    "OutlineResult",
    "ParseResult",
    "BeatDefinition",
    "FrameworkDefinition",
    "OutlineGenerationError",
    # Enums
    "ActPhase",
    "TensionLevel",
    "LLMQuality",
    "GenerationStatus",
    "ParseStatus",
    # Framework Registry
    "FRAMEWORKS",
    "get_framework",
    "list_frameworks",
]
