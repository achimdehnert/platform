.. _pydantic-schemas-reference:

==========================================
Pydantic Schemas - Technische Referenz
==========================================

.. contents:: Inhalt
   :local:
   :depth: 3

Übersicht
=========

BF Agent verwendet **Pydantic v2** für typsichere Datenvalidierung.
Die Schemas sind in ``apps/core/schemas/`` zentralisiert.

.. mermaid::

   classDiagram
       class BaseConfigModel {
           +model_config: ConfigDict
           +extra = "allow"
           +validate_assignment = True
       }
       
       class StrictConfigModel {
           +extra = "forbid"
           +frozen = False
       }
       
       class BaseInput {
           +request_id: str
           +user_id: int
           +metadata: Dict
       }
       
       class BaseOutput {
           +success: bool
           +message: str
           +errors: List
           +warnings: List
           +data: Dict
       }
       
       class PaginatedOutput {
           +page: int
           +page_size: int
           +total_items: int
           +has_next: bool
       }
       
       BaseConfigModel <|-- BaseInput
       BaseConfigModel <|-- BaseOutput
       BaseOutput <|-- PaginatedOutput

Modul-Struktur
==============

::

   apps/core/schemas/
   ├── __init__.py      # Public API
   ├── base.py          # Basis-Schemas
   ├── handlers.py      # Handler-spezifische Schemas
   └── validators.py    # Validierungs-Utilities

Basis-Schemas
=============

BaseConfigModel
---------------

.. py:class:: BaseConfigModel

   Flexible Basis für Konfigurationsmodelle.
   
   **Eigenschaften:**
   
   - Erlaubt Extra-Felder (``extra="allow"``)
   - Validiert bei Zuweisung
   - JSON Schema Generation
   
   .. code-block:: python
   
      from apps.core.schemas import BaseConfigModel
      from pydantic import Field
      
      class MyConfig(BaseConfigModel):
          timeout: int = Field(30, ge=1, le=300)
          retries: int = Field(3, ge=0)
          
      # Extra-Felder werden akzeptiert
      config = MyConfig(timeout=60, retries=5, custom_option="value")
      print(config.custom_option)  # "value"

StrictConfigModel
-----------------

.. py:class:: StrictConfigModel

   Strikte Basis für API-Verträge.
   
   **Eigenschaften:**
   
   - Verbietet Extra-Felder (``extra="forbid"``)
   - Wirft Fehler bei unbekannten Feldern
   - Für kritische Validierung
   
   .. code-block:: python
   
      from apps.core.schemas import StrictConfigModel
      
      class APIRequest(StrictConfigModel):
          action: str
          data: dict
      
      # Wirft ValidationError bei Extra-Feldern
      try:
          APIRequest(action="test", data={}, unknown="field")
      except ValidationError as e:
          print(e)  # Extra inputs are not permitted

Input/Output Schemas
====================

BaseInput
---------

.. py:class:: BaseInput

   Standard-Eingabe für Handler.
   
   **Felder:**
   
   +---------------+-----------------+--------------------------------+
   | Feld          | Typ             | Beschreibung                   |
   +===============+=================+================================+
   | ``request_id``| ``str | None``  | Unique Request ID für Tracking |
   +---------------+-----------------+--------------------------------+
   | ``user_id``   | ``int | None``  | User der die Anfrage stellt    |
   +---------------+-----------------+--------------------------------+
   | ``metadata``  | ``Dict[str,Any]``| Zusätzliche Metadaten         |
   +---------------+-----------------+--------------------------------+
   
   .. code-block:: python
   
      from apps.core.schemas import BaseInput
      
      class MyHandlerInput(BaseInput):
          content: str
          options: dict = {}
      
      input_data = MyHandlerInput(
          request_id="req_123",
          user_id=42,
          content="Hello",
          metadata={"source": "api"}
      )

BaseOutput
----------

.. py:class:: BaseOutput

   Standard-Ausgabe für Handler.
   
   **Felder:**
   
   +---------------+-----------------+--------------------------------+
   | Feld          | Typ             | Beschreibung                   |
   +===============+=================+================================+
   | ``success``   | ``bool``        | Operation erfolgreich?         |
   +---------------+-----------------+--------------------------------+
   | ``message``   | ``str | None``  | Menschenlesbare Nachricht      |
   +---------------+-----------------+--------------------------------+
   | ``errors``    | ``List[str]``   | Fehlermeldungen                |
   +---------------+-----------------+--------------------------------+
   | ``warnings``  | ``List[str]``   | Warnungen                      |
   +---------------+-----------------+--------------------------------+
   | ``data``      | ``Dict | None`` | Ergebnisdaten                  |
   +---------------+-----------------+--------------------------------+
   | ``metadata``  | ``Dict[str,Any]``| Response-Metadaten            |
   +---------------+-----------------+--------------------------------+
   
   .. code-block:: python
   
      from apps.core.schemas import BaseOutput
      
      class MyHandlerOutput(BaseOutput):
          result_count: int = 0
      
      # Erfolgreiche Antwort
      output = MyHandlerOutput(
          success=True,
          message="Verarbeitung abgeschlossen",
          data={"items": [1, 2, 3]},
          result_count=3
      )
      
      # Fehler-Antwort
      error_output = MyHandlerOutput(
          success=False,
          errors=["Validation failed", "Missing required field"]
      )

PaginatedOutput
---------------

.. py:class:: PaginatedOutput

   Basis für paginierte Antworten.
   
   **Zusätzliche Felder:**
   
   +---------------+---------+--------------------------------+
   | Feld          | Typ     | Beschreibung                   |
   +===============+=========+================================+
   | ``page``      | ``int`` | Aktuelle Seite (≥1)            |
   +---------------+---------+--------------------------------+
   | ``page_size`` | ``int`` | Items pro Seite (1-100)        |
   +---------------+---------+--------------------------------+
   | ``total_items``| ``int``| Gesamtanzahl Items             |
   +---------------+---------+--------------------------------+
   | ``total_pages``| ``int``| Gesamtanzahl Seiten            |
   +---------------+---------+--------------------------------+
   | ``has_next``  | ``bool``| Gibt es eine nächste Seite?    |
   +---------------+---------+--------------------------------+
   | ``has_previous``|``bool``| Gibt es eine vorherige Seite? |
   +---------------+---------+--------------------------------+
   
   .. code-block:: python
   
      from apps.core.schemas import PaginatedOutput
      
      class ProjectListOutput(PaginatedOutput):
          projects: list = []
      
      output = ProjectListOutput(
          success=True,
          page=2,
          page_size=20,
          total_items=45,
          total_pages=3,
          has_next=True,
          has_previous=True,
          projects=[{"id": 21, "name": "Project 21"}, ...]
      )

Enums
=====

ProcessingStatus
----------------

.. py:class:: ProcessingStatus(str, Enum)

   Standard-Verarbeitungsstatus.
   
   +---------------+-------------------+
   | Wert          | Beschreibung      |
   +===============+===================+
   | ``PENDING``   | Wartet auf Start  |
   +---------------+-------------------+
   | ``RUNNING``   | In Verarbeitung   |
   +---------------+-------------------+
   | ``COMPLETED`` | Erfolgreich       |
   +---------------+-------------------+
   | ``FAILED``    | Fehlgeschlagen    |
   +---------------+-------------------+
   | ``CANCELLED`` | Abgebrochen       |
   +---------------+-------------------+
   | ``RETRYING``  | Wiederholung      |
   +---------------+-------------------+

Priority
--------

.. py:class:: Priority(str, Enum)

   Standard-Prioritätsstufen.
   
   +---------------+
   | Wert          |
   +===============+
   | ``LOW``       |
   +---------------+
   | ``MEDIUM``    |
   +---------------+
   | ``HIGH``      |
   +---------------+
   | ``CRITICAL``  |
   +---------------+

Mixins
======

TimestampMixin
--------------

.. py:class:: TimestampMixin

   Fügt Zeitstempel-Felder hinzu.
   
   .. code-block:: python
   
      from apps.core.schemas.base import TimestampMixin
      from pydantic import BaseModel
      
      class MyModel(BaseModel, TimestampMixin):
          name: str
      
      obj = MyModel(name="Test")
      print(obj.created_at)  # datetime.now()
      
      obj.touch()  # Aktualisiert updated_at
      print(obj.updated_at)

IdentifiableMixin
-----------------

.. py:class:: IdentifiableMixin

   Fügt ID- und Slug-Felder hinzu.
   
   .. code-block:: python
   
      from apps.core.schemas.base import IdentifiableMixin
      
      class Entity(BaseModel, IdentifiableMixin):
          name: str
      
      entity = Entity(id=123, slug="my-entity", name="My Entity")

Handler Schemas
===============

HandlerConfig
-------------

.. py:class:: HandlerConfig

   Basis-Konfiguration für alle Handler.
   
   .. code-block:: python
   
      from apps.core.schemas.handlers import HandlerConfig
      
      class HandlerConfig(BaseConfigModel):
          timeout: int = Field(300, ge=1, le=3600)
          retry_count: int = Field(3, ge=0, le=10)
          retry_delay: float = Field(1.0, ge=0)
          enable_logging: bool = True
          enable_metrics: bool = True

LLMProcessorConfig
------------------

.. py:class:: LLMProcessorConfig

   Konfiguration für LLM-Handler.
   
   .. code-block:: python
   
      from apps.core.schemas.handlers import LLMProcessorConfig
      
      config = LLMProcessorConfig(
          model="gpt-4o",
          temperature=0.7,
          max_tokens=4096,
          system_prompt="Du bist ein hilfreicher Assistent."
      )

Validatoren
===========

ValidationResult
----------------

.. py:class:: ValidationResult

   Standardisiertes Validierungsergebnis.
   
   **Felder:**
   
   +------------------+--------------------+------------------------+
   | Feld             | Typ                | Beschreibung           |
   +==================+====================+========================+
   | ``is_valid``     | ``bool``           | Validierung bestanden? |
   +------------------+--------------------+------------------------+
   | ``errors``       | ``List[str]``      | Fehlermeldungen        |
   +------------------+--------------------+------------------------+
   | ``warnings``     | ``List[str]``      | Warnungen              |
   +------------------+--------------------+------------------------+
   | ``field_errors`` | ``Dict[str,List]`` | Feld-spezifische Fehler|
   +------------------+--------------------+------------------------+
   
   **Methoden:**
   
   .. code-block:: python
   
      from apps.core.schemas import ValidationResult
      
      result = ValidationResult(is_valid=True)
      
      # Fehler hinzufügen
      result.add_error("General error")
      result.add_error("Field specific error", field="email")
      
      # Warnung hinzufügen
      result.add_warning("Consider using HTTPS")
      
      # Fehleranzahl prüfen
      print(result.error_count)  # 2
      print(result.is_valid)     # False

Validierungsfunktionen
----------------------

Email-Validierung
^^^^^^^^^^^^^^^^^

.. py:function:: validate_email(email)

   Validiert E-Mail-Format (RFC 5321).
   
   .. code-block:: python
   
      from apps.core.schemas.validators import validate_email
      
      result = validate_email("user@example.com")
      assert result.is_valid
      
      result = validate_email("invalid-email")
      assert not result.is_valid

URL-Validierung
^^^^^^^^^^^^^^^

.. py:function:: validate_url(url, require_https=False)

   Validiert URL-Format.
   
   .. code-block:: python
   
      from apps.core.schemas.validators import validate_url
      
      result = validate_url("https://example.com")
      assert result.is_valid
      
      # HTTPS erforderlich
      result = validate_url("http://example.com", require_https=True)
      assert not result.is_valid

Datei-Validierung
^^^^^^^^^^^^^^^^^

.. py:function:: validate_file_extension(filename, allowed_types=None, allowed_extensions=None)

   Validiert Dateiendung.
   
   **Erlaubte Typen:**
   
   - ``image``: jpg, jpeg, png, gif, bmp, webp, svg
   - ``document``: pdf, docx, doc, txt, md, rtf
   - ``presentation``: pptx, ppt, odp
   - ``spreadsheet``: xlsx, xls, csv, ods
   - ``archive``: zip, tar, gz, rar, 7z
   - ``video``: mp4, avi, mov, wmv, flv
   - ``audio``: mp3, wav, ogg, flac, aac
   
   .. code-block:: python
   
      from apps.core.schemas.validators import validate_file_extension
      
      # Nach Typ validieren
      result = validate_file_extension("report.pdf", allowed_types=["document"])
      assert result.is_valid
      
      # Nach Extension validieren
      result = validate_file_extension("data.csv", allowed_extensions=[".csv", ".xlsx"])
      assert result.is_valid

.. py:function:: validate_file_size(file_size, max_size_mb=None, min_size_kb=None)

   Validiert Dateigröße.
   
   .. code-block:: python
   
      from apps.core.schemas.validators import validate_file_size
      
      # Max 10 MB
      result = validate_file_size(5_000_000, max_size_mb=10)
      assert result.is_valid
      
      # Min 1 KB, Max 50 MB
      result = validate_file_size(100, max_size_mb=50, min_size_kb=1)
      assert not result.is_valid  # Zu klein

Slug-Validierung
^^^^^^^^^^^^^^^^

.. py:function:: validate_slug(slug)

   Validiert URL-Slug-Format.
   
   .. code-block:: python
   
      from apps.core.schemas.validators import validate_slug
      
      result = validate_slug("my-project-name")
      assert result.is_valid
      
      result = validate_slug("Invalid Slug!")
      assert not result.is_valid

Validatoren kombinieren
^^^^^^^^^^^^^^^^^^^^^^^

.. py:function:: validate_all(*validation_results)

   Kombiniert mehrere Validierungsergebnisse.
   
   .. code-block:: python
   
      from apps.core.schemas.validators import (
          validate_email,
          validate_url,
          validate_all
      )
      
      combined = validate_all(
          validate_email("user@example.com"),
          validate_url("https://example.com"),
          validate_slug("my-project")
      )
      
      if combined.is_valid:
          print("Alle Validierungen bestanden!")
      else:
          print(f"Fehler: {combined.errors}")

Best Practices
==============

1. Eigene Schemas von Basis-Klassen ableiten
--------------------------------------------

.. code-block:: python

   from apps.core.schemas import BaseInput, BaseOutput
   
   class CreateProjectInput(BaseInput):
       title: str
       description: str = ""
       genre_id: int
   
   class CreateProjectOutput(BaseOutput):
       project_id: int | None = None

2. Field mit Constraints verwenden
----------------------------------

.. code-block:: python

   from pydantic import Field
   
   class Config(BaseConfigModel):
       timeout: int = Field(30, ge=1, le=3600, description="Timeout in Sekunden")
       temperature: float = Field(0.7, ge=0.0, le=2.0)
       max_items: int = Field(100, gt=0)

3. Validators für komplexe Logik
--------------------------------

.. code-block:: python

   from pydantic import field_validator
   
   class ProjectConfig(BaseConfigModel):
       start_date: str
       end_date: str
       
       @field_validator('end_date')
       @classmethod
       def end_after_start(cls, v, info):
           if 'start_date' in info.data and v < info.data['start_date']:
               raise ValueError('end_date must be after start_date')
           return v

4. JSON Schema für API-Dokumentation
------------------------------------

.. code-block:: python

   from apps.core.schemas import BaseInput
   
   class MyInput(BaseInput):
       name: str
       
       class Config:
           json_schema_extra = {
               "example": {
                   "request_id": "req_123",
                   "name": "Example Name"
               }
           }
   
   # JSON Schema generieren
   schema = MyInput.model_json_schema()

Siehe auch
==========

- :ref:`handler-framework-guide` - Handler Framework mit Schemas
- :ref:`llm-technical-reference` - LLM Response Schemas
- `Pydantic v2 Dokumentation <https://docs.pydantic.dev/latest/>`_
