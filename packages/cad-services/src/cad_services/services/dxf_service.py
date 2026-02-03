"""
DXF Domain Service
Extracts room polygons, blocks, and layers from DXF files.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path


@dataclass
class DXFLayerData:
    """Extracted layer information."""

    name: str
    color: int = 7
    is_visible: bool = True
    entity_count: int = 0


@dataclass
class DXFRoomData:
    """Extracted room from closed polyline."""

    layer: str
    name: str
    number: str = ""
    area_m2: Decimal = Decimal("0")
    perimeter_m: Decimal = Decimal("0")
    vertices: list[tuple[float, float]] = field(default_factory=list)


@dataclass
class DXFBlockData:
    """Extracted block reference (furniture, fixtures)."""

    block_name: str
    layer: str
    insert_point: tuple[float, float, float] = (0.0, 0.0, 0.0)
    scale: tuple[float, float, float] = (1.0, 1.0, 1.0)
    rotation: float = 0.0


@dataclass
class DXFTextData:
    """Extracted text/mtext for room labels."""

    text: str
    layer: str
    insert_point: tuple[float, float] = (0.0, 0.0)
    height: float = 2.5


@dataclass
class DXFParseResult:
    """Complete DXF parse result."""

    file_name: str
    layers: list[DXFLayerData] = field(default_factory=list)
    rooms: list[DXFRoomData] = field(default_factory=list)
    blocks: list[DXFBlockData] = field(default_factory=list)
    texts: list[DXFTextData] = field(default_factory=list)
    total_area: Decimal = Decimal("0")
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class DXFService:
    """Domain service for DXF file processing."""

    ROOM_LAYER_PATTERNS = [
        "raum",
        "room",
        "space",
        "zone",
        "a-area",
        "a-room",
        "a-space",
    ]

    def parse_file(self, file_path: Path) -> DXFParseResult:
        """Parse DXF file and extract elements."""
        try:
            import ezdxf
        except ImportError as e:
            return DXFParseResult(
                file_name=file_path.stem,
                errors=[f"ezdxf nicht installiert: {e}"],
            )

        try:
            doc = ezdxf.readfile(str(file_path))
        except Exception as e:
            return DXFParseResult(
                file_name=file_path.stem,
                errors=[f"DXF-Datei konnte nicht gelesen werden: {e}"],
            )

        layers = self._extract_layers(doc)
        rooms = self._extract_rooms(doc)
        blocks = self._extract_blocks(doc)
        texts = self._extract_texts(doc)

        # Match texts to rooms by proximity
        self._assign_room_labels(rooms, texts)

        total_area = sum((r.area_m2 for r in rooms), Decimal("0"))

        return DXFParseResult(
            file_name=file_path.stem,
            layers=layers,
            rooms=rooms,
            blocks=blocks,
            texts=texts,
            total_area=total_area,
        )

    def _extract_layers(self, doc) -> list[DXFLayerData]:
        """Extract layer information."""
        layers = []
        try:
            for layer in doc.layers:
                entity_count = len(list(doc.modelspace().query(f'*[layer=="{layer.dxf.name}"]')))
                layers.append(
                    DXFLayerData(
                        name=layer.dxf.name,
                        color=layer.dxf.color,
                        is_visible=layer.is_on(),
                        entity_count=entity_count,
                    )
                )
        except Exception:
            pass
        return layers

    def _extract_rooms(self, doc) -> list[DXFRoomData]:
        """Extract closed polylines as room boundaries."""
        rooms = []
        msp = doc.modelspace()

        # Extract from LWPOLYLINE
        try:
            for polyline in msp.query("LWPOLYLINE"):
                if not polyline.is_closed:
                    continue

                layer = polyline.dxf.layer.lower()
                if not self._is_room_layer(layer):
                    continue

                vertices = list(polyline.get_points("xy"))
                area, perimeter = self._calc_polygon_metrics(vertices)

                rooms.append(
                    DXFRoomData(
                        layer=polyline.dxf.layer,
                        name="",
                        area_m2=area,
                        perimeter_m=perimeter,
                        vertices=vertices,
                    )
                )
        except Exception:
            pass

        # Extract from POLYLINE (2D)
        try:
            for polyline in msp.query("POLYLINE"):
                if not polyline.is_closed:
                    continue

                layer = polyline.dxf.layer.lower()
                if not self._is_room_layer(layer):
                    continue

                vertices = [(v.dxf.location.x, v.dxf.location.y) for v in polyline.vertices]
                area, perimeter = self._calc_polygon_metrics(vertices)

                rooms.append(
                    DXFRoomData(
                        layer=polyline.dxf.layer,
                        name="",
                        area_m2=area,
                        perimeter_m=perimeter,
                        vertices=vertices,
                    )
                )
        except Exception:
            pass

        # Extract from HATCH (filled areas)
        try:
            for hatch in msp.query("HATCH"):
                layer = hatch.dxf.layer.lower()
                if not self._is_room_layer(layer):
                    continue

                for path in hatch.paths:
                    if hasattr(path, "vertices"):
                        vertices = [(v[0], v[1]) for v in path.vertices]
                        area, perimeter = self._calc_polygon_metrics(vertices)

                        rooms.append(
                            DXFRoomData(
                                layer=hatch.dxf.layer,
                                name="",
                                area_m2=area,
                                perimeter_m=perimeter,
                                vertices=vertices,
                            )
                        )
        except Exception:
            pass

        return rooms

    def _extract_blocks(self, doc) -> list[DXFBlockData]:
        """Extract block references (furniture, fixtures)."""
        blocks = []
        msp = doc.modelspace()

        try:
            for insert in msp.query("INSERT"):
                blocks.append(
                    DXFBlockData(
                        block_name=insert.dxf.name,
                        layer=insert.dxf.layer,
                        insert_point=(
                            insert.dxf.insert.x,
                            insert.dxf.insert.y,
                            insert.dxf.insert.z,
                        ),
                        scale=(
                            insert.dxf.xscale,
                            insert.dxf.yscale,
                            insert.dxf.zscale,
                        ),
                        rotation=insert.dxf.rotation,
                    )
                )
        except Exception:
            pass

        return blocks

    def _extract_texts(self, doc) -> list[DXFTextData]:
        """Extract TEXT and MTEXT entities for room labels."""
        texts = []
        msp = doc.modelspace()

        try:
            for text in msp.query("TEXT"):
                texts.append(
                    DXFTextData(
                        text=text.dxf.text,
                        layer=text.dxf.layer,
                        insert_point=(
                            text.dxf.insert.x,
                            text.dxf.insert.y,
                        ),
                        height=text.dxf.height,
                    )
                )
        except Exception:
            pass

        try:
            for mtext in msp.query("MTEXT"):
                texts.append(
                    DXFTextData(
                        text=mtext.text,
                        layer=mtext.dxf.layer,
                        insert_point=(
                            mtext.dxf.insert.x,
                            mtext.dxf.insert.y,
                        ),
                        height=mtext.dxf.char_height,
                    )
                )
        except Exception:
            pass

        return texts

    def _is_room_layer(self, layer_name: str) -> bool:
        """Check if layer is likely a room layer."""
        layer_lower = layer_name.lower()
        return any(p in layer_lower for p in self.ROOM_LAYER_PATTERNS)

    def _calc_polygon_metrics(
        self,
        vertices: list[tuple[float, float]],
    ) -> tuple[Decimal, Decimal]:
        """Calculate area and perimeter of polygon using Shoelace."""
        if len(vertices) < 3:
            return Decimal("0"), Decimal("0")

        # Shoelace formula for area
        n = len(vertices)
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += vertices[i][0] * vertices[j][1]
            area -= vertices[j][0] * vertices[i][1]
        area = abs(area) / 2.0

        # Perimeter
        perimeter = 0.0
        for i in range(n):
            j = (i + 1) % n
            dx = vertices[j][0] - vertices[i][0]
            dy = vertices[j][1] - vertices[i][1]
            perimeter += (dx * dx + dy * dy) ** 0.5

        return Decimal(str(round(area, 3))), Decimal(str(round(perimeter, 3)))

    def _assign_room_labels(
        self,
        rooms: list[DXFRoomData],
        texts: list[DXFTextData],
    ) -> None:
        """Assign text labels to rooms by checking if text is inside."""
        for room in rooms:
            if not room.vertices:
                continue

            for text in texts:
                if self._point_in_polygon(text.insert_point, room.vertices):
                    # Check if it looks like a room number
                    txt = text.text.strip()
                    if txt and len(txt) <= 20:
                        if room.number == "":
                            room.number = txt
                        elif room.name == "":
                            room.name = txt

    def _point_in_polygon(
        self,
        point: tuple[float, float],
        polygon: list[tuple[float, float]],
    ) -> bool:
        """Ray casting algorithm for point-in-polygon test."""
        x, y = point
        n = len(polygon)
        inside = False

        j = n - 1
        for i in range(n):
            xi, yi = polygon[i]
            xj, yj = polygon[j]

            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i

        return inside
