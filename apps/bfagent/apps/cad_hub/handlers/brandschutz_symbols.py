"""
Brandschutz Symbol Insertion Handler.

Analysiert Pläne und fügt fehlende Brandschutz-Symbole ein:
- Feuerlöscher (max 20m Laufweg nach ASR A2.2)
- Rauchmelder (max 60m² pro Melder)
- Fluchtwegschilder (an Richtungswechseln)
- Notausgang-Symbole
- Sammelplatz-Symbole

Regelwerke:
- ASR A2.2 (Feuerlöscher)
- ASR A2.3 (Fluchtwege)
- DIN 14675 (Brandmeldeanlagen)
- DIN EN ISO 7010 (Sicherheitskennzeichen)
"""
import math
import logging
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional
from pathlib import Path

from .base import (
    BaseCADHandler,
    CADHandlerResult,
    HandlerStatus,
)

logger = logging.getLogger(__name__)


class SymbolTyp(Enum):
    """Brandschutz-Symboltypen nach DIN EN ISO 7010."""
    # Rettungszeichen (grün)
    NOTAUSGANG = "E001"           # Notausgang
    NOTAUSGANG_LINKS = "E001-L"   # Notausgang links
    NOTAUSGANG_RECHTS = "E001-R"  # Notausgang rechts
    SAMMELSTELLE = "E007"         # Sammelstelle
    ERSTE_HILFE = "E003"          # Erste Hilfe
    
    # Brandschutzzeichen (rot)
    FEUERLOESCHER = "F001"        # Feuerlöscher
    LOESCHDECKE = "F002"          # Löschdecke
    FEUERLEITER = "F003"          # Feuerleiter
    BRANDMELDER = "F005"          # Brandmelder
    WANDHYDRANT = "F002"          # Löschschlauch
    
    # Warnzeichen (gelb)
    WARNUNG_FEUER = "W021"        # Feuergefährliche Stoffe
    WARNUNG_EX = "W021"           # Explosionsgefahr
    
    # Sonstige
    RAUCHMELDER = "RM"            # Rauchmelder (kein ISO)
    SPRINKLER = "SP"              # Sprinkler
    RWA = "RWA"                   # Rauch-Wärme-Abzug
    FLUCHTWEG_PFEIL = "FW"        # Fluchtweg-Richtungspfeil


@dataclass
class PlatzierungsRegel:
    """Regel für Symbol-Platzierung."""
    symbol_typ: SymbolTyp
    max_abstand_m: float = 0.0      # Max Abstand zwischen Symbolen
    max_flaeche_m2: float = 0.0     # Max Fläche pro Symbol
    min_anzahl: int = 0              # Mindestanzahl
    an_tueren: bool = False          # An Türen platzieren
    an_fluchtwegen: bool = False     # Entlang Fluchtwegen
    an_richtungswechsel: bool = False  # Bei Richtungswechseln
    regelwerk: str = ""


@dataclass
class SymbolPlatzierung:
    """Vorgeschlagene Symbol-Platzierung."""
    symbol_typ: str
    position_x: float
    position_y: float
    rotation: float = 0.0
    layer: str = "Brandschutz_Symbole"
    begruendung: str = ""
    prioritaet: int = 1  # 1=kritisch, 2=empfohlen, 3=optional
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SymbolInsertionResult:
    """Ergebnis der Symbol-Analyse und -Einfügung."""
    vorgeschlagene_symbole: list[SymbolPlatzierung] = field(default_factory=list)
    eingefuegte_symbole: list[SymbolPlatzierung] = field(default_factory=list)
    warnungen: list[str] = field(default_factory=list)
    
    # Statistik
    feuerloescher_fehlen: int = 0
    rauchmelder_fehlen: int = 0
    fluchtweg_schilder_fehlen: int = 0
    
    def to_dict(self) -> dict:
        return {
            "vorgeschlagene_symbole": [s.to_dict() for s in self.vorgeschlagene_symbole],
            "eingefuegte_symbole": [s.to_dict() for s in self.eingefuegte_symbole],
            "warnungen": self.warnungen,
            "statistik": {
                "feuerloescher_fehlen": self.feuerloescher_fehlen,
                "rauchmelder_fehlen": self.rauchmelder_fehlen,
                "fluchtweg_schilder_fehlen": self.fluchtweg_schilder_fehlen,
                "gesamt_vorgeschlagen": len(self.vorgeschlagene_symbole),
                "gesamt_eingefuegt": len(self.eingefuegte_symbole),
            }
        }


class BrandschutzSymbolHandler(BaseCADHandler):
    """
    Handler für automatische Brandschutz-Symbol-Platzierung.
    
    Funktionen:
    1. Analyse: Identifiziert fehlende Symbole basierend auf Regelwerken
    2. Vorschlag: Berechnet optimale Positionen
    3. Einfügung: Fügt Symbole in DXF ein (optional)
    
    Regelwerke:
    - ASR A2.2: Feuerlöscher alle 20m Laufweg
    - DIN 14675: Rauchmelder max 60m² / 7.5m Abstand
    - ASR A2.3: Fluchtwegschilder an Richtungswechseln
    
    Input:
        loader: ezdxf-Dokument
        format: "dxf"
        modus: "analyse" | "vorschlag" | "einfuegen"
        grundflaeche_m2: Gesamtfläche (für Berechnung)
        symbol_bibliothek: Pfad zu Symbol-Blöcken
    
    Output:
        symbole: SymbolInsertionResult mit Vorschlägen/eingefügten Symbolen
    """
    
    name = "BrandschutzSymbolHandler"
    description = "Analysiert und fügt Brandschutz-Symbole ein"
    required_inputs = ["loader"]
    optional_inputs = ["format", "modus", "grundflaeche_m2", "symbol_bibliothek", "etage"]
    
    # Platzierungsregeln nach Vorschriften
    REGELN = {
        SymbolTyp.FEUERLOESCHER: PlatzierungsRegel(
            symbol_typ=SymbolTyp.FEUERLOESCHER,
            max_abstand_m=20.0,  # ASR A2.2: max 20m Laufweg
            regelwerk="ASR A2.2",
        ),
        SymbolTyp.RAUCHMELDER: PlatzierungsRegel(
            symbol_typ=SymbolTyp.RAUCHMELDER,
            max_flaeche_m2=60.0,  # ca. 60m² pro Melder
            max_abstand_m=7.5,    # max 7.5m Abstand untereinander
            regelwerk="DIN 14675",
        ),
        SymbolTyp.NOTAUSGANG: PlatzierungsRegel(
            symbol_typ=SymbolTyp.NOTAUSGANG,
            an_tueren=True,
            an_fluchtwegen=True,
            regelwerk="ASR A2.3",
        ),
        SymbolTyp.FLUCHTWEG_PFEIL: PlatzierungsRegel(
            symbol_typ=SymbolTyp.FLUCHTWEG_PFEIL,
            an_richtungswechsel=True,
            max_abstand_m=25.0,  # Sichtweite
            regelwerk="ASR A2.3 / ASR A1.3",
        ),
        SymbolTyp.BRANDMELDER: PlatzierungsRegel(
            symbol_typ=SymbolTyp.BRANDMELDER,
            an_fluchtwegen=True,
            max_abstand_m=30.0,
            regelwerk="DIN 14675",
        ),
    }
    
    # Standard-Block-Namen für Symbole
    BLOCK_NAMEN = {
        SymbolTyp.FEUERLOESCHER: "BS_Feuerloescher",
        SymbolTyp.RAUCHMELDER: "BS_Rauchmelder",
        SymbolTyp.NOTAUSGANG: "BS_Notausgang",
        SymbolTyp.NOTAUSGANG_LINKS: "BS_Notausgang_L",
        SymbolTyp.NOTAUSGANG_RECHTS: "BS_Notausgang_R",
        SymbolTyp.FLUCHTWEG_PFEIL: "BS_Fluchtweg",
        SymbolTyp.BRANDMELDER: "BS_Brandmelder",
        SymbolTyp.SAMMELSTELLE: "BS_Sammelstelle",
        SymbolTyp.WANDHYDRANT: "BS_Wandhydrant",
        SymbolTyp.SPRINKLER: "BS_Sprinkler",
    }
    
    def execute(self, input_data: dict) -> CADHandlerResult:
        """Führt Symbol-Analyse und optional Einfügung durch."""
        result = CADHandlerResult(
            success=True,
            handler_name=self.name,
            status=HandlerStatus.RUNNING,
        )
        
        loader = input_data.get("loader")
        modus = input_data.get("modus", "vorschlag")  # analyse, vorschlag, einfuegen
        grundflaeche_m2 = input_data.get("grundflaeche_m2", 0)
        etage = input_data.get("etage", "EG")
        
        if not loader:
            result.add_error("Kein CAD-Dokument (loader) übergeben")
            return result
        
        symbol_result = SymbolInsertionResult()
        
        try:
            # 1. Bestehende Symbole und Geometrie analysieren
            bestehende_symbole = self._find_existing_symbols(loader)
            raeume = self._find_rooms(loader)
            fluchtwege = self._find_fluchtwege(loader)
            tueren = self._find_doors(loader)
            
            # Grundfläche berechnen falls nicht angegeben
            if grundflaeche_m2 == 0:
                grundflaeche_m2 = sum(r.get("flaeche", 0) for r in raeume)
            
            logger.info(f"[{self.name}] Analyse: {len(raeume)} Räume, {grundflaeche_m2:.0f}m², "
                       f"{len(bestehende_symbole)} bestehende Symbole")
            
            # 2. Fehlende Symbole berechnen
            symbol_result = self._calculate_missing_symbols(
                symbol_result, bestehende_symbole, raeume, 
                fluchtwege, tueren, grundflaeche_m2
            )
            
            # 3. Symbole einfügen (nur im Modus "einfuegen")
            if modus == "einfuegen" and symbol_result.vorgeschlagene_symbole:
                symbol_result = self._insert_symbols(loader, symbol_result)
                result.data["modified"] = True
            else:
                result.data["modified"] = False
            
        except Exception as e:
            result.add_error(f"Analyse-Fehler: {e}")
            logger.exception(f"[{self.name}] Fehler bei Symbol-Analyse")
            return result
        
        # Ergebnis
        result.data["symbole"] = symbol_result.to_dict()
        result.data["modus"] = modus
        result.data["grundflaeche_m2"] = grundflaeche_m2
        
        result.status = HandlerStatus.SUCCESS
        logger.info(f"[{self.name}] {len(symbol_result.vorgeschlagene_symbole)} Symbole vorgeschlagen, "
                   f"{len(symbol_result.eingefuegte_symbole)} eingefügt")
        
        return result
    
    def _find_existing_symbols(self, doc) -> list[dict]:
        """Findet bestehende Brandschutz-Symbole."""
        symbols = []
        msp = doc.modelspace()
        
        # Block-Referenzen durchsuchen
        for entity in msp.query("INSERT"):
            block_name = entity.dxf.name.lower()
            
            # Bekannte Brandschutz-Blöcke
            if any(kw in block_name for kw in [
                "feuer", "lösch", "rauch", "melder", "notaus", 
                "flucht", "brand", "hydrant", "sprinkler", "rwa"
            ]):
                symbols.append({
                    "name": entity.dxf.name,
                    "x": entity.dxf.insert[0],
                    "y": entity.dxf.insert[1],
                    "layer": entity.dxf.layer,
                })
        
        return symbols
    
    def _find_rooms(self, doc) -> list[dict]:
        """Findet Räume als geschlossene Polylinien."""
        rooms = []
        msp = doc.modelspace()
        
        for entity in msp.query("LWPOLYLINE"):
            if not entity.is_closed:
                continue
            
            points = list(entity.get_points())
            if len(points) < 3:
                continue
            
            # Fläche berechnen
            area = abs(sum(
                (points[i][0] * points[(i+1) % len(points)][1] - 
                 points[(i+1) % len(points)][0] * points[i][1])
                for i in range(len(points))
            ) / 2.0)
            
            # Schwerpunkt berechnen
            cx = sum(p[0] for p in points) / len(points)
            cy = sum(p[1] for p in points) / len(points)
            
            # Bounding Box
            min_x = min(p[0] for p in points)
            max_x = max(p[0] for p in points)
            min_y = min(p[1] for p in points)
            max_y = max(p[1] for p in points)
            
            # Einheiten: mm → m² (wenn Fläche > 1000000, dann mm²)
            if area > 1000000:
                area = area / 1000000
            
            if area > 5:  # Mindestens 5m² für Raum
                rooms.append({
                    "flaeche": area,
                    "zentrum_x": cx,
                    "zentrum_y": cy,
                    "min_x": min_x,
                    "max_x": max_x,
                    "min_y": min_y,
                    "max_y": max_y,
                    "layer": entity.dxf.layer,
                })
        
        return rooms
    
    def _find_fluchtwege(self, doc) -> list[dict]:
        """Findet Fluchtwege."""
        fluchtwege = []
        msp = doc.modelspace()
        
        for entity in msp:
            layer = entity.dxf.layer.lower() if hasattr(entity.dxf, 'layer') else ""
            
            if any(kw in layer for kw in ["flucht", "rettung", "escape"]):
                if entity.dxftype() == "LWPOLYLINE":
                    points = list(entity.get_points())
                    fluchtwege.append({
                        "points": points,
                        "layer": entity.dxf.layer,
                    })
                elif entity.dxftype() == "LINE":
                    fluchtwege.append({
                        "points": [(entity.dxf.start[0], entity.dxf.start[1]),
                                   (entity.dxf.end[0], entity.dxf.end[1])],
                        "layer": entity.dxf.layer,
                    })
        
        return fluchtwege
    
    def _find_doors(self, doc) -> list[dict]:
        """Findet Türen."""
        doors = []
        msp = doc.modelspace()
        
        for entity in msp.query("INSERT"):
            block_name = entity.dxf.name.lower()
            
            if any(kw in block_name for kw in ["tür", "door", "tuer", "eingang", "ausgang"]):
                doors.append({
                    "name": entity.dxf.name,
                    "x": entity.dxf.insert[0],
                    "y": entity.dxf.insert[1],
                    "rotation": entity.dxf.rotation if hasattr(entity.dxf, 'rotation') else 0,
                })
        
        return doors
    
    def _calculate_missing_symbols(
        self, 
        symbol_result: SymbolInsertionResult,
        bestehende: list[dict],
        raeume: list[dict],
        fluchtwege: list[dict],
        tueren: list[dict],
        grundflaeche_m2: float
    ) -> SymbolInsertionResult:
        """Berechnet fehlende Symbole basierend auf Regeln."""
        
        # 1. FEUERLÖSCHER (ASR A2.2: max 20m Laufweg)
        # Vereinfacht: 1 pro 200m² oder pro Raum
        bestehende_fl = [s for s in bestehende if "feuer" in s["name"].lower() or "lösch" in s["name"].lower()]
        
        if grundflaeche_m2 > 0:
            benoetigte_fl = max(1, int(grundflaeche_m2 / 200))
            fehlende_fl = benoetigte_fl - len(bestehende_fl)
            
            if fehlende_fl > 0:
                symbol_result.feuerloescher_fehlen = fehlende_fl
                
                # Positionen berechnen (in größten Räumen ohne FL)
                raeume_sorted = sorted(raeume, key=lambda r: r["flaeche"], reverse=True)
                
                for i, raum in enumerate(raeume_sorted[:fehlende_fl]):
                    symbol_result.vorgeschlagene_symbole.append(SymbolPlatzierung(
                        symbol_typ=SymbolTyp.FEUERLOESCHER.value,
                        position_x=raum["zentrum_x"],
                        position_y=raum["zentrum_y"],
                        layer="Brandschutz_Feuerloescher",
                        begruendung=f"ASR A2.2: Feuerlöscher für {raum['flaeche']:.0f}m² Raum",
                        prioritaet=1,
                    ))
        
        # 2. RAUCHMELDER (DIN 14675: ca. 60m² pro Melder)
        bestehende_rm = [s for s in bestehende if "rauch" in s["name"].lower() or "melder" in s["name"].lower()]
        
        if grundflaeche_m2 > 0:
            benoetigte_rm = max(1, int(grundflaeche_m2 / 60))
            fehlende_rm = benoetigte_rm - len(bestehende_rm)
            
            if fehlende_rm > 0:
                symbol_result.rauchmelder_fehlen = fehlende_rm
                
                # In jedem Raum > 10m² ohne Melder
                for raum in raeume:
                    if raum["flaeche"] > 10:
                        # Prüfen ob schon Melder im Raum
                        hat_melder = any(
                            raum["min_x"] <= rm["x"] <= raum["max_x"] and
                            raum["min_y"] <= rm["y"] <= raum["max_y"]
                            for rm in bestehende_rm
                        )
                        
                        if not hat_melder:
                            symbol_result.vorgeschlagene_symbole.append(SymbolPlatzierung(
                                symbol_typ=SymbolTyp.RAUCHMELDER.value,
                                position_x=raum["zentrum_x"],
                                position_y=raum["zentrum_y"],
                                layer="Brandschutz_Rauchmelder",
                                begruendung=f"DIN 14675: Rauchmelder für {raum['flaeche']:.0f}m² Raum",
                                prioritaet=2,
                            ))
        
        # 3. FLUCHTWEG-SCHILDER (ASR A2.3: an Richtungswechseln)
        bestehende_fw = [s for s in bestehende if "flucht" in s["name"].lower() or "notaus" in s["name"].lower()]
        
        for fluchtweg in fluchtwege:
            points = fluchtweg.get("points", [])
            
            # An Richtungswechseln (Ecken) Schilder vorschlagen
            for i in range(1, len(points) - 1):
                p0, p1, p2 = points[i-1], points[i], points[i+1]
                
                # Winkel berechnen
                angle1 = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
                angle2 = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
                angle_diff = abs(angle2 - angle1)
                
                # Bei Richtungswechsel > 30°
                if angle_diff > 0.5:  # ca. 30°
                    # Prüfen ob schon Schild in der Nähe
                    hat_schild = any(
                        math.sqrt((fw["x"] - p1[0])**2 + (fw["y"] - p1[1])**2) < 2000  # 2m
                        for fw in bestehende_fw
                    )
                    
                    if not hat_schild:
                        symbol_result.fluchtweg_schilder_fehlen += 1
                        symbol_result.vorgeschlagene_symbole.append(SymbolPlatzierung(
                            symbol_typ=SymbolTyp.FLUCHTWEG_PFEIL.value,
                            position_x=p1[0],
                            position_y=p1[1],
                            rotation=math.degrees(angle2),
                            layer="Brandschutz_Fluchtweg",
                            begruendung="ASR A2.3: Richtungsschild an Fluchtweg-Richtungswechsel",
                            prioritaet=1,
                        ))
        
        # 4. NOTAUSGANG-SCHILDER (an Ausgangstüren)
        for tuer in tueren:
            name = tuer["name"].lower()
            
            if any(kw in name for kw in ["notaus", "ausgang", "exit", "flucht"]):
                # Prüfen ob schon Schild
                hat_schild = any(
                    math.sqrt((fw["x"] - tuer["x"])**2 + (fw["y"] - tuer["y"])**2) < 1000
                    for fw in bestehende_fw
                )
                
                if not hat_schild:
                    symbol_result.vorgeschlagene_symbole.append(SymbolPlatzierung(
                        symbol_typ=SymbolTyp.NOTAUSGANG.value,
                        position_x=tuer["x"],
                        position_y=tuer["y"] + 500,  # Über der Tür
                        layer="Brandschutz_Fluchtweg",
                        begruendung="ASR A2.3: Notausgang-Kennzeichnung über Ausgangstür",
                        prioritaet=1,
                    ))
        
        return symbol_result
    
    def _insert_symbols(self, doc, symbol_result: SymbolInsertionResult) -> SymbolInsertionResult:
        """Fügt vorgeschlagene Symbole in DXF ein."""
        msp = doc.modelspace()
        
        # Brandschutz-Layer erstellen falls nicht vorhanden
        layer_namen = ["Brandschutz_Symbole", "Brandschutz_Feuerloescher", 
                       "Brandschutz_Rauchmelder", "Brandschutz_Fluchtweg"]
        
        for layer_name in layer_namen:
            if layer_name not in doc.layers:
                doc.layers.new(name=layer_name, dxfattribs={"color": 1})  # Rot
        
        for symbol in symbol_result.vorgeschlagene_symbole:
            try:
                # Block-Name ermitteln
                block_name = self._get_block_name(symbol.symbol_typ)
                
                # Block erstellen falls nicht vorhanden
                if block_name not in doc.blocks:
                    self._create_symbol_block(doc, block_name, symbol.symbol_typ)
                
                # Block-Referenz einfügen
                msp.add_blockref(
                    block_name,
                    insert=(symbol.position_x, symbol.position_y),
                    dxfattribs={
                        "layer": symbol.layer,
                        "rotation": symbol.rotation,
                    }
                )
                
                symbol_result.eingefuegte_symbole.append(symbol)
                logger.debug(f"[{self.name}] Symbol eingefügt: {block_name} at ({symbol.position_x}, {symbol.position_y})")
                
            except Exception as e:
                symbol_result.warnungen.append(f"Konnte {symbol.symbol_typ} nicht einfügen: {e}")
        
        return symbol_result
    
    def _get_block_name(self, symbol_typ: str) -> str:
        """Ermittelt Block-Namen für Symbol-Typ."""
        for typ, name in self.BLOCK_NAMEN.items():
            if typ.value == symbol_typ:
                return name
        return f"BS_{symbol_typ}"
    
    def _create_symbol_block(self, doc, block_name: str, symbol_typ: str):
        """Erstellt einfachen Platzhalter-Block für Symbol."""
        block = doc.blocks.new(name=block_name)
        
        # Einfaches Symbol als Kreis mit Text
        if "feuer" in block_name.lower() or symbol_typ == SymbolTyp.FEUERLOESCHER.value:
            # Roter Kreis mit F
            block.add_circle(center=(0, 0), radius=200, dxfattribs={"color": 1})
            block.add_text("F", dxfattribs={"height": 200, "color": 1}).set_placement((0, -100))
            
        elif "rauch" in block_name.lower() or symbol_typ == SymbolTyp.RAUCHMELDER.value:
            # Blauer Kreis mit RM
            block.add_circle(center=(0, 0), radius=150, dxfattribs={"color": 5})
            block.add_text("RM", dxfattribs={"height": 100, "color": 5}).set_placement((-100, -50))
            
        elif "notaus" in block_name.lower() or symbol_typ == SymbolTyp.NOTAUSGANG.value:
            # Grünes Rechteck mit Pfeil
            block.add_lwpolyline(
                [(-200, -100), (200, -100), (200, 100), (-200, 100)],
                close=True,
                dxfattribs={"color": 3}
            )
            block.add_line((-100, 0), (100, 0), dxfattribs={"color": 3})
            block.add_line((50, 50), (100, 0), dxfattribs={"color": 3})
            block.add_line((50, -50), (100, 0), dxfattribs={"color": 3})
            
        elif "flucht" in block_name.lower() or symbol_typ == SymbolTyp.FLUCHTWEG_PFEIL.value:
            # Grüner Pfeil
            block.add_line((-150, 0), (150, 0), dxfattribs={"color": 3})
            block.add_line((100, 50), (150, 0), dxfattribs={"color": 3})
            block.add_line((100, -50), (150, 0), dxfattribs={"color": 3})
            
        else:
            # Standard: Kreis mit Typ-Kürzel
            block.add_circle(center=(0, 0), radius=150, dxfattribs={"color": 7})
            block.add_text(symbol_typ[:2], dxfattribs={"height": 100}).set_placement((-50, -50))


# Singleton
_symbol_handler: Optional[BrandschutzSymbolHandler] = None

def get_brandschutz_symbol_handler() -> BrandschutzSymbolHandler:
    """Gibt BrandschutzSymbolHandler-Instanz zurück."""
    global _symbol_handler
    if _symbol_handler is None:
        _symbol_handler = BrandschutzSymbolHandler()
    return _symbol_handler
