"""
BFA Agent - Explosionsschutz Multi-Agent System
Integriert in Django/BFAgent

Basiert auf OpenAI Agents SDK + OpenRouter
"""

from .schemas import (
    ExZoneClassification,
    EquipmentCheckResult,
    VentilationAnalysis,
    BFAReport,
    ZoneType,
    RiskLevel,
)
from .config import setup_openrouter, Models
from .tools import (
    get_substance_properties,
    calculate_zone_extent,
    check_equipment_suitability,
    analyze_ventilation_effectiveness,
    read_cad_file,
    extract_ex_zones_from_cad,
    get_ventilation_from_cad,
    SUPPORTED_CAD_FORMATS,
)

__version__ = "1.0.0"

__all__ = [
    # Schemas
    "ExZoneClassification",
    "EquipmentCheckResult",
    "VentilationAnalysis",
    "BFAReport",
    "ZoneType",
    "RiskLevel",
    # Config
    "setup_openrouter",
    "Models",
    # Tools - Phase 1 & 2
    "get_substance_properties",
    "calculate_zone_extent",
    "check_equipment_suitability",
    "analyze_ventilation_effectiveness",
    # Tools - Phase 3 CAD
    "read_cad_file",
    "extract_ex_zones_from_cad",
    "get_ventilation_from_cad",
    "SUPPORTED_CAD_FORMATS",
]
