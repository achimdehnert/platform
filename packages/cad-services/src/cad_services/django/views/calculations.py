"""
Calculation Views
ADR-009: DIN 277 / WoFlV HTMX-powered calculations
"""

from decimal import Decimal

from django.http import HttpResponse
from django.shortcuts import render
from django.views import View

from cad_services.django.models import CADModel, Room


class DIN277View(View):
    """DIN 277 calculation page."""

    def get(self, request):
        models = CADModel.objects.select_related("project").all()
        return render(
            request,
            "cadhub/calculations/din277.html",
            {"models": models, "results": None},
        )


class DIN277CalculateView(View):
    """Calculate DIN 277 areas via HTMX."""

    def post(self, request):
        model_id = request.POST.get("model_id")
        if not model_id:
            return render(
                request,
                "cadhub/calculations/partials/din277_results.html",
                {"results": None, "error": "Kein Modell ausgewählt"},
            )

        rooms = Room.objects.filter(cad_model_id=model_id).select_related("usage_category", "floor")

        nuf_total = Decimal("0")
        tf_total = Decimal("0")
        vf_total = Decimal("0")

        for room in rooms:
            area = room.area_m2 or Decimal("0")
            if room.usage_category:
                cat = room.usage_category.din_category
                if cat == "TF":
                    tf_total += area
                elif cat == "VF":
                    vf_total += area
                else:
                    nuf_total += area
            else:
                nuf_total += area

        ngf_total = nuf_total + tf_total + vf_total
        bgf_total = ngf_total * Decimal("1.15")

        floors_data = []
        floor_rooms = {}
        for room in rooms:
            floor_name = room.floor.name if room.floor else "Unbekannt"
            if floor_name not in floor_rooms:
                floor_rooms[floor_name] = {
                    "name": floor_name,
                    "nuf": Decimal("0"),
                    "tf": Decimal("0"),
                    "vf": Decimal("0"),
                }
            area = room.area_m2 or Decimal("0")
            if room.usage_category and room.usage_category.din_category == "TF":
                floor_rooms[floor_name]["tf"] += area
            elif room.usage_category and room.usage_category.din_category == "VF":
                floor_rooms[floor_name]["vf"] += area
            else:
                floor_rooms[floor_name]["nuf"] += area

        for floor_data in floor_rooms.values():
            floor_data["ngf"] = floor_data["nuf"] + floor_data["tf"] + floor_data["vf"]
            floors_data.append(floor_data)

        results = {
            "model_id": model_id,
            "nuf_total": nuf_total,
            "tf_total": tf_total,
            "vf_total": vf_total,
            "ngf_total": ngf_total,
            "bgf_total": bgf_total,
            "floors": floors_data,
            "categories": [],
        }

        return render(
            request,
            "cadhub/calculations/partials/din277_results.html",
            {"results": results},
        )


class DIN277ExportView(View):
    """Export DIN 277 calculation to Excel."""

    def get(self, request, model_id):
        return HttpResponse(
            "Excel export not implemented",
            content_type="text/plain",
        )
