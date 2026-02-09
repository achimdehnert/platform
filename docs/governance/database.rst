Datenbankschema
===============

Alle Tabellen befinden sich im ``platform`` Schema der PostgreSQL-Datenbank.

.. note::

   **Managed=False Pattern**: Django-Models sind mit ``managed = False`` konfiguriert.
   Das bedeutet: Django liest/schreibt die Tabellen, erstellt sie aber **nicht** via
   Migrations. Die Tabellen werden manuell per SQL-Scripts erstellt
   (``scripts/create_governance_tables.sql``). Grund: Das ``platform`` Schema wird
   von mehreren Services geteilt und darf nicht von einem einzelnen Django-Service
   migriert werden.

Entity-Relationship
-------------------

.. code-block:: text

   ┌──────────────┐       ┌──────────────┐
   │ lkp_domain   │──────▶│ lkp_choice   │
   │              │  1:N  │              │
   └──────────────┘       └──────┬───────┘
                                │
         ┌──────────────────────┼──────────────────────┐
         │                      │                      │
         ▼                      ▼                      ▼
   ┌──────────────┐       ┌──────────────┐       ┌──────────────┐
   │ dom_business │       │ dom_use_case │       │ gov_*_rule   │
   │    _case     │──────▶│              │       │  (4 tables)  │
   └──────────────┘  1:N  └──────────────┘       └──────────────┘

   GEPLANT (noch nicht implementiert):
   ┌──────────────┐
   │   dom_adr    │  M:N Beziehung zu dom_use_case
   └──────────────┘

Lookup-Tabellen
---------------

lkp_domain
^^^^^^^^^^

Definiert Kategorien von Lookup-Werten.

.. code-block:: sql

   CREATE TABLE platform.lkp_domain (
       id SERIAL PRIMARY KEY,
       code VARCHAR(50) UNIQUE NOT NULL,
       name VARCHAR(100) NOT NULL,
       name_de VARCHAR(100),
       description TEXT,
       is_active BOOLEAN DEFAULT TRUE,
       created_at TIMESTAMP DEFAULT NOW(),
       updated_at TIMESTAMP DEFAULT NOW()
   );

lkp_choice
^^^^^^^^^^

Enthält die eigentlichen Lookup-Werte.

.. code-block:: sql

   CREATE TABLE platform.lkp_choice (
       id SERIAL PRIMARY KEY,
       domain_id INTEGER REFERENCES platform.lkp_domain(id),
       code VARCHAR(50) NOT NULL,
       name VARCHAR(100) NOT NULL,
       name_de VARCHAR(100),
       description TEXT,
       sort_order INTEGER DEFAULT 0,
       color VARCHAR(7),          -- Hex color (#FF0000)
       icon VARCHAR(50),          -- Bootstrap Icon class
       metadata JSONB DEFAULT '{}',
       is_active BOOLEAN DEFAULT TRUE,
       created_at TIMESTAMP DEFAULT NOW(),
       updated_at TIMESTAMP DEFAULT NOW(),
       UNIQUE(domain_id, code)
   );

Domain-Tabellen
---------------

dom_business_case
^^^^^^^^^^^^^^^^^

.. code-block:: sql

   CREATE TABLE platform.dom_business_case (
       id SERIAL PRIMARY KEY,
       code VARCHAR(20) UNIQUE NOT NULL,
       title VARCHAR(200) NOT NULL,
       category_id INTEGER REFERENCES platform.lkp_choice(id),
       status_id INTEGER REFERENCES platform.lkp_choice(id),
       priority_id INTEGER REFERENCES platform.lkp_choice(id),
       problem_statement TEXT NOT NULL,
       target_audience TEXT,
       expected_benefits JSONB DEFAULT '[]',
       scope TEXT,
       out_of_scope JSONB DEFAULT '[]',
       success_criteria JSONB DEFAULT '[]',
       assumptions JSONB DEFAULT '[]',
       risks JSONB DEFAULT '[]',
       requires_adr BOOLEAN DEFAULT FALSE,
       adr_reason TEXT,
       owner_id INTEGER,
       created_at TIMESTAMP DEFAULT NOW(),
       updated_at TIMESTAMP DEFAULT NOW()
   );

dom_use_case
^^^^^^^^^^^^

.. code-block:: sql

   CREATE TABLE platform.dom_use_case (
       id SERIAL PRIMARY KEY,
       code VARCHAR(20) UNIQUE NOT NULL,
       title VARCHAR(200) NOT NULL,
       business_case_id INTEGER REFERENCES platform.dom_business_case(id),
       status_id INTEGER REFERENCES platform.lkp_choice(id),
       priority_id INTEGER REFERENCES platform.lkp_choice(id),
       actor VARCHAR(100) NOT NULL,
       preconditions JSONB DEFAULT '[]',
       postconditions JSONB DEFAULT '[]',
       main_flow JSONB DEFAULT '[]',
       alternative_flows JSONB DEFAULT '[]',
       exception_flows JSONB DEFAULT '[]',
       complexity_id INTEGER REFERENCES platform.lkp_choice(id),
       estimated_effort VARCHAR(50),
       created_at TIMESTAMP DEFAULT NOW(),
       updated_at TIMESTAMP DEFAULT NOW()
   );

dom_adr (GEPLANT)
^^^^^^^^^^^^^^^^^

.. note::

   Die ``dom_adr`` Tabelle ist geplant aber noch nicht implementiert.
   ADRs werden aktuell als Markdown-Dateien in ``docs/adr/`` verwaltet.
   Die Lookup-Domains ``adr_status`` und ``adr_uc_relationship`` sind
   bereits als Seed-Daten angelegt für die spätere Migration.

Governance Rules Tabellen
-------------------------

Zusätzlich zu den DDL-Tabellen gibt es 5 Code-Governance-Tabellen
(ADR-015 Phase 3, ``scripts/create_governance_tables.sql``):

+----------------------------+------------------------------------------+
| Tabelle                    | Beschreibung                             |
+============================+==========================================+
| ``gov_access_rule``        | Zugriffskontrolle: welcher Service darf  |
|                            | auf welche Komponente zugreifen          |
+----------------------------+------------------------------------------+
| ``gov_import_rule``        | Verbotene Imports mit Alternativen       |
+----------------------------+------------------------------------------+
| ``gov_naming_rule``        | Namenskonventionen für Code-Artefakte    |
+----------------------------+------------------------------------------+
| ``gov_pattern_rule``       | Erzwungene Design Patterns               |
+----------------------------+------------------------------------------+
| ``gov_enforcement_log``    | Audit-Trail aller Regelprüfungen         |
+----------------------------+------------------------------------------+

Lookup-Domains
--------------

+----------------------+------------------------------------+--------+
| Domain Code          | Beschreibung                       | Werte  |
+======================+====================================+========+
| bc_status            | Business Case Status               | 7      |
+----------------------+------------------------------------+--------+
| bc_category          | Business Case Kategorie            | 7      |
+----------------------+------------------------------------+--------+
| bc_priority          | Priorität                          | 4      |
+----------------------+------------------------------------+--------+
| uc_status            | Use Case Status                    | 7      |
+----------------------+------------------------------------+--------+
| uc_priority          | Use Case Priorität                 | 4      |
+----------------------+------------------------------------+--------+
| uc_complexity        | Use Case Komplexität               | 5      |
+----------------------+------------------------------------+--------+
| adr_status           | ADR Status                         | 5      |
+----------------------+------------------------------------+--------+
| adr_uc_relationship  | ADR-UC Beziehungstyp               | 3      |
+----------------------+------------------------------------+--------+
| conversation_status  | Konversations-Status               | 4      |
+----------------------+------------------------------------+--------+
| conversation_role    | Rolle (user/assistant/system)      | 3      |
+----------------------+------------------------------------+--------+
| review_entity_type   | Review Entity Typ                  | 3      |
+----------------------+------------------------------------+--------+
| review_decision      | Review Entscheidung                | 3      |
+----------------------+------------------------------------+--------+

Seed Data Beispiele
-------------------

Alle Lookup-Daten werden via idempotentes SQL geladen
(``governance-deploy/governance/fixtures/seed_lookups.sql``).

Beispiel ``bc_status`` Werte:

.. code-block:: text

   draft       (#6c757d)  bi-pencil
   submitted   (#17a2b8)  bi-send
   in_review   (#ffc107)  bi-eye
   approved    (#28a745)  bi-check-circle
   rejected    (#dc3545)  bi-x-circle
   on_hold     (#6c757d)  bi-pause-circle
   archived    (#6c757d)  bi-archive

Beispiel ``uc_complexity`` Werte:

.. code-block:: text

   trivial       (#28a745)  bi-1-circle
   simple        (#20c997)  bi-2-circle
   moderate      (#ffc107)  bi-3-circle
   complex       (#fd7e14)  bi-4-circle
   very_complex  (#dc3545)  bi-5-circle

Seed-Daten laden:

.. code-block:: bash

   docker exec -i bfagent_db psql -U bfagent platform \
       < governance-deploy/governance/fixtures/seed_lookups.sql

Schema-Migration
----------------

Da ``managed = False`` verwendet wird, gibt es keine Django-Migrations.
Schema-Änderungen werden wie folgt durchgeführt:

1. SQL-Script in ``scripts/`` erstellen (z.B. ``alter_governance_v2.sql``)
2. Script auf dem Server ausführen via ``docker exec``
3. Django-Models in ``governance/models.py`` entsprechend anpassen
4. Kein ``makemigrations`` nötig - Models lesen nur
