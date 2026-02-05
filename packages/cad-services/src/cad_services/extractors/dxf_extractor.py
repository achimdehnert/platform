from __future__ import annotations

from typing import Any

from ..mapping import MappingProfile
from ..models import (
    CADElement,
    CADGeometry,
    CADProperty,
    ElementCategory,
    Point3D,
    PropertySource,
    SourceFormat,
)
from .base import BaseExtractor


def _polygon_area(points: list[tuple[float, float]]) -> float:
    if len(points) < 3:
        return 0.0

    area = 0.0
    for (x1, y1), (x2, y2) in zip(points, points[1:] + [points[0]], strict=False):
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


class DXFExtractor(BaseExtractor):
    def __init__(self, profile: MappingProfile | None = None):
        self.profile = profile or MappingProfile.default()

    def extract(self, raw_entities: Any) -> list[CADElement]:
        elements: list[CADElement] = []

        for idx, entity in enumerate(raw_entities):
            layer = getattr(getattr(entity, "dxf", None), "layer", None)
            handle = getattr(getattr(entity, "dxf", None), "handle", None)

            if layer is None:
                layer = ""

            category: ElementCategory = self.profile.get_category_for_layer(layer)

            external_id = handle or str(idx)
            element_type = getattr(entity, "dxftype", lambda: "UNKNOWN")()

            geometry: CADGeometry | None = None

            try:
                if element_type == "LWPOLYLINE":
                    is_closed = bool(getattr(entity, "closed", False))
                    if is_closed:
                        pts = list(entity.get_points("xy"))
                        points = [(float(x), float(y)) for x, y in pts]
                        area = _polygon_area(points)
                        if area > 0:
                            geometry = CADGeometry(
                                footprint_points=[Point3D(x=x, y=y, z=0.0) for x, y in points],
                                footprint_area=area,
                            )
            except Exception:
                geometry = None

            properties = [
                CADProperty(
                    name="layer",
                    value=layer,
                    source=PropertySource.DXF_LAYER,
                )
            ]

            elements.append(
                CADElement(
                    source_format=SourceFormat.DXF,
                    external_id=external_id,
                    category=category,
                    element_type=element_type,
                    layer=layer,
                    properties=properties,
                    geometry=geometry,
                )
            )

        return elements
