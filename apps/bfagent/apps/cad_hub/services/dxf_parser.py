"""
DXF Parser Service for CAD Hub
Extracts geometry, layers, texts, and dimensions from DXF files.
"""
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import ezdxf
from ezdxf.document import Drawing
from ezdxf.entities import DXFEntity

logger = logging.getLogger(__name__)


@dataclass
class DXFPoint:
    """2D/3D Point"""
    x: float
    y: float
    z: float = 0.0
    
    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y, "z": self.z}


@dataclass
class DXFLine:
    """Line entity"""
    start: DXFPoint
    end: DXFPoint
    layer: str
    color: int = 256  # BYLAYER
    
    @property
    def length(self) -> float:
        return ((self.end.x - self.start.x)**2 + 
                (self.end.y - self.start.y)**2 + 
                (self.end.z - self.start.z)**2) ** 0.5
    
    def to_dict(self) -> dict:
        return {
            "type": "LINE",
            "start": self.start.to_dict(),
            "end": self.end.to_dict(),
            "layer": self.layer,
            "length": round(self.length, 4)
        }


@dataclass
class DXFCircle:
    """Circle entity"""
    center: DXFPoint
    radius: float
    layer: str
    
    @property
    def area(self) -> float:
        import math
        return math.pi * self.radius ** 2
    
    def to_dict(self) -> dict:
        return {
            "type": "CIRCLE",
            "center": self.center.to_dict(),
            "radius": self.radius,
            "layer": self.layer,
            "area": round(self.area, 4)
        }


@dataclass
class DXFArc:
    """Arc entity"""
    center: DXFPoint
    radius: float
    start_angle: float
    end_angle: float
    layer: str
    
    def to_dict(self) -> dict:
        return {
            "type": "ARC",
            "center": self.center.to_dict(),
            "radius": self.radius,
            "start_angle": self.start_angle,
            "end_angle": self.end_angle,
            "layer": self.layer
        }


@dataclass
class DXFText:
    """Text entity (TEXT, MTEXT)"""
    text: str
    position: DXFPoint
    height: float
    rotation: float
    layer: str
    
    def to_dict(self) -> dict:
        return {
            "type": "TEXT",
            "text": self.text,
            "position": self.position.to_dict(),
            "height": self.height,
            "rotation": self.rotation,
            "layer": self.layer
        }


@dataclass
class DXFPolyline:
    """Polyline entity (LWPOLYLINE, POLYLINE)"""
    points: list[DXFPoint]
    closed: bool
    layer: str
    
    @property
    def length(self) -> float:
        total = 0.0
        for i in range(len(self.points) - 1):
            p1, p2 = self.points[i], self.points[i + 1]
            total += ((p2.x - p1.x)**2 + (p2.y - p1.y)**2) ** 0.5
        if self.closed and len(self.points) > 1:
            p1, p2 = self.points[-1], self.points[0]
            total += ((p2.x - p1.x)**2 + (p2.y - p1.y)**2) ** 0.5
        return total
    
    @property
    def area(self) -> float:
        """Shoelace formula for polygon area"""
        if not self.closed or len(self.points) < 3:
            return 0.0
        n = len(self.points)
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += self.points[i].x * self.points[j].y
            area -= self.points[j].x * self.points[i].y
        return abs(area) / 2.0
    
    def to_dict(self) -> dict:
        return {
            "type": "POLYLINE",
            "points": [p.to_dict() for p in self.points],
            "closed": self.closed,
            "layer": self.layer,
            "length": round(self.length, 4),
            "area": round(self.area, 4) if self.closed else None
        }


@dataclass
class DXFDimension:
    """Dimension entity"""
    dim_type: str  # LINEAR, ANGULAR, RADIAL, etc.
    measurement: float
    text_override: str
    layer: str
    
    def to_dict(self) -> dict:
        return {
            "type": "DIMENSION",
            "dim_type": self.dim_type,
            "measurement": self.measurement,
            "text_override": self.text_override,
            "layer": self.layer
        }


@dataclass
class DXFBlock:
    """Block reference (INSERT)"""
    name: str
    position: DXFPoint
    scale: tuple[float, float, float]
    rotation: float
    layer: str
    
    def to_dict(self) -> dict:
        return {
            "type": "INSERT",
            "block_name": self.name,
            "position": self.position.to_dict(),
            "scale": {"x": self.scale[0], "y": self.scale[1], "z": self.scale[2]},
            "rotation": self.rotation,
            "layer": self.layer
        }


@dataclass
class DXFLayer:
    """Layer definition"""
    name: str
    color: int
    linetype: str
    is_on: bool
    is_locked: bool
    entity_count: int = 0
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "color": self.color,
            "linetype": self.linetype,
            "is_on": self.is_on,
            "is_locked": self.is_locked,
            "entity_count": self.entity_count
        }


@dataclass
class DXFParseResult:
    """Complete parse result"""
    filename: str
    dxf_version: str
    units: str
    
    # Geometry
    lines: list[DXFLine] = field(default_factory=list)
    circles: list[DXFCircle] = field(default_factory=list)
    arcs: list[DXFArc] = field(default_factory=list)
    polylines: list[DXFPolyline] = field(default_factory=list)
    texts: list[DXFText] = field(default_factory=list)
    dimensions: list[DXFDimension] = field(default_factory=list)
    blocks: list[DXFBlock] = field(default_factory=list)
    
    # Metadata
    layers: list[DXFLayer] = field(default_factory=list)
    
    # Statistics
    extents: Optional[dict] = None
    
    @property
    def total_entities(self) -> int:
        return (len(self.lines) + len(self.circles) + len(self.arcs) + 
                len(self.polylines) + len(self.texts) + len(self.dimensions) + 
                len(self.blocks))
    
    def to_dict(self) -> dict:
        return {
            "filename": self.filename,
            "dxf_version": self.dxf_version,
            "units": self.units,
            "statistics": {
                "total_entities": self.total_entities,
                "lines": len(self.lines),
                "circles": len(self.circles),
                "arcs": len(self.arcs),
                "polylines": len(self.polylines),
                "texts": len(self.texts),
                "dimensions": len(self.dimensions),
                "blocks": len(self.blocks),
                "layers": len(self.layers)
            },
            "extents": self.extents,
            "layers": [l.to_dict() for l in self.layers],
            "geometry": {
                "lines": [e.to_dict() for e in self.lines],
                "circles": [e.to_dict() for e in self.circles],
                "arcs": [e.to_dict() for e in self.arcs],
                "polylines": [e.to_dict() for e in self.polylines],
                "texts": [e.to_dict() for e in self.texts],
                "dimensions": [e.to_dict() for e in self.dimensions],
                "blocks": [e.to_dict() for e in self.blocks]
            }
        }


class DXFParserService:
    """
    Service for parsing DXF files and extracting structured data.
    
    Usage:
        parser = DXFParserService()
        result = parser.parse_file("drawing.dxf")
        
        # Access data
        for line in result.lines:
            print(f"Line: {line.start} -> {line.end}")
        
        # Export to dict/JSON
        data = result.to_dict()
    """
    
    # Unit codes to names
    UNITS = {
        0: "Unitless",
        1: "Inches",
        2: "Feet",
        3: "Miles",
        4: "Millimeters",
        5: "Centimeters",
        6: "Meters",
        7: "Kilometers",
        8: "Microinches",
        9: "Mils",
        10: "Yards",
        11: "Angstroms",
        12: "Nanometers",
        13: "Microns",
        14: "Decimeters",
        15: "Decameters",
        16: "Hectometers",
        17: "Gigameters",
        18: "Astronomical units",
        19: "Light years",
        20: "Parsecs"
    }
    
    def __init__(self):
        self.doc: Optional[Drawing] = None
        self.layer_entity_counts: dict[str, int] = {}
    
    def parse_file(self, filepath: str | Path) -> DXFParseResult:
        """Parse a DXF file and return structured data."""
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"DXF file not found: {filepath}")
        
        logger.info(f"Parsing DXF file: {filepath}")
        
        try:
            self.doc = ezdxf.readfile(str(filepath))
        except ezdxf.DXFStructureError as e:
            logger.warning(f"DXF structure error, trying recovery mode: {e}")
            self.doc, auditor = ezdxf.recover.readfile(str(filepath))
        
        return self._extract_data(filepath.name)
    
    def parse_bytes(self, content: bytes, filename: str = "upload.dxf") -> DXFParseResult:
        """Parse DXF content from bytes."""
        import io
        stream = io.StringIO(content.decode('utf-8', errors='ignore'))
        
        try:
            self.doc = ezdxf.read(stream)
        except ezdxf.DXFStructureError as e:
            logger.warning(f"DXF structure error: {e}")
            raise ValueError(f"Invalid DXF content: {e}")
        
        return self._extract_data(filename)
    
    def _extract_data(self, filename: str) -> DXFParseResult:
        """Extract all data from loaded document."""
        if not self.doc:
            raise ValueError("No document loaded")
        
        # Get header info
        dxf_version = self.doc.dxfversion
        units_code = self.doc.header.get("$INSUNITS", 0)
        units = self.UNITS.get(units_code, "Unknown")
        
        # Initialize result
        result = DXFParseResult(
            filename=filename,
            dxf_version=dxf_version,
            units=units
        )
        
        # Reset layer counts
        self.layer_entity_counts = {}
        
        # Parse modelspace entities
        msp = self.doc.modelspace()
        for entity in msp:
            self._parse_entity(entity, result)
        
        # Parse layers
        for layer in self.doc.layers:
            layer_name = layer.dxf.name
            result.layers.append(DXFLayer(
                name=layer_name,
                color=layer.dxf.color,
                linetype=layer.dxf.linetype,
                is_on=layer.is_on(),
                is_locked=layer.is_locked(),
                entity_count=self.layer_entity_counts.get(layer_name, 0)
            ))
        
        # Calculate extents
        try:
            from ezdxf import bbox
            cache = bbox.Cache()
            extents = bbox.extents(msp, cache=cache)
            if extents.has_data:
                result.extents = {
                    "min": {"x": extents.extmin[0], "y": extents.extmin[1], "z": extents.extmin[2]},
                    "max": {"x": extents.extmax[0], "y": extents.extmax[1], "z": extents.extmax[2]},
                    "size": {
                        "width": extents.extmax[0] - extents.extmin[0],
                        "height": extents.extmax[1] - extents.extmin[1],
                        "depth": extents.extmax[2] - extents.extmin[2]
                    }
                }
        except Exception as e:
            logger.warning(f"Could not calculate extents: {e}")
        
        logger.info(f"Parsed {result.total_entities} entities from {filename}")
        return result
    
    def _parse_entity(self, entity: DXFEntity, result: DXFParseResult):
        """Parse a single DXF entity."""
        entity_type = entity.dxftype()
        layer = entity.dxf.layer if hasattr(entity.dxf, 'layer') else "0"
        
        # Count entities per layer
        self.layer_entity_counts[layer] = self.layer_entity_counts.get(layer, 0) + 1
        
        try:
            if entity_type == "LINE":
                result.lines.append(DXFLine(
                    start=DXFPoint(*entity.dxf.start),
                    end=DXFPoint(*entity.dxf.end),
                    layer=layer,
                    color=entity.dxf.color if hasattr(entity.dxf, 'color') else 256
                ))
            
            elif entity_type == "CIRCLE":
                result.circles.append(DXFCircle(
                    center=DXFPoint(*entity.dxf.center),
                    radius=entity.dxf.radius,
                    layer=layer
                ))
            
            elif entity_type == "ARC":
                result.arcs.append(DXFArc(
                    center=DXFPoint(*entity.dxf.center),
                    radius=entity.dxf.radius,
                    start_angle=entity.dxf.start_angle,
                    end_angle=entity.dxf.end_angle,
                    layer=layer
                ))
            
            elif entity_type == "LWPOLYLINE":
                points = [DXFPoint(p[0], p[1], 0) for p in entity.get_points()]
                result.polylines.append(DXFPolyline(
                    points=points,
                    closed=entity.closed,
                    layer=layer
                ))
            
            elif entity_type == "POLYLINE":
                points = [DXFPoint(*v.dxf.location) for v in entity.vertices]
                result.polylines.append(DXFPolyline(
                    points=points,
                    closed=entity.is_closed,
                    layer=layer
                ))
            
            elif entity_type == "TEXT":
                result.texts.append(DXFText(
                    text=entity.dxf.text,
                    position=DXFPoint(*entity.dxf.insert),
                    height=entity.dxf.height,
                    rotation=entity.dxf.rotation if hasattr(entity.dxf, 'rotation') else 0,
                    layer=layer
                ))
            
            elif entity_type == "MTEXT":
                result.texts.append(DXFText(
                    text=entity.plain_text(),
                    position=DXFPoint(*entity.dxf.insert),
                    height=entity.dxf.char_height,
                    rotation=entity.dxf.rotation if hasattr(entity.dxf, 'rotation') else 0,
                    layer=layer
                ))
            
            elif entity_type == "DIMENSION":
                result.dimensions.append(DXFDimension(
                    dim_type=entity.dimtype.name if hasattr(entity, 'dimtype') else "UNKNOWN",
                    measurement=entity.dxf.actual_measurement if hasattr(entity.dxf, 'actual_measurement') else 0,
                    text_override=entity.dxf.text if hasattr(entity.dxf, 'text') else "",
                    layer=layer
                ))
            
            elif entity_type == "INSERT":
                result.blocks.append(DXFBlock(
                    name=entity.dxf.name,
                    position=DXFPoint(*entity.dxf.insert),
                    scale=(entity.dxf.xscale, entity.dxf.yscale, entity.dxf.zscale),
                    rotation=entity.dxf.rotation if hasattr(entity.dxf, 'rotation') else 0,
                    layer=layer
                ))
        
        except Exception as e:
            logger.debug(f"Could not parse {entity_type}: {e}")
    
    def get_layer_names(self) -> list[str]:
        """Get all layer names from loaded document."""
        if not self.doc:
            return []
        return [layer.dxf.name for layer in self.doc.layers]
    
    def get_entities_by_layer(self, layer_name: str) -> list[dict]:
        """Get all entities from a specific layer."""
        if not self.doc:
            return []
        
        msp = self.doc.modelspace()
        entities = []
        
        for entity in msp.query(f'*[layer=="{layer_name}"]'):
            entity_type = entity.dxftype()
            entities.append({
                "type": entity_type,
                "handle": entity.dxf.handle
            })
        
        return entities
    
    def extract_room_candidates(self, result: DXFParseResult) -> list[dict]:
        """
        Try to identify closed polylines that could represent rooms.
        Returns list of potential room boundaries with areas.
        """
        rooms = []
        
        for i, poly in enumerate(result.polylines):
            if poly.closed and poly.area > 1.0:  # Min 1m² area
                rooms.append({
                    "id": i,
                    "layer": poly.layer,
                    "area": round(poly.area, 2),
                    "perimeter": round(poly.length, 2),
                    "vertices": len(poly.points),
                    "centroid": self._calculate_centroid(poly.points)
                })
        
        # Sort by area descending
        rooms.sort(key=lambda r: r["area"], reverse=True)
        return rooms
    
    def _calculate_centroid(self, points: list[DXFPoint]) -> dict:
        """Calculate centroid of polygon."""
        if not points:
            return {"x": 0, "y": 0}
        
        x = sum(p.x for p in points) / len(points)
        y = sum(p.y for p in points) / len(points)
        return {"x": round(x, 2), "y": round(y, 2)}
    
    def extract_texts_near_rooms(self, result: DXFParseResult, rooms: list[dict], 
                                  tolerance: float = 2.0) -> list[dict]:
        """
        Match texts to rooms based on proximity to centroid.
        Useful for finding room names/numbers.
        """
        for room in rooms:
            centroid = room["centroid"]
            nearby_texts = []
            
            for text in result.texts:
                dx = abs(text.position.x - centroid["x"])
                dy = abs(text.position.y - centroid["y"])
                
                if dx < tolerance and dy < tolerance:
                    nearby_texts.append(text.text)
            
            room["labels"] = nearby_texts
        
        return rooms


# Convenience function
def parse_dxf(filepath: str | Path) -> DXFParseResult:
    """Quick parse function."""
    parser = DXFParserService()
    return parser.parse_file(filepath)
