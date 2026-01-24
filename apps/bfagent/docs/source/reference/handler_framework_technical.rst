.. _handler-technical-reference:

==========================================
Handler Framework - Technische Referenz
==========================================

.. contents:: Inhalt
   :local:
   :depth: 3

Architektur
===========

Das Handler Framework folgt einer **Pipeline-Architektur** mit drei Phasen:

.. mermaid::

   classDiagram
       class HandlerRegistry {
           <<abstract>>
           +_handlers: Dict
           +_expected_handler_type: str
           +register(handler_class) Type
           +get(handler_name) Type
           +get_all() Dict
           +list_handlers() List
       }
       
       class InputHandlerRegistry {
           +_expected_handler_type = "input"
       }
       
       class ProcessingHandlerRegistry {
           +_expected_handler_type = "processing"
       }
       
       class OutputHandlerRegistry {
           +_expected_handler_type = "output"
       }
       
       class BaseInputHandler {
           <<abstract>>
           +handler_type = "input"
           +handler_name: str
           +handler_version: str
           +cache_enabled: bool
           +cache_ttl: int
           +validate_config()
           +collect(context) Dict
       }
       
       class BaseProcessingHandler {
           <<abstract>>
           +handler_type = "processing"
           +supports_streaming: bool
           +supports_async: bool
           +validate_config()
           +process(input_data, context) Any
       }
       
       class BaseOutputHandler {
           <<abstract>>
           +handler_type = "output"
           +supports_multiple_objects: bool
           +supports_validation: bool
           +validate_config()
           +write(processed_data, context) Dict
       }
       
       HandlerRegistry <|-- InputHandlerRegistry
       HandlerRegistry <|-- ProcessingHandlerRegistry
       HandlerRegistry <|-- OutputHandlerRegistry

Modul-Struktur
==============

::

   apps/bfagent/services/handlers/
   ├── __init__.py              # Public API
   ├── registries.py            # Handler Registries
   ├── decorators.py            # @with_logging, @with_performance_monitoring
   ├── exceptions.py            # Exception Hierarchy
   ├── schemas.py               # Pydantic Config Schemas
   ├── config_models.py         # Configuration Models
   │
   ├── base/                    # Abstract Base Classes
   │   ├── __init__.py
   │   ├── input.py             # BaseInputHandler
   │   ├── processing.py        # BaseProcessingHandler
   │   └── output.py            # BaseOutputHandler
   │
   ├── input/                   # Input Handler Implementations
   │   ├── __init__.py
   │   ├── project_fields.py
   │   ├── chapter_data.py
   │   ├── character_data.py
   │   ├── user_input.py
   │   └── world_data.py
   │
   ├── processing/              # Processing Handler Implementations
   │   ├── __init__.py
   │   ├── llm_processor.py
   │   ├── template_renderer.py
   │   └── framework_generator.py
   │
   └── output/                  # Output Handler Implementations
       ├── __init__.py
       ├── chapter_creator.py
       ├── markdown_file.py
       └── simple_text_field.py

Registry API
============

HandlerRegistry (Base)
----------------------

.. py:class:: HandlerRegistry

   Abstrakte Basisklasse für alle Handler-Registries.
   
   .. py:attribute:: _handlers
      :type: Dict[str, Type]
      
      Dictionary der registrierten Handler: ``{handler_name: handler_class}``
   
   .. py:attribute:: _expected_handler_type
      :type: str
      
      Erwarteter ``handler_type`` für diese Registry.
   
   .. py:classmethod:: register(handler_class)
   
      Registriert eine Handler-Klasse.
      
      :param handler_class: Handler-Klasse mit ``handler_name`` Attribut
      :return: Die Handler-Klasse (für Decorator-Verwendung)
      :raises ValueError: Wenn ``handler_name`` fehlt oder bereits registriert
      :raises TypeError: Wenn ``handler_type`` nicht passt
      
      **Beispiel als Decorator:**
      
      .. code-block:: python
      
         @InputHandlerRegistry.register
         class MyHandler(BaseInputHandler):
             handler_name = "my_handler"
      
      **Beispiel direkt:**
      
      .. code-block:: python
      
         InputHandlerRegistry.register(MyHandler)
   
   .. py:classmethod:: get(handler_name)
   
      Gibt Handler-Klasse zurück.
      
      :param handler_name: Name des Handlers
      :return: Handler-Klasse
      :raises ValueError: Wenn Handler nicht gefunden
   
   .. py:classmethod:: get_all()
   
      Gibt alle registrierten Handler zurück.
      
      :return: ``Dict[str, Type]`` - Kopie des Handler-Dictionaries
   
   .. py:classmethod:: list_handlers()
   
      Gibt Liste aller Handler-Namen zurück.
      
      :return: ``List[str]``
   
   .. py:classmethod:: get_handler_info()
   
      Gibt detaillierte Infos für UI/API zurück.
      
      :return: Liste von Handler-Info-Dictionaries

Spezialisierte Registries
-------------------------

.. py:class:: InputHandlerRegistry(HandlerRegistry)

   Registry für Input Handler.
   
   ``_expected_handler_type = "input"``

.. py:class:: ProcessingHandlerRegistry(HandlerRegistry)

   Registry für Processing Handler.
   
   ``_expected_handler_type = "processing"``

.. py:class:: OutputHandlerRegistry(HandlerRegistry)

   Registry für Output Handler.
   
   ``_expected_handler_type = "output"``

Utility Functions
-----------------

.. py:function:: get_all_handlers()

   Gibt alle Handler aller Registries zurück.
   
   :return: Dict mit ``{"input": [...], "processing": [...], "output": [...]}``

.. py:function:: auto_register_handlers()

   Registriert alle Standard-Handler automatisch.
   
   Wird von ``AppConfig.ready()`` aufgerufen.

Base Handler Classes
====================

BaseInputHandler
----------------

.. py:class:: BaseInputHandler

   Abstrakte Basisklasse für Input Handler.
   
   **Klassenattribute:**
   
   .. py:attribute:: handler_type
      :value: "input"
      
      Typ-Identifier (nicht ändern!)
   
   .. py:attribute:: handler_name
      :type: str
      :value: None
      
      **Pflicht!** Eindeutiger Identifier.
   
   .. py:attribute:: handler_version
      :type: str
      :value: "2.0.0"
      
      Semantic Version.
   
   .. py:attribute:: description
      :type: str
      :value: ""
      
      Menschenlesbare Beschreibung.
   
   .. py:attribute:: cache_enabled
      :type: bool
      :value: False
      
      Caching aktivieren.
   
   .. py:attribute:: cache_ttl
      :type: int
      :value: 300
      
      Cache-TTL in Sekunden.
   
   **Methoden:**
   
   .. py:method:: __init__(config)
   
      Initialisiert Handler mit Konfiguration.
      
      :param config: Handler-spezifische Konfiguration
      :raises ConfigurationException: Bei ungültiger Konfiguration
   
   .. py:method:: validate_config()
      :abstractmethod:
      
      Validiert Handler-Konfiguration.
      
      **Muss implementiert werden!**
      
      :raises ValueError: Bei ungültiger Konfiguration
   
   .. py:method:: collect(context)
      :abstractmethod:
      
      Sammelt Daten aus Quelle.
      
      **Muss implementiert werden!**
      
      :param context: Runtime-Kontext mit ``project``, ``agent``, etc.
      :return: Dictionary mit gesammelten Daten
      :raises InputHandlerException: Bei Fehlern
   
   .. py:method:: _validate_context(context, required_keys)
   
      Helper zur Validierung von Kontext-Keys.
      
      :param context: Kontext-Dictionary
      :param required_keys: Liste erforderlicher Keys
      :raises InputHandlerException: Bei fehlenden Keys

BaseProcessingHandler
---------------------

.. py:class:: BaseProcessingHandler

   Abstrakte Basisklasse für Processing Handler.
   
   **Zusätzliche Klassenattribute:**
   
   .. py:attribute:: supports_streaming
      :type: bool
      :value: False
      
      Unterstützt Streaming-Verarbeitung.
   
   .. py:attribute:: supports_async
      :type: bool
      :value: False
      
      Unterstützt asynchrone Ausführung.
   
   **Methoden:**
   
   .. py:method:: process(input_data, context)
      :abstractmethod:
      
      Verarbeitet Eingabedaten.
      
      **Muss implementiert werden!**
      
      :param input_data: Daten vom vorherigen Handler
      :param context: Runtime-Kontext
      :return: Verarbeitete Daten
      :raises ProcessingHandlerException: Bei Fehlern
   
   .. py:method:: _validate_input_data(input_data, expected_type)
   
      Helper zur Typ-Validierung.
      
      :param input_data: Zu validierende Daten
      :param expected_type: Erwarteter Typ
      :raises ProcessingHandlerException: Bei falschem Typ

BaseOutputHandler
-----------------

.. py:class:: BaseOutputHandler

   Abstrakte Basisklasse für Output Handler.
   
   **Zusätzliche Klassenattribute:**
   
   .. py:attribute:: supports_multiple_objects
      :type: bool
      :value: False
      
      Kann mehrere Objekte gleichzeitig schreiben.
   
   .. py:attribute:: supports_nested_data
      :type: bool
      :value: False
      
      Unterstützt verschachtelte Datenstrukturen.
   
   .. py:attribute:: supports_validation
      :type: bool
      :value: True
      
      Validiert Daten vor dem Schreiben.
   
   .. py:attribute:: supports_preview
      :type: bool
      :value: False
      
      Kann Vorschau generieren.
   
   .. py:attribute:: supports_rollback
      :type: bool
      :value: False
      
      Unterstützt Rollback bei Fehlern.
   
   **Methoden:**
   
   .. py:method:: write(processed_data, context)
      :abstractmethod:
      
      Schreibt verarbeitete Daten.
      
      **Muss implementiert werden!**
      
      :param processed_data: Verarbeitete Daten
      :param context: Runtime-Kontext
      :return: Ergebnis-Dictionary mit Status
      :raises OutputHandlerException: Bei Fehlern

Exception Hierarchy
===================

.. mermaid::

   classDiagram
       class HandlerException {
           +message: str
           +handler_name: str
           +context: dict
           +original_error: Exception
       }
       
       HandlerException <|-- ConfigurationException
       HandlerException <|-- InputHandlerException
       HandlerException <|-- ProcessingHandlerException
       HandlerException <|-- OutputHandlerException

Exception Reference
-------------------

.. py:exception:: HandlerException

   Basis-Exception für alle Handler-Fehler.
   
   :param message: Fehlermeldung
   :param handler_name: Name des Handlers
   :param context: Zusätzlicher Kontext (dict)
   :param original_error: Original-Exception

.. py:exception:: ConfigurationException(HandlerException)

   Konfigurationsfehler.

.. py:exception:: InputHandlerException(HandlerException)

   Fehler bei Datensammlung.

.. py:exception:: ProcessingHandlerException(HandlerException)

   Fehler bei Datenverarbeitung.

.. py:exception:: OutputHandlerException(HandlerException)

   Fehler beim Schreiben.

Decorators
==========

.. py:decorator:: with_logging

   Fügt automatisches Logging hinzu.
   
   Loggt Start, Ende und Fehler der Methode.
   
   .. code-block:: python
   
      @with_logging
      def collect(self, context):
          return {"data": "..."}

.. py:decorator:: with_performance_monitoring

   Fügt Performance-Metriken hinzu.
   
   Misst Ausführungszeit und aktualisiert Handler-Metriken.
   
   .. code-block:: python
   
      @with_performance_monitoring
      def process(self, input_data, context):
          return processed_data

Database Model
==============

Handler Model
-------------

.. py:class:: Handler

   Django Model für Handler-Definitionen.
   
   Speicherort: ``apps/core/models/handler.py``
   
   **Felder:**
   
   +-------------------------+----------------+--------------------------------+
   | Feld                    | Typ            | Beschreibung                   |
   +=========================+================+================================+
   | ``id``                  | BigAutoField   | Primary Key                    |
   +-------------------------+----------------+--------------------------------+
   | ``code``                | CharField(100) | Unique Identifier              |
   +-------------------------+----------------+--------------------------------+
   | ``name``                | CharField(200) | Display Name                   |
   +-------------------------+----------------+--------------------------------+
   | ``description``         | TextField      | Beschreibung                   |
   +-------------------------+----------------+--------------------------------+
   | ``category``            | CharField(20)  | input/processing/output        |
   +-------------------------+----------------+--------------------------------+
   | ``module_path``         | CharField(255) | Python Module Path             |
   +-------------------------+----------------+--------------------------------+
   | ``class_name``          | CharField(100) | Handler Class Name             |
   +-------------------------+----------------+--------------------------------+
   | ``config_schema``       | JSONField      | JSON Schema für Config         |
   +-------------------------+----------------+--------------------------------+
   | ``input_schema``        | JSONField      | JSON Schema für Input          |
   +-------------------------+----------------+--------------------------------+
   | ``output_schema``       | JSONField      | JSON Schema für Output         |
   +-------------------------+----------------+--------------------------------+
   | ``version``             | CharField(20)  | Semantic Version               |
   +-------------------------+----------------+--------------------------------+
   | ``is_active``           | BooleanField   | Handler aktiv?                 |
   +-------------------------+----------------+--------------------------------+
   | ``is_deprecated``       | BooleanField   | Handler deprecated?            |
   +-------------------------+----------------+--------------------------------+
   | ``requires_llm``        | BooleanField   | Benötigt LLM?                  |
   +-------------------------+----------------+--------------------------------+
   | ``avg_execution_time_ms``| IntegerField  | Ø Ausführungszeit              |
   +-------------------------+----------------+--------------------------------+
   | ``success_rate``        | FloatField     | Erfolgsrate (0-100)            |
   +-------------------------+----------------+--------------------------------+
   | ``total_executions``    | IntegerField   | Gesamte Ausführungen           |
   +-------------------------+----------------+--------------------------------+
   
   **Methoden:**
   
   .. py:method:: get_implementation()
   
      Lädt Handler-Klasse dynamisch.
      
      :return: Handler-Klasse
      :raises ImportError: Wenn Klasse nicht geladen werden kann
   
   .. py:method:: validate_config(config)
   
      Validiert Konfiguration gegen ``config_schema``.
      
      :param config: Konfiguration
      :return: True wenn valide
      :raises ValidationError: Bei ungültiger Konfiguration
   
   .. py:method:: update_metrics(execution_time_ms, success)
   
      Aktualisiert Performance-Metriken.
      
      :param execution_time_ms: Ausführungszeit
      :param success: War erfolgreich?

Management Commands
===================

sync_handlers
-------------

Synchronisiert registrierte Handler mit der Datenbank.

.. code-block:: bash

   # Standard-Sync
   python manage.py sync_handlers
   
   # Vorschau ohne Änderungen
   python manage.py sync_handlers --dry-run
   
   # Existierende Handler überschreiben
   python manage.py sync_handlers --force

load_handler_categories
-----------------------

Lädt Handler-Kategorien in die Datenbank.

.. code-block:: bash

   python manage.py load_handler_categories

Pydantic Schemas
================

HandlerConfig
-------------

.. code-block:: python

   class HandlerConfig(BaseConfigModel):
       timeout: int = Field(300, ge=1, le=3600)
       retry_count: int = Field(3, ge=0, le=10)
       retry_delay: float = Field(1.0, ge=0)
       enable_logging: bool = True
       enable_metrics: bool = True

HandlerInput / HandlerOutput
----------------------------

.. code-block:: python

   class HandlerInput(BaseInput):
       data: Dict[str, Any] = Field(default_factory=dict)
       config: Optional[HandlerConfig] = None
   
   class HandlerOutput(BaseOutput):
       handler_name: Optional[str] = None
       handler_version: Optional[str] = None
       execution_time_ms: Optional[int] = None
       status: ProcessingStatus = ProcessingStatus.COMPLETED

Spezialisierte Schemas
----------------------

+---------------------------+----------------------------------+
| Schema                    | Verwendung                       |
+===========================+==================================+
| ``LLMProcessorConfig``    | LLM Processing Handler           |
+---------------------------+----------------------------------+
| ``TemplateRendererConfig``| Template Rendering               |
+---------------------------+----------------------------------+
| ``ValidationConfig``      | Validation Handler               |
+---------------------------+----------------------------------+
| ``FileProcessorConfig``   | File Processing                  |
+---------------------------+----------------------------------+
| ``BatchProcessorConfig``  | Batch Processing                 |
+---------------------------+----------------------------------+

Eigenen Handler implementieren
==============================

Vollständiges Beispiel
----------------------

.. code-block:: python

   """
   Custom Processing Handler
   
   Modul: apps/myapp/handlers/sentiment_handler.py
   """
   
   from typing import Any, Dict
   from pydantic import BaseModel, Field
   
   from apps.bfagent.services.handlers.base.processing import BaseProcessingHandler
   from apps.bfagent.services.handlers.registries import ProcessingHandlerRegistry
   from apps.bfagent.services.handlers.decorators import with_logging, with_performance_monitoring
   from apps.bfagent.services.handlers.exceptions import ProcessingHandlerException
   
   
   class SentimentConfig(BaseModel):
       """Konfiguration für SentimentHandler."""
       language: str = Field("de", description="Sprache für Analyse")
       threshold: float = Field(0.5, ge=0.0, le=1.0, description="Schwellwert")
   
   
   @ProcessingHandlerRegistry.register
   class SentimentHandler(BaseProcessingHandler):
       """
       Analysiert Sentiment von Texten.
       
       Konfiguration:
           language: Sprache (de, en)
           threshold: Mindest-Konfidenz
       
       Input:
           text: str - Zu analysierender Text
           
       Output:
           sentiment: str - positive/negative/neutral
           confidence: float - Konfidenz (0-1)
           scores: dict - Detaillierte Scores
       """
       
       handler_name = "sentiment_analyzer"
       handler_version = "1.0.0"
       description = "Analysiert Text-Sentiment mit ML"
       
       supports_streaming = False
       supports_async = True
       
       def validate_config(self):
           """Validiert Konfiguration mit Pydantic."""
           SentimentConfig(**self.config)
       
       @with_logging
       @with_performance_monitoring
       def process(self, input_data: str, context: Dict[str, Any]) -> Dict[str, Any]:
           """
           Führt Sentiment-Analyse durch.
           
           Args:
               input_data: Text zur Analyse
               context: Runtime-Kontext
               
           Returns:
               Analyse-Ergebnis mit sentiment, confidence, scores
           """
           # Typ validieren
           self._validate_input_data(input_data, str)
           
           if not input_data.strip():
               raise ProcessingHandlerException(
                   message="Empty text provided",
                   handler_name=self.handler_name,
                   context={"input_length": len(input_data)}
               )
           
           # Konfiguration laden
           config = SentimentConfig(**self.config)
           
           # Sentiment-Analyse (vereinfacht)
           result = self._analyze_sentiment(input_data, config.language)
           
           # Schwellwert prüfen
           if result["confidence"] < config.threshold:
               result["sentiment"] = "uncertain"
           
           return result
       
       def _analyze_sentiment(self, text: str, language: str) -> Dict[str, Any]:
           """Interne Sentiment-Analyse."""
           # Hier würde die echte ML-Logik stehen
           positive_words = {"gut", "super", "toll", "excellent", "great"}
           negative_words = {"schlecht", "übel", "bad", "terrible"}
           
           text_lower = text.lower()
           pos_count = sum(1 for w in positive_words if w in text_lower)
           neg_count = sum(1 for w in negative_words if w in text_lower)
           
           total = pos_count + neg_count
           if total == 0:
               return {
                   "sentiment": "neutral",
                   "confidence": 0.5,
                   "scores": {"positive": 0.33, "negative": 0.33, "neutral": 0.34}
               }
           
           pos_score = pos_count / total
           neg_score = neg_count / total
           
           if pos_score > neg_score:
               sentiment = "positive"
               confidence = pos_score
           else:
               sentiment = "negative"
               confidence = neg_score
           
           return {
               "sentiment": sentiment,
               "confidence": confidence,
               "scores": {
                   "positive": pos_score,
                   "negative": neg_score,
                   "neutral": 1 - pos_score - neg_score
               }
           }

Handler registrieren
--------------------

In ``apps/myapp/apps.py``:

.. code-block:: python

   from django.apps import AppConfig
   
   class MyAppConfig(AppConfig):
       name = "apps.myapp"
       
       def ready(self):
           # Handler importieren, damit Decorator ausgeführt wird
           from apps.myapp.handlers import sentiment_handler

Testing
=======

Unit Test Beispiel
------------------

.. code-block:: python

   import pytest
   from apps.bfagent.services.handlers.registries import ProcessingHandlerRegistry
   
   
   class TestSentimentHandler:
       
       def test_handler_registered(self):
           """Handler ist registriert."""
           handlers = ProcessingHandlerRegistry.list_handlers()
           assert "sentiment_analyzer" in handlers
       
       def test_positive_sentiment(self):
           """Erkennt positives Sentiment."""
           handler_class = ProcessingHandlerRegistry.get("sentiment_analyzer")
           handler = handler_class(config={"language": "de"})
           
           result = handler.process("Das ist super toll!", context={})
           
           assert result["sentiment"] == "positive"
           assert result["confidence"] > 0.5
       
       def test_empty_input_raises(self):
           """Leerer Input wirft Exception."""
           handler_class = ProcessingHandlerRegistry.get("sentiment_analyzer")
           handler = handler_class(config={})
           
           with pytest.raises(ProcessingHandlerException):
               handler.process("", context={})
       
       def test_invalid_config(self):
           """Ungültige Konfiguration wird abgelehnt."""
           handler_class = ProcessingHandlerRegistry.get("sentiment_analyzer")
           
           with pytest.raises(Exception):
               handler_class(config={"threshold": 2.0})  # > 1.0 nicht erlaubt

Siehe auch
==========

- :ref:`handler-framework-guide` - Benutzerhandbuch
- :doc:`handlers` - Handler API Übersicht
- :doc:`../guides/ai_integration` - LLM Integration
