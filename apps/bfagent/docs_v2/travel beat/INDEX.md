# Travel Story - Dokumentation

> Personalisierte Geschichten für Ihre Reise

---

## 📚 Dokumentations-Übersicht

### Für Benutzer

| Dokument | Beschreibung |
|----------|--------------|
| [**USER_GUIDE.md**](USER_GUIDE.md) | Benutzerhandbuch mit Anleitungen |

### Für Entwickler

| Dokument | Beschreibung |
|----------|--------------|
| [**TECHNICAL_01_ARCHITECTURE.md**](TECHNICAL_01_ARCHITECTURE.md) | System-Architektur, Tech Stack, Komponenten |
| [**TECHNICAL_02_MODELS.md**](TECHNICAL_02_MODELS.md) | Django Models, Datenbankschema |
| [**TECHNICAL_03_VIEWS.md**](TECHNICAL_03_VIEWS.md) | Views, URLs, HTMX Patterns |
| [**TECHNICAL_04_SERVICES.md**](TECHNICAL_04_SERVICES.md) | Services, Celery, LLM, Setup |

---

## 🏗️ Architektur

```
┌────────────────────────────────────────────────────────┐
│                      FRONTEND                          │
│                                                        │
│   Django Templates + HTMX + Tailwind CSS              │
│                                                        │
└───────────────────────┬────────────────────────────────┘
                        │
┌───────────────────────▼────────────────────────────────┐
│                      DJANGO                            │
│                                                        │
│   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐ │
│   │  trips  │  │locations│  │ worlds  │  │ stories │ │
│   └─────────┘  └─────────┘  └─────────┘  └─────────┘ │
│                                                        │
└───────────────────────┬────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  PostgreSQL  │ │    Redis     │ │  Claude API  │
│              │ │   (Celery)   │ │  (Anthropic) │
└──────────────┘ └──────────────┘ └──────────────┘
```

---

## 🛠️ Tech Stack

| Komponente | Technologie |
|------------|-------------|
| Backend | Django 5.0 |
| Frontend | HTMX + Tailwind CSS |
| Datenbank | PostgreSQL 15 |
| Cache/Queue | Redis + Celery |
| LLM | Anthropic Claude |
| Container | Docker |

---

## 📁 Projekt-Struktur

```
travel_story/
├── config/              # Django Konfiguration
├── apps/
│   ├── trips/           # Reiseverwaltung
│   ├── locations/       # 3-Schichten Location-DB
│   ├── worlds/          # User Worlds
│   ├── stories/         # Story-Generierung
│   └── users/           # Auth & Profile
├── services/            # Business Logic
├── templates/           # Django Templates
├── static/              # CSS, JS
├── docker/              # Docker Setup
└── docs/                # Diese Dokumentation
```

---

## 🚀 Quick Start

### Development

```bash
# 1. Clone & Setup
git clone https://github.com/your-org/travel-story.git
cd travel-story
python -m venv venv
source venv/bin/activate
pip install -r requirements/development.txt

# 2. Environment
cp .env.example .env
# Edit .env with your settings

# 3. Database
createdb travel_story
python manage.py migrate
python manage.py createsuperuser

# 4. Seed Data (optional)
python manage.py seed_locations --cities barcelona,rom

# 5. Run
python manage.py runserver

# In separatem Terminal:
celery -A config worker -l info
```

### Production (Docker)

```bash
# 1. Environment
cp .env.example .env
# Edit .env with production settings

# 2. Build & Run
cd docker
docker-compose up -d

# 3. Initial Setup
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

---

## 📊 Datenmodell (Übersicht)

```
User
 │
 ├──► Trip ──► Stop ──► BaseLocation (shared)
 │     │                      │
 │     └──► Story ──► Chapter │
 │                            ▼
 └──► UserWorld          LocationLayer (shared)
       │
       ├──► Character
       ├──► PersonalPlace
       └──► LocationMemory
```

---

## 🔗 Externe Links

- [Django Dokumentation](https://docs.djangoproject.com/)
- [HTMX Dokumentation](https://htmx.org/docs/)
- [Anthropic API](https://docs.anthropic.com/)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [Celery Dokumentation](https://docs.celeryq.dev/)

---

## 📝 Changelog

### v1.0.0 (Januar 2025)
- Initial Release
- Django + HTMX Frontend
- PostgreSQL Location-Database
- Celery Story-Generierung
- Claude API Integration

---

*Stand: Januar 2025*
