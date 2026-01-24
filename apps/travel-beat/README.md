# 🌍 Travel Beat

**Personalisierte Reise-Geschichten, synchronisiert mit deiner Reise.**

Travel Beat erstellt einzigartige Stories, die an deinen Reisezielen spielen und sich mit deinem Reiseplan synchronisieren. Lies im Flug ein Kapitel, das genau dort spielt, wohin du fliegst.

## ✨ Features

- **Orts-Synchronisation** – Story spielt an deinen echten Reisezielen
- **Lesezeit-Kalkulation** – Kapitel angepasst an verfügbare Lesezeit
- **Genre-Auswahl** – Romance, Thriller, Mystery und mehr
- **Personalisierung** – Charaktere, die über mehrere Reisen leben
- **3-Schichten Location-System** – Effizientes Caching von Ortsinformationen

## 🚀 Quick Start

### Voraussetzungen

- Python 3.12+
- PostgreSQL 15+
- Redis 7+

### Installation

```bash
# Repository klonen
git clone https://github.com/yourusername/travel-beat.git
cd travel-beat

# Virtual Environment erstellen
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Dependencies installieren
pip install -r requirements/development.txt

# Environment konfigurieren
cp .env.example .env
# .env bearbeiten und Werte setzen

# Datenbank starten (Docker)
docker-compose -f docker/docker-compose.dev.yml up -d

# Migrationen
python manage.py migrate

# Superuser erstellen
python manage.py createsuperuser

# Server starten
python manage.py runserver
```

### Mit Docker

```bash
# Development
docker-compose -f docker/docker-compose.dev.yml up -d
python manage.py runserver

# Production
docker-compose -f docker/docker-compose.yml up -d
```

## 📁 Projekt-Struktur

```
travel-beat/
├── config/                 # Django Konfiguration
│   ├── settings/
│   │   ├── base.py        # Shared Settings
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   ├── celery.py
│   └── wsgi.py
├── apps/
│   ├── accounts/          # User Authentication
│   ├── trips/             # Reiseverwaltung
│   ├── locations/         # 3-Layer Location System
│   ├── stories/           # Story Generation & Reading
│   └── worlds/            # User Personalization
├── templates/             # Django Templates
├── static/                # Static Files
├── docker/                # Docker Configuration
├── requirements/          # Python Dependencies
└── manage.py
```

## 🏗️ Architektur

### 3-Layer Location System

```
Layer 1: BaseLocation (shared)
  └── Faktische Daten: Koordinaten, Sprache, Klima
  
Layer 2: LocationLayer (genre-specific)
  └── Genre-Overlay: Romance-Spots, Thriller-Locations
  
Layer 3: UserWorld (personal)
  └── Persönliche Orte, Ausschlüsse, Erinnerungen
```

### Apps

| App | Beschreibung |
|-----|-------------|
| `accounts` | User-Verwaltung, Subscription-Tiers |
| `trips` | Reisen, Stopps, Transportmittel |
| `locations` | Location-Datenbank, Genre-Layer |
| `stories` | Story-Generierung, Kapitel, Lesefortschritt |
| `worlds` | User-Universum, Charaktere, persönliche Orte |

## 🔧 Konfiguration

### Environment Variables

```env
# Django
DEBUG=True
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/travel_beat

# Redis / Celery
REDIS_URL=redis://localhost:6379/0

# Anthropic API
ANTHROPIC_API_KEY=sk-ant-xxx

# Feature Flags
FEATURE_PAYMENT_ENABLED=False
FEATURE_SOCIAL_AUTH=False
```

## 📖 API & Endpoints

| Endpoint | Beschreibung |
|----------|--------------|
| `/` | Landing Page |
| `/dashboard/` | User Dashboard |
| `/trips/` | Reisen verwalten |
| `/stories/` | Stories lesen |
| `/world/` | Personalisierung |
| `/admin/` | Django Admin |

## 🧪 Testing

```bash
# Tests ausführen
pytest

# Mit Coverage
pytest --cov=apps

# Nur bestimmte App
pytest apps/trips/
```

## 📝 License

MIT License - siehe [LICENSE](LICENSE)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request
