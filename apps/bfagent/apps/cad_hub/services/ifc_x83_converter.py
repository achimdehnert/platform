# apps/cad_hub/services/ifc_x83_converter.py
"""
IFC → GAEB X83 Konverter
========================

Konvertiert IFC-Modelldaten in GAEB X83 Leistungsverzeichnis (Angebot).
Extrahiert Mengen aus IFC-Elementen und erstellt LV-Positionen.

GAEB X83 = Angebotsformat mit Mengen und Preisen
"""

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from io import BytesIO
from typing import Any, Dict, List, Optional

from .gaeb_generator import (
    GAEBGenerator,
    GAEBPhase,
    Leistungsverzeichnis,
    LosGruppe,
    MengenEinheit,
    Position,
)

logger = logging.getLogger(__name__)


@dataclass
class GewerkeConfig:
    """Konfiguration für ein Gewerk mit Einheitspreisen."""
    
    name: str
    oz_prefix: str
    einheit: MengenEinheit
    einheitspreis: Decimal = Decimal("0")
    stlb_code: str = ""


# Standard-Gewerke für Bauausschreibungen
DEFAULT_GEWERKE = {
    "bodenbelag": GewerkeConfig(
        name="Bodenbelag",
        oz_prefix="01",
        einheit=MengenEinheit.M2,
        einheitspreis=Decimal("45.00"),
        stlb_code="352"
    ),
    "wandanstrich": GewerkeConfig(
        name="Wandanstrich",
        oz_prefix="02", 
        einheit=MengenEinheit.M2,
        einheitspreis=Decimal("12.50"),
        stlb_code="458"
    ),
    "deckenanstrich": GewerkeConfig(
        name="Deckenanstrich",
        oz_prefix="03",
        einheit=MengenEinheit.M2,
        einheitspreis=Decimal("10.00"),
        stlb_code="459"
    ),
    "sockelleisten": GewerkeConfig(
        name="Sockelleisten",
        oz_prefix="04",
        einheit=MengenEinheit.M,
        einheitspreis=Decimal("8.50"),
        stlb_code="353"
    ),
    "tueren": GewerkeConfig(
        name="Türen",
        oz_prefix="05",
        einheit=MengenEinheit.STK,
        einheitspreis=Decimal("450.00"),
        stlb_code="341"
    ),
    "fenster": GewerkeConfig(
        name="Fenster",
        oz_prefix="06",
        einheit=MengenEinheit.STK,
        einheitspreis=Decimal("850.00"),
        stlb_code="336"
    ),
    "trockenbau": GewerkeConfig(
        name="Trockenbau-Wände",
        oz_prefix="07",
        einheit=MengenEinheit.M2,
        einheitspreis=Decimal("65.00"),
        stlb_code="344"
    ),
    "estrich": GewerkeConfig(
        name="Estricharbeiten",
        oz_prefix="08",
        einheit=MengenEinheit.M2,
        einheitspreis=Decimal("28.00"),
        stlb_code="351"
    ),
}


class IFCX83Converter:
    """
    Konvertiert IFC-Daten in GAEB X83 Format.
    
    Usage:
        converter = IFCX83Converter()
        x83_xml = converter.convert_to_x83(ifc_data, projekt_name="Neubau EFH")
        
    IFC-Daten Format:
        {
            "rooms": [{"name": "Wohnzimmer", "area": 25.5, "perimeter": 20.2, ...}],
            "walls": [{"name": "Wall1", "area": 12.0, ...}],
            "doors": [{"name": "Tür1", "width": 1.0, "height": 2.1, ...}],
            "windows": [{"name": "Fenster1", "width": 1.2, "height": 1.4, ...}],
            "slabs": [{"name": "Decke EG", "area": 85.0, ...}],
        }
    """
    
    def __init__(self, gewerke: Optional[Dict[str, GewerkeConfig]] = None):
        self.gewerke = gewerke or DEFAULT_GEWERKE
        self.gaeb_generator = GAEBGenerator()
    
    def convert_to_x83(
        self,
        ifc_data: Dict[str, Any],
        projekt_name: str,
        projekt_nummer: str = "",
        auftraggeber: str = "",
        include_prices: bool = True,
        selected_gewerke: Optional[List[str]] = None,
    ) -> BytesIO:
        """
        Konvertiert IFC-Daten in GAEB X83 XML.
        
        Args:
            ifc_data: Extrahierte IFC-Daten (Räume, Wände, Türen, etc.)
            projekt_name: Projektbezeichnung
            projekt_nummer: Optionale Projektnummer
            auftraggeber: Name des Auftraggebers
            include_prices: Einheitspreise inkludieren
            selected_gewerke: Liste der zu exportierenden Gewerke (None = alle)
            
        Returns:
            BytesIO mit GAEB X83 XML
        """
        # Leistungsverzeichnis erstellen
        lv = self._create_leistungsverzeichnis(
            ifc_data=ifc_data,
            projekt_name=projekt_name,
            projekt_nummer=projekt_nummer,
            auftraggeber=auftraggeber,
            include_prices=include_prices,
            selected_gewerke=selected_gewerke,
        )
        
        # XML generieren
        return self.gaeb_generator.generate_xml(lv)
    
    def convert_to_excel(
        self,
        ifc_data: Dict[str, Any],
        projekt_name: str,
        projekt_nummer: str = "",
        include_prices: bool = True,
        selected_gewerke: Optional[List[str]] = None,
    ) -> BytesIO:
        """
        Konvertiert IFC-Daten in Excel-LV.
        
        Returns:
            BytesIO mit Excel-Datei
        """
        lv = self._create_leistungsverzeichnis(
            ifc_data=ifc_data,
            projekt_name=projekt_name,
            projekt_nummer=projekt_nummer,
            include_prices=include_prices,
            selected_gewerke=selected_gewerke,
        )
        
        return self.gaeb_generator.generate_excel(lv)
    
    def _create_leistungsverzeichnis(
        self,
        ifc_data: Dict[str, Any],
        projekt_name: str,
        projekt_nummer: str = "",
        auftraggeber: str = "",
        include_prices: bool = True,
        selected_gewerke: Optional[List[str]] = None,
    ) -> Leistungsverzeichnis:
        """Erstellt Leistungsverzeichnis aus IFC-Daten."""
        
        lose = []
        
        # Räume extrahieren
        rooms = ifc_data.get("rooms", [])
        walls = ifc_data.get("walls", [])
        doors = ifc_data.get("doors", [])
        windows = ifc_data.get("windows", [])
        slabs = ifc_data.get("slabs", [])
        
        # Gewerke filtern
        gewerke_to_process = selected_gewerke or list(self.gewerke.keys())
        
        # Los 1: Bodenbeläge (aus Räumen)
        if "bodenbelag" in gewerke_to_process and rooms:
            los_boden = self._create_bodenbelag_los(rooms, include_prices)
            if los_boden.positionen:
                lose.append(los_boden)
        
        # Los 2: Wandanstrich (aus Räumen oder Wänden)
        if "wandanstrich" in gewerke_to_process:
            los_wand = self._create_wandanstrich_los(rooms, walls, include_prices)
            if los_wand.positionen:
                lose.append(los_wand)
        
        # Los 3: Deckenanstrich (aus Räumen)
        if "deckenanstrich" in gewerke_to_process and rooms:
            los_decke = self._create_deckenanstrich_los(rooms, include_prices)
            if los_decke.positionen:
                lose.append(los_decke)
        
        # Los 4: Sockelleisten (aus Raumumfängen)
        if "sockelleisten" in gewerke_to_process and rooms:
            los_sockel = self._create_sockelleisten_los(rooms, include_prices)
            if los_sockel.positionen:
                lose.append(los_sockel)
        
        # Los 5: Türen
        if "tueren" in gewerke_to_process and doors:
            los_tueren = self._create_tueren_los(doors, include_prices)
            if los_tueren.positionen:
                lose.append(los_tueren)
        
        # Los 6: Fenster
        if "fenster" in gewerke_to_process and windows:
            los_fenster = self._create_fenster_los(windows, include_prices)
            if los_fenster.positionen:
                lose.append(los_fenster)
        
        # Los 7: Trockenbau (aus Wänden)
        if "trockenbau" in gewerke_to_process and walls:
            los_trockenbau = self._create_trockenbau_los(walls, include_prices)
            if los_trockenbau.positionen:
                lose.append(los_trockenbau)
        
        # Los 8: Estrich (aus Räumen)
        if "estrich" in gewerke_to_process and rooms:
            los_estrich = self._create_estrich_los(rooms, include_prices)
            if los_estrich.positionen:
                lose.append(los_estrich)
        
        return Leistungsverzeichnis(
            projekt_name=projekt_name,
            projekt_nummer=projekt_nummer,
            auftraggeber=auftraggeber,
            lose=lose,
            phase=GAEBPhase.X83,
        )
    
    def _create_bodenbelag_los(self, rooms: List[Dict], include_prices: bool) -> LosGruppe:
        """Erstellt Los für Bodenbeläge."""
        config = self.gewerke["bodenbelag"]
        positionen = []
        
        for idx, room in enumerate(rooms, 1):
            area = Decimal(str(room.get("area", 0)))
            if area <= 0:
                continue
                
            ep = config.einheitspreis if include_prices else Decimal("0")
            pos = Position(
                oz=f"{config.oz_prefix}.01.{idx:04d}",
                kurztext=f"Bodenbelag {room.get('number', '')} {room.get('name', '')}".strip(),
                langtext=f"Bodenbelag liefern und verlegen in Raum {room.get('name', '')}",
                menge=area.quantize(Decimal("0.01")),
                einheit=config.einheit,
                einheitspreis=ep,
                stlb_code=config.stlb_code,
            )
            positionen.append(pos)
        
        return LosGruppe(
            oz=config.oz_prefix,
            bezeichnung="Bodenbelagsarbeiten",
            positionen=positionen,
        )
    
    def _create_wandanstrich_los(
        self, rooms: List[Dict], walls: List[Dict], include_prices: bool
    ) -> LosGruppe:
        """Erstellt Los für Wandanstrich."""
        config = self.gewerke["wandanstrich"]
        positionen = []
        
        # Wandfläche aus Räumen berechnen (Umfang * Höhe)
        for idx, room in enumerate(rooms, 1):
            perimeter = room.get("perimeter", 0)
            height = room.get("height", 2.5)  # Default 2.5m
            
            if perimeter <= 0:
                continue
            
            wall_area = Decimal(str(perimeter * height))
            ep = config.einheitspreis if include_prices else Decimal("0")
            
            pos = Position(
                oz=f"{config.oz_prefix}.01.{idx:04d}",
                kurztext=f"Wandanstrich {room.get('number', '')} {room.get('name', '')}".strip(),
                langtext=f"Wandflächen streichen in Raum {room.get('name', '')}",
                menge=wall_area.quantize(Decimal("0.01")),
                einheit=config.einheit,
                einheitspreis=ep,
                stlb_code=config.stlb_code,
            )
            positionen.append(pos)
        
        return LosGruppe(
            oz=config.oz_prefix,
            bezeichnung="Malerarbeiten - Wandanstrich",
            positionen=positionen,
        )
    
    def _create_deckenanstrich_los(self, rooms: List[Dict], include_prices: bool) -> LosGruppe:
        """Erstellt Los für Deckenanstrich (= Bodenfläche)."""
        config = self.gewerke["deckenanstrich"]
        positionen = []
        
        for idx, room in enumerate(rooms, 1):
            area = Decimal(str(room.get("area", 0)))
            if area <= 0:
                continue
            
            ep = config.einheitspreis if include_prices else Decimal("0")
            pos = Position(
                oz=f"{config.oz_prefix}.01.{idx:04d}",
                kurztext=f"Deckenanstrich {room.get('number', '')} {room.get('name', '')}".strip(),
                langtext=f"Deckenflächen streichen in Raum {room.get('name', '')}",
                menge=area.quantize(Decimal("0.01")),
                einheit=config.einheit,
                einheitspreis=ep,
                stlb_code=config.stlb_code,
            )
            positionen.append(pos)
        
        return LosGruppe(
            oz=config.oz_prefix,
            bezeichnung="Malerarbeiten - Deckenanstrich",
            positionen=positionen,
        )
    
    def _create_sockelleisten_los(self, rooms: List[Dict], include_prices: bool) -> LosGruppe:
        """Erstellt Los für Sockelleisten."""
        config = self.gewerke["sockelleisten"]
        positionen = []
        
        for idx, room in enumerate(rooms, 1):
            perimeter = Decimal(str(room.get("perimeter", 0)))
            if perimeter <= 0:
                continue
            
            ep = config.einheitspreis if include_prices else Decimal("0")
            pos = Position(
                oz=f"{config.oz_prefix}.01.{idx:04d}",
                kurztext=f"Sockelleisten {room.get('number', '')} {room.get('name', '')}".strip(),
                langtext=f"Sockelleisten liefern und montieren in Raum {room.get('name', '')}",
                menge=perimeter.quantize(Decimal("0.01")),
                einheit=config.einheit,
                einheitspreis=ep,
                stlb_code=config.stlb_code,
            )
            positionen.append(pos)
        
        return LosGruppe(
            oz=config.oz_prefix,
            bezeichnung="Sockelleistenarbeiten",
            positionen=positionen,
        )
    
    def _create_tueren_los(self, doors: List[Dict], include_prices: bool) -> LosGruppe:
        """Erstellt Los für Türen."""
        config = self.gewerke["tueren"]
        positionen = []
        
        # Türen nach Typ gruppieren
        door_types: Dict[str, List[Dict]] = {}
        for door in doors:
            door_type = door.get("type", "Standard")
            width = door.get("width", 0.885)  # Default-Breite
            height = door.get("height", 2.135)  # Default-Höhe
            key = f"{door_type}_{width:.2f}x{height:.2f}"
            
            if key not in door_types:
                door_types[key] = []
            door_types[key].append(door)
        
        for idx, (key, type_doors) in enumerate(door_types.items(), 1):
            sample = type_doors[0]
            width = sample.get("width", 0.885)
            height = sample.get("height", 2.135)
            door_type = sample.get("type", "Standard")
            
            ep = config.einheitspreis if include_prices else Decimal("0")
            pos = Position(
                oz=f"{config.oz_prefix}.01.{idx:04d}",
                kurztext=f"Tür {door_type} {width:.2f}x{height:.2f}m",
                langtext=f"Innentür {door_type} liefern und einbauen, {width:.2f}m x {height:.2f}m",
                menge=Decimal(str(len(type_doors))),
                einheit=config.einheit,
                einheitspreis=ep,
                stlb_code=config.stlb_code,
            )
            positionen.append(pos)
        
        return LosGruppe(
            oz=config.oz_prefix,
            bezeichnung="Türarbeiten",
            positionen=positionen,
        )
    
    def _create_fenster_los(self, windows: List[Dict], include_prices: bool) -> LosGruppe:
        """Erstellt Los für Fenster."""
        config = self.gewerke["fenster"]
        positionen = []
        
        # Fenster nach Typ/Größe gruppieren
        window_types: Dict[str, List[Dict]] = {}
        for window in windows:
            width = window.get("width", 1.0)
            height = window.get("height", 1.2)
            key = f"{width:.2f}x{height:.2f}"
            
            if key not in window_types:
                window_types[key] = []
            window_types[key].append(window)
        
        for idx, (key, type_windows) in enumerate(window_types.items(), 1):
            sample = type_windows[0]
            width = sample.get("width", 1.0)
            height = sample.get("height", 1.2)
            
            ep = config.einheitspreis if include_prices else Decimal("0")
            pos = Position(
                oz=f"{config.oz_prefix}.01.{idx:04d}",
                kurztext=f"Fenster {width:.2f}x{height:.2f}m",
                langtext=f"Kunststofffenster liefern und einbauen, {width:.2f}m x {height:.2f}m, 2-fach Verglasung",
                menge=Decimal(str(len(type_windows))),
                einheit=config.einheit,
                einheitspreis=ep,
                stlb_code=config.stlb_code,
            )
            positionen.append(pos)
        
        return LosGruppe(
            oz=config.oz_prefix,
            bezeichnung="Fensterarbeiten",
            positionen=positionen,
        )
    
    def _create_trockenbau_los(self, walls: List[Dict], include_prices: bool) -> LosGruppe:
        """Erstellt Los für Trockenbau-Wände."""
        config = self.gewerke["trockenbau"]
        positionen = []
        
        # Gesamte Wandfläche
        total_area = sum(Decimal(str(w.get("area", 0))) for w in walls)
        
        if total_area > 0:
            ep = config.einheitspreis if include_prices else Decimal("0")
            pos = Position(
                oz=f"{config.oz_prefix}.01.0010",
                kurztext="Trockenbau-Wände GK",
                langtext="Trockenbau-Wände in Gipskarton erstellen, beidseitig beplankt",
                menge=total_area.quantize(Decimal("0.01")),
                einheit=config.einheit,
                einheitspreis=ep,
                stlb_code=config.stlb_code,
            )
            positionen.append(pos)
        
        return LosGruppe(
            oz=config.oz_prefix,
            bezeichnung="Trockenbauarbeiten",
            positionen=positionen,
        )
    
    def _create_estrich_los(self, rooms: List[Dict], include_prices: bool) -> LosGruppe:
        """Erstellt Los für Estricharbeiten."""
        config = self.gewerke["estrich"]
        positionen = []
        
        # Gesamte Bodenfläche
        total_area = sum(Decimal(str(r.get("area", 0))) for r in rooms)
        
        if total_area > 0:
            ep = config.einheitspreis if include_prices else Decimal("0")
            pos = Position(
                oz=f"{config.oz_prefix}.01.0010",
                kurztext="Zementestrich CT-C25-F4",
                langtext="Zementestrich CT-C25-F4 herstellen, 65mm Dicke, schwimmend auf Dämmung",
                menge=total_area.quantize(Decimal("0.01")),
                einheit=config.einheit,
                einheitspreis=ep,
                stlb_code=config.stlb_code,
            )
            positionen.append(pos)
        
        return LosGruppe(
            oz=config.oz_prefix,
            bezeichnung="Estricharbeiten",
            positionen=positionen,
        )
    
    def get_summary(self, ifc_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Erstellt Zusammenfassung der extrahierten Mengen.
        
        Returns:
            Dict mit Mengenübersicht pro Gewerk
        """
        rooms = ifc_data.get("rooms", [])
        walls = ifc_data.get("walls", [])
        doors = ifc_data.get("doors", [])
        windows = ifc_data.get("windows", [])
        
        total_floor_area = sum(r.get("area", 0) for r in rooms)
        total_perimeter = sum(r.get("perimeter", 0) for r in rooms)
        total_wall_area = sum(w.get("area", 0) for w in walls)
        
        return {
            "rooms_count": len(rooms),
            "doors_count": len(doors),
            "windows_count": len(windows),
            "walls_count": len(walls),
            "total_floor_area_m2": round(total_floor_area, 2),
            "total_perimeter_m": round(total_perimeter, 2),
            "total_wall_area_m2": round(total_wall_area, 2),
            "gewerke_available": list(self.gewerke.keys()),
        }


# Singleton
_converter = None

def get_ifc_x83_converter() -> IFCX83Converter:
    """Get singleton instance."""
    global _converter
    if _converter is None:
        _converter = IFCX83Converter()
    return _converter
