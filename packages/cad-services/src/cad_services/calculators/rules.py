from __future__ import annotations

from decimal import Decimal

from ..models import CADElement, CADQuantity, QuantityMethod, QuantityType


class FootprintAreaQuantityRule:
    def __init__(self, *, confidence: float = 0.7):
        self.confidence = confidence

    def apply(self, element: CADElement) -> list[CADQuantity]:
        if element.geometry is None:
            return []
        if element.geometry.footprint_area is None:
            return []

        area = element.geometry.footprint_area
        if area <= 0:
            return []

        return [
            CADQuantity(
                quantity_type=QuantityType.AREA,
                value=Decimal(str(area)),
                unit="m²",
                method=QuantityMethod.COMPUTED_2D,
                confidence=self.confidence,
                inputs={"footprint_area": area},
                formula="footprint_area",
            )
        ]
