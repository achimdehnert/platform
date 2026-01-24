"""BFA Agents mit OpenRouter Preset-Support.

Diese Agents nutzen @preset/ Model-IDs für:
- Fallback-Konfiguration in OpenRouter
- System-Prompts zentral verwaltet
- Model-Wechsel ohne Code-Deployment
- A/B Testing

Presets müssen in OpenRouter UI angelegt werden:
https://openrouter.ai/settings/presets

Oder nutze export_presets_for_openrouter() für die Konfiguration.
"""

from agents import Agent, handoff
from .presets import get_preset_model
from .models import ExZoneClassification, EquipmentCheckResult
from .tools import (
    read_cad_file,
    calculate_zone_extent,
    check_equipment_suitability,
    analyze_ventilation_effectiveness,
    get_substance_properties,
)


# ============================================================
# Preset-basierte Agents (empfohlen für Production)
# ============================================================

cad_reader_preset = Agent(
    name="CAD Reader",
    instructions="""Lese CAD-Dateien und extrahiere relevante Daten.

Aufgaben:
1. Nutze read_cad_file für DXF/IFC/STEP
2. Extrahiere Räume mit Abmessungen
3. Identifiziere Equipment
4. Finde Lüftungseinrichtungen
5. Erkenne Ex-Zonen aus Layer-Namen

Gib strukturierte Zusammenfassung zurück.""",
    model=get_preset_model("bfa-cad"),
    tools=[read_cad_file]
)


zone_analyzer_preset = Agent(
    name="Ex-Zone Analyzer",
    instructions="""Klassifiziere Ex-Zonen nach TRGS 720ff.

Prozess:
1. Identifiziere Freisetzungsquellen
2. Hole Stoffdaten mit get_substance_properties
3. Berechne Zonenausdehnung mit calculate_zone_extent
4. Bewerte Lüftung mit analyze_ventilation_effectiveness
5. Bestimme Zonentyp

Zonenkriterien:
- Zone 0/20: Ständig g.e.A. vorhanden
- Zone 1/21: Gelegentlich im Normalbetrieb
- Zone 2/22: Selten und kurzzeitig

Begründe mit TRGS-Bezug!""",
    model=get_preset_model("bfa-analyzer"),
    tools=[
        calculate_zone_extent,
        analyze_ventilation_effectiveness,
        get_substance_properties
    ],
    output_type=ExZoneClassification
)


equipment_checker_preset = Agent(
    name="Equipment Checker",
    instructions="""Prüfe Betriebsmittel auf Ex-Eignung.

Prüfschritte:
1. Parse Ex-Kennzeichnung
2. Nutze check_equipment_suitability
3. Verifiziere Kategorie für Zone
4. Prüfe Temperaturklasse
5. Bewerte Zündschutzart

Anforderungen:
- Zone 0 → nur 1G
- Zone 1 → 1G oder 2G
- Zone 2 → 1G, 2G oder 3G

Bei Mängeln: Konkrete Empfehlung!""",
    model=get_preset_model("bfa-equipment"),
    tools=[check_equipment_suitability],
    output_type=EquipmentCheckResult
)


report_writer_preset = Agent(
    name="Report Writer",
    instructions="""Erstelle professionelle Ex-Schutz Berichte.

Struktur:
1. Executive Summary
2. Analysierte Bereiche
3. Zoneneinteilung (mit Begründung)
4. Equipment-Bewertung
5. Maßnahmenkatalog (priorisiert)
6. Anhänge (Normverweise)

Stil: Technisch präzise, sachlich, Deutsch.""",
    model=get_preset_model("bfa-report")
)


triage_preset = Agent(
    name="BFA Triage",
    instructions="""Leite Anfragen an Spezialisten weiter.

Routing:
- CAD/Datei/DXF/IFC → CAD Reader
- Zone/ATEX/Klassifizierung → Zone Analyzer
- Equipment/Kennzeichnung/geeignet → Equipment Checker
- Bericht/Report/Dokumentation → Report Writer

Bei Unklarheit: Nachfragen!
Nach Abschluss: Zusammenfassung geben.""",
    model=get_preset_model("bfa-triage"),
    handoffs=[
        handoff(cad_reader_preset, "CAD-Datei analysieren"),
        handoff(zone_analyzer_preset, "Ex-Zone klassifizieren"),
        handoff(equipment_checker_preset, "Equipment prüfen"),
        handoff(report_writer_preset, "Bericht erstellen"),
    ]
)


# ============================================================
# Factory für dynamische Preset-Konfiguration
# ============================================================

def create_agent_with_preset(
    agent_type: str,
    custom_preset: str | None = None,
    direct_model: str | None = None
) -> Agent:
    """Erstellt Agent mit optionalem Preset/Model Override.
    
    Args:
        agent_type: "cad", "analyzer", "equipment", "report", "triage"
        custom_preset: Custom Preset-Slug (z.B. "my-custom-preset")
        direct_model: Direktes Model statt Preset
        
    Returns:
        Konfigurierter Agent
        
    Beispiele:
        # Standard-Preset
        agent = create_agent_with_preset("analyzer")
        
        # Custom Preset
        agent = create_agent_with_preset("analyzer", custom_preset="bfa-budget")
        
        # Direktes Model
        agent = create_agent_with_preset("analyzer", direct_model="openai/gpt-4o")
    """
    configs = {
        "cad": {
            "name": "CAD Reader",
            "preset": "bfa-cad",
            "tools": [read_cad_file],
            "instructions": cad_reader_preset.instructions,
        },
        "analyzer": {
            "name": "Ex-Zone Analyzer",
            "preset": "bfa-analyzer",
            "tools": [
                calculate_zone_extent,
                analyze_ventilation_effectiveness,
                get_substance_properties
            ],
            "output_type": ExZoneClassification,
            "instructions": zone_analyzer_preset.instructions,
        },
        "equipment": {
            "name": "Equipment Checker",
            "preset": "bfa-equipment",
            "tools": [check_equipment_suitability],
            "output_type": EquipmentCheckResult,
            "instructions": equipment_checker_preset.instructions,
        },
        "report": {
            "name": "Report Writer",
            "preset": "bfa-report",
            "tools": [],
            "instructions": report_writer_preset.instructions,
        },
        "triage": {
            "name": "BFA Triage",
            "preset": "bfa-triage",
            "tools": [],
            "instructions": triage_preset.instructions,
        },
    }
    
    if agent_type not in configs:
        available = ", ".join(configs.keys())
        raise ValueError(f"Unknown agent_type: {agent_type}. Available: {available}")
    
    cfg = configs[agent_type]
    
    # Model bestimmen
    if direct_model:
        model = direct_model
    elif custom_preset:
        model = f"@preset/{custom_preset}"
    else:
        model = get_preset_model(cfg["preset"])
    
    # Agent erstellen
    kwargs = {
        "name": cfg["name"],
        "instructions": cfg["instructions"],
        "model": model,
    }
    
    if cfg.get("tools"):
        kwargs["tools"] = cfg["tools"]
    
    if cfg.get("output_type"):
        kwargs["output_type"] = cfg["output_type"]
    
    return Agent(**kwargs)


# ============================================================
# Exports
# ============================================================

__all__ = [
    # Preset-basierte Agents
    "cad_reader_preset",
    "zone_analyzer_preset",
    "equipment_checker_preset",
    "report_writer_preset",
    "triage_preset",
    # Factory
    "create_agent_with_preset",
]
