# apps/cad_hub/services/__init__.py
"""
Services für IFC Dashboard

Basiert auf BauCAD Hub MCP Best Practices:
- IFC Parser mit vollständiger Quantity-Extraktion
- DIN 277 Calculator nach Norm 2021
- WoFlV Wohnflächenberechnung
- GAEB X84 Leistungsverzeichnis-Export
- Raumbuch Export mit professioneller Formatierung
"""
from .din277_calculator import AreaCategory, DIN277Calculator, DIN277Result
from .export_service import RaumbuchExportService
from .gaeb_generator import (
    GAEBGenerator,
    GAEBPhase,
    Leistungsverzeichnis,
    LosGruppe,
    MassenermittlungHelper,
    MengenEinheit,
    Position,
)
from .ifc_parser import IFCParseResult, IFCParserService, RoomType
from .ifc_x83_converter import IFCX83Converter, GewerkeConfig, get_ifc_x83_converter
from .woflv_calculator import WoFlVCalculator, WoFlVResult, WoFlVRoom
from .avb_service import AVBService, BidComparison, PriceRanking, get_avb_service
from .dxf_parser import DXFParserService, DXFParseResult, parse_dxf
from .nl2dxf import NL2DXFGenerator, NL2DXFResult, nl2dxf
from .dxf_renderer import DXFRendererService, render_dxf_to_svg, dxf_to_json
from .dwg_converter import DWGConverterService, DWGConversionResult, convert_dwg_to_dxf
from .dxf_analyzer import (
    DXFAnalyzer, 
    FloorPlanAnalyzer, 
    TechnicalDrawingAnalyzer,
    AnalysisReport,
    LayerInfo,
    BlockInfo,
    TextInfo,
    DimensionInfo,
    load_cad_file,
)
from .cad_loader import CADLoaderService, load_and_analyze, get_dwg_converter_status
from .mcp_bridge import (
    CADMCPBridge,
    get_mcp_bridge,
    analyze_cad_file,
    check_dxf_quality,
    ask_cad_question,
    batch_analyze_directory,
    AnalysisResult,
    DXFQualityResult,
    NLQueryResult,
    BatchResult,
    CADFormat,
)

__all__ = [
    # Parser
    "IFCParserService",
    "IFCParseResult",
    "RoomType",
    # DIN 277
    "DIN277Calculator",
    "DIN277Result",
    "AreaCategory",
    # WoFlV
    "WoFlVCalculator",
    "WoFlVResult",
    "WoFlVRoom",
    # GAEB
    "GAEBGenerator",
    "GAEBPhase",
    "Leistungsverzeichnis",
    "LosGruppe",
    "Position",
    "MengenEinheit",
    "MassenermittlungHelper",
    # IFC -> X83
    "IFCX83Converter",
    "GewerkeConfig",
    "get_ifc_x83_converter",
    # AVB (Ausschreibung, Vergabe, Bauausführung)
    "AVBService",
    "BidComparison",
    "PriceRanking",
    "get_avb_service",
    # Export
    "RaumbuchExportService",
    # DXF Parser
    "DXFParserService",
    "DXFParseResult",
    "parse_dxf",
    # NL2DXF (Natural Language to DXF)
    "NL2DXFGenerator",
    "NL2DXFResult",
    "nl2dxf",
    # DXF Renderer (SVG, PNG, JSON)
    "DXFRendererService",
    "render_dxf_to_svg",
    "dxf_to_json",
    # DWG Converter
    "DWGConverterService",
    "DWGConversionResult",
    "convert_dwg_to_dxf",
    # DXF Analyzer (Toolkit)
    "DXFAnalyzer",
    "FloorPlanAnalyzer",
    "TechnicalDrawingAnalyzer",
    "AnalysisReport",
    "LayerInfo",
    "BlockInfo",
    "TextInfo",
    "DimensionInfo",
    "load_cad_file",
    # CAD Loader (Unified Service)
    "CADLoaderService",
    "load_and_analyze",
    "get_dwg_converter_status",
    # MCP Bridge (CAD MCP Integration)
    "CADMCPBridge",
    "get_mcp_bridge",
    "analyze_cad_file",
    "check_dxf_quality",
    "ask_cad_question",
    "batch_analyze_directory",
    "AnalysisResult",
    "DXFQualityResult",
    "NLQueryResult",
    "BatchResult",
    "CADFormat",
]
