Architektur
===========

DDL Governance ist als eigenständiger Django-Service deployed.

Systemübersicht
---------------

.. code-block:: text

   ┌─────────────────┐     ┌─────────────────┐
   │   Browser       │────▶│     Nginx       │
   │                 │     │  (SSL/Proxy)    │
   └─────────────────┘     └────────┬────────┘
                                    │
                           ┌────────▼────────┐
                           │ governance_web  │
                           │   (Port 8082)   │
                           │   Django/WSGI   │
                           └────────┬────────┘
                                    │
                           ┌────────▼────────┐
                           │   bfagent_db    │
                           │   PostgreSQL    │
                           │ platform schema │
                           └─────────────────┘

Komponenten
-----------

Django Container
^^^^^^^^^^^^^^^^

* **Image**: Lokal gebaut (``governance:latest``)
* **Port**: 8082 (intern 8000)
* **Framework**: Django 5.x + Gunicorn
* **Netzwerk**: ``bf_platform_prod`` (Docker)

Datenbank
^^^^^^^^^

* **Host**: ``bfagent_db`` Container
* **Database**: PostgreSQL
* **Schema**: ``platform``
* **Tabellen**: ``lkp_domain``, ``lkp_choice``, ``dom_business_case``, etc.

Nginx Reverse Proxy
^^^^^^^^^^^^^^^^^^^

* **Domain**: governance.iil.pet
* **SSL**: Let's Encrypt (auto-renew)
* **IPv4 + IPv6**: Beide aktiviert

Tech Stack
----------

+----------------+------------------+
| Komponente     | Technologie      |
+================+==================+
| Backend        | Django 5.x       |
+----------------+------------------+
| WSGI Server    | Gunicorn         |
+----------------+------------------+
| Database       | PostgreSQL 16    |
+----------------+------------------+
| Frontend       | Bootstrap 5      |
+----------------+------------------+
| Interaktivität | HTMX             |
+----------------+------------------+
| Icons          | Bootstrap Icons  |
+----------------+------------------+

Designprinzipien
----------------

1. **Separation of Concerns**: Eigenständiger Service, nicht Teil von weltenhub
2. **ADR-015 Lookup Pattern**: Keine Hardcoded Enums
3. **Managed=False Models**: Django liest nur, keine Migrations
4. **Volume Mounts**: Hot-Reload für Entwicklung
