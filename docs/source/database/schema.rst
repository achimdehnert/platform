Datenbankschema
===============

.. note::
   Diese Seite wird zukünftig automatisch aus ``pg_catalog`` generiert
   via ``python manage.py generate_db_docs --include schema``.

Übersicht
---------

Alle Apps teilen sich eine PostgreSQL 16 Instanz (``bfagent_db``).

+------------------+--------------------+----------------------------------+
| Schema           | App                | Tabellen-Prefix                  |
+==================+====================+==================================+
| public           | weltenhub          | ``wh_*``                         |
+------------------+--------------------+----------------------------------+
| public           | weltenhub lookups  | ``lkp_*``                        |
+------------------+--------------------+----------------------------------+
| platform         | governance (DDL)   | ``lkp_*``, ``dom_*``            |
+------------------+--------------------+----------------------------------+
| public           | bfagent            | diverse (legacy SQLite-Schema)   |
+------------------+--------------------+----------------------------------+

Weltenhub Entity-Tabellen
-------------------------

.. code-block:: text

   wh_world ──────┐
       │          │
       ├── wh_world_rule
       │
       ├── wh_location (hierarchisch, parent FK)
       │
       ├── wh_character
       │       └── wh_character_arc
       │
       ├── wh_story
       │       └── wh_chapter
       │
       └── wh_scene
               ├── wh_scene_template
               └── wh_scene_beat

Governance-Tabellen (platform Schema)
-------------------------------------

Siehe :doc:`../governance/overview` für Details.

.. code-block:: text

   platform.lkp_domain ──► platform.lkp_choice
                                   │
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
   platform.dom_business_case  dom_use_case         dom_adr
              │                    │                    │
              └──────────┐         │         ┌─────────┘
                         ▼         ▼         ▼
                      dom_review   dom_status_history
