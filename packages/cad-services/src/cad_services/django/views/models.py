"""
Model Views (IFC/DXF)
ADR-009: Database-driven model management
"""

from typing import Any

from django.http import HttpRequest, HttpResponse
from django.views.generic import DetailView, ListView, View

from cad_services.django.models.cadhub import CADModel
from cad_services.django.views.base import HTMXMixin, TenantMixin


class ModelListView(HTMXMixin, TenantMixin, ListView):
    """List all models for a project."""

    model = CADModel
    template_name = "cadhub/models/list.html"
    partial_template_name = "cadhub/models/partials/model_list.html"
    context_object_name = "models"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        project_id = self.kwargs.get("project_id")

        if project_id:
            qs = qs.filter(project_id=project_id)

        # Filter by parse status
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(parse_status=status)

        return qs.order_by("-created_at")


class ModelDetailView(HTMXMixin, TenantMixin, DetailView):
    """Model detail with parsed elements."""

    model = CADModel
    template_name = "cadhub/models/detail.html"
    partial_template_name = "cadhub/models/partials/model_detail.html"
    context_object_name = "model"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        model = self.object

        # Load related elements
        context["floors"] = model.floors.all()
        context["rooms"] = model.rooms.all()[:10]
        context["windows"] = model.windows.all()[:10]

        # Statistics
        context["stats"] = {
            "floor_count": model.floors.count(),
            "room_count": model.rooms.count(),
            "window_count": model.windows.count(),
            "door_count": model.doors.count(),
            "wall_count": model.walls.count(),
            "slab_count": model.slabs.count(),
        }

        return context


class ModelUploadView(TenantMixin, View):
    """Handle model file uploads with processing."""

    SUPPORTED_FORMATS = {"ifc": "ifc", "ifczip": "ifc", "dxf": "dxf", "dwg": "dwg"}

    def get(self, request: HttpRequest, project_id: int) -> HttpResponse:
        """Show upload form."""
        from django.shortcuts import get_object_or_404, render

        from cad_services.django.models.cadhub import Project

        project = get_object_or_404(Project, pk=project_id)
        return render(
            request,
            "cadhub/models/upload.html",
            {"project": project},
        )

    def post(self, request: HttpRequest, project_id: int) -> HttpResponse:
        """Handle file upload and processing."""
        import os
        from pathlib import Path

        from django.http import JsonResponse
        from django.shortcuts import get_object_or_404

        from cad_services.django.models.cadhub import Project

        get_object_or_404(Project, pk=project_id)

        file = request.FILES.get("file")
        if not file:
            return JsonResponse({"error": "Keine Datei"}, status=400)

        ext = file.name.lower().split(".")[-1]
        if ext not in self.SUPPORTED_FORMATS:
            return JsonResponse(
                {"error": f"Format nicht unterstützt: {ext}"},
                status=400,
            )

        # Save file
        upload_dir = Path(os.getenv("UPLOAD_DIR", "/tmp/cadhub/uploads"))
        tenant_id = self.get_tenant_id()
        file_dir = upload_dir / str(tenant_id) / str(project_id)
        file_dir.mkdir(parents=True, exist_ok=True)

        file_path = file_dir / file.name
        with open(file_path, "wb") as f:
            for chunk in file.chunks():
                f.write(chunk)

        # Create model record
        model = CADModel.objects.create(
            project_id=project_id,
            name=file.name,
            source_file_path=str(file_path),
            source_format=self.SUPPORTED_FORMATS[ext],
            file_size_bytes=file.size,
            status="pending",
            created_by_id=1,
        )

        # Process file
        result = self._process_file(model, file_path)

        if request.headers.get("HX-Request"):
            from django.shortcuts import render

            return render(
                request,
                "cadhub/models/partials/upload_result.html",
                {"model": model, "result": result},
            )

        return JsonResponse(
            {
                "id": model.pk,
                "name": model.name,
                "status": model.status,
                **result,
            }
        )

    def _process_file(self, model: CADModel, file_path) -> dict:
        """Process uploaded file and extract elements."""
        from pathlib import Path

        file_path = Path(file_path)
        result = {"errors": [], "warnings": []}

        try:
            model.status = "processing"
            model.save()

            if model.source_format == "ifc":
                result = self._process_ifc(model, file_path)
            elif model.source_format == "dxf":
                result = self._process_dxf(model, file_path)
            else:
                fmt = model.source_format
                result["errors"].append(f"Verarbeitung nicht möglich: {fmt}")

            if not result.get("errors"):
                model.status = "ready"
            else:
                model.status = "error"
                model.error_message = "; ".join(result["errors"])

            model.save()

        except Exception as e:
            model.status = "error"
            model.error_message = str(e)
            model.save()
            result["errors"].append(str(e))

        return result

    def _process_ifc(self, model: CADModel, file_path) -> dict:
        """Process IFC file."""
        from cad_services.django.models.cadhub import (
            Door,
            Floor,
            Room,
            Slab,
            Wall,
            Window,
        )
        from cad_services.services.ifc_service import IFCService

        service = IFCService()
        parse_result = service.parse_file(file_path)

        if parse_result.errors:
            return {"errors": parse_result.errors}

        # Store floors
        floor_map = {}
        for floor_data in parse_result.floors:
            floor = Floor.objects.create(
                cad_model=model,
                ifc_guid=floor_data.ifc_guid,
                name=floor_data.name,
                code=floor_data.code,
                elevation_m=floor_data.elevation_m,
                sort_order=floor_data.sort_order,
            )
            floor_map[floor_data.ifc_guid] = floor.pk

        # Store rooms
        for room_data in parse_result.rooms:
            floor_id = floor_map.get(room_data.floor_guid)
            Room.objects.create(
                cad_model=model,
                floor_id=floor_id,
                ifc_guid=room_data.ifc_guid,
                number=room_data.number,
                name=room_data.name,
                long_name=room_data.long_name,
                area_m2=room_data.area_m2,
                height_m=room_data.height_m,
                volume_m3=room_data.volume_m3,
                perimeter_m=room_data.perimeter_m,
            )

        # Store walls
        for wall_data in parse_result.walls:
            floor_id = floor_map.get(wall_data.floor_guid)
            Wall.objects.create(
                cad_model=model,
                floor_id=floor_id,
                ifc_guid=wall_data.ifc_guid,
                name=wall_data.name,
                length_m=wall_data.length_m,
                height_m=wall_data.height_m,
                thickness_m=wall_data.thickness_m,
                area_m2=wall_data.area_m2,
                is_external=wall_data.is_external,
            )

        # Store doors
        for door_data in parse_result.doors:
            floor_id = floor_map.get(door_data.floor_guid)
            Door.objects.create(
                cad_model=model,
                floor_id=floor_id,
                ifc_guid=door_data.ifc_guid,
                name=door_data.name,
                width_m=door_data.width_m,
                height_m=door_data.height_m,
            )

        # Store windows
        for window_data in parse_result.windows:
            floor_id = floor_map.get(window_data.floor_guid)
            Window.objects.create(
                cad_model=model,
                floor_id=floor_id,
                ifc_guid=window_data.ifc_guid,
                name=window_data.name,
                width_m=window_data.width_m,
                height_m=window_data.height_m,
                area_m2=window_data.area_m2,
            )

        # Store slabs
        for slab_data in parse_result.slabs:
            floor_id = floor_map.get(slab_data.floor_guid)
            Slab.objects.create(
                cad_model=model,
                floor_id=floor_id,
                ifc_guid=slab_data.ifc_guid,
                name=slab_data.name,
                area_m2=slab_data.area_m2,
                thickness_m=slab_data.thickness_m,
                is_floor=slab_data.is_floor,
            )

        model.ifc_schema = parse_result.ifc_schema
        model.save()

        return {
            "floors": len(parse_result.floors),
            "rooms": len(parse_result.rooms),
            "walls": len(parse_result.walls),
            "doors": len(parse_result.doors),
            "windows": len(parse_result.windows),
            "slabs": len(parse_result.slabs),
            "total_area_m2": float(parse_result.total_area),
            "errors": [],
            "warnings": parse_result.warnings,
        }

    def _process_dxf(self, model: CADModel, file_path) -> dict:
        """Process DXF file."""
        import uuid

        from cad_services.django.models.cadhub import Room
        from cad_services.services.dxf_service import DXFService

        service = DXFService()
        parse_result = service.parse_file(file_path)

        if parse_result.errors:
            return {"errors": parse_result.errors}

        # Store rooms from DXF
        for idx, room_data in enumerate(parse_result.rooms):
            Room.objects.create(
                cad_model=model,
                ifc_guid=str(uuid.uuid4())[:36],
                number=room_data.number or f"R{idx + 1}",
                name=room_data.name or room_data.layer,
                area_m2=room_data.area_m2,
                perimeter_m=room_data.perimeter_m,
                height_m=0,
                volume_m3=0,
            )

        return {
            "layers": len(parse_result.layers),
            "rooms": len(parse_result.rooms),
            "blocks": len(parse_result.blocks),
            "total_area_m2": float(parse_result.total_area),
            "errors": [],
            "warnings": parse_result.warnings,
        }
