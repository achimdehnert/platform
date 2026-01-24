"""
RoomAnalysisHandler - Raum-Extraktion & DIN 277 Klassifikation.

Analysiert CAD-Daten zur Raumerkennung und klassifiziert
nach DIN 277 Nutzungsarten.
"""
import logging
from dataclasses import dataclass, field
from typing import Optional

from .base import (
    BaseCADHandler,
    CADHandlerResult,
    CADHandlerError,
    HandlerStatus,
)
from .area_classifier import get_area_classifier, AreaCategory

logger = logging.getLogger(__name__)


@dataclass
class RoomInfo:
    """Rauminformationen."""
    name: str
    area: float = 0.0  # in m²
    perimeter: float = 0.0  # in m
    layer: str = ""
    din277_category: str = ""
    din277_code: str = ""
    floor: int = 0
    has_door: bool = False
    has_window: bool = False
    furniture_count: int = 0
    position: tuple = (0.0, 0.0)


class RoomAnalysisHandler(BaseCADHandler):
    """
    Handler für Raum-Analyse und DIN 277 Klassifikation.
    
    Funktionen:
    - Raumerkennung aus CAD-Daten (Text + Geometrie)
    - Flächenberechnung geschlossener Polygone
    - DIN 277 Klassifikation
    - Tür/Fenster-Zuordnung
    - Raumbuch-Generierung
    
    Input:
        loader: CADLoaderService (von CADFileInputHandler)
        ifc_result: Optional - IFC Parse Result
        classify_din277: Optional - DIN 277 Klassifikation aktivieren
    
    Output:
        rooms: Liste der erkannten Räume
        total_area: Gesamtfläche in m²
        din277_summary: DIN 277 Zusammenfassung
        doors: Erkannte Türen
        windows: Erkannte Fenster
    """
    
    name = "RoomAnalysisHandler"
    description = "Raum-Extraktion & DIN 277 Klassifikation"
    required_inputs = []  # Either loader or ifc_result
    optional_inputs = ["loader", "ifc_result", "classify_din277"]
    
    # Layer die KEINE echten Raumflächen (Nutzflächen) enthalten
    EXCLUDED_LAYER_KEYWORDS = [
        # Symbole & Grafik
        "symbol", "symbole",
        "schraffur", "hatch",
        "text", "beschriftung", "annotation",
        "bemaßung", "dimension", "dim",
        # Hilfslinien
        "achse", "axis", "grid",
        "hilfslin", "construction", "hilfslinie",
        # Möbel & Einrichtung
        "möbel", "furniture", "einrichtung",
        # Haustechnik
        "elektro", "electric",
        "sanitär", "sanitary",
        "heizung", "heating",
        "lüftung", "hvac",
        # Legende & Rahmen
        "legende", "legend",
        "rahmen", "frame", "border",
        "logo", "titel", "title",
        "north", "nord", "maßstab", "scale",
        "viewport", "defpoints",
        # Ergänzungen
        "ergänzung", "ergaenzung", "supplement",
        "notiz", "note", "comment",
        # KONSTRUKTION - keine Nutzflächen!
        "decken", "ceiling", "decken",
        "deckenkonstruktion", "deckenbelag",
        "fußbodenaufbau", "fussbodenaufbau", "bodenaufbau",
        "wand", "wände", "wall", "außenwand", "innenwand",
        "sandwichwand", "sandwich",
        "konstruktion", "tragwerk", "statik",
        "fundament", "foundation",
        "dach", "roof",
        "fassade", "facade",
        "treppe", "stair",
        "aufzug", "elevator", "lift",
    ]
    
    # Layer die GÜLTIGE Raumflächen enthalten (Whitelist)
    VALID_FLOOR_KEYWORDS = [
        "raum", "räume", "room",
        "nutzfläche", "nutzflaeche", "nuf",
        "bodenplatte", "grundriss",
        "wohnfläche", "wohnflaeche",
        "büro", "buero", "office",
        "flur", "corridor",
        "küche", "kueche", "kitchen",
        "bad", "wc", "bathroom",
        "schlaf", "bedroom",
        "wohn", "living",
        "lager", "storage",
        "keller", "basement",
        "garage",
    ]
    
    # DIN 277 Kategorien
    DIN277_CATEGORIES = {
        "NUF": "Nutzungsfläche",
        "TF": "Technikfläche", 
        "VF": "Verkehrsfläche",
        "NRF": "Netto-Raumfläche",
        "KGF": "Konstruktions-Grundfläche",
        "BGF": "Brutto-Grundfläche",
    }
    
    # Raum-Klassifikation basierend auf Namen
    ROOM_CLASSIFICATION = {
        # NUF 1 - Wohnen
        "wohn": ("NUF 1", "Wohnen und Aufenthalt"),
        "schlaf": ("NUF 1", "Wohnen und Aufenthalt"),
        "kinder": ("NUF 1", "Wohnen und Aufenthalt"),
        "gäste": ("NUF 1", "Wohnen und Aufenthalt"),
        
        # NUF 2 - Büro
        "büro": ("NUF 2", "Büroarbeit"),
        "office": ("NUF 2", "Büroarbeit"),
        "arbeits": ("NUF 2", "Büroarbeit"),
        
        # NUF 3 - Produktion
        "werkstatt": ("NUF 3", "Produktion"),
        "lager": ("NUF 3", "Produktion"),
        
        # NUF 4 - Sanitär
        "bad": ("NUF 4", "Sanitär"),
        "wc": ("NUF 4", "Sanitär"),
        "dusche": ("NUF 4", "Sanitär"),
        "toilette": ("NUF 4", "Sanitär"),
        
        # NUF 5 - Küche
        "küche": ("NUF 5", "Zubereitung"),
        "kitchen": ("NUF 5", "Zubereitung"),
        
        # VF - Verkehrsfläche
        "flur": ("VF", "Verkehrsfläche"),
        "diele": ("VF", "Verkehrsfläche"),
        "treppe": ("VF", "Verkehrsfläche"),
        "gang": ("VF", "Verkehrsfläche"),
        "eingang": ("VF", "Verkehrsfläche"),
        
        # TF - Technikfläche
        "technik": ("TF", "Technikfläche"),
        "heizung": ("TF", "Technikfläche"),
        "server": ("TF", "Technikfläche"),
    }
    
    def execute(self, input_data: dict) -> CADHandlerResult:
        """Analysiert Räume."""
        result = CADHandlerResult(
            success=True,
            handler_name=self.name,
            status=HandlerStatus.RUNNING,
        )
        
        loader = input_data.get("_loader") or input_data.get("loader")
        ifc_result = input_data.get("ifc_result")
        classify_din277 = input_data.get("classify_din277", True)
        
        if not loader and not ifc_result:
            result.add_error("Keine CAD-Daten (loader oder ifc_result)")
            return result
        
        rooms = []
        doors = []
        windows = []
        
        # Process based on data source
        if ifc_result:
            rooms = self._analyze_ifc_rooms(ifc_result, result)
        elif loader:
            rooms = self._analyze_dxf_rooms(loader, result)
            doors = self._get_doors(loader)
            windows = self._get_windows(loader)
        
        # Remove duplicates (same layer + same area)
        rooms = self._deduplicate_rooms(rooms, result)
        
        # DIN 277 Classification
        if classify_din277:
            rooms = self._classify_din277(rooms)
        
        # Calculate totals
        total_area = sum(r.area for r in rooms)
        
        # DIN 277 Summary
        din277_summary = self._create_din277_summary(rooms)
        
        result.data.update({
            "rooms": [self._room_to_dict(r) for r in rooms],
            "room_count": len(rooms),
            "total_area": total_area,
            "total_area_formatted": f"{total_area:.2f} m²",
            "din277_summary": din277_summary,
            "doors": doors,
            "door_count": len(doors),
            "windows": windows,
            "window_count": len(windows),
        })
        
        result.status = HandlerStatus.SUCCESS
        logger.info(f"[{self.name}] {len(rooms)} Räume, {total_area:.1f} m²")
        
        return result
    
    def _analyze_ifc_rooms(self, ifc_result, result: CADHandlerResult) -> list[RoomInfo]:
        """Extrahiert Räume aus IFC."""
        rooms = []
        
        for ifc_room in ifc_result.rooms:
            room = RoomInfo(
                name=ifc_room.name or "Unbekannt",
                area=ifc_room.area or 0.0,
                layer="IFC",
                floor=getattr(ifc_room, 'floor', 0),
            )
            rooms.append(room)
        
        return rooms
    
    def _analyze_dxf_rooms(self, loader, result: CADHandlerResult) -> list[RoomInfo]:
        """Extrahiert Räume aus DXF."""
        rooms = []
        
        # 1. Text-basierte Raumerkennung
        try:
            text_rooms = loader.get_rooms()
            for tr in text_rooms:
                room = RoomInfo(
                    name=tr.get("name", "Unbekannt"),
                    layer=tr.get("layer", ""),
                    position=(tr.get("x", 0), tr.get("y", 0)),
                )
                rooms.append(room)
        except Exception as e:
            result.add_warning(f"Text-Raumerkennung fehlgeschlagen: {e}")
        
        # 2. Geometrie-basierte Flächenberechnung
        try:
            room_areas = loader.get_room_areas()
            
            if not room_areas:
                result.add_warning("Keine geschlossenen Polylinien (LWPOLYLINE) gefunden")
            else:
                # Detect units for conversion
                unit_factor = self._get_unit_factor(loader, room_areas)
                logger.info(f"[{self.name}] Unit factor: {unit_factor}, {len(room_areas)} areas found")
                
                # Match areas to rooms or create new
                excluded_count = 0
                valid_count = 0
                use_llm = input_data.get("use_llm", True)  # LLM-Fallback default AN
                classifier = get_area_classifier(use_llm=use_llm)
                
                for area_info in room_areas:
                    layer = area_info.get("layer", "")
                    
                    # Klassifiziere Layer mit dem neuen Classifier
                    category, confidence = classifier.classify(layer)
                    
                    # Nur GRUNDFLÄCHE zählt als Nutzfläche
                    if category != AreaCategory.GRUNDFLAECHE:
                        excluded_count += 1
                        continue
                    
                    area_raw = area_info.get("area", 0)
                    perimeter_raw = area_info.get("perimeter", 0)
                    
                    # Apply unit conversion
                    area_m2 = area_raw * unit_factor
                    perimeter_m = perimeter_raw * (unit_factor ** 0.5)  # sqrt for linear
                    
                    # Skip unrealistic areas (< 1m² or > 10000m²)
                    if area_m2 < 1.0 or area_m2 > 10000:
                        continue
                    
                    # Try to find matching room
                    matched = False
                    for room in rooms:
                        if room.layer == layer and room.area == 0:
                            room.area = area_m2
                            room.perimeter = perimeter_m
                            matched = True
                            break
                    
                    # Create new room if no match
                    if not matched:
                        room = RoomInfo(
                            name=f"Fläche_{layer}" if layer else "Unbenannt",
                            area=area_m2,
                            perimeter=perimeter_m,
                            layer=layer,
                        )
                        rooms.append(room)
                        valid_count += 1
                
                if excluded_count > 0:
                    result.add_warning(f"{excluded_count} Layer übersprungen (Konstruktion/Symbole)")
                logger.info(f"[{self.name}] {valid_count} gültige Nutzflächen gefunden")
                    
        except Exception as e:
            result.add_warning(f"Flächen-Berechnung fehlgeschlagen: {e}")
        
        # 3. Fallback: Estimate from bounding box if no areas found
        if not any(r.area > 0 for r in rooms):
            try:
                stats = loader.get_statistics()
                bbox = stats.get("bounding_box", {})
                if bbox:
                    width = bbox.get("width", 0)
                    height = bbox.get("height", 0)
                    if width > 0 and height > 0:
                        # Estimate ~60% of bounding box as usable area
                        estimated_area = width * height * 0.6
                        # Apply unit conversion
                        if estimated_area > 1_000_000:
                            estimated_area /= 1_000_000
                        elif estimated_area > 10_000:
                            estimated_area /= 10_000
                        
                        if estimated_area > 1:
                            result.add_warning(f"Keine Polylinien - Schätzung aus Bounding Box: ~{estimated_area:.0f} m²")
                            rooms.append(RoomInfo(
                                name="Geschätzte Gesamtfläche",
                                area=estimated_area,
                                layer="ESTIMATE",
                            ))
            except Exception as e:
                logger.warning(f"Bounding box estimation failed: {e}")
        
        return rooms
    
    def _deduplicate_rooms(self, rooms: list[RoomInfo], result: CADHandlerResult) -> list[RoomInfo]:
        """
        Entfernt Duplikate basierend auf Layer + Fläche.
        
        Duplikate entstehen wenn:
        - Gleiche Polyline mehrfach vorkommt
        - Gleicher Layer mit gleicher Fläche
        """
        if not rooms:
            return rooms
        
        seen = set()
        unique_rooms = []
        duplicates = 0
        
        for room in rooms:
            # Key: Layer + gerundete Fläche (auf 0.1 m²)
            key = (room.layer, round(room.area, 1))
            
            if key in seen:
                duplicates += 1
                continue
            
            seen.add(key)
            unique_rooms.append(room)
        
        if duplicates > 0:
            result.add_warning(f"{duplicates} Duplikate entfernt")
            logger.info(f"[{self.name}] Removed {duplicates} duplicate rooms")
        
        return unique_rooms
    
    def _is_excluded_layer(self, layer_name: str) -> bool:
        """
        Prüft ob Layer von Flächenberechnung ausgeschlossen werden soll.
        
        Ausgeschlossen werden:
        - Symbole, Schraffuren, Beschriftungen
        - Konstruktionen (Decken, Wände, etc.)
        - TEXT-Formatierungen
        """
        if not layer_name:
            return False
        
        layer_lower = layer_name.lower()
        
        # TEXT-Formatierungscodes filtern (z.B. \A1;{\pql;\fArial...)
        if layer_name.startswith("\\") or "{\\p" in layer_name or "\\f" in layer_name:
            return True
        
        # Prüfe Ausschluss-Keywords
        for keyword in self.EXCLUDED_LAYER_KEYWORDS:
            if keyword in layer_lower:
                return True
        
        return False
    
    def _is_valid_floor_layer(self, layer_name: str) -> bool:
        """
        Prüft ob Layer eine gültige Raumfläche ist (Whitelist).
        
        Gültig sind nur:
        - Räume, Nutzflächen, Bodenplatten
        - Spezifische Raumtypen (Büro, Flur, etc.)
        """
        if not layer_name:
            return False
        
        layer_lower = layer_name.lower()
        
        for keyword in self.VALID_FLOOR_KEYWORDS:
            if keyword in layer_lower:
                return True
        
        return False
    
    def _get_unit_factor(self, loader, room_areas: list) -> float:
        """
        Ermittelt Umrechnungsfaktor für Flächen zu m².
        
        Strategie:
        1. Prüfe DXF-Einheiten
        2. Analysiere Größenordnung der Flächen
        3. Wähle passenden Faktor
        """
        # Try to get units from analysis
        try:
            analysis = loader.get_analysis()
            units = getattr(analysis, 'units', None)
            if units:
                units_lower = str(units).lower()
                if 'mm' in units_lower or 'millimeter' in units_lower:
                    return 1 / 1_000_000  # mm² to m²
                elif 'cm' in units_lower or 'centimeter' in units_lower:
                    return 1 / 10_000  # cm² to m²
                elif 'm' in units_lower and 'mm' not in units_lower:
                    return 1.0  # Already m²
        except:
            pass
        
        # Fallback: Analyze magnitude of areas
        if not room_areas:
            return 1.0
        
        max_area = max(a.get("area", 0) for a in room_areas)
        
        if max_area > 1_000_000:  # Likely mm² (>1m² in mm² = 1,000,000)
            return 1 / 1_000_000
        elif max_area > 10_000:  # Likely cm² 
            return 1 / 10_000
        elif max_area > 1:  # Reasonable m² values
            return 1.0
        else:  # Very small, might be km² or already normalized
            return 1.0
    
    def _get_doors(self, loader) -> list[dict]:
        """Holt Tür-Informationen."""
        try:
            return loader.get_doors()
        except:
            return []
    
    def _get_windows(self, loader) -> list[dict]:
        """Holt Fenster-Informationen."""
        try:
            return loader.get_windows()
        except:
            return []
    
    def _classify_din277(self, rooms: list[RoomInfo]) -> list[RoomInfo]:
        """Klassifiziert Räume nach DIN 277."""
        for room in rooms:
            name_lower = room.name.lower()
            
            for keyword, (code, category) in self.ROOM_CLASSIFICATION.items():
                if keyword in name_lower:
                    room.din277_code = code
                    room.din277_category = category
                    break
            
            # Default to NUF if not classified
            if not room.din277_code:
                room.din277_code = "NUF"
                room.din277_category = "Nutzungsfläche"
        
        return rooms
    
    def _create_din277_summary(self, rooms: list[RoomInfo]) -> dict:
        """Erstellt DIN 277 Zusammenfassung."""
        summary = {}
        
        for room in rooms:
            code = room.din277_code or "Unbekannt"
            if code not in summary:
                summary[code] = {
                    "category": room.din277_category,
                    "count": 0,
                    "area": 0.0,
                }
            summary[code]["count"] += 1
            summary[code]["area"] += room.area
        
        # Format areas
        for code in summary:
            summary[code]["area_formatted"] = f"{summary[code]['area']:.2f} m²"
        
        return summary
    
    def _room_to_dict(self, room: RoomInfo) -> dict:
        """Konvertiert RoomInfo zu Dictionary."""
        return {
            "name": room.name,
            "area": room.area,
            "area_formatted": f"{room.area:.2f} m²",
            "perimeter": room.perimeter,
            "layer": room.layer,
            "din277_code": room.din277_code,
            "din277_category": room.din277_category,
            "floor": room.floor,
            "has_door": room.has_door,
            "has_window": room.has_window,
            "furniture_count": room.furniture_count,
            "position": room.position,
        }
