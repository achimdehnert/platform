"""Fire Safety Analysis Service.

Extracts fire ratings from IFC elements and checks compliance
with DIN 4102 / EN 13501 requirements.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any

import ifcopenshell


class FireRatingStandard(str, Enum):
    """Fire rating classification standards."""

    DIN4102 = "din4102"
    EN13501 = "en13501"


class ComplianceStatus(str, Enum):
    """Element compliance status."""

    PENDING = "pending"
    COMPLIANT = "compliant"
    WARNING = "warning"
    VIOLATION = "violation"


@dataclass
class FireRatedElement:
    """Element with fire protection requirements."""

    element_type: str
    ifc_guid: str
    name: str
    required_rating: str | None = None
    required_standard: str = FireRatingStandard.DIN4102
    actual_rating: str | None = None
    actual_standard: str | None = None
    is_compliant: bool | None = None
    compliance_note: str = ""


@dataclass
class FireCompartment:
    """Fire compartment (Brandabschnitt)."""

    name: str
    area_m2: Decimal = Decimal("0")
    max_area_m2: Decimal = Decimal("1600")
    has_sprinkler: bool = False
    fire_load_mj_m2: Decimal | None = None
    status: ComplianceStatus = ComplianceStatus.PENDING
    room_ids: list[int] = field(default_factory=list)


@dataclass
class FireSafetyResult:
    """Result of fire safety analysis."""

    model_id: int
    is_compliant: bool
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    compartments: list[FireCompartment] = field(default_factory=list)
    rated_elements: list[FireRatedElement] = field(default_factory=list)
    statistics: dict[str, Any] = field(default_factory=dict)


# PropertySet mappings for fire ratings
FIRE_RATING_PSETS = {
    "IfcWall": [
        ("Pset_WallCommon", "FireRating"),
        ("Pset_WallCommon", "Compartmentation"),
        ("CPset_FireRating", "FireResistanceRating"),
    ],
    "IfcDoor": [
        ("Pset_DoorCommon", "FireRating"),
        ("Pset_DoorCommon", "SelfClosing"),
        ("CPset_FireRating", "FireResistanceRating"),
    ],
    "IfcSlab": [
        ("Pset_SlabCommon", "FireRating"),
        ("CPset_FireRating", "FireResistanceRating"),
    ],
    "IfcCurtainWall": [
        ("Pset_CurtainWallCommon", "FireRating"),
    ],
}

# Fire rating normalization
RATING_NORMALIZATION = {
    "F30": "F30",
    "F30-B": "F30",
    "F 30": "F30",
    "REI30": "REI30",
    "REI 30": "REI30",
    "30": "F30",
    "F60": "F60",
    "F60-B": "F60",
    "F 60": "F60",
    "REI60": "REI60",
    "REI 60": "REI60",
    "60": "F60",
    "F90": "F90",
    "F90-A": "F90",
    "F90-AB": "F90",
    "F 90": "F90",
    "REI90": "REI90",
    "REI 90": "REI90",
    "90": "F90",
    "F120": "F120",
    "F 120": "F120",
    "REI120": "REI120",
    "120": "F120",
    "T30": "T30",
    "T30-1": "T30",
    "T30-2": "T30",
    "EI30": "EI30",
    "EI230": "EI30",
    "T60": "T60",
    "EI60": "EI60",
    "T90": "T90",
    "EI90": "EI90",
}


def rating_to_minutes(rating: str | None) -> int:
    """Extract minutes from fire rating code."""
    if not rating:
        return 0
    import re

    match = re.search(r"(\d+)", rating)
    return int(match.group(1)) if match else 0


class FireSafetyService:
    """Service for fire safety analysis of IFC models."""

    def __init__(self, building_type: str = "standard", has_sprinkler: bool = False):
        """Initialize service with building parameters.

        Args:
            building_type: Type of building (standard, industrial, high_rise, etc.)
            has_sprinkler: Whether building has sprinkler system
        """
        self.building_type = building_type
        self.has_sprinkler = has_sprinkler
        self._set_parameters()

    def _set_parameters(self) -> None:
        """Set analysis parameters based on building type."""
        params = {
            "standard": {"max_compartment_area": 1600, "max_escape_distance": 35},
            "industrial": {"max_compartment_area": 10000, "max_escape_distance": 50},
            "high_rise": {"max_compartment_area": 400, "max_escape_distance": 25},
            "assembly": {"max_compartment_area": 1000, "max_escape_distance": 30},
            "healthcare": {"max_compartment_area": 500, "max_escape_distance": 30},
        }
        p = params.get(self.building_type, params["standard"])
        self.max_compartment_area = p["max_compartment_area"]
        self.max_escape_distance = p["max_escape_distance"]

        if self.has_sprinkler:
            self.max_compartment_area *= 2
            self.max_escape_distance *= 2

    def analyze(self, ifc_model: ifcopenshell.file, model_id: int) -> FireSafetyResult:
        """Perform complete fire safety analysis.

        Args:
            ifc_model: Opened IFC model
            model_id: Database ID of the model

        Returns:
            FireSafetyResult with all findings
        """
        result = FireSafetyResult(model_id=model_id, is_compliant=True)

        rated_elements = self._extract_fire_rated_elements(ifc_model)
        result.rated_elements = rated_elements

        result.statistics = self._calculate_statistics(rated_elements)

        violations = []
        warnings = []
        for elem in rated_elements:
            if elem.is_compliant is False:
                violations.append(
                    f"{elem.element_type} '{elem.name}' ({elem.ifc_guid}): "
                    f"Erforderlich {elem.required_rating}, Ist {elem.actual_rating or 'nicht angegeben'}"
                )
            elif elem.actual_rating is None and elem.required_rating:
                warnings.append(
                    f"{elem.element_type} '{elem.name}': Brandschutzklasse nicht definiert"
                )

        result.violations = violations
        result.warnings = warnings
        result.is_compliant = len(violations) == 0

        return result

    def _extract_fire_rated_elements(self, ifc_model: ifcopenshell.file) -> list[FireRatedElement]:
        """Extract all elements with fire rating properties."""
        elements = []

        for ifc_type, pset_mappings in FIRE_RATING_PSETS.items():
            try:
                ifc_elements = ifc_model.by_type(ifc_type)
            except RuntimeError:
                continue

            for elem in ifc_elements:
                rating = self._get_fire_rating(elem, pset_mappings)
                name = getattr(elem, "Name", None) or f"{ifc_type}_{elem.id()}"

                fire_elem = FireRatedElement(
                    element_type=ifc_type.replace("Ifc", "").lower(),
                    ifc_guid=elem.GlobalId,
                    name=name,
                    actual_rating=rating,
                    actual_standard=self._detect_standard(rating),
                )

                fire_elem.is_compliant = self._check_element_compliance(fire_elem)
                elements.append(fire_elem)

        return elements

    def _get_fire_rating(self, element: Any, pset_mappings: list[tuple[str, str]]) -> str | None:
        """Get fire rating from element's property sets."""
        for pset_name, prop_name in pset_mappings:
            try:
                psets = ifcopenshell.util.element.get_psets(element)
                if pset_name in psets and prop_name in psets[pset_name]:
                    raw_value = psets[pset_name][prop_name]
                    if raw_value:
                        return self._normalize_rating(str(raw_value))
            except (AttributeError, KeyError, TypeError):
                continue
        return None

    def _normalize_rating(self, rating: str) -> str:
        """Normalize fire rating to standard format."""
        rating_upper = rating.upper().strip()
        return RATING_NORMALIZATION.get(rating_upper, rating_upper)

    def _detect_standard(self, rating: str | None) -> str | None:
        """Detect which standard a rating belongs to."""
        if not rating:
            return None
        if rating.startswith(("REI", "EI", "E ", "R ")):
            return FireRatingStandard.EN13501
        if rating.startswith(("F", "T", "W", "G")):
            return FireRatingStandard.DIN4102
        return None

    def _check_element_compliance(self, element: FireRatedElement) -> bool | None:
        """Check if element meets fire rating requirements."""
        if not element.required_rating:
            return None

        if not element.actual_rating:
            return False

        required_minutes = rating_to_minutes(element.required_rating)
        actual_minutes = rating_to_minutes(element.actual_rating)

        return actual_minutes >= required_minutes

    def _calculate_statistics(self, elements: list[FireRatedElement]) -> dict[str, Any]:
        """Calculate statistics from analyzed elements."""
        stats = {
            "total_elements": len(elements),
            "by_type": {},
            "by_rating": {},
            "compliant": 0,
            "non_compliant": 0,
            "undefined": 0,
        }

        for elem in elements:
            elem_type = elem.element_type
            stats["by_type"][elem_type] = stats["by_type"].get(elem_type, 0) + 1

            if elem.actual_rating:
                rating = elem.actual_rating
                stats["by_rating"][rating] = stats["by_rating"].get(rating, 0) + 1

            if elem.is_compliant is True:
                stats["compliant"] += 1
            elif elem.is_compliant is False:
                stats["non_compliant"] += 1
            else:
                stats["undefined"] += 1

        return stats

    def extract_fire_doors(self, ifc_model: ifcopenshell.file) -> list[FireRatedElement]:
        """Extract only fire-rated doors."""
        doors = []
        try:
            ifc_doors = ifc_model.by_type("IfcDoor")
        except RuntimeError:
            return doors

        pset_mappings = FIRE_RATING_PSETS["IfcDoor"]

        for door in ifc_doors:
            rating = self._get_fire_rating(door, pset_mappings)
            if rating:  # Only include doors with fire rating
                name = getattr(door, "Name", None) or f"Door_{door.id()}"
                doors.append(
                    FireRatedElement(
                        element_type="door",
                        ifc_guid=door.GlobalId,
                        name=name,
                        actual_rating=rating,
                        actual_standard=self._detect_standard(rating),
                    )
                )

        return doors

    def extract_fire_walls(self, ifc_model: ifcopenshell.file) -> list[FireRatedElement]:
        """Extract only fire-rated walls."""
        walls = []
        try:
            ifc_walls = ifc_model.by_type("IfcWall")
        except RuntimeError:
            return walls

        pset_mappings = FIRE_RATING_PSETS["IfcWall"]

        for wall in ifc_walls:
            rating = self._get_fire_rating(wall, pset_mappings)
            if rating:  # Only include walls with fire rating
                name = getattr(wall, "Name", None) or f"Wall_{wall.id()}"

                is_compartment = False
                try:
                    psets = ifcopenshell.util.element.get_psets(wall)
                    if "Pset_WallCommon" in psets:
                        is_compartment = psets["Pset_WallCommon"].get("Compartmentation", False)
                except (AttributeError, KeyError):
                    pass

                elem = FireRatedElement(
                    element_type="wall",
                    ifc_guid=wall.GlobalId,
                    name=name,
                    actual_rating=rating,
                    actual_standard=self._detect_standard(rating),
                )
                elem.compliance_note = "Brandabschnittsbildend" if is_compartment else ""
                walls.append(elem)

        return walls
