.. _handler-framework-guide:

==========================================
Handler Framework - Benutzerhandbuch
==========================================

.. contents:: Inhalt
   :local:
   :depth: 2

Übersicht
=========

Das **Handler Framework** ist das zentrale Erweiterungssystem von BF Agent.
Es ermöglicht die modulare Verarbeitung von Daten in drei Phasen:

.. mermaid::

   flowchart LR
       subgraph Input["📥 Input Phase"]
           I1[Project Fields]
           I2[Character Data]
           I3[User Input]
       end
       
       subgraph Processing["⚙️ Processing Phase"]
           P1[LLM Processor]
           P2[Template Renderer]
           P3[Framework Generator]
       end
       
       subgraph Output["📤 Output Phase"]
           O1[Chapter Creator]
           O2[Markdown Exporter]
           O3[Text Field Writer]
       end
       
       Input --> Processing --> Output

**Drei-Phasen-Architektur:**

1. **Input Handler** - Sammeln Daten aus verschiedenen Quellen
2. **Processing Handler** - Transformieren und verarbeiten Daten
3. **Output Handler** - Schreiben Ergebnisse in Ziele

Schnellstart
============

1. Eigenen Handler erstellen
----------------------------

.. code-block:: python

   from apps.bfagent.services.handlers.base.processing import BaseProcessingHandler
   from apps.bfagent.services.handlers.registries import ProcessingHandlerRegistry
   
   @ProcessingHandlerRegistry.register
   class MyTextProcessor(BaseProcessingHandler):
       """Verarbeitet Text mit eigener Logik."""
       
       handler_name = "my_text_processor"
       handler_version = "1.0.0"
       description = "Verarbeitet Text mit eigener Logik"
       
       def validate_config(self):
           # Konfiguration validieren
           if "mode" not in self.config:
               raise ValueError("'mode' is required in config")
       
       def process(self, input_data, context):
           mode = self.config["mode"]
           
           if mode == "uppercase":
               return input_data.upper()
           elif mode == "lowercase":
               return input_data.lower()
           else:
               return input_data

2. Handler verwenden
--------------------

.. code-block:: python

   from apps.bfagent.services.handlers.registries import ProcessingHandlerRegistry
   
   # Handler-Klasse abrufen
   handler_class = ProcessingHandlerRegistry.get("my_text_processor")
   
   # Handler instanziieren
   handler = handler_class(config={"mode": "uppercase"})
   
   # Daten verarbeiten
   result = handler.process("Hello World", context={})
   # result = "HELLO WORLD"

3. Handler mit Datenbank synchronisieren
----------------------------------------

.. code-block:: bash

   # Alle registrierten Handler in DB synchronisieren
   python manage.py sync_handlers
   
   # Vorschau ohne Änderungen
   python manage.py sync_handlers --dry-run

Handler-Typen
=============

Input Handler
-------------

Input Handler sammeln Daten aus verschiedenen Quellen:

.. code-block:: python

   from apps.bfagent.services.handlers.base.input import BaseInputHandler
   from apps.bfagent.services.handlers.registries import InputHandlerRegistry
   
   @InputHandlerRegistry.register
   class MyDataCollector(BaseInputHandler):
       """Sammelt Daten aus einer API."""
       
       handler_name = "api_data_collector"
       handler_version = "1.0.0"
       description = "Sammelt Daten von externer API"
       
       # Optional: Caching aktivieren
       cache_enabled = True
       cache_ttl = 300  # 5 Minuten
       
       def validate_config(self):
           if "api_url" not in self.config:
               raise ValueError("'api_url' is required")
       
       def collect(self, context):
           """
           Hauptmethode für Input Handler.
           
           Args:
               context: Enthält 'project', 'agent', etc.
               
           Returns:
               Dictionary mit gesammelten Daten
           """
           import requests
           
           response = requests.get(self.config["api_url"])
           return {"data": response.json()}

**Verfügbare Input Handler:**

+------------------------+----------------------------------------+
| Handler                | Beschreibung                           |
+========================+========================================+
| ``project_fields``     | Lädt Felder vom BookProject            |
+------------------------+----------------------------------------+
| ``chapter_data``       | Lädt Kapitel-Informationen             |
+------------------------+----------------------------------------+
| ``character_data``     | Lädt Charakter-Daten                   |
+------------------------+----------------------------------------+
| ``world_data``         | Lädt Welt-/Setting-Daten               |
+------------------------+----------------------------------------+
| ``user_input``         | Verarbeitet Benutzereingaben           |
+------------------------+----------------------------------------+

Processing Handler
------------------

Processing Handler transformieren und verarbeiten Daten:

.. code-block:: python

   from apps.bfagent.services.handlers.base.processing import BaseProcessingHandler
   from apps.bfagent.services.handlers.registries import ProcessingHandlerRegistry
   
   @ProcessingHandlerRegistry.register
   class SentimentAnalyzer(BaseProcessingHandler):
       """Analysiert Sentiment von Texten."""
       
       handler_name = "sentiment_analyzer"
       handler_version = "1.0.0"
       description = "Analysiert Text-Sentiment"
       
       # Handler-Fähigkeiten
       supports_streaming = False
       supports_async = True
       
       def validate_config(self):
           pass  # Keine spezielle Konfiguration nötig
       
       def process(self, input_data, context):
           """
           Hauptmethode für Processing Handler.
           
           Args:
               input_data: Daten vom vorherigen Handler
               context: Runtime-Kontext
               
           Returns:
               Verarbeitete Daten
           """
           # Einfache Sentiment-Analyse
           positive_words = ["gut", "super", "toll", "schön"]
           negative_words = ["schlecht", "übel", "furchtbar"]
           
           text = input_data.lower()
           score = sum(1 for w in positive_words if w in text)
           score -= sum(1 for w in negative_words if w in text)
           
           return {
               "text": input_data,
               "sentiment_score": score,
               "sentiment": "positive" if score > 0 else "negative" if score < 0 else "neutral"
           }

**Verfügbare Processing Handler:**

+------------------------+----------------------------------------+
| Handler                | Beschreibung                           |
+========================+========================================+
| ``llm_processor``      | Verarbeitet mit LLM                    |
+------------------------+----------------------------------------+
| ``template_renderer``  | Rendert Jinja2 Templates               |
+------------------------+----------------------------------------+
| ``framework_generator``| Generiert Story-Frameworks             |
+------------------------+----------------------------------------+

Output Handler
--------------

Output Handler schreiben Ergebnisse in verschiedene Ziele:

.. code-block:: python

   from apps.bfagent.services.handlers.base.output import BaseOutputHandler
   from apps.bfagent.services.handlers.registries import OutputHandlerRegistry
   
   @OutputHandlerRegistry.register
   class JsonFileWriter(BaseOutputHandler):
       """Schreibt Daten als JSON-Datei."""
       
       handler_name = "json_file_writer"
       handler_version = "1.0.0"
       description = "Schreibt JSON-Dateien"
       
       # Output Handler Fähigkeiten
       supports_multiple_objects = True
       supports_nested_data = True
       supports_validation = True
       supports_preview = True
       supports_rollback = True
       
       def validate_config(self):
           if "output_path" not in self.config:
               raise ValueError("'output_path' is required")
       
       def write(self, processed_data, context):
           """
           Hauptmethode für Output Handler.
           
           Args:
               processed_data: Verarbeitete Daten
               context: Runtime-Kontext
               
           Returns:
               Ergebnis der Schreiboperation
           """
           import json
           from pathlib import Path
           
           output_path = Path(self.config["output_path"])
           output_path.write_text(json.dumps(processed_data, indent=2))
           
           return {
               "success": True,
               "path": str(output_path),
               "bytes_written": output_path.stat().st_size
           }

**Verfügbare Output Handler:**

+------------------------+----------------------------------------+
| Handler                | Beschreibung                           |
+========================+========================================+
| ``chapter_creator``    | Erstellt Kapitel in DB                 |
+------------------------+----------------------------------------+
| ``markdown_exporter``  | Exportiert als Markdown                |
+------------------------+----------------------------------------+
| ``simple_text_field``  | Schreibt in Textfelder                 |
+------------------------+----------------------------------------+

Konfiguration
=============

Handler-Konfiguration über Pydantic
-----------------------------------

Verwenden Sie Pydantic-Schemas für typsichere Konfiguration:

.. code-block:: python

   from pydantic import BaseModel, Field
   from typing import List, Optional
   
   class MyHandlerConfig(BaseModel):
       """Konfiguration für MyHandler."""
       
       api_url: str = Field(..., description="API Endpoint URL")
       timeout: int = Field(30, ge=1, le=300, description="Timeout in Sekunden")
       retry_count: int = Field(3, ge=0, le=10)
       headers: Optional[dict] = None
   
   class MyHandler(BaseProcessingHandler):
       handler_name = "my_handler"
       
       def validate_config(self):
           # Pydantic validiert automatisch
           MyHandlerConfig(**self.config)

Konfiguration in der Datenbank
------------------------------

Handler-Konfigurationen werden im ``Handler``-Model gespeichert:

.. code-block:: python

   from apps.core.models import Handler
   
   # Handler aus DB laden
   handler_def = Handler.objects.get(code="my_handler")
   
   # Konfiguration validieren
   handler_def.validate_config({"api_url": "https://api.example.com"})
   
   # Handler-Klasse dynamisch laden
   handler_class = handler_def.get_implementation()

Handler-Registrierung
=====================

Automatische Registrierung (Decorator)
--------------------------------------

.. code-block:: python

   from apps.bfagent.services.handlers.registries import ProcessingHandlerRegistry
   
   @ProcessingHandlerRegistry.register
   class MyHandler(BaseProcessingHandler):
       handler_name = "my_handler"
       # ...

Manuelle Registrierung
----------------------

.. code-block:: python

   from apps.bfagent.services.handlers.registries import ProcessingHandlerRegistry
   
   class MyHandler(BaseProcessingHandler):
       handler_name = "my_handler"
       # ...
   
   # Explizit registrieren
   ProcessingHandlerRegistry.register(MyHandler)

Handler auflisten
-----------------

.. code-block:: python

   from apps.bfagent.services.handlers.registries import (
       InputHandlerRegistry,
       ProcessingHandlerRegistry,
       OutputHandlerRegistry,
       get_all_handlers
   )
   
   # Alle Handler eines Typs
   input_handlers = InputHandlerRegistry.list_handlers()
   # ['project_fields', 'chapter_data', 'character_data', ...]
   
   # Handler-Info für UI/API
   all_info = get_all_handlers()
   # {
   #     "input": [...],
   #     "processing": [...],
   #     "output": [...]
   # }

Best Practices
==============

1. Immer ``handler_name`` definieren
------------------------------------

.. code-block:: python

   class MyHandler(BaseProcessingHandler):
       handler_name = "my_handler"  # PFLICHT!
       handler_version = "1.0.0"    # Empfohlen
       description = "Was macht dieser Handler"  # Empfohlen

2. Konfiguration validieren
---------------------------

.. code-block:: python

   def validate_config(self):
       required = ["field1", "field2"]
       for field in required:
           if field not in self.config:
               raise ValueError(f"'{field}' is required")

3. Logging verwenden
--------------------

.. code-block:: python

   def process(self, input_data, context):
       self.logger.info("Processing started", input_size=len(input_data))
       
       try:
           result = self._do_processing(input_data)
           self.logger.info("Processing completed", output_size=len(result))
           return result
       except Exception as e:
           self.logger.error("Processing failed", error=str(e))
           raise

4. Decorators für Monitoring nutzen
-----------------------------------

.. code-block:: python

   from apps.bfagent.services.handlers.decorators import (
       with_logging,
       with_performance_monitoring
   )
   
   class MyHandler(BaseProcessingHandler):
       @with_logging
       @with_performance_monitoring
       def process(self, input_data, context):
           # Automatisches Logging und Metriken
           return self._process(input_data)

5. Exceptions korrekt werfen
----------------------------

.. code-block:: python

   from apps.bfagent.services.handlers.exceptions import (
       InputHandlerException,
       ProcessingHandlerException,
       OutputHandlerException
   )
   
   def process(self, input_data, context):
       if not input_data:
           raise ProcessingHandlerException(
               message="Empty input data",
               handler_name=self.handler_name,
               context={"input_type": type(input_data).__name__}
           )

Fehlerbehebung
==============

Handler nicht gefunden
----------------------

.. code-block:: python

   # Prüfen ob Handler registriert ist
   from apps.bfagent.services.handlers.registries import ProcessingHandlerRegistry
   
   print(ProcessingHandlerRegistry.list_handlers())
   # Falls leer: Handler-Modul wurde nicht importiert
   
   # Auto-Registrierung manuell auslösen
   from apps.bfagent.services.handlers.registries import auto_register_handlers
   auto_register_handlers()

Konfigurationsfehler
--------------------

.. code-block:: python

   try:
       handler = MyHandler(config={"invalid": "config"})
   except ConfigurationException as e:
       print(f"Config Error: {e.message}")
       print(f"Handler: {e.handler_name}")
       print(f"Context: {e.context}")

Handler synchronisieren
-----------------------

.. code-block:: bash

   # Kategorien laden (einmalig)
   python manage.py load_handler_categories
   
   # Handler synchronisieren
   python manage.py sync_handlers --force

Weiterführende Dokumentation
============================

- :ref:`handler-technical-reference` - Technische API-Referenz
- :doc:`../reference/handlers` - Handler API Übersicht
- :doc:`../concepts/agent-architecture` - Agent-Architektur
