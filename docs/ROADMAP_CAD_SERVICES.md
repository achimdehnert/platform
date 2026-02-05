# CAD-Services Implementierungs-Roadmap

**Letzte Aktualisierung:** 2026-02-02  
**Verantwortlich:** Architektur-Team  
**Repository:** `platform/packages/cad-services`

---

## Übersicht

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CAD-SERVICES ROADMAP                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Q1/2026                    Q2/2026                    Q3/2026              │
│  ────────                   ────────                   ────────              │
│                                                                              │
│  ┌─────────────┐           ┌─────────────┐           ┌─────────────┐       │
│  │ Phase 1     │           │ Phase 2     │           │ Phase 3     │       │
│  │ ═══════════ │           │ ═══════════ │           │ ═══════════ │       │
│  │ ✅ Core     │──────────▶│ ✅ Brandsch.│──────────▶│ ⏳ 3D-View  │       │
│  │ ✅ IFC/DXF  │           │ ✅ Fluchtw. │           │ ⏳ Export   │       │
│  │ ✅ Upload   │           │ ✅ 2D-Viewer│           │ ⏳ BCF      │       │
│  │ ✅ DIN 277  │           │ ⏳ Reports  │           │ ⏳ Collab   │       │
│  └─────────────┘           └─────────────┘           └─────────────┘       │
│                                                                              │
│  Legende: ✅ Done  🔄 In Progress  ⏳ Planned  ❌ Delayed                    │
│                                                                              │
│  HINWEIS: 3D-Viewer (xeokit) verschoben auf Phase 3                         │
│           2D-Viewer (SVG/iframe) in Phase 2 implementiert                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Core Infrastructure (✅ Abgeschlossen)

**Zeitraum:** KW 1-4 / 2026  
**Status:** Abgeschlossen

### Deliverables

| Item | Status | Datei/Location |
|------|--------|----------------|
| Package-Struktur | ✅ | `packages/cad-services/` |
| Django Models | ✅ | `django/models/cadhub.py` |
| SQL Schema | ✅ | `sql/001_initial_schema.sql` |
| RLS Policies | ✅ | `sql/004_rls_policies.sql` |
| IFC Service | ✅ | `services/ifc_service.py` |
| DXF Service | ✅ | `services/dxf_service.py` |
| Upload API | ✅ | `api/routers/upload.py` |
| Django Views | ✅ | `django/views/` |
| Templates | ✅ | `django/templates/cadhub/` |

### Metriken

- **Lines of Code:** ~3.500
- **Test Coverage:** ~45%
- **API Endpoints:** 8

---

## Phase 2: Brandschutz-Modul & 2D-Viewer (✅ Abgeschlossen)

**Zeitraum:** KW 5-8 / 2026  
**Status:** Abgeschlossen

### Sprint 5 (KW 5-6): Fire Safety Service

| Task | Priorität | Status | Assignee |
|------|-----------|--------|----------|
| `FireSafetyService` Grundgerüst | Must | ✅ | - |
| Feuerwiderstandsklassen aus IFC | Must | ✅ | - |
| DB-Tabellen `cadhub_fire_*` | Must | ✅ | - |
| Unit Tests | Must | ✅ | - |

### Sprint 6 (KW 7-8): Fluchtweg-Analyse & 2D-Viewer

| Task | Priorität | Status | Assignee |
|------|-----------|--------|----------|
| `EscapeRouteService` mit networkx | Must | ✅ | - |
| Graph-Modell Raum → Tür → Raum | Must | ✅ | - |
| Dijkstra Shortest Path | Must | ✅ | - |
| **2D-Viewer (SVG/iframe)** | Must | ✅ | - |
| `FloorplanSVGService` | Must | ✅ | - |
| Visualisierung Fluchtwege | Should | ⏳ | - |
| PDF-Report Brandschutz | Should | ✅ | - |

### Deliverables Phase 2

```text
services/
├── fire_safety_service.py      # ✅ Feuerwiderstandsklassen
├── escape_route_service.py     # ✅ Fluchtweg-Berechnung (networkx)
├── floorplan_svg_service.py    # ✅ 2D SVG-Generierung
└── woflv_service.py            # ⏳ Wohnflächenberechnung

sql/
└── 006_fire_safety_tables.sql  # ✅ Brandschutz-Tabellen

django/views/
└── viewer.py                   # ✅ 2D-Viewer Views

templates/cadhub/
├── viewer/
│   └── floorplan_viewer.html   # ✅ 2D-Viewer mit iframe
└── reports/
    ├── fire_safety_report.html # ⏳ Geplant
    └── escape_route_plan.html  # ⏳ Geplant
```

### Hinweis: 3D-Viewer Entscheidung

Der ursprünglich für Phase 2 geplante **3D-Viewer (xeokit)** wurde auf **Phase 3** verschoben.
Stattdessen wurde ein **2D-Viewer mit SVG und iframe** implementiert (analog zu expert-hub).

**Begründung:**
- Schnellere Implementierung
- Geringere Lizenzkosten
- Bessere Browser-Kompatibilität
- Ausreichend für initiale Use Cases (Grundriss-Ansicht, Brandschutz-Visualisierung)

---

## Phase 3: 3D-Viewer & Export (⏳ Geplant)

**Zeitraum:** KW 9-14 / 2026  
**Status:** Geplant

### Sprint 7-8 (KW 9-10): xeokit Integration

| Task | Priorität | Status |
|------|-----------|--------|
| xeokit-sdk einbinden | Must | ⏳ |
| XKT Converter Service | Must | ⏳ |
| Basis-Viewer Template | Must | ⏳ |
| Property Panel | Should | ⏳ |
| Tree View | Should | ⏳ |

### Sprint 9-10 (KW 11-12): Viewer Features

| Task | Priorität | Status |
|------|-----------|--------|
| Section Planes | Must | ⏳ |
| Distance Measurement | Should | ⏳ |
| BCF Viewpoints | Should | ⏳ |
| Navigation Cube | Must | ⏳ |

### Sprint 11-12 (KW 13-14): Export & Polish

| Task | Priorität | Status |
|------|-----------|--------|
| Excel Export Templates | Must | ⏳ |
| PDF Report Generator | Must | ⏳ |
| Raumbuch-Export | Must | ⏳ |
| Elementlisten-Export | Should | ⏳ |

### Deliverables Phase 3

```text
services/
├── xkt_converter.py          # NEU: IFC → XKT Konvertierung
└── export_service.py         # NEU: Excel/PDF Export

static/
└── js/
    ├── xeokit-sdk.min.js     # NEU: xeokit Library
    └── viewer-controller.js   # NEU: Viewer Logic

templates/
└── cadhub/viewer/
    └── model_viewer.html      # NEU: 3D-Viewer
```

---

## Phase 4: Enterprise Features (⏳ Backlog)

**Zeitraum:** Q3/2026  
**Status:** Backlog

### Geplante Features

| Feature | Beschreibung | Priorität |
|---------|--------------|-----------|
| Async Processing | Celery für große Dateien | Should |
| Batch Import | Mehrere Dateien gleichzeitig | Could |
| Version History | Modell-Versionen vergleichen | Could |
| BCF Server | Issue-Tracking Integration | Could |
| Multi-User Viewer | Echtzeit-Kollaboration | Could |
| API Rate Limiting | Schutz vor Missbrauch | Should |

---

## Technische Schulden

| ID | Beschreibung | Priorität | Aufwand |
|----|--------------|-----------|---------|
| TD-01 | Test Coverage auf 80% erhöhen | Hoch | 2 Tage |
| TD-02 | Error Handling vereinheitlichen | Mittel | 1 Tag |
| TD-03 | API Documentation (OpenAPI) | Mittel | 1 Tag |
| TD-04 | Performance Benchmarks | Mittel | 1 Tag |
| TD-05 | Accessibility in Templates | Niedrig | 2 Tage |

---

## Dependencies

### Externe Bibliotheken

| Bibliothek | Version | Lizenz | Status |
|------------|---------|--------|--------|
| ifcopenshell | 0.8.4 | LGPL-3.0 | ✅ Installiert |
| ezdxf | 1.4.3 | MIT | ✅ Installiert |
| shapely | 2.0+ | BSD | ✅ Installiert |
| networkx | 3.3+ | BSD | ⏳ Zu installieren |
| xeokit-sdk | 2.x | AGPL/Comm | ⏳ Phase 3 |
| openpyxl | 3.1+ | MIT | ✅ Installiert |
| reportlab | 4.2+ | BSD | ⏳ Zu installieren |

### Interne Dependencies

| Package | Beschreibung | Status |
|---------|--------------|--------|
| bfagent-core | Tenant, Auth, RBAC | ✅ Integriert |
| shared-utils | Logging, Config | ✅ Integriert |

---

## Risiken & Mitigationen

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| xeokit Lizenzkosten | Mittel | Mittel | web-ifc Fallback evaluieren |
| Performance >100MB | Mittel | Hoch | Async Worker, Streaming |
| IFC4.3 Inkompatibilität | Niedrig | Mittel | Fallback auf IFC4 |
| Browser-Kompatibilität | Niedrig | Mittel | WebGL 2.0 Polyfill |

---

## Erfolgskriterien

### Phase 2 Abnahmekriterien

- [ ] Feuerwiderstandsklassen aus IFC extrahierbar
- [ ] Fluchtweg-Berechnung für alle Räume
- [ ] PDF-Report mit Brandschutz-Prüfung
- [ ] Test Coverage ≥ 60%

### Phase 3 Abnahmekriterien

- [ ] 3D-Viewer lädt Modelle < 3s
- [ ] Section Planes funktional
- [ ] Excel-Export für Raumbuch
- [ ] BCF Viewpoint Import/Export

---

## Kontakt

| Rolle | Name | Verantwortung |
|-------|------|---------------|
| Tech Lead | TBD | Architektur, Code Review |
| Backend Dev | TBD | Services, API |
| Frontend Dev | TBD | Viewer, Templates |
| QA | TBD | Testing, Dokumentation |

---

## Changelog

| Datum | Version | Änderung |
|-------|---------|----------|
| 2026-02-02 | 1.0 | Initiale Roadmap |

---

## Referenzen

- [ADR-008: Use-Case-Analyse](adr/ADR-008-USE_CASE_ANALYSIS.md)
- [ADR-009: IFC/DXF Processing](adr/ADR-009-IFC_DXF_PROCESSING.md)
- [ADR-010: 3D-Viewer Strategie](adr/ADR-010-3D_VIEWER_STRATEGY.md)
