"""
Model Element Repositories
ADR-009: Data access for CAD elements (rooms, windows, etc.)
"""

from decimal import Decimal

from django.db.models import QuerySet, Sum

from cad_services.django.models.cadhub import (
    Door,
    Floor,
    Room,
    Slab,
    Wall,
    Window,
)
from cad_services.django.repositories.base import BaseRepository


class FloorRepository(BaseRepository[Floor]):
    """Repository for Floor operations."""

    model_class = Floor

    def __init__(self, model_id: int):
        self.model_id = model_id
        super().__init__()

    def get_queryset(self) -> QuerySet[Floor]:
        return Floor.objects.filter(model_id=self.model_id)

    def get_by_name(self, name: str) -> Floor | None:
        try:
            return self.get_queryset().get(name=name)
        except Floor.DoesNotExist:
            return None


class RoomRepository(BaseRepository[Room]):
    """Repository for Room operations."""

    model_class = Room

    def __init__(self, model_id: int):
        self.model_id = model_id
        super().__init__()

    def get_queryset(self) -> QuerySet[Room]:
        return Room.objects.filter(model_id=self.model_id)

    def get_by_floor(self, floor_id: int) -> QuerySet[Room]:
        return self.get_queryset().filter(floor_id=floor_id)

    def get_by_usage_category(self, category_id: int) -> QuerySet[Room]:
        return self.get_queryset().filter(usage_category_id=category_id)

    def get_total_area(self) -> Decimal:
        result = self.get_queryset().aggregate(total=Sum("area"))
        return result["total"] or Decimal("0")

    def get_total_volume(self) -> Decimal:
        result = self.get_queryset().aggregate(total=Sum("volume"))
        return result["total"] or Decimal("0")


class WindowRepository(BaseRepository[Window]):
    """Repository for Window operations."""

    model_class = Window

    def __init__(self, model_id: int):
        self.model_id = model_id
        super().__init__()

    def get_queryset(self) -> QuerySet[Window]:
        return Window.objects.filter(model_id=self.model_id)

    def get_by_floor(self, floor_id: int) -> QuerySet[Window]:
        return self.get_queryset().filter(floor_id=floor_id)

    def get_total_area(self) -> Decimal:
        result = self.get_queryset().aggregate(total=Sum("area"))
        return result["total"] or Decimal("0")


class DoorRepository(BaseRepository[Door]):
    """Repository for Door operations."""

    model_class = Door

    def __init__(self, model_id: int):
        self.model_id = model_id
        super().__init__()

    def get_queryset(self) -> QuerySet[Door]:
        return Door.objects.filter(model_id=self.model_id)

    def get_by_floor(self, floor_id: int) -> QuerySet[Door]:
        return self.get_queryset().filter(floor_id=floor_id)


class WallRepository(BaseRepository[Wall]):
    """Repository for Wall operations."""

    model_class = Wall

    def __init__(self, model_id: int):
        self.model_id = model_id
        super().__init__()

    def get_queryset(self) -> QuerySet[Wall]:
        return Wall.objects.filter(model_id=self.model_id)

    def get_external(self) -> QuerySet[Wall]:
        return self.get_queryset().filter(is_external=True)

    def get_internal(self) -> QuerySet[Wall]:
        return self.get_queryset().filter(is_external=False)

    def get_total_area(self, external_only: bool = False) -> Decimal:
        qs = self.get_external() if external_only else self.get_queryset()
        result = qs.aggregate(total=Sum("area"))
        return result["total"] or Decimal("0")


class SlabRepository(BaseRepository[Slab]):
    """Repository for Slab operations."""

    model_class = Slab

    def __init__(self, model_id: int):
        self.model_id = model_id
        super().__init__()

    def get_queryset(self) -> QuerySet[Slab]:
        return Slab.objects.filter(model_id=self.model_id)

    def get_by_type(self, slab_type: str) -> QuerySet[Slab]:
        return self.get_queryset().filter(slab_type=slab_type)

    def get_floors(self) -> QuerySet[Slab]:
        return self.get_by_type("floor")

    def get_ceilings(self) -> QuerySet[Slab]:
        return self.get_by_type("ceiling")

    def get_roofs(self) -> QuerySet[Slab]:
        return self.get_by_type("roof")
