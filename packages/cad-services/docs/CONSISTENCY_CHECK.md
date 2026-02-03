# CAD-Hub Konsistenz-Prüfung

**Datum:** 2026-02-02  
**Status:** ✅ Geprüft und erweitert

## 1. Models - Vollständigkeit

| Model | Tabelle | Status | Fehlende Attribute |
|-------|---------|--------|-------------------|
| Project | cadhub_project | ✅ | - |
| CADModel | cadhub_cad_model | ✅ | - |
| Floor | cadhub_floor | ✅ | - |
| Room | cadhub_room | ✅ | - |
| Window | cadhub_window | ✅ | - |
| Door | cadhub_door | ✅ | - |
| Wall | cadhub_wall | ✅ | - |
| FireRatedElement | cadhub_fire_rated_element | ✅ | - |
| FireCompartment | cadhub_fire_compartment | ✅ | - |
| EscapeRoute | cadhub_escape_route | ✅ | - |

## 2. Views - Vollständigkeit

| View | URL-Name | Template | Status |
|------|----------|----------|--------|
| DashboardView | dashboard | dashboard.html | ✅ |
| ProjectListView | project-list | projects/list.html | ✅ |
| ProjectDetailView | project-detail | projects/detail.html | ✅ |
| ProjectCreateView | project-create | projects/create.html | ✅ |
| ProjectEditView | project-edit | projects/edit.html | ✅ |
| ModelListView | model-list | models/list.html | ⚠️ Fehlt |
| ModelDetailView | model-detail | models/detail.html | ✅ |
| ModelUploadView | model-upload | models/upload.html | ✅ |
| RoomListView | room-list | rooms/list.html | ✅ |
| DIN277View | din277 | calculations/din277.html | ✅ |
| FireSafetyDashboardView | fire-safety | fire_safety/dashboard.html | ✅ |
| **model_viewer_3d** | model-viewer-3d | viewer/model_viewer_3d.html | ✅ NEU |
| floorplan_viewer | floorplan-viewer | viewer/floorplan_viewer.html | ✅ |

## 3. URLs - Vollständigkeit

### Core URLs ✅
- `/` - Dashboard
- `/projects/` - Projektliste
- `/projects/<id>/` - Projektdetail
- `/projects/<id>/models/` - Modellliste
- `/models/<id>/` - Modelldetail

### Viewer URLs ✅
- `/viewer/<model_id>/` - 2D Floorplan Viewer
- `/viewer/<model_id>/svg/` - SVG Generierung
- `/viewer3d/<model_id>/` - **NEU** 3D xeokit Viewer

### API URLs ✅
- `/api/fire-safety/<model_id>/` - Brandschutz Stats
- `/api/viewer3d/<model_id>/structure/` - **NEU** Modellstruktur
- `/api/viewer3d/<model_id>/properties/` - **NEU** Element Properties
- `/api/viewer3d/<model_id>/viewpoints/` - **NEU** BCF Viewpoints

### Export URLs ✅ NEU
- `/export/<model_id>/raumbuch/` - Excel Raumbuch
- `/export/<model_id>/din277/` - Excel DIN 277
- `/export/<model_id>/fire-safety/` - Excel Brandschutz

## 4. Services - Vollständigkeit

| Service | Datei | Status |
|---------|-------|--------|
| FloorplanSVGService | floorplan_svg_service.py | ✅ |
| FireSafetyService | fire_safety_service.py | ✅ |
| EscapeRouteService | escape_route_service.py | ✅ |
| PDFReportService | pdf_report_service.py | ✅ NEU |
| ExcelExportService | excel_export_service.py | ✅ NEU |
| XKTConverterService | xkt_converter_service.py | ✅ NEU |

## 5. Templates - Konsistenz

### Base Template
- `cadhub/base.html` - ✅ Vorhanden

### Block-Struktur
Alle Templates nutzen:
- `{% block title %}` ✅
- `{% block content %}` ✅
- `{% block extra_css %}` ✅
- `{% block extra_js %}` ✅

### Fehlende Templates
- `cadhub/models/list.html` - ⚠️ Sollte erstellt werden
- `cadhub/projects/partials/project_list.html` - ⚠️ HTMX Partial

## 6. JavaScript - Vollständigkeit

| Datei | Beschreibung | Status |
|-------|--------------|--------|
| xeokit-viewer.js | CADHubViewer Controller | ✅ NEU |
| xeokit-sdk.min.js | xeokit SDK (CDN) | ✅ CDN |

### xeokit Use Cases implementiert:
- ✅ Modell laden (XKT Format)
- ✅ Navigation (Orbit, Pan, Zoom)
- ✅ Objekt-Selektion
- ✅ Schnittebenen (Section Planes)
- ✅ Messung (Distance)
- ✅ Isolieren/Ausblenden
- ✅ BCF Viewpoints
- ✅ Predefined Views (Front, Top, Iso etc.)
- ✅ Model Structure Tree

## 7. Lint-Fehler (bekannt, nicht kritisch)

### HTML Accessibility
- Buttons ohne discernible text (Icon-only buttons)
- Select ohne accessible name
- **Lösung:** `aria-label` oder `title` hinzufügen

### CSS
- Inline styles in Templates
- **Lösung:** In separate CSS-Datei auslagern

## 8. Empfohlene nächste Schritte

1. **Models List Template** erstellen
2. **Accessibility fixes** für Buttons/Links
3. **CSS auslagern** aus Templates
4. **XKT Dateien** für Test-Modelle generieren
5. **Tests** für neue Services schreiben

## 9. Dependencies

### Python (pyproject.toml)
```toml
[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-cov>=4.0", "ruff>=0.1"]
report = ["reportlab>=4.0", "openpyxl>=3.1"]
```

### JavaScript (CDN)
- xeokit-sdk: `@xeokit/xeokit-sdk`
- Bootstrap Icons: bereits in base.html

### External Tools
- `xeokit-convert`: `npm i -g @xeokit/xeokit-convert`
- `ifc2gltf`: IfcOpenShell
