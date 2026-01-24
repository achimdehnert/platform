# apps/cad_hub/services/mcp_bridge.py
"""
CAD MCP Bridge Service
======================

Bridge zwischen CAD Hub (Django Frontend) und CAD MCP Server (Analysis Backend).

Implementiert die 4 Hauptszenarien:
1. IFC-Upload mit Auto-Analyse
2. DXF Qualitätsprüfung (Maßketten + Schnitte)
3. Natural Language Query
4. Multi-Format Batch-Analyse

Usage:
    from apps.cad_hub.services.mcp_bridge import CADMCPBridge, get_mcp_bridge
    
    bridge = get_mcp_bridge()
    result = await bridge.analyze_file("/path/to/model.ifc")
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================

class CADFormat(str, Enum):
    """Unterstützte CAD-Formate"""
    IFC = "ifc"
    DXF = "dxf"
    DWG = "dwg"
    IGES = "iges"
    FBX = "fbx"
    GLTF = "gltf"
    GLB = "glb"
    THREE_MF = "3mf"
    PLY = "ply"
    STEP = "step"
    UNKNOWN = "unknown"


@dataclass
class AnalysisResult:
    """Ergebnis einer CAD-Analyse"""
    success: bool
    file_path: str
    format: CADFormat
    data: Dict[str, Any] = field(default_factory=dict)
    markdown_report: str = ""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "file_path": self.file_path,
            "format": self.format.value,
            "data": self.data,
            "markdown_report": self.markdown_report,
            "errors": self.errors,
            "warnings": self.warnings,
        }


@dataclass
class DXFQualityResult:
    """Ergebnis der DXF-Qualitätsprüfung"""
    success: bool
    file_path: str
    dimension_chains: Dict[str, Any] = field(default_factory=dict)
    section_views: Dict[str, Any] = field(default_factory=dict)
    quality_score: float = 0.0
    issues: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass 
class NLQueryResult:
    """Ergebnis einer Natural Language Abfrage"""
    success: bool
    query: str
    answer: str
    data: Any = None
    source_file: str = ""
    confidence: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BatchResult:
    """Ergebnis einer Batch-Analyse"""
    success: bool
    total_files: int
    analyzed: int
    failed: int
    results: List[AnalysisResult] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "total_files": self.total_files,
            "analyzed": self.analyzed,
            "failed": self.failed,
            "results": [r.to_dict() for r in self.results],
            "summary": self.summary,
        }


# =============================================================================
# MCP Bridge Service
# =============================================================================

class CADMCPBridge:
    """
    Bridge Service für CAD MCP Integration.
    
    Kann entweder:
    1. Direkt die Python-Module importieren (LOCAL mode)
    2. Via HTTP mit einem separaten MCP Server kommunizieren (REMOTE mode)
    """
    
    def __init__(self, mode: str = "local"):
        """
        Args:
            mode: "local" für direkten Import, "remote" für HTTP
        """
        self.mode = mode
        self._parsers = {}
        self._analyzers = {}
        self._initialized = False
        
        # Remote mode settings
        self.mcp_base_url = getattr(settings, "CAD_MCP_URL", "http://localhost:8001")
        self.timeout = 60.0
    
    def _ensure_initialized(self):
        """Lazy initialization der Parser/Analyzer"""
        if self._initialized:
            return
            
        if self.mode == "local":
            self._init_local_parsers()
        
        self._initialized = True
    
    def _init_local_parsers(self):
        """Initialisiert lokale Parser (aus mcp-hub/cad_mcp)"""
        try:
            # Versuche Import aus dem installierten Package
            from baucad_hub_mcp.parsers import (
                DXFParser, IFCParser, IGESParser, FBXParser
            )
            from baucad_hub_mcp.analyzers import (
                DimensionChainAnalyzer, SectionViewAnalyzer
            )
            
            self._parsers = {
                CADFormat.DXF: DXFParser(),
                CADFormat.DWG: DXFParser(),  # DWG wird zu DXF konvertiert
                CADFormat.IFC: IFCParser(),
                CADFormat.IGES: IGESParser(),
                CADFormat.FBX: FBXParser(),
            }
            
            self._analyzers = {
                "dimension_chains": DimensionChainAnalyzer(),
                "section_views": SectionViewAnalyzer(),
            }
            
            logger.info("CAD MCP Bridge: Local parsers initialized")
            
        except ImportError as e:
            logger.warning(f"CAD MCP local import failed: {e}. Using fallback.")
            self._init_fallback_parsers()
    
    def _init_fallback_parsers(self):
        """Fallback: Nutze lokale CAD Hub Services"""
        try:
            from .ifc_parser import IFCParserService
            from .dxf_parser import DXFParserService
            
            self._parsers = {
                CADFormat.IFC: IFCParserService(),
                CADFormat.DXF: DXFParserService(),
            }
            
            # DXFAnalyzer wird nicht vorinitialisiert, da er einen filepath benötigt
            # Er wird in _analyze_dxf_quality_fallback() bei Bedarf erstellt
            self._analyzers = {}
            
            logger.info("CAD MCP Bridge: Fallback parsers initialized")
            
        except ImportError as e:
            logger.error(f"Fallback parser import failed: {e}")
    
    def _detect_format(self, file_path: Union[str, Path]) -> CADFormat:
        """Erkennt das CAD-Format anhand der Dateiendung"""
        path = Path(file_path)
        suffix = path.suffix.lower()
        
        format_map = {
            ".ifc": CADFormat.IFC,
            ".dxf": CADFormat.DXF,
            ".dwg": CADFormat.DWG,
            ".igs": CADFormat.IGES,
            ".iges": CADFormat.IGES,
            ".fbx": CADFormat.FBX,
            ".gltf": CADFormat.GLTF,
            ".glb": CADFormat.GLB,
            ".3mf": CADFormat.THREE_MF,
            ".ply": CADFormat.PLY,
            ".stp": CADFormat.STEP,
            ".step": CADFormat.STEP,
        }
        
        return format_map.get(suffix, CADFormat.UNKNOWN)
    
    # =========================================================================
    # Szenario 1: Format-Analyse
    # =========================================================================
    
    async def analyze_file(
        self, 
        file_path: str, 
        format: str = "auto",
        output_format: str = "dict"
    ) -> AnalysisResult:
        """
        Analysiert eine CAD-Datei.
        
        Szenario 1: IFC-Upload mit Auto-Analyse
        
        Args:
            file_path: Pfad zur CAD-Datei
            format: "auto" oder spezifisches Format
            output_format: "dict", "markdown", "json"
            
        Returns:
            AnalysisResult mit Analyse-Daten
        """
        self._ensure_initialized()
        
        path = Path(file_path)
        if not path.exists():
            return AnalysisResult(
                success=False,
                file_path=file_path,
                format=CADFormat.UNKNOWN,
                errors=[f"Datei nicht gefunden: {file_path}"]
            )
        
        # Format erkennen
        detected_format = self._detect_format(path) if format == "auto" else CADFormat(format)
        
        try:
            if self.mode == "local":
                result = await self._analyze_local(path, detected_format)
            else:
                result = await self._analyze_remote(path, detected_format)
            
            return result
            
        except Exception as e:
            logger.exception(f"Analyse fehlgeschlagen für {file_path}")
            return AnalysisResult(
                success=False,
                file_path=file_path,
                format=detected_format,
                errors=[str(e)]
            )
    
    async def _analyze_local(self, path: Path, format: CADFormat) -> AnalysisResult:
        """Lokale Analyse mit importierten Parsern"""
        parser = self._parsers.get(format)
        
        if not parser:
            return AnalysisResult(
                success=False,
                file_path=str(path),
                format=format,
                errors=[f"Kein Parser für Format {format.value} verfügbar"]
            )
        
        # Parser aufrufen (sync oder async)
        if asyncio.iscoroutinefunction(parser.parse):
            result = await parser.parse(path)
        else:
            result = parser.parse(path)
        
        # Result normalisieren
        data = result.to_dict() if hasattr(result, "to_dict") else dict(result)
        markdown = result.to_markdown() if hasattr(result, "to_markdown") else ""
        
        return AnalysisResult(
            success=True,
            file_path=str(path),
            format=format,
            data=data,
            markdown_report=markdown
        )
    
    async def _analyze_remote(self, path: Path, format: CADFormat) -> AnalysisResult:
        """Remote-Analyse via HTTP"""
        import httpx
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Datei hochladen
            with open(path, "rb") as f:
                files = {"file": (path.name, f)}
                response = await client.post(
                    f"{self.mcp_base_url}/api/analyze",
                    files=files,
                    data={"format": format.value}
                )
            
            if response.status_code != 200:
                return AnalysisResult(
                    success=False,
                    file_path=str(path),
                    format=format,
                    errors=[f"MCP Server Error: {response.status_code}"]
                )
            
            data = response.json()
            return AnalysisResult(
                success=True,
                file_path=str(path),
                format=format,
                data=data.get("data", {}),
                markdown_report=data.get("markdown", "")
            )
    
    # =========================================================================
    # Szenario 2: DXF Qualitätsprüfung
    # =========================================================================
    
    async def check_dxf_quality(self, file_path: str) -> DXFQualityResult:
        """
        Prüft die Qualität einer DXF-Zeichnung.
        
        Szenario 2: DXF Qualitätsprüfung (Maßketten + Schnitte)
        
        Analysiert:
        - Maßketten (Dimension Chains)
        - Schnittdarstellungen (Section Views)
        - Überbestimmung / Schließfehler
        - Material-Erkennung via Schraffuren
        
        Args:
            file_path: Pfad zur DXF-Datei
            
        Returns:
            DXFQualityResult mit Qualitäts-Metriken
        """
        self._ensure_initialized()
        
        path = Path(file_path)
        if not path.exists():
            return DXFQualityResult(
                success=False,
                file_path=file_path,
                issues=[{"type": "error", "message": f"Datei nicht gefunden: {file_path}"}]
            )
        
        issues = []
        dimension_result = {}
        section_result = {}
        
        # Prüfen ob MCP-Analyzer verfügbar sind
        has_mcp_analyzers = "dimension_chains" in self._analyzers or "section_views" in self._analyzers
        
        if has_mcp_analyzers:
            # MCP-Analyzer verwenden
            # Maßketten analysieren
            try:
                if "dimension_chains" in self._analyzers:
                    analyzer = self._analyzers["dimension_chains"]
                    result = analyzer.analyze(path)
                    dimension_result = result.to_dict() if hasattr(result, "to_dict") else {}
                    
                    # Issues aus Validierung extrahieren
                    if hasattr(result, "validation"):
                        for warning in result.validation.warnings:
                            issues.append({"type": "warning", "category": "dimension", "message": warning})
                        for error in result.validation.errors:
                            issues.append({"type": "error", "category": "dimension", "message": error})
                            
            except Exception as e:
                logger.warning(f"Maßketten-Analyse fehlgeschlagen: {e}")
                issues.append({"type": "error", "category": "dimension", "message": str(e)})
            
            # Schnittdarstellungen analysieren
            try:
                if "section_views" in self._analyzers:
                    analyzer = self._analyzers["section_views"]
                    result = analyzer.analyze(path)
                    section_result = result.to_dict() if hasattr(result, "to_dict") else {}
                    
            except Exception as e:
                logger.warning(f"Schnitt-Analyse fehlgeschlagen: {e}")
                issues.append({"type": "error", "category": "section", "message": str(e)})
        else:
            # Fallback: Lokalen DXFAnalyzer verwenden
            dimension_result, section_result, issues = await self._analyze_dxf_quality_fallback(path)
        
        # Qualitäts-Score berechnen
        quality_score = self._calculate_quality_score(dimension_result, section_result, issues)
        
        return DXFQualityResult(
            success=len([i for i in issues if i["type"] == "error"]) == 0,
            file_path=file_path,
            dimension_chains=dimension_result,
            section_views=section_result,
            quality_score=quality_score,
            issues=issues
        )
    
    async def _analyze_dxf_quality_fallback(self, path: Path) -> tuple:
        """
        Fallback-Analyse mit lokalem DXFAnalyzer.
        
        Wird verwendet wenn MCP-Analyzer nicht verfügbar sind.
        """
        dimension_result = {}
        section_result = {}
        issues = []
        
        try:
            from .dxf_analyzer import DXFAnalyzer
            
            # DXFAnalyzer initialisieren (unterstützt DXF und DWG)
            analyzer = DXFAnalyzer(path)
            
            # Vollständige Analyse durchführen
            report = analyzer.full_analysis()
            
            # Dimensionen extrahieren
            dimensions = report.dimensions if hasattr(report, 'dimensions') else []
            dimension_count = len(dimensions)
            
            dimension_result = {
                "chain_count": dimension_count,
                "chain_dimensions": dimension_count,
                "baseline_dimensions": 0,
                "dimensions": dimensions[:20],  # Erste 20 für Anzeige
            }
            
            # Schraffuren/Schnitte analysieren (aus Layern und Entities)
            entity_counts = report.entity_counts if hasattr(report, 'entity_counts') else {}
            hatch_count = entity_counts.get('HATCH', 0)
            
            section_result = {
                "section_view_count": hatch_count,
                "hatches": hatch_count,
                "materials": [],
            }
            
            # Issues aus Qualitätsprüfung
            quality_issues = report.issues if hasattr(report, 'issues') else []
            for issue in quality_issues:
                if isinstance(issue, dict):
                    issues.append(issue)
                else:
                    issues.append({"type": "warning", "category": "quality", "message": str(issue)})
            
            # Layer-Analyse für zusätzliche Infos
            layers = analyzer.analyze_layers()
            layer_count = len(layers)
            
            # Zusätzliche Infos in dimension_result
            dimension_result["layer_count"] = layer_count
            dimension_result["entity_count"] = report.entity_count if hasattr(report, 'entity_count') else 0
            dimension_result["source_format"] = report.source_format if hasattr(report, 'source_format') else "DXF"
            dimension_result["was_converted"] = report.was_converted if hasattr(report, 'was_converted') else False
            
            logger.info(f"DXF-Qualitätsanalyse erfolgreich: {dimension_count} Bemaßungen, {hatch_count} Schraffuren")
            
        except RuntimeError as e:
            # DWG-Konvertierung fehlgeschlagen (ODA nicht installiert)
            error_msg = str(e)
            if "ODA" in error_msg or "DWG" in error_msg:
                logger.warning(f"DWG-Konvertierung nicht möglich: {e}")
                issues.append({
                    "type": "error", 
                    "category": "conversion", 
                    "message": "DWG-Datei kann nicht gelesen werden. ODA File Converter ist nicht installiert. Bitte als DXF speichern oder ODA installieren."
                })
            else:
                logger.exception(f"DXF-Qualitätsanalyse Fallback fehlgeschlagen: {e}")
                issues.append({"type": "error", "category": "analysis", "message": error_msg})
                
        except Exception as e:
            logger.exception(f"DXF-Qualitätsanalyse Fallback fehlgeschlagen: {e}")
            issues.append({"type": "error", "category": "analysis", "message": str(e)})
        
        return dimension_result, section_result, issues
    
    def _calculate_quality_score(
        self, 
        dimensions: Dict, 
        sections: Dict, 
        issues: List[Dict]
    ) -> float:
        """Berechnet einen Qualitäts-Score (0-100)"""
        score = 100.0
        
        # Abzüge für Fehler
        errors = len([i for i in issues if i["type"] == "error"])
        warnings = len([i for i in issues if i["type"] == "warning"])
        
        score -= errors * 15
        score -= warnings * 5
        
        # Bonus für vollständige Analysen
        if dimensions.get("chain_count", 0) > 0:
            score += 5
        if sections.get("section_view_count", 0) > 0:
            score += 5
        
        # Abzug für überbestimmte Maßketten
        if dimensions.get("validation", {}).get("overdetermined_count", 0) > 0:
            score -= 10
        
        return max(0.0, min(100.0, score))
    
    # =========================================================================
    # Szenario 3: Natural Language Query
    # =========================================================================
    
    async def query_natural_language(
        self, 
        question: str,
        model_id: Optional[UUID] = None,
        file_path: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> NLQueryResult:
        """
        Beantwortet eine Frage in natürlicher Sprache.
        
        Szenario 3: Natural Language Query
        
        Unterstützte Fragen:
        - "Welcher Raum ist am größten?"
        - "Wie viele Türen gibt es?"
        - "Gesamtfläche aller Räume?"
        - "Liste alle Räume im 1. OG"
        
        Args:
            question: Frage in natürlicher Sprache
            model_id: Optional - UUID des IFC-Models
            file_path: Optional - Pfad zur CAD-Datei
            context: Optional - Zusätzlicher Kontext
            
        Returns:
            NLQueryResult mit Antwort
        """
        self._ensure_initialized()
        
        question_lower = question.lower()
        
        # Pattern Matching für häufige Fragen
        if model_id:
            return await self._query_from_model(question, model_id)
        elif file_path:
            return await self._query_from_file(question, file_path)
        else:
            # Allgemeine Frage ohne Datei-Kontext
            return NLQueryResult(
                success=False,
                query=question,
                answer="Bitte geben Sie eine CAD-Datei oder ein Modell an, um Fragen zu stellen.",
                confidence=0.0
            )
    
    async def _query_from_model(self, question: str, model_id: UUID) -> NLQueryResult:
        """Query basierend auf einem Django Model"""
        from apps.cad_hub.models import IFCModel, Room, Door, Window
        
        question_lower = question.lower()
        
        try:
            model = IFCModel.objects.get(pk=model_id)
            rooms = Room.objects.filter(ifc_model=model)
            doors = Door.objects.filter(ifc_model=model)
            windows = Window.objects.filter(ifc_model=model)
            
            # Größter Raum
            if "größt" in question_lower and "raum" in question_lower:
                largest = rooms.order_by("-area").first()
                if largest:
                    return NLQueryResult(
                        success=True,
                        query=question,
                        answer=f"Der größte Raum ist **{largest.name}** mit **{largest.area:.1f} m²** "
                               f"auf dem Geschoss **{largest.floor.name if largest.floor else 'unbekannt'}**.",
                        data={"room": largest.name, "area": largest.area, "floor": str(largest.floor)},
                        source_file=str(model_id),
                        confidence=1.0
                    )
            
            # Kleinster Raum
            if "kleinst" in question_lower and "raum" in question_lower:
                smallest = rooms.filter(area__gt=0).order_by("area").first()
                if smallest:
                    return NLQueryResult(
                        success=True,
                        query=question,
                        answer=f"Der kleinste Raum ist **{smallest.name}** mit **{smallest.area:.1f} m²**.",
                        data={"room": smallest.name, "area": smallest.area},
                        source_file=str(model_id),
                        confidence=1.0
                    )
            
            # Anzahl Räume
            if "wie viel" in question_lower and "räume" in question_lower:
                count = rooms.count()
                return NLQueryResult(
                    success=True,
                    query=question,
                    answer=f"Das Modell enthält **{count} Räume**.",
                    data={"count": count},
                    source_file=str(model_id),
                    confidence=1.0
                )
            
            # Anzahl Türen
            if "tür" in question_lower and ("wie viel" in question_lower or "anzahl" in question_lower):
                count = doors.count()
                return NLQueryResult(
                    success=True,
                    query=question,
                    answer=f"Das Modell enthält **{count} Türen**.",
                    data={"count": count},
                    source_file=str(model_id),
                    confidence=1.0
                )
            
            # Anzahl Fenster
            if "fenster" in question_lower and ("wie viel" in question_lower or "anzahl" in question_lower):
                count = windows.count()
                return NLQueryResult(
                    success=True,
                    query=question,
                    answer=f"Das Modell enthält **{count} Fenster**.",
                    data={"count": count},
                    source_file=str(model_id),
                    confidence=1.0
                )
            
            # Gesamtfläche
            if "gesamt" in question_lower and "fläche" in question_lower:
                from django.db.models import Sum
                total = rooms.aggregate(Sum("area"))["area__sum"] or 0
                return NLQueryResult(
                    success=True,
                    query=question,
                    answer=f"Die Gesamtfläche aller Räume beträgt **{total:.1f} m²**.",
                    data={"total_area": total, "room_count": rooms.count()},
                    source_file=str(model_id),
                    confidence=1.0
                )
            
            # Liste Räume
            if "liste" in question_lower and "räume" in question_lower:
                room_list = list(rooms.values("name", "area", "floor__name")[:20])
                answer_lines = ["**Raumliste:**\n"]
                for r in room_list:
                    answer_lines.append(f"- {r['name']}: {r['area']:.1f} m² ({r['floor__name'] or '-'})")
                
                return NLQueryResult(
                    success=True,
                    query=question,
                    answer="\n".join(answer_lines),
                    data={"rooms": room_list},
                    source_file=str(model_id),
                    confidence=1.0
                )
            
            # Fallback
            return NLQueryResult(
                success=False,
                query=question,
                answer="Ich konnte die Frage nicht verstehen. Versuchen Sie:\n"
                       "- 'Welcher Raum ist am größten?'\n"
                       "- 'Wie viele Türen gibt es?'\n"
                       "- 'Gesamtfläche aller Räume?'\n"
                       "- 'Liste alle Räume'",
                source_file=str(model_id),
                confidence=0.3
            )
            
        except IFCModel.DoesNotExist:
            return NLQueryResult(
                success=False,
                query=question,
                answer=f"Modell mit ID {model_id} nicht gefunden.",
                confidence=0.0
            )
        except Exception as e:
            logger.exception(f"NL Query fehlgeschlagen: {e}")
            return NLQueryResult(
                success=False,
                query=question,
                answer=f"Fehler bei der Verarbeitung: {str(e)}",
                confidence=0.0
            )
    
    async def _query_from_file(self, question: str, file_path: str) -> NLQueryResult:
        """Query basierend auf einer Datei"""
        # Erst Datei analysieren
        analysis = await self.analyze_file(file_path)
        
        if not analysis.success:
            return NLQueryResult(
                success=False,
                query=question,
                answer=f"Datei-Analyse fehlgeschlagen: {', '.join(analysis.errors)}",
                source_file=file_path,
                confidence=0.0
            )
        
        # Dann Frage beantworten basierend auf Analyse-Daten
        data = analysis.data
        question_lower = question.lower()
        
        # Entity-Zählung
        if "wie viel" in question_lower or "anzahl" in question_lower:
            if "entit" in question_lower:
                count = data.get("total_entities", data.get("entity_count", 0))
                return NLQueryResult(
                    success=True,
                    query=question,
                    answer=f"Die Datei enthält **{count} Entities**.",
                    data={"count": count},
                    source_file=file_path,
                    confidence=1.0
                )
        
        # Fallback: Markdown Report zurückgeben
        return NLQueryResult(
            success=True,
            query=question,
            answer=analysis.markdown_report or "Keine detaillierte Antwort verfügbar.",
            data=data,
            source_file=file_path,
            confidence=0.5
        )
    
    # =========================================================================
    # Szenario 4: Batch-Analyse
    # =========================================================================
    
    async def batch_analyze(
        self, 
        directory: str,
        extensions: Optional[List[str]] = None,
        recursive: bool = False
    ) -> BatchResult:
        """
        Analysiert mehrere CAD-Dateien in einem Verzeichnis.
        
        Szenario 4: Multi-Format Batch-Analyse
        
        Args:
            directory: Pfad zum Verzeichnis
            extensions: Liste der Dateiendungen (z.B. [".ifc", ".dxf"])
            recursive: Unterverzeichnisse einbeziehen
            
        Returns:
            BatchResult mit allen Ergebnissen
        """
        self._ensure_initialized()
        
        if extensions is None:
            extensions = [".ifc", ".dxf", ".dwg", ".igs", ".iges", ".fbx", ".gltf", ".glb", ".3mf", ".ply"]
        
        path = Path(directory)
        if not path.exists() or not path.is_dir():
            return BatchResult(
                success=False,
                total_files=0,
                analyzed=0,
                failed=0,
                summary={"error": f"Verzeichnis nicht gefunden: {directory}"}
            )
        
        # Dateien sammeln
        files = []
        pattern = "**/*" if recursive else "*"
        for ext in extensions:
            files.extend(path.glob(f"{pattern}{ext}"))
        
        results = []
        analyzed = 0
        failed = 0
        format_counts = {}
        
        # Alle Dateien analysieren
        for file in files:
            result = await self.analyze_file(str(file))
            results.append(result)
            
            if result.success:
                analyzed += 1
                fmt = result.format.value
                format_counts[fmt] = format_counts.get(fmt, 0) + 1
            else:
                failed += 1
        
        return BatchResult(
            success=failed == 0,
            total_files=len(files),
            analyzed=analyzed,
            failed=failed,
            results=results,
            summary={
                "directory": directory,
                "format_distribution": format_counts,
                "extensions_searched": extensions,
            }
        )
    
    # =========================================================================
    # Hilfsmethoden
    # =========================================================================
    
    async def get_supported_formats(self) -> Dict[str, Any]:
        """Gibt alle unterstützten Formate zurück"""
        return {
            "formats": [
                {"name": "IFC", "extensions": [".ifc"], "description": "Industry Foundation Classes (BIM)"},
                {"name": "DXF", "extensions": [".dxf"], "description": "Drawing Exchange Format (2D/3D)"},
                {"name": "DWG", "extensions": [".dwg"], "description": "AutoCAD Drawing (via Konvertierung)"},
                {"name": "IGES", "extensions": [".igs", ".iges"], "description": "Initial Graphics Exchange Specification"},
                {"name": "FBX", "extensions": [".fbx"], "description": "Filmbox (3D/Animation)"},
                {"name": "GLTF", "extensions": [".gltf", ".glb"], "description": "GL Transmission Format (Web3D)"},
                {"name": "3MF", "extensions": [".3mf"], "description": "3D Manufacturing Format"},
                {"name": "PLY", "extensions": [".ply"], "description": "Polygon File Format (Point Clouds)"},
                {"name": "STEP", "extensions": [".stp", ".step"], "description": "Standard for Exchange (CAD)"},
            ],
            "features": {
                "analysis": ["IFC", "DXF", "IGES", "FBX", "GLTF", "3MF", "PLY"],
                "dimension_chains": ["DXF"],
                "section_views": ["DXF"],
                "nl_query": ["IFC"],
            }
        }


# =============================================================================
# Singleton Factory
# =============================================================================

_bridge_instance: Optional[CADMCPBridge] = None


def get_mcp_bridge(mode: str = "local") -> CADMCPBridge:
    """
    Factory für CADMCPBridge Singleton.
    
    Usage:
        bridge = get_mcp_bridge()
        result = await bridge.analyze_file("model.ifc")
    """
    global _bridge_instance
    
    if _bridge_instance is None:
        _bridge_instance = CADMCPBridge(mode=mode)
    
    return _bridge_instance


# =============================================================================
# Convenience Functions
# =============================================================================

async def analyze_cad_file(file_path: str, format: str = "auto") -> AnalysisResult:
    """Shortcut für Datei-Analyse"""
    bridge = get_mcp_bridge()
    return await bridge.analyze_file(file_path, format)


async def check_dxf_quality(file_path: str) -> DXFQualityResult:
    """Shortcut für DXF-Qualitätsprüfung"""
    bridge = get_mcp_bridge()
    return await bridge.check_dxf_quality(file_path)


async def ask_cad_question(question: str, model_id: UUID = None, file_path: str = None) -> NLQueryResult:
    """Shortcut für NL Query"""
    bridge = get_mcp_bridge()
    return await bridge.query_natural_language(question, model_id, file_path)


async def batch_analyze_directory(directory: str, extensions: List[str] = None) -> BatchResult:
    """Shortcut für Batch-Analyse"""
    bridge = get_mcp_bridge()
    return await bridge.batch_analyze(directory, extensions)
