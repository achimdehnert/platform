"""Tests for writer module (ADR-034 §2).

Tests the mapping logic from CADElement → SQL parameters without
requiring a real PostgreSQL connection.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from cad_services.models import (
    CADElement,
    CADMaterial,
    CADParseResult,
    CADParseStatistics,
    CADProperty,
    CADQuantity,
    ElementCategory,
    PropertySource,
    QuantityMethod,
    QuantityType,
    SourceFormat,
)
from cad_services.writer.base import WriteResult
from cad_services.writer.postgres import (
    _first_material,
    _get_bool_property,
    _get_property_value,
    _get_quantity,
)


# ------------------------------------------------------------------
# Helper extraction functions
# ------------------------------------------------------------------


def _make_element(
    category: ElementCategory = ElementCategory.WALL,
    external_id: str = "abc123",
    element_type: str = "IfcWall",
    **kwargs,
) -> CADElement:
    return CADElement(
        source_format=SourceFormat.IFC,
        external_id=external_id,
        category=category,
        element_type=element_type,
        **kwargs,
    )


class TestGetQuantity:
    def test_should_return_matching_quantity(self) -> None:
        el = _make_element(
            quantities=[
                CADQuantity(
                    quantity_type=QuantityType.LENGTH,
                    value=Decimal("5.5"),
                    unit="m",
                    method=QuantityMethod.IFC_QUANTITY,
                ),
                CADQuantity(
                    quantity_type=QuantityType.AREA,
                    value=Decimal("12.3"),
                    unit="m²",
                    method=QuantityMethod.IFC_QUANTITY,
                ),
            ]
        )
        assert _get_quantity(el, QuantityType.AREA) == Decimal("12.3")

    def test_should_return_none_for_missing_type(self) -> None:
        el = _make_element(quantities=[])
        assert _get_quantity(el, QuantityType.VOLUME) is None

    def test_should_return_first_match(self) -> None:
        el = _make_element(
            quantities=[
                CADQuantity(
                    quantity_type=QuantityType.HEIGHT,
                    value=Decimal("2.8"),
                    unit="m",
                    method=QuantityMethod.IFC_QUANTITY,
                ),
                CADQuantity(
                    quantity_type=QuantityType.HEIGHT,
                    value=Decimal("3.0"),
                    unit="m",
                    method=QuantityMethod.IFC_ATTRIBUTE,
                ),
            ]
        )
        assert _get_quantity(el, QuantityType.HEIGHT) == Decimal("2.8")


class TestGetPropertyValue:
    def test_should_find_by_name_case_insensitive(self) -> None:
        el = _make_element(
            properties=[
                CADProperty(
                    name="IsExternal",
                    value=True,
                    source=PropertySource.IFC_PSET,
                ),
            ]
        )
        assert _get_property_value(el, "isexternal") is True

    def test_should_return_none_for_missing(self) -> None:
        el = _make_element(properties=[])
        assert _get_property_value(el, "FireRating") is None


class TestGetBoolProperty:
    @pytest.mark.parametrize(
        "raw_value,expected",
        [
            (True, True),
            (False, False),
            ("true", True),
            ("false", False),
            (".T.", True),
            ("ja", True),
            ("0", False),
            ("1", True),
        ],
    )
    def test_should_parse_various_bool_formats(
        self, raw_value: object, expected: bool
    ) -> None:
        el = _make_element(
            properties=[
                CADProperty(
                    name="LoadBearing",
                    value=raw_value,
                    source=PropertySource.IFC_PSET,
                ),
            ]
        )
        assert _get_bool_property(el, "LoadBearing") is expected

    def test_should_default_false_when_missing(self) -> None:
        el = _make_element(properties=[])
        assert _get_bool_property(el, "LoadBearing") is False


class TestFirstMaterial:
    def test_should_return_first_material_name(self) -> None:
        el = _make_element(
            materials=[
                CADMaterial(name="Beton"),
                CADMaterial(name="Stahl"),
            ]
        )
        assert _first_material(el) == "Beton"

    def test_should_return_none_when_empty(self) -> None:
        el = _make_element(materials=[])
        assert _first_material(el) is None


# ------------------------------------------------------------------
# WriteResult
# ------------------------------------------------------------------


class TestWriteResult:
    def test_should_calculate_total_elements(self) -> None:
        r = WriteResult(
            cad_model_id=1,
            floors_written=3,
            rooms_written=10,
            walls_written=20,
            windows_written=5,
            doors_written=8,
            slabs_written=3,
        )
        assert r.total_elements == 46
        assert r.floors_written == 3

    def test_should_have_empty_warnings_by_default(self) -> None:
        r = WriteResult(cad_model_id=1)
        assert r.warnings == []
        assert r.total_elements == 0


# ------------------------------------------------------------------
# CADParseResult structure (integration sanity check)
# ------------------------------------------------------------------


class TestCADParseResultStructure:
    def test_should_group_elements_by_category(self) -> None:
        elements = [
            _make_element(
                category=ElementCategory.WALL,
                external_id="w1",
            ),
            _make_element(
                category=ElementCategory.SPACE,
                external_id="r1",
                element_type="IfcSpace",
            ),
            _make_element(
                category=ElementCategory.WINDOW,
                external_id="win1",
                element_type="IfcWindow",
            ),
        ]
        result = CADParseResult(
            file_hash="abc",
            source_format=SourceFormat.IFC,
            parser_version="1.0",
            elements=elements,
            statistics=CADParseStatistics(total_elements=3),
        )

        by_cat = {}
        for el in result.elements:
            by_cat.setdefault(el.category, []).append(el)

        assert len(by_cat[ElementCategory.WALL]) == 1
        assert len(by_cat[ElementCategory.SPACE]) == 1
        assert len(by_cat[ElementCategory.WINDOW]) == 1
