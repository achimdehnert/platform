===========
MCP Server
===========

.. note::
   **Model Context Protocol** | Status: Production Ready

BF Agent stellt mehrere MCP Server bereit, die AI-Assistenten (Claude, Cascade)
mit strukturiertem Zugriff auf Projektfunktionen versorgen.

.. toctree::
   :maxdepth: 2
   :caption: MCP Server

   bfagent_mcp
   bfagent_db_mcp
   code_quality_mcp
   test_generator_mcp
   illustration_mcp
   deployment_mcp

Übersicht
=========

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Server
     - Tools
     - Beschreibung
   * - :doc:`bfagent_mcp`
     - 35+
     - Haupt-MCP für Domain-Management, Handler, Refactoring, Requirements
   * - :doc:`bfagent_db_mcp`
     - 8
     - PostgreSQL & Django ORM Integration
   * - :doc:`code_quality_mcp`
     - 8
     - Code-Analyse, Naming Conventions, UI Consistency
   * - :doc:`test_generator_mcp`
     - 5
     - Test-Generierung, Ausführung, Coverage-Analyse
   * - :doc:`illustration_mcp`
     - 6
     - ComfyUI Integration für Buch-Illustrationen
   * - :doc:`deployment_mcp`
     - 50+
     - Hetzner, Docker, SSL, DNS, Database Management

Architektur
===========

.. code-block:: text

   ┌─────────────────────────────────────────────────────────────┐
   │                    AI ASSISTANT (Cascade)                    │
   ├─────────────────────────────────────────────────────────────┤
   │                                                              │
   │  Tool Call: bfagent_list_domains()                          │
   │       ↓                                                      │
   │  ┌──────────────────────────────────────────────────────┐   │
   │  │                  MCP SERVER LAYER                     │   │
   │  ├──────────────────────────────────────────────────────┤   │
   │  │  bfagent_mcp    │ bfagent_db_mcp │ code_quality_mcp  │   │
   │  │  deployment_mcp │ illustration   │ test_generator    │   │
   │  └──────────────────────────────────────────────────────┘   │
   │       ↓                                                      │
   │  ┌──────────────────────────────────────────────────────┐   │
   │  │                  DJANGO / SERVICES                    │   │
   │  └──────────────────────────────────────────────────────┘   │
   │                                                              │
   └─────────────────────────────────────────────────────────────┘

Konfiguration
=============

Windsurf MCP Settings
---------------------

.. code-block:: json

   {
     "mcpServers": {
       "bfagent": {
         "command": "python",
         "args": ["-m", "bfagent_mcp.server"],
         "cwd": "/path/to/bfagent/packages/bfagent_mcp"
       },
       "bfagent-db": {
         "command": "python", 
         "args": ["server.py"],
         "cwd": "/path/to/bfagent/packages/bfagent_db_mcp"
       },
       "code-quality": {
         "command": "python",
         "args": ["-m", "code_quality_mcp.server"],
         "cwd": "/path/to/bfagent/packages/code_quality_mcp"
       }
     }
   }

Umgebungsvariablen
------------------

.. code-block:: bash

   # Django Integration
   export BFAGENT_PROJECT_ROOT=/path/to/bfagent
   export DJANGO_SETTINGS_MODULE=config.settings
   
   # Hetzner Cloud (deployment_mcp)
   export HETZNER_API_TOKEN=xxx
   
   # ComfyUI (illustration_mcp)
   export COMFYUI_URL=http://localhost:8181

Best Practices
==============

1. **Tool-Auswahl**: Nutze spezifische Tools statt generische
2. **Response Format**: ``response_format="markdown"`` für Lesbarkeit
3. **Batch-Operationen**: Mehrere unabhängige Calls parallel
4. **Error Handling**: Tools geben strukturierte Fehler zurück
5. **Session Tracking**: ``bfagent_log_user_request`` am Anfang

Entwicklung
===========

Neuen MCP Server erstellen:

.. code-block:: bash

   # Verzeichnis erstellen
   mkdir -p packages/my_mcp/my_mcp
   
   # Server Template
   cp packages/bfagent_db_mcp/server.py packages/my_mcp/server.py

Minimales Server-Template:

.. code-block:: python

   from mcp.server import Server
   from mcp.server.stdio import stdio_server
   from mcp.types import Tool, TextContent
   
   server = Server("my-mcp")
   
   TOOLS = [
       Tool(
           name="my_tool",
           description="Tool description",
           inputSchema={
               "type": "object",
               "properties": {"param": {"type": "string"}},
               "required": ["param"]
           }
       )
   ]
   
   @server.list_tools()
   async def list_tools():
       return TOOLS
   
   @server.call_tool()
   async def call_tool(name: str, arguments: dict):
       if name == "my_tool":
           result = do_something(arguments["param"])
           return [TextContent(type="text", text=str(result))]
