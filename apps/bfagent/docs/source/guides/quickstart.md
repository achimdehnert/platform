# Quickstart Guide

```{note}
Diese Anleitung führt Sie in 5 Minuten zu einer funktionierenden BF Agent Installation.
```

## Voraussetzungen

- Python 3.11+
- PostgreSQL 14+ (oder SQLite für Entwicklung)
- Redis (für Celery)
- Git

## Installation

### 1. Repository klonen

```bash
git clone https://github.com/your-org/bf-agent.git
cd bf-agent
```

### 2. Virtual Environment erstellen

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oder: venv\Scripts\activate  # Windows
```

### 3. Dependencies installieren

```bash
pip install -r requirements.txt
```

### 4. Umgebungsvariablen konfigurieren

```bash
cp .env.example .env
# Bearbeiten Sie .env mit Ihren Einstellungen
```

Mindest-Konfiguration in `.env`:

```ini
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///db.sqlite3

# AI Provider (mindestens einer)
OPENAI_API_KEY=sk-...
# oder
ANTHROPIC_API_KEY=sk-ant-...
```

### 5. Datenbank migrieren

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 6. Server starten

```bash
python manage.py runserver
```

Öffnen Sie http://localhost:8000/admin/ im Browser.

## Erster Workflow

### Handler über Admin aktivieren

1. Navigieren Sie zu **Admin → Handler Registry**
2. Aktivieren Sie die gewünschten Handler
3. Konfigurieren Sie die Domain-spezifischen Einstellungen

### Beispiel: Comic erstellen

```python
from bf_agent.domains.comics import ComicProject

# Neues Projekt erstellen
project = ComicProject.objects.create(
    title="Mein erster Comic",
    genre="superhero",
    target_pages=8
)

# Handler ausführen
from bf_agent.handlers import execute_handler

result = execute_handler(
    handler_name="story_generator",
    context={"project_id": project.id}
)
```

## Nächste Schritte

```{seealso}
- {doc}`installation` - Detaillierte Installationsanleitung
- {doc}`configuration` - Konfigurationsoptionen
- {doc}`/domains/index` - Verfügbare Domains
```

## Troubleshooting

### Häufige Fehler

:::{dropdown} ModuleNotFoundError: No module named 'bf_agent'
Stellen Sie sicher, dass Sie sich im richtigen Verzeichnis befinden und das Virtual Environment aktiviert ist.
:::

:::{dropdown} Database connection failed
Überprüfen Sie Ihre `DATABASE_URL` in der `.env` Datei.
:::

:::{dropdown} AI API Error: 401 Unauthorized
Überprüfen Sie Ihre API-Keys in der `.env` Datei.
:::
