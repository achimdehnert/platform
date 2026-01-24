"""Beispiel: BFA Agent mit MCP Server.

Zeigt verschiedene Wege MCP Server zu integrieren:
1. Eingebauter BFA MCP Server
2. Externer MCP Server (z.B. Filesystem)
3. Kombination mehrerer MCP Server
"""

import asyncio
from agents import Agent, Runner, RunConfig
from agents.mcp import MCPServerStdio

from bfa_agent.config import setup_openrouter, Models
from bfa_agent.agents_mcp import (
    create_triage_agent,
    get_bfa_mcp_server,
)


async def example_1_builtin_mcp():
    """Beispiel 1: Eingebauter BFA MCP Server."""
    print("\n" + "="*60)
    print("Beispiel 1: BFA MCP Server")
    print("="*60)
    
    # Triage Agent mit MCP erstellen
    agent = create_triage_agent(use_mcp=True)
    
    # Anfrage ausführen
    result = await Runner.run(
        agent,
        "Lies die Datei anlage.ifc und zeige mir alle Räume mit ihren Ex-Zonen"
    )
    
    print(f"\nErgebnis:\n{result.final_output}")


async def example_2_external_mcp():
    """Beispiel 2: Externer Filesystem MCP Server."""
    print("\n" + "="*60)
    print("Beispiel 2: Filesystem MCP Server")
    print("="*60)
    
    # Filesystem MCP Server (Node.js basiert)
    filesystem_mcp = MCPServerStdio(
        name="filesystem",
        command="npx",
        args=[
            "-y",
            "@modelcontextprotocol/server-filesystem",
            "/tmp/cad_files",  # Erlaubter Pfad
            "/home/user/projects"
        ]
    )
    
    # Agent mit Filesystem-Zugriff
    file_agent = Agent(
        name="File Explorer",
        instructions="""Du kannst Dateien im Filesystem lesen.
        
Nutze die MCP Tools um:
- Verzeichnisse zu listen
- Dateien zu lesen
- Nach CAD-Dateien zu suchen (.dxf, .ifc, .step)""",
        model=Models.FAST,
        mcp_servers=[filesystem_mcp]
    )
    
    result = await Runner.run(
        file_agent,
        "Zeige mir alle Dateien im /tmp/cad_files Verzeichnis"
    )
    
    print(f"\nErgebnis:\n{result.final_output}")


async def example_3_multiple_mcp():
    """Beispiel 3: Mehrere MCP Server kombinieren."""
    print("\n" + "="*60)
    print("Beispiel 3: Multiple MCP Server")
    print("="*60)
    
    # BFA MCP Server
    bfa_mcp = get_bfa_mcp_server()
    
    # SQLite MCP Server für Datenbank-Zugriff
    sqlite_mcp = MCPServerStdio(
        name="sqlite",
        command="uvx",
        args=["mcp-server-sqlite", "--db-path", "/tmp/bfa_data.db"]
    )
    
    # Fetch MCP Server für Web-Requests (z.B. Normen-Datenbank)
    fetch_mcp = MCPServerStdio(
        name="fetch",
        command="uvx",
        args=["mcp-server-fetch"]
    )
    
    # Agent mit allen drei MCP Servern
    super_agent = Agent(
        name="BFA Super Agent",
        instructions="""Du hast Zugriff auf mehrere Datenquellen:

1. BFA Tools (bfa-cad):
   - read_cad_file: CAD-Dateien lesen
   - calculate_zone_extent: Zonen berechnen
   - check_equipment_for_zone: Equipment prüfen
   - get_substance_data: Stoffdaten abrufen

2. SQLite (sqlite):
   - Datenbank-Abfragen für historische Analysen

3. Web Fetch (fetch):
   - Aktuelle Informationen aus dem Web

Kombiniere diese Tools für umfassende Analysen.""",
        model=Models.PRECISE,
        mcp_servers=[bfa_mcp, sqlite_mcp, fetch_mcp]
    )
    
    result = await Runner.run(
        super_agent,
        "Hole die Stoffdaten für Aceton und erkläre die Explosionsgruppe"
    )
    
    print(f"\nErgebnis:\n{result.final_output}")


async def example_4_hybrid_tools():
    """Beispiel 4: MCP Server + Function Tools kombiniert."""
    print("\n" + "="*60)
    print("Beispiel 4: Hybrid (MCP + Function Tools)")
    print("="*60)
    
    from agents import function_tool
    
    # Lokale Function Tools für schnelle Berechnungen
    @function_tool
    def quick_zone_check(zone: str, category: str) -> str:
        """Schnelle Zonenprüfung ohne MCP Overhead."""
        requirements = {
            "Zone 0": ["1G"],
            "Zone 1": ["1G", "2G"],
            "Zone 2": ["1G", "2G", "3G"],
        }
        req = requirements.get(zone, [])
        ok = category in req
        return f"{category} für {zone}: {'✓ OK' if ok else '✗ NICHT OK'}"
    
    # Agent mit beiden Tool-Typen
    hybrid_agent = Agent(
        name="Hybrid Agent",
        instructions="""Du hast zwei Tool-Typen:

1. MCP Tools (für komplexe Operationen):
   - read_cad_file
   - calculate_zone_extent
   - get_substance_data

2. Lokale Tools (für schnelle Checks):
   - quick_zone_check: Schnelle Kategorieprüfung

Nutze lokale Tools für einfache Abfragen,
MCP Tools für komplexe Analysen.""",
        model=Models.FAST,
        mcp_servers=[get_bfa_mcp_server()],
        tools=[quick_zone_check]  # Lokale Tools zusätzlich!
    )
    
    result = await Runner.run(
        hybrid_agent,
        "Prüfe schnell: Ist Kategorie 2G für Zone 1 geeignet?"
    )
    
    print(f"\nErgebnis:\n{result.final_output}")


async def main():
    """Führt alle Beispiele aus."""
    
    # OpenRouter initialisieren
    setup_openrouter()
    
    # Beispiele ausführen
    await example_1_builtin_mcp()
    # await example_2_external_mcp()  # Benötigt npx
    # await example_3_multiple_mcp()  # Benötigt uvx
    await example_4_hybrid_tools()


if __name__ == "__main__":
    asyncio.run(main())
