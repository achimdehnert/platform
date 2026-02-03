"""2D Floor Plan Viewer Views."""

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from cad_services.django.models.cadhub import CADModel, Floor, Room
from cad_services.services.floorplan_svg_service import (
    FloorplanSVGService,
    SVGConfig,
)


@require_GET
def floorplan_viewer(request, model_id: int):
    """Render 2D floor plan viewer page with iframe."""
    model = get_object_or_404(CADModel, pk=model_id)
    floors = Floor.objects.filter(cad_model_id=model_id).order_by("sort_order")

    selected_floor_id = request.GET.get("floor")
    if selected_floor_id:
        selected_floor = get_object_or_404(Floor, pk=selected_floor_id)
    else:
        selected_floor = floors.first()

    context = {
        "model": model,
        "floors": floors,
        "selected_floor": selected_floor,
        "page_title": f"Grundriss: {model.name}",
    }

    return render(request, "cadhub/viewer/floorplan_viewer.html", context)


@require_GET
def floorplan_svg(request, model_id: int):
    """Generate SVG floor plan for iframe embedding."""
    model = get_object_or_404(CADModel, pk=model_id)

    floor_id = request.GET.get("floor")
    show_fire = request.GET.get("fire", "0") == "1"
    show_labels = request.GET.get("labels", "1") == "1"
    width = int(request.GET.get("width", 800))
    height = int(request.GET.get("height", 600))

    room_qs = Room.objects.filter(cad_model_id=model_id)
    if floor_id:
        room_qs = room_qs.filter(floor_id=floor_id)

    rooms = []
    for room in room_qs:
        polygon = _get_room_polygon(room)
        if polygon:
            rooms.append(
                {
                    "id": room.id,
                    "name": room.name or room.number or f"Raum {room.id}",
                    "number": room.number,
                    "area_m2": room.area_m2,
                    "polygon": polygon,
                    "centroid_x": _calc_centroid_x(polygon),
                    "centroid_y": _calc_centroid_y(polygon),
                    "usage_category": (room.usage_category.code if room.usage_category else None),
                }
            )

    config = SVGConfig(
        width=width,
        height=height,
        show_labels=show_labels,
        highlight_fire_rated=show_fire,
    )

    service = FloorplanSVGService(config)

    floor_name = "Grundriss"
    if floor_id:
        floor = Floor.objects.filter(pk=floor_id).first()
        if floor:
            floor_name = floor.name or f"Etage {floor.code}"

    svg_content = service.generate_svg(
        rooms=rooms,
        floor_name=f"{model.name} - {floor_name}",
    )

    return HttpResponse(svg_content, content_type="image/svg+xml")


@require_GET
def floorplan_embed(request, model_id: int):
    """Render standalone SVG page for iframe embedding."""
    return floorplan_svg(request, model_id)


def _get_room_polygon(room: Room) -> list[list[float]] | None:
    """Extract polygon coordinates from room."""
    if hasattr(room, "polygon_coords") and room.polygon_coords:
        return room.polygon_coords

    if hasattr(room, "geometry") and room.geometry:
        try:
            import json

            geom = json.loads(room.geometry)
            if geom.get("type") == "Polygon":
                return geom.get("coordinates", [[]])[0]
        except (json.JSONDecodeError, TypeError):
            pass

    return _generate_simple_polygon(room)


def _generate_simple_polygon(room: Room) -> list[list[float]] | None:
    """Generate simple rectangular polygon from room area."""
    if not room.area_m2:
        return None

    import math

    area = float(room.area_m2)
    side = math.sqrt(area)

    offset_x = (room.id % 10) * side * 1.2
    offset_y = (room.id // 10) * side * 1.2

    return [
        [offset_x, offset_y],
        [offset_x + side, offset_y],
        [offset_x + side, offset_y + side],
        [offset_x, offset_y + side],
        [offset_x, offset_y],
    ]


def _calc_centroid_x(polygon: list[list[float]]) -> float:
    """Calculate centroid X coordinate."""
    if not polygon:
        return 0
    return sum(p[0] for p in polygon) / len(polygon)


def _calc_centroid_y(polygon: list[list[float]]) -> float:
    """Calculate centroid Y coordinate."""
    if not polygon:
        return 0
    return sum(p[1] for p in polygon) / len(polygon)
