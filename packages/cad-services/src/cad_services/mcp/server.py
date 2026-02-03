"""
CAD-Hub MCP Server Implementation.

Exponiert CAD-Funktionen über Model Context Protocol.
Läuft via WSL für Integration mit Windsurf/Cascade.
"""

from __future__ import annotations

import asyncio
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool


# MCP Server Instance
server = Server("cadhub-mcp")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """Listet verfügbare MCP Tools.

    Returns:
        Liste aller CAD-Hub Tools mit Schema.
    """
    return [
        Tool(
            name="parse_ifc",
            description=(
                "Parst IFC-Datei und extrahiert alle CAD-Elemente "
                "(Räume, Fenster, Türen, Wände, Decken)"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Pfad zur IFC-Datei",
                    },
                    "project_id": {
                        "type": "integer",
                        "description": "Ziel-Projekt ID",
                    },
                },
                "required": ["file_path", "project_id"],
            },
        ),
        Tool(
            name="list_rooms",
            description="Listet alle Räume eines CAD-Modells (Raumliste)",
            inputSchema={
                "type": "object",
                "properties": {
                    "model_id": {
                        "type": "integer",
                        "description": "CAD-Modell ID",
                    },
                    "floor_id": {
                        "type": "integer",
                        "description": "Optional: Filter nach Geschoss",
                    },
                },
                "required": ["model_id"],
            },
        ),
        Tool(
            name="list_windows",
            description=(
                "Listet alle Fenster eines CAD-Modells (Fensterliste) mit Abmessungen und U-Werten"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "model_id": {
                        "type": "integer",
                        "description": "CAD-Modell ID",
                    },
                    "floor_id": {
                        "type": "integer",
                        "description": "Optional: Filter nach Geschoss",
                    },
                },
                "required": ["model_id"],
            },
        ),
        Tool(
            name="list_doors",
            description=("Listet alle Türen eines CAD-Modells (Türliste) mit Brandschutzklassen"),
            inputSchema={
                "type": "object",
                "properties": {
                    "model_id": {
                        "type": "integer",
                        "description": "CAD-Modell ID",
                    },
                },
                "required": ["model_id"],
            },
        ),
        Tool(
            name="calculate_din277",
            description=(
                "Berechnet Flächen nach DIN 277 (BGF, KGF, NRF, NF, TF, VF) und umbauten Raum (BRI)"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "model_id": {
                        "type": "integer",
                        "description": "CAD-Modell ID",
                    },
                },
                "required": ["model_id"],
            },
        ),
        Tool(
            name="calculate_woflv",
            description="Berechnet Wohnfläche nach Wohnflächenverordnung (WoFlV) mit Anrechnungsfaktoren",
            inputSchema={
                "type": "object",
                "properties": {
                    "model_id": {
                        "type": "integer",
                        "description": "CAD-Modell ID",
                    },
                },
                "required": ["model_id"],
            },
        ),
        Tool(
            name="get_model_statistics",
            description="Gibt Übersicht über alle Elemente eines CAD-Modells",
            inputSchema={
                "type": "object",
                "properties": {
                    "model_id": {
                        "type": "integer",
                        "description": "CAD-Modell ID",
                    },
                },
                "required": ["model_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Führt MCP Tool aus.

    Args:
        name: Tool-Name.
        arguments: Tool-Argumente.

    Returns:
        Liste von TextContent mit Ergebnis.

    Raises:
        ValueError: Bei unbekanntem Tool.
    """
    if name == "parse_ifc":
        return await _handle_parse_ifc(arguments)
    elif name == "list_rooms":
        return await _handle_list_rooms(arguments)
    elif name == "list_windows":
        return await _handle_list_windows(arguments)
    elif name == "list_doors":
        return await _handle_list_doors(arguments)
    elif name == "calculate_din277":
        return await _handle_calculate_din277(arguments)
    elif name == "calculate_woflv":
        return await _handle_calculate_woflv(arguments)
    elif name == "get_model_statistics":
        return await _handle_get_statistics(arguments)

    raise ValueError(f"Unknown tool: {name}")


async def _handle_parse_ifc(arguments: dict[str, Any]) -> list[TextContent]:
    """Handled parse_ifc Tool."""
    file_path = arguments["file_path"]
    project_id = arguments["project_id"]

    # TODO: Integrate with actual handler
    return [
        TextContent(
            type="text",
            text=f"""IFC-Datei wird geparst: {file_path}
Ziel-Projekt: {project_id}

[Simulation - Handler-Integration erforderlich]
""",
        )
    ]


async def _handle_list_rooms(arguments: dict[str, Any]) -> list[TextContent]:
    """Handled list_rooms Tool."""
    model_id = arguments["model_id"]
    floor_id = arguments.get("floor_id")

    # TODO: Integrate with actual repository
    filter_info = f" (Geschoss: {floor_id})" if floor_id else ""
    return [
        TextContent(
            type="text",
            text=f"""Raumliste für Modell {model_id}{filter_info}:

| Nr. | Name | Fläche | Höhe | Volumen | DIN 277 |
|-----|------|--------|------|---------|---------|
| 001 | Wohnzimmer | 28.50 m² | 2.80 m | 79.80 m³ | NF1.1 |
| 002 | Schlafzimmer | 16.20 m² | 2.80 m | 45.36 m³ | NF1.1 |
| 003 | Küche | 12.80 m² | 2.80 m | 35.84 m³ | NF1.1 |
| 004 | Bad | 8.50 m² | 2.80 m | 23.80 m³ | NF1.1 |
| 005 | Flur | 9.30 m² | 2.80 m | 26.04 m³ | VF8 |

**Gesamt:** 5 Räume, 75.30 m², 210.84 m³

[Simulation - Repository-Integration erforderlich]
""",
        )
    ]


async def _handle_list_windows(arguments: dict[str, Any]) -> list[TextContent]:
    """Handled list_windows Tool."""
    model_id = arguments["model_id"]

    return [
        TextContent(
            type="text",
            text=f"""Fensterliste für Modell {model_id}:

| Nr. | Name | Breite | Höhe | Fläche | U-Wert | Material |
|-----|------|--------|------|--------|--------|----------|
| F01 | Wohnzimmer Nord | 1.50 m | 1.40 m | 2.10 m² | 1.1 W/m²K | Kunststoff |
| F02 | Wohnzimmer Süd | 2.00 m | 2.20 m | 4.40 m² | 1.0 W/m²K | Holz-Alu |
| F03 | Schlafzimmer | 1.20 m | 1.40 m | 1.68 m² | 1.1 W/m²K | Kunststoff |
| F04 | Küche | 1.00 m | 1.20 m | 1.20 m² | 1.1 W/m²K | Kunststoff |
| F05 | Bad | 0.80 m | 0.60 m | 0.48 m² | 1.3 W/m²K | Kunststoff |

**Gesamt:** 5 Fenster, 9.86 m²
**Durchschnitt U-Wert:** 1.12 W/m²K

[Simulation - Repository-Integration erforderlich]
""",
        )
    ]


async def _handle_list_doors(arguments: dict[str, Any]) -> list[TextContent]:
    """Handled list_doors Tool."""
    model_id = arguments["model_id"]

    return [
        TextContent(
            type="text",
            text=f"""Türliste für Modell {model_id}:

| Nr. | Name | Breite | Höhe | Typ | Brandschutz |
|-----|------|--------|------|-----|-------------|
| T01 | Eingangstür | 1.00 m | 2.10 m | Außen | T30 |
| T02 | Wohnzimmer | 0.88 m | 2.01 m | Innen | - |
| T03 | Schlafzimmer | 0.88 m | 2.01 m | Innen | - |
| T04 | Küche | 0.88 m | 2.01 m | Innen | - |
| T05 | Bad | 0.78 m | 2.01 m | Innen | - |

**Gesamt:** 5 Türen
**Mit Brandschutz:** 1 (T30)

[Simulation - Repository-Integration erforderlich]
""",
        )
    ]


async def _handle_calculate_din277(arguments: dict[str, Any]) -> list[TextContent]:
    """Handled calculate_din277 Tool."""
    model_id = arguments["model_id"]

    return [
        TextContent(
            type="text",
            text=f"""DIN 277 Flächenberechnung für Modell {model_id}:

## Grundflächen
- **Brutto-Grundfläche (BGF):** 95.00 m²
- **Konstruktions-Grundfläche (KGF):** 19.70 m²
- **Netto-Raumfläche (NRF):** 75.30 m²

## Nutzflächen
- **NF1 Wohnen/Aufenthalt:** 66.00 m²
- **NF2 Büroarbeit:** 0.00 m²
- **NF3 Lager/Verteilen:** 0.00 m²
- **TF7 Technikflächen:** 0.00 m²
- **VF8 Verkehrsflächen:** 9.30 m²

## Umbauter Raum
- **Brutto-Rauminhalt (BRI):** 266.00 m³

[Simulation - Repository-Integration erforderlich]
""",
        )
    ]


async def _handle_calculate_woflv(arguments: dict[str, Any]) -> list[TextContent]:
    """Handled calculate_woflv Tool."""
    model_id = arguments["model_id"]

    return [
        TextContent(
            type="text",
            text=f"""WoFlV Wohnflächenberechnung für Modell {model_id}:

## Übersicht
- **Grundfläche gesamt:** 75.30 m²
- **Wohnfläche gesamt:** 69.55 m²

## Anrechnung nach WoFlV
| Faktor | Fläche | Angerechnet |
|--------|--------|-------------|
| 100% (≥2m Höhe) | 66.00 m² | 66.00 m² |
| 50% (1-2m Höhe) | 3.10 m² | 1.55 m² |
| 25% (Balkone) | 8.00 m² | 2.00 m² |
| 0% (Keller etc.) | 0.00 m² | 0.00 m² |

## Anrechnungsquote
- **Quote:** 92.4%

[Simulation - Repository-Integration erforderlich]
""",
        )
    ]


async def _handle_get_statistics(arguments: dict[str, Any]) -> list[TextContent]:
    """Handled get_model_statistics Tool."""
    model_id = arguments["model_id"]

    return [
        TextContent(
            type="text",
            text=f"""CAD-Modell Statistiken für Modell {model_id}:

## Elementübersicht
| Element | Anzahl | Gesamt |
|---------|--------|--------|
| Geschosse | 1 | - |
| Räume | 5 | 75.30 m² |
| Fenster | 5 | 9.86 m² |
| Türen | 5 | - |
| Wände | 12 | 48.50 m² |
| Decken | 2 | 95.00 m² |

## Modell-Info
- **Format:** IFC4
- **Status:** ready
- **Erstellt:** 2026-02-02

[Simulation - Repository-Integration erforderlich]
""",
        )
    ]


def create_server() -> Server:
    """Erstellt MCP Server Instance.

    Returns:
        Konfigurierter MCP Server.
    """
    return server


async def main() -> None:
    """Startet MCP Server via stdio.

    Haupteintrittspunkt für WSL-Integration.
    """
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
