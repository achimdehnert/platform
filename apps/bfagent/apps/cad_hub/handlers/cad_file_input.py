"""
CADFileInputHandler - Format-Erkennung & Konvertierung.

Verarbeitet IFC, DXF und DWG Dateien und stellt sie
für nachfolgende Handler bereit.
"""
import logging
from pathlib import Path
from typing import Optional, Union
import tempfile

from .base import (
    BaseCADHandler,
    CADHandlerResult,
    CADHandlerError,
    CADFormat,
    HandlerStatus,
)

logger = logging.getLogger(__name__)


class CADFileInputHandler(BaseCADHandler):
    """
    Handler für CAD-Datei-Eingabe.
    
    Funktionen:
    - Format-Erkennung (IFC/DXF/DWG)
    - DWG → DXF Konvertierung
    - Datei-Validierung
    - Basis-Metadaten-Extraktion
    
    Input:
        file_path: Pfad zur CAD-Datei
        file_content: Optional - Dateiinhalt als bytes
        filename: Optional - Dateiname (bei file_content)
    
    Output:
        format: Erkanntes Format (ifc/dxf/dwg)
        file_path: Pfad zur verarbeiteten Datei
        was_converted: True wenn DWG→DXF konvertiert
        loader: CADLoaderService Instanz (für DXF)
        ifc_model: IFC Modell (für IFC)
    """
    
    name = "CADFileInputHandler"
    description = "Format-Erkennung & Konvertierung für CAD-Dateien"
    required_inputs = []  # Either file_path or file_content
    optional_inputs = ["file_path", "file_content", "filename"]
    
    def execute(self, input_data: dict) -> CADHandlerResult:
        """Verarbeitet CAD-Datei."""
        result = CADHandlerResult(
            success=True,
            handler_name=self.name,
            status=HandlerStatus.RUNNING,
        )
        
        # Get file path or content
        file_path = input_data.get("file_path")
        file_content = input_data.get("file_content")
        filename = input_data.get("filename", "upload.dxf")
        
        if not file_path and not file_content:
            result.add_error("Keine Datei angegeben (file_path oder file_content)")
            return result
        
        # Handle bytes input - write to temp file
        if file_content and not file_path:
            suffix = Path(filename).suffix.lower() or ".dxf"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                f.write(file_content)
                file_path = f.name
            result.data["temp_file"] = True
        
        file_path = Path(file_path)
        
        # Validate file exists
        if not file_path.exists():
            result.add_error(f"Datei nicht gefunden: {file_path}")
            return result
        
        # Detect format
        cad_format = CADFormat.from_extension(file_path)
        result.data["original_format"] = cad_format.value
        result.data["original_path"] = str(file_path)
        
        if cad_format == CADFormat.UNKNOWN:
            result.add_error(f"Unbekanntes Format: {file_path.suffix}")
            return result
        
        logger.info(f"[{self.name}] Format erkannt: {cad_format.value}")
        
        # Process based on format
        if cad_format == CADFormat.IFC:
            return self._process_ifc(file_path, result)
        elif cad_format == CADFormat.DWG:
            return self._process_dwg(file_path, result)
        else:  # DXF
            return self._process_dxf(file_path, result)
    
    def _process_ifc(self, file_path: Path, result: CADHandlerResult) -> CADHandlerResult:
        """Verarbeitet IFC-Datei."""
        try:
            from ..services import IFCParserService
            
            parser = IFCParserService()
            ifc_result = parser.parse_file(str(file_path))
            
            if not ifc_result.success:
                result.add_error(f"IFC-Parsing fehlgeschlagen: {ifc_result.error}")
                return result
            
            result.data.update({
                "format": "ifc",
                "file_path": str(file_path),
                "was_converted": False,
                "ifc_result": ifc_result,
                "rooms": ifc_result.rooms,
                "room_count": len(ifc_result.rooms),
                "total_area": sum(r.area for r in ifc_result.rooms if r.area),
            })
            
            result.status = HandlerStatus.SUCCESS
            logger.info(f"[{self.name}] IFC geladen: {len(ifc_result.rooms)} Räume")
            
        except ImportError:
            result.add_error("IFCParserService nicht verfügbar")
        except Exception as e:
            result.add_error(f"IFC-Verarbeitung fehlgeschlagen: {e}")
        
        return result
    
    def _process_dwg(self, file_path: Path, result: CADHandlerResult) -> CADHandlerResult:
        """Konvertiert DWG zu DXF und verarbeitet."""
        try:
            from ..services import DWGConverterService
            
            converter = DWGConverterService()
            available = converter.get_available_methods()
            
            if not any(m in available for m in ['oda', 'libredwg']):
                result.add_error(
                    "DWG-Konvertierung nicht verfügbar. "
                    "Bitte ODA File Converter installieren: "
                    "https://www.opendesign.com/guestfiles/oda_file_converter"
                )
                return result
            
            # Convert
            conversion = converter.convert_to_dxf(file_path)
            
            if not conversion.success:
                result.add_error(f"DWG-Konvertierung fehlgeschlagen: {conversion.error}")
                return result
            
            result.data["was_converted"] = True
            result.data["conversion_method"] = conversion.method
            result.add_warning(f"DWG wurde zu DXF konvertiert (Methode: {conversion.method})")
            
            # Process converted DXF
            return self._process_dxf(Path(conversion.dxf_path), result)
            
        except ImportError:
            result.add_error("DWGConverterService nicht verfügbar")
        except Exception as e:
            result.add_error(f"DWG-Verarbeitung fehlgeschlagen: {e}")
        
        return result
    
    def _process_dxf(self, file_path: Path, result: CADHandlerResult) -> CADHandlerResult:
        """Verarbeitet DXF-Datei."""
        try:
            from ..services import CADLoaderService
            
            loader = CADLoaderService.from_file(file_path)
            
            # Get basic statistics
            stats = loader.get_statistics()
            analysis = loader.get_analysis()
            
            result.data.update({
                "format": "dxf",
                "file_path": str(file_path),
                "was_converted": result.data.get("was_converted", False),
                "_loader": loader,  # Prefix with _ to mark as non-serializable
                "statistics": stats,
                "total_entities": stats.get("total_entities", 0),
                "layer_count": stats.get("layer_count", 0),
                "dxf_version": analysis.dxf_version,
                "units": analysis.units,
                "bounding_box": stats.get("bounding_box"),
            })
            
            result.status = HandlerStatus.SUCCESS
            logger.info(
                f"[{self.name}] DXF geladen: "
                f"{stats.get('total_entities', 0)} Entities, "
                f"{stats.get('layer_count', 0)} Layer"
            )
            
        except ImportError:
            result.add_error("CADLoaderService nicht verfügbar")
        except Exception as e:
            result.add_error(f"DXF-Verarbeitung fehlgeschlagen: {e}")
        
        return result
