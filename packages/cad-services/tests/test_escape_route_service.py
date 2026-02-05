"""Unit tests for EscapeRouteService."""

from decimal import Decimal

import pytest

from cad_services.services.escape_route_service import (
    EscapeRoute,
    EscapeRouteResult,
    EscapeRouteService,
)


class TestEscapeRoute:
    """Test EscapeRoute dataclass."""

    def test_create_escape_route(self):
        route = EscapeRoute(
            from_room_id=1,
            from_room_name="Büro 101",
            to_exit_type="external",
            to_element_id=5,
            distance_m=Decimal("25.5"),
            max_distance_m=Decimal("35"),
            is_compliant=True,
        )
        assert route.from_room_id == 1
        assert route.distance_m == Decimal("25.5")
        assert route.is_compliant is True

    def test_route_non_compliant(self):
        route = EscapeRoute(
            from_room_id=1,
            from_room_name="Büro 102",
            to_exit_type="stairway",
            to_element_id=6,
            distance_m=Decimal("40"),
            max_distance_m=Decimal("35"),
            is_compliant=False,
        )
        assert route.is_compliant is False


class TestEscapeRouteResult:
    """Test EscapeRouteResult dataclass."""

    def test_create_result(self):
        result = EscapeRouteResult(
            model_id=1,
            floor_id=None,
            is_compliant=True,
        )
        assert result.model_id == 1
        assert result.is_compliant is True
        assert result.routes == []

    def test_result_with_violations(self):
        result = EscapeRouteResult(
            model_id=1,
            floor_id=1,
            is_compliant=False,
            violations=["Fluchtweg zu lang"],
        )
        assert len(result.violations) == 1


class TestEscapeRouteService:
    """Test EscapeRouteService."""

    @pytest.fixture
    def service(self):
        return EscapeRouteService()

    @pytest.fixture
    def service_with_sprinkler(self):
        return EscapeRouteService(has_sprinkler=True)

    def test_init_default(self, service):
        assert service.building_type == "standard"
        assert service.has_sprinkler is False
        assert service.max_distance == Decimal("35")

    def test_init_with_sprinkler(self, service_with_sprinkler):
        assert service_with_sprinkler.max_distance == Decimal("70")

    def test_init_high_rise(self):
        service = EscapeRouteService(building_type="high_rise")
        assert service.max_distance == Decimal("25")

    def test_init_assembly(self):
        service = EscapeRouteService(building_type="assembly")
        assert service.max_distance == Decimal("30")

    def test_min_door_width(self, service):
        assert service.min_door_width == Decimal("0.90")

    def test_min_corridor_width(self, service):
        assert service.min_corridor_width == Decimal("1.20")

    @pytest.fixture
    def simple_rooms(self):
        """Create a simple room layout for testing."""
        return [
            {"id": 1, "name": "Raum A", "centroid_x": 0, "centroid_y": 0},
            {"id": 2, "name": "Raum B", "centroid_x": 10, "centroid_y": 0},
            {"id": 3, "name": "Flur", "centroid_x": 5, "centroid_y": 5},
        ]

    @pytest.fixture
    def simple_doors(self):
        """Room connections (doors) for simple layout."""
        return [
            {"id": 101, "room_ids": [1, 3], "width": Decimal("0.90")},
            {"id": 102, "room_ids": [2, 3], "width": Decimal("0.90")},
        ]

    @pytest.fixture
    def simple_exits(self):
        """Exit points for simple layout."""
        return [
            {"id": 201, "type": "external", "room_id": 3, "x": 5, "y": 10},
        ]

    def test_build_room_graph(self, service, simple_rooms, simple_doors, simple_exits):
        graph = service.build_room_graph(simple_rooms, simple_doors, simple_exits)
        assert graph is not None
        # 3 rooms + 1 exit
        assert graph.number_of_nodes() == 4
        # 2 doors + 1 exit connection
        assert graph.number_of_edges() == 3

    def test_calculate_escape_routes(
        self, service, simple_rooms, simple_doors, simple_exits
    ):
        graph = service.build_room_graph(simple_rooms, simple_doors, simple_exits)
        result = service.calculate_escape_routes(graph, model_id=1)
        assert isinstance(result, EscapeRouteResult)
        assert result.model_id == 1
        # Should have routes for 3 rooms
        assert len(result.routes) == 3

    def test_no_exits_violation(self, service, simple_rooms, simple_doors):
        graph = service.build_room_graph(simple_rooms, simple_doors, exits=[])
        result = service.calculate_escape_routes(graph, model_id=1)
        assert result.is_compliant is False
        assert "Keine Ausgänge" in result.violations[0]
