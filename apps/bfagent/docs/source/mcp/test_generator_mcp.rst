==================
Test Generator MCP
==================

.. note::
   **Test-Generierung & Ausführung** | 5 Tools | Status: Production

Übersicht
=========

Der Test Generator MCP Server bietet automatische Test-Generierung und
-Ausführung speziell für Django und BF Agent Projekte.

Unique Features:

- **AST-basierte Generierung**: Analysiert Code-Struktur
- **Handler-spezifische Templates**: BF Agent Pattern Support
- **Coverage-Gap Analyse**: Gezielte Test-Vorschläge
- **Test-Execution**: Strukturiertes Reporting
- **Quality Trends**: Tracking über Zeit

Installation
============

.. code-block:: bash

   cd packages/test_generator_mcp
   pip install -e .

Konfiguration
-------------

.. code-block:: python

   @dataclass
   class TestGeneratorConfig:
       test_framework: str = "pytest"
       async_support: bool = True
       django_settings_module: str = "config.settings"
       use_django_test_client: bool = True
       coverage_threshold: float = 80.0
       branch_coverage: bool = True
       handler_test_template: str = "handler"
       mock_ai_calls: bool = True
       test_output_dir: str = "tests"

Start
-----

.. code-block:: bash

   python -m test_generator_mcp.server
   # oder mit Projekt-Root
   python -m test_generator_mcp.server --project-root /path/to/bfagent

Tools
=====

Test-Generierung
----------------

.. function:: generate_tests(file_path, test_types?, output_dir?, response_format?)

   Generiert Tests für eine Python-Datei.
   
   Analysiert Code-Struktur und generiert passende Tests für:
   
   - **Handlers**: BF Agent Pattern mit INPUT_SCHEMA, execute
   - **Django Models**: create, str, validation
   - **Django Views**: GET, POST, authentication
   - **Django Forms**: valid, invalid data
   - **Generic Classes/Functions**
   
   :param file_path: Pfad zur Python-Datei
   :param test_types: Liste von Typen: unit, integration, handler, api, model, view, form, e2e
   :param output_dir: Ausgabeverzeichnis für Tests
   :return: Generierter Test-Code

   Beispiel:

   .. code-block:: python

      generate_tests(
          file_path="apps/writing_hub/handlers/chapter_handler.py",
          test_types=["handler", "unit"]
      )

Test-Ausführung
---------------

.. function:: run_tests(test_path?, pattern?, coverage?, verbose?, save_report?, response_format?)

   Führt Tests aus und liefert Ergebnisse.
   
   :param test_path: Spezifische Test-Datei oder Verzeichnis
   :param pattern: Test-Name Pattern (pytest -k)
   :param coverage: Coverage-Daten sammeln (default: true)
   :param verbose: Ausführliche Ausgabe
   :param save_report: Report speichern
   :return: Pass/Fail Status, Error Messages, Coverage Report

   Beispiel:

   .. code-block:: python

      # Alle Tests
      run_tests(coverage=True)
      
      # Spezifische Tests
      run_tests(
          test_path="tests/test_handlers",
          pattern="test_chapter"
      )

Failure-Analyse
---------------

.. function:: analyze_test_failures(test_path?, pattern?, coverage?, save_report?, response_format?)

   Führt Tests aus und analysiert Failures detailliert.
   
   - Gruppiert Failures nach Typ
   - Identifiziert Patterns
   - Schlägt Fixes für häufige Issues vor
   
   :return: Grouped Failures, Patterns, Suggested Fixes

Coverage-Analyse
----------------

.. function:: suggest_tests_for_coverage(file_path, max_suggestions?, response_format?)

   Analysiert Datei und schlägt Tests für Coverage-Lücken vor.
   
   Identifiziert:
   
   - Ungetestete Code-Pfade
   - Fehlende Edge Cases
   - Ungetestete Branches
   
   :param file_path: Zu analysierende Datei
   :param max_suggestions: Max. Vorschläge (1-50, default: 10)
   :return: Test-Vorschläge mit Code-Snippets

Quality Trends
--------------

.. function:: get_quality_trend(days?, response_format?)

   Zeigt Qualitäts-Trend über Zeit.
   
   :param days: Analyse-Zeitraum (1-365, default: 30)
   :return: Test Count, Pass Rate, Coverage Trend

Test-Typen
==========

.. list-table::
   :header-rows: 1
   :widths: 15 85

   * - Typ
     - Beschreibung
   * - unit
     - Isolierte Unit Tests für Funktionen/Methoden
   * - integration
     - Integration Tests mit DB/Services
   * - handler
     - BF Agent Handler Tests (INPUT → execute → OUTPUT)
   * - api
     - REST API Tests (DRF, Django Views)
   * - model
     - Django Model Tests (create, str, validation)
   * - view
     - Django View Tests (GET, POST, auth)
   * - form
     - Django Form Tests (valid, invalid, clean)
   * - e2e
     - End-to-End Tests (Playwright/Selenium)

Beispiele
=========

Handler-Tests generieren
------------------------

.. code-block:: python

   # Tests für Handler generieren
   generate_tests(
       file_path="apps/writing_hub/handlers/chapter_handler.py",
       test_types=["handler"]
   )

Generierter Test:

.. code-block:: python

   import pytest
   from apps.writing_hub.handlers.chapter_handler import ChapterHandler
   
   
   class TestChapterHandler:
       @pytest.fixture
       def handler(self):
           return ChapterHandler()
       
       def test_input_schema_exists(self, handler):
           assert hasattr(handler, 'INPUT_SCHEMA')
       
       def test_output_schema_exists(self, handler):
           assert hasattr(handler, 'OUTPUT_SCHEMA')
       
       def test_execute_with_valid_input(self, handler):
           input_data = {
               "project_id": 1,
               "chapter_number": 1,
               "content": "Test content"
           }
           result = handler.execute(input_data)
           assert result is not None
       
       def test_execute_with_missing_required_field(self, handler):
           with pytest.raises(ValidationError):
               handler.execute({})

Coverage verbessern
-------------------

.. code-block:: python

   # Coverage-Lücken identifizieren
   suggest_tests_for_coverage(
       file_path="apps/writing_hub/handlers/chapter_handler.py",
       max_suggestions=5
   )
   
   # Ergebnis:
   # 1. Test for error handling in _validate_input()
   # 2. Test for edge case: empty content
   # 3. Test for branch: chapter_number <= 0

Test-Trend analysieren
----------------------

.. code-block:: python

   # 30-Tage Trend
   get_quality_trend(days=30)
   
   # Ergebnis:
   # {
   #   "period_days": 30,
   #   "test_count": {"start": 150, "end": 180, "change": "+30"},
   #   "pass_rate": {"start": 95.0, "end": 98.5, "change": "+3.5%"},
   #   "coverage": {"start": 75.0, "end": 82.0, "change": "+7.0%"}
   # }

Best Practices
==============

1. **Handler-Tests First**: Immer INPUT_SCHEMA/OUTPUT_SCHEMA testen
2. **Mock AI Calls**: ``mock_ai_calls=True`` für deterministische Tests
3. **Coverage Threshold**: 80% als Minimum anstreben
4. **Integration Tests**: Für kritische Workflows
5. **Fixture Reuse**: Gemeinsame Test-Fixtures definieren

Integration
===========

pytest.ini Konfiguration
------------------------

.. code-block:: ini

   [pytest]
   DJANGO_SETTINGS_MODULE = config.settings
   python_files = test_*.py
   python_classes = Test*
   python_functions = test_*
   addopts = --cov=apps --cov-report=html --cov-fail-under=80

CI/CD Integration
-----------------

.. code-block:: yaml

   # .github/workflows/tests.yml
   - name: Run Tests
     run: |
       pytest --cov=apps --cov-report=xml
       
   - name: Generate Missing Tests
     run: |
       python -m test_generator_mcp.server --generate-missing
