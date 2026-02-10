Lookup-Tabellen
===============

.. note::
   Diese Seite wird zukünftig automatisch aus den ``lkp_*`` Tabellen generiert
   via ``python manage.py generate_db_docs --include lookups``.

Weltenhub Lookups
-----------------

+-----------------------------+-------------------------------+
| Tabelle                     | Beschreibung                  |
+=============================+===============================+
| ``lkp_genre``               | Story-Genres                  |
+-----------------------------+-------------------------------+
| ``lkp_mood``                | Atmosphäre / Stimmung         |
+-----------------------------+-------------------------------+
| ``lkp_conflict_level``      | Konflikt-Intensität           |
+-----------------------------+-------------------------------+
| ``lkp_location_type``       | Orts-Kategorien               |
+-----------------------------+-------------------------------+
| ``lkp_scene_type``          | Szenen-Kategorien             |
+-----------------------------+-------------------------------+
| ``lkp_character_role``      | Charakter-Archetypen          |
+-----------------------------+-------------------------------+
| ``lkp_character_trait``     | Bipolare Charakter-Traits     |
+-----------------------------+-------------------------------+
| ``lkp_transport_type``      | Transport-Arten               |
+-----------------------------+-------------------------------+
| ``lkp_enrichment_action``   | AI-Enrichment Konfiguration   |
+-----------------------------+-------------------------------+

Governance Lookups (platform Schema)
------------------------------------

+-----------------------------+-------------------------------+
| Domain Code                 | Beschreibung                  |
+=============================+===============================+
| ``bc_status``               | Business Case Status          |
+-----------------------------+-------------------------------+
| ``bc_category``             | Business Case Kategorie       |
+-----------------------------+-------------------------------+
| ``bc_priority``             | Priorität                     |
+-----------------------------+-------------------------------+
| ``uc_status``               | Use Case Status               |
+-----------------------------+-------------------------------+
| ``uc_complexity``           | Use Case Komplexität          |
+-----------------------------+-------------------------------+
| ``adr_status``              | ADR Status                    |
+-----------------------------+-------------------------------+
| ``review_decision``         | Review-Entscheidung           |
+-----------------------------+-------------------------------+
| ``conversation_status``     | Konversations-Status          |
+-----------------------------+-------------------------------+
| ``conversation_role``       | Rolle (user/assistant/system) |
+-----------------------------+-------------------------------+

Prinzip
-------

Alle Status-, Kategorie- und Prioritätsfelder referenzieren ``lkp_choice``
per Foreign Key. Neue Werte werden per DB-Insert hinzugefügt — **keine
Code-Änderung nötig**.
