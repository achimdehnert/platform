Weltenhub API
=============

REST API bereitgestellt via Django REST Framework + drf-spectacular.

**Swagger UI**: https://weltenforger.com/api/docs/

**OpenAPI Schema**: https://weltenforger.com/api/schema/

Endpoints
---------

+----------------------------+--------+-----------------------------+
| URL                        | Method | Beschreibung                |
+============================+========+=============================+
| ``/api/v1/tenants/``       | GET    | Tenant-Verwaltung           |
+----------------------------+--------+-----------------------------+
| ``/api/v1/lookups/``       | GET    | Genres, Moods, Types        |
+----------------------------+--------+-----------------------------+
| ``/api/v1/worlds/``        | CRUD   | Welten                      |
+----------------------------+--------+-----------------------------+
| ``/api/v1/locations/``     | CRUD   | Hierarchische Orte          |
+----------------------------+--------+-----------------------------+
| ``/api/v1/characters/``    | CRUD   | Charaktere                  |
+----------------------------+--------+-----------------------------+
| ``/api/v1/scenes/``        | CRUD   | Szenen                      |
+----------------------------+--------+-----------------------------+
| ``/api/v1/stories/``       | CRUD   | Geschichten & Kapitel       |
+----------------------------+--------+-----------------------------+

Authentifizierung
-----------------

Session-basiert (``SessionAuthentication``). Alle Endpoints erfordern Login.

Pagination
----------

``PageNumberPagination`` mit ``PAGE_SIZE=20``.

Filter
------

- ``DjangoFilterBackend`` — Feldbasierte Filter
- ``SearchFilter`` — Volltextsuche
- ``OrderingFilter`` — Sortierung
