"""
MassenHandler - Flächen, Volumina, Umfänge berechnen.

Berechnet Massen aus CAD-Geometrie für LV-Erstellung
und GAEB-Export.
"""
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .base import (
    BaseCADHandler,
    CADHandlerResult,
    CADHandlerError,
    HandlerStatus,
)

logger = logging.getLogger(__name__)


class MassType(Enum):
    """Massentypen."""
    AREA = "area"           # Fläche (m²)
    LENGTH = "length"       # Länge (m)
    PERIMETER = "perimeter" # Umfang (m)
    VOLUME = "volume"       # Volumen (m³)
    COUNT = "count"         # Stückzahl


@dataclass
class MassItem:
    """Einzelne Massenposition."""
    description: str
    mass_type: MassType
    value: float
    unit: str
    layer: str = ""
    gaeb_position: str = ""
    gaeb_text: str = ""
    
    def to_dict(self) -> dict:
        return {
            "description": self.description,
            "type": self.mass_type.value,
            "value": self.value,
            "unit": self.unit,
            "layer": self.layer,
            "gaeb_position": self.gaeb_position,
            "gaeb_text": self.gaeb_text,
            "formatted": f"{self.value:.2f} {self.unit}",
        }


@dataclass
class MassCategory:
    """Massenkategorie (z.B. Wände, Böden, etc.)."""
    name: str
    items: list = field(default_factory=list)
    total: float = 0.0
    unit: str = "m²"
    
    def add_item(self, item: MassItem):
        self.items.append(item)
        if item.mass_type == MassType.AREA:
            self.total += item.value


class MassenHandler(BaseCADHandler):
    """
    Handler für Massenberechnung.
    
    Funktionen:
    - Flächenberechnung aus Polygonen
    - Längenberechnung aus Linien
    - Umfangsberechnung
    - Stückzählung (Türen, Fenster, etc.)
    - GAEB-Positionszuordnung
    - LV-Struktur Vorbereitung
    
    Input:
        loader: CADLoaderService (von CADFileInputHandler)
        rooms: Optional - Räume (von RoomAnalysisHandler)
        include_gaeb: Optional - GAEB-Positionen generieren
    
    Output:
        masses: Massenliste nach Kategorien
        summary: Zusammenfassung
        gaeb_positions: GAEB-Positionen (wenn aktiviert)
    """
    
    name = "MassenHandler"
    description = "Flächen, Volumina, Umfänge berechnen für LV/GAEB"
    required_inputs = []
    optional_inputs = ["loader", "rooms", "include_gaeb", "wall_height"]
    
    # Layer die KEINE echten Flächen sind (gleich wie RoomAnalysisHandler)
    EXCLUDED_LAYER_KEYWORDS = [
        "symbol", "symbole",
        "schraffur", "hatch",
        "text", "beschriftung", "annotation",
        "bemaßung", "dimension", "dim",
        "möbel", "furniture", "einrichtung",
        "legende", "legend",
        "rahmen", "frame", "border",
        "viewport", "defpoints",
        "ergänzung", "ergaenzung", "supplement",
        "notiz", "note", "comment",
        "hilfslin", "construction",
    ]
    
    # Standard GAEB Positionen
    GAEB_MAPPING = {
        "wand": {
            "position": "03.01.001",
            "text": "Wandfläche",
            "unit": "m²",
        },
        "boden": {
            "position": "03.02.001",
            "text": "Bodenfläche",
            "unit": "m²",
        },
        "decke": {
            "position": "03.03.001",
            "text": "Deckenfläche",
            "unit": "m²",
        },
        "tür": {
            "position": "04.01.001",
            "text": "Innentür",
            "unit": "Stk",
        },
        "fenster": {
            "position": "04.02.001",
            "text": "Fenster",
            "unit": "Stk",
        },
        "sockel": {
            "position": "03.04.001",
            "text": "Sockelleiste",
            "unit": "m",
        },
    }
    
    def execute(self, input_data: dict) -> CADHandlerResult:
        """Berechnet Massen."""
        result = CADHandlerResult(
            success=True,
            handler_name=self.name,
            status=HandlerStatus.RUNNING,
        )
        
        loader = input_data.get("_loader") or input_data.get("loader")
        rooms = input_data.get("rooms", [])
        include_gaeb = input_data.get("include_gaeb", True)
        wall_height = input_data.get("wall_height", 2.5)  # Standard 2.5m
        
        if not loader and not rooms:
            result.add_error("Keine Daten (loader oder rooms)")
            return result
        
        categories = {}
        
        # 1. Bodenflächen
        floor_cat = self._calculate_floors(loader, rooms, result)
        if floor_cat.items:
            categories["floors"] = floor_cat
        
        # 2. Wandflächen (aus Umfang * Höhe)
        wall_cat = self._calculate_walls(loader, rooms, wall_height, result)
        if wall_cat.items:
            categories["walls"] = wall_cat
        
        # 3. Deckenflächen (= Bodenflächen)
        ceiling_cat = self._calculate_ceilings(floor_cat, result)
        if ceiling_cat.items:
            categories["ceilings"] = ceiling_cat
        
        # 4. Sockelleisten (Umfang)
        baseboard_cat = self._calculate_baseboards(loader, rooms, result)
        if baseboard_cat.items:
            categories["baseboards"] = baseboard_cat
        
        # 5. Stückzahlen (Türen, Fenster)
        elements_cat = self._count_elements(loader, result)
        if elements_cat.items:
            categories["elements"] = elements_cat
        
        # GAEB Export vorbereiten
        gaeb_positions = []
        if include_gaeb:
            gaeb_positions = self._create_gaeb_positions(categories)
        
        # Zusammenfassung
        summary = self._create_summary(categories)
        
        result.data.update({
            "categories": {k: self._category_to_dict(v) for k, v in categories.items()},
            "summary": summary,
            "gaeb_positions": gaeb_positions,
            "wall_height_used": wall_height,
        })
        
        result.status = HandlerStatus.SUCCESS
        logger.info(f"[{self.name}] {len(categories)} Kategorien berechnet")
        
        return result
    
    def _is_excluded_layer(self, layer_name: str) -> bool:
        """Prüft ob Layer ausgeschlossen werden soll."""
        if not layer_name:
            return False
        layer_lower = layer_name.lower()
        return any(kw in layer_lower for kw in self.EXCLUDED_LAYER_KEYWORDS)
    
    def _calculate_floors(self, loader, rooms: list, result: CADHandlerResult) -> MassCategory:
        """Berechnet Bodenflächen."""
        category = MassCategory(name="Bodenflächen", unit="m²")
        
        # From rooms (filter excluded layers)
        for room in rooms:
            if isinstance(room, dict):
                area = room.get("area", 0)
                name = room.get("name", "Raum")
                layer = room.get("layer", "")
            else:
                area = getattr(room, "area", 0)
                name = getattr(room, "name", "Raum")
                layer = getattr(room, "layer", "")
            
            # Skip excluded layers (Symbole, Schraffuren, etc.)
            if self._is_excluded_layer(layer):
                continue
            
            if area > 0:
                item = MassItem(
                    description=f"Boden {name}",
                    mass_type=MassType.AREA,
                    value=area,
                    unit="m²",
                    gaeb_position=self.GAEB_MAPPING["boden"]["position"],
                    gaeb_text=f"Bodenbelag {name}",
                )
                category.add_item(item)
        
        # From loader if no rooms
        if not category.items and loader:
            try:
                room_areas = loader.get_room_areas()
                for i, ra in enumerate(room_areas[:20]):
                    area_m2 = ra.get("area", 0) / 1_000_000
                    if area_m2 > 1.0:
                        item = MassItem(
                            description=f"Fläche {i+1}",
                            mass_type=MassType.AREA,
                            value=area_m2,
                            unit="m²",
                            layer=ra.get("layer", ""),
                            gaeb_position=self.GAEB_MAPPING["boden"]["position"],
                        )
                        category.add_item(item)
            except Exception as e:
                result.add_warning(f"Flächenberechnung fehlgeschlagen: {e}")
        
        return category
    
    def _calculate_walls(self, loader, rooms: list, wall_height: float, 
                         result: CADHandlerResult) -> MassCategory:
        """Berechnet Wandflächen aus Umfang × Höhe."""
        category = MassCategory(name="Wandflächen", unit="m²")
        
        for room in rooms:
            if isinstance(room, dict):
                perimeter = room.get("perimeter", 0)
                name = room.get("name", "Raum")
                layer = room.get("layer", "")
            else:
                perimeter = getattr(room, "perimeter", 0)
                name = getattr(room, "name", "Raum")
                layer = getattr(room, "layer", "")
            
            # Skip excluded layers
            if self._is_excluded_layer(layer):
                continue
            
            if perimeter > 0:
                wall_area = perimeter * wall_height
                item = MassItem(
                    description=f"Wände {name}",
                    mass_type=MassType.AREA,
                    value=wall_area,
                    unit="m²",
                    gaeb_position=self.GAEB_MAPPING["wand"]["position"],
                    gaeb_text=f"Wandfläche {name} (U={perimeter:.1f}m × H={wall_height}m)",
                )
                category.add_item(item)
        
        return category
    
    def _calculate_ceilings(self, floor_cat: MassCategory, 
                            result: CADHandlerResult) -> MassCategory:
        """Deckenflächen = Bodenflächen."""
        category = MassCategory(name="Deckenflächen", unit="m²")
        
        for floor_item in floor_cat.items:
            item = MassItem(
                description=floor_item.description.replace("Boden", "Decke"),
                mass_type=MassType.AREA,
                value=floor_item.value,
                unit="m²",
                layer=floor_item.layer,
                gaeb_position=self.GAEB_MAPPING["decke"]["position"],
                gaeb_text=floor_item.gaeb_text.replace("Bodenbelag", "Decke") if floor_item.gaeb_text else "",
            )
            category.add_item(item)
        
        return category
    
    def _calculate_baseboards(self, loader, rooms: list, 
                              result: CADHandlerResult) -> MassCategory:
        """Berechnet Sockelleisten (Umfang)."""
        category = MassCategory(name="Sockelleisten", unit="m")
        
        for room in rooms:
            if isinstance(room, dict):
                perimeter = room.get("perimeter", 0)
                name = room.get("name", "Raum")
                layer = room.get("layer", "")
            else:
                perimeter = getattr(room, "perimeter", 0)
                name = getattr(room, "name", "Raum")
                layer = getattr(room, "layer", "")
            
            # Skip excluded layers
            if self._is_excluded_layer(layer):
                continue
            
            if perimeter > 0:
                item = MassItem(
                    description=f"Sockel {name}",
                    mass_type=MassType.LENGTH,
                    value=perimeter,
                    unit="m",
                    gaeb_position=self.GAEB_MAPPING["sockel"]["position"],
                    gaeb_text=f"Sockelleiste {name}",
                )
                category.items.append(item)
                category.total += perimeter
        
        return category
    
    def _count_elements(self, loader, result: CADHandlerResult) -> MassCategory:
        """Zählt Bauelemente (Türen, Fenster)."""
        category = MassCategory(name="Bauelemente", unit="Stk")
        
        if not loader:
            return category
        
        try:
            doors = loader.get_doors()
            if doors:
                item = MassItem(
                    description="Innentüren",
                    mass_type=MassType.COUNT,
                    value=len(doors),
                    unit="Stk",
                    gaeb_position=self.GAEB_MAPPING["tür"]["position"],
                    gaeb_text="Innentür einflügelig",
                )
                category.items.append(item)
                category.total += len(doors)
        except:
            pass
        
        try:
            windows = loader.get_windows()
            if windows:
                item = MassItem(
                    description="Fenster",
                    mass_type=MassType.COUNT,
                    value=len(windows),
                    unit="Stk",
                    gaeb_position=self.GAEB_MAPPING["fenster"]["position"],
                    gaeb_text="Fenster",
                )
                category.items.append(item)
                category.total += len(windows)
        except:
            pass
        
        return category
    
    def _create_gaeb_positions(self, categories: dict) -> list[dict]:
        """Erstellt GAEB X84 Positionen."""
        positions = []
        
        for cat_name, category in categories.items():
            for item in category.items:
                if item.gaeb_position:
                    positions.append({
                        "position": item.gaeb_position,
                        "text": item.gaeb_text or item.description,
                        "quantity": item.value,
                        "unit": item.unit,
                        "category": cat_name,
                    })
        
        return positions
    
    def _create_summary(self, categories: dict) -> dict:
        """Erstellt Zusammenfassung."""
        summary = {
            "total_floor_area": 0.0,
            "total_wall_area": 0.0,
            "total_ceiling_area": 0.0,
            "total_baseboard_length": 0.0,
            "door_count": 0,
            "window_count": 0,
        }
        
        if "floors" in categories:
            summary["total_floor_area"] = categories["floors"].total
        if "walls" in categories:
            summary["total_wall_area"] = categories["walls"].total
        if "ceilings" in categories:
            summary["total_ceiling_area"] = categories["ceilings"].total
        if "baseboards" in categories:
            summary["total_baseboard_length"] = categories["baseboards"].total
        if "elements" in categories:
            for item in categories["elements"].items:
                if "tür" in item.description.lower():
                    summary["door_count"] = int(item.value)
                elif "fenster" in item.description.lower():
                    summary["window_count"] = int(item.value)
        
        # Formatted strings
        summary["total_floor_area_formatted"] = f"{summary['total_floor_area']:.2f} m²"
        summary["total_wall_area_formatted"] = f"{summary['total_wall_area']:.2f} m²"
        
        return summary
    
    def _category_to_dict(self, category: MassCategory) -> dict:
        """Konvertiert Kategorie zu Dictionary."""
        return {
            "name": category.name,
            "items": [item.to_dict() for item in category.items],
            "total": category.total,
            "total_formatted": f"{category.total:.2f} {category.unit}",
            "unit": category.unit,
            "item_count": len(category.items),
        }
