.. BF Agent documentation master file

===============================================
BF Agent - Universal Workflow Orchestration
===============================================

.. image:: https://img.shields.io/badge/Django-5.0-green
   :alt: Django 5.0

.. image:: https://img.shields.io/badge/Python-3.11+-blue
   :alt: Python 3.11+

.. image:: https://img.shields.io/badge/License-Proprietary-red
   :alt: License

**BF Agent** ist eine Django-basierte Universal Workflow Orchestration Platform 
mit Zero-Hardcoding-Philosophie. Alle Konfigurationen sind datenbankgesteuert 
und über Django Admin verwaltbar.

.. note::
   Diese Dokumentation wird automatisch aus dem Quellcode generiert (Single Source of Truth).

Schnellstart
============

.. code-block:: bash

   # Installation
   pip install -r requirements.txt
   
   # Django Setup
   python manage.py migrate
   python manage.py createsuperuser
   
   # Server starten
   python manage.py runserver

Features
========

.. grid:: 2

   .. grid-item-card:: 🔧 Handler Framework
      :link: reference/handlers
      :link-type: doc

      38+ spezialisierte Handler für verschiedene Aufgaben.
      Drei-Phasen-Verarbeitung: Input → Processing → Output.

   .. grid-item-card:: 🌐 Spezialisierte Hubs
      :link: hubs/index
      :link-type: doc

      Writing Hub, CAD Hub, Research Hub, 
      Control Center und weitere Hubs.

   .. grid-item-card:: 🤖 AI Integration
      :link: guides/ai-integration
      :link-type: doc

      Multi-Provider-Support: OpenAI, Claude, Ollama.
      63% AI-Integration über alle Handler.

   .. grid-item-card:: 📊 Zero-Hardcoding
      :link: guides/configuration
      :link-type: doc

      Datenbankgesteuerte Konfiguration.
      Runtime-Änderungen ohne Deployment.


Architektur Übersicht
=====================

.. mermaid::

   flowchart TB
       subgraph "BF Agent Core"
           HF[Handler Framework]
           PR[Plugin Registry]
           CE[Context Engine]
       end
       
       subgraph "Hubs"
           H1[📚 Writing Hub]
           H2[📐 CAD Hub]
           H3[🔍 Research Hub]
           H4[⚙️ Control Center]
           H5[🔌 MCP Hub]
       end
       
       subgraph "External"
           AI[AI Providers]
           N8N[n8n Workflows]
           DB[(PostgreSQL)]
       end
       
       HF --> H1
       HF --> H2
       HF --> H3
       HF --> H4
       HF --> H5
       
       CE --> AI
       PR --> N8N
       HF --> DB


Inhaltsverzeichnis
==================

.. toctree::
   :maxdepth: 2
   :caption: 🚀 Erste Schritte

   guides/quickstart
   guides/installation
   guides/configuration

.. toctree::
   :maxdepth: 2
   :caption: 📚 Benutzerhandbuch

   guides/ai_integration
   guides/handler_framework
   guides/prompt_system_user

.. toctree::
   :maxdepth: 2
   :caption: 🏗️ Hubs

   hubs/index
   hubs/writing-hub
   hubs/cad-hub
   hubs/control-center
   hubs/research-hub
   hubs/mcp-hub
   hubs/expert-hub

.. toctree::
   :maxdepth: 2
   :caption: 🔌 MCP Server

   mcp/index
   mcp/bfagent_mcp
   mcp/bfagent_db_mcp
   mcp/code_quality_mcp
   mcp/test_generator_mcp
   mcp/illustration_mcp
   mcp/deployment_mcp

.. toctree::
   :maxdepth: 2
   :caption: 🔧 API Referenz

   reference/handlers
   reference/models
   reference/handler_framework_technical
   reference/schemas
   reference/llm_technical
   reference/prompt_system_technical

.. toctree::
   :maxdepth: 2
   :caption: 🧠 Konzepte

   concepts/system-architecture
   concepts/agent-architecture
   concepts/event-driven-architecture

.. toctree::
   :maxdepth: 2
   :caption: 👨‍💻 Entwickler

   developer/architecture
   developer/handler-development
   developer/testing
   developer/contributing

.. toctree::
   :maxdepth: 1
   :caption: 📋 Anhang

   changelog
   glossary


Indizes und Tabellen
====================

* :ref:`genindex` - Allgemeiner Index
* :ref:`modindex` - Modul-Index
* :ref:`search` - Suche


Status
======

+-------------------+------------+-------------+
| Hub               | Status     | Handler     |
+===================+============+=============+
| Writing Hub       | ✅ Prod    | 5           |
+-------------------+------------+-------------+
| CAD Hub           | ✅ Prod    | 5           |
+-------------------+------------+-------------+
| Research Hub      | ✅ Prod    | 3           |
+-------------------+------------+-------------+
| Control Center    | ✅ Prod    | -           |
+-------------------+------------+-------------+
| MCP Hub           | ✅ Prod    | -           |
+-------------------+------------+-------------+
| Expert Hub        | 🟡 Beta    | 2           |
+-------------------+------------+-------------+


.. seealso::

   - `Django Documentation <https://docs.djangoproject.com/>`_
   - `Pydantic Documentation <https://docs.pydantic.dev/>`_
   - `n8n Documentation <https://docs.n8n.io/>`_
