# ADR-008: Use-Case-Analyse & Bibliotheksauswahl für CAD-Services

| Attribut | Wert |
|----------|------|
| **Status** | Accepted |
| **Datum** | 2026-02-02 |
| **Aktualisiert** | 2026-02-02 |
| **Autor** | IT-Architekt |
| **Deciders** | Architektur-Team |
| **Relates to** | [ADR-007](ADR-007-NO_JSON_COLUMNS.md), [ADR-009](ADR-009-IFC_DXF_PROCESSING.md) |

---

## Kontext

Das CAD-Hub-Modul (`packages/cad-services`) bedient zwei Kernzielgruppen:

1. **Architekten** – BIM-Analyse, Flächenberechnungen (DIN 277, WoFlV), Raumbücher
2. **Brandschutz-Sachverständige** – Feuerwiderstandsklassen, Fluchtweg-Analyse, Brandabschnitte

Für beide Zielgruppen müssen IFC- und DXF-Dateien verarbeitet, analysiert und exportiert werden.

## Entscheidung

### Bibliotheksauswahl

| Bereich | Bibliothek | Version | Lizenz | Begründung |
|---------|------------|---------|--------|------------|
| **IFC-Parsing** | ifcopenshell | ≥0.8.4 | LGPL-3.0 | IFC2X3/IFC4/IFC4.3 Support, aktive Community |
| **DXF-Parsing** | ezdxf | ≥1.4.3 | MIT | R12-R2018 Support, beste Python-Library |
| **Geometrie** | shapely | ≥2.0 | BSD | Polygon-Operationen, Flächenberechnung |
| **Graph-Algo** | networkx | ≥3.3 | BSD | Fluchtweg-Berechnung (Dijkstra) |
| **3D-Viewer** | xeokit-sdk | ≥2.x | AGPL/Comm | Enterprise-ready, BCF-Support, XKT-Format |
| **Export** | openpyxl, reportlab | aktuell | MIT | Excel/PDF-Generierung |

### Architektur-Entscheidung

**Monolith-first** mit Option auf Worker-Extraktion:

- Phase 1: Services im `cad-services` Package (Django + FastAPI)
- Phase 2+: Bei Bedarf Celery-Worker für Batch-Processing

---

## Use Cases

### Architekten (UC-A)

| ID | Use Case | Häufigkeit | Priorität | Status |
|----|----------|------------|-----------|--------|
| A-01 | Flächenberechnung nach DIN 277 | Täglich | Must | ✅ Implementiert |
| A-02 | Wohnflächenberechnung nach WoFlV | Wöchentlich | Must | 🔄 Geplant |
| A-03 | Raumbuch-Erstellung aus IFC | Täglich | Must | ✅ Implementiert |
| A-04 | Fenster-/Türlisten-Export | Wöchentlich | Should | ✅ Implementiert |
| A-05 | Umbauter Raum (BRI) Berechnung | Wöchentlich | Should | 🔄 Geplant |
| A-06 | Wandaufbau-Analyse | Monatlich | Could | ⏳ Backlog |
| A-07 | 3D-Visualisierung im Browser | Täglich | Must | 🔄 Geplant |

### Brandschutz-Sachverständige (UC-B)

| ID | Use Case | Häufigkeit | Priorität | Status |
|----|----------|------------|-----------|--------|
| B-01 | Feuerwiderstandsklassen-Prüfung (F30/F60/F90) | Täglich | Must | 🔄 Geplant |
| B-02 | Türen mit Brandschutzanforderungen extrahieren | Täglich | Must | ✅ Vorbereitet |
| B-03 | Fluchtweglängen berechnen | Wöchentlich | Must | 🔄 Geplant |
| B-04 | Brandabschnitte visualisieren | Wöchentlich | Should | ⏳ Backlog |
| B-05 | Rettungsweg-Plan generieren (DIN ISO 23601) | Monatlich | Should | ⏳ Backlog |
| B-06 | Nutzungseinheiten nach MBO prüfen | Wöchentlich | Should | ⏳ Backlog |

---

## Anforderungen

### Funktionale Anforderungen (Auszug)

#### DIN 277 Modul

```yaml
requirements:
  - id: REQ-A-001
    name: BGF-Berechnung
    description: Brutto-Grundfläche aus IFC IfcSpace extrahieren
    ifc_entities: [IfcSpace, IfcBuildingStorey]
    
  - id: REQ-A-002
    name: NRF-Klassifizierung
    description: Automatische Zuordnung zu NF1-NF6, TF, VF
    rules: [Raumname-basiert, PropertySet-basiert, Manuell]
```

#### Brandschutz-Modul

```yaml
requirements:
  - id: REQ-B-001
    name: Feuerwiderstand-Extraktion
    psets: [Pset_DoorCommon.FireRating, Pset_WallCommon.FireRating]
    classifications:
      din4102: [F30, F60, F90, F120]
      en13501: [REI30, REI60, REI90, REI120]
      
  - id: REQ-B-010
    name: Fluchtweglängen
    max_distances:
      standard: 35m
      with_sprinkler: 70m
```

### Nicht-funktionale Anforderungen

| NFR-ID | Anforderung | Zielwert |
|--------|-------------|----------|
| NFR-01 | IFC-Parsing Performance | < 5s für 50MB IFC |
| NFR-02 | Flächenberechnung Genauigkeit | ±0.5% vs. Revit/ArchiCAD |
| NFR-03 | 3D-Viewer Ladezeit | < 3s für 100k Elemente |
| NFR-04 | Multi-Tenant Isolation | 100% Datentrennung |

---

## Datenmodell

> Vollständiges Schema: siehe `packages/cad-services/sql/`

### Kern-Entitäten

```text
cadhub_project ──┬── cadhub_cad_model ──┬── cadhub_floor
                 │                      ├── cadhub_room
                 │                      ├── cadhub_wall
                 │                      ├── cadhub_door
                 │                      ├── cadhub_window
                 │                      └── cadhub_slab
                 │
                 └── cadhub_usage_category (Stammdaten DIN 277)
```

### Brandschutz-Erweiterung (Phase 2)

```text
bim_fire_compartment ──┬── bim_fire_rated_element
                       └── bim_escape_route
```

---

## Service-Architektur

### Implementierte Services

| Service | Datei | Beschreibung |
|---------|-------|--------------|
| `IFCService` | `services/ifc_service.py` | Extraktion: Floors, Rooms, Walls, Doors, Windows, Slabs |
| `DXFService` | `services/dxf_service.py` | Extraktion: Layers, Polylines→Rooms, Blocks, Texts |
| `DIN277Service` | `views/calculations.py` | Flächenberechnung nach DIN 277:2021 |

### Geplante Services (Phase 2)

| Service | Beschreibung |
|---------|--------------|
| `WoFlVService` | Wohnflächenberechnung mit Anrechnungsfaktoren |
| `FireSafetyService` | Feuerwiderstandsklassen-Prüfung |
| `EscapeRouteService` | Graph-basierte Fluchtweg-Berechnung |

---

## API-Endpoints

### Implementiert

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/upload/cad/{project_id}` | POST | IFC/DXF/DWG Upload |
| `/upload/process/{model_id}` | POST | Verarbeitung starten |
| `/api/v1/projects/` | CRUD | Projekt-Management |
| `/api/v1/rooms/` | CRUD | Raum-Management |

### Geplant

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/v1/analysis/din277` | POST | DIN 277 Berechnung |
| `/api/v1/analysis/fire-safety` | POST | Brandschutz-Analyse |
| `/api/v1/analysis/escape-routes` | POST | Fluchtweg-Berechnung |
| `/api/v1/export/{format}` | GET | Excel/PDF Export |

---

## Konsequenzen

### Positiv

- **ifcopenshell**: Vollständiger IFC4.3 Support, große Community
- **ezdxf**: MIT-Lizenz, exzellente Dokumentation
- **xeokit**: Enterprise-ready 3D-Viewer mit BCF-Support
- **Normalisiertes Datenmodell**: Konsistent mit ADR-007, effiziente Queries

### Negativ

- **ifcopenshell LGPL**: Copyleft-Lizenz erfordert Vorsicht bei Distribution
- **xeokit AGPL**: Kommerzielle Lizenz für SaaS erforderlich
- **Große IFC-Dateien**: Performance-Optimierung nötig (XKT-Konvertierung)

### Risiken

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| IFC-Parsing langsam bei >100MB | Mittel | Hoch | Async Worker, XKT-Cache |
| Brandschutz-Normen ändern sich | Niedrig | Mittel | Konfigurierbare Regeln |
| xeokit Lizenzkosten | Mittel | Mittel | Alternative: web-ifc evaluieren |

---

## Implementierungsplan

### Phase 1: Core (✅ Abgeschlossen)

- [x] `cad-services` Package erstellen
- [x] ifcopenshell + ezdxf Integration
- [x] IFCService & DXFService
- [x] Upload API (FastAPI)
- [x] Django Web-UI für Upload
- [x] DIN 277 Grundberechnung

### Phase 2: Brandschutz (🔄 In Arbeit)

- [ ] FireSafetyService
- [ ] Feuerwiderstandsklassen-Extraktion
- [ ] Fluchtweg-Algorithmus (networkx)
- [ ] Brandschutz-Report (PDF)

### Phase 3: Viewer & Export

- [ ] xeokit 3D-Viewer Integration
- [ ] XKT-Konvertierung Pipeline
- [ ] Excel/PDF Export Templates
- [ ] BCF-Import/Export

---

## Alternativen (Abgelehnt)

| Alternative | Grund für Ablehnung |
|-------------|---------------------|
| **Serverless (Lambda)** | ifcopenshell schwer zu deployen, Cold Start |
| **web-ifc only** | Weniger Features als ifcopenshell |
| **Microservice sofort** | Zu viel Overhead für Phase 1 |

---

## Referenzen

- **Implementation**: `packages/cad-services/src/cad_services/`
- **SQL Schema**: `packages/cad-services/sql/`
- **Tests**: `packages/cad-services/tests/`
- **ifcopenshell Docs**: https://blenderbim.org/docs-python/
- **ezdxf Docs**: https://ezdxf.readthedocs.io/
- **xeokit Docs**: https://xeokit.github.io/xeokit-sdk/

---

**Erstellt:** 2026-02-02  
**Letzte Änderung:** 2026-02-02  
**Review-Status:** Approved
