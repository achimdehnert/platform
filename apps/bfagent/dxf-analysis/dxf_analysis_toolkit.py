#!/usr/bin/env python3
"""
DXF/DWG Analyse Toolkit - Umfassende Analyse- und Erkennungs-Bibliothek

Fokus: Auswertung, Extraktion, Erkennung
Unterstützt: DXF (nativ) und DWG (via ODA File Converter)
Version: 2.1
"""

import ezdxf
from ezdxf.math import Vec3, BoundingBox
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from typing import Optional, Iterator, Any, Union
from pathlib import Path
from enum import Enum, auto
import json
import math
import subprocess
import shutil
import tempfile
import os


# ============================================================================
# DATENSTRUKTUREN
# ============================================================================

class EntityCategory(Enum):
    """Kategorisierung von DXF-Entities."""
    PRIMITIVE = auto()      # LINE, POINT
    CURVE = auto()          # ARC, CIRCLE, ELLIPSE, SPLINE
    POLYLINE = auto()       # LWPOLYLINE, POLYLINE
    SURFACE = auto()        # HATCH, SOLID, 3DFACE
    TEXT = auto()           # TEXT, MTEXT
    DIMENSION = auto()      # DIMENSION, LEADER
    REFERENCE = auto()      # INSERT (Block-Referenz)
    OTHER = auto()


ENTITY_CATEGORIES = {
    "POINT": EntityCategory.PRIMITIVE,
    "LINE": EntityCategory.PRIMITIVE,
    "XLINE": EntityCategory.PRIMITIVE,
    "RAY": EntityCategory.PRIMITIVE,
    "CIRCLE": EntityCategory.CURVE,
    "ARC": EntityCategory.CURVE,
    "ELLIPSE": EntityCategory.CURVE,
    "SPLINE": EntityCategory.CURVE,
    "LWPOLYLINE": EntityCategory.POLYLINE,
    "POLYLINE": EntityCategory.POLYLINE,
    "HATCH": EntityCategory.SURFACE,
    "SOLID": EntityCategory.SURFACE,
    "3DFACE": EntityCategory.SURFACE,
    "MESH": EntityCategory.SURFACE,
    "TEXT": EntityCategory.TEXT,
    "MTEXT": EntityCategory.TEXT,
    "ATTRIB": EntityCategory.TEXT,
    "ATTDEF": EntityCategory.TEXT,
    "DIMENSION": EntityCategory.DIMENSION,
    "LEADER": EntityCategory.DIMENSION,
    "TOLERANCE": EntityCategory.DIMENSION,
    "INSERT": EntityCategory.REFERENCE,
}


@dataclass
class LayerInfo:
    """Layer-Informationen."""
    name: str
    color: int
    linetype: str
    is_on: bool
    is_frozen: bool
    is_locked: bool
    entity_count: int = 0
    entity_types: dict = field(default_factory=dict)


@dataclass
class BlockInfo:
    """Block-Informationen."""
    name: str
    base_point: tuple
    entity_count: int
    has_attributes: bool
    attribute_tags: list
    insert_count: int = 0
    insert_positions: list = field(default_factory=list)


@dataclass
class TextInfo:
    """Extrahierte Text-Information."""
    content: str
    position: tuple
    height: float
    rotation: float
    layer: str
    entity_type: str
    style: str = ""


@dataclass
class DimensionInfo:
    """Extrahierte Bemaßungs-Information."""
    measurement: float
    text_override: str
    dim_type: str
    layer: str
    definition_points: list = field(default_factory=list)


@dataclass
class GeometryInfo:
    """Geometrische Entity-Information."""
    entity_type: str
    layer: str
    color: int
    handle: str
    geometry: dict  # Typ-spezifische Geometrie-Daten


@dataclass 
class AnalysisReport:
    """Vollständiger Analyse-Report."""
    filename: str
    dxf_version: str
    encoding: str
    units: str
    
    # Statistiken
    total_entities: int
    entity_statistics: dict
    category_statistics: dict
    
    # Struktur
    layers: list
    blocks: list
    
    # Geometrie
    bounding_box: dict
    estimated_area: float
    
    # Inhalte
    texts: list
    dimensions: list
    
    # Qualität
    issues: list
    
    # DWG-spezifisch
    source_format: str = "DXF"
    was_converted: bool = False


# ============================================================================
# DWG KONVERTIERUNG
# ============================================================================

class DWGConverter:
    """
    DWG zu DXF Konverter via ODA File Converter.
    
    Der ODA File Converter muss installiert sein:
    - Windows: https://www.opendesign.com/guestfiles/oda_file_converter
    - Linux: Als .deb, .rpm oder AppImage verfügbar
    - macOS: Als .dmg verfügbar
    
    Verwendung:
        converter = DWGConverter()
        if converter.is_available:
            dxf_path = converter.convert_to_dxf("drawing.dwg")
    """
    
    # Bekannte Pfade für ODA File Converter
    KNOWN_PATHS = {
        "windows": [
            r"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe",
            r"C:\Program Files (x86)\ODA\ODAFileConverter\ODAFileConverter.exe",
        ],
        "linux": [
            "/usr/bin/ODAFileConverter",
            "/opt/ODAFileConverter/ODAFileConverter",
            "/usr/local/bin/ODAFileConverter",
        ],
        "darwin": [  # macOS
            "/Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter",
            "/usr/local/bin/ODAFileConverter",
        ]
    }
    
    # DXF Versionen
    DXF_VERSIONS = {
        "R12": "ACAD12",
        "R14": "ACAD14",
        "R2000": "ACAD2000",
        "R2004": "ACAD2004",
        "R2007": "ACAD2007",
        "R2010": "ACAD2010",
        "R2013": "ACAD2013",
        "R2018": "ACAD2018",
    }
    
    def __init__(self, oda_path: Optional[str] = None):
        """
        Initialisiert den Konverter.
        
        Args:
            oda_path: Optionaler Pfad zum ODA File Converter.
                      Wenn None, wird automatisch gesucht.
        """
        self.oda_path = oda_path or self._find_oda_converter()
        self._temp_dirs = []  # Track temp dirs for cleanup
    
    def _find_oda_converter(self) -> Optional[str]:
        """Sucht den ODA File Converter auf dem System."""
        import platform
        system = platform.system().lower()
        
        # 1. Prüfe ob im PATH
        which_result = shutil.which("ODAFileConverter")
        if which_result:
            return which_result
        
        # 2. Prüfe bekannte Pfade
        paths_to_check = self.KNOWN_PATHS.get(system, [])
        for path in paths_to_check:
            if Path(path).exists():
                return path
        
        # 3. Prüfe ezdxf config (falls vorhanden)
        try:
            from ezdxf import options
            if hasattr(options, 'odafc_addon'):
                config_path = options.odafc_addon.get('win_exec_path') or \
                             options.odafc_addon.get('unix_exec_path')
                if config_path and Path(config_path).exists():
                    return config_path
        except:
            pass
        
        return None
    
    @property
    def is_available(self) -> bool:
        """Prüft ob der ODA File Converter verfügbar ist."""
        return self.oda_path is not None and Path(self.oda_path).exists()
    
    def get_status(self) -> dict:
        """Gibt Statusinformationen zurück."""
        return {
            "available": self.is_available,
            "path": self.oda_path,
            "supported_versions": list(self.DXF_VERSIONS.keys()),
        }
    
    def convert_to_dxf(
        self, 
        dwg_path: Union[str, Path], 
        output_path: Optional[Union[str, Path]] = None,
        dxf_version: str = "R2018",
        audit: bool = True
    ) -> Optional[Path]:
        """
        Konvertiert eine DWG-Datei zu DXF.
        
        Args:
            dwg_path: Pfad zur DWG-Datei
            output_path: Optionaler Ausgabepfad. Wenn None, wird ein temp-Pfad verwendet.
            dxf_version: Ziel-DXF-Version (R12, R2000, R2004, R2007, R2010, R2013, R2018)
            audit: Führe Audit der Eingabedatei durch
            
        Returns:
            Pfad zur konvertierten DXF-Datei oder None bei Fehler
        """
        if not self.is_available:
            raise RuntimeError(
                "ODA File Converter nicht gefunden. "
                "Bitte installieren von: https://www.opendesign.com/guestfiles/oda_file_converter"
            )
        
        dwg_path = Path(dwg_path)
        if not dwg_path.exists():
            raise FileNotFoundError(f"DWG-Datei nicht gefunden: {dwg_path}")
        
        if not dwg_path.suffix.lower() == ".dwg":
            raise ValueError(f"Keine DWG-Datei: {dwg_path}")
        
        # Output-Verzeichnis bestimmen
        if output_path:
            output_dir = Path(output_path).parent
            output_name = Path(output_path).stem
        else:
            output_dir = Path(tempfile.mkdtemp(prefix="dwg_convert_"))
            output_name = dwg_path.stem
            self._temp_dirs.append(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # ODA Version String
        oda_version = self.DXF_VERSIONS.get(dxf_version, "ACAD2018")
        
        # ODA File Converter Kommando
        # Syntax: ODAFileConverter <input_folder> <output_folder> <output_version> <output_type> <recurse> <audit>
        cmd = [
            self.oda_path,
            str(dwg_path.parent),      # Input folder
            str(output_dir),            # Output folder
            oda_version,                # Output version
            "DXF",                      # Output type
            "0",                        # Recurse: No
            "1" if audit else "0",      # Audit
            str(dwg_path.name)          # Input file filter
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120  # 2 Minuten Timeout
            )
            
            # Suche nach der konvertierten Datei
            expected_output = output_dir / f"{dwg_path.stem}.dxf"
            
            if expected_output.exists():
                return expected_output
            
            # Fallback: Suche nach .dxf Dateien im Output-Verzeichnis
            dxf_files = list(output_dir.glob("*.dxf"))
            if dxf_files:
                return dxf_files[0]
            
            # Fehler loggen
            print(f"Konvertierung fehlgeschlagen. STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return None
            
        except subprocess.TimeoutExpired:
            print("Konvertierung: Timeout nach 120 Sekunden")
            return None
        except Exception as e:
            print(f"Konvertierungsfehler: {e}")
            return None
    
    def convert_to_dwg(
        self,
        dxf_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        dwg_version: str = "R2018",
        audit: bool = True
    ) -> Optional[Path]:
        """
        Konvertiert eine DXF-Datei zu DWG.
        
        Args:
            dxf_path: Pfad zur DXF-Datei
            output_path: Optionaler Ausgabepfad
            dwg_version: Ziel-DWG-Version
            audit: Führe Audit durch
            
        Returns:
            Pfad zur konvertierten DWG-Datei oder None bei Fehler
        """
        if not self.is_available:
            raise RuntimeError("ODA File Converter nicht gefunden.")
        
        dxf_path = Path(dxf_path)
        if not dxf_path.exists():
            raise FileNotFoundError(f"DXF-Datei nicht gefunden: {dxf_path}")
        
        if output_path:
            output_dir = Path(output_path).parent
        else:
            output_dir = Path(tempfile.mkdtemp(prefix="dxf_convert_"))
            self._temp_dirs.append(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        oda_version = self.DXF_VERSIONS.get(dwg_version, "ACAD2018")
        
        cmd = [
            self.oda_path,
            str(dxf_path.parent),
            str(output_dir),
            oda_version,
            "DWG",  # Output type = DWG
            "0",
            "1" if audit else "0",
            str(dxf_path.name)
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            expected_output = output_dir / f"{dxf_path.stem}.dwg"
            if expected_output.exists():
                return expected_output
            
            dwg_files = list(output_dir.glob("*.dwg"))
            if dwg_files:
                return dwg_files[0]
            
            return None
            
        except Exception as e:
            print(f"Konvertierungsfehler: {e}")
            return None
    
    def cleanup(self):
        """Räumt temporäre Verzeichnisse auf."""
        for temp_dir in self._temp_dirs:
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
        self._temp_dirs = []
    
    def __del__(self):
        """Cleanup bei Objektzerstörung."""
        self.cleanup()


def load_cad_file(filepath: Union[str, Path]) -> tuple:
    """
    Universelle Ladefunktion für DXF und DWG Dateien.
    
    Args:
        filepath: Pfad zur CAD-Datei (.dxf oder .dwg)
        
    Returns:
        Tuple (ezdxf.Drawing, was_converted: bool, original_format: str)
    """
    filepath = Path(filepath)
    suffix = filepath.suffix.lower()
    
    if suffix == ".dxf":
        doc = ezdxf.readfile(str(filepath))
        return doc, False, "DXF"
    
    elif suffix == ".dwg":
        # Versuche ezdxf odafc Addon
        try:
            from ezdxf.addons import odafc
            doc = odafc.readfile(str(filepath))
            return doc, True, "DWG"
        except ImportError:
            pass
        except Exception as e:
            print(f"ezdxf odafc Fehler: {e}")
        
        # Fallback: Eigener Konverter
        converter = DWGConverter()
        if converter.is_available:
            dxf_path = converter.convert_to_dxf(filepath)
            if dxf_path:
                doc = ezdxf.readfile(str(dxf_path))
                return doc, True, "DWG"
        
        raise RuntimeError(
            f"Kann DWG-Datei nicht laden: {filepath}\n"
            "ODA File Converter nicht gefunden. "
            "Bitte installieren von: https://www.opendesign.com/guestfiles/oda_file_converter"
        )
    
    else:
        raise ValueError(f"Nicht unterstütztes Format: {suffix} (nur .dxf und .dwg)")


# ============================================================================
# HAUPT-ANALYSEKLASSE
# ============================================================================

class DXFAnalyzer:
    """
    Umfassende DXF/DWG-Analyse-Engine.
    
    Unterstützt sowohl DXF als auch DWG Dateien.
    DWG-Dateien werden automatisch via ODA File Converter konvertiert.
    
    Verwendung:
        analyzer = DXFAnalyzer("zeichnung.dxf")  # oder .dwg
        report = analyzer.full_analysis()
        analyzer.export_json("report.json")
    """
    
    def __init__(self, filepath: str | Path):
        """
        Initialisiert den Analyzer.
        
        Args:
            filepath: Pfad zur DXF- oder DWG-Datei
        """
        self.filepath = Path(filepath)
        
        # Lade Datei (DXF oder DWG)
        self.doc, self._was_converted, self._source_format = load_cad_file(filepath)
        self.msp = self.doc.modelspace()
        
        # Caches für Performance
        self._entity_cache: list = None
        self._layer_cache: dict = None
        self._block_cache: dict = None
    
    @property
    def source_format(self) -> str:
        """Gibt das Original-Format zurück (DXF oder DWG)."""
        return self._source_format
    
    @property
    def was_converted(self) -> bool:
        """Gibt zurück ob die Datei konvertiert wurde."""
        return self._was_converted
    
    # -------------------------------------------------------------------------
    # ENTITY-ANALYSE
    # -------------------------------------------------------------------------
    
    @property
    def entities(self) -> list:
        """Alle Entities (gecached)."""
        if self._entity_cache is None:
            self._entity_cache = list(self.msp)
        return self._entity_cache
    
    def count_entities(self) -> dict[str, int]:
        """Zählt Entities nach Typ."""
        return dict(Counter(e.dxftype() for e in self.entities))
    
    def count_by_category(self) -> dict[str, int]:
        """Zählt Entities nach Kategorie."""
        counts = Counter()
        for entity in self.entities:
            cat = ENTITY_CATEGORIES.get(entity.dxftype(), EntityCategory.OTHER)
            counts[cat.name] += 1
        return dict(counts)
    
    def get_entities_by_type(self, entity_type: str) -> Iterator:
        """Filtert Entities nach Typ."""
        return self.msp.query(entity_type)
    
    def get_entities_by_layer(self, layer_name: str) -> Iterator:
        """Filtert Entities nach Layer."""
        return self.msp.query(f"*[layer=='{layer_name}']")
    
    def get_entities_by_category(self, category: EntityCategory) -> list:
        """Filtert Entities nach Kategorie."""
        return [
            e for e in self.entities 
            if ENTITY_CATEGORIES.get(e.dxftype(), EntityCategory.OTHER) == category
        ]
    
    # -------------------------------------------------------------------------
    # LAYER-ANALYSE
    # -------------------------------------------------------------------------
    
    def analyze_layers(self) -> list[LayerInfo]:
        """Analysiert alle Layer."""
        if self._layer_cache is not None:
            return list(self._layer_cache.values())
        
        # Layer-Entity-Zuordnung
        layer_entities = defaultdict(lambda: {"count": 0, "types": Counter()})
        for entity in self.entities:
            layer = entity.dxf.layer
            layer_entities[layer]["count"] += 1
            layer_entities[layer]["types"][entity.dxftype()] += 1
        
        layers = []
        for layer in self.doc.layers:
            name = layer.dxf.name
            # Handle both property and method access for compatibility
            is_on = layer.is_on() if callable(layer.is_on) else layer.is_on
            is_frozen = layer.is_frozen() if callable(layer.is_frozen) else layer.is_frozen
            is_locked = layer.is_locked() if callable(layer.is_locked) else layer.is_locked
            
            info = LayerInfo(
                name=name,
                color=layer.dxf.color,
                linetype=layer.dxf.linetype,
                is_on=is_on,
                is_frozen=is_frozen,
                is_locked=is_locked,
                entity_count=layer_entities[name]["count"],
                entity_types=dict(layer_entities[name]["types"])
            )
            layers.append(info)
        
        self._layer_cache = {l.name: l for l in layers}
        return layers
    
    def get_layer_names(self) -> list[str]:
        """Liste aller Layer-Namen."""
        return [layer.dxf.name for layer in self.doc.layers]
    
    def get_empty_layers(self) -> list[str]:
        """Findet leere Layer."""
        layers = self.analyze_layers()
        return [l.name for l in layers if l.entity_count == 0]
    
    def get_layer_statistics(self) -> dict:
        """Statistiken über Layer."""
        layers = self.analyze_layers()
        return {
            "total": len(layers),
            "with_entities": sum(1 for l in layers if l.entity_count > 0),
            "empty": sum(1 for l in layers if l.entity_count == 0),
            "frozen": sum(1 for l in layers if l.is_frozen),
            "off": sum(1 for l in layers if not l.is_on),
        }
    
    # -------------------------------------------------------------------------
    # BLOCK-ANALYSE
    # -------------------------------------------------------------------------
    
    def analyze_blocks(self) -> list[BlockInfo]:
        """Analysiert alle Block-Definitionen und deren Verwendung."""
        if self._block_cache is not None:
            return list(self._block_cache.values())
        
        # INSERT-Referenzen zählen
        insert_counts = Counter()
        insert_positions = defaultdict(list)
        
        for insert in self.msp.query("INSERT"):
            name = insert.dxf.name
            insert_counts[name] += 1
            insert_positions[name].append(tuple(insert.dxf.insert))
        
        blocks = []
        for block in self.doc.blocks:
            if block.name.startswith("*"):  # Interne Blöcke überspringen
                continue
            
            # Attribute-Definitionen finden
            attdefs = list(block.query("ATTDEF"))
            attr_tags = [a.dxf.tag for a in attdefs]
            
            info = BlockInfo(
                name=block.name,
                base_point=tuple(block.base_point),
                entity_count=len(list(block)),
                has_attributes=len(attdefs) > 0,
                attribute_tags=attr_tags,
                insert_count=insert_counts.get(block.name, 0),
                insert_positions=insert_positions.get(block.name, [])
            )
            blocks.append(info)
        
        self._block_cache = {b.name: b for b in blocks}
        return blocks
    
    def get_block_inserts(self, block_name: str) -> list[dict]:
        """Alle INSERT-Referenzen eines Blocks mit Attributen."""
        inserts = []
        
        for insert in self.msp.query(f"INSERT[name=='{block_name}']"):
            attribs = {}
            if insert.has_attrib:
                for attrib in insert.attribs:
                    attribs[attrib.dxf.tag] = attrib.dxf.text
            
            inserts.append({
                "handle": insert.dxf.handle,
                "position": tuple(insert.dxf.insert),
                "rotation": insert.dxf.rotation,
                "scale": (insert.dxf.xscale, insert.dxf.yscale, insert.dxf.zscale),
                "layer": insert.dxf.layer,
                "attributes": attribs
            })
        
        return inserts
    
    def get_unused_blocks(self) -> list[str]:
        """Findet nicht verwendete Block-Definitionen."""
        blocks = self.analyze_blocks()
        return [b.name for b in blocks if b.insert_count == 0]
    
    # -------------------------------------------------------------------------
    # GEOMETRIE-ANALYSE
    # -------------------------------------------------------------------------
    
    def calculate_bounding_box(self) -> dict:
        """Berechnet die Bounding Box aller Entities."""
        bbox = BoundingBox()
        
        for entity in self.entities:
            try:
                # Verschiedene Entity-Typen haben unterschiedliche Vertex-Methoden
                if hasattr(entity, 'vertices'):
                    for v in entity.vertices():
                        bbox.extend([v])
                elif entity.dxftype() == "LINE":
                    bbox.extend([entity.dxf.start, entity.dxf.end])
                elif entity.dxftype() == "CIRCLE":
                    c = entity.dxf.center
                    r = entity.dxf.radius
                    bbox.extend([
                        Vec3(c.x - r, c.y - r, c.z),
                        Vec3(c.x + r, c.y + r, c.z)
                    ])
                elif entity.dxftype() == "ARC":
                    c = entity.dxf.center
                    r = entity.dxf.radius
                    bbox.extend([
                        Vec3(c.x - r, c.y - r, c.z),
                        Vec3(c.x + r, c.y + r, c.z)
                    ])
                elif entity.dxftype() == "POINT":
                    bbox.extend([entity.dxf.location])
                elif entity.dxftype() in ("TEXT", "MTEXT"):
                    bbox.extend([entity.dxf.insert])
                elif entity.dxftype() == "INSERT":
                    bbox.extend([entity.dxf.insert])
            except (AttributeError, TypeError):
                pass
        
        if bbox.has_data:
            return {
                "min": {"x": bbox.extmin.x, "y": bbox.extmin.y, "z": bbox.extmin.z},
                "max": {"x": bbox.extmax.x, "y": bbox.extmax.y, "z": bbox.extmax.z},
                "size": {
                    "width": bbox.extmax.x - bbox.extmin.x,
                    "height": bbox.extmax.y - bbox.extmin.y,
                    "depth": bbox.extmax.z - bbox.extmin.z,
                },
                "center": {
                    "x": (bbox.extmin.x + bbox.extmax.x) / 2,
                    "y": (bbox.extmin.y + bbox.extmax.y) / 2,
                    "z": (bbox.extmin.z + bbox.extmax.z) / 2,
                }
            }
        return None
    
    def extract_geometry(self, entity_types: list[str] = None) -> list[GeometryInfo]:
        """
        Extrahiert Geometrie-Daten aus Entities.
        
        Args:
            entity_types: Filter für Entity-Typen (None = alle)
        """
        geometries = []
        
        for entity in self.entities:
            etype = entity.dxftype()
            
            if entity_types and etype not in entity_types:
                continue
            
            geom_data = self._extract_entity_geometry(entity)
            if geom_data:
                geometries.append(GeometryInfo(
                    entity_type=etype,
                    layer=entity.dxf.layer,
                    color=entity.dxf.color,
                    handle=entity.dxf.handle,
                    geometry=geom_data
                ))
        
        return geometries
    
    def _extract_entity_geometry(self, entity) -> dict:
        """Extrahiert Geometrie-Daten einer einzelnen Entity."""
        etype = entity.dxftype()
        
        if etype == "LINE":
            return {
                "start": tuple(entity.dxf.start),
                "end": tuple(entity.dxf.end),
                "length": entity.dxf.start.distance(entity.dxf.end)
            }
        
        elif etype == "CIRCLE":
            return {
                "center": tuple(entity.dxf.center),
                "radius": entity.dxf.radius,
                "area": math.pi * entity.dxf.radius ** 2,
                "circumference": 2 * math.pi * entity.dxf.radius
            }
        
        elif etype == "ARC":
            return {
                "center": tuple(entity.dxf.center),
                "radius": entity.dxf.radius,
                "start_angle": entity.dxf.start_angle,
                "end_angle": entity.dxf.end_angle,
                "arc_length": self._calculate_arc_length(entity)
            }
        
        elif etype == "LWPOLYLINE":
            points = list(entity.get_points("xy"))
            return {
                "points": points,
                "closed": entity.closed,
                "vertex_count": len(points),
                "perimeter": self._calculate_polyline_length(points, entity.closed),
                "area": self._calculate_polygon_area(points) if entity.closed else None
            }
        
        elif etype == "POINT":
            return {"location": tuple(entity.dxf.location)}
        
        elif etype == "ELLIPSE":
            return {
                "center": tuple(entity.dxf.center),
                "major_axis": tuple(entity.dxf.major_axis),
                "ratio": entity.dxf.ratio,
                "start_param": entity.dxf.start_param,
                "end_param": entity.dxf.end_param
            }
        
        return None
    
    def _calculate_arc_length(self, arc) -> float:
        """Berechnet die Bogenlänge eines ARC."""
        angle = abs(arc.dxf.end_angle - arc.dxf.start_angle)
        if angle > 180:
            angle = 360 - angle
        return math.radians(angle) * arc.dxf.radius
    
    def _calculate_polyline_length(self, points: list, closed: bool) -> float:
        """Berechnet die Länge einer Polylinie."""
        length = 0.0
        for i in range(len(points) - 1):
            dx = points[i+1][0] - points[i][0]
            dy = points[i+1][1] - points[i][1]
            length += math.sqrt(dx*dx + dy*dy)
        
        if closed and len(points) > 2:
            dx = points[0][0] - points[-1][0]
            dy = points[0][1] - points[-1][1]
            length += math.sqrt(dx*dx + dy*dy)
        
        return length
    
    def _calculate_polygon_area(self, points: list) -> float:
        """Berechnet die Fläche eines Polygons (Shoelace-Formel)."""
        n = len(points)
        if n < 3:
            return 0.0
        
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += points[i][0] * points[j][1]
            area -= points[j][0] * points[i][1]
        
        return abs(area) / 2.0
    
    # -------------------------------------------------------------------------
    # TEXT-EXTRAKTION
    # -------------------------------------------------------------------------
    
    def extract_texts(self) -> list[TextInfo]:
        """Extrahiert alle Texte aus der Zeichnung."""
        texts = []
        
        for entity in self.msp.query("TEXT MTEXT"):
            etype = entity.dxftype()
            
            if etype == "TEXT":
                texts.append(TextInfo(
                    content=entity.dxf.text,
                    position=tuple(entity.dxf.insert),
                    height=entity.dxf.height,
                    rotation=entity.dxf.rotation,
                    layer=entity.dxf.layer,
                    entity_type="TEXT",
                    style=entity.dxf.style
                ))
            else:  # MTEXT
                texts.append(TextInfo(
                    content=entity.text,  # Bereinigter Text
                    position=tuple(entity.dxf.insert),
                    height=entity.dxf.char_height,
                    rotation=entity.dxf.rotation,
                    layer=entity.dxf.layer,
                    entity_type="MTEXT",
                    style=entity.dxf.style
                ))
        
        return texts
    
    def extract_block_attributes(self) -> list[dict]:
        """Extrahiert alle Block-Attribute (ATTRIB)."""
        attributes = []
        
        for insert in self.msp.query("INSERT"):
            if insert.has_attrib:
                block_attribs = {
                    "block_name": insert.dxf.name,
                    "position": tuple(insert.dxf.insert),
                    "layer": insert.dxf.layer,
                    "attributes": {}
                }
                for attrib in insert.attribs:
                    block_attribs["attributes"][attrib.dxf.tag] = attrib.dxf.text
                
                attributes.append(block_attribs)
        
        return attributes
    
    # -------------------------------------------------------------------------
    # BEMAÄUNGS-EXTRAKTION
    # -------------------------------------------------------------------------
    
    def extract_dimensions(self) -> list[DimensionInfo]:
        """Extrahiert alle Bemaßungen."""
        dimensions = []
        
        for dim in self.msp.query("DIMENSION"):
            try:
                measurement = dim.get_measurement()
            except:
                measurement = None
            
            dimensions.append(DimensionInfo(
                measurement=measurement,
                text_override=dim.dxf.text if dim.dxf.text else "",
                dim_type=str(dim.dimtype),
                layer=dim.dxf.layer,
                definition_points=[
                    tuple(dim.dxf.defpoint),
                    tuple(dim.dxf.defpoint2) if hasattr(dim.dxf, 'defpoint2') else None,
                    tuple(dim.dxf.defpoint3) if hasattr(dim.dxf, 'defpoint3') else None,
                ]
            ))
        
        return dimensions
    
    def get_dimension_values(self) -> list[float]:
        """Liste aller Bemaßungswerte."""
        dims = self.extract_dimensions()
        return [d.measurement for d in dims if d.measurement is not None]
    
    # -------------------------------------------------------------------------
    # QUALITÄTSPRÜFUNG
    # -------------------------------------------------------------------------
    
    def check_quality(self) -> list[dict]:
        """Führt Qualitätsprüfungen durch."""
        issues = []
        
        # 1. Sehr kurze Linien
        for line in self.msp.query("LINE"):
            length = line.dxf.start.distance(line.dxf.end)
            if length < 0.1:
                issues.append({
                    "type": "SHORT_LINE",
                    "severity": "info",
                    "handle": line.dxf.handle,
                    "message": f"Sehr kurze Linie ({length:.4f})",
                    "layer": line.dxf.layer
                })
        
        # 2. Entities auf Layer "0"
        layer0_count = sum(1 for e in self.entities if e.dxf.layer == "0")
        if layer0_count > 0:
            issues.append({
                "type": "LAYER_ZERO",
                "severity": "info",
                "message": f"{layer0_count} Entities auf Layer '0'",
            })
        
        # 3. Leere Layer
        empty_layers = self.get_empty_layers()
        if empty_layers:
            issues.append({
                "type": "EMPTY_LAYERS",
                "severity": "info",
                "message": f"{len(empty_layers)} leere Layer",
                "layers": empty_layers
            })
        
        # 4. Unbenutzte Blöcke
        unused_blocks = self.get_unused_blocks()
        if unused_blocks:
            issues.append({
                "type": "UNUSED_BLOCKS",
                "severity": "info",
                "message": f"{len(unused_blocks)} unbenutzte Block-Definitionen",
                "blocks": unused_blocks
            })
        
        # 5. Doppelte Entities (gleiche Geometrie)
        duplicates = self._find_duplicate_entities()
        if duplicates:
            issues.append({
                "type": "DUPLICATES",
                "severity": "warning",
                "message": f"{len(duplicates)} mögliche Duplikate gefunden",
                "count": len(duplicates)
            })
        
        # 6. Nicht geschlossene Polylinien (die es sein sollten)
        open_polylines = self._find_nearly_closed_polylines()
        if open_polylines:
            issues.append({
                "type": "UNCLOSED_POLYLINES",
                "severity": "warning",
                "message": f"{len(open_polylines)} fast geschlossene Polylinien",
                "handles": open_polylines
            })
        
        return issues
    
    def _find_duplicate_entities(self, tolerance: float = 0.001) -> list[tuple]:
        """Findet potenzielle Duplikate."""
        duplicates = []
        lines = list(self.msp.query("LINE"))
        
        for i, line1 in enumerate(lines):
            for line2 in lines[i+1:]:
                if (line1.dxf.start.distance(line2.dxf.start) < tolerance and
                    line1.dxf.end.distance(line2.dxf.end) < tolerance):
                    duplicates.append((line1.dxf.handle, line2.dxf.handle))
        
        return duplicates
    
    def _find_nearly_closed_polylines(self, tolerance: float = 1.0) -> list[str]:
        """Findet Polylinien die fast geschlossen sind."""
        nearly_closed = []
        
        for pline in self.msp.query("LWPOLYLINE"):
            if not pline.closed:
                points = list(pline.get_points("xy"))
                if len(points) >= 3:
                    first = points[0]
                    last = points[-1]
                    dist = math.sqrt((first[0]-last[0])**2 + (first[1]-last[1])**2)
                    if dist < tolerance:
                        nearly_closed.append(pline.dxf.handle)
        
        return nearly_closed
    
    # -------------------------------------------------------------------------
    # VOLLSTÄNDIGE ANALYSE
    # -------------------------------------------------------------------------
    
    def full_analysis(self) -> AnalysisReport:
        """Führt eine vollständige Analyse durch."""
        bbox = self.calculate_bounding_box()
        
        # Geschätzte Fläche (2D)
        estimated_area = 0.0
        if bbox:
            estimated_area = bbox["size"]["width"] * bbox["size"]["height"]
        
        # Einheiten aus Header
        units_map = {
            0: "Unitless", 1: "Inches", 2: "Feet", 3: "Miles",
            4: "Millimeters", 5: "Centimeters", 6: "Meters", 7: "Kilometers"
        }
        try:
            insunits = self.doc.header.get("$INSUNITS", 0)
            units = units_map.get(insunits, "Unknown")
        except:
            units = "Unknown"
        
        return AnalysisReport(
            filename=self.filepath.name,
            dxf_version=self.doc.dxfversion,
            encoding=self.doc.encoding,
            units=units,
            total_entities=len(self.entities),
            entity_statistics=self.count_entities(),
            category_statistics=self.count_by_category(),
            layers=[asdict(l) for l in self.analyze_layers()],
            blocks=[asdict(b) for b in self.analyze_blocks()],
            bounding_box=bbox,
            estimated_area=estimated_area,
            texts=[asdict(t) for t in self.extract_texts()],
            dimensions=[asdict(d) for d in self.extract_dimensions()],
            issues=self.check_quality(),
            source_format=self._source_format,
            was_converted=self._was_converted
        )
    
    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------
    
    def export_json(self, filepath: str, indent: int = 2):
        """Exportiert vollständige Analyse als JSON."""
        report = self.full_analysis()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(asdict(report), f, indent=indent, default=str, ensure_ascii=False)
        
        return filepath
    
    def export_entities_csv(self, filepath: str):
        """Exportiert Entity-Geometrie als CSV."""
        import csv
        
        geometries = self.extract_geometry(["LINE", "CIRCLE", "ARC", "LWPOLYLINE"])
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["handle", "type", "layer", "color", "geometry"])
            
            for geom in geometries:
                writer.writerow([
                    geom.handle,
                    geom.entity_type,
                    geom.layer,
                    geom.color,
                    json.dumps(geom.geometry)
                ])
        
        return filepath
    
    def export_texts_csv(self, filepath: str):
        """Exportiert Texte als CSV."""
        import csv
        
        texts = self.extract_texts()
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["content", "position_x", "position_y", "height", 
                           "rotation", "layer", "type"])
            
            for text in texts:
                writer.writerow([
                    text.content,
                    text.position[0],
                    text.position[1],
                    text.height,
                    text.rotation,
                    text.layer,
                    text.entity_type
                ])
        
        return filepath


# ============================================================================
# SPEZIALISIERTE ANALYSEN
# ============================================================================

class FloorPlanAnalyzer(DXFAnalyzer):
    """Spezialisierte Analyse für Grundrisse."""
    
    # Typische Block-Namen für Grundriss-Elemente
    DOOR_PATTERNS = ["DOOR", "TÜR", "TUER", "D-", "DR-"]
    WINDOW_PATTERNS = ["WINDOW", "FENSTER", "W-", "WI-", "FE-"]
    FURNITURE_PATTERNS = ["DESK", "TABLE", "CHAIR", "SOFA", "BED", 
                          "TISCH", "STUHL", "BETT", "SCHRANK"]
    SANITARY_PATTERNS = ["WC", "TOILET", "SINK", "BATH", "SHOWER",
                         "WASCHBECKEN", "DUSCHE", "BADEWANNE"]
    
    def find_doors(self) -> list[dict]:
        """Findet Tür-Blöcke."""
        return self._find_blocks_by_pattern(self.DOOR_PATTERNS)
    
    def find_windows(self) -> list[dict]:
        """Findet Fenster-Blöcke."""
        return self._find_blocks_by_pattern(self.WINDOW_PATTERNS)
    
    def find_furniture(self) -> list[dict]:
        """Findet Möbel-Blöcke."""
        return self._find_blocks_by_pattern(self.FURNITURE_PATTERNS)
    
    def find_sanitary(self) -> list[dict]:
        """Findet Sanitär-Blöcke."""
        return self._find_blocks_by_pattern(self.SANITARY_PATTERNS)
    
    def _find_blocks_by_pattern(self, patterns: list[str]) -> list[dict]:
        """Findet Blöcke die einem Muster entsprechen."""
        results = []
        
        for insert in self.msp.query("INSERT"):
            name = insert.dxf.name.upper()
            for pattern in patterns:
                if pattern.upper() in name:
                    results.append({
                        "block_name": insert.dxf.name,
                        "position": tuple(insert.dxf.insert),
                        "rotation": insert.dxf.rotation,
                        "layer": insert.dxf.layer,
                        "matched_pattern": pattern
                    })
                    break
        
        return results
    
    def identify_rooms(self) -> list[dict]:
        """
        Versucht Räume anhand von Texten in geschlossenen Bereichen zu identifizieren.
        """
        rooms = []
        texts = self.extract_texts()
        
        # Typische Raumnamen
        room_keywords = [
            "ZIMMER", "RAUM", "KÜCHE", "BAD", "WC", "FLUR", "DIELE",
            "WOHNZIMMER", "SCHLAFZIMMER", "KINDERZIMMER", "ARBEITSZIMMER",
            "KELLER", "GARAGE", "BALKON", "TERRASSE", "LIVING", "BEDROOM",
            "KITCHEN", "BATHROOM", "OFFICE", "ROOM"
        ]
        
        for text in texts:
            content_upper = text.content.upper()
            for keyword in room_keywords:
                if keyword in content_upper:
                    rooms.append({
                        "name": text.content,
                        "position": text.position,
                        "layer": text.layer
                    })
                    break
        
        return rooms
    
    def calculate_room_areas(self) -> list[dict]:
        """
        Berechnet Flächen geschlossener Polylinien (potenzielle Räume).
        """
        areas = []
        
        for pline in self.msp.query("LWPOLYLINE"):
            if pline.closed:
                points = list(pline.get_points("xy"))
                area = self._calculate_polygon_area(points)
                
                if area > 1.0:  # Mindestgröße 1 m² (bei Meter-Einheiten)
                    areas.append({
                        "handle": pline.dxf.handle,
                        "layer": pline.dxf.layer,
                        "area": area,
                        "perimeter": self._calculate_polyline_length(points, True),
                        "vertex_count": len(points)
                    })
        
        return sorted(areas, key=lambda x: x["area"], reverse=True)


class TechnicalDrawingAnalyzer(DXFAnalyzer):
    """Spezialisierte Analyse für technische Zeichnungen."""
    
    def analyze_centerlines(self) -> list[dict]:
        """Findet Mittellinien (typischerweise auf eigenen Layern)."""
        centerline_keywords = ["CENTER", "MITTEL", "CL", "AXIS", "ACHSE"]
        results = []
        
        for layer in self.get_layer_names():
            layer_upper = layer.upper()
            if any(kw in layer_upper for kw in centerline_keywords):
                entities = list(self.get_entities_by_layer(layer))
                results.append({
                    "layer": layer,
                    "entity_count": len(entities),
                    "types": dict(Counter(e.dxftype() for e in entities))
                })
        
        return results
    
    def extract_holes(self) -> list[dict]:
        """Extrahiert Bohrungen (Kreise auf bestimmten Layern oder mit bestimmten Radien)."""
        holes = []
        
        for circle in self.msp.query("CIRCLE"):
            radius = circle.dxf.radius
            # Typische Bohrungsdurchmesser (in mm)
            standard_diameters = [3, 4, 5, 6, 8, 10, 12, 14, 16, 20, 25, 30]
            diameter = radius * 2
            
            is_standard = any(abs(diameter - d) < 0.1 for d in standard_diameters)
            
            holes.append({
                "center": tuple(circle.dxf.center),
                "radius": radius,
                "diameter": diameter,
                "is_standard_size": is_standard,
                "layer": circle.dxf.layer
            })
        
        return holes
    
    def extract_tolerances(self) -> list[dict]:
        """Extrahiert Toleranz-Informationen aus Bemaßungen und Texten."""
        tolerances = []
        
        # Aus Bemaßungen
        for dim in self.extract_dimensions():
            if dim.text_override and ("±" in dim.text_override or 
                                      "+/-" in dim.text_override or
                                      "+" in dim.text_override):
                tolerances.append({
                    "type": "dimension",
                    "value": dim.measurement,
                    "text": dim.text_override,
                    "layer": dim.layer
                })
        
        # Aus Texten
        import re
        tolerance_pattern = r'[±]\s*[\d.,]+|[\d.,]+\s*[±]\s*[\d.,]+'
        
        for text in self.extract_texts():
            if re.search(tolerance_pattern, text.content):
                tolerances.append({
                    "type": "text",
                    "content": text.content,
                    "position": text.position,
                    "layer": text.layer
                })
        
        return tolerances


# ============================================================================
# DEMO & TESTS
# ============================================================================

def create_test_drawing() -> str:
    """Erstellt eine Test-DXF für Demonstrationszwecke."""
    doc = ezdxf.new(dxfversion="R2010")
    msp = doc.modelspace()
    
    # Layer erstellen
    doc.layers.add("WALLS", color=7)
    doc.layers.add("DOORS", color=3)
    doc.layers.add("WINDOWS", color=5)
    doc.layers.add("TEXT", color=4)
    doc.layers.add("DIMENSIONS", color=2)
    doc.layers.add("FURNITURE", color=6)
    doc.layers.add("EMPTY_LAYER", color=1)  # Leerer Layer für Test
    
    # Raum 1: Wohnzimmer
    msp.add_lwpolyline(
        [(0, 0), (5000, 0), (5000, 4000), (0, 4000)],
        close=True, dxfattribs={"layer": "WALLS"}
    )
    msp.add_text("Wohnzimmer", dxfattribs={
        "layer": "TEXT", "insert": (2500, 2000), "height": 200
    })
    
    # Raum 2: Küche
    msp.add_lwpolyline(
        [(5000, 0), (8000, 0), (8000, 3000), (5000, 3000)],
        close=True, dxfattribs={"layer": "WALLS"}
    )
    msp.add_text("Küche", dxfattribs={
        "layer": "TEXT", "insert": (6500, 1500), "height": 200
    })
    
    # Türöffnung (simuliert)
    msp.add_arc((5000, 1500), 800, 0, 90, dxfattribs={"layer": "DOORS"})
    msp.add_line((5000, 1500), (5000, 2300), dxfattribs={"layer": "DOORS"})
    
    # Fenster (Linien)
    msp.add_line((1000, 4000), (2000, 4000), dxfattribs={"layer": "WINDOWS"})
    msp.add_line((3000, 4000), (4000, 4000), dxfattribs={"layer": "WINDOWS"})
    
    # Einige Kreise (z.B. Möbel-Symbole)
    msp.add_circle((1500, 1500), 300, dxfattribs={"layer": "FURNITURE"})
    msp.add_circle((3500, 1500), 300, dxfattribs={"layer": "FURNITURE"})
    
    # Bemaßungen
    msp.add_linear_dim(base=(0, -500), p1=(0, 0), p2=(5000, 0),
                       dxfattribs={"layer": "DIMENSIONS"}).render()
    msp.add_linear_dim(base=(-500, 0), p1=(0, 0), p2=(0, 4000), angle=90,
                       dxfattribs={"layer": "DIMENSIONS"}).render()
    
    # Duplikat für Test
    msp.add_line((0, 0), (100, 0), dxfattribs={"layer": "WALLS"})
    msp.add_line((0, 0), (100, 0), dxfattribs={"layer": "WALLS"})  # Duplikat!
    
    # Fast geschlossene Polylinie
    msp.add_lwpolyline(
        [(6000, 3500), (7500, 3500), (7500, 4500), (6000.5, 4500.5)],
        close=False, dxfattribs={"layer": "WALLS"}
    )
    
    filepath = "/tmp/test_floorplan.dxf"
    doc.saveas(filepath)
    return filepath


def demo_full_analysis():
    """Demonstriert die vollständige Analyse."""
    print("=" * 70)
    print("DXF/DWG ANALYSE DEMO")
    print("=" * 70)
    
    # Test-Zeichnung erstellen
    filepath = create_test_drawing()
    print(f"\n✓ Test-DXF erstellt: {filepath}")
    
    # Analyse durchführen
    analyzer = DXFAnalyzer(filepath)
    
    # Format-Info
    print(f"\n📄 Format: {analyzer.source_format}", end="")
    if analyzer.was_converted:
        print(" (konvertiert von DWG)")
    else:
        print(" (nativ)")
    
    # 1. Basis-Statistiken
    print("\n" + "-" * 50)
    print("1. ENTITY-STATISTIKEN")
    print("-" * 50)
    stats = analyzer.count_entities()
    for etype, count in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"   {etype:15} : {count:5}")
    print(f"   {'GESAMT':15} : {sum(stats.values()):5}")
    
    # 2. Kategorien
    print("\n" + "-" * 50)
    print("2. KATEGORIEN")
    print("-" * 50)
    cats = analyzer.count_by_category()
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"   {cat:15} : {count:5}")
    
    # 3. Layer
    print("\n" + "-" * 50)
    print("3. LAYER-ANALYSE")
    print("-" * 50)
    layers = analyzer.analyze_layers()
    for layer in layers:
        status = "✓" if layer.entity_count > 0 else "○"
        print(f"   {status} {layer.name:15} : {layer.entity_count:3} Entities")
    
    # 4. Bounding Box
    print("\n" + "-" * 50)
    print("4. BOUNDING BOX")
    print("-" * 50)
    bbox = analyzer.calculate_bounding_box()
    if bbox:
        print(f"   Min: ({bbox['min']['x']:.1f}, {bbox['min']['y']:.1f})")
        print(f"   Max: ({bbox['max']['x']:.1f}, {bbox['max']['y']:.1f})")
        print(f"   Größe: {bbox['size']['width']:.1f} x {bbox['size']['height']:.1f}")
    
    # 5. Texte
    print("\n" + "-" * 50)
    print("5. EXTRAHIERTE TEXTE")
    print("-" * 50)
    texts = analyzer.extract_texts()
    for text in texts[:10]:
        print(f"   '{text.content}' @ ({text.position[0]:.0f}, {text.position[1]:.0f})")
    
    # 6. Qualitätsprüfung
    print("\n" + "-" * 50)
    print("6. QUALITÄTSPRÜFUNG")
    print("-" * 50)
    issues = analyzer.check_quality()
    for issue in issues:
        icon = {"info": "ℹ", "warning": "⚠", "error": "✗"}.get(issue["severity"], "?")
        print(f"   {icon} [{issue['severity'].upper()}] {issue['message']}")
    
    # 7. JSON Export
    print("\n" + "-" * 50)
    print("7. EXPORT")
    print("-" * 50)
    json_path = analyzer.export_json("/tmp/analysis_report.json")
    print(f"   ✓ JSON: {json_path}")
    
    csv_path = analyzer.export_texts_csv("/tmp/texts.csv")
    print(f"   ✓ Texte CSV: {csv_path}")
    
    print("\n" + "=" * 70)
    print("ANALYSE ABGESCHLOSSEN")
    print("=" * 70)
    
    return analyzer


def demo_dwg_support():
    """Demonstriert die DWG-Unterstützung."""
    print("\n" + "=" * 70)
    print("DWG UNTERSTÜTZUNG")
    print("=" * 70)
    
    # Prüfe ODA File Converter Status
    converter = DWGConverter()
    status = converter.get_status()
    
    print("\n📋 ODA File Converter Status:")
    print(f"   Verfügbar: {'✓ Ja' if status['available'] else '✗ Nein'}")
    
    if status['available']:
        print(f"   Pfad: {status['path']}")
        print(f"   Unterstützte Versionen: {', '.join(status['supported_versions'])}")
        
        # Demo: DXF zu DWG und zurück
        print("\n📝 Demo: Konvertierung")
        test_dxf = create_test_drawing()
        
        # DXF → DWG
        dwg_path = converter.convert_to_dwg(test_dxf, dxf_version="R2018")
        if dwg_path:
            print(f"   ✓ DXF → DWG: {dwg_path}")
            
            # DWG → DXF (zurück)
            dxf_path = converter.convert_to_dxf(dwg_path)
            if dxf_path:
                print(f"   ✓ DWG → DXF: {dxf_path}")
                
                # Analyse der zurück-konvertierten Datei
                analyzer = DXFAnalyzer(dxf_path)
                print(f"   ✓ Entities nach Roundtrip: {len(analyzer.entities)}")
        
        converter.cleanup()
    else:
        print("\n   ⚠ ODA File Converter nicht installiert!")
        print("   Download: https://www.opendesign.com/guestfiles/oda_file_converter")
        print("\n   Installation (Linux):")
        print("   - DEB: sudo dpkg -i ODAFileConverter_*.deb")
        print("   - RPM: sudo rpm -i ODAFileConverter_*.rpm")
        print("   - AppImage: chmod +x ODAFileConverter_*.AppImage && ./ODAFileConverter_*.AppImage")
    
    print("\n" + "=" * 70)


def demo_floorplan_analysis():
    """Demonstriert die Grundriss-Analyse."""
    print("\n" + "=" * 70)
    print("GRUNDRISS-ANALYSE DEMO")
    print("=" * 70)
    
    filepath = create_test_drawing()
    analyzer = FloorPlanAnalyzer(filepath)
    
    print("\n📍 Identifizierte Räume:")
    rooms = analyzer.identify_rooms()
    for room in rooms:
        print(f"   - {room['name']} @ {room['position']}")
    
    print("\n📐 Flächen (geschlossene Polylinien):")
    areas = analyzer.calculate_room_areas()
    for area in areas[:5]:
        print(f"   - {area['area']:.2f} Einheiten² (Layer: {area['layer']})")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    analyzer = demo_full_analysis()
    demo_floorplan_analysis()
    demo_dwg_support()
    
    print("\n" + "=" * 70)
    print("ALLE DEMOS ABGESCHLOSSEN")
    print("=" * 70)
