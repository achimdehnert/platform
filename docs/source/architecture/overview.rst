Plattform-Übersicht
===================

Das BF Agent Ecosystem besteht aus mehreren Django-Applikationen,
die auf einer gemeinsamen Infrastruktur betrieben werden.

Ecosystem
---------

.. code-block:: text

                         ┌──────────────────┐
                         │    platform/     │
                         │ (Packages, ADRs, │
                         │  Docs, Concepts) │
                         └────────┬─────────┘
                                  │
       ┌──────────┬───────────────┼───────────────┬──────────┐
       ▼          ▼               ▼               ▼          ▼
  ┌──────────┐ ┌───────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐
  │ bfagent  │ │travel-beat│ │ weltenhub│ │ risk-hub │ │ cad-hub │
  │ (Django) │ │ (Django)  │ │ (Django) │ │ (Django) │ │ (Django)│
  └──────────┘ └───────────┘ └──────────┘ └──────────┘ └─────────┘
  Book Writing  Travel        Story         Occupational  CAD/BIM
  bfagent.      Stories       Universes     Safety SaaS   Viewer
  iil.pet       drifttales    weltenforger  schutztat.de  cadhub.
                .com          .com                        iil.pet

Shared Infrastructure
---------------------

Alle Apps laufen auf einem Hetzner VM (``88.198.191.108``):

+------------------+------+----------------------+---------------------+
| App              | Port | Domain               | Server-Pfad         |
+==================+======+======================+=====================+
| bfagent          | 8000 | bfagent.iil.pet      | /opt/bfagent-app    |
+------------------+------+----------------------+---------------------+
| travel-beat      | 8002 | drifttales.com       | /opt/travel-beat    |
+------------------+------+----------------------+---------------------+
| weltenhub        | 8081 | weltenforger.com     | /opt/weltenhub      |
+------------------+------+----------------------+---------------------+
| mcp-hub          | 8003 | mcp-hub.iil.pet      | /opt/mcp-hub        |
+------------------+------+----------------------+---------------------+
| cad-hub          | 8004 | cadhub.iil.pet       | /opt/cad-hub        |
+------------------+------+----------------------+---------------------+

Shared Services:

- **PostgreSQL 16** — ``bfagent_db`` Container (shared by all apps)
- **Redis 7** — ``bfagent_redis`` Container (cache + Celery broker)
- **Nginx** — Reverse Proxy mit TLS (Let's Encrypt)
- **Docker Network** — ``bf_platform_prod`` (extern)

Design-Prinzipien
-----------------

Database-First
   Alle Choices aus ``lkp_*`` Lookup-Tabellen, keine hardcoded Enums.

Multi-Tenant
   Row-Level Isolation via ``tenant_id`` FK auf allen Daten-Models.

Soft Delete
   ``deleted_at`` Feld statt Hard Deletes.

Audit Trail
   ``created_at``, ``updated_at``, ``created_by``, ``updated_by`` auf allen Models.

UUID Primary Keys
   Für externe Referenzen und verteilte Systeme.
