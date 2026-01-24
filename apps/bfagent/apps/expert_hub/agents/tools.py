"""
BFA Agent Tools - Echte Implementierungen für Explosionsschutz

Phase 1: Stoffdaten + Zonenberechnung (implementiert)
Phase 2: Equipment-Prüfung (implementiert)
Phase 3: CAD-Integration (Stub mit Basislogik)
"""

import math
import os
from typing import Optional
from .schemas import SubstanceProperties


# ============================================================================
# STOFFDATENBANK (Phase 1 - Echte Daten)
# ============================================================================

SUBSTANCE_DATABASE = {
    # Lösungsmittel
    "aceton": SubstanceProperties(
        name="Aceton",
        cas_number="67-64-1",
        lower_explosion_limit=2.5,
        upper_explosion_limit=13.0,
        flash_point_c=-17,
        ignition_temperature_c=465,
        temperature_class="T1",
        explosion_group="IIA",
        vapor_density=2.0,
        molar_mass=58.08
    ),
    "ethanol": SubstanceProperties(
        name="Ethanol",
        cas_number="64-17-5",
        lower_explosion_limit=3.1,
        upper_explosion_limit=27.7,
        flash_point_c=12,
        ignition_temperature_c=363,
        temperature_class="T2",
        explosion_group="IIB",
        vapor_density=1.6,
        molar_mass=46.07
    ),
    "methanol": SubstanceProperties(
        name="Methanol",
        cas_number="67-56-1",
        lower_explosion_limit=6.0,
        upper_explosion_limit=36.0,
        flash_point_c=11,
        ignition_temperature_c=440,
        temperature_class="T2",
        explosion_group="IIA",
        vapor_density=1.1,
        molar_mass=32.04
    ),
    "toluol": SubstanceProperties(
        name="Toluol",
        cas_number="108-88-3",
        lower_explosion_limit=1.1,
        upper_explosion_limit=7.1,
        flash_point_c=4,
        ignition_temperature_c=480,
        temperature_class="T1",
        explosion_group="IIA",
        vapor_density=3.2,
        molar_mass=92.14
    ),
    "xylol": SubstanceProperties(
        name="Xylol",
        cas_number="1330-20-7",
        lower_explosion_limit=1.0,
        upper_explosion_limit=7.0,
        flash_point_c=25,
        ignition_temperature_c=463,
        temperature_class="T1",
        explosion_group="IIA",
        vapor_density=3.7,
        molar_mass=106.17
    ),
    "benzin": SubstanceProperties(
        name="Benzin (Ottokraftstoff)",
        cas_number="86290-81-5",
        lower_explosion_limit=0.6,
        upper_explosion_limit=8.0,
        flash_point_c=-40,
        ignition_temperature_c=220,
        temperature_class="T3",
        explosion_group="IIA",
        vapor_density=3.5,
        molar_mass=100.0
    ),
    "diesel": SubstanceProperties(
        name="Dieselkraftstoff",
        cas_number="68476-34-6",
        lower_explosion_limit=0.6,
        upper_explosion_limit=6.5,
        flash_point_c=55,
        ignition_temperature_c=220,
        temperature_class="T3",
        explosion_group="IIA",
        vapor_density=4.5,
        molar_mass=200.0
    ),
    "wasserstoff": SubstanceProperties(
        name="Wasserstoff",
        cas_number="1333-74-0",
        lower_explosion_limit=4.0,
        upper_explosion_limit=77.0,
        flash_point_c=None,  # Gas
        ignition_temperature_c=560,
        temperature_class="T1",
        explosion_group="IIC",
        vapor_density=0.07,
        molar_mass=2.02
    ),
    "methan": SubstanceProperties(
        name="Methan (Erdgas)",
        cas_number="74-82-8",
        lower_explosion_limit=4.4,
        upper_explosion_limit=17.0,
        flash_point_c=None,  # Gas
        ignition_temperature_c=595,
        temperature_class="T1",
        explosion_group="IIA",
        vapor_density=0.55,
        molar_mass=16.04
    ),
    "propan": SubstanceProperties(
        name="Propan",
        cas_number="74-98-6",
        lower_explosion_limit=1.7,
        upper_explosion_limit=10.9,
        flash_point_c=None,  # Gas
        ignition_temperature_c=470,
        temperature_class="T1",
        explosion_group="IIA",
        vapor_density=1.56,
        molar_mass=44.10
    ),
    "isopropanol": SubstanceProperties(
        name="Isopropanol (2-Propanol)",
        cas_number="67-63-0",
        lower_explosion_limit=2.0,
        upper_explosion_limit=12.7,
        flash_point_c=12,
        ignition_temperature_c=399,
        temperature_class="T2",
        explosion_group="IIA",
        vapor_density=2.1,
        molar_mass=60.10
    ),
    "butanol": SubstanceProperties(
        name="n-Butanol",
        cas_number="71-36-3",
        lower_explosion_limit=1.4,
        upper_explosion_limit=11.2,
        flash_point_c=29,
        ignition_temperature_c=343,
        temperature_class="T2",
        explosion_group="IIA",
        vapor_density=2.6,
        molar_mass=74.12
    ),
    "ethylacetat": SubstanceProperties(
        name="Ethylacetat",
        cas_number="141-78-6",
        lower_explosion_limit=2.0,
        upper_explosion_limit=11.5,
        flash_point_c=-4,
        ignition_temperature_c=426,
        temperature_class="T1",
        explosion_group="IIA",
        vapor_density=3.0,
        molar_mass=88.11
    ),
}


def get_substance_properties(substance_name: str) -> dict:
    """Holt Stoffeigenschaften aus der Datenbank.
    
    Args:
        substance_name: Name des Stoffes (deutsch oder englisch)
        
    Returns:
        Dict mit Stoffeigenschaften oder Fehlermeldung
    """
    # Normalisieren
    key = substance_name.lower().strip()
    
    # Aliase
    aliases = {
        "acetone": "aceton",
        "toluene": "toluol",
        "xylene": "xylol",
        "gasoline": "benzin",
        "petrol": "benzin",
        "hydrogen": "wasserstoff",
        "methane": "methan",
        "propane": "propan",
        "2-propanol": "isopropanol",
        "ipa": "isopropanol",
        "n-butanol": "butanol",
        "ethyl acetate": "ethylacetat",
        "erdgas": "methan",
        "natural gas": "methan",
    }
    
    if key in aliases:
        key = aliases[key]
    
    if key in SUBSTANCE_DATABASE:
        substance = SUBSTANCE_DATABASE[key]
        return {
            "success": True,
            "substance": substance.model_dump(),
            "source": "BFA Agent Stoffdatenbank (GESTIS-basiert)"
        }
    
    # Fuzzy search
    matches = [k for k in SUBSTANCE_DATABASE.keys() if key in k or k in key]
    if matches:
        return {
            "success": False,
            "error": f"Stoff '{substance_name}' nicht gefunden",
            "suggestions": matches,
            "hint": "Versuche einen der Vorschläge"
        }
    
    return {
        "success": False,
        "error": f"Stoff '{substance_name}' nicht in Datenbank",
        "available_substances": list(SUBSTANCE_DATABASE.keys())
    }


# ============================================================================
# ZONENBERECHNUNG (Phase 1 - Echte TRGS 721 Berechnung)
# ============================================================================

def calculate_zone_extent(
    release_rate_kg_s: float,
    ventilation_rate_m3_s: float,
    lel_percent: float = 1.5,
    substance_name: Optional[str] = None,
    room_volume_m3: Optional[float] = None,
    release_type: str = "jet"
) -> dict:
    """Berechnet die Zonenausdehnung nach TRGS 721.
    
    Args:
        release_rate_kg_s: Freisetzungsrate in kg/s
        ventilation_rate_m3_s: Luftvolumenstrom in m³/s
        lel_percent: Untere Explosionsgrenze in Vol-% (default 1.5)
        substance_name: Optional - Stoffname für automatische LEL
        room_volume_m3: Optional - Raumvolumen für Verdünnungsberechnung
        release_type: "jet" (Strahl), "pool" (Pfütze), "diffuse" (diffus)
        
    Returns:
        Dict mit berechneter Zonenausdehnung und Klassifizierung
    """
    # Stoffdaten holen wenn angegeben
    if substance_name:
        substance_data = get_substance_properties(substance_name)
        if substance_data.get("success"):
            lel_percent = substance_data["substance"]["lower_explosion_limit"]
    
    # Sicherheitsfaktoren nach TRGS 721
    SAFETY_FACTORS = {
        "jet": 5.0,      # Strahl/Spray
        "pool": 3.0,     # Verdunstung von Oberfläche
        "diffuse": 10.0  # Diffuse Freisetzung
    }
    safety_factor = SAFETY_FACTORS.get(release_type, 5.0)
    
    # Berechnung nach TRGS 721 Anhang 1
    # V_ex = (W / (LEL * ρ)) * SF
    # Vereinfacht: W = Massenstrom, LEL in Vol-%, ρ ≈ Luft
    
    if ventilation_rate_m3_s > 0:
        # Verdünnungsfaktor
        dilution_factor = ventilation_rate_m3_s / (release_rate_kg_s + 0.0001)
        
        # Kritisches Volumen (Vol-% → Anteil)
        lel_fraction = lel_percent / 100.0
        
        # Zonenvolumen
        zone_volume_m3 = (release_rate_kg_s / lel_fraction) * safety_factor
        
        # Zonenradius (Kugel-Approximation)
        zone_radius_m = (zone_volume_m3 * 3 / (4 * math.pi)) ** (1/3)
        
        # Zonenklassifizierung nach TRGS 721
        if dilution_factor >= 1000:
            zone_type = "Zone 2"
            zone_description = "Selten und nur kurzzeitig g.e.A."
        elif dilution_factor >= 100:
            zone_type = "Zone 1"
            zone_description = "Gelegentlich im Normalbetrieb g.e.A."
        else:
            zone_type = "Zone 0"
            zone_description = "Ständig oder langzeitig g.e.A."
            
    else:
        # Keine Lüftung
        zone_volume_m3 = room_volume_m3 if room_volume_m3 else float('inf')
        zone_radius_m = float('inf')
        dilution_factor = 0
        zone_type = "Zone 0"
        zone_description = "Keine Lüftung - gesamter Raum Zone 0"
    
    # Lüftungsbewertung
    if room_volume_m3 and ventilation_rate_m3_s > 0:
        air_changes = (ventilation_rate_m3_s * 3600) / room_volume_m3
        if air_changes >= 12:
            ventilation_class = "gut"
        elif air_changes >= 4:
            ventilation_class = "mittel"
        else:
            ventilation_class = "gering"
    else:
        air_changes = 0
        ventilation_class = "keine"
    
    return {
        "success": True,
        "zone_volume_m3": round(zone_volume_m3, 2) if zone_volume_m3 != float('inf') else "unbegrenzt",
        "zone_radius_m": round(zone_radius_m, 2) if zone_radius_m != float('inf') else "unbegrenzt",
        "dilution_factor": round(dilution_factor, 2),
        "zone_type": zone_type,
        "zone_description": zone_description,
        "ventilation": {
            "air_changes_per_hour": round(air_changes, 1),
            "classification": ventilation_class
        },
        "input_parameters": {
            "release_rate_kg_s": release_rate_kg_s,
            "ventilation_rate_m3_s": ventilation_rate_m3_s,
            "lel_percent": lel_percent,
            "release_type": release_type,
            "safety_factor": safety_factor
        },
        "calculation_basis": "TRGS 721 Anhang 1",
        "note": "Vereinfachte Berechnung - für genaue Analyse CFD-Simulation empfohlen"
    }


# ============================================================================
# EQUIPMENT-PRÜFUNG (Phase 2 - Stub mit Basislogik)
# ============================================================================

def check_equipment_suitability(
    ex_marking: str,
    zone: str
) -> dict:
    """Prüft ob ein Gerät für eine Ex-Zone geeignet ist.
    
    Args:
        ex_marking: Ex-Kennzeichnung (z.B. "II 2G Ex d IIB T4")
        zone: Zielzone (z.B. "Zone 1", "Zone 21")
        
    Returns:
        Dict mit Eignungsprüfung
    """
    # Kategorie-Mapping nach ATEX
    zone_requirements = {
        "Zone 0": {"min_category": "1G", "allowed": ["1G"]},
        "Zone 1": {"min_category": "2G", "allowed": ["1G", "2G"]},
        "Zone 2": {"min_category": "3G", "allowed": ["1G", "2G", "3G"]},
        "Zone 20": {"min_category": "1D", "allowed": ["1D"]},
        "Zone 21": {"min_category": "2D", "allowed": ["1D", "2D"]},
        "Zone 22": {"min_category": "3D", "allowed": ["1D", "2D", "3D"]},
    }
    
    # Normalisieren
    zone_normalized = zone.strip().replace("-", " ").title()
    if zone_normalized not in zone_requirements:
        return {
            "success": False,
            "error": f"Unbekannte Zone: {zone}",
            "valid_zones": list(zone_requirements.keys())
        }
    
    requirements = zone_requirements[zone_normalized]
    
    # Ex-Kennzeichnung parsen
    marking_upper = ex_marking.upper()
    
    # Kategorie extrahieren
    detected_category = None
    for cat in ["1G", "2G", "3G", "1D", "2D", "3D"]:
        if cat in marking_upper:
            detected_category = cat
            break
    
    # Temperaturklasse extrahieren
    temp_class = None
    for tc in ["T6", "T5", "T4", "T3", "T2", "T1"]:
        if tc in marking_upper:
            temp_class = tc
            break
    
    # Explosionsgruppe extrahieren
    exp_group = None
    for eg in ["IIC", "IIB", "IIA"]:
        if eg in marking_upper:
            exp_group = eg
            break
    
    # Eignung prüfen
    is_suitable = detected_category in requirements["allowed"] if detected_category else False
    
    issues = []
    recommendations = []
    
    if not detected_category:
        issues.append("Keine Gerätekategorie in Ex-Kennzeichnung erkannt")
        recommendations.append(f"Kennzeichnung muss eine der Kategorien enthalten: {requirements['allowed']}")
    elif not is_suitable:
        issues.append(f"Kategorie {detected_category} nicht für {zone_normalized} geeignet")
        recommendations.append(f"Erforderlich: Kategorie {requirements['min_category']} oder besser")
    
    if not temp_class:
        issues.append("Keine Temperaturklasse erkannt")
        recommendations.append("Temperaturklasse (T1-T6) muss angegeben sein")
    
    if not exp_group:
        issues.append("Keine Explosionsgruppe erkannt")
        recommendations.append("Explosionsgruppe (IIA/IIB/IIC) muss angegeben sein")
    
    return {
        "success": True,
        "equipment_marking": ex_marking,
        "target_zone": zone_normalized,
        "detected": {
            "category": detected_category,
            "temperature_class": temp_class,
            "explosion_group": exp_group
        },
        "requirements": requirements,
        "is_suitable": is_suitable and len(issues) == 0,
        "issues": issues,
        "recommendations": recommendations,
        "reference": "ATEX Richtlinie 2014/34/EU"
    }


# ============================================================================
# LÜFTUNGSANALYSE (Phase 2)
# ============================================================================

def analyze_ventilation_effectiveness(
    room_volume_m3: float,
    air_flow_m3_h: float,
    ventilation_type: str = "technisch",
    has_ex_zone: bool = True
) -> dict:
    """Analysiert die Lüftungseffektivität nach TRGS 722.
    
    Args:
        room_volume_m3: Raumvolumen in m³
        air_flow_m3_h: Luftvolumenstrom in m³/h
        ventilation_type: "technisch", "natürlich", "keine"
        has_ex_zone: Ob Ex-Zone vorhanden ist
        
    Returns:
        Dict mit Lüftungsanalyse
    """
    # Luftwechselrate berechnen
    air_changes = air_flow_m3_h / room_volume_m3 if room_volume_m3 > 0 else 0
    
    # Bewertung nach TRGS 722
    if ventilation_type == "technisch":
        if air_changes >= 12:
            effectiveness = "hoch"
            can_reduce_zone = True
            recommendation = "Lüftung ausreichend für Zonenreduzierung"
        elif air_changes >= 6:
            effectiveness = "mittel"
            can_reduce_zone = has_ex_zone
            recommendation = "Lüftung begrenzt wirksam - Zonenverkleinerung möglich"
        else:
            effectiveness = "gering"
            can_reduce_zone = False
            recommendation = "Lüftung erhöhen auf mind. 6 LW/h für Zonenverkleinerung"
    elif ventilation_type == "natürlich":
        effectiveness = "variabel"
        can_reduce_zone = False
        recommendation = "Natürliche Lüftung: Keine Anrechnung für Zonenreduzierung nach TRGS 722"
    else:
        effectiveness = "keine"
        can_reduce_zone = False
        recommendation = "Technische Lüftung erforderlich für Ex-Bereiche"
    
    return {
        "success": True,
        "room_volume_m3": room_volume_m3,
        "air_flow_m3_h": air_flow_m3_h,
        "air_changes_per_hour": round(air_changes, 1),
        "ventilation_type": ventilation_type,
        "effectiveness": effectiveness,
        "can_reduce_zone": can_reduce_zone,
        "recommendation": recommendation,
        "reference": "TRGS 722"
    }


# ============================================================================
# CAD-INTEGRATION (Phase 3 - Stub mit Basislogik)
# ============================================================================

# Supported CAD formats
SUPPORTED_CAD_FORMATS = {
    '.dxf': 'AutoCAD DXF',
    '.dwg': 'AutoCAD DWG',
    '.ifc': 'Industry Foundation Classes (BIM)',
    '.step': 'STEP (ISO 10303)',
    '.stp': 'STEP (ISO 10303)',
    '.iges': 'IGES',
    '.igs': 'IGES',
}


def read_cad_file(file_path: str) -> dict:
    """Liest eine CAD-Datei und extrahiert Raum- und Equipment-Daten.
    
    Args:
        file_path: Pfad zur CAD-Datei (DXF, IFC, STEP, etc.)
        
    Returns:
        Dict mit Räumen, Equipment und Metadaten
        
    Note:
        Phase 3 Stub - für echte CAD-Verarbeitung:
        - DXF: ezdxf library
        - IFC: ifcopenshell library
        - STEP: pythonocc-core library
    """
    # Validierung
    if not file_path:
        return {"success": False, "error": "Kein Dateipfad angegeben"}
    
    # Format erkennen
    _, ext = os.path.splitext(file_path.lower())
    
    if ext not in SUPPORTED_CAD_FORMATS:
        return {
            "success": False,
            "error": f"Nicht unterstütztes Format: {ext}",
            "supported_formats": list(SUPPORTED_CAD_FORMATS.keys())
        }
    
    format_name = SUPPORTED_CAD_FORMATS[ext]
    
    # Prüfen ob Datei existiert (wenn lokaler Pfad)
    file_exists = os.path.exists(file_path) if not file_path.startswith(('http://', 'https://')) else None
    
    # TODO: Echte CAD-Parser Integration
    # Für jetzt: Strukturierte Dummy-Daten für Demo/Testing
    
    if ext == '.ifc':
        # IFC-spezifische Struktur (BIM)
        return {
            "success": True,
            "file": file_path,
            "format": format_name,
            "file_exists": file_exists,
            "parser": "ifcopenshell (nicht installiert - Demo-Daten)",
            "building": {
                "name": "Industrieanlage Demo",
                "stories": 2,
                "gross_area_m2": 2500
            },
            "rooms": [
                {
                    "id": "IfcSpace_001",
                    "name": "Lackierkabine 1",
                    "volume_m3": 450,
                    "area_m2": 150,
                    "height_m": 3.0,
                    "story": "EG",
                    "ex_zone_hint": "Zone 1"
                },
                {
                    "id": "IfcSpace_002",
                    "name": "Mischraum",
                    "volume_m3": 80,
                    "area_m2": 40,
                    "height_m": 2.0,
                    "story": "EG",
                    "ex_zone_hint": "Zone 2"
                },
                {
                    "id": "IfcSpace_003",
                    "name": "Lagerraum Lösungsmittel",
                    "volume_m3": 120,
                    "area_m2": 60,
                    "height_m": 2.0,
                    "story": "EG",
                    "ex_zone_hint": "Zone 1"
                }
            ],
            "equipment": [
                {"id": "Eq_001", "name": "Spritzpistole SP-01", "room": "Lackierkabine 1", "type": "Sprühgerät"},
                {"id": "Eq_002", "name": "Mischbehälter MB-01", "room": "Mischraum", "type": "Behälter"},
                {"id": "Eq_003", "name": "Absauganlage AA-01", "room": "Lackierkabine 1", "type": "Lüftung"},
                {"id": "Eq_004", "name": "Pumpe P-01", "room": "Lagerraum Lösungsmittel", "type": "Pumpe"}
            ],
            "ventilation": [
                {"room": "Lackierkabine 1", "type": "technisch", "air_changes": 25, "flow_m3_h": 11250},
                {"room": "Mischraum", "type": "technisch", "air_changes": 10, "flow_m3_h": 800},
                {"room": "Lagerraum Lösungsmittel", "type": "natürlich", "air_changes": 2, "flow_m3_h": 240}
            ],
            "note": "Demo-Daten - für echte IFC-Verarbeitung ifcopenshell installieren"
        }
    
    elif ext == '.dxf':
        # DXF-spezifische Struktur
        return {
            "success": True,
            "file": file_path,
            "format": format_name,
            "file_exists": file_exists,
            "parser": "ezdxf (nicht installiert - Demo-Daten)",
            "layers": [
                "0", "WALLS", "ROOMS", "EQUIPMENT", "EX_ZONE_0", "EX_ZONE_1", "EX_ZONE_2",
                "VENTILATION", "DIMENSIONS"
            ],
            "rooms": [
                {
                    "name": "Raum A",
                    "layer": "ROOMS",
                    "bounding_box": {"x": 0, "y": 0, "width": 10, "height": 15},
                    "area_m2": 150,
                    "ex_zone_layer": "EX_ZONE_1"
                },
                {
                    "name": "Raum B",
                    "layer": "ROOMS",
                    "bounding_box": {"x": 10, "y": 0, "width": 8, "height": 5},
                    "area_m2": 40,
                    "ex_zone_layer": "EX_ZONE_2"
                }
            ],
            "equipment": [
                {"name": "Motor M1", "layer": "EQUIPMENT", "position": {"x": 5, "y": 7}},
                {"name": "Ventilator V1", "layer": "VENTILATION", "position": {"x": 2, "y": 2}}
            ],
            "note": "Demo-Daten - für echte DXF-Verarbeitung ezdxf installieren"
        }
    
    else:
        # Generische STEP/IGES Struktur
        return {
            "success": True,
            "file": file_path,
            "format": format_name,
            "file_exists": file_exists,
            "parser": "pythonocc-core (nicht installiert - Demo-Daten)",
            "geometry": {
                "solids": 15,
                "surfaces": 42,
                "edges": 128
            },
            "components": [
                {"name": "Gehäuse", "type": "enclosure", "volume_m3": 0.5},
                {"name": "Motor", "type": "equipment", "volume_m3": 0.1},
                {"name": "Rohrleitung", "type": "piping", "length_m": 12.5}
            ],
            "note": "Demo-Daten - für echte STEP-Verarbeitung pythonocc-core installieren"
        }


def extract_ex_zones_from_cad(cad_data: dict) -> list[dict]:
    """Extrahiert Ex-Zonen Informationen aus CAD-Daten.
    
    Args:
        cad_data: Output von read_cad_file()
        
    Returns:
        Liste von Räumen mit Ex-Zonen Hinweisen
    """
    if not cad_data.get("success"):
        return []
    
    zones = []
    for room in cad_data.get("rooms", []):
        zone_info = {
            "room_name": room.get("name", "Unbekannt"),
            "volume_m3": room.get("volume_m3"),
            "area_m2": room.get("area_m2"),
        }
        
        # Ex-Zone Hinweis aus verschiedenen Quellen
        if "ex_zone_hint" in room:
            zone_info["suggested_zone"] = room["ex_zone_hint"]
        elif "ex_zone_layer" in room:
            layer = room["ex_zone_layer"]
            if "ZONE_0" in layer or "ZONE_20" in layer:
                zone_info["suggested_zone"] = "Zone 0" if "ZONE_0" in layer else "Zone 20"
            elif "ZONE_1" in layer or "ZONE_21" in layer:
                zone_info["suggested_zone"] = "Zone 1" if "ZONE_1" in layer else "Zone 21"
            elif "ZONE_2" in layer or "ZONE_22" in layer:
                zone_info["suggested_zone"] = "Zone 2" if "ZONE_2" in layer else "Zone 22"
        
        zones.append(zone_info)
    
    return zones


def get_ventilation_from_cad(cad_data: dict) -> list[dict]:
    """Extrahiert Lüftungsinformationen aus CAD-Daten.
    
    Args:
        cad_data: Output von read_cad_file()
        
    Returns:
        Liste von Lüftungsanlagen mit Leistungsdaten
    """
    if not cad_data.get("success"):
        return []
    
    return cad_data.get("ventilation", [])
