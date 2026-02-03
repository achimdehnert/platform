from __future__ import annotations

from typing import Protocol

from ..models import CADElement, CADQuantity


class QuantityRule(Protocol):
    def apply(self, element: CADElement) -> list[CADQuantity]: ...


class QuantityEngine:
    def __init__(self, rules: list[QuantityRule]):
        self.rules = rules

    def apply(self, elements: list[CADElement]) -> list[CADElement]:
        for element in elements:
            for rule in self.rules:
                quantities = rule.apply(element)
                if quantities:
                    element.quantities.extend(quantities)
        return elements
