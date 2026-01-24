Architecture
============

Travel Beat follows Django best practices with a modular app structure.

Project Structure
-----------------

.. code-block:: text

   travel-beat/
   ├── apps/
   │   ├── accounts/       # User authentication
   │   ├── trips/          # Trip management & wizard
   │   ├── stories/        # Story generation & reading
   │   ├── subscriptions/  # SaaS billing
   │   └── core/           # Shared utilities
   ├── config/
   │   ├── settings/       # Environment-specific settings
   │   ├── urls.py         # Root URL configuration
   │   ├── celery.py       # Celery configuration
   │   └── wsgi.py         # WSGI entry point
   ├── templates/          # Global templates
   ├── static/             # Static assets
   ├── docker/             # Docker configuration
   └── docs/               # Sphinx documentation

Technology Stack
----------------

**Backend:**

- Django 5.0 - Web framework
- PostgreSQL 15 - Primary database
- Redis 7 - Cache & Celery broker
- Celery 5 - Async task queue
- Gunicorn - WSGI server

**Frontend:**

- Django Templates - Server-side rendering
- Bootstrap 5 - CSS framework
- HTMX - Dynamic interactions
- Alpine.js - Lightweight reactivity

**AI Integration:**

- Anthropic Claude - Story generation
- Async processing via Celery

**Infrastructure:**

- Docker & Docker Compose
- Caddy - Reverse proxy & SSL
- GitHub Actions - CI/CD

Data Flow
---------

.. code-block:: text

   User Request
        │
        ▼
   ┌─────────┐
   │  Caddy  │  (SSL termination, reverse proxy)
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │ Django  │  (Request handling, business logic)
   └────┬────┘
        │
   ┌────┴────┐
   │         │
   ▼         ▼
┌──────┐  ┌───────┐
│ PostgreSQL │  │ Redis │
└──────┘  └───┬───┘
              │
              ▼
         ┌────────┐
         │ Celery │  (Async story generation)
         └────┬───┘
              │
              ▼
         ┌─────────┐
         │ Claude  │  (AI story generation)
         └─────────┘

Key Design Decisions
--------------------

**Session-Based Wizard**
   Trip creation wizard stores data in session across steps,
   only persisting to database on final submission.

**Async Story Generation**
   Long-running AI calls handled by Celery workers to avoid
   blocking web requests. Progress tracked via polling.

**Modular Apps**
   Each feature area is a separate Django app for maintainability
   and potential future extraction as microservices.

**Environment-Based Settings**
   Separate settings modules for development, test, and production
   with shared base configuration.
