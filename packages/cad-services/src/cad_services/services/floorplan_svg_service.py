"""SVG Floor Plan Generator Service.

Generates 2D SVG floor plans from room and element data.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass
class SVGConfig:
    """Configuration for SVG generation."""

    width: int = 800
    height: int = 600
    padding: int = 40
    scale: float = 1.0
    show_rooms: bool = True
    show_doors: bool = True
    show_windows: bool = True
    show_labels: bool = True
    show_dimensions: bool = False
    highlight_fire_rated: bool = False
    room_fill: str = "#f8f9fa"
    room_stroke: str = "#495057"
    door_color: str = "#28a745"
    window_color: str = "#17a2b8"
    fire_wall_color: str = "#dc3545"
    text_color: str = "#212529"
    font_size: int = 12


class FloorplanSVGService:
    """Service for generating SVG floor plans."""

    def __init__(self, config: SVGConfig | None = None):
        """Initialize with optional config."""
        self.config = config or SVGConfig()

    def generate_svg(
        self,
        rooms: list[dict],
        doors: list[dict] | None = None,
        windows: list[dict] | None = None,
        walls: list[dict] | None = None,
        floor_name: str = "Grundriss",
    ) -> str:
        """Generate SVG floor plan.

        Args:
            rooms: List of room dicts with polygon coordinates
            doors: Optional list of door dicts
            windows: Optional list of window dicts
            walls: Optional list of wall dicts (for fire-rated highlighting)
            floor_name: Title for the floor plan

        Returns:
            SVG string
        """
        doors = doors or []
        windows = windows or []
        walls = walls or []

        bounds = self._calculate_bounds(rooms)
        scale, offset_x, offset_y = self._calc_transform(bounds)

        svg_parts = [self._svg_header(floor_name)]

        svg_parts.append(self._svg_defs())

        if self.config.highlight_fire_rated and walls:
            svg_parts.append(self._render_fire_walls(walls, scale, offset_x, offset_y))

        if self.config.show_rooms:
            svg_parts.append(self._render_rooms(rooms, scale, offset_x, offset_y))

        if self.config.show_doors:
            svg_parts.append(self._render_doors(doors, scale, offset_x, offset_y))

        if self.config.show_windows:
            svg_parts.append(self._render_windows(windows, scale, offset_x, offset_y))

        if self.config.show_labels:
            svg_parts.append(self._render_labels(rooms, scale, offset_x, offset_y))

        svg_parts.append(self._render_legend())
        svg_parts.append("</svg>")

        return "\n".join(svg_parts)

    def _svg_header(self, title: str) -> str:
        """Generate SVG header."""
        w, h = self.config.width, self.config.height
        return f'''<svg xmlns="http://www.w3.org/2000/svg"
     viewBox="0 0 {w} {h}"
     width="{w}" height="{h}"
     style="background: white; font-family: Arial, sans-serif;">
  <title>{title}</title>'''

    def _svg_defs(self) -> str:
        """Generate SVG definitions (patterns, markers)."""
        return """  <defs>
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="4" height="4">
      <path d="M-1,1 l2,-2 M0,4 l4,-4 M3,5 l2,-2"
            stroke="#dee2e6" stroke-width="1"/>
    </pattern>
    <marker id="door-swing" markerWidth="10" markerHeight="10"
            refX="5" refY="5" orient="auto">
      <path d="M 0 0 Q 5 5, 10 0" fill="none" stroke="#28a745"/>
    </marker>
  </defs>"""

    def _calculate_bounds(self, rooms: list[dict]) -> tuple[float, float, float, float]:
        """Calculate bounding box of all rooms."""
        min_x = min_y = float("inf")
        max_x = max_y = float("-inf")

        for room in rooms:
            coords = room.get("polygon", [])
            for point in coords:
                x, y = point[0], point[1]
                min_x = min(min_x, x)
                max_x = max(max_x, x)
                min_y = min(min_y, y)
                max_y = max(max_y, y)

        if min_x == float("inf"):
            return (0, 0, 100, 100)

        return (min_x, min_y, max_x, max_y)

    def _calc_transform(
        self, bounds: tuple[float, float, float, float]
    ) -> tuple[float, float, float]:
        """Calculate scale and offset for coordinate transform."""
        min_x, min_y, max_x, max_y = bounds
        data_width = max_x - min_x
        data_height = max_y - min_y

        if data_width == 0:
            data_width = 1
        if data_height == 0:
            data_height = 1

        available_w = self.config.width - 2 * self.config.padding
        available_h = self.config.height - 2 * self.config.padding - 60

        scale_x = available_w / data_width
        scale_y = available_h / data_height
        scale = min(scale_x, scale_y) * self.config.scale

        offset_x = self.config.padding - min_x * scale
        offset_y = self.config.padding - min_y * scale

        return scale, offset_x, offset_y

    def _transform_point(
        self, x: float, y: float, scale: float, offset_x: float, offset_y: float
    ) -> tuple[float, float]:
        """Transform a point from data coordinates to SVG coordinates."""
        svg_x = x * scale + offset_x
        svg_y = self.config.height - 60 - (y * scale + offset_y)
        return svg_x, svg_y

    def _render_rooms(
        self,
        rooms: list[dict],
        scale: float,
        offset_x: float,
        offset_y: float,
    ) -> str:
        """Render rooms as SVG polygons."""
        parts = ['  <g id="rooms">']

        for room in rooms:
            coords = room.get("polygon", [])
            if not coords:
                continue

            points = []
            for point in coords:
                sx, sy = self._transform_point(point[0], point[1], scale, offset_x, offset_y)
                points.append(f"{sx:.1f},{sy:.1f}")

            if points:
                room_id = room.get("id", "")
                room_name = room.get("name", "")
                fill = self.config.room_fill
                stroke = self.config.room_stroke

                usage = room.get("usage_category", "")
                if usage and usage.startswith("VF"):
                    fill = "#e9ecef"
                elif usage and usage.startswith("TF"):
                    fill = "#fff3cd"

                parts.append(
                    f'    <polygon points="{" ".join(points)}" '
                    f'fill="{fill}" stroke="{stroke}" stroke-width="1.5" '
                    f'data-room-id="{room_id}" data-room-name="{room_name}">'
                    f"<title>{room_name}</title></polygon>"
                )

        parts.append("  </g>")
        return "\n".join(parts)

    def _render_doors(
        self,
        doors: list[dict],
        scale: float,
        offset_x: float,
        offset_y: float,
    ) -> str:
        """Render doors as SVG rectangles with swing arcs."""
        parts = ['  <g id="doors">']

        for door in doors:
            x = door.get("x", 0)
            y = door.get("y", 0)
            width = door.get("width", 0.9) * scale
            sx, sy = self._transform_point(x, y, scale, offset_x, offset_y)

            color = self.config.door_color
            fire_rating = door.get("fire_rating")
            if fire_rating:
                color = self.config.fire_wall_color

            parts.append(
                f'    <rect x="{sx - width / 2:.1f}" y="{sy - 3}" '
                f'width="{width:.1f}" height="6" '
                f'fill="{color}" rx="1">'
                f"<title>{door.get('name', 'Tür')}"
                f"{' - ' + fire_rating if fire_rating else ''}</title>"
                f"</rect>"
            )

        parts.append("  </g>")
        return "\n".join(parts)

    def _render_windows(
        self,
        windows: list[dict],
        scale: float,
        offset_x: float,
        offset_y: float,
    ) -> str:
        """Render windows as SVG lines."""
        parts = ['  <g id="windows">']

        for window in windows:
            x = window.get("x", 0)
            y = window.get("y", 0)
            width = window.get("width", 1.0) * scale
            sx, sy = self._transform_point(x, y, scale, offset_x, offset_y)

            parts.append(
                f'    <line x1="{sx - width / 2:.1f}" y1="{sy}" '
                f'x2="{sx + width / 2:.1f}" y2="{sy}" '
                f'stroke="{self.config.window_color}" stroke-width="4">'
                f"<title>{window.get('name', 'Fenster')}</title></line>"
            )

        parts.append("  </g>")
        return "\n".join(parts)

    def _render_fire_walls(
        self,
        walls: list[dict],
        scale: float,
        offset_x: float,
        offset_y: float,
    ) -> str:
        """Render fire-rated walls with special styling."""
        parts = ['  <g id="fire-walls">']

        for wall in walls:
            if not wall.get("fire_rating"):
                continue

            start = wall.get("start", [0, 0])
            end = wall.get("end", [0, 0])
            sx1, sy1 = self._transform_point(start[0], start[1], scale, offset_x, offset_y)
            sx2, sy2 = self._transform_point(end[0], end[1], scale, offset_x, offset_y)

            parts.append(
                f'    <line x1="{sx1:.1f}" y1="{sy1:.1f}" '
                f'x2="{sx2:.1f}" y2="{sy2:.1f}" '
                f'stroke="{self.config.fire_wall_color}" '
                f'stroke-width="4" stroke-dasharray="8,4">'
                f"<title>{wall.get('name', 'Brandwand')} - "
                f"{wall.get('fire_rating', '')}</title></line>"
            )

        parts.append("  </g>")
        return "\n".join(parts)

    def _render_labels(
        self,
        rooms: list[dict],
        scale: float,
        offset_x: float,
        offset_y: float,
    ) -> str:
        """Render room labels."""
        parts = ['  <g id="labels">']

        for room in rooms:
            cx = room.get("centroid_x")
            cy = room.get("centroid_y")

            if cx is None or cy is None:
                coords = room.get("polygon", [])
                if coords:
                    cx = sum(p[0] for p in coords) / len(coords)
                    cy = sum(p[1] for p in coords) / len(coords)

            if cx is not None and cy is not None:
                sx, sy = self._transform_point(cx, cy, scale, offset_x, offset_y)
                name = room.get("name", "")
                number = room.get("number", "")
                area = room.get("area_m2")

                label = number or name
                if len(label) > 15:
                    label = label[:12] + "..."

                parts.append(
                    f'    <text x="{sx:.1f}" y="{sy:.1f}" '
                    f'text-anchor="middle" '
                    f'fill="{self.config.text_color}" '
                    f'font-size="{self.config.font_size}">'
                    f"{label}</text>"
                )

                if area:
                    area_val = float(area) if isinstance(area, Decimal) else area
                    parts.append(
                        f'    <text x="{sx:.1f}" y="{sy + 14:.1f}" '
                        f'text-anchor="middle" '
                        f'fill="#6c757d" font-size="{self.config.font_size - 2}">'
                        f"{area_val:.1f} m²</text>"
                    )

        parts.append("  </g>")
        return "\n".join(parts)

    def _render_legend(self) -> str:
        """Render legend at bottom of SVG."""
        y = self.config.height - 30
        return f'''  <g id="legend" transform="translate(20, {y})">
    <rect x="0" y="0" width="12" height="12" fill="{self.config.room_fill}"
          stroke="{self.config.room_stroke}"/>
    <text x="18" y="10" font-size="10">Raum</text>
    <rect x="70" y="0" width="12" height="12" fill="{self.config.door_color}"/>
    <text x="88" y="10" font-size="10">Tür</text>
    <line x1="140" y1="6" x2="152" y2="6" stroke="{self.config.window_color}"
          stroke-width="3"/>
    <text x="158" y="10" font-size="10">Fenster</text>
    <line x1="210" y1="6" x2="230" y2="6" stroke="{self.config.fire_wall_color}"
          stroke-width="3" stroke-dasharray="4,2"/>
    <text x="236" y="10" font-size="10">Brandwand</text>
  </g>'''

    def generate_from_model(
        self,
        model_id: int,
        floor_id: int | None = None,
        db_session: Any = None,
    ) -> str:
        """Generate SVG from database model.

        Args:
            model_id: CAD model ID
            floor_id: Optional floor filter
            db_session: Database session

        Returns:
            SVG string
        """
        rooms = []
        doors = []
        windows = []
        walls = []

        return self.generate_svg(
            rooms=rooms,
            doors=doors,
            windows=windows,
            walls=walls,
            floor_name=f"Model {model_id}",
        )
