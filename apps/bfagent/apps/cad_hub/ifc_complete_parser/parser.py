"""
IFC Complete Parser - Parser Implementation

Extrahiert ALLE Informationen aus IFC-Dateien mit ifcopenshell.
"""

from __future__ import annotations

import hashlib
import logging
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element
import ifcopenshell.util.placement
import ifcopenshell.util.unit

from .models import (
    IfcSchemaVersion,
    ParsedBuilding,
    ParsedClassification,
    ParsedElement,
    ParsedElementType,
    ParsedMaterial,
    ParsedProject,
    ParsedProperty,
    ParsedQuantity,
    ParsedSite,
    ParsedSpace,
    ParsedStorey,
    PropertyDataType,
)

logger = logging.getLogger(__name__)


class IfcCompleteParser:
    """
    Vollständiger IFC Parser für alle Informationen.

    Extrahiert:
    - Alle PropertySets (Pset_*)
    - Alle BaseQuantities (Qto_*)
    - Materialien und Schichten
    - Klassifikationen
    - Räumliche Struktur
    - Alle Bauelemente
    - Beziehungen

    Usage:
        parser = IfcCompleteParser("/path/to/model.ifc")
        project = parser.parse()

        # Zugriff auf Daten
        for space in project.spaces:
            print(f"{space.name}: {space.net_floor_area} m²")
            print(f"  Brandschutz: {space.fire_rating}")

        # Export als JSON
        project.save_json("output.json")
    """

    # Unterstützte IFC Schemas
    SUPPORTED_SCHEMAS = {"IFC2X3", "IFC4", "IFC4X1", "IFC4X2", "IFC4X3"}

    # Zu extrahierende Element-Klassen
    ELEMENT_CLASSES = {
        # Bauteile
        "IfcWall",
        "IfcWallStandardCase",
        "IfcCurtainWall",
        "IfcDoor",
        "IfcWindow",
        "IfcSlab",
        "IfcRoof",
        "IfcColumn",
        "IfcBeam",
        "IfcStair",
        "IfcStairFlight",
        "IfcRamp",
        "IfcRampFlight",
        "IfcRailing",
        "IfcCovering",
        "IfcPlate",
        "IfcMember",
        "IfcFooting",
        "IfcPile",
        "IfcBuildingElementProxy",
        # Öffnungen
        "IfcOpeningElement",
        # Einrichtung
        "IfcFurniture",
        "IfcFurnishingElement",
        "IfcSystemFurnitureElement",
        # TGA - Allgemein
        "IfcDistributionElement",
        "IfcDistributionControlElement",
        "IfcDistributionFlowElement",
        # Rohre & Kanäle
        "IfcFlowSegment",
        "IfcPipeSegment",
        "IfcDuctSegment",
        "IfcCableCarrierSegment",
        "IfcCableSegment",
        # Verbindungen
        "IfcFlowFitting",
        "IfcPipeFitting",
        "IfcDuctFitting",
        "IfcCableCarrierFitting",
        "IfcCableFitting",
        # Endgeräte
        "IfcFlowTerminal",
        "IfcAirTerminal",
        "IfcFireSuppressionTerminal",
        "IfcSanitaryTerminal",
        "IfcLightFixture",
        "IfcOutlet",
        # Ausrüstung
        "IfcEnergyConversionDevice",
        "IfcFlowController",
        "IfcFlowMovingDevice",
        "IfcFlowStorageDevice",
        "IfcFlowTreatmentDevice",
    }

    # Type Classes
    TYPE_CLASSES = {
        "IfcWallType",
        "IfcDoorType",
        "IfcWindowType",
        "IfcSlabType",
        "IfcColumnType",
        "IfcBeamType",
        "IfcCoveringType",
        "IfcStairType",
        "IfcRampType",
        "IfcRailingType",
        "IfcRoofType",
        "IfcFurnitureType",
        "IfcSystemFurnitureElementType",
        "IfcPipeSegmentType",
        "IfcDuctSegmentType",
        "IfcAirTerminalType",
        "IfcSanitaryTerminalType",
        "IfcLightFixtureType",
    }

    # Standard PropertySet Namen für spezielle Behandlung
    COMMON_PSETS = {
        "Pset_WallCommon",
        "Pset_DoorCommon",
        "Pset_WindowCommon",
        "Pset_SlabCommon",
        "Pset_ColumnCommon",
        "Pset_BeamCommon",
        "Pset_SpaceCommon",
        "Pset_SpaceFireSafetyRequirements",
        "Pset_SpaceThermalRequirements",
        "Pset_SpaceOccupancyRequirements",
        "Pset_SpaceLightingRequirements",
    }

    def __init__(self, file_path: str | Path) -> None:
        """
        Initialisiert den Parser.

        Args:
            file_path: Pfad zur IFC-Datei
        """
        self.file_path = Path(file_path)

        if not self.file_path.exists():
            raise FileNotFoundError(f"IFC-Datei nicht gefunden: {self.file_path}")

        self.ifc: Optional[ifcopenshell.file] = None
        self._unit_scale: float = 1.0

    def parse(self) -> ParsedProject:
        """
        Parst die komplette IFC-Datei.

        Returns:
            ParsedProject mit allen extrahierten Daten
        """
        logger.info(f"Starte Parsing: {self.file_path}")

        # IFC Datei öffnen
        self.ifc = ifcopenshell.open(str(self.file_path))

        # Schema prüfen
        schema = self.ifc.schema
        if schema not in self.SUPPORTED_SCHEMAS:
            logger.warning(f"Schema {schema} möglicherweise nicht vollständig unterstützt")

        # Einheiten-Skalierung berechnen
        self._unit_scale = ifcopenshell.util.unit.calculate_unit_scale(self.ifc)

        # Projekt erstellen
        project = self._create_project()

        # Räumliche Struktur parsen
        project.sites = list(self._parse_sites())
        project.buildings = list(self._parse_buildings())
        project.storeys = list(self._parse_storeys())
        project.spaces = list(self._parse_spaces())

        # Element Types parsen
        project.element_types = list(self._parse_element_types())

        # Elemente parsen
        project.elements = list(self._parse_elements())

        # Statistiken berechnen
        project.element_counts = self._calculate_element_counts()
        project.all_materials = self._collect_all_materials(project)

        logger.info(
            f"Parsing abgeschlossen: {len(project.elements)} Elemente, {len(project.spaces)} Räume"
        )

        return project

    def _create_project(self) -> ParsedProject:
        """Erstellt das Projekt-Objekt mit Metadaten."""
        ifc_project = self.ifc.by_type("IfcProject")[0] if self.ifc.by_type("IfcProject") else None

        # File Hash berechnen
        file_hash = hashlib.md5(self.file_path.read_bytes()).hexdigest()

        # Schema Version ermitteln
        schema_map = {
            "IFC2X3": IfcSchemaVersion.IFC2X3,
            "IFC4": IfcSchemaVersion.IFC4,
            "IFC4X1": IfcSchemaVersion.IFC4X1,
            "IFC4X2": IfcSchemaVersion.IFC4X2,
            "IFC4X3": IfcSchemaVersion.IFC4X3,
        }
        schema_version = schema_map.get(self.ifc.schema, IfcSchemaVersion.IFC4)

        # Authoring Info
        owner_history = None
        authoring_app = None
        author = None
        organization = None

        if ifc_project and hasattr(ifc_project, "OwnerHistory") and ifc_project.OwnerHistory:
            owner_history = ifc_project.OwnerHistory

            if owner_history.OwningApplication:
                app = owner_history.OwningApplication
                authoring_app = (
                    app.ApplicationFullName if hasattr(app, "ApplicationFullName") else None
                )

            if owner_history.OwningUser:
                user = owner_history.OwningUser
                if hasattr(user, "ThePerson") and user.ThePerson:
                    person = user.ThePerson
                    if hasattr(person, "FamilyName"):
                        author = f"{getattr(person, 'GivenName', '')} {person.FamilyName}".strip()

                if hasattr(user, "TheOrganization") and user.TheOrganization:
                    org = user.TheOrganization
                    organization = org.Name if hasattr(org, "Name") else None

        return ParsedProject(
            name=ifc_project.Name if ifc_project else "Unbenannt",
            description=(
                ifc_project.Description
                if ifc_project and hasattr(ifc_project, "Description")
                else None
            ),
            schema_version=schema_version,
            file_path=str(self.file_path),
            file_hash=file_hash,
            file_size_bytes=self.file_path.stat().st_size,
            authoring_app=authoring_app,
            author=author,
            organization=organization,
        )

    # =========================================================================
    # Räumliche Struktur
    # =========================================================================

    def _parse_sites(self) -> Iterator[ParsedSite]:
        """Parst alle IfcSite Objekte."""
        for site in self.ifc.by_type("IfcSite"):
            parsed = ParsedSite(
                global_id=site.GlobalId,
                name=site.Name,
                description=getattr(site, "Description", None),
            )

            # Geolocation
            if hasattr(site, "RefLatitude") and site.RefLatitude:
                parsed.latitude = self._dms_to_decimal(site.RefLatitude)
            if hasattr(site, "RefLongitude") and site.RefLongitude:
                parsed.longitude = self._dms_to_decimal(site.RefLongitude)
            if hasattr(site, "RefElevation"):
                parsed.elevation = site.RefElevation

            # Adresse
            if hasattr(site, "SiteAddress") and site.SiteAddress:
                addr = site.SiteAddress
                if hasattr(addr, "AddressLines") and addr.AddressLines:
                    parsed.address_lines = list(addr.AddressLines)
                if hasattr(addr, "PostalCode"):
                    parsed.postal_code = addr.PostalCode
                if hasattr(addr, "Town"):
                    parsed.city = addr.Town
                if hasattr(addr, "Country"):
                    parsed.country = addr.Country

            # Properties
            parsed.properties = list(self._extract_properties(site))

            yield parsed

    def _parse_buildings(self) -> Iterator[ParsedBuilding]:
        """Parst alle IfcBuilding Objekte."""
        for building in self.ifc.by_type("IfcBuilding"):
            parsed = ParsedBuilding(
                global_id=building.GlobalId,
                name=building.Name,
                long_name=getattr(building, "LongName", None),
                description=getattr(building, "Description", None),
            )

            # Elevations
            if hasattr(building, "ElevationOfRefHeight"):
                parsed.elevation_of_ref_height = building.ElevationOfRefHeight
            if hasattr(building, "ElevationOfTerrain"):
                parsed.elevation_of_terrain = building.ElevationOfTerrain

            # Properties
            parsed.properties = list(self._extract_properties(building))

            # Building Type aus Properties
            for prop in parsed.properties:
                if prop.name == "OccupancyType":
                    parsed.building_type = str(prop.value)
                elif prop.name == "YearOfConstruction":
                    try:
                        parsed.construction_year = int(prop.value)
                    except (ValueError, TypeError):
                        pass

            yield parsed

    def _parse_storeys(self) -> Iterator[ParsedStorey]:
        """Parst alle IfcBuildingStorey Objekte."""
        for storey in self.ifc.by_type("IfcBuildingStorey"):
            parsed = ParsedStorey(
                global_id=storey.GlobalId,
                name=storey.Name,
                long_name=getattr(storey, "LongName", None),
                description=getattr(storey, "Description", None),
                elevation=getattr(storey, "Elevation", None),
            )

            # Building Reference
            if hasattr(storey, "Decomposes") and storey.Decomposes:
                for rel in storey.Decomposes:
                    if rel.is_a("IfcRelAggregates"):
                        parent = rel.RelatingObject
                        if parent.is_a("IfcBuilding"):
                            parsed.building_global_id = parent.GlobalId
                            break

            # Properties
            parsed.properties = list(self._extract_properties(storey))

            # Geschosshöhe aus Properties oder Quantities
            for prop in parsed.properties:
                if prop.name in ("GrossHeight", "NetHeight", "Height"):
                    try:
                        parsed.height = float(prop.value) * self._unit_scale
                    except (ValueError, TypeError):
                        pass

            yield parsed

    def _parse_spaces(self) -> Iterator[ParsedSpace]:
        """Parst alle IfcSpace Objekte (Räume)."""
        for space in self.ifc.by_type("IfcSpace"):
            parsed = ParsedSpace(
                global_id=space.GlobalId,
                name=space.Name,
                long_name=getattr(space, "LongName", None),
                description=getattr(space, "Description", None),
            )

            # Raumnummer aus Name oder Properties
            parsed.space_number = self._extract_space_number(space)

            # Geschoss-Referenz
            container = ifcopenshell.util.element.get_container(space)
            if container and container.is_a("IfcBuildingStorey"):
                parsed.storey_global_id = container.GlobalId

            # Type-Referenz
            space_type = ifcopenshell.util.element.get_type(space)
            if space_type:
                parsed.space_type_global_id = space_type.GlobalId

            # Properties extrahieren
            parsed.properties = list(self._extract_properties(space))
            parsed.quantities = list(self._extract_quantities(space))
            parsed.classifications = list(self._extract_classifications(space))

            # Quantities in Felder übertragen
            self._apply_space_quantities(parsed)

            # Spezial-Properties übertragen
            self._apply_space_properties(parsed)

            # Begrenzende Elemente
            parsed.boundary_element_ids = self._get_space_boundaries(space)

            # Türen und Fenster im Raum
            parsed.door_ids, parsed.window_ids = self._get_space_openings(space)

            yield parsed

    def _extract_space_number(self, space: Any) -> Optional[str]:
        """Extrahiert die Raumnummer."""
        # Erst direkt am Element
        if hasattr(space, "Tag") and space.Tag:
            return space.Tag

        # Dann aus Properties
        psets = ifcopenshell.util.element.get_psets(space)
        for pset_name, props in psets.items():
            if isinstance(props, dict):
                for prop_name in ["Number", "SpaceNumber", "RoomNumber", "Raumnummer"]:
                    if prop_name in props and props[prop_name]:
                        return str(props[prop_name])

        return None

    def _apply_space_quantities(self, parsed: ParsedSpace) -> None:
        """Überträgt Quantities in die Space-Felder."""
        for qty in parsed.quantities:
            name = qty.name
            value = qty.value

            if not value:
                continue

            # Flächen
            if name == "NetFloorArea":
                parsed.net_floor_area = value
            elif name == "GrossFloorArea":
                parsed.gross_floor_area = value
            elif name == "NetWallArea":
                parsed.net_wall_area = value
            elif name == "NetCeilingArea":
                parsed.net_ceiling_area = value
            # Volumen
            elif name == "NetVolume":
                parsed.net_volume = value
            elif name == "GrossVolume":
                parsed.gross_volume = value
            # Höhe
            elif name in ("FinishCeilingHeight", "NetHeight", "Height"):
                parsed.net_height = value
            elif name == "GrossHeight":
                parsed.gross_height = value
            # Umfang
            elif name in ("NetPerimeter", "Perimeter"):
                parsed.net_perimeter = value

    def _apply_space_properties(self, parsed: ParsedSpace) -> None:
        """Überträgt Standard-Properties in die Space-Felder."""
        for prop in parsed.properties:
            pset = prop.pset_name
            name = prop.name
            value = prop.value

            if value is None:
                continue

            # === Pset_SpaceCommon ===
            if name == "OccupancyType":
                parsed.occupancy_type = str(value)
            elif name == "OccupancyNumber":
                try:
                    parsed.occupancy_number = int(value)
                except (ValueError, TypeError):
                    pass

            # === Pset_SpaceFireSafetyRequirements ===
            elif name == "FireRiskFactor" or name == "FireRating":
                parsed.fire_rating = str(value)
            elif name == "FlammableStorage":
                pass  # Könnte für Ex-Zone relevant sein
            elif name == "SprinklerProtection":
                parsed.sprinkler_protected = self._parse_bool(value)
            elif name == "AirPressurization":
                pass

            # === Ex-Zone (custom oder Standard) ===
            elif name in ("ExZone", "HazardousArea", "ExplosionZone"):
                parsed.ex_zone = str(value)

            # === Brandabschnitt ===
            elif name in ("FireCompartment", "Brandabschnitt"):
                parsed.fire_compartment = str(value)

            # === Pset_SpaceThermalRequirements ===
            elif name == "SpaceTemperatureSummerMax":
                parsed.design_temperature_cooling = self._to_decimal(value)
            elif name == "SpaceTemperatureWinterMin":
                parsed.design_temperature_heating = self._to_decimal(value)
            elif name == "SpaceHumidity":
                # Oft als einzelner Wert oder Bereich
                parsed.humidity_min = self._to_decimal(value)
            elif name == "SpaceHumidityMax":
                parsed.humidity_max = self._to_decimal(value)
            elif name == "SpaceHumidityMin":
                parsed.humidity_min = self._to_decimal(value)
            elif name == "CoolingDesignHeatTransfer":
                parsed.design_cooling_load = self._to_decimal(value)
            elif name == "HeatingDesignHeatTransfer":
                parsed.design_heating_load = self._to_decimal(value)

            # === Akustik ===
            elif name in ("AcousticRating", "SoundRating"):
                parsed.acoustic_rating = str(value)
            elif name == "ReverberationTime":
                parsed.reverberation_time = self._to_decimal(value)

            # === Beleuchtung (Pset_SpaceLightingRequirements) ===
            elif name == "Illuminance":
                parsed.illuminance = self._to_decimal(value)

            # === Elektro ===
            elif name in ("ElectricalLoad", "PowerRequirement"):
                parsed.electrical_load = self._to_decimal(value)

            # === Oberflächen / Finishes ===
            elif name == "FinishFloor":
                parsed.finish_floor = str(value)
            elif name == "FinishWall" or name == "FinishWalls":
                parsed.finish_wall = str(value)
            elif name == "FinishCeiling":
                parsed.finish_ceiling = str(value)
            elif name in ("FloorSlipResistance", "FinishFloorRating"):
                parsed.finish_floor_rating = str(value)

    def _get_space_boundaries(self, space: Any) -> List[str]:
        """Ermittelt die IDs der begrenzenden Elemente."""
        boundary_ids = []

        try:
            boundaries = getattr(space, "BoundedBy", []) or []
            for boundary in boundaries:
                if hasattr(boundary, "RelatedBuildingElement"):
                    related = boundary.RelatedBuildingElement
                    if related:
                        boundary_ids.append(related.GlobalId)
        except Exception as e:
            logger.debug(f"Fehler bei Boundary-Extraktion: {e}")

        return boundary_ids

    def _get_space_openings(self, space: Any) -> Tuple[List[str], List[str]]:
        """Ermittelt Türen und Fenster im Raum."""
        door_ids = []
        window_ids = []

        try:
            boundaries = getattr(space, "BoundedBy", []) or []
            for boundary in boundaries:
                if hasattr(boundary, "RelatedBuildingElement"):
                    element = boundary.RelatedBuildingElement
                    if element:
                        # Prüfen ob das Element Öffnungen hat
                        if hasattr(element, "HasOpenings"):
                            for opening_rel in element.HasOpenings:
                                opening = opening_rel.RelatedOpeningElement
                                if hasattr(opening, "HasFillings"):
                                    for filling_rel in opening.HasFillings:
                                        filling = filling_rel.RelatedBuildingElement
                                        if filling.is_a("IfcDoor"):
                                            door_ids.append(filling.GlobalId)
                                        elif filling.is_a("IfcWindow"):
                                            window_ids.append(filling.GlobalId)
        except Exception as e:
            logger.debug(f"Fehler bei Opening-Extraktion: {e}")

        return list(set(door_ids)), list(set(window_ids))

    # =========================================================================
    # Element Types
    # =========================================================================

    def _parse_element_types(self) -> Iterator[ParsedElementType]:
        """Parst alle Element-Typen."""
        for type_class in self.TYPE_CLASSES:
            try:
                for element_type in self.ifc.by_type(type_class):
                    yield self._parse_single_type(element_type)
            except Exception as e:
                logger.debug(f"Fehler bei Type-Klasse {type_class}: {e}")

    def _parse_single_type(self, element_type: Any) -> ParsedElementType:
        """Parst einen einzelnen Element-Typ."""
        parsed = ParsedElementType(
            global_id=element_type.GlobalId,
            ifc_class=element_type.is_a(),
            name=element_type.Name,
            description=getattr(element_type, "Description", None),
            element_type=getattr(element_type, "PredefinedType", None),
        )

        # Properties & Quantities
        parsed.properties = list(self._extract_properties(element_type))
        parsed.quantities = list(self._extract_quantities(element_type))
        parsed.classifications = list(self._extract_classifications(element_type))

        # Materialien
        parsed.materials = list(self._extract_materials(element_type))

        return parsed

    # =========================================================================
    # Elements
    # =========================================================================

    def _parse_elements(self) -> Iterator[ParsedElement]:
        """Parst alle Bauelemente."""
        for element_class in self.ELEMENT_CLASSES:
            try:
                for element in self.ifc.by_type(element_class):
                    yield self._parse_single_element(element)
            except Exception as e:
                logger.warning(f"Fehler bei Element-Klasse {element_class}: {e}")

    def _parse_single_element(self, element: Any) -> ParsedElement:
        """Parst ein einzelnes Bauelement mit allen Properties."""
        parsed = ParsedElement(
            global_id=element.GlobalId,
            ifc_class=element.is_a(),
            name=element.Name,
            description=getattr(element, "Description", None),
            object_type=getattr(element, "ObjectType", None),
            tag=getattr(element, "Tag", None),
        )

        # Geschoss-Referenz
        container = ifcopenshell.util.element.get_container(element)
        if container and container.is_a("IfcBuildingStorey"):
            parsed.storey_global_id = container.GlobalId

        # Type-Referenz
        element_type = ifcopenshell.util.element.get_type(element)
        if element_type:
            parsed.type_global_id = element_type.GlobalId

        # Position
        try:
            placement = ifcopenshell.util.placement.get_local_placement(element.ObjectPlacement)
            if placement is not None:
                parsed.position_x = Decimal(str(placement[0][3] * self._unit_scale))
                parsed.position_y = Decimal(str(placement[1][3] * self._unit_scale))
                parsed.position_z = Decimal(str(placement[2][3] * self._unit_scale))
        except Exception:
            pass

        # Properties, Quantities, Classifications
        parsed.properties = list(self._extract_properties(element))
        parsed.quantities = list(self._extract_quantities(element))
        parsed.classifications = list(self._extract_classifications(element))

        # Materialien
        parsed.materials = list(self._extract_materials(element))

        # Quantities in Felder übertragen
        self._apply_element_quantities(parsed)

        # Standard-Properties übertragen
        self._apply_element_properties(parsed)

        # Beziehungen
        self._apply_element_relationships(parsed, element)

        return parsed

    def _apply_element_quantities(self, parsed: ParsedElement) -> None:
        """Überträgt Quantities in Element-Felder."""
        for qty in parsed.quantities:
            name = qty.name
            value = qty.value

            if not value:
                continue

            # Länge
            if name in ("Length", "NetLength", "GrossLength"):
                if parsed.length_m is None:
                    parsed.length_m = value
            # Breite
            elif name in ("Width", "NetWidth", "GrossWidth"):
                if parsed.width_m is None:
                    parsed.width_m = value
            # Höhe
            elif name in ("Height", "NetHeight", "GrossHeight", "OverallHeight"):
                if parsed.height_m is None:
                    parsed.height_m = value
            # Dicke
            elif name in ("Thickness", "Width"):
                if parsed.thickness_m is None:
                    parsed.thickness_m = value
            # Flächen
            elif name in ("NetSideArea", "NetArea"):
                parsed.net_area_m2 = value
            elif name in ("GrossSideArea", "GrossArea"):
                parsed.gross_area_m2 = value
            elif name in ("Area", "TotalSurfaceArea"):
                if parsed.area_m2 is None:
                    parsed.area_m2 = value
            elif name == "OpeningArea":
                parsed.opening_area_m2 = value
            # Volumen
            elif name in ("NetVolume", "GrossVolume", "Volume"):
                if parsed.volume_m3 is None:
                    parsed.volume_m3 = value

    def _apply_element_properties(self, parsed: ParsedElement) -> None:
        """Überträgt Standard-Properties in Element-Felder."""
        for prop in parsed.properties:
            name = prop.name
            value = prop.value

            if value is None:
                continue

            # === Common Properties ===
            if name == "IsExternal":
                parsed.is_external = self._parse_bool(value)
            elif name == "LoadBearing":
                parsed.is_load_bearing = self._parse_bool(value)

            # === Brandschutz ===
            elif name == "FireRating":
                parsed.fire_rating = str(value)
            elif name == "SurfaceSpreadOfFlame":
                parsed.surface_spread_of_flame = str(value)
            elif name == "Combustible":
                parsed.combustible = self._parse_bool(value)

            # === Akustik ===
            elif name == "AcousticRating":
                parsed.acoustic_rating = str(value)
            elif name == "SoundTransmissionClass":
                try:
                    parsed.sound_transmission_class = int(value)
                except (ValueError, TypeError):
                    pass

            # === Thermik ===
            elif name == "ThermalTransmittance":
                parsed.thermal_transmittance = self._to_decimal(value)

            # === Türen/Fenster spezifisch ===
            elif name == "OperationType":
                parsed.operation_type = str(value)
            elif name == "PanelOperation":
                parsed.panel_operation = str(value)
            elif name == "GlassLayers":
                try:
                    parsed.glass_layers = int(value)
                except (ValueError, TypeError):
                    pass

    def _apply_element_relationships(self, parsed: ParsedElement, element: Any) -> None:
        """Extrahiert Beziehungen des Elements."""
        # Host Element (z.B. Wand bei Tür)
        if hasattr(element, "FillsVoids") and element.FillsVoids:
            for rel in element.FillsVoids:
                opening = rel.RelatingOpeningElement
                if hasattr(opening, "VoidsElements") and opening.VoidsElements:
                    for void_rel in opening.VoidsElements:
                        host = void_rel.RelatingBuildingElement
                        if host:
                            parsed.host_element_id = host.GlobalId
                            parsed.fills_void_ids.append(opening.GlobalId)

        # Öffnungen im Element
        if hasattr(element, "HasOpenings") and element.HasOpenings:
            for rel in element.HasOpenings:
                opening = rel.RelatedOpeningElement
                if opening:
                    parsed.has_openings_ids.append(opening.GlobalId)

        # Verbundene Elemente
        if hasattr(element, "ConnectedTo") and element.ConnectedTo:
            for rel in element.ConnectedTo:
                if hasattr(rel, "RelatedElement") and rel.RelatedElement:
                    parsed.connected_element_ids.append(rel.RelatedElement.GlobalId)

        if hasattr(element, "ConnectedFrom") and element.ConnectedFrom:
            for rel in element.ConnectedFrom:
                if hasattr(rel, "RelatingElement") and rel.RelatingElement:
                    parsed.connected_element_ids.append(rel.RelatingElement.GlobalId)

    # =========================================================================
    # Property & Quantity Extraction
    # =========================================================================

    def _extract_properties(self, element: Any) -> Iterator[ParsedProperty]:
        """Extrahiert alle Properties eines Elements."""
        try:
            psets = ifcopenshell.util.element.get_psets(element, psets_only=True)

            for pset_name, properties in psets.items():
                if not isinstance(properties, dict):
                    continue

                for prop_name, prop_value in properties.items():
                    if prop_name == "id":  # Interne ID überspringen
                        continue

                    yield ParsedProperty(
                        pset_name=pset_name,
                        name=prop_name,
                        value=prop_value,
                        data_type=self._get_data_type(prop_value),
                    )

        except Exception as e:
            logger.debug(f"Fehler bei Property-Extraktion: {e}")

    def _extract_quantities(self, element: Any) -> Iterator[ParsedQuantity]:
        """Extrahiert alle Quantities eines Elements."""
        try:
            qtos = ifcopenshell.util.element.get_psets(element, qtos_only=True)

            for qto_name, quantities in qtos.items():
                if not isinstance(quantities, dict):
                    continue

                for qty_name, qty_value in quantities.items():
                    if qty_name == "id":
                        continue

                    # Quantity-Typ ermitteln
                    qty_type = self._get_quantity_type(qty_name)

                    # Wert konvertieren
                    decimal_value = None
                    if qty_value is not None:
                        try:
                            decimal_value = Decimal(str(qty_value)) * Decimal(str(self._unit_scale))

                            # Bei Flächen: m² (scale²)
                            if qty_type == "area":
                                decimal_value = Decimal(str(qty_value)) * Decimal(
                                    str(self._unit_scale**2)
                                )
                            # Bei Volumen: m³ (scale³)
                            elif qty_type == "volume":
                                decimal_value = Decimal(str(qty_value)) * Decimal(
                                    str(self._unit_scale**3)
                                )
                            # Längen: m (scale)
                            elif qty_type == "length":
                                decimal_value = Decimal(str(qty_value)) * Decimal(
                                    str(self._unit_scale)
                                )
                            else:
                                decimal_value = Decimal(str(qty_value))

                        except (ValueError, TypeError):
                            decimal_value = None

                    yield ParsedQuantity(
                        qto_name=qto_name,
                        name=qty_name,
                        value=decimal_value,
                        quantity_type=qty_type,
                        unit=self._get_unit_for_type(qty_type),
                    )

        except Exception as e:
            logger.debug(f"Fehler bei Quantity-Extraktion: {e}")

    def _extract_materials(self, element: Any) -> Iterator[ParsedMaterial]:
        """Extrahiert Materialien eines Elements."""
        try:
            material = ifcopenshell.util.element.get_material(element)

            if material is None:
                return

            # Einzelnes Material
            if material.is_a("IfcMaterial"):
                yield ParsedMaterial(
                    name=material.Name,
                    category=getattr(material, "Category", None),
                )

            # Material Layer Set (mehrschichtig)
            elif material.is_a("IfcMaterialLayerSet"):
                for i, layer in enumerate(material.MaterialLayers):
                    mat = layer.Material
                    yield ParsedMaterial(
                        name=mat.Name if mat else "Unbekannt",
                        thickness=(
                            Decimal(str(layer.LayerThickness * self._unit_scale))
                            if layer.LayerThickness
                            else None
                        ),
                        layer_order=i,
                        is_ventilated=getattr(layer, "IsVentilated", False) or False,
                        category=getattr(mat, "Category", None) if mat else None,
                    )

            # Material Layer Set Usage
            elif material.is_a("IfcMaterialLayerSetUsage"):
                layer_set = material.ForLayerSet
                if layer_set:
                    for i, layer in enumerate(layer_set.MaterialLayers):
                        mat = layer.Material
                        yield ParsedMaterial(
                            name=mat.Name if mat else "Unbekannt",
                            thickness=(
                                Decimal(str(layer.LayerThickness * self._unit_scale))
                                if layer.LayerThickness
                                else None
                            ),
                            layer_order=i,
                            is_ventilated=getattr(layer, "IsVentilated", False) or False,
                            category=getattr(mat, "Category", None) if mat else None,
                        )

            # Material Constituent Set
            elif material.is_a("IfcMaterialConstituentSet"):
                for i, constituent in enumerate(material.MaterialConstituents or []):
                    mat = constituent.Material
                    yield ParsedMaterial(
                        name=mat.Name if mat else constituent.Name or "Unbekannt",
                        layer_order=i,
                        category=constituent.Category,
                    )

            # Material Profile Set
            elif material.is_a("IfcMaterialProfileSet"):
                for i, profile in enumerate(material.MaterialProfiles or []):
                    mat = profile.Material
                    yield ParsedMaterial(
                        name=mat.Name if mat else "Unbekannt",
                        layer_order=i,
                        category=getattr(mat, "Category", None) if mat else None,
                    )

        except Exception as e:
            logger.debug(f"Fehler bei Material-Extraktion: {e}")

    def _extract_classifications(self, element: Any) -> Iterator[ParsedClassification]:
        """Extrahiert Klassifikations-Referenzen."""
        try:
            # Über HasAssociations
            if hasattr(element, "HasAssociations"):
                for assoc in element.HasAssociations:
                    if assoc.is_a("IfcRelAssociatesClassification"):
                        ref = assoc.RelatingClassification

                        if ref.is_a("IfcClassificationReference"):
                            system_name = ""
                            if hasattr(ref, "ReferencedSource") and ref.ReferencedSource:
                                source = ref.ReferencedSource
                                if hasattr(source, "Name"):
                                    system_name = source.Name

                            yield ParsedClassification(
                                system=system_name,
                                code=(
                                    ref.Identification
                                    if hasattr(ref, "Identification")
                                    else ref.ItemReference if hasattr(ref, "ItemReference") else ""
                                ),
                                name=ref.Name,
                                location=getattr(ref, "Location", None),
                            )
        except Exception as e:
            logger.debug(f"Fehler bei Classification-Extraktion: {e}")

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _get_data_type(self, value: Any) -> PropertyDataType:
        """Ermittelt den Datentyp eines Property-Werts."""
        if value is None:
            return PropertyDataType.UNKNOWN
        elif isinstance(value, bool):
            return PropertyDataType.BOOLEAN
        elif isinstance(value, int):
            return PropertyDataType.INTEGER
        elif isinstance(value, float):
            return PropertyDataType.REAL
        elif isinstance(value, str):
            return PropertyDataType.STRING
        elif isinstance(value, (list, tuple)):
            return PropertyDataType.LIST
        elif isinstance(value, dict):
            return PropertyDataType.COMPLEX
        else:
            return PropertyDataType.UNKNOWN

    def _get_quantity_type(self, qty_name: str) -> str:
        """Ermittelt den Quantity-Typ aus dem Namen."""
        name_lower = qty_name.lower()

        if any(x in name_lower for x in ["area", "fläche"]):
            return "area"
        elif any(x in name_lower for x in ["volume", "volumen"]):
            return "volume"
        elif any(x in name_lower for x in ["length", "länge", "perimeter", "umfang"]):
            return "length"
        elif any(
            x in name_lower for x in ["height", "höhe", "width", "breite", "thickness", "dicke"]
        ):
            return "length"
        elif any(x in name_lower for x in ["count", "anzahl", "number"]):
            return "count"
        elif any(x in name_lower for x in ["weight", "gewicht", "mass"]):
            return "weight"
        else:
            return "unknown"

    def _get_unit_for_type(self, qty_type: str) -> Optional[str]:
        """Gibt die Standard-Einheit für einen Quantity-Typ zurück."""
        units = {
            "area": "m²",
            "volume": "m³",
            "length": "m",
            "count": "Stk",
            "weight": "kg",
        }
        return units.get(qty_type)

    def _parse_bool(self, value: Any) -> bool:
        """Konvertiert verschiedene Formate zu Boolean."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "yes", "ja", "1", ".t.")
        if isinstance(value, (int, float)):
            return bool(value)
        return False

    def _to_decimal(self, value: Any) -> Optional[Decimal]:
        """Konvertiert zu Decimal."""
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except (ValueError, TypeError):
            return None

    def _dms_to_decimal(self, dms: tuple) -> Optional[float]:
        """Konvertiert Grad/Minuten/Sekunden zu Dezimalgrad."""
        try:
            if len(dms) >= 3:
                return dms[0] + dms[1] / 60 + dms[2] / 3600
            elif len(dms) >= 2:
                return dms[0] + dms[1] / 60
            elif len(dms) >= 1:
                return dms[0]
        except (TypeError, IndexError):
            pass
        return None

    def _calculate_element_counts(self) -> Dict[str, int]:
        """Berechnet Element-Anzahl pro Klasse."""
        counts = {}
        for element_class in self.ELEMENT_CLASSES:
            try:
                count = len(self.ifc.by_type(element_class))
                if count > 0:
                    counts[element_class] = count
            except Exception:
                pass
        return counts

    def _collect_all_materials(self, project: ParsedProject) -> Set[str]:
        """Sammelt alle verwendeten Materialnamen."""
        materials = set()

        for element in project.elements:
            for mat in element.materials:
                materials.add(mat.name)

        for elem_type in project.element_types:
            for mat in elem_type.materials:
                materials.add(mat.name)

        return materials
