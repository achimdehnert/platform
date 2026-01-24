==============
Control Center
==============

.. note::
   **Zentrale Steuerung für BF Agent** | Status: Production Ready

Übersicht
=========

Das Control Center ist die zentrale Verwaltungsoberfläche für:

- **LLMs**: Konfiguration und Monitoring von AI-Modellen
- **Agents**: Verwaltung von AI-Agenten
- **MCP Server**: Model Context Protocol Server
- **Workflows**: Workflow-Konfiguration und -Überwachung
- **Controlling**: Kosten- und Performance-Tracking

Architektur
===========

.. code-block:: text

   ┌─────────────────────────────────────────────────────────────┐
   │                    CONTROL CENTER                            │
   ├─────────────────────────────────────────────────────────────┤
   │                                                             │
   │  Dashboard ──→ Tool Registry ──→ MCP Integration            │
   │      │              │                  │                    │
   │      ↓              ↓                  ↓                    │
   │  Navigation    System Health      Tool Execution           │
   │      │              │                  │                    │
   │      ↓              ↓                  ↓                    │
   │  Feature Planning ←── AI Config ←── Initiatives            │
   │                                                             │
   └─────────────────────────────────────────────────────────────┘

Hauptfunktionen
===============

Dashboard
---------

**URL:** ``/control-center/``

.. code-block:: python

   def dashboard_home(request):
       context = {
           "llm_count": Llms.objects.filter(is_active=True).count(),
           "agent_count": Agents.objects.filter(status='active').count(),
           "mcp_server_count": MCPServer.objects.filter(is_enabled=True).count(),
           "tool_count": len(tool_registry.tools),
       }
       return render(request, "control_center/dashboard_new.html", context)

Navigation System
-----------------

Dynamische Navigation aus der Datenbank:

.. code-block:: python

   # models_navigation.py
   class NavigationGroup(models.Model):
       name = models.CharField(max_length=100)
       slug = models.SlugField(unique=True)
       icon = models.CharField(max_length=50)
       order = models.IntegerField(default=0)
       is_active = models.BooleanField(default=True)
   
   class NavigationItem(models.Model):
       group = models.ForeignKey(NavigationGroup, on_delete=models.CASCADE)
       name = models.CharField(max_length=100)
       url_name = models.CharField(max_length=200)
       icon = models.CharField(max_length=50)
       permission_required = models.CharField(max_length=100, blank=True)

Tool Registry
-------------

Zentrale Registrierung aller verfügbaren Tools:

.. code-block:: python

   # registry.py
   from apps.control_center.registry import tool_registry
   
   # Tool registrieren
   @tool_registry.register
   def my_tool(param: str) -> dict:
       """Tool Beschreibung."""
       return {"result": param}
   
   # System Health abrufen
   health = tool_registry.get_system_health()

Module
======

AI Configuration
----------------

**URL:** ``/control-center/ai-config/``

Verwaltung von:

- LLM-Modellen (OpenAI, Anthropic, Groq, Ollama)
- API-Keys
- Default-Einstellungen
- Kosten-Limits

Feature Planning
----------------

**URL:** ``/control-center/features/``

- Feature Requests erstellen
- Priorisierung
- Status-Tracking
- Roadmap-Ansicht

Initiatives
-----------

**URL:** ``/control-center/initiatives/``

Größere Projekte die mehrere Requirements umfassen:

.. code-block:: python

   class Initiative(models.Model):
       title = models.CharField(max_length=200)
       description = models.TextField()
       status = models.CharField(choices=STATUS_CHOICES)
       priority = models.CharField(choices=PRIORITY_CHOICES)
       domain = models.CharField(choices=DOMAIN_CHOICES)
       
       # Workflow
       analysis = models.TextField(blank=True)
       concept = models.TextField(blank=True)

Workflow V2
-----------

**URL:** ``/control-center/workflow-v2/``

- Domain-basierte Workflows
- Project Types mit Phasen
- Phase Actions konfigurieren
- Drag & Drop Sortierung

MCP Integration
===============

MCP Server Management
---------------------

**URL:** ``/control-center/mcp/``

.. code-block:: python

   # views_mcp.py
   def mcp_dashboard(request):
       servers = MCPServer.objects.all()
       return render(request, "control_center/mcp/dashboard.html", {
           "servers": servers,
           "active_count": servers.filter(is_enabled=True).count(),
       })

MCP Task Execution
------------------

.. code-block:: python

   # tasks_mcp.py
   from celery import shared_task
   
   @shared_task
   def execute_mcp_tool(server_id: int, tool_name: str, params: dict):
       server = MCPServer.objects.get(id=server_id)
       result = server.execute_tool(tool_name, params)
       return result

URLs
====

.. code-block:: python

   # urls.py (Auszug)
   
   urlpatterns = [
       # Dashboard
       path("", views.dashboard_home, name="dashboard"),
       path("api/status/", views.api_status, name="api_status"),
       
       # AI Config
       path("ai-config/", include("apps.control_center.urls_ai_config")),
       
       # Features & Initiatives
       path("features/", include("apps.control_center.urls_features")),
       path("initiatives/", include("apps.control_center.urls_initiatives")),
       
       # MCP
       path("mcp/", include("apps.control_center.urls_mcp")),
       
       # Workflow V2
       path("workflow-v2/", include("apps.control_center.urls_workflow_v2")),
       
       # Controlling
       path("controlling/", include("apps.bfagent.urls_controlling")),
   ]

Context Processors
==================

.. code-block:: python

   # context_processors.py
   
   def navigation_context(request):
       """Lädt Navigation aus DB für alle Templates."""
       groups = NavigationGroup.objects.filter(is_active=True).prefetch_related('items')
       return {
           "nav_groups": groups,
           "current_path": request.path,
       }

Siehe auch
==========

.. toctree::
   :maxdepth: 1

   ../guides/session_handling_controlling
   dlm_hub
