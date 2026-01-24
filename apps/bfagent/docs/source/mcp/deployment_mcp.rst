==============
Deployment MCP
==============

.. note::
   **Infrastructure Management** | 50+ Tools | Status: Production

Übersicht
=========

Der Deployment MCP Server bietet vollständiges Infrastructure Management
für Hetzner Cloud, Docker, SSL, DNS und Datenbanken.

Kategorien:

- **Hetzner Cloud**: Server, Firewalls, SSH Keys
- **Docker**: Container, Compose, Logs
- **PostgreSQL**: Databases, Backups, Migrations
- **SSL/TLS**: Zertifikate, Renewal, Let's Encrypt
- **DNS**: Zonen, Records, Cloudflare
- **Environment**: Secrets, Configs

Installation
============

.. code-block:: bash

   cd packages/deployment_mcp
   pip install -e .

Umgebungsvariablen
------------------

.. code-block:: bash

   # Hetzner Cloud
   export HETZNER_API_TOKEN=xxx
   
   # SSH
   export SSH_KEY_PATH=~/.ssh/id_rsa
   
   # Remote Host
   export DEPLOY_HOST=bfagent.iil.pet
   export DEPLOY_USER=root

Start
-----

.. code-block:: bash

   python server.py
   
   # Mit Tool-Allowlist (Sicherheit)
   DEPLOYMENT_MCP_TOOL_ALLOWLIST=server_list,server_status python server.py

Tools
=====

Hetzner Server
--------------

.. function:: server_list()

   Listet alle Hetzner Cloud Server.
   
   :return: Server mit ID, Name, Status, IP, Type

.. function:: server_status(server_id)

   Holt Server-Status und Details.
   
   :param server_id: Hetzner Server ID
   :return: Status, Metrics, Volumes

.. function:: server_power(server_id, action)

   Server Power Management.
   
   :param action: on, off, reboot, reset
   :return: Action Status

.. function:: server_create(name, server_type, image, location?, ssh_keys?, firewalls?)

   Erstellt neuen Server.
   
   :param name: Server-Name
   :param server_type: cx11, cx21, cpx11, etc.
   :param image: ubuntu-22.04, debian-11, etc.
   :param location: nbg1, fsn1, hel1
   :param ssh_keys: Liste von SSH Key IDs
   :return: Neuer Server mit Root-Passwort

.. function:: server_delete(server_id)

   Löscht Server.
   
   :param server_id: Server ID
   :return: Bestätigung

.. function:: server_rebuild(server_id, image)

   Rebuilt Server mit neuem Image.

.. function:: server_types_list()

   Listet verfügbare Server-Typen mit Preisen.

.. function:: images_list()

   Listet verfügbare OS-Images.

.. function:: locations_list()

   Listet Hetzner Datacenter Locations.

Firewalls
---------

.. function:: firewall_list()

   Listet alle Firewalls.

.. function:: firewall_get(firewall_id)

   Holt Firewall-Details mit Regeln.

.. function:: firewall_create(name, rules?)

   Erstellt neue Firewall.
   
   :param rules: Liste von Regeln (direction, protocol, port, source_ips)

.. function:: firewall_set_rules(firewall_id, rules)

   Setzt Firewall-Regeln.

.. function:: firewall_apply(firewall_id, server_ids)

   Wendet Firewall auf Server an.

.. function:: firewall_remove(firewall_id, server_ids)

   Entfernt Firewall von Servern.

.. function:: firewall_delete(firewall_id)

   Löscht Firewall.

SSH Keys
--------

.. function:: ssh_key_list()

   Listet alle SSH Keys.

.. function:: ssh_key_create(name, public_key)

   Fügt neuen SSH Key hinzu.

.. function:: ssh_key_delete(ssh_key_id)

   Löscht SSH Key.

Docker Container
----------------

.. function:: container_list(host?)

   Listet alle Container.
   
   :param host: Remote Host (default: local)

.. function:: container_status(container_id, host?)

   Holt Container-Status.

.. function:: container_logs(container_id, tail?, host?)

   Holt Container-Logs.
   
   :param tail: Letzte N Zeilen

.. function:: container_restart(container_id, host?)

   Startet Container neu.

.. function:: container_start(container_id, host?)

   Startet gestoppten Container.

.. function:: container_stop(container_id, host?)

   Stoppt Container.

Docker Compose
--------------

.. function:: compose_ps(project_dir?, compose_file?, host?)

   Zeigt Compose Services.
   
   :param project_dir: Projekt-Verzeichnis
   :param compose_file: Compose-Datei (default: docker-compose.yml)

.. function:: compose_up(project_dir?, compose_file?, services?, detach?, host?)

   Startet Compose Services.
   
   :param services: Spezifische Services (optional)
   :param detach: Im Hintergrund

.. function:: compose_down(project_dir?, compose_file?, volumes?, host?)

   Stoppt Compose Services.
   
   :param volumes: Volumes auch löschen

.. function:: compose_logs(project_dir?, compose_file?, services?, tail?, host?)

   Holt Compose Logs.

.. function:: compose_pull(project_dir?, compose_file?, services?, host?)

   Pulled neue Images.

.. function:: compose_restart(project_dir?, compose_file?, services?, host?)

   Startet Services neu.

BFAgent Deployment
------------------

.. function:: bfagent_deploy_web(image_tag, host?, project_dir?, compose_file?, env_file?, service?, pull?, recreate?, verify_url?, expect_http_status?)

   Deployed bfagent-web auf Remote Host.
   
   :param image_tag: Image Tag (prefer full Git SHA)
   :param host: SSH Host Override
   :param project_dir: /opt/bfagent-app
   :param compose_file: docker-compose.prod.yml
   :param verify_url: https://bfagent.iil.pet/login/
   :return: Deploy Status, HTTP Check

PostgreSQL
----------

.. function:: db_list(host?)

   Listet alle Datenbanken.

.. function:: db_status(database, host?)

   Holt DB-Status und Connections.

.. function:: db_create(database, owner?, host?)

   Erstellt neue Datenbank.

.. function:: db_drop(database, host?)

   Löscht Datenbank (VORSICHT!).

.. function:: db_query(database, query, host?)

   Führt SQL Query aus.

.. function:: db_backup(database, output_path?, host?)

   Erstellt DB-Backup.

.. function:: db_backup_list(host?)

   Listet vorhandene Backups.

.. function:: db_restore(database, backup_path, host?)

   Stellt DB aus Backup wieder her.

.. function:: db_migrate(host?)

   Führt Django Migrations aus.

SSL/TLS
-------

.. function:: ssl_status(domain?, host?)

   Zeigt SSL-Zertifikat Status.

.. function:: ssl_expiring(days?, host?)

   Listet bald ablaufende Zertifikate.
   
   :param days: Warnschwelle in Tagen

.. function:: ssl_renew(domain?, host?)

   Erneuert Zertifikat.

.. function:: ssl_obtain(domain, email?, host?)

   Holt neues Zertifikat via Let's Encrypt.

.. function:: ssl_revoke(domain, host?)

   Widerruft Zertifikat.

.. function:: ssl_delete(domain, host?)

   Löscht Zertifikat.

.. function:: ssl_certbot_info(host?)

   Zeigt Certbot-Konfiguration.

DNS Management
--------------

.. function:: dns_zone_list()

   Listet DNS Zonen.

.. function:: dns_zone_get(zone_id)

   Holt Zone-Details.

.. function:: dns_zone_create(name, ttl?)

   Erstellt neue DNS Zone.

.. function:: dns_zone_delete(zone_id)

   Löscht Zone.

.. function:: dns_record_list(zone_id)

   Listet DNS Records.

.. function:: dns_record_get(zone_id, record_id)

   Holt Record-Details.

.. function:: dns_record_create(zone_id, name, type, value, ttl?)

   Erstellt DNS Record.
   
   :param type: A, AAAA, CNAME, MX, TXT, etc.

.. function:: dns_record_update(zone_id, record_id, name?, type?, value?, ttl?)

   Aktualisiert Record.

.. function:: dns_record_delete(zone_id, record_id)

   Löscht Record.

.. function:: dns_find_records(pattern)

   Sucht Records nach Pattern.

.. function:: dns_set_a_record(zone_id, name, ip)

   Setzt A Record (Shortcut).

.. function:: dns_set_cname_record(zone_id, name, target)

   Setzt CNAME Record (Shortcut).

Environment & Secrets
---------------------

.. function:: env_list(host?)

   Listet Umgebungsvariablen.

.. function:: env_get(key, host?)

   Holt einzelne Variable.

.. function:: env_set(key, value, host?)

   Setzt Variable.

.. function:: env_delete(key, host?)

   Löscht Variable.

.. function:: env_validate(host?)

   Validiert erforderliche Variablen.

.. function:: secret_list(host?)

   Listet Secrets (Namen, keine Werte).

.. function:: secret_set(name, value, host?)

   Setzt Secret.

.. function:: secret_delete(name, host?)

   Löscht Secret.

Beispiele
=========

Server erstellen
----------------

.. code-block:: python

   # Server erstellen
   server_create(
       name="bfagent-prod",
       server_type="cpx21",
       image="ubuntu-22.04",
       location="nbg1",
       ssh_keys=[12345],
       firewalls=[67890]
   )
   
   # Status prüfen
   server_status(server_id=123456)

Deployment Workflow
-------------------

.. code-block:: python

   # 1. Images pullen
   compose_pull(
       project_dir="/opt/bfagent-app",
       compose_file="docker-compose.prod.yml",
       host="bfagent.iil.pet"
   )
   
   # 2. Deployen
   bfagent_deploy_web(
       image_tag="052bc3c2cc27926e6fa104e94fceaea0f58df08e",
       verify_url="https://bfagent.iil.pet/login/"
   )
   
   # 3. Logs prüfen
   compose_logs(
       project_dir="/opt/bfagent-app",
       services=["bfagent-web"],
       tail=50
   )

SSL erneuern
------------

.. code-block:: python

   # Ablaufende Zertifikate finden
   ssl_expiring(days=30)
   
   # Erneuern
   ssl_renew(domain="bfagent.iil.pet")

Sicherheit
==========

Tool Allowlist
--------------

Für Produktionsumgebungen empfohlen:

.. code-block:: bash

   # Nur lesende Tools erlauben
   export DEPLOYMENT_MCP_TOOL_ALLOWLIST=server_list,server_status,container_list,compose_ps,ssl_status

Gefährliche Tools
-----------------

.. warning::
   Folgende Tools können destruktiv sein:
   
   - ``server_delete``
   - ``db_drop``
   - ``firewall_delete``
   - ``secret_delete``
   
   Nur mit Vorsicht verwenden!
