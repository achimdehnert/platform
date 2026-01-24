# Brandschutz-Experte: Teil 2 - Parser & Analyzer Spezifikationen

## 4. Parser-Module im Detail

### 4.1 Base Parser (Abstrakte Klasse)

```python
# parsers/base_parser.py
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class ParseResult:
    """Ergebnis eines Parse-Vorgangs"""
    success: bool
    content: Dict[str, Any]
    raw_text: str = ""
    metadata: Dict[str, Any] = None
    errors: list = None
    
    def __post_init__(self):
        self.metadata = self.metadata or {}
        self.errors = self.errors or []

class BaseParser(ABC):
    """Abstrakte Basisklasse für alle Parser"""
    
    SUPPORTED_EXTENSIONS: list = []
    
    def __init__(self, file_path: Path):
        self.file_path = Path(file_path)
        self._validate_file()
    
    def _validate_file(self):
        if not self.file_path.exists():
            raise FileNotFoundError(f"Datei nicht gefunden: {self.file_path}")
        if self.file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Nicht unterstütztes Format: {self.file_path.suffix}. "
                f"Unterstützt: {self.SUPPORTED_EXTENSIONS}"
            )
    
    @abstractmethod
    def parse(self) -> ParseResult:
        """Führt das Parsing durch"""
        pass
    
    @abstractmethod
    def extract_sections(self) -> Dict[str, str]:
        """Extrahiert strukturierte Abschnitte"""
        pass
```

### 4.2 PDF-Parser

```python
# parsers/pdf_parser.py
import fitz  # PyMuPDF
import re
from pathlib import Path
from typing import Dict, List, Tuple
from .base_parser import BaseParser, ParseResult

class PDFParser(BaseParser):
    """Parser für PDF-Brandschutzkonzepte"""
    
    SUPPORTED_EXTENSIONS = ['.pdf']
    
    # Typische Abschnitts-Überschriften in Brandschutzkonzepten
    SECTION_PATTERNS = {
        'allgemein': r'(?i)(1\.?\s*)?(allgemein|grundlage|einleitung|vorbemerkung)',
        'gebaeude': r'(?i)(2\.?\s*)?(gebäude|bauliche\s+anlage|objekt)',
        'brandabschnitte': r'(?i)(3\.?\s*)?(brandabschnitt|brandbekämpfungsabschnitt)',
        'fluchtwege': r'(?i)(4\.?\s*)?(flucht|rettungsweg|notausgang)',
        'anlagentechnik': r'(?i)(5\.?\s*)?(anlagentechnik|technische?\s+anlagen?|brandmeldeanlage)',
        'loeschmittel': r'(?i)(6\.?\s*)?(löschmittel|löscheinrichtung|feuerlöscher)',
        'organisation': r'(?i)(7\.?\s*)?(organisation|betrieblich|brandschutzordnung)',
        'zusammenfassung': r'(?i)(8\.?\s*)?(zusammenfassung|fazit|schlussbemerkung)',
    }
    
    def parse(self) -> ParseResult:
        """Extrahiert Text und Struktur aus PDF"""
        try:
            doc = fitz.open(str(self.file_path))
            
            full_text = []
            pages_content = []
            
            for page_num, page in enumerate(doc, 1):
                text = page.get_text("text")
                full_text.append(text)
                pages_content.append({
                    'page': page_num,
                    'text': text,
                    'tables': self._extract_tables(page),
                    'images': len(page.get_images())
                })
            
            raw_text = "\n".join(full_text)
            sections = self.extract_sections(raw_text)
            
            return ParseResult(
                success=True,
                content={
                    'pages': pages_content,
                    'sections': sections,
                    'page_count': len(doc),
                    'toc': self._extract_toc(doc)
                },
                raw_text=raw_text,
                metadata={
                    'title': doc.metadata.get('title', ''),
                    'author': doc.metadata.get('author', ''),
                    'creation_date': doc.metadata.get('creationDate', ''),
                }
            )
            
        except Exception as e:
            return ParseResult(
                success=False,
                content={},
                errors=[str(e)]
            )
    
    def extract_sections(self, text: str = None) -> Dict[str, str]:
        """Identifiziert und extrahiert Konzept-Abschnitte"""
        if text is None:
            result = self.parse()
            text = result.raw_text
        
        sections = {}
        lines = text.split('\n')
        
        current_section = 'unbekannt'
        current_content = []
        
        for line in lines:
            # Prüfe auf Abschnitts-Überschrift
            found_section = None
            for section_name, pattern in self.SECTION_PATTERNS.items():
                if re.match(pattern, line.strip()):
                    found_section = section_name
                    break
            
            if found_section:
                # Speichere vorherigen Abschnitt
                if current_content:
                    sections[current_section] = '\n'.join(current_content)
                current_section = found_section
                current_content = [line]
            else:
                current_content.append(line)
        
        # Letzten Abschnitt speichern
        if current_content:
            sections[current_section] = '\n'.join(current_content)
        
        return sections
    
    def _extract_tables(self, page) -> List[Dict]:
        """Extrahiert Tabellen aus einer Seite"""
        tables = []
        # PyMuPDF Tabellen-Extraktion
        try:
            tabs = page.find_tables()
            for tab in tabs:
                tables.append({
                    'bbox': tab.bbox,
                    'rows': tab.row_count,
                    'cols': tab.col_count,
                    'data': tab.extract()
                })
        except:
            pass
        return tables
    
    def _extract_toc(self, doc) -> List[Tuple]:
        """Extrahiert Inhaltsverzeichnis"""
        return doc.get_toc()
```

### 4.3 CAD-Parser für Brandschutzpläne

```python
# parsers/cad_parser.py
import ezdxf
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from .base_parser import BaseParser, ParseResult
import subprocess
import tempfile
import os

@dataclass
class FireSafetyElement:
    """Brandschutz-relevantes Element aus CAD"""
    type: str  # 'door', 'wall', 'extinguisher', 'escape_sign', etc.
    layer: str
    position: Tuple[float, float]
    attributes: Dict[str, str] = field(default_factory=dict)
    geometry: Dict = field(default_factory=dict)

class CADParser(BaseParser):
    """Parser für DXF/DWG Brandschutzpläne"""
    
    SUPPORTED_EXTENSIONS = ['.dxf', '.dwg']
    
    # Layer-Namen Mapping (typische Bezeichnungen)
    FIRE_SAFETY_LAYERS = {
        'fluchtwege': ['flucht', 'escape', 'rettung', 'notaus', 'rw_'],
        'brandabschnitt': ['brand', 'fire', 'f30', 'f60', 'f90', 'rei'],
        'brandschutztueren': ['bst', 't30', 't60', 't90', 'rs_tuer', 'feuerschutz'],
        'loescher': ['lösch', 'extinguish', 'feuerloescher'],
        'melder': ['bma', 'rauchmelder', 'smoke', 'detector'],
        'rwa': ['rwa', 'rauch', 'smoke_vent'],
        'beschilderung': ['schild', 'sign', 'fluchtweg_schild'],
    }
    
    # Block-Namen für Brandschutz-Symbole
    FIRE_SAFETY_BLOCKS = {
        'feuerloescher': ['feuerlöscher', 'extinguisher', 'fe_', 'abc_'],
        'druckknopfmelder': ['druckknopf', 'manual_call', 'dkm_'],
        'rauchmelder': ['rauchmelder', 'smoke_det', 'rm_'],
        'brandschutztuer': ['bst_', 't30_', 't60_', 't90_', 'fire_door'],
        'notausgang': ['notausgang', 'emergency_exit', 'exit_'],
        'sammelplatz': ['sammelplatz', 'assembly', 'sammelpunkt'],
        'loeschwasser': ['hydrant', 'loeschwasser', 'fire_hose'],
    }
    
    def __init__(self, file_path: Path):
        self.file_path = Path(file_path)
        self._temp_dxf = None
        
        # DWG-Konvertierung wenn nötig
        if self.file_path.suffix.lower() == '.dwg':
            self._convert_dwg_to_dxf()
        
        self._validate_file()
    
    def _convert_dwg_to_dxf(self):
        """Konvertiert DWG zu DXF via ODA File Converter"""
        # Prüfe ob ODA Converter verfügbar
        oda_paths = [
            '/usr/bin/ODAFileConverter',
            '/opt/ODAFileConverter/ODAFileConverter',
            'ODAFileConverter'  # Falls im PATH
        ]
        
        oda_path = None
        for path in oda_paths:
            if os.path.exists(path) or subprocess.run(
                ['which', path], capture_output=True
            ).returncode == 0:
                oda_path = path
                break
        
        if not oda_path:
            raise RuntimeError(
                "ODA File Converter nicht gefunden. "
                "Bitte installieren: https://www.opendesign.com/guestfiles/oda_file_converter"
            )
        
        # Temporäres Verzeichnis für Output
        temp_dir = tempfile.mkdtemp()
        input_dir = str(self.file_path.parent)
        
        # Konvertierung durchführen
        cmd = [
            oda_path,
            input_dir,
            temp_dir,
            'ACAD2018',  # Output Version
            'DXF',       # Output Format
            '0',         # Recurse folders: No
            '1',         # Audit: Yes
            self.file_path.name
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"DWG-Konvertierung fehlgeschlagen: {result.stderr}")
        
        # Finde konvertierte Datei
        converted = Path(temp_dir) / self.file_path.with_suffix('.dxf').name
        if converted.exists():
            self._temp_dxf = converted
            self.file_path = converted
        else:
            raise RuntimeError("Konvertierte DXF-Datei nicht gefunden")
    
    def parse(self) -> ParseResult:
        """Analysiert CAD-Datei für Brandschutz-Elemente"""
        try:
            doc = ezdxf.readfile(str(self.file_path))
            msp = doc.modelspace()
            
            # Basis-Analyse
            layers = self._analyze_layers(doc)
            blocks = self._analyze_blocks(doc)
            fire_elements = self._extract_fire_safety_elements(msp)
            rooms = self._detect_rooms(msp)
            escape_routes = self._detect_escape_routes(msp, fire_elements)
            
            return ParseResult(
                success=True,
                content={
                    'layers': layers,
                    'blocks': blocks,
                    'fire_elements': fire_elements,
                    'rooms': rooms,
                    'escape_routes': escape_routes,
                    'bounding_box': self._get_bounding_box(msp),
                    'statistics': self._get_statistics(msp)
                },
                metadata={
                    'dxf_version': doc.dxfversion,
                    'units': self._get_units(doc),
                    'filename': self.file_path.name
                }
            )
            
        except Exception as e:
            return ParseResult(
                success=False,
                content={},
                errors=[str(e)]
            )
    
    def extract_sections(self) -> Dict[str, str]:
        """Nicht anwendbar für CAD - gibt leeres Dict zurück"""
        return {}
    
    def _analyze_layers(self, doc) -> Dict[str, Dict]:
        """Analysiert Layer-Struktur"""
        layers = {}
        for layer in doc.layers:
            layer_name = layer.dxf.name.lower()
            
            # Klassifiziere Layer
            category = 'sonstige'
            for cat, patterns in self.FIRE_SAFETY_LAYERS.items():
                if any(p in layer_name for p in patterns):
                    category = cat
                    break
            
            layers[layer.dxf.name] = {
                'category': category,
                'color': layer.color,
                'is_on': layer.is_on(),
                'is_locked': layer.is_locked(),
            }
        return layers
    
    def _analyze_blocks(self, doc) -> Dict[str, Dict]:
        """Analysiert Block-Definitionen"""
        blocks = {}
        for block in doc.blocks:
            if block.name.startswith('*'):  # System-Blöcke überspringen
                continue
            
            block_name = block.name.lower()
            
            # Klassifiziere Block
            category = 'sonstige'
            for cat, patterns in self.FIRE_SAFETY_BLOCKS.items():
                if any(p in block_name for p in patterns):
                    category = cat
                    break
            
            blocks[block.name] = {
                'category': category,
                'entity_count': len(list(block)),
                'has_attributes': any(
                    e.dxftype() == 'ATTDEF' for e in block
                )
            }
        return blocks
    
    def _extract_fire_safety_elements(self, msp) -> List[Dict]:
        """Extrahiert Brandschutz-relevante Elemente"""
        elements = []
        
        for entity in msp:
            layer = entity.dxf.layer.lower()
            
            # Prüfe ob brandschutz-relevant
            is_relevant = False
            category = 'sonstige'
            
            for cat, patterns in self.FIRE_SAFETY_LAYERS.items():
                if any(p in layer for p in patterns):
                    is_relevant = True
                    category = cat
                    break
            
            # Block-Referenzen (INSERT) prüfen
            if entity.dxftype() == 'INSERT':
                block_name = entity.dxf.name.lower()
                for cat, patterns in self.FIRE_SAFETY_BLOCKS.items():
                    if any(p in block_name for p in patterns):
                        is_relevant = True
                        category = cat
                        break
            
            if is_relevant:
                elem = {
                    'type': entity.dxftype(),
                    'layer': entity.dxf.layer,
                    'category': category,
                }
                
                # Position hinzufügen wenn verfügbar
                if hasattr(entity.dxf, 'insert'):
                    elem['position'] = (
                        entity.dxf.insert.x,
                        entity.dxf.insert.y
                    )
                elif hasattr(entity.dxf, 'start'):
                    elem['position'] = (
                        entity.dxf.start.x,
                        entity.dxf.start.y
                    )
                
                # Attribute extrahieren bei INSERTs
                if entity.dxftype() == 'INSERT' and entity.has_attrib:
                    elem['attributes'] = {
                        attrib.dxf.tag: attrib.dxf.text
                        for attrib in entity.attribs
                    }
                
                elements.append(elem)
        
        return elements
    
    def _detect_rooms(self, msp) -> List[Dict]:
        """Erkennt Räume anhand geschlossener Polylinien"""
        rooms = []
        
        for entity in msp.query('LWPOLYLINE POLYLINE'):
            if entity.is_closed:
                # Prüfe ob auf Raum-Layer
                layer = entity.dxf.layer.lower()
                if any(kw in layer for kw in ['raum', 'room', 'space', 'zone']):
                    try:
                        points = list(entity.vertices())
                        if len(points) >= 3:
                            # Berechne Fläche (Shoelace-Formel)
                            area = self._calculate_polygon_area(points)
                            rooms.append({
                                'layer': entity.dxf.layer,
                                'vertices': len(points),
                                'area_sqm': abs(area) / 1_000_000,  # mm² zu m²
                                'centroid': self._calculate_centroid(points)
                            })
                    except:
                        pass
        
        return rooms
    
    def _detect_escape_routes(self, msp, fire_elements: List[Dict]) -> List[Dict]:
        """Erkennt Fluchtwege"""
        routes = []
        
        # Suche nach Fluchtweg-Linien
        for entity in msp:
            layer = entity.dxf.layer.lower()
            if any(kw in layer for kw in ['flucht', 'escape', 'rw_']):
                if entity.dxftype() in ['LINE', 'LWPOLYLINE', 'POLYLINE']:
                    route = {
                        'layer': entity.dxf.layer,
                        'type': entity.dxftype(),
                    }
                    
                    if entity.dxftype() == 'LINE':
                        length = entity.dxf.start.distance(entity.dxf.end)
                        route['length_m'] = length / 1000  # mm zu m
                    elif hasattr(entity, 'length'):
                        route['length_m'] = entity.length / 1000
                    
                    routes.append(route)
        
        return routes
    
    def _calculate_polygon_area(self, points) -> float:
        """Shoelace-Formel für Polygonfläche"""
        n = len(points)
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += points[i][0] * points[j][1]
            area -= points[j][0] * points[i][1]
        return area / 2.0
    
    def _calculate_centroid(self, points) -> Tuple[float, float]:
        """Berechnet Schwerpunkt eines Polygons"""
        n = len(points)
        cx = sum(p[0] for p in points) / n
        cy = sum(p[1] for p in points) / n
        return (cx, cy)
    
    def _get_bounding_box(self, msp) -> Dict:
        """Ermittelt Gesamtausdehnung"""
        bbox = ezdxf.bbox.extents(msp)
        if bbox.is_empty:
            return {}
        return {
            'min': (bbox.extmin.x, bbox.extmin.y),
            'max': (bbox.extmax.x, bbox.extmax.y),
            'width_m': (bbox.extmax.x - bbox.extmin.x) / 1000,
            'height_m': (bbox.extmax.y - bbox.extmin.y) / 1000
        }
    
    def _get_statistics(self, msp) -> Dict:
        """Erstellt Statistik über Entities"""
        stats = {}
        for entity in msp:
            etype = entity.dxftype()
            stats[etype] = stats.get(etype, 0) + 1
        return stats
    
    def _get_units(self, doc) -> str:
        """Ermittelt Einheiten"""
        units_map = {
            0: 'unbekannt', 1: 'inches', 2: 'feet',
            4: 'mm', 5: 'cm', 6: 'm'
        }
        try:
            unit_code = doc.header.get('$INSUNITS', 0)
            return units_map.get(unit_code, 'unbekannt')
        except:
            return 'unbekannt'
    
    def __del__(self):
        """Aufräumen temporärer Dateien"""
        if self._temp_dxf and self._temp_dxf.exists():
            try:
                self._temp_dxf.unlink()
            except:
                pass
```

---

## 5. Nächste Schritte

Die Parser sind nun spezifiziert. Im nächsten Teil folgen:
- **Teil 3:** Normendatenbank und Checklisten
- **Teil 4:** Analyzer-Module für Konzept- und Planprüfung
- **Teil 5:** Report-Generator und Empfehlungs-Engine

Soll ich mit Teil 3 (Normendatenbank) fortfahren?
