"""BFA CAD MCP Server - Tools für Explosionsschutz-Analyse.

Dieser Server stellt CAD-Verarbeitung und Ex-Schutz Tools via MCP bereit.
Kann standalone oder als Teil des Agents SDK verwendet werden.

Starten:
    python -m bfa_agent.mcp_server.server
    
Oder via FastMCP CLI:
    fastmcp run bfa_agent/mcp_server/server.py
"""

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from pathlib import Path
import json

# FastMCP Server erstellen
mcp = FastMCP(
    name="bfa-cad-server",
    version="0.1.0",
    description="MCP Server für Explosionsschutz CAD-Analyse"
)


# ============================================================
# Pydantic Models für strukturierte Responses
# ============================================================

class RoomData(BaseModel):
    """Raumdaten aus CAD-Datei."""
    name: str
    volume_m3: float
    area_m2: float
    height_m: float
    layer: str | None = None


class EquipmentData(BaseModel):
    """Equipment-Daten aus CAD-Datei."""
    name: str
    room: str
    equipment_type: str
    ex_marking: str | None = None


class CADFileResult(BaseModel):
    """Ergebnis des CAD-Parsings."""
    file_path: str
    format: str
    rooms: list[RoomData]
    equipment: list[EquipmentData]
    layers: list[str]


class ZoneCalculation(BaseModel):
    """Ergebnis einer Zonenberechnung."""
    zone_volume_m3: float
    zone_radius_m: float
    zone_height_m: float
    calculation_method: str
    parameters_used: dict


class EquipmentSuitability(BaseModel):
    """Ergebnis einer Eignungsprüfung."""
    equipment_name: str
    ex_marking: str
    target_zone: str
    is_suitable: bool
    category_found: str | None
    category_required: list[str]
    issues: list[str]


# ============================================================
# MCP Tools
# ============================================================

@mcp.tool()
def read_cad_file(file_path: str) -> CADFileResult:
    """Liest eine CAD-Datei (DXF, IFC, STEP) und extrahiert Daten.
    
    Args:
        file_path: Pfad zur CAD-Datei
        
    Returns:
        Strukturierte CAD-Daten mit Räumen, Equipment und Layern
    """
    path = Path(file_path)
    
    if not path.exists():
        # Demo-Daten wenn Datei nicht existiert
        return CADFileResult(
            file_path=str(path),
            format=path.suffix.upper().lstrip(".") or "UNKNOWN",
            rooms=[
                RoomData(
                    name="Lackierkabine 1",
                    volume_m3=450.0,
                    area_m2=150.0,
                    height_m=3.0,
                    layer="EX_ZONE_1"
                ),
                RoomData(
                    name="Mischraum",
                    volume_m3=80.0,
                    area_m2=40.0,
                    height_m=2.0,
                    layer="EX_ZONE_2"
                ),
                RoomData(
                    name="Lagerraum Lösemittel",
                    volume_m3=120.0,
                    area_m2=60.0,
                    height_m=2.0,
                    layer="EX_ZONE_1"
                )
            ],
            equipment=[
                EquipmentData(
                    name="Spritzpistole SP-01",
                    room="Lackierkabine 1",
                    equipment_type="Sprühgerät",
                    ex_marking="II 2G Ex h IIB T4"
                ),
                EquipmentData(
                    name="Mischbehälter MB-01",
                    room="Mischraum",
                    equipment_type="Behälter",
                    ex_marking=None
                ),
                EquipmentData(
                    name="Absauganlage AA-01",
                    room="Lackierkabine 1",
                    equipment_type="Lüftung",
                    ex_marking="II 2G Ex d IIB T4"
                ),
                EquipmentData(
                    name="Pumpe P-01",
                    room="Lagerraum Lösemittel",
                    equipment_type="Pumpe",
                    ex_marking="II 2G Ex d IIC T3"
                )
            ],
            layers=["EX_ZONE_0", "EX_ZONE_1", "EX_ZONE_2", "EQUIPMENT", "VENTILATION"]
        )
    
    # TODO: Echte CAD-Parser Integration
    # from bfa_agent.cad import read_cad_file as parse_cad
    # return parse_cad(path)
    
    return CADFileResult(
        file_path=str(path),
        format=path.suffix.upper().lstrip("."),
        rooms=[],
        equipment=[],
        layers=[]
    )


@mcp.tool()
def calculate_zone_extent(
    release_rate_kg_s: float,
    ventilation_rate_m3_s: float,
    release_velocity_m_s: float = 0.5,
    lel_vol_percent: float = 1.5,
    safety_factor: float = 5.0
) -> ZoneCalculation:
    """Berechnet Ex-Zonen Ausdehnung nach TRGS 721.
    
    Args:
        release_rate_kg_s: Freisetzungsrate in kg/s
        ventilation_rate_m3_s: Luftvolumenstrom in m³/s
        release_velocity_m_s: Austrittsgeschwindigkeit in m/s
        lel_vol_percent: Untere Explosionsgrenze in Vol-%
        safety_factor: Sicherheitsfaktor (default 5.0)
        
    Returns:
        Berechnete Zonenausdehnung mit Parametern
    """
    import math
    
    # Berechnung nach TRGS 721 Anhang 1
    # Hypothetisches Volumen V_z
    if ventilation_rate_m3_s > 0:
        # Mit Lüftung: V_z = Q_g / (k * LEL * n_v)
        k = 0.25  # Mischungsfaktor
        lel_fraction = lel_vol_percent / 100
        
        v_z = (release_rate_kg_s * safety_factor) / (k * lel_fraction * ventilation_rate_m3_s)
        
        # Kugelförmige Zone annehmen
        radius = (3 * v_z / (4 * math.pi)) ** (1/3)
        
        # Höhe basierend auf Dampfdichte (vereinfacht)
        height = radius * 0.5  # Flache Zone bei schweren Dämpfen
        
    else:
        # Ohne Lüftung: Zone dehnt sich aus
        v_z = float('inf')
        radius = float('inf')
        height = float('inf')
    
    return ZoneCalculation(
        zone_volume_m3=round(v_z, 2) if v_z != float('inf') else -1,
        zone_radius_m=round(radius, 2) if radius != float('inf') else -1,
        zone_height_m=round(height, 2) if height != float('inf') else -1,
        calculation_method="TRGS 721 Anhang 1 - Hypothetisches Volumen",
        parameters_used={
            "release_rate_kg_s": release_rate_kg_s,
            "ventilation_rate_m3_s": ventilation_rate_m3_s,
            "release_velocity_m_s": release_velocity_m_s,
            "lel_vol_percent": lel_vol_percent,
            "safety_factor": safety_factor
        }
    )


@mcp.tool()
def check_equipment_for_zone(
    ex_marking: str,
    zone: str
) -> EquipmentSuitability:
    """Prüft ob Equipment für eine Ex-Zone geeignet ist.
    
    Args:
        ex_marking: Ex-Kennzeichnung (z.B. "II 2G Ex d IIB T4")
        zone: Zielzone (z.B. "Zone 1", "Zone 21")
        
    Returns:
        Eignungsprüfung mit Details
    """
    # Anforderungen nach ATEX/IECEx
    zone_requirements = {
        "Zone 0": ["1G"],
        "Zone 1": ["1G", "2G"],
        "Zone 2": ["1G", "2G", "3G"],
        "Zone 20": ["1D"],
        "Zone 21": ["1D", "2D"],
        "Zone 22": ["1D", "2D", "3D"],
    }
    
    zone_key = zone.replace("zone", "Zone").replace("  ", " ").strip()
    required = zone_requirements.get(zone_key, [])
    
    if not required:
        return EquipmentSuitability(
            equipment_name="Unknown",
            ex_marking=ex_marking,
            target_zone=zone,
            is_suitable=False,
            category_found=None,
            category_required=[],
            issues=[f"Unbekannte Zone: {zone}"]
        )
    
    # Kategorie aus Marking extrahieren
    marking_upper = ex_marking.upper()
    found_category = None
    
    for cat in ["1G", "2G", "3G", "1D", "2D", "3D"]:
        if cat in marking_upper:
            found_category = cat
            break
    
    issues = []
    is_suitable = False
    
    if found_category is None:
        issues.append("Keine Gerätekategorie in Kennzeichnung erkannt")
    elif found_category in required:
        is_suitable = True
    else:
        issues.append(
            f"Kategorie {found_category} nicht für {zone_key} zugelassen. "
            f"Erforderlich: {', '.join(required)}"
        )
    
    # Zusätzliche Prüfungen
    if "EX D" in marking_upper or "EX E" in marking_upper:
        pass  # Druckfeste/Erhöhte Sicherheit OK
    elif "EX N" in marking_upper and zone_key not in ["Zone 2", "Zone 22"]:
        issues.append("Zündschutzart 'n' nur für Zone 2/22 zugelassen")
    
    return EquipmentSuitability(
        equipment_name="Equipment",
        ex_marking=ex_marking,
        target_zone=zone_key,
        is_suitable=is_suitable,
        category_found=found_category,
        category_required=required,
        issues=issues
    )


@mcp.tool()
def get_substance_data(substance_name: str) -> dict:
    """Ruft Stoffdaten für Ex-Schutz Beurteilung ab.
    
    Args:
        substance_name: Name des Stoffes (deutsch oder englisch)
        
    Returns:
        Sicherheitsrelevante Stoffeigenschaften
    """
    # Stoffdatenbank (vereinfacht)
    substances = {
        "aceton": {
            "name_de": "Aceton",
            "name_en": "Acetone",
            "cas": "67-64-1",
            "flash_point_c": -18,
            "boiling_point_c": 56,
            "lel_vol_percent": 2.5,
            "uel_vol_percent": 13.0,
            "explosion_group": "IIA",
            "temperature_class": "T1",
            "ignition_temp_c": 535,
            "vapor_density_air": 2.0,
            "molar_mass_g_mol": 58.08,
            "hazard_statements": ["H225", "H319", "H336"],
            "ghs_pictograms": ["GHS02", "GHS07"]
        },
        "ethanol": {
            "name_de": "Ethanol",
            "name_en": "Ethanol",
            "cas": "64-17-5",
            "flash_point_c": 12,
            "boiling_point_c": 78,
            "lel_vol_percent": 3.1,
            "uel_vol_percent": 27.7,
            "explosion_group": "IIB",
            "temperature_class": "T2",
            "ignition_temp_c": 425,
            "vapor_density_air": 1.6,
            "molar_mass_g_mol": 46.07,
            "hazard_statements": ["H225", "H319"],
            "ghs_pictograms": ["GHS02"]
        },
        "wasserstoff": {
            "name_de": "Wasserstoff",
            "name_en": "Hydrogen",
            "cas": "1333-74-0",
            "flash_point_c": None,  # Gas
            "boiling_point_c": -253,
            "lel_vol_percent": 4.0,
            "uel_vol_percent": 77.0,
            "explosion_group": "IIC",
            "temperature_class": "T1",
            "ignition_temp_c": 560,
            "vapor_density_air": 0.07,
            "molar_mass_g_mol": 2.016,
            "hazard_statements": ["H220"],
            "ghs_pictograms": ["GHS02"]
        },
        "methan": {
            "name_de": "Methan",
            "name_en": "Methane",
            "cas": "74-82-8",
            "flash_point_c": None,  # Gas
            "boiling_point_c": -161,
            "lel_vol_percent": 4.4,
            "uel_vol_percent": 17.0,
            "explosion_group": "IIA",
            "temperature_class": "T1",
            "ignition_temp_c": 595,
            "vapor_density_air": 0.55,
            "molar_mass_g_mol": 16.04,
            "hazard_statements": ["H220"],
            "ghs_pictograms": ["GHS02"]
        },
        "toluol": {
            "name_de": "Toluol",
            "name_en": "Toluene",
            "cas": "108-88-3",
            "flash_point_c": 4,
            "boiling_point_c": 111,
            "lel_vol_percent": 1.1,
            "uel_vol_percent": 7.1,
            "explosion_group": "IIA",
            "temperature_class": "T1",
            "ignition_temp_c": 535,
            "vapor_density_air": 3.2,
            "molar_mass_g_mol": 92.14,
            "hazard_statements": ["H225", "H304", "H315", "H336", "H361d", "H373"],
            "ghs_pictograms": ["GHS02", "GHS07", "GHS08"]
        }
    }
    
    # Normalisierte Suche
    key = substance_name.lower().replace(" ", "").replace("-", "")
    
    # Direkte Suche
    if key in substances:
        return substances[key]
    
    # Suche in Namen
    for k, data in substances.items():
        if (key in data["name_de"].lower() or 
            key in data["name_en"].lower() or
            key in data.get("cas", "")):
            return data
    
    return {
        "error": f"Stoff '{substance_name}' nicht gefunden",
        "available_substances": list(substances.keys()),
        "hint": "Verfügbar: Aceton, Ethanol, Wasserstoff, Methan, Toluol"
    }


@mcp.tool()
def analyze_ventilation(
    room_volume_m3: float,
    air_changes_per_hour: float,
    ventilation_type: str = "technisch"
) -> dict:
    """Analysiert Lüftungseffektivität nach TRGS 722.
    
    Args:
        room_volume_m3: Raumvolumen in m³
        air_changes_per_hour: Luftwechselrate pro Stunde
        ventilation_type: "natürlich", "technisch" oder "keine"
        
    Returns:
        Bewertung der Lüftung mit Empfehlungen
    """
    air_flow_m3_h = room_volume_m3 * air_changes_per_hour
    
    # Effektivitätsbewertung nach TRGS 722
    if ventilation_type == "technisch":
        if air_changes_per_hour >= 12:
            effectiveness = "hoch"
            availability = "gut"
            zone_reduction = True
        elif air_changes_per_hour >= 6:
            effectiveness = "mittel"
            availability = "ausreichend"
            zone_reduction = True
        else:
            effectiveness = "gering"
            availability = "unzureichend"
            zone_reduction = False
    elif ventilation_type == "natürlich":
        if air_changes_per_hour >= 3:
            effectiveness = "mittel"
            availability = "eingeschränkt"
            zone_reduction = False
        else:
            effectiveness = "gering"
            availability = "unzureichend"
            zone_reduction = False
    else:
        effectiveness = "keine"
        availability = "keine"
        zone_reduction = False
    
    recommendations = []
    if not zone_reduction:
        recommendations.append("Technische Lüftung mit ≥12 Luftwechseln/h installieren")
    if ventilation_type == "natürlich":
        recommendations.append("Übergang auf technische Lüftung prüfen")
    if air_changes_per_hour < 6:
        recommendations.append("Luftwechselrate erhöhen")
    
    return {
        "room_volume_m3": room_volume_m3,
        "air_changes_per_hour": air_changes_per_hour,
        "air_flow_m3_h": round(air_flow_m3_h, 1),
        "ventilation_type": ventilation_type,
        "effectiveness": effectiveness,
        "availability": availability,
        "zone_reduction_possible": zone_reduction,
        "recommendations": recommendations,
        "norm_reference": "TRGS 722 Abschnitt 4.3"
    }


# ============================================================
# MCP Resources (optional)
# ============================================================

@mcp.resource("bfa://substances")
def get_all_substances() -> str:
    """Liste aller verfügbaren Stoffe in der Datenbank."""
    return json.dumps({
        "substances": ["Aceton", "Ethanol", "Wasserstoff", "Methan", "Toluol"],
        "description": "Verwende get_substance_data(name) für Details"
    })


@mcp.resource("bfa://zone-requirements")
def get_zone_requirements() -> str:
    """Übersicht der Zonenanforderungen."""
    return json.dumps({
        "gas_zones": {
            "Zone 0": "Ständig oder langzeitig g.e.A. - Kategorie 1G",
            "Zone 1": "Gelegentlich im Normalbetrieb - Kategorie 1G oder 2G",
            "Zone 2": "Selten und kurzzeitig - Kategorie 1G, 2G oder 3G"
        },
        "dust_zones": {
            "Zone 20": "Ständig oder langzeitig g.e.A. - Kategorie 1D",
            "Zone 21": "Gelegentlich im Normalbetrieb - Kategorie 1D oder 2D",
            "Zone 22": "Selten und kurzzeitig - Kategorie 1D, 2D oder 3D"
        },
        "norm_reference": "ATEX 2014/34/EU, IECEx"
    })


# ============================================================
# Server starten
# ============================================================

if __name__ == "__main__":
    mcp.run()
