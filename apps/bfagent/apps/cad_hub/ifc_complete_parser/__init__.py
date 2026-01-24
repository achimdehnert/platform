"""
IFC Complete Parser

Vollständiger IFC Parser für alle Informationen aus IFC-Dateien.

Usage:
    from ifc_complete_parser import IfcCompleteParser

    parser = IfcCompleteParser("/path/to/model.ifc")
    project = parser.parse()

    # Alle Räume mit Brandschutz
    for space in project.spaces:
        print(f"{space.name}: {space.fire_rating}")

    # Export als JSON
    project.save_json("output.json")

Supported IFC Schemas:
    - IFC2X3
    - IFC4
    - IFC4X1
    - IFC4X2
    - IFC4X3
"""

from .models import (  # Enums; Properties & Quantities; Spatial Structure; Elements; Project
    IfcSchemaVersion,
    ParsedBuilding,
    ParsedClassification,
    ParsedElement,
    ParsedElementType,
    ParsedMaterial,
    ParsedProject,
    ParsedProperty,
    ParsedQuantity,
    ParsedSite,
    ParsedSpace,
    ParsedStorey,
    PropertyDataType,
)
from .parser import IfcCompleteParser

__all__ = [
    # Parser
    "IfcCompleteParser",
    # Enums
    "IfcSchemaVersion",
    "PropertyDataType",
    # Properties & Quantities
    "ParsedProperty",
    "ParsedQuantity",
    "ParsedMaterial",
    "ParsedClassification",
    # Spatial Structure
    "ParsedSite",
    "ParsedBuilding",
    "ParsedStorey",
    "ParsedSpace",
    # Elements
    "ParsedElement",
    "ParsedElementType",
    # Project
    "ParsedProject",
]

__version__ = "2.0.0"
__author__ = "BauCAD Hub"
