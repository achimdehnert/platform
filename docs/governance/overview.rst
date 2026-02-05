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

.. code-block:: text

   draft → submitted → in_review → approved → implemented
                    ↓
              rejected

Alle Status-Werte kommen aus der ``lkp_choice`` Tabelle (ADR-015 Pattern).

Lookup-System
-------------

Das DDL Governance System verwendet das Lookup-Pattern aus ADR-015:

+--------------------+----------------------------------+
| Domain             | Beschreibung                     |
+====================+==================================+
| bc_status          | Business Case Status             |
+--------------------+----------------------------------+
| bc_category        | Business Case Kategorie          |
+--------------------+----------------------------------+
| bc_priority        | Priorität (high/medium/low)      |
+--------------------+----------------------------------+
| uc_status          | Use Case Status                  |
+--------------------+----------------------------------+
| uc_complexity      | Use Case Komplexität             |
+--------------------+----------------------------------+

Keine Hardcoded Enums - alles aus der Datenbank!
