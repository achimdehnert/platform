.. _event-driven-architecture:

==========================================
Event-Driven Architecture (EDA)
==========================================

.. contents:: Inhalt
   :local:
   :depth: 2

.. note::
   Diese Funktionalität ist hinter Feature Flags implementiert und standardmäßig deaktiviert.
   Aktivierung erfolgt schrittweise: Local → Staging → Production.

Übersicht
=========

BF Agent unterstützt eine **Event-Driven Architecture** für lose gekoppelte 
Kommunikation zwischen Komponenten. Das System verwendet Django Signals als 
Basis und ist vollständig Feature-Flag-gesteuert.

.. mermaid::

   flowchart LR
       subgraph Producer["📤 Event Producer"]
           H1[ChapterWriterHandler]
           H2[CharacterHandler]
           H3[Other Handlers]
       end
       
       subgraph Bus["🚌 Event Bus"]
           EB[event_bus.publish]
           FF{Feature Flag?}
       end
       
       subgraph Consumer["📥 Event Consumers"]
           C1[Illustration Service]
           C2[Analytics Service]
           C3[Notification Service]
       end
       
       H1 --> EB
       H2 --> EB
       H3 --> EB
       EB --> FF
       FF -->|ON| C1
       FF -->|ON| C2
       FF -->|ON| C3
       FF -->|OFF| X[No-Op]

Komponenten
===========

Feature Flags
-------------

Alle neuen Funktionen sind hinter Feature Flags geschützt:

.. code-block:: python

   # apps/core/feature_flags.py
   FEATURES = {
       "USE_EVENT_BUS": False,      # Event-Driven Architecture
       "USE_HUB_REGISTRY": False,   # Dynamic Hub Management
       "USE_ASYNC_EVENTS": False,   # Async Event Processing
   }

**Aktivierung per Environment Variable:**

.. code-block:: bash

   export FEATURE_FLAG_USE_EVENT_BUS=true

**Aktivierung im Code:**

.. code-block:: python

   from apps.core.feature_flags import enable_feature, disable_feature
   
   enable_feature("USE_EVENT_BUS")   # Aktivieren
   disable_feature("USE_EVENT_BUS")  # Deaktivieren

Event Types
-----------

Vordefinierte Event-Typen in ``apps/core/events.py``:

.. list-table:: Event Types
   :header-rows: 1
   :widths: 30 70

   * - Event
     - Beschreibung
   * - ``CHAPTER_CREATED``
     - Neues Kapitel wurde erstellt
   * - ``CHAPTER_UPDATED``
     - Kapitel wurde aktualisiert
   * - ``CONTENT_GENERATED``
     - Inhalt wurde via LLM generiert
   * - ``CHARACTER_CREATED``
     - Neuer Charakter wurde erstellt
   * - ``WORKFLOW_STARTED``
     - Workflow wurde gestartet
   * - ``WORKFLOW_COMPLETED``
     - Workflow wurde abgeschlossen
   * - ``HUB_ACTIVATED``
     - Hub wurde aktiviert
   * - ``HUB_DEACTIVATED``
     - Hub wurde deaktiviert

Event Bus
---------

Der zentrale Event Bus in ``apps/core/event_bus.py``:

.. code-block:: python

   from apps.core.event_bus import event_bus
   from apps.core.events import Events
   
   # Event publizieren
   event_bus.publish(
       Events.CONTENT_GENERATED,
       source="ChapterWriterHandler",
       content_type="chapter",
       content_id=123,
       word_count=2500
   )
   
   # Event abonnieren
   @event_bus.subscribe(Events.CONTENT_GENERATED)
   def on_content_generated(content_type, content_id, **kwargs):
       print(f"Content {content_id} generated!")

Integration in Handler
======================

Beispiel: ChapterWriterHandler
------------------------------

.. code-block:: python

   # apps/writing_hub/handlers/chapter_writer_handler.py
   
   from apps.core.event_bus import event_bus
   from apps.core.events import Events
   
   class ChapterWriterHandler:
       def write_chapter(self, context):
           result = self._write_chapter_single(context, llm, model_max)
           
           # Event nur wenn Feature Flag aktiv
           if result.get('success'):
               event_bus.publish(
                   Events.CONTENT_GENERATED,
                   source="ChapterWriterHandler",
                   content_type="chapter",
                   content_id=context.chapter_id,
                   project_id=context.project_id,
                   word_count=result.get('word_count', 0),
               )
           
           return result

Hub Registry
============

Dynamische Hub-Verwaltung via ``apps/core/hub_registry.py``:

.. code-block:: python

   from apps.core.hub_registry import hub_registry
   
   # Alle Hubs auflisten
   hubs = hub_registry.get_all_hubs()
   
   # Hub aktivieren/deaktivieren
   hub_registry.activate_hub("writing_hub")
   hub_registry.deactivate_hub("cad_hub")
   
   # Nur aktive Hubs
   active = hub_registry.get_active_hubs()

Testing
=======

Management Command für Tests:

.. code-block:: bash

   # Ohne Event-Publishing (Feature OFF)
   python manage.py test_event_bus
   
   # Mit Event-Publishing (Feature temporär ON)
   python manage.py test_event_bus --enable

Rollback
========

Bei Problemen kann das System sofort zurückgesetzt werden:

1. **Feature Flag deaktivieren:**

   .. code-block:: bash
   
      export FEATURE_FLAG_USE_EVENT_BUS=false

2. **Git Rollback (falls nötig):**

   .. code-block:: bash
   
      git checkout f0e6a1e5  # Pre-EDA Commit

Migration Path
==============

.. list-table:: Rollout Plan
   :header-rows: 1
   :widths: 20 30 50

   * - Phase
     - Umgebung
     - Aktion
   * - 1
     - Local Dev
     - Feature Flags manuell aktivieren, testen
   * - 2
     - Staging
     - Environment Variables setzen, E2E Tests
   * - 3
     - Production
     - Schrittweise aktivieren, Monitoring

Commits
=======

- ``f0e6a1e5`` - Pre-EDA Rollback Point
- ``5314584f`` - Event System Foundation
- ``5e384f23`` - ChapterWriterHandler mit Event-Publishing
