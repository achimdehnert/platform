Datenbankschema
===============

Alle Tabellen befinden sich im ``platform`` Schema der PostgreSQL-Datenbank.

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
   │ dom_business │       │ dom_use_case │       │   dom_adr    │
   │    _case     │──────▶│              │◀──────│              │
   └──────────────┘  1:N  └──────────────┘  M:N  └──────────────┘

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

Lookup-Domains
--------------

+----------------------+------------------------------------+
| Domain Code          | Beschreibung                       |
+======================+====================================+
| bc_status            | Business Case Status               |
+----------------------+------------------------------------+
| bc_category          | Business Case Kategorie            |
+----------------------+------------------------------------+
| bc_priority          | Priorität                          |
+----------------------+------------------------------------+
| uc_status            | Use Case Status                    |
+----------------------+------------------------------------+
| uc_complexity        | Use Case Komplexität               |
+----------------------+------------------------------------+
| adr_status           | ADR Status                         |
+----------------------+------------------------------------+
| review_decision      | Review Entscheidung                |
+----------------------+------------------------------------+
| conversation_status  | Konversations-Status               |
+----------------------+------------------------------------+
| conversation_role    | Rolle (user/assistant/system)      |
+----------------------+------------------------------------+

Seed Data
---------

Initiale Daten werden via SQL-Fixture geladen:

.. code-block:: bash

   # Auf dem Server
   docker exec -i bfagent_db psql -U bfagent platform < seed_lookups.sql
