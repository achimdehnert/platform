from decimal import Decimal

import pytest

from cad_services.models import CADQuantity, QuantityMethod, QuantityType


def test_quantity_requires_method():
    with pytest.raises(Exception):
        CADQuantity(quantity_type=QuantityType.AREA, value=Decimal("1"), unit="m²")


def test_quantity_confidence_range():
    with pytest.raises(Exception):
        CADQuantity(
            quantity_type=QuantityType.AREA,
            value=Decimal("1"),
            unit="m²",
            method=QuantityMethod.IFC_QUANTITY,
            confidence=2.0,
        )


def test_quantity_unit_matches_type():
    with pytest.raises(Exception):
        CADQuantity(
            quantity_type=QuantityType.AREA,
            value=Decimal("1"),
            unit="m",
            method=QuantityMethod.IFC_QUANTITY,
        )


def test_computed_quantity_requires_inputs_and_formula():
    with pytest.raises(Exception):
        CADQuantity(
            quantity_type=QuantityType.AREA,
            value=Decimal("1"),
            unit="m²",
            method=QuantityMethod.COMPUTED_2D,
        )

    q = CADQuantity(
        quantity_type=QuantityType.AREA,
        value=Decimal("1"),
        unit="m²",
        method=QuantityMethod.COMPUTED_2D,
        inputs={"a": 1},
        formula="a",
    )
    assert q.formula == "a"
