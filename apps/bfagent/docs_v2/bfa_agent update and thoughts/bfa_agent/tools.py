"""BFA Agent Tools - Funktionen die von Agents aufgerufen werden."""

from agents import function_tool


@function_tool
def read_cad_file(file_path: str) -> dict:
    """Liest eine CAD-Datei und extrahiert Raum- und Equipment-Daten.
    
    Args:
        file_path: Pfad zur CAD-Datei (DXF, IFC, STEP)
        
    Returns:
        Dict mit Räumen, Equipment und Metadaten
    """
    # TODO: Echte CAD-Reader Integration (aus bfa_cad Package)
    # Hier Dummy-Daten für Demonstration
    return {
        "file": file_path,
        "format": "IFC" if file_path.endswith(".ifc") else "DXF",
        "rooms": [
            {
                "name": "Lackierkabine 1",
                "volume_m3": 450,
                "area_m2": 150,
                "height_m": 3.0,
                "layer": "EX_ZONE_1"
            },
            {
                "name": "Mischraum",
                "volume_m3": 80,
                "area_m2": 40,
                "height_m": 2.0,
                "layer": "EX_ZONE_2"
            }
        ],
        "equipment": [
            {"name": "Spritzpistole SP-01", "room": "Lackierkabine 1", "type": "Sprühgerät"},
            {"name": "Mischbehälter MB-01", "room": "Mischraum", "type": "Behälter"},
            {"name": "Absauganlage AA-01", "room": "Lackierkabine 1", "type": "Lüftung"}
        ],
        "ventilation": [
            {"room": "Lackierkabine 1", "type": "technisch", "air_changes": 25},
            {"room": "Mischraum", "type": "natürlich", "air_changes": 2}
        ]
    }


@function_tool
def calculate_zone_extent(
    release_rate_kg_s: float,
    ventilation_rate_m3_s: float,
    lel_percent: float = 1.5
) -> dict:
    """Berechnet die Zonenausdehnung nach TRGS 720/721.
    
    Args:
        release_rate_kg_s: Freisetzungsrate in kg/s
        ventilation_rate_m3_s: Luftvolumenstrom in m³/s  
        lel_percent: Untere Explosionsgrenze in Vol-%
        
    Returns:
        Dict mit berechneter Zonenausdehnung
    """
    # Vereinfachte Berechnung nach TRGS 721
    # V_ex = (release_rate / LEL) * safety_factor
    safety_factor = 5.0
    
    if ventilation_rate_m3_s > 0:
        dilution_factor = ventilation_rate_m3_s / (release_rate_kg_s + 0.001)
        zone_volume_m3 = (release_rate_kg_s / (lel_percent / 100)) * safety_factor
        zone_radius_m = (zone_volume_m3 * 3 / (4 * 3.14159)) ** (1/3)
    else:
        zone_volume_m3 = float('inf')
        zone_radius_m = float('inf')
    
    return {
        "zone_volume_m3": round(zone_volume_m3, 2),
        "zone_radius_m": round(zone_radius_m, 2),
        "dilution_factor": round(dilution_factor, 2) if ventilation_rate_m3_s > 0 else 0,
        "calculation_basis": "TRGS 721 Anhang 1"
    }


@function_tool
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
        "Zone 0": {"required": ["1G"], "description": "Kategorie 1G erforderlich"},
        "Zone 1": {"required": ["1G", "2G"], "description": "Kategorie 1G oder 2G erforderlich"},
        "Zone 2": {"required": ["1G", "2G", "3G"], "description": "Kategorie 1G, 2G oder 3G"},
        "Zone 20": {"required": ["1D"], "description": "Kategorie 1D erforderlich"},
        "Zone 21": {"required": ["1D", "2D"], "description": "Kategorie 1D oder 2D erforderlich"},
        "Zone 22": {"required": ["1D", "2D", "3D"], "description": "Kategorie 1D, 2D oder 3D"},
    }
    
    req = zone_requirements.get(zone)
    if not req:
        return {"error": f"Unbekannte Zone: {zone}"}
    
    # Parse Ex-Marking
    marking_upper = ex_marking.upper()
    
    # Kategorie extrahieren
    found_category = None
    for cat in ["1G", "2G", "3G", "1D", "2D", "3D"]:
        if cat in marking_upper:
            found_category = cat
            break
    
    is_suitable = found_category in req["required"] if found_category else False
    
    issues = []
    if not found_category:
        issues.append("Keine erkennbare Gerätekategorie in der Kennzeichnung")
    elif not is_suitable:
        issues.append(f"Kategorie {found_category} nicht für {zone} zugelassen")
    
    # Temperaturklasse prüfen (vereinfacht)
    temp_classes = ["T1", "T2", "T3", "T4", "T5", "T6"]
    found_temp = None
    for tc in temp_classes:
        if tc in marking_upper:
            found_temp = tc
            break
    
    return {
        "ex_marking": ex_marking,
        "zone": zone,
        "found_category": found_category,
        "found_temp_class": found_temp,
        "required_categories": req["required"],
        "is_suitable": is_suitable,
        "issues": issues,
        "recommendation": "Geeignet" if is_suitable else "Nicht geeignet - Austausch erforderlich"
    }


@function_tool
def analyze_ventilation_effectiveness(
    room_volume_m3: float,
    air_changes_per_hour: float,
    ventilation_type: str
) -> dict:
    """Bewertet die Lüftungseffektivität nach TRGS 722.
    
    Args:
        room_volume_m3: Raumvolumen in m³
        air_changes_per_hour: Luftwechselrate pro Stunde
        ventilation_type: "natürlich", "technisch" oder "keine"
        
    Returns:
        Dict mit Bewertung der Lüftungseffektivität
    """
    # Bewertung nach TRGS 722
    air_flow_m3_h = room_volume_m3 * air_changes_per_hour
    
    # Effektivitätsfaktor
    if ventilation_type == "technisch":
        if air_changes_per_hour >= 12:
            effectiveness = "hoch"
            factor = 0.5
        elif air_changes_per_hour >= 6:
            effectiveness = "mittel"
            factor = 1.0
        else:
            effectiveness = "gering"
            factor = 2.0
    elif ventilation_type == "natürlich":
        if air_changes_per_hour >= 3:
            effectiveness = "mittel"
            factor = 1.5
        else:
            effectiveness = "gering"
            factor = 3.0
    else:
        effectiveness = "keine"
        factor = 5.0
    
    # Zone-Reduktion möglich?
    zone_reduction_possible = effectiveness in ["hoch", "mittel"]
    
    return {
        "room_volume_m3": room_volume_m3,
        "air_changes_per_hour": air_changes_per_hour,
        "air_flow_m3_h": round(air_flow_m3_h, 1),
        "ventilation_type": ventilation_type,
        "effectiveness": effectiveness,
        "effectiveness_factor": factor,
        "zone_reduction_possible": zone_reduction_possible,
        "recommendation": (
            "Zonenverkleinerung durch Lüftung möglich" 
            if zone_reduction_possible 
            else "Lüftung verbessern für Zonenreduzierung"
        ),
        "basis": "TRGS 722 Abschnitt 4.3"
    }


@function_tool
def get_substance_properties(substance_name: str) -> dict:
    """Ruft sicherheitsrelevante Stoffdaten ab.
    
    Args:
        substance_name: Name des Stoffes (z.B. "Aceton", "Ethanol")
        
    Returns:
        Dict mit Stoffeigenschaften
    """
    # Vereinfachte Stoffdatenbank
    substances = {
        "aceton": {
            "name": "Aceton",
            "cas": "67-64-1",
            "flash_point_c": -18,
            "lel_percent": 2.5,
            "uel_percent": 13.0,
            "explosion_group": "IIA",
            "temp_class": "T1",
            "vapor_density": 2.0,
            "classification": "Flammable Liquid Cat. 2"
        },
        "ethanol": {
            "name": "Ethanol",
            "cas": "64-17-5",
            "flash_point_c": 12,
            "lel_percent": 3.1,
            "uel_percent": 27.7,
            "explosion_group": "IIB",
            "temp_class": "T2",
            "vapor_density": 1.6,
            "classification": "Flammable Liquid Cat. 2"
        },
        "wasserstoff": {
            "name": "Wasserstoff",
            "cas": "1333-74-0",
            "flash_point_c": -273,  # Gas
            "lel_percent": 4.0,
            "uel_percent": 77.0,
            "explosion_group": "IIC",
            "temp_class": "T1",
            "vapor_density": 0.07,
            "classification": "Flammable Gas Cat. 1"
        }
    }
    
    key = substance_name.lower().replace(" ", "")
    data = substances.get(key)
    
    if not data:
        return {
            "error": f"Stoff '{substance_name}' nicht in Datenbank",
            "available": list(substances.keys())
        }
    
    return data
