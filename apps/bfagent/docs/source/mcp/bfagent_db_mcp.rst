=============
BFAgent DB MCP
=============

.. note::
   **PostgreSQL & Django ORM Integration** | 8 Tools | Status: Production

Übersicht
=========

Der BFAgent DB MCP Server bietet sicheren, strukturierten Zugriff auf die
PostgreSQL-Datenbank mit Django-Integration. Alle Queries sind read-only
(außer Django Migrations).

Features:

- **Tabellen-Inspektion**: Struktur, Indizes, Foreign Keys
- **Django Models**: ORM-Metadaten und Relations
- **Query-Analyse**: EXPLAIN ANALYZE für Optimierung
- **Migration Status**: Django Migrations verfolgen
- **Sichere Queries**: Nur SELECT, parametrisiert

Installation
============

.. code-block:: bash

   cd packages/bfagent_db_mcp
   pip install -e .

Umgebungsvariablen
------------------

.. code-block:: bash

   export BFAGENT_PROJECT_ROOT=/path/to/bfagent
   export DJANGO_SETTINGS_MODULE=config.settings

Start
-----

.. code-block:: bash

   python server.py

Tools
=====

Tabellen-Inspektion
-------------------

.. function:: db_list_tables(schema?)

   Listet alle Tabellen mit Row-Counts und Größen.
   
   :param schema: Database Schema (default: public)
   :return: Tabellen-Liste mit Statistiken
   
   Beispiel-Ausgabe:
   
   .. code-block:: json
   
      {
        "schema": "public",
        "table_count": 85,
        "tables": [
          {"name": "llms", "row_count": 10, "size": "48 kB"},
          {"name": "agents", "row_count": 15, "size": "64 kB"}
        ]
      }

.. function:: db_describe_table(table_name)

   Zeigt detaillierte Tabellen-Struktur.
   
   :param table_name: Name der Tabelle
   :return: Columns, Types, Indexes, Foreign Keys, Primary Key
   
   Beispiel-Ausgabe:
   
   .. code-block:: json
   
      {
        "table": "agents",
        "columns": [
          {"name": "id", "type": "integer", "nullable": false},
          {"name": "name", "type": "varchar(200)", "nullable": false},
          {"name": "llm_id", "type": "integer", "nullable": true}
        ],
        "indexes": [
          {"name": "agents_pkey", "definition": "PRIMARY KEY (id)"}
        ],
        "foreign_keys": [
          {"column": "llm_id", "references": "llms.id"}
        ],
        "primary_key": "id"
      }

.. function:: db_search_tables(pattern)

   Sucht Tabellen nach Name-Pattern (case-insensitive).
   
   :param pattern: Suchmuster (z.B. 'book', 'user', 'workflow')
   :return: Matching Tabellen mit Row-Counts

.. function:: db_table_stats(table_name)

   Detaillierte Tabellen-Statistiken.
   
   :param table_name: Name der Tabelle
   :return: Live/Dead Rows, Vacuum-Info, Größen
   
   Beispiel:
   
   .. code-block:: json
   
      {
        "table": "chapters_v2",
        "live_rows": 150,
        "dead_rows": 5,
        "last_vacuum": "2026-01-15T10:30:00",
        "total_size": "256 kB",
        "table_size": "128 kB",
        "index_size": "128 kB"
      }

Django Integration
------------------

.. function:: db_django_models(app_label?)

   Listet Django Models mit Fields und Relations.
   
   :param app_label: App-Filter (z.B. 'bfagent', 'writing_hub')
   :return: Models pro App mit Feldern
   
   Beispiel:
   
   .. code-block:: json
   
      {
        "apps": [
          {
            "label": "writing_hub",
            "models": [
              {
                "name": "BookProject",
                "db_table": "writing_book_projects",
                "fields": [
                  {"name": "title", "type": "CharField"},
                  {"name": "genre", "type": "ForeignKey", "related_to": "Genre"}
                ]
              }
            ]
          }
        ]
      }

.. function:: db_migration_status(app_label?)

   Zeigt Django Migration Status.
   
   :param app_label: Optional App-Filter
   :return: Angewandte Migrations pro App

Query-Ausführung
----------------

.. function:: db_execute_query(sql, params?)

   Führt sichere, parametrisierte SELECT Query aus.
   
   :param sql: SELECT Query mit Platzhaltern
   :param params: Query-Parameter als Array
   :return: Columns und Rows (max 100)
   
   **Nur SELECT erlaubt!**
   
   Beispiel:
   
   .. code-block:: python
   
      db_execute_query(
          sql="SELECT name, status FROM agents WHERE is_active = %s",
          params=["true"]
      )

.. function:: db_analyze_query(sql)

   EXPLAIN ANALYZE für Query-Optimierung.
   
   :param sql: SELECT Query
   :return: Execution Plan, Timing, Buffer Usage
   
   **Nur SELECT erlaubt!**
   
   Beispiel-Ausgabe:
   
   .. code-block:: json
   
      {
        "query": "SELECT * FROM chapters_v2 WHERE book_id = 1",
        "execution_time_ms": 0.5,
        "planning_time_ms": 0.1,
        "plan": {
          "Node Type": "Index Scan",
          "Index Name": "chapters_v2_book_id_idx"
        }
      }

Beispiele
=========

Tabellen erkunden
-----------------

.. code-block:: python

   # Alle Tabellen mit 'book' im Namen
   db_search_tables(pattern="book")
   
   # Struktur einer Tabelle
   db_describe_table(table_name="writing_book_projects")
   
   # Statistiken
   db_table_stats(table_name="chapters_v2")

Django Models analysieren
-------------------------

.. code-block:: python

   # Models einer App
   db_django_models(app_label="writing_hub")
   
   # Migration Status prüfen
   db_migration_status(app_label="writing_hub")

Query-Optimierung
-----------------

.. code-block:: python

   # Query analysieren
   db_analyze_query(
       sql="SELECT * FROM chapters_v2 WHERE book_id = 1 ORDER BY chapter_number"
   )
   
   # Index-Nutzung prüfen
   # → Wenn "Seq Scan" statt "Index Scan": Index hinzufügen!

Sicherheit
==========

- **Nur SELECT**: Keine INSERT/UPDATE/DELETE möglich
- **Parametrisiert**: SQL Injection verhindert
- **Limit 100**: Große Result Sets begrenzt
- **Read-Only Connection**: Schreibzugriff auf DB-Ebene blockiert
- **Django Settings**: Nutzt konfigurierte DB-Credentials
