Deployment Guide
================

Travel Beat is deployed using Docker on Hetzner Cloud.

Infrastructure
--------------

**Server:** Hetzner Cloud CX21 (2 vCPU, 4GB RAM)

**Domain:** travel-beat.iil.pet

**Services:**

- Django (Gunicorn)
- PostgreSQL 15
- Redis 7
- Celery Worker
- Celery Beat
- Caddy (shared with BF Agent)

Docker Compose
--------------

Production deployment uses ``docker/docker-compose.prod.yml``:

.. code-block:: yaml

   services:
     travel-beat-web:
       image: ghcr.io/achimdehnert/travel-beat:latest
       depends_on:
         - travel-beat-db
         - travel-beat-redis

     travel-beat-celery:
       image: ghcr.io/achimdehnert/travel-beat:latest
       command: celery -A config worker -l info

     travel-beat-db:
       image: postgres:15-alpine

     travel-beat-redis:
       image: redis:7-alpine

CI/CD Pipeline
--------------

GitHub Actions workflow (``.github/workflows/deploy.yml``):

1. **Test** - Run pytest suite
2. **Build** - Build Docker image
3. **Push** - Push to GitHub Container Registry
4. **Deploy** - SSH to server, pull image, restart services

Deployment Steps
----------------

**Initial Setup:**

.. code-block:: bash

   # On server
   mkdir -p /opt/travel-beat
   cd /opt/travel-beat

   # Copy docker-compose.prod.yml
   # Create .env.prod with secrets

   # Start services
   docker compose --env-file .env.prod -f docker-compose.prod.yml up -d

**Update Deployment:**

.. code-block:: bash

   # Automated via GitHub Actions on push to main
   # Or manually:
   docker compose --env-file .env.prod -f docker-compose.prod.yml pull
   docker compose --env-file .env.prod -f docker-compose.prod.yml up -d

Environment Variables
---------------------

Required in ``.env.prod``:

.. code-block:: bash

   # Django
   SECRET_KEY=your-secret-key
   ALLOWED_HOSTS=travel-beat.iil.pet,localhost

   # Database
   POSTGRES_DB=travel_beat
   POSTGRES_USER=travelbeat
   POSTGRES_PASSWORD=secure-password

   # API Keys
   ANTHROPIC_API_KEY=sk-ant-...

   # Stripe (optional)
   STRIPE_PUBLIC_KEY=pk_...
   STRIPE_SECRET_KEY=sk_...

SSL/TLS
-------

Caddy automatically provisions Let's Encrypt certificates.

Caddyfile entry:

.. code-block:: text

   travel-beat.iil.pet {
       encode gzip
       reverse_proxy travel-beat-web:8000
   }

Monitoring
----------

**Logs:**

.. code-block:: bash

   docker logs travel_beat_web
   docker logs travel_beat_celery

**Health Check:**

.. code-block:: bash

   curl https://travel-beat.iil.pet/health/

Backup
------

Database backup:

.. code-block:: bash

   docker exec travel_beat_db pg_dump -U travelbeat travel_beat > backup.sql
