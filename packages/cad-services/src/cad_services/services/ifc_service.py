"""
IFC Domain Service
Extracts floors, rooms, walls, doors, windows from IFC files.
"""

import contextlib
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any


@dataclass
class FloorData:
    """Extracted floor data."""

    ifc_guid: str
    name: str
    code: str | None = None
    elevation_m: Decimal = Decimal("0")
    sort_order: int = 0


@dataclass
class RoomData:
    """Extracted room data."""

    ifc_guid: str
    number: str
    name: str
    long_name: str | None = None
    floor_guid: str | None = None
    area_m2: Decimal = Decimal("0")
    height_m: Decimal = Decimal("0")
    volume_m3: Decimal = Decimal("0")
    perimeter_m: Decimal = Decimal("0")


@dataclass
class WallData:
    """Extracted wall data."""

    ifc_guid: str
    name: str
    floor_guid: str | None = None
    length_m: Decimal = Decimal("0")
    height_m: Decimal = Decimal("0")
    thickness_m: Decimal = Decimal("0")
    area_m2: Decimal = Decimal("0")
    is_external: bool = False


@dataclass
class DoorData:
    """Extracted door data."""

    ifc_guid: str
    name: str
    floor_guid: str | None = None
    width_m: Decimal = Decimal("0")
    height_m: Decimal = Decimal("0")
    from_room_guid: str | None = None
    to_room_guid: str | None = None


@dataclass
class WindowData:
    """Extracted window data."""

    ifc_guid: str
    name: str
    floor_guid: str | None = None
    room_guid: str | None = None
    width_m: Decimal = Decimal("0")
    height_m: Decimal = Decimal("0")
    area_m2: Decimal = Decimal("0")


@dataclass
class SlabData:
    """Extracted slab data."""

    ifc_guid: str
    name: str
    floor_guid: str | None = None
    area_m2: Decimal = Decimal("0")
    thickness_m: Decimal = Decimal("0")
    is_floor: bool = True


@dataclass
class IFCParseResult:
    """Complete IFC parse result."""

    model_name: str
    ifc_schema: str | None = None
    floors: list[FloorData] = field(default_factory=list)
    rooms: list[RoomData] = field(default_factory=list)
    walls: list[WallData] = field(default_factory=list)
    doors: list[DoorData] = field(default_factory=list)
    windows: list[WindowData] = field(default_factory=list)
    slabs: list[SlabData] = field(default_factory=list)
    total_area: Decimal = Decimal("0")
    total_volume: Decimal = Decimal("0")
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class IFCService:
    """Domain service for IFC file processing."""

    def parse_file(self, file_path: Path) -> IFCParseResult:
        """Parse IFC file and extract building elements."""
        try:
            import ifcopenshell
        except ImportError as e:
            return IFCParseResult(
                model_name=file_path.stem,
                errors=[f"ifcopenshell nicht installiert: {e}"],
            )

        try:
            ifc = ifcopenshell.open(str(file_path))
        except Exception as e:
            return IFCParseResult(
                model_name=file_path.stem,
                errors=[f"IFC-Datei konnte nicht gelesen werden: {e}"],
            )

        schema = self._get_schema(ifc)
        model_name = self._get_project_name(ifc) or file_path.stem

        floors = self._extract_floors(ifc)
        rooms = self._extract_rooms(ifc)
        walls = self._extract_walls(ifc)
        doors = self._extract_doors(ifc)
        windows = self._extract_windows(ifc)
        slabs = self._extract_slabs(ifc)

        total_area = sum((r.area_m2 for r in rooms), Decimal("0"))
        total_volume = sum((r.volume_m3 for r in rooms), Decimal("0"))

        return IFCParseResult(
            model_name=model_name,
            ifc_schema=schema,
            floors=floors,
            rooms=rooms,
            walls=walls,
            doors=doors,
            windows=windows,
            slabs=slabs,
            total_area=total_area,
            total_volume=total_volume,
        )

    def _get_schema(self, ifc: Any) -> str | None:
        """Get IFC schema version."""
        try:
            return ifc.schema
        except Exception:
            return None

    def _get_project_name(self, ifc: Any) -> str | None:
        """Get project name from IfcProject."""
        try:
            projects = ifc.by_type("IfcProject")
            if projects:
                return projects[0].Name or projects[0].LongName
        except Exception:
            pass
        return None

    def _extract_floors(self, ifc: Any) -> list[FloorData]:
        """Extract IfcBuildingStorey elements."""
        floors = []
        try:
            for idx, storey in enumerate(ifc.by_type("IfcBuildingStorey")):
                elevation = Decimal("0")
                with contextlib.suppress(Exception):
                    elevation = Decimal(str(storey.Elevation or 0))

                floors.append(
                    FloorData(
                        ifc_guid=storey.GlobalId,
                        name=storey.Name or f"Etage {idx}",
                        code=storey.Name[:20] if storey.Name else None,
                        elevation_m=elevation,
                        sort_order=idx,
                    )
                )
        except Exception:
            pass

        floors.sort(key=lambda f: f.elevation_m)
        for idx, floor in enumerate(floors):
            floor.sort_order = idx

        return floors

    def _extract_rooms(self, ifc: Any) -> list[RoomData]:
        """Extract IfcSpace elements with quantities."""
        rooms = []
        try:
            for space in ifc.by_type("IfcSpace"):
                area = self._get_quantity(space, "NetFloorArea", "Area")
                height = self._get_quantity(space, "Height", "FinishCeilingHeight")
                volume = self._get_quantity(space, "NetVolume", "GrossVolume")
                perimeter = self._get_quantity(space, "Perimeter", "NetPerimeter")

                floor_guid = self._get_storey_guid(space)

                rooms.append(
                    RoomData(
                        ifc_guid=space.GlobalId,
                        number=self._get_property(space, "Number") or space.Name or "",
                        name=space.Name or "",
                        long_name=space.LongName,
                        floor_guid=floor_guid,
                        area_m2=area,
                        height_m=height,
                        volume_m3=volume,
                        perimeter_m=perimeter,
                    )
                )
        except Exception:
            pass
        return rooms

    def _extract_walls(self, ifc: Any) -> list[WallData]:
        """Extract IfcWall elements."""
        walls = []
        try:
            for wall in ifc.by_type("IfcWall"):
                length = self._get_quantity(wall, "Length", "NominalLength")
                height = self._get_quantity(wall, "Height", "NominalHeight")
                thickness = self._get_quantity(wall, "Width", "NominalWidth")
                area = self._get_quantity(wall, "NetSideArea", "GrossSideArea")

                is_external = self._get_property(wall, "IsExternal") == "True"

                walls.append(
                    WallData(
                        ifc_guid=wall.GlobalId,
                        name=wall.Name or "",
                        floor_guid=self._get_storey_guid(wall),
                        length_m=length,
                        height_m=height,
                        thickness_m=thickness,
                        area_m2=area,
                        is_external=is_external,
                    )
                )
        except Exception:
            pass
        return walls

    def _extract_doors(self, ifc: Any) -> list[DoorData]:
        """Extract IfcDoor elements."""
        doors = []
        try:
            for door in ifc.by_type("IfcDoor"):
                width = Decimal("0")
                height = Decimal("0")
                try:
                    width = Decimal(str(door.OverallWidth or 0))
                    height = Decimal(str(door.OverallHeight or 0))
                except Exception:
                    pass

                doors.append(
                    DoorData(
                        ifc_guid=door.GlobalId,
                        name=door.Name or "",
                        floor_guid=self._get_storey_guid(door),
                        width_m=width,
                        height_m=height,
                    )
                )
        except Exception:
            pass
        return doors

    def _extract_windows(self, ifc: Any) -> list[WindowData]:
        """Extract IfcWindow elements."""
        windows = []
        try:
            for window in ifc.by_type("IfcWindow"):
                width = Decimal("0")
                height = Decimal("0")
                try:
                    width = Decimal(str(window.OverallWidth or 0))
                    height = Decimal(str(window.OverallHeight or 0))
                except Exception:
                    pass

                area = width * height if width and height else Decimal("0")

                windows.append(
                    WindowData(
                        ifc_guid=window.GlobalId,
                        name=window.Name or "",
                        floor_guid=self._get_storey_guid(window),
                        width_m=width,
                        height_m=height,
                        area_m2=area,
                    )
                )
        except Exception:
            pass
        return windows

    def _extract_slabs(self, ifc: Any) -> list[SlabData]:
        """Extract IfcSlab elements."""
        slabs = []
        try:
            for slab in ifc.by_type("IfcSlab"):
                area = self._get_quantity(slab, "NetArea", "GrossArea")
                thickness = self._get_quantity(slab, "Width", "Depth")

                is_floor = True
                try:
                    pred_type = slab.PredefinedType
                    is_floor = pred_type in ("FLOOR", "BASESLAB", None)
                except Exception:
                    pass

                slabs.append(
                    SlabData(
                        ifc_guid=slab.GlobalId,
                        name=slab.Name or "",
                        floor_guid=self._get_storey_guid(slab),
                        area_m2=area,
                        thickness_m=thickness,
                        is_floor=is_floor,
                    )
                )
        except Exception:
            pass
        return slabs

    def _get_storey_guid(self, element: Any) -> str | None:
        """Get the IfcBuildingStorey GUID for an element."""
        try:
            for rel in element.Decomposes:
                if rel.is_a("IfcRelAggregates"):
                    parent = rel.RelatingObject
                    if parent.is_a("IfcBuildingStorey"):
                        return parent.GlobalId
        except Exception:
            pass

        try:
            for rel in element.ContainedInStructure:
                if rel.is_a("IfcRelContainedInSpatialStructure"):
                    structure = rel.RelatingStructure
                    if structure.is_a("IfcBuildingStorey"):
                        return structure.GlobalId
        except Exception:
            pass

        return None

    def _get_quantity(self, element: Any, *names: str) -> Decimal:
        """Get quantity value from element."""
        try:
            for rel in element.IsDefinedBy:
                if rel.is_a("IfcRelDefinesByProperties"):
                    prop_set = rel.RelatingPropertyDefinition
                    if prop_set.is_a("IfcElementQuantity"):
                        for qty in prop_set.Quantities:
                            if qty.Name in names:
                                if hasattr(qty, "AreaValue"):
                                    return Decimal(str(qty.AreaValue))
                                if hasattr(qty, "LengthValue"):
                                    return Decimal(str(qty.LengthValue))
                                if hasattr(qty, "VolumeValue"):
                                    return Decimal(str(qty.VolumeValue))
        except Exception:
            pass
        return Decimal("0")

    def _get_property(self, element: Any, name: str) -> str | None:
        """Get property value from element."""
        try:
            for rel in element.IsDefinedBy:
                if rel.is_a("IfcRelDefinesByProperties"):
                    prop_set = rel.RelatingPropertyDefinition
                    if prop_set.is_a("IfcPropertySet"):
                        for prop in prop_set.HasProperties:
                            if prop.Name == name:
                                val = prop.NominalValue
                                if val:
                                    return str(val.wrappedValue)
        except Exception:
            pass
        return None
