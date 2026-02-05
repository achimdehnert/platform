"""Django views for Excel/PDF export."""

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from cad_services.django.models import CADModel, Floor, Room
from cad_services.services.excel_export_service import (
    ElementData,
    ExcelExportService,
    ExportConfig,
    RoomData,
)


@require_GET
def export_room_book(request, model_id: int):
    """Export room book as Excel."""
    model = get_object_or_404(CADModel, pk=model_id)

    rooms = Room.objects.filter(floor__model=model).select_related("floor")
    room_data = [
        RoomData(
            room_id=r.id,
            name=r.name or f"Raum {r.id}",
            number=r.room_number or "",
            floor_name=r.floor.name if r.floor else "",
            area_m2=r.area_m2 or 0,
            usage_type=r.usage_type or "",
            din277_category=r.din277_category or "",
            height_m=r.height_m,
            volume_m3=r.volume_m3,
        )
        for r in rooms
    ]

    service = ExcelExportService()
    excel_bytes = service.export_room_book(
        rooms=room_data,
        project_name=model.name,
    )

    response = HttpResponse(
        excel_bytes,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    filename = f"Raumbuch_{model.name.replace(' ', '_')}.xlsx"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@require_GET
def export_din277(request, model_id: int):
    """Export DIN 277 calculation as Excel."""
    model = get_object_or_404(CADModel, pk=model_id)

    floors = Floor.objects.filter(model=model)
    floor_data = []

    for floor in floors:
        rooms = Room.objects.filter(floor=floor)
        bgf = sum(r.area_m2 or 0 for r in rooms)
        ngf = bgf * 0.85  # Simplified calculation
        nuf = ngf * 0.80

        floor_data.append({
            "name": floor.name,
            "bgf": float(bgf),
            "kgf": float(bgf * 0.15),
            "ngf": float(ngf),
            "nuf": float(nuf),
            "tf": float(ngf * 0.10),
            "vf": float(ngf * 0.10),
        })

    service = ExcelExportService()
    excel_bytes = service.export_din277(
        floors=floor_data,
        project_name=model.name,
    )

    response = HttpResponse(
        excel_bytes,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    filename = f"DIN277_{model.name.replace(' ', '_')}.xlsx"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@require_GET
def export_fire_safety(request, model_id: int):
    """Export fire safety report as Excel."""
    model = get_object_or_404(CADModel, pk=model_id)

    # Get fire-rated elements from database
    from cad_services.django.models import FireRatedElement

    elements = FireRatedElement.objects.filter(model=model)
    element_data = [
        {
            "element_type": e.element_type,
            "name": e.name,
            "ifc_guid": e.ifc_guid,
            "required_rating": e.required_rating,
            "actual_rating": e.actual_rating,
            "is_compliant": e.is_compliant,
        }
        for e in elements
    ]

    service = ExcelExportService()
    excel_bytes = service.export_fire_safety_summary(
        rated_elements=element_data,
        project_name=model.name,
    )

    response = HttpResponse(
        excel_bytes,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    filename = f"Brandschutz_{model.name.replace(' ', '_')}.xlsx"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
