# apps/cad_hub/services/woflv_calculator.py
"""
WoFlV Wohnflächenberechnung

Basiert auf BauCAD Hub MCP standards/woflv.py
Wohnflächenverordnung für Mietwohnungen
"""
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Dict, List, Tuple


@dataclass
class WoFlVRoom:
    """Einzelner Raum mit WoFlV-Berechnung"""

    name: str
    number: str = ""
    floor_name: str = ""

    # Flächen
    grundflaeche: Decimal = Decimal("0")
    hoehe: Decimal = Decimal("2.50")

    # Faktoren
    hoehen_faktor: Decimal = Decimal("1.0")
    raumtyp: str = "wohnraum"
    raumtyp_faktor: Decimal = Decimal("1.0")

    @property
    def gesamt_faktor(self) -> Decimal:
        """Kombinierter Faktor (Höhe × Raumtyp)"""
        return self.hoehen_faktor * self.raumtyp_faktor

    @property
    def wohnflaeche(self) -> Decimal:
        """Anrechenbare Wohnfläche"""
        return self.grundflaeche * self.gesamt_faktor

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "number": self.number,
            "floor_name": self.floor_name,
            "grundflaeche": float(self.grundflaeche),
            "hoehe": float(self.hoehe),
            "hoehen_faktor": float(self.hoehen_faktor),
            "raumtyp": self.raumtyp,
            "raumtyp_faktor": float(self.raumtyp_faktor),
            "gesamt_faktor": float(self.gesamt_faktor),
            "wohnflaeche": float(self.wohnflaeche),
        }


@dataclass
class WoFlVResult:
    """Ergebnis der WoFlV-Berechnung"""

    # Summen
    grundflaeche_gesamt: Decimal = Decimal("0")
    wohnflaeche_gesamt: Decimal = Decimal("0")

    # Nach Anrechnung
    wohnflaeche_100: Decimal = Decimal("0")  # 100% angerechnet
    wohnflaeche_50: Decimal = Decimal("0")  # 50% angerechnet
    wohnflaeche_25: Decimal = Decimal("0")  # 25% angerechnet
    nicht_angerechnet: Decimal = Decimal("0")

    # Räume
    rooms: List[WoFlVRoom] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def _round(self, value: Decimal, decimals: int = 2) -> Decimal:
        return value.quantize(Decimal(10) ** -decimals, rounding=ROUND_HALF_UP)

    @property
    def anrechnungsquote(self) -> float:
        """Verhältnis Wohnfläche/Grundfläche"""
        if self.grundflaeche_gesamt == 0:
            return 0.0
        return float(self.wohnflaeche_gesamt / self.grundflaeche_gesamt)

    def to_dict(self) -> Dict:
        return {
            "grundflaeche_gesamt": float(self._round(self.grundflaeche_gesamt)),
            "wohnflaeche_gesamt": float(self._round(self.wohnflaeche_gesamt)),
            "wohnflaeche_100": float(self._round(self.wohnflaeche_100)),
            "wohnflaeche_50": float(self._round(self.wohnflaeche_50)),
            "wohnflaeche_25": float(self._round(self.wohnflaeche_25)),
            "nicht_angerechnet": float(self._round(self.nicht_angerechnet)),
            "anrechnungsquote": round(self.anrechnungsquote, 3),
            "room_count": len(self.rooms),
            "warnings": self.warnings,
        }

    def to_table(self) -> str:
        """Formatierte Tabelle"""
        lines = [
            "WoFlV Wohnflächenberechnung",
            "=" * 45,
            f"Grundfläche gesamt:         {self._round(self.grundflaeche_gesamt):>10.2f} m²",
            "-" * 45,
            f"Wohnfläche 100%:            {self._round(self.wohnflaeche_100):>10.2f} m²",
            f"Wohnfläche  50%:            {self._round(self.wohnflaeche_50):>10.2f} m²",
            f"Wohnfläche  25%:            {self._round(self.wohnflaeche_25):>10.2f} m²",
            f"Nicht angerechnet:          {self._round(self.nicht_angerechnet):>10.2f} m²",
            "-" * 45,
            f"WOHNFLÄCHE GESAMT:          {self._round(self.wohnflaeche_gesamt):>10.2f} m²",
            "=" * 45,
            f"Anrechnungsquote:           {self.anrechnungsquote:>10.1%}",
        ]
        return "\n".join(lines)


class WoFlVCalculator:
    """
    Berechnet Wohnfläche nach Wohnflächenverordnung (WoFlV)

    Regeln:
    - Höhe >= 2,00m: 100% Anrechnung
    - Höhe 1,00-2,00m: 50% Anrechnung
    - Höhe < 1,00m: keine Anrechnung
    - Balkone/Terrassen: 25% (max 50%)
    - Keller/Garagen: 0%
    """

    # Raumtyp-Faktoren nach WoFlV
    RAUMTYP_FAKTOREN = {
        "wohnraum": {
            "faktor": Decimal("1.0"),
            "keywords": ["wohn", "schlaf", "kind", "küche", "bad", "dusch", "ess", "arbeits"],
        },
        "wintergarten_beheizt": {"faktor": Decimal("1.0"), "keywords": ["wintergarten beheizt"]},
        "wintergarten_unbeheizt": {"faktor": Decimal("0.5"), "keywords": ["wintergarten"]},
        "schwimmbad": {"faktor": Decimal("0.5"), "keywords": ["schwimm", "pool", "sauna"]},
        "balkon": {"faktor": Decimal("0.25"), "keywords": ["balkon", "loggia", "dachgarten"]},
        "terrasse": {"faktor": Decimal("0.25"), "keywords": ["terrasse", "freisitz"]},
        "keller": {
            "faktor": Decimal("0.0"),
            "keywords": ["keller", "wasch", "trocken", "heizung", "technik"],
        },
        "garage": {"faktor": Decimal("0.0"), "keywords": ["garage", "carport", "stellplatz"]},
        "flur": {"faktor": Decimal("1.0"), "keywords": ["flur", "diele", "gang"]},
    }

    def get_hoehen_faktor(self, hoehe: float) -> Decimal:
        """Ermittelt Anrechnungsfaktor nach Raumhöhe"""
        if hoehe >= 2.0:
            return Decimal("1.0")
        elif hoehe >= 1.0:
            return Decimal("0.5")
        else:
            return Decimal("0.0")

    def get_raumtyp_faktor(self, name: str, category: str = "") -> Tuple[str, Decimal]:
        """Ermittelt Raumtyp und Faktor aus Name"""
        search_text = f"{name} {category}".lower()

        # Prüfreihenfolge (spezifisch → allgemein)
        type_order = [
            "wintergarten_beheizt",
            "wintergarten_unbeheizt",
            "schwimmbad",
            "balkon",
            "terrasse",
            "keller",
            "garage",
            "flur",
            "wohnraum",
        ]

        for raumtyp in type_order:
            config = self.RAUMTYP_FAKTOREN.get(raumtyp, {})
            keywords = config.get("keywords", [])

            if any(kw in search_text for kw in keywords):
                return raumtyp, config.get("faktor", Decimal("1.0"))

        # Default: Wohnraum
        return "wohnraum", Decimal("1.0")

    def calculate_room(
        self,
        name: str,
        area: float,
        hoehe: float = 2.50,
        category: str = "",
        number: str = "",
        floor_name: str = "",
    ) -> WoFlVRoom:
        """Berechnet Wohnfläche für einen Raum"""
        hoehen_faktor = self.get_hoehen_faktor(hoehe)
        raumtyp, raumtyp_faktor = self.get_raumtyp_faktor(name, category)

        return WoFlVRoom(
            name=name,
            number=number,
            grundflaeche=Decimal(str(area)),
            hoehe=Decimal(str(hoehe)),
            hoehen_faktor=hoehen_faktor,
            raumtyp=raumtyp,
            raumtyp_faktor=raumtyp_faktor,
            floor_name=floor_name,
        )

    def calculate_from_rooms(
        self,
        rooms: List[Dict],
        default_hoehe: float = 2.50,
    ) -> WoFlVResult:
        """
        Berechnet WoFlV aus Raumliste

        Args:
            rooms: Liste von Dicts mit 'name', 'area', optional 'hoehe'
            default_hoehe: Standard-Raumhöhe wenn nicht angegeben
        """
        result = WoFlVResult()

        for room_data in rooms:
            name = room_data.get("name", "Raum")
            area = room_data.get("area", 0)
            hoehe = room_data.get("hoehe", room_data.get("height", default_hoehe))
            number = room_data.get("number", "")
            floor_name = room_data.get("floor_name", "")

            woflv_room = self.calculate_room(
                name=name,
                area=area,
                hoehe=hoehe,
                number=number,
                floor_name=floor_name,
            )

            result.rooms.append(woflv_room)
            result.grundflaeche_gesamt += woflv_room.grundflaeche
            result.wohnflaeche_gesamt += woflv_room.wohnflaeche

            # Nach Anrechnungsfaktor gruppieren
            faktor = woflv_room.gesamt_faktor
            if faktor == Decimal("1.0"):
                result.wohnflaeche_100 += woflv_room.wohnflaeche
            elif faktor == Decimal("0.5"):
                result.wohnflaeche_50 += woflv_room.wohnflaeche
            elif faktor == Decimal("0.25"):
                result.wohnflaeche_25 += woflv_room.wohnflaeche
            else:
                result.nicht_angerechnet += woflv_room.grundflaeche

        return result

    def calculate_from_queryset(self, rooms_qs, default_hoehe: float = 2.50) -> WoFlVResult:
        """Berechnet WoFlV direkt aus Django QuerySet"""
        rooms = list(rooms_qs.values("name", "number", "area", "height"))
        return self.calculate_from_rooms(rooms, default_hoehe=default_hoehe)
