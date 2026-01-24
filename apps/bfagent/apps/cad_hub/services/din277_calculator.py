# apps/cad_hub/services/din277_calculator.py
"""
DIN 277:2021 Flächenberechnung

Basiert auf BauCAD Hub MCP standards/din277.py
"""
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import Dict, List, Optional


class AreaCategory(str, Enum):
    """Flächenkategorien nach DIN 277:2021"""

    BGF = "BGF"  # Brutto-Grundfläche
    KGF = "KGF"  # Konstruktions-Grundfläche
    NRF = "NRF"  # Netto-Raumfläche
    NF = "NF"  # Nutzfläche
    NF1 = "NF1"  # Wohnen und Aufenthalt
    NF2 = "NF2"  # Büroarbeit
    NF3 = "NF3"  # Produktion
    NF4 = "NF4"  # Lagern, Verkaufen
    NF5 = "NF5"  # Bildung, Kultur
    NF6 = "NF6"  # Heilen und Pflegen
    NF7 = "NF7"  # Sonstige Nutzflächen
    TF = "TF"  # Technische Funktionsfläche
    VF = "VF"  # Verkehrsfläche


# Mapping von Django UsageCategory zu AreaCategory
USAGE_TO_AREA = {
    "NF1.1": AreaCategory.NF1,
    "NF1.2": AreaCategory.NF1,
    "NF1.3": AreaCategory.NF1,
    "NF2": AreaCategory.NF2,
    "NF3": AreaCategory.NF3,
    "NF4": AreaCategory.NF4,
    "NF5": AreaCategory.NF5,
    "NF6": AreaCategory.NF6,
    "TF7": AreaCategory.TF,
    "VF8": AreaCategory.VF,
}


@dataclass
class DIN277Result:
    """Ergebnis einer DIN 277 Berechnung"""

    # Hauptflächen
    bgf: Decimal = Decimal("0")
    kgf: Decimal = Decimal("0")
    nrf: Decimal = Decimal("0")

    # Nutzflächen
    nf: Decimal = Decimal("0")
    nf1: Decimal = Decimal("0")
    nf2: Decimal = Decimal("0")
    nf3: Decimal = Decimal("0")
    nf4: Decimal = Decimal("0")
    nf5: Decimal = Decimal("0")
    nf6: Decimal = Decimal("0")
    nf7: Decimal = Decimal("0")

    # Funktionsflächen
    tf: Decimal = Decimal("0")
    vf: Decimal = Decimal("0")

    # Rauminhalt
    bri: Decimal = Decimal("0")

    # Metadaten
    room_count: int = 0
    warnings: List[str] = field(default_factory=list)

    def __post_init__(self):
        self._recalculate()

    def _recalculate(self):
        """Berechnet NF und NRF aus Teilflächen"""
        self.nf = sum(
            [self.nf1, self.nf2, self.nf3, self.nf4, self.nf5, self.nf6, self.nf7], Decimal("0")
        )
        self.nrf = self.nf + self.tf + self.vf

    @property
    def nrf_ratio(self) -> float:
        """NRF/BGF Verhältnis (Flächeneffizienz)"""
        if self.bgf == 0:
            return 0.0
        return float(self.nrf / self.bgf)

    @property
    def vf_ratio(self) -> float:
        """VF/NRF Verhältnis (Verkehrsflächenanteil)"""
        if self.nrf == 0:
            return 0.0
        return float(self.vf / self.nrf)

    def to_dict(self) -> Dict:
        """Für JSON/Template-Nutzung"""
        return {
            "bgf": float(self.bgf),
            "kgf": float(self.kgf),
            "nrf": float(self.nrf),
            "nf": float(self.nf),
            "nf1": float(self.nf1),
            "nf2": float(self.nf2),
            "nf3": float(self.nf3),
            "nf4": float(self.nf4),
            "nf5": float(self.nf5),
            "nf6": float(self.nf6),
            "nf7": float(self.nf7),
            "tf": float(self.tf),
            "vf": float(self.vf),
            "bri": float(self.bri),
            "nrf_ratio": round(self.nrf_ratio, 3),
            "vf_ratio": round(self.vf_ratio, 3),
            "room_count": self.room_count,
        }


class DIN277Calculator:
    """
    Berechnet Flächen nach DIN 277:2021

    Nutzt BauCAD Hub MCP Patterns für korrekte Klassifizierung.
    """

    # Raum-Klassifizierung nach Namen
    ROOM_PATTERNS = {
        AreaCategory.NF1: ["wohn", "schlaf", "kind", "gäste", "essen", "aufenthalt"],
        AreaCategory.NF2: ["büro", "office", "besprechung", "meeting", "konferenz"],
        AreaCategory.NF3: ["küche", "kochen", "produktion", "werkstatt"],
        AreaCategory.NF4: ["lager", "abstell", "keller", "archiv", "verkauf"],
        AreaCategory.NF5: ["schule", "unterricht", "bibliothek", "museum"],
        AreaCategory.NF6: ["arzt", "praxis", "pflege", "behandlung"],
        AreaCategory.NF7: ["bad", "wc", "dusche", "sanitär", "garderobe"],
        AreaCategory.TF: ["technik", "heizung", "server", "elektro", "haustechnik"],
        AreaCategory.VF: ["flur", "gang", "treppe", "aufzug", "eingang", "foyer", "diele"],
    }

    def classify_room(self, name: str, usage_category: str = "") -> AreaCategory:
        """
        Klassifiziert einen Raum nach DIN 277

        1. Prüft usage_category (aus Model)
        2. Falls leer: Name-basierte Klassifizierung
        """
        # Methode 1: Direkte Kategorie
        if usage_category:
            if usage_category in USAGE_TO_AREA:
                return USAGE_TO_AREA[usage_category]

        # Methode 2: Name-basiert
        name_lower = name.lower()
        for category, patterns in self.ROOM_PATTERNS.items():
            if any(p in name_lower for p in patterns):
                return category

        # Fallback: Sonstige Nutzfläche
        return AreaCategory.NF7

    def calculate_from_rooms(
        self,
        rooms: List[Dict],
        bgf: Optional[float] = None,
        floor_height: float = 3.0,
    ) -> DIN277Result:
        """
        Berechnet DIN 277 aus Raumliste

        Args:
            rooms: Liste von Dicts mit 'name', 'area', 'usage_category'
            bgf: Brutto-Grundfläche (optional, sonst geschätzt)
            floor_height: Geschosshöhe für BRI
        """
        result = DIN277Result()
        result.room_count = len(rooms)

        for room in rooms:
            name = room.get("name", "")
            area = Decimal(str(room.get("area", 0)))
            usage = room.get("usage_category", "")

            category = self.classify_room(name, usage)

            if category == AreaCategory.NF1:
                result.nf1 += area
            elif category == AreaCategory.NF2:
                result.nf2 += area
            elif category == AreaCategory.NF3:
                result.nf3 += area
            elif category == AreaCategory.NF4:
                result.nf4 += area
            elif category == AreaCategory.NF5:
                result.nf5 += area
            elif category == AreaCategory.NF6:
                result.nf6 += area
            elif category == AreaCategory.NF7:
                result.nf7 += area
            elif category == AreaCategory.TF:
                result.tf += area
            elif category == AreaCategory.VF:
                result.vf += area

        # NF und NRF berechnen
        result._recalculate()

        # BGF
        if bgf is not None:
            result.bgf = Decimal(str(bgf))
        else:
            # Schätzung: NRF ≈ 82% von BGF
            result.bgf = result.nrf / Decimal("0.82")
            result.warnings.append("BGF geschätzt (NRF/0.82)")

        # KGF = BGF - NRF
        result.kgf = result.bgf - result.nrf

        # BRI
        result.bri = result.bgf * Decimal(str(floor_height))

        return result

    def calculate_from_queryset(self, rooms_qs, bgf: float = None) -> DIN277Result:
        """
        Berechnet DIN 277 direkt aus Django QuerySet

        Args:
            rooms_qs: Room.objects.filter(...)
            bgf: Optional BGF
        """
        rooms = list(rooms_qs.values("name", "area", "usage_category"))
        return self.calculate_from_rooms(rooms, bgf=bgf)
