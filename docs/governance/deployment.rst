Deployment
==========

DDL Governance läuft als eigenständiger Docker-Container auf dem 
Produktionsserver ``88.198.191.108``.

Server-Struktur
---------------

.. code-block:: text

   /opt/governance/
   ├── docker-compose.yml    # Container-Konfiguration
   ├── Dockerfile            # Image-Definition
   ├── .env                  # Umgebungsvariablen
   ├── requirements.txt      # Python Dependencies
   ├── manage.py             # Django Management
   ├── config/               # Django Settings
   │   ├── settings.py
   │   ├── urls.py
   │   └── wsgi.py
   └── governance/           # App (Volume Mount)
       ├── models.py
       ├── views.py
       ├── urls.py
       └── templates/

Deployment-Befehle
------------------

Code synchronisieren
^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Von lokal zum Server
   rsync -avz governance-deploy/ root@88.198.191.108:/opt/governance/

Container neu bauen
^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   ssh root@88.198.191.108
   cd /opt/governance
   docker build --no-cache -t governance:latest .
   docker compose up -d --force-recreate

Logs prüfen
^^^^^^^^^^^

.. code-block:: bash

   docker logs governance_web --tail 50
   docker logs governance_web -f  # Live-Follow

Container-Status
^^^^^^^^^^^^^^^^

.. code-block:: bash

   docker ps | grep governance
   docker exec governance_web python manage.py check

Umgebungsvariablen
------------------

Die ``.env`` Datei enthält:

.. code-block:: ini

   SECRET_KEY=<django-secret>
   DEBUG=False
   ALLOWED_HOSTS=governance.iil.pet,localhost
   CSRF_TRUSTED_ORIGINS=https://governance.iil.pet
   
   # Database
   DB_NAME=platform
   DB_USER=bfagent
   DB_PASSWORD=<password>
   DB_HOST=bfagent_db
   DB_PORT=5432

Nginx-Konfiguration
-------------------

Datei: ``/etc/nginx/sites-enabled/governance.iil.pet.conf``

.. code-block:: nginx

   server {
       listen 80;
       listen [::]:80;
       server_name governance.iil.pet;

       location /.well-known/acme-challenge/ {
           root /var/www/html;
       }

       location / {
           proxy_pass http://127.0.0.1:8082;
           proxy_http_version 1.1;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto https;
       }
   }

SSL-Zertifikat
--------------

Certbot für Let's Encrypt:

.. code-block:: bash

   certbot --nginx -d governance.iil.pet

Auto-Renewal ist via systemd timer aktiviert.

Troubleshooting
---------------

500 Internal Server Error
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Logs prüfen
   docker logs governance_web 2>&1 | tail -30
   
   # Django Check
   docker exec governance_web python manage.py check

Container startet nicht
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Netzwerk prüfen
   docker network ls | grep bf_platform_prod
   
   # DB-Verbindung testen
   docker exec governance_web python -c "from django.db import connection; connection.ensure_connection()"
