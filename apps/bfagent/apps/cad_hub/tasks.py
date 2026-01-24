# apps/cad_hub/tasks.py
"""
Background Tasks für IFC Verarbeitung

Nutzt BauCAD Hub MCP Patterns für:
- Vollständige Quantity-Extraktion
- DIN 277 Raumklassifizierung
- Robuste Fehlerbehandlung
"""
import logging
from pathlib import Path

from django.utils import timezone

logger = logging.getLogger(__name__)


def process_ifc_upload(model_id: str):
    """
    Verarbeitet einen IFC-Upload.

    Features:
    - Extrahiert Geschosse und Räume
    - Klassifiziert Räume nach DIN 277
    - Setzt usage_category automatisch
    """
    from decimal import Decimal

    from .models import Door, Floor, IFCModel, Room, Slab, Wall, Window
    from .services.ifc_parser import IFCParserService, RoomType

    # RoomType → Django UsageCategory Mapping
    ROOMTYPE_TO_USAGE = {
        RoomType.NF1_WOHNEN: "NF1.1",
        RoomType.NF1_BUERO: "NF1.2",
        RoomType.NF2: "NF2",
        RoomType.NF3: "NF3",
        RoomType.NF4: "NF4",
        RoomType.NF5: "NF5",
        RoomType.NF6: "NF6",
        RoomType.TF7: "TF7",
        RoomType.VF8: "VF8",
    }

    try:
        ifc_model = IFCModel.objects.get(pk=model_id)
        ifc_model.status = IFCModel.Status.PROCESSING
        ifc_model.save(update_fields=["status"])

        logger.info(f"Processing IFC: {model_id}")

        # Parse mit optimiertem Service
        parser = IFCParserService()
        result = parser.parse_file(Path(ifc_model.ifc_file.path))

        if result.errors:
            ifc_model.status = IFCModel.Status.ERROR
            ifc_model.error_message = "\n".join(result.errors)
            ifc_model.save()
            logger.error(f"Parse errors: {result.errors}")
            return

        # Metadata
        ifc_model.ifc_schema = result.schema
        ifc_model.application = result.application

        # Geschosse
        floor_map = {}
        for idx, parsed_floor in enumerate(result.floors):
            floor = Floor.objects.create(
                ifc_model=ifc_model,
                ifc_guid=parsed_floor.ifc_guid,
                name=parsed_floor.name,
                code=_generate_floor_code(parsed_floor.elevation),
                elevation=parsed_floor.elevation,
                sort_order=idx,
            )
            floor_map[parsed_floor.ifc_guid] = floor

        # Räume mit DIN 277 Klassifizierung
        room_map = {}
        for parsed_room in result.rooms:
            floor = floor_map.get(parsed_room.floor_guid)

            # RoomType zu UsageCategory
            usage_category = ROOMTYPE_TO_USAGE.get(parsed_room.room_type, "")

            room = Room.objects.create(
                ifc_model=ifc_model,
                floor=floor,
                ifc_guid=parsed_room.ifc_guid,
                number=parsed_room.number,
                name=parsed_room.name,
                long_name=parsed_room.long_name,
                area=parsed_room.area,
                height=parsed_room.height,
                volume=parsed_room.volume,
                perimeter=parsed_room.perimeter,
                usage_category=usage_category,  # Auto-klassifiziert!
            )
            room_map[parsed_room.ifc_guid] = room

        # Fenster
        for parsed_window in result.windows:
            floor = floor_map.get(parsed_window.floor_guid)

            Window.objects.create(
                ifc_model=ifc_model,
                floor=floor,
                ifc_guid=parsed_window.ifc_guid,
                number=parsed_window.number,
                name=parsed_window.name,
                width=Decimal(str(parsed_window.width)) if parsed_window.width else None,
                height=Decimal(str(parsed_window.height)) if parsed_window.height else None,
                area=Decimal(str(parsed_window.area)) if parsed_window.area else None,
                material=parsed_window.material,
                u_value=Decimal(str(parsed_window.u_value)) if parsed_window.u_value else None,
                properties=parsed_window.properties,
            )

        # Türen
        for parsed_door in result.doors:
            floor = floor_map.get(parsed_door.floor_guid)

            Door.objects.create(
                ifc_model=ifc_model,
                floor=floor,
                ifc_guid=parsed_door.ifc_guid,
                number=parsed_door.number,
                name=parsed_door.name,
                width=Decimal(str(parsed_door.width)) if parsed_door.width else None,
                height=Decimal(str(parsed_door.height)) if parsed_door.height else None,
                door_type=parsed_door.door_type,
                material=parsed_door.material,
                fire_rating=parsed_door.fire_rating,
            )

        # Wände
        for parsed_wall in result.walls:
            floor = floor_map.get(parsed_wall.floor_guid)

            Wall.objects.create(
                ifc_model=ifc_model,
                floor=floor,
                ifc_guid=parsed_wall.ifc_guid,
                name=parsed_wall.name,
                length=Decimal(str(parsed_wall.length)) if parsed_wall.length else None,
                height=Decimal(str(parsed_wall.height)) if parsed_wall.height else None,
                width=Decimal(str(parsed_wall.width)) if parsed_wall.width else None,
                gross_area=Decimal(str(parsed_wall.gross_area)) if parsed_wall.gross_area else None,
                net_area=Decimal(str(parsed_wall.net_area)) if parsed_wall.net_area else None,
                volume=Decimal(str(parsed_wall.volume)) if parsed_wall.volume else None,
                is_external=parsed_wall.is_external,
                is_load_bearing=parsed_wall.is_load_bearing,
                material=parsed_wall.material,
            )

        # Decken/Platten
        for parsed_slab in result.slabs:
            floor = floor_map.get(parsed_slab.floor_guid)

            Slab.objects.create(
                ifc_model=ifc_model,
                floor=floor,
                ifc_guid=parsed_slab.ifc_guid,
                name=parsed_slab.name,
                slab_type=parsed_slab.slab_type,
                area=Decimal(str(parsed_slab.area)) if parsed_slab.area else None,
                thickness=Decimal(str(parsed_slab.thickness)) if parsed_slab.thickness else None,
                volume=Decimal(str(parsed_slab.volume)) if parsed_slab.volume else None,
                perimeter=Decimal(str(parsed_slab.perimeter)) if parsed_slab.perimeter else None,
                material=parsed_slab.material,
            )

        # Status Ready
        ifc_model.status = IFCModel.Status.READY
        ifc_model.processed_at = timezone.now()
        ifc_model.save()

        logger.info(
            f"Processed {model_id}: {len(result.floors)} floors, "
            f"{len(result.rooms)} rooms, {len(result.windows)} windows, "
            f"{len(result.doors)} doors, {len(result.walls)} walls, "
            f"{len(result.slabs)} slabs"
        )

    except IFCModel.DoesNotExist:
        logger.error(f"Model {model_id} not found")
    except Exception as e:
        logger.exception(f"Processing error: {e}")
        try:
            ifc_model = IFCModel.objects.get(pk=model_id)
            ifc_model.status = IFCModel.Status.ERROR
            ifc_model.error_message = str(e)
            ifc_model.save()
        except Exception:
            pass


def _generate_floor_code(elevation: float) -> str:
    """Generiert Geschoss-Code aus Höhe"""
    if elevation < -0.5:
        level = int(abs(elevation) / 3) + 1
        return f"{level}.UG"
    elif elevation < 0.5:
        return "EG"
    else:
        level = int(elevation / 3)
        if level == 0:
            level = 1
        return f"{level}.OG"
