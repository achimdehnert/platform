from .calculators import BaseCalculator, FootprintAreaQuantityRule, QuantityEngine, QuantityRule
from .exceptions import CADError, CADParseError, CADResourceError, CADSecurityError
from .extractors import BaseExtractor, DXFExtractor, IFCExtractor
from .mapping import LayerMapping, MappingProfile
from .models import (
    CADElement,
    CADGeometry,
    CADMaterial,
    CADParseResult,
    CADParseStatistics,
    CADProperty,
    CADQuantity,
    CADWarning,
    ElementCategory,
    PropertySource,
    QuantityMethod,
    QuantityType,
    SourceFormat,
)
from .parsers import BaseParser, DXFParser, IFCParser
from .pipeline import run_pipeline
from .repositories import FileProfileRepository, MappingProfileRepository
from .utils.hash import sha256_file
from .utils.path_validation import validate_file_path
from .version import __version__
from .writer import BaseWriter, WriteResult

try:
    from .writer import PostgresWriter  # requires asyncpg
except ImportError:
    PostgresWriter = None  # type: ignore[assignment,misc]


__all__ = [
    "__version__",
    # Errors
    "CADError",
    "CADParseError",
    "CADSecurityError",
    "CADResourceError",
    # Calculators
    "BaseCalculator",
    "QuantityRule",
    "QuantityEngine",
    "FootprintAreaQuantityRule",
    # Pipeline
    "run_pipeline",
    # Models
    "CADElement",
    "ElementCategory",
    "SourceFormat",
    "CADProperty",
    "PropertySource",
    "CADQuantity",
    "QuantityType",
    "QuantityMethod",
    "CADMaterial",
    "CADGeometry",
    "CADWarning",
    "CADParseStatistics",
    "CADParseResult",
    # Mapping
    "LayerMapping",
    "MappingProfile",
    # Extractors
    "BaseExtractor",
    "DXFExtractor",
    "IFCExtractor",
    # Repositories
    "MappingProfileRepository",
    "FileProfileRepository",
    # Parsers
    "BaseParser",
    "IFCParser",
    "DXFParser",
    # Writer (ADR-034)
    "BaseWriter",
    "PostgresWriter",
    "WriteResult",
    # Utils
    "validate_file_path",
    "sha256_file",
]
