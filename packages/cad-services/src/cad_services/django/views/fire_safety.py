"""Fire Safety Analysis Views."""

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views import View
from django.views.decorators.http import require_GET

from cad_services.django.models import (
    CADModel,
    EscapeRoute,
    FireCompartment,
    FireRatedElement,
    Floor,
)


class FireSafetyDashboardView(View):
    """Fire safety overview for a CAD model."""

    template_name = "cadhub/fire_safety/dashboard.html"

    def get(self, request, model_id: int):
        model = get_object_or_404(CADModel, pk=model_id)
        floors = Floor.objects.filter(cad_model_id=model_id)

        compartments = FireCompartment.objects.filter(cad_model_id=model_id)
        rated_elements = FireRatedElement.objects.filter(cad_model_id=model_id)
        escape_routes = EscapeRoute.objects.filter(cad_model_id=model_id)

        stats = {
            "compartments": compartments.count(),
            "compliant_compartments": compartments.filter(status="compliant").count(),
            "rated_elements": rated_elements.count(),
            "compliant_elements": rated_elements.filter(is_compliant=True).count(),
            "escape_routes": escape_routes.count(),
            "compliant_routes": escape_routes.filter(is_compliant=True).count(),
        }

        violations = []
        for elem in rated_elements.filter(is_compliant=False):
            violations.append(
                {
                    "type": "element",
                    "name": elem.name or elem.element_type,
                    "issue": f"Erforderlich: {elem.required_rating}, "
                    f"Ist: {elem.actual_rating or 'k.A.'}",
                }
            )

        for route in escape_routes.filter(is_compliant=False):
            violations.append(
                {
                    "type": "route",
                    "name": f"Raum {route.from_room_id}",
                    "issue": f"Fluchtweg {route.distance_m}m > max. {route.max_distance_m}m",
                }
            )

        context = {
            "model": model,
            "floors": floors,
            "compartments": compartments,
            "stats": stats,
            "violations": violations,
            "page_title": f"Brandschutz: {model.name}",
        }

        return render(request, self.template_name, context)


class FireCompartmentListView(View):
    """List fire compartments for a model."""

    template_name = "cadhub/fire_safety/partials/compartment_list.html"

    def get(self, request, model_id: int):
        compartments = FireCompartment.objects.filter(cad_model_id=model_id).select_related("floor")

        floor_id = request.GET.get("floor")
        if floor_id:
            compartments = compartments.filter(floor_id=floor_id)

        context = {
            "compartments": compartments,
            "model_id": model_id,
        }

        return render(request, self.template_name, context)


class FireRatedElementListView(View):
    """List fire-rated elements for a model."""

    template_name = "cadhub/fire_safety/partials/element_list.html"

    def get(self, request, model_id: int):
        elements = FireRatedElement.objects.filter(cad_model_id=model_id).select_related(
            "compartment"
        )

        element_type = request.GET.get("type")
        if element_type:
            elements = elements.filter(element_type=element_type)

        compliant = request.GET.get("compliant")
        if compliant == "true":
            elements = elements.filter(is_compliant=True)
        elif compliant == "false":
            elements = elements.filter(is_compliant=False)

        context = {
            "elements": elements,
            "model_id": model_id,
        }

        return render(request, self.template_name, context)


class EscapeRouteListView(View):
    """List escape routes for a model."""

    template_name = "cadhub/fire_safety/partials/route_list.html"

    def get(self, request, model_id: int):
        routes = EscapeRoute.objects.filter(cad_model_id=model_id).select_related(
            "floor", "from_room"
        )

        floor_id = request.GET.get("floor")
        if floor_id:
            routes = routes.filter(floor_id=floor_id)

        compliant = request.GET.get("compliant")
        if compliant == "true":
            routes = routes.filter(is_compliant=True)
        elif compliant == "false":
            routes = routes.filter(is_compliant=False)

        context = {
            "routes": routes,
            "model_id": model_id,
        }

        return render(request, self.template_name, context)


@require_GET
def fire_safety_stats_api(request, model_id: int):
    """API endpoint for fire safety statistics."""
    model = get_object_or_404(CADModel, pk=model_id)

    compartments = FireCompartment.objects.filter(cad_model_id=model_id)
    elements = FireRatedElement.objects.filter(cad_model_id=model_id)
    routes = EscapeRoute.objects.filter(cad_model_id=model_id)

    data = {
        "model_id": model_id,
        "model_name": model.name,
        "compartments": {
            "total": compartments.count(),
            "compliant": compartments.filter(status="compliant").count(),
            "warning": compartments.filter(status="warning").count(),
            "violation": compartments.filter(status="violation").count(),
        },
        "elements": {
            "total": elements.count(),
            "compliant": elements.filter(is_compliant=True).count(),
            "non_compliant": elements.filter(is_compliant=False).count(),
            "undefined": elements.filter(is_compliant__isnull=True).count(),
            "by_type": {},
        },
        "routes": {
            "total": routes.count(),
            "compliant": routes.filter(is_compliant=True).count(),
            "non_compliant": routes.filter(is_compliant=False).count(),
        },
    }

    for elem_type in ["wall", "door", "slab"]:
        data["elements"]["by_type"][elem_type] = elements.filter(element_type=elem_type).count()

    return JsonResponse(data)
