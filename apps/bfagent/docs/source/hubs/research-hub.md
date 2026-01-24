# Research Hub

**Status:** ✅ Production  
**Domain:** `research`  
**URL:** `/research/`

---

## Übersicht

Der Research Hub ermöglicht Deep Research mit automatischer Quellenanalyse, Synthese und Berichterstellung.

## Features

- **Research Sessions:** Verwaltung von Recherche-Projekten
- **Multi-Source:** Web, Academic, Databases, PDFs
- **Synthese:** AI-gestützte Zusammenfassung
- **Explosionsschutz:** Spezialisierte ExSchutz-Recherche

## Models

### ResearchSession

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `title` | CharField | Session-Titel |
| `query` | TextField | Forschungsfrage |
| `depth` | ForeignKey | Research-Tiefe |
| `status` | CharField | Status |

### ResearchSource

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `session` | ForeignKey | Zugehörige Session |
| `url` | URLField | Quell-URL |
| `title` | CharField | Quell-Titel |
| `content` | TextField | Extrahierter Inhalt |
| `relevance_score` | FloatField | Relevanz (0-1) |

## Views & URLs

| URL | View | Beschreibung |
|-----|------|--------------|
| `/research/` | `dashboard` | Dashboard |
| `/research/sessions/` | `session_list` | Session-Liste |
| `/research/session/create/` | `session_create` | Neue Session |
| `/research/exschutz/` | `exschutz_dashboard` | ExSchutz |
