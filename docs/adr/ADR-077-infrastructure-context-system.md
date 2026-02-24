---
status: "accepted"
date: 2026-02-23
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
amends: ["ADR-020-documentation-strategy.md", "ADR-021-unified-deployment-pattern.md"]
related: ["ADR-050-platform-decomposition.md", "ADR-067-work-management-strategy.md", "ADR-075-deployment-execution-strategy.md"]
---

# Infrastructure Context System: catalog-info.yaml → dev-hub API → context.md

---

## Context and Problem Statement

Externe AI-Services (ChatGPT, Claude, JetBrains AI, etc.) haben keinen Zugriff auf
den aktuellen Infrastruktur-Zustand der Plattform. Ohne diesen Kontext liefern sie
ungenaue oder veraltete Antworten zu Deployment-Fragen, Service-Abhängigkeiten
und Architekturentscheidungen.

Drei Informationsquellen existieren bereits, sind aber nicht integriert:

1. **`catalog-info.yaml`** — Backstage-kompatible Metadaten pro Repo (manuell gepflegt)
2. **dev-hub Catalog DB** — normalisierte Django-Modelle (Domain, System, Component, API, Resource)
3. **`platform-context.md`** — statisches Markdown-Dokument (veraltet sobald geschrieben)

**Ziel**: Ein dreistufiges System das (a) `catalog-info.yaml` als Import-Format nutzt,
(b) die dev-hub DB als Single Source of Truth führt, und (c) einen API-Endpoint
bereitstellt der aktuellen Kontext als Markdown oder JSON liefert.

---

## Decision Drivers

- **Aktualität**: Kontext-Dokument soll immer den aktuellen DB-Stand widerspiegeln
- **Maschinenlesbarkeit**: JSON-Export für programmatische Nutzung
- **AI-Kompatibilität**: Markdown-Export als Attachment für ChatGPT, Claude, etc.
- **Einfachheit**: Kein separater Sync-Prozess — API generiert Dokument on-demand
- **Erweiterbarkeit**: Neue Services werden durch `catalog-info.yaml` Import automatisch erfasst

---

## Considered Options

### Option 1 — Dreistufiges System: catalog-info.yaml → DB → API (gewählt)

Import-Pipeline + Live-API-Endpoint in dev-hub.

**Pro:**
- DB ist immer aktuell (Single Source of Truth gemäß ADR-050)
- API liefert immer aktuellen Stand — kein veraltetes Dokument
- `catalog-info.yaml` als standardisiertes Import-Format (Backstage-kompatibel)
- Markdown + JSON aus einer Quelle

**Con:**
- Initiales Befüllen der DB erfordert `populate_catalog` Management Command
- `catalog-info.yaml` muss pro Repo gepflegt werden

---

### Option 2 — Statisches Markdown-Dokument (verworfen)

`platform-context.md` manuell pflegen.

**Con:** Veraltet sofort nach Änderungen, kein API-Zugriff, keine Maschinenlesbarkeit.

---

### Option 3 — GitHub API als Datenquelle (verworfen)

Direkt GitHub-Repos scannen und Kontext generieren.

**Con:** Rate-Limits, private Repos erfordern Token, keine strukturierten Metadaten.

---

## Decision Outcome

**Gewählt: Option 1** — Dreistufiges System implementiert in dev-hub.

### Architektur

```
┌─────────────────────────────────────────────────────┐
│  catalog-info.yaml (pro Repo)                        │
│  Backstage-kompatibles YAML — Import-Format          │
└──────────────────────┬──────────────────────────────┘
                       │ manage.py populate_catalog
                       ▼
┌─────────────────────────────────────────────────────┐
│  dev-hub Catalog DB (Single Source of Truth)         │
│  Domain, System, Component, API, Resource            │
│  15 Components, 12 Systems, 5 Domains, 12 Resources  │
└──────────────────────┬──────────────────────────────┘
                       │ on-demand
                       ▼
┌─────────────────────────────────────────────────────┐
│  GET /api/v1/context/                                │
│  ?format=json     → strukturiertes JSON              │
│  ?format=markdown → AI-Attachment Markdown           │
│  URL: https://devhub.iil.pet/api/v1/context/         │
└─────────────────────────────────────────────────────┘
```

### Implementierte Dateien

| Datei | Beschreibung |
|-------|-------------|
| `dev-hub/apps/catalog/context_export.py` | Service: DB → JSON/Markdown |
| `dev-hub/apps/catalog/api_views.py` | Django View: `PlatformContextView` |
| `dev-hub/apps/catalog/api_urls.py` | URL-Routing: `/api/v1/context/` |
| `dev-hub/config/urls.py` | Registrierung unter `/api/v1/` |
| `platform/docs/platform-context.md` | Statisches Fallback-Dokument |
| `platform/docs/templates/catalog-info-template.yaml` | Template für neue Repos |

### API-Nutzung

```bash
# Markdown für AI-Attachment (ChatGPT, Claude, etc.):
curl https://devhub.iil.pet/api/v1/context/?format=markdown

# JSON für programmatische Nutzung:
curl https://devhub.iil.pet/api/v1/context/
```

### catalog-info.yaml Schema (pro Repo)

```yaml
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: my-service
  description: "Kurzbeschreibung"
  annotations:
    github.com/project-slug: achimdehnert/my-service
spec:
  type: service
  lifecycle: production
  owner: achim-dehnert
  system: my-system
  providesApis: []
  dependsOn: []
```

### Positive Consequences

- Externer AI-Kontext immer aktuell — kein manuelles Dokument-Update
- Einheitliches Import-Format für alle Repos (Backstage-kompatibel)
- JSON-Export ermöglicht programmatische Weiterverarbeitung
- Kein Tenant-Filter nötig — globaler Plattform-Kontext

### Negative Consequences

- `catalog-info.yaml` muss pro Repo initial erstellt werden
- DB-Befüllung erfordert manuellen `populate_catalog` Aufruf nach Änderungen
- Kein automatischer Sync bei Repo-Änderungen (kein Webhook implementiert)

---

## Migration Tracking

| Phase | Inhalt | Status |
|-------|--------|--------|
| 1 | `context_export.py` + `api_views.py` + `api_urls.py` in dev-hub | ✅ done |
| 2 | Nginx-Config: `proxy_pass` auf `127.0.0.1:8085` korrigiert | ✅ done |
| 3 | `platform/docs/platform-context.md` als statisches Fallback | ✅ done |
| 4 | `catalog-info-template.yaml` in `platform/docs/templates/` | ✅ done |
| 5 | `catalog-info.yaml` in alle aktiven Repos eintragen | ✅ done (2026-02-24) |
| 6 | Webhook: auto-import bei Push auf main (GitHub Actions) | ✅ done (2026-02-24) |

---

## Deferred Decisions

| Entscheidung | Begründung | Zieldatum |
|--------------|------------|-----------|
| Automatischer Webhook-Import | Erfordert GitHub App oder PAT mit Repo-Zugriff | 2026-Q2 |
| Versionierung des Kontext-Dokuments | Snapshot-Archiv für historische Vergleiche | 2026-Q3 |
| Auth für `/api/v1/context/` | Aktuell öffentlich — API-Key wenn extern exponiert | 2026-Q2 |

---

## More Information

- dev-hub Catalog: `https://devhub.iil.pet/catalog/`
- Context API: `https://devhub.iil.pet/api/v1/context/`
- Template: `platform/docs/templates/catalog-info-template.yaml`
- ADR-050: Platform Decomposition — DB als Single Source of Truth
- ADR-065: ADR Numbering Filesystem-First — Grundlage für diese Nummer

---

## Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-02-23 | Achim Dehnert | Initial — Status: Accepted |
