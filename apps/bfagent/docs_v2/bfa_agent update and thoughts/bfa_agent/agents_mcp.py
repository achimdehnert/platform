"""BFA Agent Definitionen mit MCP Server Support.

Dieser Modul definiert Agents die sowohl:
- Function Tools (direkt eingebettet)
- MCP Server Tools (via MCPServerStdio)

nutzen können.
"""

from agents import Agent, handoff
from agents.mcp import MCPServerStdio
from pathlib import Path

from .config import Models
from .models import ExZoneClassification, EquipmentCheckResult, VentilationAnalysis
from .tools import (
    read_cad_file,
    calculate_zone_extent,
    check_equipment_suitability,
    analyze_ventilation_effectiveness,
    get_substance_properties,
)


def get_bfa_mcp_server() -> MCPServerStdio:
    """Erstellt den BFA MCP Server."""
    server_path = Path(__file__).parent / "mcp_server" / "server.py"
    return MCPServerStdio(
        name="bfa-cad",
        command="python",
        args=[str(server_path)]
    )


# ============================================================
# Agents MIT MCP Server (empfohlen für Production)
# ============================================================

def create_cad_reader_agent(use_mcp: bool = True) -> Agent:
    """Erstellt CAD Reader Agent.
    
    Args:
        use_mcp: True für MCP Server, False für Function Tools
    """
    if use_mcp:
        return Agent(
            name="CAD Reader (MCP)",
            instructions="""Du bist spezialisiert auf das Lesen von CAD-Dateien.

Nutze die MCP Tools:
- read_cad_file: Liest DXF/IFC/STEP Dateien
- get_substance_data: Holt Stoffeigenschaften

Extrahiere:
1. Alle Räume mit Abmessungen
2. Equipment und Positionen
3. Lüftungsinformationen
4. Layer-Informationen für Ex-Zonen

Gib strukturierte Zusammenfassung zurück.""",
            model=Models.FAST,
            mcp_servers=[get_bfa_mcp_server()]
        )
    else:
        return Agent(
            name="CAD Reader",
            instructions="""Du bist spezialisiert auf das Lesen von CAD-Dateien.
Nutze read_cad_file für DXF/IFC/STEP Dateien.""",
            model=Models.FAST,
            tools=[read_cad_file]
        )


def create_zone_analyzer_agent(use_mcp: bool = True) -> Agent:
    """Erstellt Zone Analyzer Agent.
    
    Args:
        use_mcp: True für MCP Server, False für Function Tools
    """
    base_instructions = """Du bist ein Experte für Ex-Zonen Klassifizierung nach TRGS 720ff.

Klassifizierungs-Prozess:
1. Identifiziere Freisetzungsquellen
2. Hole Stoffdaten (LEL, Explosionsgruppe, Temperaturklasse)
3. Berechne Zonenausdehnung
4. Bewerte Lüftungseffektivität
5. Bestimme finale Zonenklassifizierung

Zonentypen:
- Zone 0/20: Ständig oder langzeitig g.e.A.
- Zone 1/21: Gelegentlich im Normalbetrieb
- Zone 2/22: Selten und nur kurzzeitig

Begründe JEDE Klassifizierung mit Normbezug (TRGS 720, 721, 722)."""

    if use_mcp:
        return Agent(
            name="Ex-Zone Analyzer (MCP)",
            instructions=base_instructions + """

Nutze MCP Tools:
- calculate_zone_extent: Zonenberechnung
- analyze_ventilation: Lüftungsbewertung
- get_substance_data: Stoffeigenschaften""",
            model=Models.PRECISE,
            mcp_servers=[get_bfa_mcp_server()],
            output_type=ExZoneClassification
        )
    else:
        return Agent(
            name="Ex-Zone Analyzer",
            instructions=base_instructions,
            model=Models.PRECISE,
            tools=[
                calculate_zone_extent,
                analyze_ventilation_effectiveness,
                get_substance_properties
            ],
            output_type=ExZoneClassification
        )


def create_equipment_checker_agent(use_mcp: bool = True) -> Agent:
    """Erstellt Equipment Checker Agent.
    
    Args:
        use_mcp: True für MCP Server, False für Function Tools
    """
    base_instructions = """Du prüfst Betriebsmittel auf Ex-Schutz Eignung.

Prüfkriterien:
1. Gerätekategorie passend zur Zone?
2. Explosionsgruppe kompatibel?
3. Temperaturklasse ausreichend?
4. Zündschutzart geeignet?

Kategorien-Anforderungen:
- Zone 0: nur 1G
- Zone 1: 1G oder 2G
- Zone 2: 1G, 2G oder 3G
(analog für Staub mit D statt G)

Bei Mängeln: Konkrete Handlungsempfehlung!"""

    if use_mcp:
        return Agent(
            name="Equipment Checker (MCP)",
            instructions=base_instructions + """

Nutze MCP Tool:
- check_equipment_for_zone: Prüft Eignung""",
            model=Models.PRECISE,
            mcp_servers=[get_bfa_mcp_server()],
            output_type=EquipmentCheckResult
        )
    else:
        return Agent(
            name="Equipment Checker",
            instructions=base_instructions,
            model=Models.PRECISE,
            tools=[check_equipment_suitability],
            output_type=EquipmentCheckResult
        )


def create_report_writer_agent() -> Agent:
    """Erstellt Report Writer Agent (immer ohne MCP)."""
    return Agent(
        name="Report Writer",
        instructions="""Du erstellst professionelle Explosionsschutz-Berichte.

Struktur:
1. **Zusammenfassung** - Executive Summary
2. **Analysierte Bereiche** - Räume mit Klassifizierung
3. **Zoneneinteilung** - Detaillierte Begründung
4. **Equipment-Bewertung** - Eignungsprüfung
5. **Maßnahmenkatalog** - Priorisiert nach Dringlichkeit
6. **Normverweise** - TRGS, ATEX, IECEx

Stil: Technisch präzise, sachlich, mit konkreten Maßnahmen.""",
        model=Models.CREATIVE
    )


def create_triage_agent(use_mcp: bool = True) -> Agent:
    """Erstellt Triage Agent mit allen Handoffs.
    
    Args:
        use_mcp: True für MCP-basierte Sub-Agents
    """
    cad_agent = create_cad_reader_agent(use_mcp)
    zone_agent = create_zone_analyzer_agent(use_mcp)
    equipment_agent = create_equipment_checker_agent(use_mcp)
    report_agent = create_report_writer_agent()
    
    return Agent(
        name="BFA Triage",
        instructions="""Du bist der Einstiegspunkt für Explosionsschutz-Anfragen.

Routing:
1. CAD-Datei Analyse → CAD Reader
   Keywords: "lies", "CAD", "DXF", "IFC", "Datei"

2. Ex-Zonen Klassifizierung → Zone Analyzer
   Keywords: "Zone", "klassifizier", "ATEX", "Explosionsschutz"

3. Equipment-Prüfung → Equipment Checker
   Keywords: "Gerät", "Equipment", "Kennzeichnung", "geeignet"

4. Bericht → Report Writer
   Keywords: "Bericht", "Report", "Dokumentation"

Bei Unklarheit: Frage nach!
Nach Abschluss: Zusammenfassung + weitere Optionen anbieten.""",
        model=Models.FAST,
        handoffs=[
            handoff(cad_agent, "CAD-Datei lesen"),
            handoff(zone_agent, "Ex-Zonen klassifizieren"),
            handoff(equipment_agent, "Equipment prüfen"),
            handoff(report_agent, "Bericht erstellen"),
        ]
    )


# ============================================================
# Convenience: Vorkonfigurierte Agents
# ============================================================

# Standard-Agents (mit MCP)
cad_reader_agent = create_cad_reader_agent(use_mcp=True)
zone_analyzer_agent = create_zone_analyzer_agent(use_mcp=True)
equipment_checker_agent = create_equipment_checker_agent(use_mcp=True)
report_writer_agent = create_report_writer_agent()
triage_agent = create_triage_agent(use_mcp=True)

# Legacy-Agents (ohne MCP, nur Function Tools)
cad_reader_agent_legacy = create_cad_reader_agent(use_mcp=False)
zone_analyzer_agent_legacy = create_zone_analyzer_agent(use_mcp=False)
equipment_checker_agent_legacy = create_equipment_checker_agent(use_mcp=False)
triage_agent_legacy = create_triage_agent(use_mcp=False)


__all__ = [
    # Factory Functions
    "create_triage_agent",
    "create_cad_reader_agent",
    "create_zone_analyzer_agent",
    "create_equipment_checker_agent",
    "create_report_writer_agent",
    # MCP Server
    "get_bfa_mcp_server",
    # Pre-built Agents (MCP)
    "triage_agent",
    "cad_reader_agent",
    "zone_analyzer_agent",
    "equipment_checker_agent",
    "report_writer_agent",
    # Legacy Agents (Function Tools)
    "triage_agent_legacy",
    "cad_reader_agent_legacy",
    "zone_analyzer_agent_legacy",
    "equipment_checker_agent_legacy",
]
