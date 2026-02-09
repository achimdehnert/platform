Systemübersicht
===============

DDL Governance ist das zentrale System für strukturierte Feature-Entwicklung
nach dem Domain Development Lifecycle (ADR-017).

Kernkonzepte
------------

Business Cases
^^^^^^^^^^^^^^

Ein Business Case beschreibt:

* **Problem Statement** - Was ist das Problem?
* **Target Audience** - Wer ist betroffen?
* **Expected Benefits** - Was sind die erwarteten Vorteile?
* **Success Criteria** - Woran messen wir Erfolg?

.. code-block:: python

   # Beispiel: Business Case erstellen
   bc = BusinessCase.objects.create(
       code="BC-042",
       title="KI-gestützte Dokumentation",
       problem_statement="Manuelle Dokumentation ist zeitaufwändig",
       category=LookupChoice.objects.get(code="feature"),
       status=LookupChoice.objects.get(code="draft"),
   )

Use Cases
^^^^^^^^^

Use Cases beschreiben konkrete Benutzerinteraktionen:

* **Actor** - Wer führt die Aktion aus?
* **Preconditions** - Was muss vorher erfüllt sein?
* **Main Flow** - Hauptablauf der Interaktion
* **Postconditions** - Was ist das Ergebnis?

Status-Workflow
---------------

Business Case Status (7 Zustände):

.. code-block:: text

   draft → submitted → in_review → approved
                    ↓              ↓
              rejected       on_hold
                                ↓
                           archived

   Hinweis: Rücksprung von in_review → draft ist möglich.
   Status on_hold kann jederzeit gesetzt werden.
   Archivierung ist der Endzustand.

Use Case Status (7 Zustände):

.. code-block:: text

   draft → defined → approved → implemented → tested → deployed
                                                        ↓
                                                   deprecated

Alle Status-Werte kommen aus der ``lkp_choice`` Tabelle (ADR-015 Pattern).
Keine Hardcoded Enums - alles aus der Datenbank!

Lookup-System
-------------

Das DDL Governance System verwendet das Lookup-Pattern aus ADR-015:

+------------------------+------------------------------------------+
| Domain                 | Beschreibung                             |
+========================+==========================================+
| bc_status              | Business Case Status (7 Werte)           |
+------------------------+------------------------------------------+
| bc_category            | Business Case Kategorie (7 Werte)        |
+------------------------+------------------------------------------+
| bc_priority            | Priorität (critical/high/medium/low)     |
+------------------------+------------------------------------------+
| uc_status              | Use Case Status (7 Werte)                |
+------------------------+------------------------------------------+
| uc_priority            | Use Case Priorität (4 Werte)             |
+------------------------+------------------------------------------+
| uc_complexity          | Use Case Komplexität (5 Stufen)          |
+------------------------+------------------------------------------+
| adr_status             | ADR Status (5 Werte)                     |
+------------------------+------------------------------------------+
| adr_uc_relationship    | ADR-UC Beziehungstyp (3 Werte)           |
+------------------------+------------------------------------------+
| conversation_status    | Konversations-Status (4 Werte)           |
+------------------------+------------------------------------------+
| conversation_role      | Rolle (user/assistant/system)            |
+------------------------+------------------------------------------+
| review_entity_type     | Review Entity Typ (3 Werte)              |
+------------------------+------------------------------------------+
| review_decision        | Review Entscheidung (3 Werte)            |
+------------------------+------------------------------------------+

12 Domains, 54+ Choices - vollständig datengetrieben.

MCP Integration
---------------

Das Governance-System wird über den **Orchestrator MCP** (``mcp-hub``) gesteuert.
Folgende MCP-Tools interagieren mit Governance-Daten:

+------------------------+------------------------------------------------+
| MCP Tool               | Funktion                                       |
+========================+================================================+
| ``check_gate``         | Prüft ob eine Aktion am aktuellen Gate-Level   |
|                        | erlaubt ist (Gate 0-4)                         |
+------------------------+------------------------------------------------+
| ``request_approval``   | Fordert menschliche Freigabe für gated Actions |
|                        | an (Gate 2+ erfordert Approval)                |
+------------------------+------------------------------------------------+
| ``log_action``         | Protokolliert AI-Aktionen im Audit-Log         |
+------------------------+------------------------------------------------+
| ``analyze_task``       | Analysiert eine Aufgabe und empfiehlt          |
|                        | Modell/Team/Gate-Level                         |
+------------------------+------------------------------------------------+
| ``get_audit_log``      | Liest den Audit-Trail für Nachvollziehbarkeit  |
+------------------------+------------------------------------------------+

Gate-Level:

* **Gate 0-1**: Auto-approved (Lesen, einfache Operationen)
* **Gate 2**: Menschliche Bestätigung empfohlen (Schreiboperationen)
* **Gate 3-4**: Menschliche Bestätigung erforderlich (Destruktive Aktionen)

Governance Rules
----------------

Zusätzlich zu Business Cases und Use Cases verwaltet das System
Code-Governance-Regeln (ADR-015 Phase 3):

* **Access Rules** - Welcher Service darf auf welche Komponente zugreifen?
* **Import Rules** - Verbotene Imports mit Alternativen
* **Naming Rules** - Namenskonventionen für Code-Artefakte
* **Pattern Rules** - Erzwungene Design Patterns
* **Enforcement Log** - Audit-Trail aller Regelprüfungen
