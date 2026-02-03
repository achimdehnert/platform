from __future__ import annotations

from typing import Any

from ..models import CADElement, CADProperty, ElementCategory, PropertySource, SourceFormat
from .base import BaseExtractor


class IFCExtractor(BaseExtractor):
    TYPE_MAPPING: dict[str, ElementCategory] = {
        "IfcWall": ElementCategory.WALL,
        "IfcWallStandardCase": ElementCategory.WALL,
        "IfcDoor": ElementCategory.DOOR,
        "IfcWindow": ElementCategory.WINDOW,
        "IfcSlab": ElementCategory.SLAB,
        "IfcSpace": ElementCategory.SPACE,
        "IfcColumn": ElementCategory.COLUMN,
        "IfcBeam": ElementCategory.BEAM,
        "IfcStair": ElementCategory.STAIR,
        "IfcRoof": ElementCategory.ROOF,
        "IfcZone": ElementCategory.ZONE,
    }

    def extract(self, raw_entities: Any) -> list[CADElement]:
        ifc = raw_entities
        elements: list[CADElement] = []

        for ifc_type, category in self.TYPE_MAPPING.items():
            for obj in ifc.by_type(ifc_type):
                external_id = getattr(obj, "GlobalId", None) or str(getattr(obj, "id", ""))
                name = getattr(obj, "Name", None) or ""

                properties = [
                    CADProperty(
                        name="ifc_type",
                        value=ifc_type,
                        source=PropertySource.IFC_ATTRIBUTE,
                    )
                ]

                elements.append(
                    CADElement(
                        source_format=SourceFormat.IFC,
                        external_id=external_id,
                        category=category,
                        element_type=ifc_type,
                        name=name,
                        properties=properties,
                    )
                )

        return elements
