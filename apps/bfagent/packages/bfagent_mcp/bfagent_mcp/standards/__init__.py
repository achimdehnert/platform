"""
Standards Knowledge Base
========================

Zentrale Definition aller BF Agent Coding Standards.
Diese Standards werden für Validierung UND Template-Generierung verwendet.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class StandardCategory(Enum):
    """Kategorien von Standards"""
    HANDLER = "handler"
    SCHEMA = "schema"
    ERROR_HANDLING = "error_handling"
    LOGGING = "logging"
    DOCUMENTATION = "documentation"
    NAMING = "naming"
    TESTING = "testing"


@dataclass
class Standard:
    """Definition eines einzelnen Standards"""
    id: str
    category: StandardCategory
    name: str
    description: str
    severity: str  # "error" | "warning" | "info"
    
    # Patterns für Validierung
    check_pattern: Optional[str] = None  # MUSS vorhanden sein
    anti_pattern: Optional[str] = None   # DARF NICHT vorhanden sein
    
    # Beispiele
    good_example: Optional[str] = None
    bad_example: Optional[str] = None
    
    # Auto-Fix
    auto_fixable: bool = False


# ═══════════════════════════════════════════════════════════════════════════════
# STANDARDS DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

STANDARDS: Dict[str, Standard] = {
    
    # ─────────────────────────────────────────────────────────────────────────
    # HANDLER STANDARDS (H)
    # ─────────────────────────────────────────────────────────────────────────
    
    "H001": Standard(
        id="H001",
        category=StandardCategory.HANDLER,
        name="BaseHandler Inheritance",
        description="Handler MÜSSEN von BaseHandler erben",
        severity="error",
        check_pattern=r"class\s+\w+\(BaseHandler\)",
        auto_fixable=True,
    ),
    
    "H002": Standard(
        id="H002",
        category=StandardCategory.HANDLER,
        name="Three-Phase Pattern",
        description="Handler MÜSSEN validate(), process(), cleanup() haben",
        severity="error",
        check_pattern=r"async def process\s*\(",
        auto_fixable=True,
    ),
    
    "H003": Standard(
        id="H003",
        category=StandardCategory.HANDLER,
        name="HandlerResult Return",
        description="process() MUSS HandlerResult zurückgeben",
        severity="error",
        check_pattern=r"return\s+HandlerResult",
    ),
    
    "H004": Standard(
        id="H004",
        category=StandardCategory.HANDLER,
        name="Handler Metadata",
        description="Handler MÜSSEN name, description, version haben",
        severity="error",
        check_pattern=r'name\s*=\s*["\']',
        auto_fixable=True,
    ),
    
    # ─────────────────────────────────────────────────────────────────────────
    # SCHEMA STANDARDS (S)
    # ─────────────────────────────────────────────────────────────────────────
    
    "S001": Standard(
        id="S001",
        category=StandardCategory.SCHEMA,
        name="Pydantic Input Schema",
        description="Handler MÜSSEN input_schema definieren",
        severity="error",
        check_pattern=r"input_schema\s*=",
        auto_fixable=True,
    ),
    
    "S002": Standard(
        id="S002",
        category=StandardCategory.SCHEMA,
        name="Pydantic Output Schema",
        description="Handler MÜSSEN output_schema definieren",
        severity="error",
        check_pattern=r"output_schema\s*=",
        auto_fixable=True,
    ),
    
    "S003": Standard(
        id="S003",
        category=StandardCategory.SCHEMA,
        name="Field Descriptions",
        description="Pydantic Fields SOLLEN description haben",
        severity="warning",
        check_pattern=r"Field\([^)]*description\s*=",
    ),
    
    # ─────────────────────────────────────────────────────────────────────────
    # ERROR HANDLING STANDARDS (E)
    # ─────────────────────────────────────────────────────────────────────────
    
    "E001": Standard(
        id="E001",
        category=StandardCategory.ERROR_HANDLING,
        name="Try-Except in process()",
        description="process() MUSS try-except Block haben",
        severity="error",
        check_pattern=r"try\s*:",
    ),
    
    # ─────────────────────────────────────────────────────────────────────────
    # LOGGING STANDARDS (L)
    # ─────────────────────────────────────────────────────────────────────────
    
    "L001": Standard(
        id="L001",
        category=StandardCategory.LOGGING,
        name="Logger Usage",
        description="Handler SOLLEN self.logger verwenden",
        severity="warning",
        check_pattern=r"self\.logger\.",
    ),
    
    # ─────────────────────────────────────────────────────────────────────────
    # DOCUMENTATION STANDARDS (D)
    # ─────────────────────────────────────────────────────────────────────────
    
    "D001": Standard(
        id="D001",
        category=StandardCategory.DOCUMENTATION,
        name="Class Docstring",
        description="Handler-Klasse MUSS Docstring haben",
        severity="error",
        check_pattern=r'class\s+\w+Handler.*:\s*\n\s*"""',
        auto_fixable=True,
    ),
    
    # ─────────────────────────────────────────────────────────────────────────
    # NAMING STANDARDS (N)
    # ─────────────────────────────────────────────────────────────────────────
    
    "N001": Standard(
        id="N001",
        category=StandardCategory.NAMING,
        name="Handler Suffix",
        description="Handler-Klassen MÜSSEN mit 'Handler' enden",
        severity="error",
        check_pattern=r"class\s+\w+Handler\(",
    ),
    
    # ─────────────────────────────────────────────────────────────────────────
    # TESTING STANDARDS (T)
    # ─────────────────────────────────────────────────────────────────────────
    
    "T001": Standard(
        id="T001",
        category=StandardCategory.TESTING,
        name="Test Class",
        description="Handler SOLLTEN Test-Klasse haben",
        severity="warning",
        check_pattern=r"class\s+Test\w+Handler",
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_all_standards() -> List[Standard]:
    """Alle Standards abrufen"""
    return list(STANDARDS.values())


def get_standards_by_category(category: StandardCategory) -> List[Standard]:
    """Standards einer Kategorie"""
    return [s for s in STANDARDS.values() if s.category == category]


def get_standards_by_severity(severity: str) -> List[Standard]:
    """Standards einer Severity"""
    return [s for s in STANDARDS.values() if s.severity == severity]


def get_error_standards() -> List[Standard]:
    """Nur Error-Standards (MÜSSEN erfüllt sein)"""
    return get_standards_by_severity("error")


def get_standard(standard_id: str) -> Optional[Standard]:
    """Einzelnen Standard abrufen"""
    return STANDARDS.get(standard_id)
