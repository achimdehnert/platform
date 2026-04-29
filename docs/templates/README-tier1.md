# <Repo-Name> — <1-Zeile Zweck>

[![Status](https://img.shields.io/badge/status-active-green)]()
[![Version](https://img.shields.io/badge/version-0.1.0-blue)]()
[![Python](https://img.shields.io/badge/python-3.12-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

> **<2-3 Sätze Kurzbeschreibung des Repos und seiner Hauptfunktion.>**

---

## 🧭 Schnellnavigation

| Ich möchte... | Dann lies... |
|---|---|
| ...das System verstehen | [docs/concepts/](docs/concepts/) |
| ...lokal starten | [Quickstart](#quickstart) |
| ...deployen | [docs/guides/deployment.md](docs/guides/deployment.md) |
| ...Architekturentscheidungen nachvollziehen | [docs/adr/](docs/adr/) |
| ...die API nutzen | [docs/reference/api.md](docs/reference/api.md) |
| ...Feedback geben | [Issues](../../issues) |

---

## 📦 Module / Apps

| Modul | URL-Prefix | Beschreibung |
|---|---|---|
| **<app_name>** | `/<prefix>/` | <Beschreibung> |

---

## 🛠️ Tech Stack

| Komponente | Technologie |
|---|---|
| **Backend** | Django 5.x · Gunicorn |
| **Frontend** | HTMX · Bootstrap 5 |
| **Database** | PostgreSQL 16 |
| **Queue** | Celery + Redis 7 |
| **Infrastructure** | Docker · Hetzner Cloud |

---

## 🚀 Quickstart (lokal) {#quickstart}

```bash
git clone https://github.com/achimdehnert/<repo>.git
cd <repo>
cp .env.example .env

docker compose up --build -d
docker compose exec <container> python manage.py migrate
docker compose exec <container> python manage.py createsuperuser
```

Zugriff: **http://localhost:<PORT>/dashboard/**

---

## 📚 Dokumentation

| Dokument | Inhalt |
|---|---|
| [docs/guides/deployment.md](docs/guides/deployment.md) | Docker · .env · Health-Checks · Rollback |
| [docs/guides/local-setup.md](docs/guides/local-setup.md) | Onboarding für neue Entwickler |
| [docs/reference/models.md](docs/reference/models.md) | Alle Models + Felder |
| [docs/reference/api.md](docs/reference/api.md) | API-Endpunkte |
| [docs/adr/](docs/adr/) | Architecture Decision Records |
| [docs/pdf/](docs/pdf/) | Generierte PDFs |
| [CHANGELOG.md](CHANGELOG.md) | Versionshistorie |

---

## 🤝 Mitwirken

Siehe [CONTRIBUTING.md](CONTRIBUTING.md).

---

## 📞 Kontakt

**Maintainer:** <Name> · <Email>
**Produktion:** https://<prod-url> · Port <PORT>
