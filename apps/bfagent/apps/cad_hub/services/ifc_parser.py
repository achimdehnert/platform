# apps/cad_hub/services/ifc_parser.py
"""
Optimierter IFC Parser Service

Basiert auf Best Practices aus BauCAD Hub MCP:
- Vollständige Quantity-Extraktion
- DIN 277 Klassifizierung
- Robuste Fehlerbehandlung
"""
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Iterator, List, Optional

try:
    import ifcopenshell
    import ifcopenshell.util.element as element_util

    IFCOPENSHELL_AVAILABLE = True
except ImportError:
    IFCOPENSHELL_AVAILABLE = False
    ifcopenshell = None
    element_util = None

logger = logging.getLogger(__name__)


class RoomType(Enum):
    """DIN 277 Raumtypen"""

    NF1_WOHNEN = "NF1.1"
    NF1_BUERO = "NF1.2"
    NF2 = "NF2"
    NF3 = "NF3"
    NF4 = "NF4"
    NF5 = "NF5"
    NF6 = "NF6"
    TF7 = "TF7"
    VF8 = "VF8"
    UNKNOWN = ""


# Mapping RoomType → Django Model UsageCategory
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


@dataclass
class ParsedFloor:
    """Geparstes Geschoss"""

    ifc_guid: str
    name: str
    elevation: float
    rooms_count: int = 0


@dataclass
class ParsedRoom:
    """Geparseter Raum mit DIN 277 Klassifizierung"""

    ifc_guid: str
    number: str
    name: str
    long_name: str = ""
    area: float = 0.0
    height: float = 0.0
    volume: float = 0.0
    perimeter: float = 0.0
    floor_guid: Optional[str] = None
    room_type: RoomType = RoomType.UNKNOWN
    properties: dict = field(default_factory=dict)

    @property
    def usage_category(self) -> str:
        """Gibt Django Model UsageCategory zurück"""
        return ROOMTYPE_TO_USAGE.get(self.room_type, "")


@dataclass
class ParsedWindow:
    """Geparstes Fenster"""

    ifc_guid: str
    number: str = ""
    name: str = ""
    width: float = 0.0
    height: float = 0.0
    area: float = 0.0
    floor_guid: Optional[str] = None
    material: str = ""
    u_value: Optional[float] = None
    properties: dict = field(default_factory=dict)


@dataclass
class ParsedDoor:
    """Gepars te Tür"""

    ifc_guid: str
    number: str = ""
    name: str = ""
    width: float = 0.0
    height: float = 0.0
    door_type: str = ""
    floor_guid: Optional[str] = None
    material: str = ""
    fire_rating: str = ""
    properties: dict = field(default_factory=dict)


@dataclass
class ParsedWall:
    """Gepars te Wand"""

    ifc_guid: str
    name: str = ""
    length: float = 0.0
    height: float = 0.0
    width: float = 0.0
    gross_area: float = 0.0
    net_area: float = 0.0
    volume: float = 0.0
    floor_guid: Optional[str] = None
    is_external: bool = False
    is_load_bearing: bool = False
    material: str = ""


@dataclass
class ParsedSlab:
    """Gepars te Decke/Platte"""

    ifc_guid: str
    name: str = ""
    slab_type: str = "FLOOR"
    area: float = 0.0
    thickness: float = 0.0
    volume: float = 0.0
    perimeter: float = 0.0
    floor_guid: Optional[str] = None
    material: str = ""


@dataclass
class IFCParseResult:
    """Ergebnis des IFC Parsings"""

    schema: str = ""
    application: str = ""
    project_name: str = ""
    floors: List[ParsedFloor] = field(default_factory=list)
    rooms: List[ParsedRoom] = field(default_factory=list)
    windows: List[ParsedWindow] = field(default_factory=list)
    doors: List[ParsedDoor] = field(default_factory=list)
    walls: List[ParsedWall] = field(default_factory=list)
    slabs: List[ParsedSlab] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def total_area(self) -> float:
        return sum(r.area for r in self.rooms)


class IFCParserService:
    """
    Optimierter IFC Parser - nutzt BauCAD Hub MCP Patterns
    """

    def __init__(self):
        self._ifc = None
        self._unit_scale = 1.0
        self._element_util = None

    def parse_file(self, file_path: Path) -> IFCParseResult:
        """Parst IFC-Datei"""
        result = IFCParseResult()

        # Check if ifcopenshell is available
        if not IFCOPENSHELL_AVAILABLE:
            error_msg = (
                "ifcopenshell nicht installiert - bitte 'pip install ifcopenshell' ausführen"
            )
            result.errors.append(error_msg)
            logger.error(error_msg)
            return result

        try:
            logger.info(f"Opening IFC file: {file_path}")
            self._ifc = ifcopenshell.open(str(file_path))
            self._element_util = element_util

            result.schema = self._ifc.schema
            result.project_name = self._get_project_name()
            result.application = self._get_application()
            self._unit_scale = self._get_unit_scale()

            logger.info("Extracting IFC elements...")
            result.floors = list(self._extract_floors())
            result.rooms = list(self._extract_rooms())
            result.windows = list(self._extract_windows())
            result.doors = list(self._extract_doors())
            result.walls = list(self._extract_walls())
            result.slabs = list(self._extract_slabs())
            self._count_rooms_per_floor(result)

            logger.info(
                f"Parsed: {len(result.floors)} floors, {len(result.rooms)} rooms, "
                f"{len(result.windows)} windows, {len(result.doors)} doors, "
                f"{len(result.walls)} walls, {len(result.slabs)} slabs"
            )

        except Exception as e:
            error_msg = f"IFC Parse Error: {str(e)}"
            result.errors.append(error_msg)
            logger.exception(error_msg)

        return result

    def _get_project_name(self) -> str:
        try:
            projects = self._ifc.by_type("IfcProject")
            return projects[0].Name if projects else "Unbenannt"
        except:
            return "Unbenannt"

    def _get_application(self) -> str:
        try:
            for oh in self._ifc.by_type("IfcOwnerHistory"):
                if oh.OwningApplication:
                    return oh.OwningApplication.ApplicationFullName or ""
        except:
            pass
        return ""

    def _get_unit_scale(self) -> float:
        try:
            for ua in self._ifc.by_type("IfcUnitAssignment"):
                for unit in ua.Units:
                    if unit.is_a("IfcSIUnit") and unit.UnitType == "LENGTHUNIT":
                        if unit.Prefix == "MILLI":
                            return 0.001
                        elif unit.Prefix == "CENTI":
                            return 0.01
        except:
            pass
        return 1.0

    def _extract_floors(self) -> Iterator[ParsedFloor]:
        storeys = self._ifc.by_type("IfcBuildingStorey")
        for storey in sorted(storeys, key=lambda s: s.Elevation or 0):
            yield ParsedFloor(
                ifc_guid=storey.GlobalId,
                name=storey.Name or "Unbenannt",
                elevation=(storey.Elevation or 0) * self._unit_scale,
            )

    def _extract_rooms(self) -> Iterator[ParsedRoom]:
        for space in self._ifc.by_type("IfcSpace"):
            room = ParsedRoom(
                ifc_guid=space.GlobalId,
                number=self._get_room_number(space),
                name=space.LongName or space.Name or "Raum",
                long_name=space.Description or "",
            )

            # Quantities
            room.area = self._get_quantity(space, "NetFloorArea") or 0
            room.height = self._get_quantity(space, "Height") or 0
            room.volume = self._get_quantity(space, "NetVolume") or 0
            room.perimeter = self._get_quantity(space, "NetPerimeter") or 0

            # Scale
            room.area = round(room.area * self._unit_scale**2, 2)
            room.height = round(room.height * self._unit_scale, 2)
            room.volume = round(room.volume * self._unit_scale**3, 2)
            room.perimeter = round(room.perimeter * self._unit_scale, 2)

            room.floor_guid = self._find_floor(space)
            room.room_type = self._classify_room(space)

            yield room

    def _get_room_number(self, space) -> str:
        if space.Name:
            parts = space.Name.split()
            if parts:
                return parts[0]
        return ""

    def _get_quantity(self, element, name: str) -> Optional[float]:
        try:
            for rel in element.IsDefinedBy:
                if rel.is_a("IfcRelDefinesByProperties"):
                    pset = rel.RelatingPropertyDefinition
                    if pset.is_a("IfcElementQuantity"):
                        for q in pset.Quantities:
                            if q.Name == name:
                                if hasattr(q, "AreaValue"):
                                    return float(q.AreaValue)
                                elif hasattr(q, "LengthValue"):
                                    return float(q.LengthValue)
                                elif hasattr(q, "VolumeValue"):
                                    return float(q.VolumeValue)
        except:
            pass
        return None

    def _find_floor(self, space) -> Optional[str]:
        try:
            for rel in self._ifc.by_type("IfcRelContainedInSpatialStructure"):
                if space in rel.RelatedElements:
                    if rel.RelatingStructure.is_a("IfcBuildingStorey"):
                        return rel.RelatingStructure.GlobalId
        except:
            pass
        return None

    def _classify_room(self, space) -> RoomType:
        name = (space.Name or "").lower() + " " + (space.LongName or "").lower()

        if any(w in name for w in ["wohn", "schlaf", "kind"]):
            return RoomType.NF1_WOHNEN
        elif any(w in name for w in ["büro", "office"]):
            return RoomType.NF1_BUERO
        elif any(w in name for w in ["flur", "gang", "treppen"]):
            return RoomType.VF8
        elif any(w in name for w in ["technik", "heizung"]):
            return RoomType.TF7
        elif any(w in name for w in ["lager", "abstell"]):
            return RoomType.NF3

        return RoomType.UNKNOWN

    def _count_rooms_per_floor(self, result: IFCParseResult):
        counts = {}
        for room in result.rooms:
            if room.floor_guid:
                counts[room.floor_guid] = counts.get(room.floor_guid, 0) + 1
        for floor in result.floors:
            floor.rooms_count = counts.get(floor.ifc_guid, 0)

    def _extract_windows(self) -> Iterator[ParsedWindow]:
        """Extrahiert Fenster aus IFC"""
        for window in self._ifc.by_type("IfcWindow"):
            parsed = ParsedWindow(
                ifc_guid=window.GlobalId,
                name=window.Name or "",
                number=self._get_element_number(window),
            )

            # Geometrie
            parsed.width = self._get_quantity(window, "Width") or 0
            parsed.height = self._get_quantity(window, "Height") or 0

            # Scale
            parsed.width = round(parsed.width * self._unit_scale, 3)
            parsed.height = round(parsed.height * self._unit_scale, 3)
            parsed.area = round(parsed.width * parsed.height, 3)

            # Eigenschaften (spezifische)
            parsed.material = self._get_property(window, "Material") or ""
            u_val = self._get_property(window, "ThermalTransmittance")
            if u_val:
                try:
                    parsed.u_value = float(u_val)
                except:
                    pass

            # Geschoss
            parsed.floor_guid = self._find_element_floor(window)

            # ALLE Properties extrahieren
            parsed.properties = self._get_all_properties(window)

            # Material-Schichtaufbau hinzufügen
            material_info = self._get_material_layers(window)
            if material_info["layers"]:
                parsed.properties["Material_Layers"] = material_info

            yield parsed

    def _extract_doors(self) -> Iterator[ParsedDoor]:
        """Extrahiert Türen aus IFC"""
        for door in self._ifc.by_type("IfcDoor"):
            parsed = ParsedDoor(
                ifc_guid=door.GlobalId,
                name=door.Name or "",
                number=self._get_element_number(door),
            )

            # Geometrie
            parsed.width = self._get_quantity(door, "Width") or 0
            parsed.height = self._get_quantity(door, "Height") or 0

            # Scale
            parsed.width = round(parsed.width * self._unit_scale, 3)
            parsed.height = round(parsed.height * self._unit_scale, 3)

            # Eigenschaften
            parsed.door_type = str(door.ObjectType or "")
            parsed.material = self._get_property(door, "Material") or ""
            parsed.fire_rating = self._get_property(door, "FireRating") or ""

            parsed.floor_guid = self._find_element_floor(door)
            yield parsed

    def _extract_walls(self) -> Iterator[ParsedWall]:
        """Extrahiert Wände aus IFC"""
        for wall in self._ifc.by_type("IfcWall"):
            parsed = ParsedWall(
                ifc_guid=wall.GlobalId,
                name=wall.Name or "",
            )

            # Geometrie
            parsed.length = self._get_quantity(wall, "Length") or 0
            parsed.height = self._get_quantity(wall, "Height") or 0
            parsed.width = self._get_quantity(wall, "Width") or 0
            parsed.gross_area = self._get_quantity(wall, "GrossSideArea") or 0
            parsed.net_area = self._get_quantity(wall, "NetSideArea") or 0
            parsed.volume = self._get_quantity(wall, "GrossVolume") or 0

            # Scale
            parsed.length = round(parsed.length * self._unit_scale, 3)
            parsed.height = round(parsed.height * self._unit_scale, 3)
            parsed.width = round(parsed.width * self._unit_scale, 3)
            parsed.gross_area = round(parsed.gross_area * self._unit_scale**2, 3)
            parsed.net_area = round(parsed.net_area * self._unit_scale**2, 3)
            parsed.volume = round(parsed.volume * self._unit_scale**3, 3)

            # Eigenschaften (spezifische)
            parsed.is_external = self._get_property(wall, "IsExternal") == "TRUE"
            parsed.is_load_bearing = self._get_property(wall, "LoadBearing") == "TRUE"
            parsed.material = self._get_property(wall, "Material") or ""

            # ALLE Properties extrahieren
            parsed.properties = self._get_all_properties(wall)

            # Material-Schichtaufbau hinzufügen
            material_info = self._get_material_layers(wall)
            if material_info["layers"]:
                parsed.properties["Material_Layers"] = material_info

            parsed.floor_guid = self._find_element_floor(wall)
            yield parsed

    def _extract_slabs(self) -> Iterator[ParsedSlab]:
        """Extrahiert Decken/Platten aus IFC"""
        for slab in self._ifc.by_type("IfcSlab"):
            parsed = ParsedSlab(
                ifc_guid=slab.GlobalId,
                name=slab.Name or "",
                slab_type=str(slab.PredefinedType or "FLOOR"),
            )

            # Geometrie
            parsed.area = self._get_quantity(slab, "GrossArea") or 0
            parsed.thickness = self._get_quantity(slab, "Thickness") or 0
            parsed.volume = self._get_quantity(slab, "GrossVolume") or 0
            parsed.perimeter = self._get_quantity(slab, "Perimeter") or 0

            # Scale
            parsed.area = round(parsed.area * self._unit_scale**2, 3)
            parsed.thickness = round(parsed.thickness * self._unit_scale, 3)
            parsed.volume = round(parsed.volume * self._unit_scale**3, 3)
            parsed.perimeter = round(parsed.perimeter * self._unit_scale, 3)

            # Eigenschaften (spezifische)
            parsed.material = self._get_property(slab, "Material") or ""

            # ALLE Properties extrahieren
            parsed.properties = self._get_all_properties(slab)

            parsed.floor_guid = self._find_element_floor(slab)
            yield parsed

    def _get_element_number(self, element) -> str:
        """Extrahiert Element-Nummer"""
        if element.Name:
            parts = element.Name.split()
            if parts:
                return parts[0]
        return ""

    def _get_property(self, element, prop_name: str) -> Optional[str]:
        """Liest Property aus PropertySet"""
        try:
            for rel in element.IsDefinedBy:
                if rel.is_a("IfcRelDefinesByProperties"):
                    pset = rel.RelatingPropertyDefinition
                    if pset.is_a("IfcPropertySet"):
                        for prop in pset.HasProperties:
                            if prop.Name == prop_name:
                                if hasattr(prop, "NominalValue"):
                                    return str(prop.NominalValue.wrappedValue)
        except:
            pass
        return None

    def _get_all_properties(self, element) -> dict:
        """Liest ALLE Properties aus ALLEN PropertySets"""
        properties = {}

        # DEBUG: Check ob element IsDefinedBy hat
        if not hasattr(element, "IsDefinedBy"):
            logger.warning(f"Element {element} hat kein IsDefinedBy Attribut!")
            return properties

        try:
            relations = list(element.IsDefinedBy)
            logger.debug(
                f"Element {getattr(element, 'Name', 'Unknown')} hat {len(relations)} IsDefinedBy Relations"
            )

            for rel in relations:
                logger.debug(f"  Relation Type: {rel.is_a()}")

                if rel.is_a("IfcRelDefinesByProperties"):
                    pset = rel.RelatingPropertyDefinition
                    logger.debug(f"    PropertyDefinition Type: {pset.is_a()}")

                    if pset.is_a("IfcPropertySet"):
                        pset_name = pset.Name or "Unknown"
                        pset_props = {}

                        props_count = (
                            len(list(pset.HasProperties)) if hasattr(pset, "HasProperties") else 0
                        )
                        logger.debug(f"    PropertySet '{pset_name}' hat {props_count} Properties")

                        for prop in pset.HasProperties:
                            try:
                                prop_name = prop.Name or "Unknown"

                                # Single Value Property
                                if prop.is_a("IfcPropertySingleValue"):
                                    if hasattr(prop, "NominalValue") and prop.NominalValue:
                                        pset_props[prop_name] = str(prop.NominalValue.wrappedValue)
                                    else:
                                        pset_props[prop_name] = None

                                # Complex Property (z.B. Listen)
                                elif prop.is_a("IfcComplexProperty"):
                                    pset_props[prop_name] = "Complex Property"

                                # Andere Property-Typen
                                else:
                                    pset_props[prop_name] = str(prop)

                            except Exception as e:
                                logger.warning(
                                    f"Property {prop.Name} konnte nicht gelesen werden: {e}"
                                )
                                continue

                        if pset_props:
                            properties[pset_name] = pset_props
                            logger.debug(
                                f"    ✅ PropertySet '{pset_name}' gespeichert mit {len(pset_props)} Properties"
                            )

        except Exception as e:
            logger.error(f"PropertySets konnten nicht gelesen werden: {e}", exc_info=True)

        logger.debug(f"  Gesamt extrahierte PropertySets: {len(properties)}")
        return properties

    def _get_material_layers(self, element) -> dict:
        """
        Extrahiert Material-Schichtaufbau aus IFC Element.

        Returns:
            dict mit 'name' (Material-Name) und 'layers' (Liste von Schichten)
        """
        material_info = {"name": "", "layers": []}

        try:
            # Material-Assoziationen durchsuchen
            if hasattr(element, "HasAssociations"):
                for rel in element.HasAssociations:
                    if rel.is_a("IfcRelAssociatesMaterial"):
                        material = rel.RelatingMaterial

                        # Einfaches Material
                        if material.is_a("IfcMaterial"):
                            material_info["name"] = material.Name or ""

                        # Material-Schichtaufbau (z.B. bei Wänden)
                        elif material.is_a("IfcMaterialLayerSetUsage"):
                            layer_set = material.ForLayerSet
                            if layer_set and hasattr(layer_set, "MaterialLayers"):
                                for layer in layer_set.MaterialLayers:
                                    if layer.Material:
                                        layer_data = {
                                            "material": layer.Material.Name or "",
                                            "thickness": (
                                                round(
                                                    float(layer.LayerThickness) * self._unit_scale,
                                                    3,
                                                )
                                                if layer.LayerThickness
                                                else 0
                                            ),
                                            "category": getattr(layer, "Category", "") or "",
                                        }
                                        material_info["layers"].append(layer_data)

                                # Name ist der erste Layer oder LayerSet-Name
                                if material_info["layers"]:
                                    material_info["name"] = material_info["layers"][0]["material"]
                                elif hasattr(layer_set, "LayerSetName"):
                                    material_info["name"] = layer_set.LayerSetName or ""

                        # Material-Schichtaufbau direkt
                        elif material.is_a("IfcMaterialLayerSet"):
                            if hasattr(material, "MaterialLayers"):
                                for layer in material.MaterialLayers:
                                    if layer.Material:
                                        layer_data = {
                                            "material": layer.Material.Name or "",
                                            "thickness": (
                                                round(
                                                    float(layer.LayerThickness) * self._unit_scale,
                                                    3,
                                                )
                                                if layer.LayerThickness
                                                else 0
                                            ),
                                            "category": getattr(layer, "Category", "") or "",
                                        }
                                        material_info["layers"].append(layer_data)

                                if material_info["layers"]:
                                    material_info["name"] = material_info["layers"][0]["material"]

                        # Material-Liste (z.B. bei zusammengesetzten Elementen)
                        elif material.is_a("IfcMaterialList"):
                            if hasattr(material, "Materials"):
                                materials = []
                                for mat in material.Materials:
                                    if mat.Name:
                                        materials.append(mat.Name)
                                material_info["name"] = ", ".join(materials)

        except Exception as e:
            logger.debug(f"Material-Extraktion fehlgeschlagen: {e}")

        return material_info

    def _find_element_floor(self, element) -> Optional[str]:
        """Findet Geschoss für Element"""
        try:
            for rel in self._ifc.by_type("IfcRelContainedInSpatialStructure"):
                if element in rel.RelatedElements:
                    if rel.RelatingStructure.is_a("IfcBuildingStorey"):
                        return rel.RelatingStructure.GlobalId
        except:
            pass
        return None
