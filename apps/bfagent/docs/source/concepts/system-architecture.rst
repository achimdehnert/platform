.. _system-architecture:

==========================================
BF Agent - System-Architektur
==========================================

.. contents:: Inhalt
   :local:
   :depth: 2

Übersicht
=========

**BF Agent** ist eine modulare Django-basierte Plattform für AI-gestützte 
Workflow-Orchestrierung. Die Architektur folgt dem Prinzip der 
**Zero-Hardcoding-Philosophie** - alle Konfigurationen sind datenbankgesteuert.

.. mermaid::

   flowchart TB
       subgraph UI["🖥️ Frontend Layer"]
           WEB[Django Templates]
           HTMX[HTMX Components]
           API[REST API]
       end
       
       subgraph HUBS["🏗️ Hub Layer"]
           WH[Writing Hub]
           CH[CAD Hub]
           CC[Control Center]
           EH[Expert Hub]
           MH[MedTrans Hub]
           RH[Research Hub]
       end
       
       subgraph CORE["⚙️ Core Services"]
           LLM[LLM Service]
           HF[Handler Framework]
           WF[Workflow System]
           NAV[Navigation Service]
       end
       
       subgraph DATA["💾 Data Layer"]
           PG[(PostgreSQL)]
           CACHE[(Redis Cache)]
           FILES[(File Storage)]
       end
       
       subgraph EXT["🔌 External"]
           MCP[MCP Servers]
           AI[AI Providers]
           N8N[n8n Workflows]
       end
       
       UI --> HUBS
       HUBS --> CORE
       CORE --> DATA
       CORE --> EXT

Schichten-Architektur
=====================

1. Frontend Layer
-----------------

+------------------+----------------------------------+
| Komponente       | Technologie                      |
+==================+==================================+
| Templates        | Django Templates + Jinja2        |
+------------------+----------------------------------+
| Styling          | Bootstrap 5 + Custom CSS         |
+------------------+----------------------------------+
| Interaktivität   | HTMX + Alpine.js                 |
+------------------+----------------------------------+
| Icons            | Bootstrap Icons                  |
+------------------+----------------------------------+
| REST API         | Django REST Framework            |
+------------------+----------------------------------+

2. Hub Layer
------------

Spezialisierte Django-Apps für verschiedene Anwendungsbereiche:

.. list-table:: Verfügbare Hubs
   :header-rows: 1
   :widths: 20 40 40

   * - Hub
     - Zweck
     - Key Features
   * - **Writing Hub**
     - Buchautoren-Unterstützung
     - Projects, Chapters, Characters, Worlds, Illustrations
   * - **CAD Hub**
     - Bauzeichnungs-Analyse
     - IFC Import, Raumbuch, GAEB Export, WoFlV
   * - **Control Center**
     - System-Administration
     - Agents, LLMs, Templates, Workflows, Master Data
   * - **Expert Hub**
     - Fachexperten-Wissen
     - Explosionsschutz, Compliance-Checks
   * - **MedTrans**
     - Medizinische Übersetzung
     - Translation, Terminology, Quality Assurance
   * - **Research Hub**
     - Recherche & Analyse
     - Web Search, Fact Check, Knowledge Base

3. Core Services
----------------

.. mermaid::

   classDiagram
       class LLMService {
           +get_client(provider)
           +generate(prompt)
           +generate_structured(prompt, schema)
       }
       
       class HandlerFramework {
           +InputHandlerRegistry
           +ProcessingHandlerRegistry
           +OutputHandlerRegistry
       }
       
       class WorkflowSystem {
           +execute_workflow(workflow_id)
           +get_status(execution_id)
       }
       
       class NavigationService {
           +get_sections(hub)
           +resolve_url(item, context)
       }

**LLM Service** (`apps/core/services/llm/`)
   Multi-Provider LLM-Integration (OpenAI, Anthropic, Google).
   Siehe :ref:`llm-technical-reference`.

**Handler Framework** (`apps/bfagent/services/handlers/`)
   Drei-Phasen-Verarbeitung: Input → Processing → Output.
   Siehe :ref:`handler-technical-reference`.

**Workflow System** (`apps/workflow_system/`)
   Workflow-Orchestrierung mit Status-Tracking.

**Navigation Service** (`apps/core/services/navigation/`)
   Dynamische DB-gesteuerte Navigation für alle Hubs.

4. Data Layer
-------------

+------------------+----------------------------------+
| Storage          | Verwendung                       |
+==================+==================================+
| PostgreSQL       | Hauptdatenbank für alle Models   |
+------------------+----------------------------------+
| Redis            | Caching, Session Storage         |
+------------------+----------------------------------+
| File Storage     | Media Files, Uploads, Exports    |
+------------------+----------------------------------+

App-Struktur
============

::

   apps/
   ├── api/                 # REST API Endpoints
   ├── bfagent/             # Core BFAgent Logic
   │   ├── services/
   │   │   ├── handlers/    # Handler Framework
   │   │   └── llm_client/  # Legacy LLM Client
   │   └── models.py        # Core Models
   │
   ├── core/                # Shared Core Components
   │   ├── models/          # Handler, Agent, Navigation
   │   ├── services/
   │   │   ├── llm/         # LLM Service (Primary)
   │   │   └── navigation/  # Navigation Service
   │   └── schemas/         # Pydantic Schemas
   │
   ├── control_center/      # Admin & Configuration
   ├── writing_hub/         # Book Writing Features
   ├── cad_hub/             # CAD/IFC Processing
   ├── expert_hub/          # Expert Knowledge
   ├── medtrans/            # Medical Translation
   ├── research/            # Research Tools
   │
   ├── workflow_system/     # Workflow Engine
   ├── image_generation/    # AI Image Generation
   └── mcp_hub/             # MCP Server Integration

Key Models
==========

Core Models
-----------

.. code-block:: python

   # apps/core/models/
   
   class Handler(models.Model):
       """Registrierter Handler mit Metriken."""
       code = models.CharField(unique=True)
       category = models.CharField(choices=CATEGORY_CHOICES)
       module_path = models.CharField()
       class_name = models.CharField()
       config_schema = models.JSONField()
   
   class Agent(models.Model):
       """AI Agent mit LLM-Konfiguration."""
       name = models.CharField()
       llm = models.ForeignKey('LLM')
       system_prompt = models.TextField()
   
   class NavigationSection(models.Model):
       """Hub-spezifische Navigation."""
       hub_code = models.CharField()
       name = models.CharField()
       order = models.IntegerField()
   
   class NavigationItem(models.Model):
       """Navigations-Eintrag mit URL-Pattern."""
       section = models.ForeignKey(NavigationSection)
       url_name = models.CharField()
       icon = models.CharField()

Domain Models
-------------

.. code-block:: python

   # apps/writing_hub/models.py
   
   class BookProject(models.Model):
       """Buchprojekt mit Metadaten."""
       title = models.CharField()
       genre = models.ForeignKey('Genre')
       status = models.ForeignKey('WritingStatus')
   
   class Chapter(models.Model):
       """Kapitel eines Buchprojekts."""
       project = models.ForeignKey(BookProject)
       title = models.CharField()
       content = models.TextField()
   
   class Character(models.Model):
       """Charakter mit Profil und Beziehungen."""
       project = models.ForeignKey(BookProject)
       name = models.CharField()
       description = models.TextField()
   
   class World(models.Model):
       """Welt/Setting mit Locations und Regeln."""
       project = models.ForeignKey(BookProject)
       name = models.CharField()
       geography = models.TextField()

Konfigurationsphilosophie
=========================

Zero-Hardcoding Prinzip
-----------------------

Alle Konfigurationen werden in der Datenbank gespeichert:

+------------------------+----------------------------------+
| Aspekt                 | DB-gesteuert durch               |
+========================+==================================+
| Navigation             | NavigationSection, NavigationItem|
+------------------------+----------------------------------+
| Workflows              | Workflow, WorkflowStep           |
+------------------------+----------------------------------+
| Agents                 | Agent, AgentAction               |
+------------------------+----------------------------------+
| LLM-Konfiguration      | LLM, LLMProvider                 |
+------------------------+----------------------------------+
| Handler                | Handler, HandlerCategory         |
+------------------------+----------------------------------+
| Master Data            | Genre, DomainType, DomainArt     |
+------------------------+----------------------------------+

Admin-First Design
------------------

Alle Entitäten sind über Django Admin verwaltbar:

.. code-block:: python

   # Beispiel: Navigation per Admin verwalten
   
   @admin.register(NavigationItem)
   class NavigationItemAdmin(admin.ModelAdmin):
       list_display = ['name', 'section', 'url_name', 'order']
       list_filter = ['section__hub_code']
       ordering = ['section', 'order']

Integration Points
==================

MCP Server
----------

BF Agent stellt mehrere MCP Server bereit:

+------------------+----------------------------------+
| Server           | Funktionen                       |
+==================+==================================+
| bfagent          | Domain Management, Handlers      |
+------------------+----------------------------------+
| bfagent-db       | Database Queries, Schema Info    |
+------------------+----------------------------------+
| code-quality     | Code Analysis, UI Consistency    |
+------------------+----------------------------------+
| test-generator   | Test Generation, Coverage        |
+------------------+----------------------------------+
| illustration     | ComfyUI Integration              |
+------------------+----------------------------------+

n8n Integration
---------------

Visuelle Workflow-Orchestrierung über n8n:

.. mermaid::

   flowchart LR
       N8N[n8n Workflow] --> API[Django REST API]
       API --> WF[Workflow System]
       WF --> H[Handlers]
       H --> DB[(Database)]

**API Endpoints:**

- ``POST /api/n8n/workflow/execute`` - Workflow starten
- ``GET /api/n8n/workflow/{id}/status`` - Status prüfen
- ``POST /api/n8n/characters/generate`` - Charaktere generieren

Deployment
==========

Docker Compose (Production)
---------------------------

.. code-block:: yaml

   services:
     bfagent-web:
       image: ghcr.io/achimdehnert/bfagent/bfagent-web:latest
       ports:
         - "8000:8000"
       environment:
         - DATABASE_URL=postgres://...
         - OPENAI_API_KEY=${OPENAI_API_KEY}
     
     postgres:
       image: postgres:15
       volumes:
         - postgres_data:/var/lib/postgresql/data
     
     redis:
       image: redis:7-alpine

Umgebungsvariablen
------------------

+------------------------+----------------------------------+
| Variable               | Beschreibung                     |
+========================+==================================+
| ``DATABASE_URL``       | PostgreSQL Connection String     |
+------------------------+----------------------------------+
| ``REDIS_URL``          | Redis Connection String          |
+------------------------+----------------------------------+
| ``OPENAI_API_KEY``     | OpenAI API Key                   |
+------------------------+----------------------------------+
| ``ANTHROPIC_API_KEY``  | Anthropic API Key                |
+------------------------+----------------------------------+
| ``SECRET_KEY``         | Django Secret Key                |
+------------------------+----------------------------------+
| ``DEBUG``              | Debug Mode (false in Production) |
+------------------------+----------------------------------+

Erweiterbarkeit
===============

Neuen Hub erstellen
-------------------

1. Django App erstellen:

.. code-block:: bash

   python manage.py startapp my_hub apps/my_hub

2. Models definieren:

.. code-block:: python

   # apps/my_hub/models.py
   from django.db import models
   
   class MyEntity(models.Model):
       name = models.CharField(max_length=200)
       # ...

3. Navigation registrieren:

.. code-block:: python

   # Management Command
   NavigationSection.objects.create(
       hub_code='my_hub',
       name='My Hub',
       icon='bi-star'
   )

4. Handler implementieren:

.. code-block:: python

   @ProcessingHandlerRegistry.register
   class MyHandler(BaseProcessingHandler):
       handler_name = "my_handler"
       # ...

Neuen LLM Provider
------------------

.. code-block:: python

   # apps/core/services/llm/my_provider.py
   
   class MyProviderClient(BaseLLMClient):
       provider = "myprovider"
       
       def _init_client(self):
           self._client = MySDK(api_key=self.config.api_key)
       
       def _generate(self, request):
           result = self._client.complete(...)
           return LLMResponse.success_response(...)

Siehe auch
==========

- :ref:`handler-framework-guide` - Handler Framework Benutzerhandbuch
- :ref:`ai-integration-guide` - LLM Integration Guide
- :doc:`agent-architecture` - Agent-Architektur im Detail
- :doc:`/hubs/index` - Hub-Übersicht
