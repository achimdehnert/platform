"""
Brandschutz Handler für CAD-Analyse.

Erkennt und analysiert brandschutzrelevante Elemente aus CAD-Dateien:
- Fluchtwege und Rettungswege
- Brandabschnitte und Feuerwiderstandsklassen
- Ex-Zonen (Explosionsgefährdete Bereiche)
- Löscheinrichtungen (Feuerlöscher, Hydranten, Sprinkler)
- Rauch- und Wärmemelder
- Brandschutztüren (T30, T60, T90)
- RWA-Anlagen

Regelwerke:
- ASR A2.3 (Fluchtwege)
- DIN 4102 / EN 13501 (Feuerwiderstand)
- ATEX / BetrSichV (Ex-Schutz)
- DIN 14675 (Brandmeldeanlagen)
"""
import re
import json
import logging
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional

from .base import (
    BaseCADHandler,
    CADHandlerResult,
    HandlerStatus,
)

logger = logging.getLogger(__name__)


class Feuerwiderstand(Enum):
    """Feuerwiderstandsklassen nach DIN 4102 / EN 13501."""
    F30 = "F30"    # 30 Minuten
    F60 = "F60"    # 60 Minuten
    F90 = "F90"    # 90 Minuten
    F120 = "F120"  # 120 Minuten
    F180 = "F180"  # 180 Minuten
    UNBEKANNT = "unbekannt"


class ExZone(Enum):
    """Explosionsgefährdete Bereiche nach ATEX."""
    ZONE_0 = "Zone 0"    # Ständig explosionsfähige Atmosphäre (Gas)
    ZONE_1 = "Zone 1"    # Gelegentlich (Gas)
    ZONE_2 = "Zone 2"    # Selten und kurzzeitig (Gas)
    ZONE_20 = "Zone 20"  # Ständig (Staub)
    ZONE_21 = "Zone 21"  # Gelegentlich (Staub)
    ZONE_22 = "Zone 22"  # Selten (Staub)
    KEINE = "keine"


class BrandschutzKategorie(Enum):
    """Kategorien für Brandschutz-Elemente."""
    FLUCHTWEG = "fluchtweg"
    NOTAUSGANG = "notausgang"
    BRANDABSCHNITT = "brandabschnitt"
    BRANDWAND = "brandwand"
    BRANDSCHUTZTUR = "brandschutztür"
    FEUERLOESCHER = "feuerlöscher"
    HYDRANT = "hydrant"
    SPRINKLER = "sprinkler"
    RAUCHMELDER = "rauchmelder"
    WAERMEMELDER = "wärmemelder"
    BRANDMELDER = "brandmelder"
    RWA = "rwa"
    EX_ZONE = "ex_zone"
    LAGERBEREICH = "lagerbereich"
    SAMMELPLATZ = "sammelplatz"
    SONSTIGES = "sonstiges"


@dataclass
class Fluchtweg:
    """Fluchtweg-Information."""
    name: str = ""
    laenge_m: float = 0.0
    breite_m: float = 0.0
    layer: str = ""
    etage: str = ""
    ist_hauptfluchtweg: bool = False
    max_laenge_ok: bool = True  # Max 35m nach ASR A2.3
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Brandabschnitt:
    """Brandabschnitt-Information."""
    name: str = ""
    flaeche_m2: float = 0.0
    feuerwiderstand: str = Feuerwiderstand.UNBEKANNT.value
    layer: str = ""
    etage: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ExBereich:
    """Explosionsgefährdeter Bereich."""
    name: str = ""
    zone: str = ExZone.KEINE.value
    flaeche_m2: float = 0.0
    layer: str = ""
    medium: str = ""  # Gas, Staub, etc.
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Brandschutzeinrichtung:
    """Brandschutz-Einrichtung (Melder, Löscher, etc.)."""
    typ: str = ""
    kategorie: str = ""
    position_x: float = 0.0
    position_y: float = 0.0
    layer: str = ""
    etage: str = ""
    block_name: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BrandschutzAnalyse:
    """Gesamtergebnis der Brandschutz-Analyse."""
    fluchtwege: list[Fluchtweg] = field(default_factory=list)
    brandabschnitte: list[Brandabschnitt] = field(default_factory=list)
    ex_bereiche: list[ExBereich] = field(default_factory=list)
    einrichtungen: list[Brandschutzeinrichtung] = field(default_factory=list)
    
    # Zusammenfassung
    anzahl_notausgaenge: int = 0
    anzahl_feuerloescher: int = 0
    anzahl_rauchmelder: int = 0
    anzahl_sprinkler: int = 0
    gesamtflaeche_ex_m2: float = 0.0
    
    # Prüfergebnisse
    warnungen: list[str] = field(default_factory=list)
    maengel: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "fluchtwege": [f.to_dict() for f in self.fluchtwege],
            "brandabschnitte": [b.to_dict() for b in self.brandabschnitte],
            "ex_bereiche": [e.to_dict() for e in self.ex_bereiche],
            "einrichtungen": [e.to_dict() for e in self.einrichtungen],
            "zusammenfassung": {
                "notausgaenge": self.anzahl_notausgaenge,
                "feuerloescher": self.anzahl_feuerloescher,
                "rauchmelder": self.anzahl_rauchmelder,
                "sprinkler": self.anzahl_sprinkler,
                "ex_flaeche_m2": self.gesamtflaeche_ex_m2,
            },
            "warnungen": self.warnungen,
            "maengel": self.maengel,
        }


class BrandschutzHandler(BaseCADHandler):
    """
    Handler für Brandschutz-Analyse aus CAD-Dateien.
    
    Erkennt:
    - Fluchtwege und Rettungswege
    - Brandabschnitte (F30, F60, F90)
    - Ex-Zonen (0, 1, 2, 20, 21, 22)
    - Löscheinrichtungen
    - Melder (Rauch, Wärme, Brand)
    - Brandschutztüren (T30, T60, T90)
    
    Input:
        loader: ezdxf-Dokument oder ifcopenshell-Modell
        format: "dxf" oder "ifc"
        use_llm: bool - LLM für unbekannte Layer
    
    Output:
        brandschutz: BrandschutzAnalyse mit allen Elementen
    """
    
    name = "BrandschutzHandler"
    description = "Analysiert Brandschutz-Elemente in CAD-Dateien"
    required_inputs = ["loader", "format"]
    optional_inputs = ["use_llm", "etage"]
    
    # Layer-Keywords für Erkennung
    LAYER_KEYWORDS = {
        BrandschutzKategorie.FLUCHTWEG: [
            "flucht", "rettung", "escape", "notweg", "fluchtweg",
            "rettungsweg", "emergency",
        ],
        BrandschutzKategorie.NOTAUSGANG: [
            "notausgang", "emergency exit", "notaus", "ausgang_not",
        ],
        BrandschutzKategorie.BRANDABSCHNITT: [
            "brandabschnitt", "ba_", "fire compartment", "brandschutz_abschnitt",
        ],
        BrandschutzKategorie.BRANDWAND: [
            "brandwand", "f30", "f60", "f90", "f120", "fire wall",
            "feuerwiderstand", "rei", "el", "ei_",
        ],
        BrandschutzKategorie.BRANDSCHUTZTUR: [
            "t30", "t60", "t90", "brandschutzt", "feuerschutzt",
            "rauchschutzt", "rs_", "fire door",
        ],
        BrandschutzKategorie.FEUERLOESCHER: [
            "feuerlöscher", "feuerloescher", "lösch", "extinguisher",
        ],
        BrandschutzKategorie.HYDRANT: [
            "hydrant", "wandhydrant", "löschwasser",
        ],
        BrandschutzKategorie.SPRINKLER: [
            "sprinkler", "sprink", "löschanlage",
        ],
        BrandschutzKategorie.RAUCHMELDER: [
            "rauchmelder", "rauchwarn", "smoke", "rm_",
        ],
        BrandschutzKategorie.WAERMEMELDER: [
            "wärmemelder", "waermemelder", "heat", "wm_",
        ],
        BrandschutzKategorie.BRANDMELDER: [
            "brandmelder", "bma", "fire alarm", "melder",
        ],
        BrandschutzKategorie.RWA: [
            "rwa", "rauch", "wärmeabzug", "rauchabzug", "entrauchung",
        ],
        BrandschutzKategorie.EX_ZONE: [
            "ex_", "ex-", "zone_0", "zone_1", "zone_2", "zone_20",
            "zone_21", "zone_22", "atex", "explosion",
        ],
        BrandschutzKategorie.LAGERBEREICH: [
            "lager", "gefahrstoff", "brennbar", "storage",
        ],
        BrandschutzKategorie.SAMMELPLATZ: [
            "sammelplatz", "sammelpunkt", "assembly", "muster",
        ],
    }
    
    # Feuerwiderstand-Patterns
    FEUERWIDERSTAND_PATTERNS = [
        (r"F\s*30|REI\s*30|EI\s*30", Feuerwiderstand.F30),
        (r"F\s*60|REI\s*60|EI\s*60", Feuerwiderstand.F60),
        (r"F\s*90|REI\s*90|EI\s*90", Feuerwiderstand.F90),
        (r"F\s*120|REI\s*120|EI\s*120", Feuerwiderstand.F120),
        (r"F\s*180|REI\s*180|EI\s*180", Feuerwiderstand.F180),
    ]
    
    # Ex-Zonen-Patterns
    EX_ZONE_PATTERNS = [
        (r"(?:zone|ex)[_\-\s]*0(?!\d)", ExZone.ZONE_0),
        (r"(?:zone|ex)[_\-\s]*1(?!\d)", ExZone.ZONE_1),
        (r"(?:zone|ex)[_\-\s]*2(?:0|1|2)?", ExZone.ZONE_2),
        (r"(?:zone|ex)[_\-\s]*20", ExZone.ZONE_20),
        (r"(?:zone|ex)[_\-\s]*21", ExZone.ZONE_21),
        (r"(?:zone|ex)[_\-\s]*22", ExZone.ZONE_22),
    ]
    
    def execute(self, input_data: dict) -> CADHandlerResult:
        """Führt Brandschutz-Analyse durch."""
        result = CADHandlerResult(
            success=True,
            handler_name=self.name,
            status=HandlerStatus.RUNNING,
        )
        
        loader = input_data.get("loader")
        format_type = input_data.get("format", "dxf")
        use_llm = input_data.get("use_llm", False)
        etage = input_data.get("etage", "EG")
        
        if not loader:
            result.add_error("Kein CAD-Dokument (loader) übergeben")
            return result
        
        analyse = BrandschutzAnalyse()
        
        try:
            if format_type == "dxf":
                analyse = self._analyze_dxf(loader, analyse, etage)
            elif format_type == "ifc":
                analyse = self._analyze_ifc(loader, analyse, etage)
            else:
                result.add_error(f"Unbekanntes Format: {format_type}")
                return result
            
            # Prüfungen durchführen
            analyse = self._perform_checks(analyse)
            
            # Zusammenfassung berechnen
            analyse = self._calculate_summary(analyse)
            
        except Exception as e:
            result.add_error(f"Analyse-Fehler: {e}")
            logger.exception(f"[{self.name}] Fehler bei Brandschutz-Analyse")
            return result
        
        # Ergebnis
        result.data["brandschutz"] = analyse.to_dict()
        result.data["fluchtwege_count"] = len(analyse.fluchtwege)
        result.data["brandabschnitte_count"] = len(analyse.brandabschnitte)
        result.data["ex_bereiche_count"] = len(analyse.ex_bereiche)
        result.data["einrichtungen_count"] = len(analyse.einrichtungen)
        result.data["warnungen"] = analyse.warnungen
        result.data["maengel"] = analyse.maengel
        
        result.status = HandlerStatus.SUCCESS
        logger.info(f"[{self.name}] Analyse abgeschlossen: {len(analyse.einrichtungen)} Einrichtungen gefunden")
        
        return result
    
    def _analyze_dxf(self, doc, analyse: BrandschutzAnalyse, etage: str) -> BrandschutzAnalyse:
        """Analysiert DXF-Dokument."""
        msp = doc.modelspace()
        
        # Alle Layer durchgehen
        for layer in doc.layers:
            layer_name = layer.dxf.name.lower()
            kategorie = self._classify_layer(layer_name)
            
            if kategorie:
                logger.debug(f"[{self.name}] Layer '{layer.dxf.name}' → {kategorie.value}")
        
        # Entities durchgehen
        for entity in msp:
            layer_name = entity.dxf.layer.lower() if hasattr(entity.dxf, 'layer') else ""
            kategorie = self._classify_layer(layer_name)
            
            if not kategorie:
                continue
            
            # Je nach Entity-Typ verarbeiten
            if entity.dxftype() == "LWPOLYLINE":
                self._process_polyline(entity, kategorie, analyse, etage)
            elif entity.dxftype() == "INSERT":
                self._process_block(entity, kategorie, analyse, etage)
            elif entity.dxftype() == "LINE":
                self._process_line(entity, kategorie, analyse, etage)
            elif entity.dxftype() in ("TEXT", "MTEXT"):
                self._process_text(entity, kategorie, analyse, etage)
        
        return analyse
    
    def _analyze_ifc(self, model, analyse: BrandschutzAnalyse, etage: str) -> BrandschutzAnalyse:
        """Analysiert IFC-Modell."""
        try:
            # IfcFireSuppressionTerminal (Löscheinrichtungen)
            for element in model.by_type("IfcFireSuppressionTerminal"):
                einrichtung = Brandschutzeinrichtung(
                    typ=element.Name or "Feuerlöscheinrichtung",
                    kategorie=BrandschutzKategorie.FEUERLOESCHER.value,
                    etage=etage,
                )
                analyse.einrichtungen.append(einrichtung)
            
            # IfcSensor (Melder)
            for element in model.by_type("IfcSensor"):
                name = (element.Name or "").lower()
                if "smoke" in name or "rauch" in name:
                    kat = BrandschutzKategorie.RAUCHMELDER
                elif "heat" in name or "wärme" in name:
                    kat = BrandschutzKategorie.WAERMEMELDER
                else:
                    kat = BrandschutzKategorie.BRANDMELDER
                
                einrichtung = Brandschutzeinrichtung(
                    typ=element.Name or "Melder",
                    kategorie=kat.value,
                    etage=etage,
                )
                analyse.einrichtungen.append(einrichtung)
            
            # IfcDoor mit Brandschutz-Properties
            for door in model.by_type("IfcDoor"):
                name = (door.Name or "").lower()
                for pattern, fw in self.FEUERWIDERSTAND_PATTERNS:
                    if re.search(pattern, name, re.IGNORECASE):
                        einrichtung = Brandschutzeinrichtung(
                            typ=f"Brandschutztür {fw.value}",
                            kategorie=BrandschutzKategorie.BRANDSCHUTZTUR.value,
                            etage=etage,
                        )
                        analyse.einrichtungen.append(einrichtung)
                        break
            
            # IfcSpace für Ex-Zonen
            for space in model.by_type("IfcSpace"):
                name = (space.Name or "").lower()
                for pattern, zone in self.EX_ZONE_PATTERNS:
                    if re.search(pattern, name, re.IGNORECASE):
                        ex_bereich = ExBereich(
                            name=space.Name or "Ex-Bereich",
                            zone=zone.value,
                            etage=etage,
                        )
                        analyse.ex_bereiche.append(ex_bereich)
                        break
                        
        except Exception as e:
            logger.warning(f"[{self.name}] IFC-Analyse Fehler: {e}")
        
        return analyse
    
    def _classify_layer(self, layer_name: str) -> Optional[BrandschutzKategorie]:
        """Klassifiziert Layer nach Brandschutz-Kategorie."""
        layer_lower = layer_name.lower()
        
        for kategorie, keywords in self.LAYER_KEYWORDS.items():
            for keyword in keywords:
                if keyword in layer_lower:
                    return kategorie
        
        return None
    
    def _process_polyline(self, entity, kategorie: BrandschutzKategorie, analyse: BrandschutzAnalyse, etage: str):
        """Verarbeitet Polylinien (Fluchtwege, Brandabschnitte, Ex-Zonen)."""
        try:
            points = list(entity.get_points())
            if len(points) < 2:
                return
            
            # Länge berechnen
            length = sum(
                ((points[i+1][0] - points[i][0])**2 + (points[i+1][1] - points[i][1])**2)**0.5
                for i in range(len(points) - 1)
            )
            
            # Fläche berechnen (falls geschlossen)
            area = 0.0
            if entity.is_closed:
                area = abs(sum(
                    (points[i][0] * points[(i+1) % len(points)][1] - 
                     points[(i+1) % len(points)][0] * points[i][1])
                    for i in range(len(points))
                ) / 2.0)
            
            layer_name = entity.dxf.layer
            
            if kategorie == BrandschutzKategorie.FLUCHTWEG:
                fluchtweg = Fluchtweg(
                    name=layer_name,
                    laenge_m=length / 1000 if length > 100 else length,  # mm → m
                    layer=layer_name,
                    etage=etage,
                    max_laenge_ok=length < 35000,  # 35m max nach ASR A2.3
                )
                analyse.fluchtwege.append(fluchtweg)
                
            elif kategorie in (BrandschutzKategorie.BRANDABSCHNITT, BrandschutzKategorie.BRANDWAND):
                fw = self._detect_feuerwiderstand(layer_name)
                brandabschnitt = Brandabschnitt(
                    name=layer_name,
                    flaeche_m2=area / 1000000 if area > 10000 else area,  # mm² → m²
                    feuerwiderstand=fw.value,
                    layer=layer_name,
                    etage=etage,
                )
                analyse.brandabschnitte.append(brandabschnitt)
                
            elif kategorie == BrandschutzKategorie.EX_ZONE:
                zone = self._detect_ex_zone(layer_name)
                ex_bereich = ExBereich(
                    name=layer_name,
                    zone=zone.value,
                    flaeche_m2=area / 1000000 if area > 10000 else area,
                    layer=layer_name,
                )
                analyse.ex_bereiche.append(ex_bereich)
                
        except Exception as e:
            logger.debug(f"[{self.name}] Polyline-Fehler: {e}")
    
    def _process_block(self, entity, kategorie: BrandschutzKategorie, analyse: BrandschutzAnalyse, etage: str):
        """Verarbeitet Block-Referenzen (Symbole für Melder, Löscher, etc.)."""
        try:
            block_name = entity.dxf.name
            insert_point = entity.dxf.insert
            
            einrichtung = Brandschutzeinrichtung(
                typ=block_name,
                kategorie=kategorie.value,
                position_x=insert_point[0],
                position_y=insert_point[1],
                layer=entity.dxf.layer,
                etage=etage,
                block_name=block_name,
            )
            analyse.einrichtungen.append(einrichtung)
            
        except Exception as e:
            logger.debug(f"[{self.name}] Block-Fehler: {e}")
    
    def _process_line(self, entity, kategorie: BrandschutzKategorie, analyse: BrandschutzAnalyse, etage: str):
        """Verarbeitet Linien (z.B. Fluchtwege als einzelne Linien)."""
        try:
            start = entity.dxf.start
            end = entity.dxf.end
            length = ((end[0] - start[0])**2 + (end[1] - start[1])**2)**0.5
            
            if kategorie == BrandschutzKategorie.FLUCHTWEG:
                fluchtweg = Fluchtweg(
                    name=entity.dxf.layer,
                    laenge_m=length / 1000 if length > 100 else length,
                    layer=entity.dxf.layer,
                    etage=etage,
                )
                analyse.fluchtwege.append(fluchtweg)
                
        except Exception as e:
            logger.debug(f"[{self.name}] Line-Fehler: {e}")
    
    def _process_text(self, entity, kategorie: BrandschutzKategorie, analyse: BrandschutzAnalyse, etage: str):
        """Verarbeitet Text-Elemente für zusätzliche Informationen."""
        try:
            text = entity.dxf.text if hasattr(entity.dxf, 'text') else ""
            
            # Feuerwiderstand aus Text extrahieren
            fw = self._detect_feuerwiderstand(text)
            if fw != Feuerwiderstand.UNBEKANNT:
                # Prüfen ob schon ein Brandabschnitt mit diesem Layer existiert
                for ba in analyse.brandabschnitte:
                    if ba.feuerwiderstand == Feuerwiderstand.UNBEKANNT.value:
                        ba.feuerwiderstand = fw.value
                        break
                        
        except Exception as e:
            logger.debug(f"[{self.name}] Text-Fehler: {e}")
    
    def _detect_feuerwiderstand(self, text: str) -> Feuerwiderstand:
        """Erkennt Feuerwiderstandsklasse aus Text."""
        for pattern, fw in self.FEUERWIDERSTAND_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return fw
        return Feuerwiderstand.UNBEKANNT
    
    def _detect_ex_zone(self, text: str) -> ExZone:
        """Erkennt Ex-Zone aus Text."""
        for pattern, zone in self.EX_ZONE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return zone
        return ExZone.KEINE
    
    def _perform_checks(self, analyse: BrandschutzAnalyse) -> BrandschutzAnalyse:
        """Führt Prüfungen durch und generiert Warnungen/Mängel."""
        
        # Fluchtweg-Prüfung (max 35m nach ASR A2.3)
        for fluchtweg in analyse.fluchtwege:
            if fluchtweg.laenge_m > 35:
                analyse.maengel.append(
                    f"Fluchtweg '{fluchtweg.name}' überschreitet 35m ({fluchtweg.laenge_m:.1f}m)"
                )
            elif fluchtweg.laenge_m > 30:
                analyse.warnungen.append(
                    f"Fluchtweg '{fluchtweg.name}' nähert sich 35m-Grenze ({fluchtweg.laenge_m:.1f}m)"
                )
        
        # Ex-Zonen-Prüfung
        for ex in analyse.ex_bereiche:
            if ex.zone in (ExZone.ZONE_0.value, ExZone.ZONE_20.value):
                analyse.warnungen.append(
                    f"Kritische Ex-Zone gefunden: {ex.name} ({ex.zone})"
                )
        
        # Brandabschnitte ohne Feuerwiderstand
        for ba in analyse.brandabschnitte:
            if ba.feuerwiderstand == Feuerwiderstand.UNBEKANNT.value:
                analyse.warnungen.append(
                    f"Brandabschnitt '{ba.name}' ohne Feuerwiderstandsklasse"
                )
        
        return analyse
    
    def _calculate_summary(self, analyse: BrandschutzAnalyse) -> BrandschutzAnalyse:
        """Berechnet Zusammenfassung."""
        
        # Einrichtungen zählen
        for einrichtung in analyse.einrichtungen:
            kat = einrichtung.kategorie
            if kat == BrandschutzKategorie.NOTAUSGANG.value:
                analyse.anzahl_notausgaenge += 1
            elif kat == BrandschutzKategorie.FEUERLOESCHER.value:
                analyse.anzahl_feuerloescher += 1
            elif kat == BrandschutzKategorie.RAUCHMELDER.value:
                analyse.anzahl_rauchmelder += 1
            elif kat == BrandschutzKategorie.SPRINKLER.value:
                analyse.anzahl_sprinkler += 1
        
        # Ex-Flächen summieren
        analyse.gesamtflaeche_ex_m2 = sum(ex.flaeche_m2 for ex in analyse.ex_bereiche)
        
        return analyse


# Singleton für einfachen Zugriff
_brandschutz_handler: Optional[BrandschutzHandler] = None

def get_brandschutz_handler() -> BrandschutzHandler:
    """Gibt BrandschutzHandler-Instanz zurück."""
    global _brandschutz_handler
    if _brandschutz_handler is None:
        _brandschutz_handler = BrandschutzHandler()
    return _brandschutz_handler
