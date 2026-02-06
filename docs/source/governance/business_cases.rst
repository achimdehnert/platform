Business Cases
==============

.. note::
   Wird zukünftig aus ``platform.dom_business_case`` generiert.

Business Cases beschreiben fachliche Anforderungen und Problemstellungen.

Felder
------

- **code** — Eindeutiger Identifier (z.B. BC-001)
- **title** — Kurztitel
- **category** — FK → ``lkp_choice`` (bc_category)
- **status** — FK → ``lkp_choice`` (bc_status)
- **priority** — FK → ``lkp_choice`` (bc_priority)
- **problem_statement** — Problembeschreibung
- **expected_benefits** — JSON Array
- **success_criteria** — JSON Array
- **requires_adr** — Boolean, ob ein ADR nötig ist
