"""Escape Route Analysis Service.

Calculates escape routes using graph algorithms (networkx).
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


try:
    import networkx as nx

    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    nx = None


@dataclass
class EscapeRoute:
    """Calculated escape route from a room to an exit."""

    from_room_id: int
    from_room_name: str
    to_exit_type: str  # 'external', 'stairway', 'compartment'
    to_element_id: int | None
    distance_m: Decimal
    max_distance_m: Decimal
    is_compliant: bool
    route_type: str = "primary"  # 'primary', 'secondary'
    path_room_ids: list[int] = field(default_factory=list)
    path_door_ids: list[int] = field(default_factory=list)
    min_width_m: Decimal | None = None
    required_width_m: Decimal = Decimal("0.90")


@dataclass
class EscapeRouteResult:
    """Result of escape route analysis."""

    model_id: int
    floor_id: int | None
    is_compliant: bool
    routes: list[EscapeRoute] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    statistics: dict[str, Any] = field(default_factory=dict)


class EscapeRouteService:
    """Service for escape route calculation using graph algorithms."""

    def __init__(
        self,
        building_type: str = "standard",
        has_sprinkler: bool = False,
    ):
        """Initialize service.

        Args:
            building_type: Type of building for max distance calculation
            has_sprinkler: Whether sprinkler system is installed
        """
        if not NETWORKX_AVAILABLE:
            raise ImportError(
                "networkx is required for escape route calculation. "
                "Install with: pip install networkx"
            )

        self.building_type = building_type
        self.has_sprinkler = has_sprinkler
        self._set_parameters()

    def _set_parameters(self) -> None:
        """Set analysis parameters based on building type."""
        params = {
            "standard": {
                "max_distance": Decimal("35"),
                "max_distance_sprinkler": Decimal("70"),
                "min_door_width": Decimal("0.90"),
                "min_corridor_width": Decimal("1.20"),
            },
            "industrial": {
                "max_distance": Decimal("50"),
                "max_distance_sprinkler": Decimal("100"),
                "min_door_width": Decimal("1.00"),
                "min_corridor_width": Decimal("1.50"),
            },
            "high_rise": {
                "max_distance": Decimal("25"),
                "max_distance_sprinkler": Decimal("50"),
                "min_door_width": Decimal("0.90"),
                "min_corridor_width": Decimal("1.20"),
            },
            "assembly": {
                "max_distance": Decimal("30"),
                "max_distance_sprinkler": Decimal("60"),
                "min_door_width": Decimal("1.20"),
                "min_corridor_width": Decimal("2.00"),
            },
            "healthcare": {
                "max_distance": Decimal("30"),
                "max_distance_sprinkler": Decimal("60"),
                "min_door_width": Decimal("1.20"),
                "min_corridor_width": Decimal("2.40"),
            },
        }
        p = params.get(self.building_type, params["standard"])

        if self.has_sprinkler:
            self.max_distance = p["max_distance_sprinkler"]
        else:
            self.max_distance = p["max_distance"]

        self.min_door_width = p["min_door_width"]
        self.min_corridor_width = p["min_corridor_width"]

    def build_room_graph(
        self,
        rooms: list[dict],
        doors: list[dict],
        exits: list[dict],
    ) -> "nx.Graph":
        """Build a graph representing room connectivity.

        Args:
            rooms: List of room dicts with id, name, centroid_x, centroid_y
            doors: List of door dicts with id, room_ids (list), width
            exits: List of exit dicts with id, type, room_id, position

        Returns:
            NetworkX graph with rooms as nodes and doors as edges
        """
        G = nx.Graph()

        for room in rooms:
            G.add_node(
                f"room_{room['id']}",
                node_type="room",
                room_id=room["id"],
                name=room.get("name", f"Room {room['id']}"),
                x=room.get("centroid_x", 0),
                y=room.get("centroid_y", 0),
            )

        for exit_point in exits:
            node_id = f"exit_{exit_point['id']}"
            G.add_node(
                node_id,
                node_type="exit",
                exit_type=exit_point.get("type", "external"),
                exit_id=exit_point["id"],
                x=exit_point.get("x", 0),
                y=exit_point.get("y", 0),
            )
            room_id = exit_point.get("room_id")
            if room_id:
                room_node = f"room_{room_id}"
                if G.has_node(room_node):
                    G.add_edge(
                        room_node,
                        node_id,
                        weight=Decimal("1"),
                        door_id=None,
                        width=exit_point.get("width", Decimal("0.90")),
                    )

        for door in doors:
            room_ids = door.get("room_ids", [])
            if len(room_ids) >= 2:
                room1 = f"room_{room_ids[0]}"
                room2 = f"room_{room_ids[1]}"
                if G.has_node(room1) and G.has_node(room2):
                    distance = self._calc_distance(G.nodes[room1], G.nodes[room2])
                    G.add_edge(
                        room1,
                        room2,
                        weight=distance,
                        door_id=door["id"],
                        width=door.get("width", Decimal("0.90")),
                    )

        return G

    def _calc_distance(self, node1: dict, node2: dict) -> Decimal:
        """Calculate Euclidean distance between two nodes."""
        import math

        x1, y1 = node1.get("x", 0), node1.get("y", 0)
        x2, y2 = node2.get("x", 0), node2.get("y", 0)
        dist = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        return Decimal(str(round(dist, 2)))

    def calculate_escape_routes(
        self,
        graph: "nx.Graph",
        model_id: int,
        floor_id: int | None = None,
    ) -> EscapeRouteResult:
        """Calculate shortest escape routes for all rooms.

        Args:
            graph: Room connectivity graph
            model_id: Database model ID
            floor_id: Optional floor filter

        Returns:
            EscapeRouteResult with all routes and compliance info
        """
        result = EscapeRouteResult(
            model_id=model_id,
            floor_id=floor_id,
            is_compliant=True,
        )

        room_nodes = [n for n, d in graph.nodes(data=True) if d.get("node_type") == "room"]
        exit_nodes = [n for n, d in graph.nodes(data=True) if d.get("node_type") == "exit"]

        if not exit_nodes:
            result.is_compliant = False
            result.violations.append("Keine Ausgänge im Modell gefunden")
            return result

        for room_node in room_nodes:
            room_data = graph.nodes[room_node]
            room_id = room_data["room_id"]
            room_name = room_data.get("name", f"Room {room_id}")

            shortest_route = None
            shortest_distance = None

            for exit_node in exit_nodes:
                try:
                    path = nx.shortest_path(graph, room_node, exit_node, weight="weight")
                    distance = self._calc_path_distance(graph, path)

                    if shortest_distance is None or distance < shortest_distance:
                        shortest_distance = distance
                        exit_data = graph.nodes[exit_node]
                        shortest_route = EscapeRoute(
                            from_room_id=room_id,
                            from_room_name=room_name,
                            to_exit_type=exit_data.get("exit_type", "external"),
                            to_element_id=exit_data.get("exit_id"),
                            distance_m=distance,
                            max_distance_m=self.max_distance,
                            is_compliant=distance <= self.max_distance,
                            path_room_ids=self._extract_room_ids(path),
                            path_door_ids=self._extract_door_ids(graph, path),
                            min_width_m=self._get_min_width(graph, path),
                            required_width_m=self.min_door_width,
                        )
                except nx.NetworkXNoPath:
                    continue

            if shortest_route:
                result.routes.append(shortest_route)
                if not shortest_route.is_compliant:
                    result.violations.append(
                        f"Raum '{room_name}': Fluchtweg {shortest_route.distance_m}m "
                        f"> max. {self.max_distance}m"
                    )
                    result.is_compliant = False
            else:
                result.violations.append(
                    f"Raum '{room_name}': Kein Fluchtweg zu einem Ausgang gefunden"
                )
                result.is_compliant = False

        result.statistics = self._calc_statistics(result.routes)
        return result

    def _calc_path_distance(self, graph: "nx.Graph", path: list[str]) -> Decimal:
        """Calculate total distance along a path."""
        total = Decimal("0")
        for i in range(len(path) - 1):
            edge_data = graph.get_edge_data(path[i], path[i + 1])
            if edge_data:
                weight = edge_data.get("weight", Decimal("1"))
                if isinstance(weight, int | float):
                    weight = Decimal(str(weight))
                total += weight
        return total

    def _extract_room_ids(self, path: list[str]) -> list[int]:
        """Extract room IDs from path."""
        return [int(node.split("_")[1]) for node in path if node.startswith("room_")]

    def _extract_door_ids(self, graph: "nx.Graph", path: list[str]) -> list[int]:
        """Extract door IDs from path edges."""
        door_ids = []
        for i in range(len(path) - 1):
            edge_data = graph.get_edge_data(path[i], path[i + 1])
            if edge_data and edge_data.get("door_id"):
                door_ids.append(edge_data["door_id"])
        return door_ids

    def _get_min_width(self, graph: "nx.Graph", path: list[str]) -> Decimal | None:
        """Get minimum door width along path."""
        widths = []
        for i in range(len(path) - 1):
            edge_data = graph.get_edge_data(path[i], path[i + 1])
            if edge_data and "width" in edge_data:
                w = edge_data["width"]
                if isinstance(w, int | float):
                    w = Decimal(str(w))
                widths.append(w)
        return min(widths) if widths else None

    def _calc_statistics(self, routes: list[EscapeRoute]) -> dict[str, Any]:
        """Calculate statistics from routes."""
        if not routes:
            return {"total_routes": 0}

        distances = [float(r.distance_m) for r in routes]
        compliant = sum(1 for r in routes if r.is_compliant)

        return {
            "total_routes": len(routes),
            "compliant_routes": compliant,
            "non_compliant_routes": len(routes) - compliant,
            "compliance_rate": round(compliant / len(routes) * 100, 1),
            "min_distance_m": min(distances),
            "max_distance_m": max(distances),
            "avg_distance_m": round(sum(distances) / len(distances), 2),
        }
