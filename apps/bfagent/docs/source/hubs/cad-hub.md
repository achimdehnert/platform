# CAD Hub

**Status:** ✅ Production  
**Domain:** `cad_hub`  
**URL:** `/cad-hub/`

---

## Übersicht

Der CAD Hub ermöglicht die Analyse von Bauplänen (IFC, DWG, DXF) und den Export in verschiedene Formate (GAEB, Raumbuch, WoFlV).

```{mermaid}
flowchart LR
    A[Upload] --> B[Parsing]
    B --> C[IFC/DWG/DXF]
    C --> D[Analyse]
    D --> E[Räume]
    D --> F[Elemente]
    E --> G[Export]
    F --> G
    G --> H[GAEB/PDF]
```

## Features

- **IFC-Analyse:** Vollständige IFC-Datei Analyse mit ifcopenshell
- **Raumerkennung:** Automatische Raum- und Flächenberechnung
- **Element-Extraktion:** Wände, Türen, Fenster, Decken
- **GAEB-Export:** X83/X84 Export für AVA-Software
- **WoFlV-Berechnung:** Wohnflächenverordnung konform
- **Brandschutz:** Brandschutzrelevante Analysen

## Schnellstart

### Projekt erstellen

```python
from apps.cad_hub.models import CADProject

project = CADProject.objects.create(
    name="Bürogebäude München",
    description="IFC-Analyse für Neubau"
)
```

### IFC-Datei hochladen

```python
from apps.cad_hub.models import IFCVersion

version = IFCVersion.objects.create(
    project=project,
    file=uploaded_file,
    version_number="1.0"
)
```

## Handler

| Handler | Typ | Beschreibung |
|---------|-----|--------------|
| `DXFParserHandler` | ⚙️ Rule | Parst DXF mit ezdxf |
| `IFCParserHandler` | ⚙️ Rule | Parst IFC mit ifcopenshell |
| `DimensionExtractorHandler` | 🔄 Hybrid | OCR für Maßketten |
| `ComplianceCheckerHandler` | ⚙️ Rule | DIN/ISO Prüfung |
| `ReportGeneratorHandler` | 🔧 Utility | PDF/DOCX Report |

## Models

### CADProject

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `name` | CharField | Projektname |
| `description` | TextField | Beschreibung |
| `created_at` | DateTimeField | Erstellungsdatum |

### IFCVersion

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `project` | ForeignKey | Zugehöriges Projekt |
| `file` | FileField | IFC-Datei |
| `version_number` | CharField | Versionsnummer |
| `parsed_data` | JSONField | Geparste Daten |

### Room

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `ifc_version` | ForeignKey | Zugehörige IFC-Version |
| `name` | CharField | Raumname |
| `number` | CharField | Raumnummer |
| `area` | DecimalField | Fläche in m² |
| `height` | DecimalField | Raumhöhe |

## Views & URLs

| URL | View | Beschreibung |
|-----|------|--------------|
| `/cad-hub/` | `dashboard` | Dashboard |
| `/cad-hub/projects/` | `project_list` | Projektliste |
| `/cad-hub/project/<id>/` | `project_detail` | Projektdetails |
| `/cad-hub/model/<id>/` | `model_detail` | IFC-Modell Details |
| `/cad-hub/model/<id>/rooms/` | `room_list` | Raumliste |
| `/cad-hub/model/<id>/export/gaeb/` | `export_gaeb` | GAEB Export |

## Export-Formate

### GAEB X84

```python
from apps.cad_hub.views import ExportGAEBView

# Export als XML
response = ExportGAEBView.as_view()(request, model_id=1, format='xml')

# Export als Excel
response = ExportGAEBView.as_view()(request, model_id=1, format='excel')
```

### Raumbuch PDF

```python
from apps.cad_hub.services import RaumbuchExporter

exporter = RaumbuchExporter(ifc_version)
pdf = exporter.generate_pdf()
```
