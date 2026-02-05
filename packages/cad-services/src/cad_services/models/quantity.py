from __future__ import annotations

from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class QuantityType(str, Enum):
    LENGTH = "length"
    AREA = "area"
    VOLUME = "volume"
    COUNT = "count"
    HEIGHT = "height"
    WIDTH = "width"
    THICKNESS = "thickness"
    PERIMETER = "perimeter"
    WEIGHT = "weight"


class QuantityMethod(str, Enum):
    IFC_QUANTITY = "ifc_quantity"
    IFC_ATTRIBUTE = "ifc_attribute"
    COMPUTED_GEOMETRY = "computed_geometry"
    COMPUTED_2D = "computed_2d"
    COMPUTED_HEURISTIC = "computed_heuristic"
    MANUAL = "manual"


_EXPECTED_UNITS: dict[QuantityType, set[str]] = {
    QuantityType.LENGTH: {"m"},
    QuantityType.HEIGHT: {"m"},
    QuantityType.WIDTH: {"m"},
    QuantityType.THICKNESS: {"m"},
    QuantityType.PERIMETER: {"m"},
    QuantityType.AREA: {"m²"},
    QuantityType.VOLUME: {"m³"},
    QuantityType.COUNT: {"Stk"},
    QuantityType.WEIGHT: {"kg"},
}


class CADQuantity(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    quantity_type: QuantityType
    value: Decimal
    unit: str

    method: QuantityMethod
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)

    source_name: str | None = None
    inputs: dict | None = None
    formula: str | None = None

    @field_validator("unit")
    @classmethod
    def _unit_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("unit must not be empty")
        return v

    @model_validator(mode="after")
    def _validate_invariants(self):
        expected = _EXPECTED_UNITS.get(self.quantity_type)
        if expected is not None and self.unit not in expected:
            raise ValueError(
                f"unit '{self.unit}' not allowed for quantity_type '{self.quantity_type}'"
            )

        computed_methods = {
            QuantityMethod.COMPUTED_GEOMETRY,
            QuantityMethod.COMPUTED_2D,
            QuantityMethod.COMPUTED_HEURISTIC,
        }
        if self.method in computed_methods and (self.inputs is None or self.formula is None):
            raise ValueError("computed quantities require inputs and formula")
        return self
