================
Code Quality MCP
================

.. note::
   **Code-Analyse & Naming Conventions** | 8 Tools | Status: Production

Übersicht
=========

Der Code Quality MCP Server bietet automatische Code-Analyse basierend auf:

- **AST-Analyse**: Python Abstract Syntax Tree Parsing
- **Naming Conventions**: PEP 8, Django, BF Agent Patterns
- **Architecture Validation**: Layer Boundaries, Separation of Concerns
- **UI Consistency**: Bootstrap 5, HTMX, Template Standards
- **Auto-Fix**: Refactoring-Vorschläge mit Diff-Preview

Features:

- Datei- und Projekt-Analyse
- Inline Code-Snippets prüfen
- Hub-übergreifende UI-Konsistenz
- HTMX Pattern Library
- Regelbasierte Validierung

Installation
============

.. code-block:: bash

   cd packages/code_quality_mcp
   pip install -e .

Start
-----

.. code-block:: bash

   python -m code_quality_mcp.server
   # oder mit Projekt-Root
   python -m code_quality_mcp.server --project-root /path/to/bfagent

Tools
=====

Code-Analyse
------------

.. function:: analyze_python_file(file_path, response_format?)

   Analysiert eine Python-Datei auf Qualitätsprobleme.
   
   Prüft:
   
   - Naming Convention Violations (PEP 8, Django, BF Agent)
   - Architecture Pattern Violations
   - Separation of Concerns Issues
   - Missing Required Elements (für Handler, Models, etc.)
   
   :param file_path: Pfad zur Python-Datei
   :param response_format: markdown oder json
   :return: Issues mit Severity, Suggestions, Fix-Availability

.. function:: analyze_python_project(project_root, exclude_patterns?, max_files?, response_format?)

   Analysiert gesamtes Python/Django Projekt.
   
   :param project_root: Projekt-Wurzelverzeichnis
   :param exclude_patterns: Ausschluss-Patterns (z.B. ['migrations', 'tests'])
   :param max_files: Maximum Dateien (default: 100)
   :return: Summary, Per-File Breakdown, Fixable Issues Count

.. function:: analyze_code_snippet(code, file_name?, component_type?, response_format?)

   Analysiert Inline Python Code.
   
   :param code: Python-Code String
   :param file_name: Virtueller Dateiname für Kontext
   :param component_type: model, view, form, handler, service, etc.
   :return: Gefundene Issues

Naming Conventions
------------------

.. function:: check_naming_convention(name, expected_type)

   Prüft ob ein Name der Konvention entspricht.
   
   Unterstützte Typen:
   
   - **Python/PEP 8**: class, function, constant, variable, module
   - **Django**: model, form, view, serializer
   - **BF Agent**: handler, service, plugin, repository
   
   :param name: Zu prüfender Name
   :param expected_type: Erwarteter Typ
   :return: Valid/Invalid mit Erklärung

.. function:: list_quality_rules(category?, response_format?)

   Listet alle aktiven Code-Qualitätsregeln.
   
   :param category: naming, architecture, separation_of_concerns, database, performance, security, style, documentation
   :return: Regel-IDs, Beschreibungen, Kategorien

UI Consistency
--------------

.. function:: check_ui_consistency(hub_path, response_format?)

   Prüft Hub-Templates auf UI-Konsistenz mit BF Agent Standards.
   
   Prüft:
   
   - **Base Template**: Sollte zentrale base.html nutzen
   - **CSS Framework**: Bootstrap 5 (nicht Tailwind)
   - **Navigation**: Dynamische Navigation aus DB
   - **Theme**: Light Theme Standard
   - **JavaScript**: HTMX Standard (nicht Alpine.js)
   
   :param hub_path: Pfad zum Hub-App-Verzeichnis
   :return: Issues mit Migration-Suggestions

.. function:: analyze_all_hubs_ui(apps_path?, response_format?)

   Analysiert UI-Konsistenz über alle Hubs.
   
   Scannt alle ``*_hub`` Verzeichnisse im apps-Ordner.
   
   :param apps_path: Pfad zu apps (default: 'apps')
   :return: Konsistenz-Report über alle Hubs

HTMX Tools
----------

.. function:: list_htmx_patterns(category?)

   Listet verfügbare HTMX Patterns für Django.
   
   Kategorien:
   
   - **forms**: Click-to-Edit, Inline Validation
   - **lists**: Infinite Scroll, Sortable
   - **search**: Active Search, Autocomplete
   - **modals**: Modal Forms, Confirmations
   
   :param category: Optional Kategorie-Filter
   :return: Patterns mit Code-Snippets

.. function:: validate_htmx_attributes(html, response_format?)

   Validiert HTMX-Attribute in HTML.
   
   Prüft:
   
   - Invalid ``hx-swap`` Values
   - Invalid ``hx-trigger`` Events
   - Malformed ``hx-target`` Selectors
   - Empty URLs in ``hx-get``/``hx-post``
   - Unknown ``hx-*`` Attributes
   
   :param html: HTML-Content
   :return: Issues mit Fix-Suggestions

Refactoring
-----------

.. function:: suggest_refactoring(file_path, issue_ids?, response_format?)

   Generiert Refactoring-Vorschläge für eine Datei.
   
   :param file_path: Pfad zur Datei
   :param issue_ids: Spezifische Issue-IDs (None = alle fixable)
   :return: Diff-Style Preview der Änderungen

Konfiguration
=============

Naming Rules
------------

.. code-block:: python

   @dataclass
   class NamingRules:
       # Python/PEP 8
       class_pattern: str = r'^[A-Z][a-zA-Z0-9]+$'
       function_pattern: str = r'^[a-z_][a-z0-9_]*$'
       constant_pattern: str = r'^[A-Z][A-Z0-9_]*$'
       
       # Django Specific
       model_suffix: str = ''
       form_suffix: str = 'Form'
       view_suffix: str = 'View'
       
       # BF Agent Specific
       handler_suffix: str = 'Handler'
       service_suffix: str = 'Service'
       plugin_suffix: str = 'Plugin'

Architecture Rules
------------------

.. code-block:: python

   @dataclass
   class ArchitectureRules:
       # Layer Boundaries
       allowed_imports: Dict = {
           'models': ['django', 'pydantic'],
           'views': ['models', 'forms', 'services'],
           'handlers': ['models', 'services', 'schemas'],
           'services': ['models', 'repositories'],
       }
       
       # Required Patterns
       handler_must_have: List = [
           'INPUT_SCHEMA',
           'OUTPUT_SCHEMA',
           'execute',
       ]
       
       model_must_have: List = [
           '__str__',
           'class Meta',
       ]

Beispiele
=========

Datei analysieren
-----------------

.. code-block:: python

   # Einzelne Datei
   analyze_python_file(
       file_path="apps/writing_hub/handlers/chapter_handler.py"
   )
   
   # Ergebnis:
   # - WARNING: Missing OUTPUT_SCHEMA in handler
   # - INFO: Function 'get_data' should be 'get_chapter_data'

Projekt-Scan
------------

.. code-block:: python

   # Ganzes Projekt
   analyze_python_project(
       project_root="apps/writing_hub",
       exclude_patterns=["migrations", "__pycache__"],
       max_files=50
   )

Naming prüfen
-------------

.. code-block:: python

   # Handler-Name prüfen
   check_naming_convention(
       name="ChapterProcessor",
       expected_type="handler"
   )
   # → Invalid: Handler should end with 'Handler'
   
   # Korrekter Name
   check_naming_convention(
       name="ChapterProcessorHandler",
       expected_type="handler"
   )
   # → Valid

UI-Konsistenz
-------------

.. code-block:: python

   # Einzelnen Hub prüfen
   check_ui_consistency(hub_path="apps/cad_hub")
   
   # Alle Hubs prüfen
   analyze_all_hubs_ui()

HTMX validieren
---------------

.. code-block:: python

   html = '''
   <button hx-post="/save" hx-swap="invalid" hx-target="#result">
       Save
   </button>
   '''
   
   validate_htmx_attributes(html=html)
   # → ERROR: Invalid hx-swap value 'invalid'
   #          Valid: innerHTML, outerHTML, beforebegin, afterend, ...

Issue-Kategorien
================

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Kategorie
     - Severity
     - Beschreibung
   * - naming
     - warning
     - Naming Convention Violations
   * - architecture
     - error
     - Layer Boundary Violations
   * - separation_of_concerns
     - warning
     - Business Logic in Views, etc.
   * - database
     - error
     - N+1 Queries, Missing Indexes
   * - performance
     - info
     - Optimization Opportunities
   * - security
     - error
     - SQL Injection, XSS Risks
   * - style
     - style
     - Code Style Issues
   * - documentation
     - info
     - Missing Docstrings
