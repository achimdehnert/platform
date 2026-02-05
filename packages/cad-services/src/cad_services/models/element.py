from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .geometry import CADGeometry
from .material import CADMaterial
from .property import CADProperty
from .quantity import CADQuantity


class ElementCategory(str, Enum):
    WALL = "wall"
    DOOR = "door"
    WINDOW = "window"
    SLAB = "slab"
    SPACE = "space"
    COLUMN = "column"
    BEAM = "beam"
    STAIR = "stair"
    ROOF = "roof"
    OPENING = "opening"
    EQUIPMENT = "equipment"
    ZONE = "zone"
    UNKNOWN = "unknown"


class SourceFormat(str, Enum):
    IFC = "ifc"
    DXF = "dxf"
    DWG = "dwg"


class CADElement(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: UUID = Field(default_factory=uuid4)

    source_format: SourceFormat
    external_id: str

    category: ElementCategory
    element_type: str
    type_name: str | None = None

    name: str = ""
    number: str | None = None

    storey_id: str | None = None
    storey_name: str | None = None
    space_id: str | None = None

    layer: str | None = None

    properties: list[CADProperty] = Field(default_factory=list)
    quantities: list[CADQuantity] = Field(default_factory=list)
    materials: list[CADMaterial] = Field(default_factory=list)

    geometry: CADGeometry | None = None

    @field_validator("external_id")
    @classmethod
    def _external_id_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("external_id must not be empty")
        return v

    def get_property(self, name: str, default: Any = None):
        for prop in self.properties:
            if prop.name == name:
                return prop.value
        return default
