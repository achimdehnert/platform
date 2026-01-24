# Installationsanleitung

Diese Anleitung beschreibt die vollständige Installation von BF Agent
in verschiedenen Umgebungen.

## Systemanforderungen

### Minimum

| Komponente | Anforderung |
|------------|-------------|
| Python | 3.11+ |
| RAM | 4 GB |
| Speicher | 10 GB |
| OS | Linux, macOS, Windows |

### Empfohlen (Produktion)

| Komponente | Anforderung |
|------------|-------------|
| Python | 3.12 |
| RAM | 16 GB |
| Speicher | 50 GB SSD |
| OS | Ubuntu 22.04 LTS |
| CPU | 4+ Cores |

## Entwicklungsumgebung

### 1. Repository klonen

```bash
git clone https://github.com/your-org/bf-agent.git
cd bf-agent
```

### 2. Python-Umgebung einrichten

```{tab} venv
\`\`\`bash
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
\`\`\`
```

```{tab} conda
\`\`\`bash
conda create -n bf-agent python=3.12
conda activate bf-agent
\`\`\`
```

```{tab} poetry
\`\`\`bash
poetry install
poetry shell
\`\`\`
```

### 3. Dependencies installieren

```bash
# Basis-Dependencies
pip install -r requirements.txt

# Entwickler-Dependencies (Tests, Linting)
pip install -r requirements-dev.txt

# Dokumentations-Dependencies
pip install -r docs/requirements.txt
```

### 4. Umgebungsvariablen

Kopiere die Beispiel-Konfiguration:

```bash
cp .env.example .env
```

Bearbeite `.env` mit deinen Einstellungen:

```ini
# Django Settings
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=sqlite:///db.sqlite3
# oder PostgreSQL:
# DATABASE_URL=postgres://user:pass@localhost:5432/bf_agent

# Redis (für Celery)
REDIS_URL=redis://localhost:6379/0

# AI Provider (mindestens einer erforderlich)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Optionale AI Provider
TOGETHER_API_KEY=...
OLLAMA_HOST=http://localhost:11434
```

### 5. Datenbank einrichten

```bash
# Migrationen ausführen
python manage.py migrate

# Superuser erstellen
python manage.py createsuperuser

# Initiale Daten laden (optional)
python manage.py loaddata fixtures/initial_data.json
```

### 6. Server starten

```bash
# Entwicklungsserver
python manage.py runserver

# Mit Celery Worker (separates Terminal)
celery -A bf_agent worker -l info
```

## Produktionsumgebung

### Docker-Installation

```{note}
Docker ist die empfohlene Methode für Produktionsdeployments.
```

#### Docker Compose (empfohlen)

```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEBUG=False
      - DATABASE_URL=postgres://postgres:password@db:5432/bf_agent
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  worker:
    build: .
    command: celery -A bf_agent worker -l info
    environment:
      - DATABASE_URL=postgres://postgres:password@db:5432/bf_agent
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=bf_agent
      - POSTGRES_PASSWORD=password

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

Starten:

```bash
docker-compose up -d
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

### Manuelle Installation

Für Server ohne Docker:

```bash
# System-Dependencies (Ubuntu)
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-dev \
    postgresql postgresql-contrib redis-server nginx

# PostgreSQL einrichten
sudo -u postgres createuser bf_agent
sudo -u postgres createdb -O bf_agent bf_agent

# Application installieren
cd /opt
sudo git clone https://github.com/your-org/bf-agent.git
cd bf-agent
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Gunicorn für Production
pip install gunicorn
```

### Nginx-Konfiguration

```nginx
# /etc/nginx/sites-available/bf-agent
server {
    listen 80;
    server_name your-domain.com;

    location /static/ {
        alias /opt/bf-agent/staticfiles/;
    }

    location /media/ {
        alias /opt/bf-agent/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Systemd Service

```ini
# /etc/systemd/system/bf-agent.service
[Unit]
Description=BF Agent Web Application
After=network.target postgresql.service redis.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/bf-agent
Environment="PATH=/opt/bf-agent/venv/bin"
ExecStart=/opt/bf-agent/venv/bin/gunicorn \
    --workers 4 \
    --bind 127.0.0.1:8000 \
    bf_agent.wsgi:application

[Install]
WantedBy=multi-user.target
```

## Troubleshooting

### Häufige Probleme

:::{dropdown} ImportError: No module named 'bf_agent'
**Lösung:** Stelle sicher, dass das Virtual Environment aktiviert ist:
```bash
source venv/bin/activate
```
:::

:::{dropdown} Database connection refused
**Lösung:** Prüfe ob PostgreSQL läuft:
```bash
sudo systemctl status postgresql
```
:::

:::{dropdown} Redis connection failed
**Lösung:** Prüfe ob Redis läuft:
```bash
redis-cli ping
```
:::

:::{dropdown} Static files not loading
**Lösung:** Sammle static files:
```bash
python manage.py collectstatic
```
:::

## Nächste Schritte

Nach erfolgreicher Installation:

1. {doc}`configuration` - System konfigurieren
2. {doc}`/guides/django-admin` - Admin-Interface nutzen
3. {doc}`/domains/index` - Domains aktivieren
