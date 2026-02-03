"""Unit tests for FireSafetyService."""

import pytest

from cad_services.services.fire_safety_service import (
    ComplianceStatus,
    FireCompartment,
    FireRatedElement,
    FireRatingStandard,
    FireSafetyResult,
    FireSafetyService,
    rating_to_minutes,
)


class TestRatingToMinutes:
    """Test rating_to_minutes utility function."""

    def test_f30(self):
        assert rating_to_minutes("F30") == 30

    def test_f90(self):
        assert rating_to_minutes("F90") == 90

    def test_rei60(self):
        assert rating_to_minutes("REI60") == 60

    def test_f120(self):
        assert rating_to_minutes("F120") == 120

    def test_t30(self):
        assert rating_to_minutes("T30") == 30

    def test_none(self):
        assert rating_to_minutes(None) == 0

    def test_empty(self):
        assert rating_to_minutes("") == 0

    def test_no_number(self):
        assert rating_to_minutes("ABC") == 0


class TestFireRatedElement:
    """Test FireRatedElement dataclass."""

    def test_create_element(self):
        elem = FireRatedElement(
            element_type="wall",
            ifc_guid="abc123",
            name="Brandwand",
            actual_rating="F90",
        )
        assert elem.element_type == "wall"
        assert elem.ifc_guid == "abc123"
        assert elem.actual_rating == "F90"

    def test_element_with_required_rating(self):
        elem = FireRatedElement(
            element_type="door",
            ifc_guid="def456",
            name="Brandschutztür",
            actual_rating="T30",
            required_rating="T30",
            is_compliant=True,
        )
        assert elem.is_compliant is True

    def test_element_non_compliant(self):
        elem = FireRatedElement(
            element_type="door",
            ifc_guid="ghi789",
            name="Tür",
            actual_rating="T30",
            required_rating="T60",
            is_compliant=False,
        )
        assert elem.is_compliant is False


class TestFireCompartment:
    """Test FireCompartment dataclass."""

    def test_create_compartment(self):
        comp = FireCompartment(name="Brandabschnitt 1")
        assert comp.name == "Brandabschnitt 1"
        assert comp.status == ComplianceStatus.PENDING

    def test_compartment_with_sprinkler(self):
        from decimal import Decimal

        comp = FireCompartment(
            name="Brandabschnitt 2",
            area_m2=Decimal("800"),
            has_sprinkler=True,
        )
        assert comp.has_sprinkler is True


class TestFireSafetyService:
    """Test FireSafetyService."""

    @pytest.fixture
    def service(self):
        return FireSafetyService()

    @pytest.fixture
    def service_with_sprinkler(self):
        return FireSafetyService(has_sprinkler=True)

    def test_init_default(self, service):
        assert service.building_type == "standard"
        assert service.has_sprinkler is False
        assert service.max_compartment_area == 1600
        assert service.max_escape_distance == 35

    def test_init_with_sprinkler(self, service_with_sprinkler):
        assert service_with_sprinkler.max_compartment_area == 3200
        assert service_with_sprinkler.max_escape_distance == 70

    def test_init_high_rise(self):
        service = FireSafetyService(building_type="high_rise")
        assert service.max_compartment_area == 400
        assert service.max_escape_distance == 25

    def test_init_assembly(self):
        service = FireSafetyService(building_type="assembly")
        assert service.max_compartment_area == 1000
        assert service.max_escape_distance == 30

    def test_normalize_rating_f30(self, service):
        result = service._normalize_rating("F30")
        assert result == "F30"

    def test_normalize_rating_f90_a(self, service):
        result = service._normalize_rating("F90-A")
        assert result == "F90"

    def test_normalize_rating_rei60(self, service):
        result = service._normalize_rating("REI60")
        assert result == "REI60"

    def test_normalize_rating_with_spaces(self, service):
        result = service._normalize_rating("F 90")
        assert result == "F90"

    def test_detect_standard_din(self, service):
        result = service._detect_standard("F90")
        assert result == FireRatingStandard.DIN4102

    def test_detect_standard_euroclass(self, service):
        result = service._detect_standard("REI90")
        assert result == FireRatingStandard.EN13501


class TestFireSafetyResult:
    """Test FireSafetyResult dataclass."""

    def test_create_result(self):
        result = FireSafetyResult(model_id=1, is_compliant=True)
        assert result.model_id == 1
        assert result.is_compliant is True
        assert result.violations == []
        assert result.warnings == []

    def test_result_with_violations(self):
        result = FireSafetyResult(
            model_id=1,
            is_compliant=False,
            violations=["Brandwand nicht F90"],
        )
        assert result.is_compliant is False
        assert len(result.violations) == 1
