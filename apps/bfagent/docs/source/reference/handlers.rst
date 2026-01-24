Handler API-Referenz
====================

Diese Seite dokumentiert alle verfügbaren Handler im BF Agent Framework.
Die Dokumentation wird automatisch aus den Docstrings generiert.

.. contents:: Inhaltsverzeichnis
   :local:
   :depth: 2


Übersicht
---------

Das Handler Framework folgt dem **Drei-Phasen-Muster**:

.. mermaid::

   flowchart LR
       I[Input Phase] --> P[Processing Phase] --> O[Output Phase]
       
       subgraph "Input"
           I1[Validation]
           I2[Context Building]
       end
       
       subgraph "Processing"
           P1[Business Logic]
           P2[AI Integration]
       end
       
       subgraph "Output"
           O1[Formatting]
           O2[Persistence]
       end


Writing Hub Handler
-------------------

Handler für die Bucherstellung.

.. note::
   Die Handler-Dokumentation wird automatisch aus den Docstrings generiert,
   sobald Django korrekt initialisiert ist.

.. code-block:: python

   # Beispiel: Writing Hub Handlers
   from apps.writing_hub.handlers import OutlineHandler, ChapterWriterHandler
   
   # Outline Handler
   handler = OutlineHandler()
   result = await handler.execute(context)


CAD Hub Handler
---------------

Handler für die CAD-Analyse (IFC, DWG, GAEB).

.. code-block:: python

   # Beispiel: CAD Hub Views
   from apps.cad_hub.views import CADUploadView, IFCContentOverviewView
   
   # IFC-Analyse durchführen
   # Siehe apps/cad_hub/handlers/ für Handler-Implementierung


Expert Hub Handler
------------------

Handler für Explosionsschutz-Analysen.

.. code-block:: python

   # Beispiel: Expert Hub Handler
   from apps.expert_hub.handlers import ExSchutzAnalysisHandler
   
   # Analyse starten
   handler = ExSchutzAnalysisHandler()
   result = await handler.analyze(document_id)


Handler Konfiguration
---------------------

Handler werden über die Datenbank konfiguriert:

.. code-block:: python

   from apps.core.models import Handler
   
   # Handler in der Datenbank registrieren
   handler = Handler.objects.create(
       name="outline_handler",
       handler_class="apps.writing_hub.handlers.OutlineHandler",
       domain="writing_hub",
       config={
           "timeout": 300,
           "retry_count": 3,
           "ai_enabled": True,
       }
   )

.. list-table:: Handler-Konfigurationsoptionen
   :header-rows: 1
   :widths: 20 15 65

   * - Option
     - Typ
     - Beschreibung
   * - ``timeout``
     - int
     - Maximale Ausführungszeit in Sekunden
   * - ``retry_count``
     - int
     - Anzahl der Wiederholungsversuche bei Fehlern
   * - ``ai_enabled``
     - bool
     - AI-Integration aktiviert
   * - ``async_mode``
     - bool
     - Asynchrone Ausführung via Celery


Handler entwickeln
------------------

.. seealso::

   Siehe :doc:`/developer/handler-development` für eine vollständige Anleitung
   zur Handler-Entwicklung.


Beispiel: Eigener Handler
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from bf_agent.handlers.base import BaseHandler
   from pydantic import BaseModel
   
   class MyInputSchema(BaseModel):
       """Input Schema für meinen Handler."""
       project_id: str
       options: dict = {}
   
   class MyHandler(BaseHandler):
       """
       Mein eigener Handler.
       
       Dieser Handler macht etwas Nützliches.
       
       Attributes:
           input_schema: Schema für Eingabedaten
           output_schema: Schema für Ausgabedaten
       
       Example:
           >>> handler = MyHandler()
           >>> result = await handler.execute({"project_id": "123"})
       """
       
       input_schema = MyInputSchema
       
       async def validate(self, context: MyInputSchema) -> None:
           """Validiert die Eingabedaten."""
           if not context.project_id:
               raise ValueError("project_id ist erforderlich")
       
       async def process(self, context: MyInputSchema) -> dict:
           """Führt die Hauptlogik aus."""
           # Business Logic hier
           return {"status": "success"}
