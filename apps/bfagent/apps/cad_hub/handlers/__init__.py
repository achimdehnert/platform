"""
CAD Hub Handlers - NL2CAD Integration

Handler-basierte Architektur für CAD-Analyse und Natural Language Queries.

Architektur:
    INPUT LAYER → PROCESSING LAYER → ENGINE → STANDARDS → OUTPUT LAYER

Handler:
    - CADFileInputHandler: Format-Erkennung & Konvertierung (IFC/DXF/DWG)
    - NLQueryHandler: Pattern-Matching + LLM für natürliche Sprache
    - RoomAnalysisHandler: Raum-Extraktion & DIN 277 Klassifikation
    - MassenHandler: Flächen, Volumina, Umfänge berechnen
    - PDFLageplanHandler: Extraktion aus Lageplan-PDFs
    - PDFAbstandsflaechenHandler: Extraktion aus Abstandsflächenplan-PDFs
"""

from .base import BaseCADHandler, CADHandlerResult, CADHandlerError, CADHandlerPipeline
from .cad_file_input import CADFileInputHandler
from .nl_query import NLQueryHandler
from .room_analysis import RoomAnalysisHandler
from .massen import MassenHandler
from .pdf_lageplan import PDFLageplanHandler
from .pdf_abstandsflaechen import PDFAbstandsflaechenHandler
from .brandschutz import BrandschutzHandler
from .brandschutz_symbols import BrandschutzSymbolHandler
from .pdf_vision import PDFVisionHandler
from .brandschutz_report import BrandschutzReportHandler

__all__ = [
    # Base
    "BaseCADHandler",
    "CADHandlerResult",
    "CADHandlerError",
    "CADHandlerPipeline",
    # Handlers
    "CADFileInputHandler",
    "NLQueryHandler",
    "RoomAnalysisHandler",
    "MassenHandler",
    # PDF Handlers
    "PDFLageplanHandler",
    "PDFAbstandsflaechenHandler",
    # Brandschutz
    "BrandschutzHandler",
    "BrandschutzSymbolHandler",
    # Vision & Reporting
    "PDFVisionHandler",
    "BrandschutzReportHandler",
]
