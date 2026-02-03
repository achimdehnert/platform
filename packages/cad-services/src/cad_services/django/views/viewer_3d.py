"""3D Model Viewer Views using xeokit."""

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from cad_services.django.models import CADModel, Floor, Room


@require_GET
def model_viewer_3d(request, model_id: int):
    """Render 3D model viewer page with xeokit."""
    model = get_object_or_404(CADModel, pk=model_id)
    floors = Floor.objects.filter(cad_model_id=model_id).order_by("sort_order")

    context = {
        "model": model,
        "floors": floors,
        "page_title": f"3D Viewer: {model.name}",
        "xkt_url": f"/media/xkt/model_{model_id}.xkt",
        "metadata_url": f"/media/xkt/model_{model_id}.json",
    }

    return render(request, "cadhub/viewer/model_viewer_3d.html", context)


@require_GET
def model_structure_api(request, model_id: int):
    """API: Get model structure tree for tree view."""
    model = get_object_or_404(CADModel, pk=model_id)

    floors = Floor.objects.filter(cad_model_id=model_id).order_by("sort_order")

    structure = {
        "id": f"model_{model_id}",
        "name": model.name,
        "type": "Model",
        "children": [],
    }

    for floor in floors:
        floor_node = {
            "id": f"floor_{floor.id}",
            "ifc_guid": floor.ifc_guid,
            "name": floor.name,
            "type": "IfcBuildingStorey",
            "children": [],
        }

        rooms = Room.objects.filter(floor=floor)
        for room in rooms:
            room_node = {
                "id": f"room_{room.id}",
                "ifc_guid": room.ifc_guid,
                "name": room.name or room.number,
                "type": "IfcSpace",
            }
            floor_node["children"].append(room_node)

        structure["children"].append(floor_node)

    return JsonResponse(structure)


@require_GET
def element_properties_api(request, model_id: int):
    """API: Get properties for selected element."""
    ifc_guid = request.GET.get("guid")
    if not ifc_guid:
        return JsonResponse({"error": "Missing guid parameter"}, status=400)

    model = get_object_or_404(CADModel, pk=model_id)

    # Try to find element in different tables
    properties = {"ifc_guid": ifc_guid, "model": model.name}

    # Check rooms
    room = Room.objects.filter(cad_model=model, ifc_guid=ifc_guid).first()
    if room:
        properties.update({
            "type": "IfcSpace",
            "name": room.name,
            "number": room.number,
            "area_m2": float(room.area_m2) if room.area_m2 else None,
            "height_m": float(room.height_m) if room.height_m else None,
            "volume_m3": float(room.volume_m3) if room.volume_m3 else None,
            "usage_category": room.usage_category.code if room.usage_category else None,
            "floor": room.floor.name if room.floor else None,
        })
        return JsonResponse(properties)

    # Check floors
    floor = Floor.objects.filter(cad_model=model, ifc_guid=ifc_guid).first()
    if floor:
        properties.update({
            "type": "IfcBuildingStorey",
            "name": floor.name,
            "code": floor.code,
            "elevation_m": float(floor.elevation_m) if floor.elevation_m else None,
        })
        return JsonResponse(properties)

    # Element not found in our database
    properties["type"] = "Unknown"
    properties["note"] = "Element details not in database"

    return JsonResponse(properties)


@require_GET
def bcf_viewpoints_api(request, model_id: int):
    """API: Get/Save BCF viewpoints for model."""
    model = get_object_or_404(CADModel, pk=model_id)

    # Placeholder - would need BCFViewpoint model
    viewpoints = []

    return JsonResponse({
        "model_id": model_id,
        "model_name": model.name,
        "viewpoints": viewpoints,
    })


# ============================================================
# V3 VIEWER (xeokit SDK v3 with XGF format)
# ============================================================

@require_GET
def model_viewer_3d_v3(request, model_id: int):
    """Render 3D model viewer V3 with xeokit SDK v3 and XGF format."""
    from pathlib import Path

    model = get_object_or_404(CADModel, pk=model_id)
    floors = Floor.objects.filter(cad_model_id=model_id).order_by("sort_order")

    # Determine best loading strategy
    xgf_path = Path(f"./media/xgf/model_{model_id}.xgf")
    ifc_path = Path(f"./media/ifc/model_{model_id}.ifc")

    # Check which files exist and determine format
    if xgf_path.exists():
        load_format = "xgf"
        xgf_url = f"/media/xgf/model_{model_id}.xgf"
        datamodel_url = f"/media/xgf/model_{model_id}.json"
        ifc_url = ""
    elif ifc_path.exists():
        # Direct IFC loading for small files
        file_size_mb = ifc_path.stat().st_size / 1024 / 1024
        if file_size_mb < 20:
            load_format = "ifc"
            xgf_url = ""
            datamodel_url = ""
            ifc_url = f"/media/ifc/model_{model_id}.ifc"
        else:
            # Large file - need conversion
            load_format = "xgf"
            xgf_url = f"/media/xgf/model_{model_id}.xgf"
            datamodel_url = f"/media/xgf/model_{model_id}.json"
            ifc_url = ""
    else:
        # Fallback to XKT (legacy)
        load_format = "xkt"
        xgf_url = f"/media/xkt/model_{model_id}.xkt"
        datamodel_url = f"/media/xkt/model_{model_id}.json"
        ifc_url = ""

    context = {
        "model": model,
        "floors": floors,
        "page_title": f"3D Viewer V3: {model.name}",
        "format": load_format,
        "xgf_url": xgf_url,
        "datamodel_url": datamodel_url,
        "ifc_url": ifc_url,
    }

    return render(request, "cadhub/viewer/model_viewer_3d_v3.html", context)


@require_GET
def convert_model_api(request, model_id: int):
    """API: Convert IFC to XGF format."""
    from pathlib import Path
    from cad_services.services.xgf_converter_service import XGFConverterService

    model = get_object_or_404(CADModel, pk=model_id)

    # Check if IFC exists
    ifc_path = Path(f"./media/ifc/model_{model_id}.ifc")
    if not ifc_path.exists():
        return JsonResponse({
            "success": False,
            "error": "IFC file not found"
        }, status=404)

    # Convert
    converter = XGFConverterService(output_dir=Path("./media/xgf"))
    result = converter.convert_ifc(
        ifc_path=ifc_path,
        output_name=f"model_{model_id}"
    )

    if result.success:
        return JsonResponse({
            "success": True,
            "xgf_url": f"/media/xgf/model_{model_id}.xgf",
            "datamodel_url": f"/media/xgf/model_{model_id}.json",
            "stats": result.stats
        })
    else:
        return JsonResponse({
            "success": False,
            "error": result.error
        }, status=500)
