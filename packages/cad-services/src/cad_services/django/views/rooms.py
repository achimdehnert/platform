"""
Room Views
ADR-009: HTMX-powered room management
"""

from decimal import Decimal, InvalidOperation

from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views import View

from cad_services.django.models import Floor, Room, UsageCategory


class RoomListView(View):
    """List rooms with HTMX filtering."""

    def get(self, request):
        rooms = Room.objects.select_related("floor", "cad_model", "usage_category")
        floors = Floor.objects.all()

        search = request.GET.get("search", "")
        floor_filter = request.GET.get("floor_filter", "")

        if search:
            rooms = rooms.filter(name__icontains=search)
        if floor_filter:
            rooms = rooms.filter(floor_id=floor_filter)

        total_area = rooms.aggregate(total=Sum("area_m2"))["total"] or 0
        total_volume = rooms.aggregate(total=Sum("volume_m3"))["total"] or 0

        context = {
            "rooms": rooms,
            "floors": floors,
            "total_area": total_area,
            "total_volume": total_volume,
            "room_count": rooms.count(),
            "floor_count": floors.count(),
        }

        if request.headers.get("HX-Request"):
            return render(
                request,
                "cadhub/rooms/partials/room_table.html",
                context,
            )
        return render(request, "cadhub/rooms/list.html", context)


class RoomDetailView(View):
    """Room detail modal content."""

    def get(self, request, pk):
        room = get_object_or_404(
            Room.objects.select_related("floor", "cad_model", "usage_category"),
            pk=pk,
        )
        return render(
            request,
            "cadhub/rooms/partials/room_detail_modal.html",
            {"room": room},
        )


class RoomEditView(View):
    """Room inline edit form with full CRUD."""

    def get(self, request, pk):
        room = get_object_or_404(
            Room.objects.select_related("floor", "usage_category"),
            pk=pk,
        )
        usage_categories = UsageCategory.objects.all()
        floors = Floor.objects.filter(cad_model_id=room.cad_model_id)

        return render(
            request,
            "cadhub/rooms/partials/room_edit_form.html",
            {
                "room": room,
                "usage_categories": usage_categories,
                "floors": floors,
            },
        )

    def post(self, request, pk):
        room = get_object_or_404(Room, pk=pk)

        # Update basic fields
        room.name = request.POST.get("name", room.name)
        room.number = request.POST.get("number", room.number)
        room.long_name = request.POST.get("long_name", room.long_name)

        # Update numeric fields with validation
        try:
            area = request.POST.get("area_m2")
            if area:
                room.area_m2 = Decimal(area)
        except (InvalidOperation, ValueError):
            pass

        try:
            height = request.POST.get("height_m")
            if height:
                room.height_m = Decimal(height)
        except (InvalidOperation, ValueError):
            pass

        # Update foreign keys
        usage_id = request.POST.get("usage_category_id")
        if usage_id:
            room.usage_category_id = int(usage_id) if usage_id else None

        floor_id = request.POST.get("floor_id")
        if floor_id:
            room.floor_id = int(floor_id) if floor_id else None

        room.save()

        # Return updated room row for HTMX swap
        if request.headers.get("HX-Request"):
            return render(
                request,
                "cadhub/rooms/partials/room_row.html",
                {"room": room},
            )

        return JsonResponse({"status": "ok", "id": room.pk})
