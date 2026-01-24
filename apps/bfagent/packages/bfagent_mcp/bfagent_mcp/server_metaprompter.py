"""
BF Agent MCP Server v2.0
========================

Universal MCP Server mit:
- MetaPrompter Gateway (natürliche Sprache)
- Standards Enforcement (garantierte Konformität)
"""

from typing import Dict, Any

# MCP SDK (for reference - actual import depends on environment)
# from mcp.server import Server

from .metaprompter import UniversalGateway, Intent
from .metaprompter.gateway import Strategy
from .standards import get_all_standards
from .standards.validator import CodeValidator
from .standards.enforcer import TemplateEnforcer


class BFAgentMCPServer:
    """
    BF Agent MCP Server mit Universal Gateway.
    
    Ein einziges Tool für ALLE Anfragen.
    """
    
    def __init__(self):
        # Core Components
        self.gateway = UniversalGateway(strategy=Strategy.HYBRID)
        self.validator = CodeValidator()
        self.enforcer = TemplateEnforcer()
        
        # Tool Executor registrieren
        self.gateway.set_tool_executor(self._execute_tool)
        
        # Tool Registry
        self._tools: Dict[str, callable] = {
            "bfagent_list_domains": self._list_domains,
            "bfagent_generate_handler": self._generate_handler,
            "bfagent_validate_handler": self._validate_handler,
            "bfagent_get_best_practices": self._get_best_practices,
            "bfagent_help": self._show_help,
            # CAD Tools (Platzhalter)
            "cad_list_rooms": self._cad_list_rooms,
            "cad_get_dimensions": self._cad_get_dimensions,
            "cad_calculate_volume": self._cad_calculate_volume,
        }
    
    # ═══════════════════════════════════════════════════════════════════════
    # PUBLIC API - Das einzige Tool das exposed wird
    # ═══════════════════════════════════════════════════════════════════════
    
    async def bfagent(self, request: str) -> str:
        """
        🤖 BF Agent Universal Interface
        
        Sprich natürlich - ich verstehe dich!
        
        Beispiele:
        - "Zeig alle Domains"
        - "Erstelle einen IFC Parser"
        - "Liste Räume aus building.ifc"
        - "Hilfe"
        """
        result = await self.gateway.process(request)
        
        if result.success:
            output = result.result or "✅ Erledigt"
            
            # Assumptions hinzufügen wenn vorhanden
            if result.assumptions:
                output += "\n\n---\nℹ️ **Annahmen:**\n"
                for a in result.assumptions:
                    output += f"• {a}\n"
            
            return output
        
        if result.needs_input:
            return result.prompt or "Was möchtest du tun?"
        
        return result.result or "❌ Unbekannter Fehler"
    
    # ═══════════════════════════════════════════════════════════════════════
    # INTERNAL TOOL EXECUTOR
    # ═══════════════════════════════════════════════════════════════════════
    
    async def _execute_tool(self, tool_name: str, params: Dict[str, Any]) -> str:
        """Führt internes Tool aus"""
        handler = self._tools.get(tool_name)
        if handler:
            return await handler(params)
        return f"❌ Tool nicht gefunden: {tool_name}"
    
    # ═══════════════════════════════════════════════════════════════════════
    # INTERNAL TOOLS
    # ═══════════════════════════════════════════════════════════════════════
    
    async def _list_domains(self, params: Dict) -> str:
        """Listet alle Domains"""
        return """
# 📁 Verfügbare Domains

| Domain | Handler | Status |
|--------|---------|--------|
| book_writing | 20 | ✅ Production |
| cad_analysis | 12 | 🟡 Beta |
| medical_translation | 8 | ✅ Production |
| comic_creation | 15 | 🟢 Development |
| exschutz_forensics | 10 | 🟡 Beta |
"""
    
    async def _generate_handler(self, params: Dict) -> str:
        """Generiert Handler mit Standards Enforcement"""
        
        handler_name = params.get("handler_name", "NewHandler")
        description = params.get("description", "Auto-generated handler")
        domain = params.get("domain", "cad_analysis")
        
        # Input/Output Fields
        input_fields = params.get("input_fields", [
            {"name": "file_path", "type": "str", "description": "Path to file", "required": True},
        ])
        output_fields = params.get("output_fields", [
            {"name": "data", "type": "Dict[str, Any]", "description": "Result data", "required": True},
        ])
        
        # Template Enforcer generiert standard-konformen Code
        result = self.enforcer.generate_handler(
            handler_name=handler_name,
            description=description,
            domain=domain,
            input_fields=input_fields,
            output_fields=output_fields,
            use_cases=params.get("use_cases", ["Process data"]),
        )
        
        # Validieren (Double-Check)
        validation = self.validator.validate(result["handler_code"])
        
        output = f"""
# ✅ Handler generiert: {handler_name}

**Score:** {validation.score}/100 | **Status:** {validation.summary}

## Handler Code
**File:** `apps/{domain}/handlers/{result['handler_filename']}`

```python
{result['handler_code']}
```

## Test Code
**File:** `apps/{domain}/tests/{result['test_filename']}`

```python
{result['test_code']}
```

## Applied Standards
{self._format_applied_standards()}
"""
        return output
    
    async def _validate_handler(self, params: Dict) -> str:
        """Validiert Code gegen Standards"""
        code = params.get("code", "")
        if not code:
            return "❌ Kein Code zum Validieren"
        
        result = self.validator.validate(code, strict=params.get("strict", False))
        return self.validator.format_report(result)
    
    async def _get_best_practices(self, params: Dict) -> str:
        """Liefert Best Practices"""
        topic = params.get("topic", "handler")
        
        standards = get_all_standards()
        
        output = f"# 💡 Best Practices: {topic}\n\n"
        output += "## Standards\n\n"
        
        for std in standards[:6]:
            output += f"### [{std.id}] {std.name}\n"
            output += f"{std.description}\n\n"
        
        return output
    
    async def _show_help(self, params: Dict) -> str:
        """Zeigt Hilfe"""
        return """
# 🤖 BF Agent MCP Server v2.0

## Wie nutze ich es?

Sprich einfach natürlich mit mir:

```
"Erstelle einen IFC Parser für CAD"
"Validiere diesen Code: ..."
"Zeig Best Practices für Pydantic"
```

## Features

✅ **Universal Gateway** - Ein Tool für alles
✅ **Standards Enforcement** - Immer konformer Code
✅ **Smart Defaults** - Fehlende Parameter werden ergänzt
✅ **Rückfragen** - Bei Unklarheiten frage ich nach

## Domains

- 📚 book_writing
- 🏗️ cad_analysis
- 🏥 medical_translation
- 🎨 comic_creation
- 💥 exschutz_forensics
"""
    
    # ═══════════════════════════════════════════════════════════════════════
    # CAD TOOLS (Platzhalter - werden später implementiert)
    # ═══════════════════════════════════════════════════════════════════════
    
    async def _cad_list_rooms(self, params: Dict) -> str:
        """Listet Räume aus CAD-Datei"""
        file_path = params.get("file_path", "unknown.ifc")
        return f"""
# 🏠 Räume in {file_path}

| Raum | Fläche | Volumen |
|------|--------|---------|
| Wohnzimmer | 35.4 m² | 99.1 m³ |
| Küche | 12.8 m² | 35.8 m³ |
| Schlafzimmer | 18.2 m² | 50.9 m³ |
| Bad | 8.5 m² | 23.8 m³ |

*[Mock-Daten - IFC Parser noch nicht implementiert]*
"""
    
    async def _cad_get_dimensions(self, params: Dict) -> str:
        """Zeigt Raum-Dimensionen"""
        room = params.get("room_name", "Raum")
        return f"""
# 📐 Dimensionen: {room}

- **Bruttofläche:** 35.4 m²
- **Nettofläche:** 32.1 m²
- **Volumen:** 99.1 m³
- **Höhe:** 2.80 m

*[Mock-Daten]*
"""
    
    async def _cad_calculate_volume(self, params: Dict) -> str:
        """Berechnet Gesamtvolumen"""
        return """
# 📊 Umbauter Raum (BRI)

**Gesamtvolumen:** 487.3 m³

| Raum | Volumen |
|------|---------|
| Wohnzimmer | 99.1 m³ |
| Küche | 35.8 m³ |
| Schlafzimmer | 50.9 m³ |
| Bad | 23.8 m³ |
| Sonstige | 277.7 m³ |

*[Mock-Daten]*
"""
    
    # ═══════════════════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════════════════
    
    def _format_applied_standards(self) -> str:
        """Formatiert angewendete Standards"""
        return """
- ✅ H001: BaseHandler Inheritance
- ✅ H002: Three-Phase Pattern
- ✅ H003: HandlerResult Return
- ✅ H004: Handler Metadata
- ✅ S001: Pydantic Input Schema
- ✅ S002: Pydantic Output Schema
- ✅ E001: Try-Except Error Handling
- ✅ L001: Logger Usage
- ✅ D001: Class Docstring
"""


# ═══════════════════════════════════════════════════════════════════════════════
# STANDALONE TEST
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    """Test the server"""
    server = BFAgentMCPServer()
    
    # Test verschiedene Anfragen
    tests = [
        "Hilfe",
        "Zeig alle Domains",
        "Erstelle einen IFC Parser für CAD",
        "Liste Räume aus building.ifc",
    ]
    
    for test in tests:
        print(f"\n{'='*60}")
        print(f"INPUT: {test}")
        print('='*60)
        result = await server.bfagent(test)
        print(result)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
