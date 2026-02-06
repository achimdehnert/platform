Use Cases
=========

.. note::
   Wird zukünftig aus ``platform.dom_use_case`` generiert.

Use Cases beschreiben detaillierte Benutzerinteraktionen.

Felder
------

- **code** — Eindeutiger Identifier (z.B. UC-001)
- **title** — Kurztitel
- **business_case** — FK → ``dom_business_case``
- **status** — FK → ``lkp_choice`` (uc_status)
- **priority** — FK → ``lkp_choice`` (uc_priority)
- **actor** — Handelnde Person/System
- **preconditions** — JSON Array
- **postconditions** — JSON Array
- **main_flow** — JSON Array (Hauptablauf)
- **alternative_flows** — JSON Array
- **exception_flows** — JSON Array
- **complexity** — FK → ``lkp_choice`` (uc_complexity)
