# ADR-009: IFC/DXF Processing Architecture

| Attribut | Wert |
|----------|------|
| **Status** | Accepted |
| **Datum** | 2026-02-02 |
| **Aktualisiert** | 2026-02-02 |
| **Autor** | IT-Architekt |
| **Deciders** | Architektur-Team |
| **Relates to** | [ADR-007](ADR-007-NO_JSON_COLUMNS.md), [ADR-008](ADR-008-USE_CASE_ANALYSIS.md) |

---

## Kontext

CAD-Dateien (IFC, DXF) müssen zuverlässig hochgeladen, validiert, geparst und in das normalisierte Datenmodell überführt werden. Die Verarbeitung muss:

- Große Dateien (bis 500MB) unterstützen
- Multi-Tenant-sicher sein
- Fehler robust behandeln
- Fortschritt kommunizieren

## Entscheidung

### Processing Pipeline

```text
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Upload    │───▶│  Validate   │───▶│   Parse     │───▶│   Store     │
│  (FastAPI)  │    │  (Format)   │    │  (Service)  │    │  (Django)   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       │                  │                  │                  │
       ▼                  ▼                  ▼                  ▼
  cadhub_cad_model   status='pending'  status='processing'  status='ready'
```

### Architektur-Pattern

| Aspekt | Entscheidung | Begründung |
|--------|--------------|------------|
| **Upload** | Synchron (FastAPI) | Einfach, ausreichend für <100MB |
| **Parsing** | Synchron (Phase 1), Async (Phase 2+) | Schnelle Iteration vs. Skalierung |
| **Storage** | Filesystem + DB-Referenz | Kostengünstig, performant |
| **Fehler** | Status-Field + error_message | Transparenz für User |

---

## IFC Processing

### Unterstützte Versionen

| Version | Status | Entities |
|---------|--------|----------|
| IFC2X3 | ✅ Vollständig | Alle Standard-Entities |
| IFC4 | ✅ Vollständig | + IfcProject, IfcSite erweitert |
| IFC4.3 | ⚠️ Basis | Infrastructure-Entities fehlen |

### Extraktion-Pipeline

```python
# Pseudo-Code der IFC-Extraktion
def extract_from_ifc(file_path: Path) -> IFCParseResult:
    model = ifcopenshell.open(file_path)
    
    # 1. Etagen (IfcBuildingStorey)
    floors = extract_floors(model)
    
    # 2. Räume (IfcSpace) mit Zuordnung zu Etagen
    rooms = extract_rooms(model, floors)
    
    # 3. Bauteile mit PropertySets
    walls = extract_elements(model, "IfcWall", WALL_PSETS)
    doors = extract_elements(model, "IfcDoor", DOOR_PSETS)
    windows = extract_elements(model, "IfcWindow", WINDOW_PSETS)
    slabs = extract_elements(model, "IfcSlab", SLAB_PSETS)
    
    return IFCParseResult(floors, rooms, walls, doors, windows, slabs)
```

### PropertySet-Mapping

| IFC PropertySet | Extrahierte Felder |
|-----------------|-------------------|
| `Pset_SpaceCommon` | Area, Height, Volume |
| `Pset_WallCommon` | IsExternal, IsLoadBearing, FireRating |
| `Pset_DoorCommon` | FireRating, Width, Height |
| `Pset_WindowCommon` | Width, Height, ThermalTransmittance |
| `Qto_SpaceBaseQuantities` | GrossFloorArea, NetFloorArea |

### Quantity Extraction

```python
# Priorität: IfcQuantitySet > IfcPropertySet > Geometrie-Berechnung
def get_area(element) -> Decimal:
    # 1. Versuch: Quantity Set
    if qto := get_quantity_set(element, "Qto_SpaceBaseQuantities"):
        return qto.get("NetFloorArea")
    
    # 2. Versuch: Property Set
    if pset := get_property_set(element, "Pset_SpaceCommon"):
        return pset.get("Area")
    
    # 3. Fallback: Geometrie berechnen
    return calculate_area_from_geometry(element)
```

---

## DXF Processing

### Unterstützte Versionen

| Version | Status |
|---------|--------|
| R12 | ✅ Vollständig |
| R2000-R2018 | ✅ Vollständig |
| R2024+ | ⚠️ Experimentell |

### Raum-Erkennung aus DXF

```text
┌─────────────────────────────────────────────────────────────┐
│  DXF RAUM-ERKENNUNG                                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Layer-Filter                                            │
│     └─ Raum-Layer: "RAUM", "ROOM", "A-ROOM", "S-SPACE"     │
│                                                             │
│  2. Entity-Typen                                            │
│     ├─ LWPOLYLINE (geschlossen) → Raum-Polygon             │
│     ├─ POLYLINE (geschlossen) → Raum-Polygon               │
│     └─ HATCH → Raum-Füllung                                │
│                                                             │
│  3. Label-Zuordnung                                         │
│     └─ TEXT/MTEXT im Polygon → Raumnummer/Name             │
│                                                             │
│  4. Flächen-Berechnung                                      │
│     └─ Shapely Polygon.area (Surveyor's Formula)           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Layer-Konfiguration

```yaml
# config/dxf_layers.yaml
room_layers:
  patterns:
    - "RAUM*"
    - "ROOM*"
    - "A-ROOM*"
    - "S-SPACE*"
    - "*_ROOM"
    - "*_RAUM"
  
furniture_layers:
  patterns:
    - "MÖBEL*"
    - "FURNITURE*"
    - "A-FURN*"

wall_layers:
  patterns:
    - "WAND*"
    - "WALL*"
    - "A-WALL*"
```

---

## Datenbank-Schema

### CAD Model Status

```sql
CREATE TYPE cad_model_status AS ENUM (
    'pending',      -- Hochgeladen, wartet auf Verarbeitung
    'processing',   -- Wird gerade verarbeitet
    'ready',        -- Erfolgreich verarbeitet
    'error',        -- Verarbeitung fehlgeschlagen
    'archived'      -- Archiviert (nicht mehr aktiv)
);
```

### Kern-Tabellen

```sql
-- Bereits implementiert in sql/001_initial_schema.sql
CREATE TABLE cadhub_cad_model (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES cadhub_project(id),
    
    -- Datei-Info
    name VARCHAR(255) NOT NULL,
    source_file_path VARCHAR(500) NOT NULL,
    source_format VARCHAR(20) NOT NULL,  -- 'ifc', 'dxf', 'dwg'
    file_size_bytes BIGINT,
    
    -- IFC-spezifisch
    ifc_schema VARCHAR(20),  -- 'IFC2X3', 'IFC4', 'IFC4X3'
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending',
    error_message TEXT,
    processed_at TIMESTAMPTZ,
    
    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by_id INTEGER NOT NULL
);
```

---

## API-Endpoints

### Upload Endpoint

```
POST /upload/cad/{project_id}
Content-Type: multipart/form-data

Request:
  - file: Binary (IFC/DXF/DWG)

Response (201):
{
    "model_id": 42,
    "filename": "building.ifc",
    "format": "ifc",
    "size_bytes": 15728640,
    "status": "pending"
}
```

### Process Endpoint

```
POST /upload/process/{model_id}

Response (200):
{
    "status": "success",
    "model_id": 42,
    "format": "ifc",
    "schema": "IFC4",
    "floors": 5,
    "rooms": 127,
    "walls": 342,
    "doors": 89,
    "windows": 156,
    "slabs": 10,
    "total_area_m2": 4521.35
}
```

### Status Endpoint

```
GET /upload/status/{model_id}

Response (200):
{
    "model_id": 42,
    "status": "processing",
    "progress_percent": 65,
    "current_step": "Extracting rooms"
}
```

---

## Fehlerbehandlung

### Error Categories

| Code | Kategorie | Beispiel | Aktion |
|------|-----------|----------|--------|
| E001 | Format | Ungültiges IFC | Reject mit Hinweis |
| E002 | Parsing | Korrupte Geometrie | Partial Success + Warning |
| E003 | Version | IFC4.3 unsupported Entity | Skip + Warning |
| E004 | Size | Datei > 500MB | Reject mit Limit-Hinweis |
| E005 | Timeout | Processing > 10min | Retry als Background Job |

### Error Response

```json
{
    "status": "error",
    "model_id": 42,
    "error_code": "E002",
    "error_message": "Geometrie-Fehler in IfcWall #12345",
    "partial_result": {
        "floors": 5,
        "rooms": 120,
        "warnings": [
            "7 Räume ohne Flächenangabe",
            "3 Wände mit ungültiger Geometrie"
        ]
    }
}
```

---

## Performance

### Benchmarks (Zielwerte)

| Dateigröße | Parsing | DB-Insert | Total |
|------------|---------|-----------|-------|
| 10 MB | < 2s | < 1s | < 3s |
| 50 MB | < 5s | < 2s | < 7s |
| 100 MB | < 15s | < 5s | < 20s |
| 500 MB | < 60s | < 15s | < 90s |

### Optimierungen (Phase 2)

1. **Streaming Parse**: Große IFC-Dateien chunk-weise lesen
2. **Batch Insert**: Bulk-Insert statt Einzelinserts
3. **XKT Pre-Conversion**: 3D-Daten vorab konvertieren
4. **Async Processing**: Celery für Dateien > 50MB

---

## Sicherheit

### Validierung

```python
ALLOWED_EXTENSIONS = {'.ifc', '.ifczip', '.dxf', '.dwg'}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB

def validate_upload(file: UploadFile) -> None:
    # 1. Extension prüfen
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(f"Format nicht erlaubt: {ext}")
    
    # 2. Größe prüfen
    if file.size > MAX_FILE_SIZE:
        raise ValidationError(f"Datei zu groß: {file.size} bytes")
    
    # 3. Magic Bytes prüfen (gegen Extension-Spoofing)
    magic = file.file.read(8)
    file.file.seek(0)
    if not verify_magic_bytes(magic, ext):
        raise ValidationError("Dateiinhalt entspricht nicht Extension")
```

### Tenant-Isolation

```python
# Upload-Pfad mit Tenant-ID
upload_path = UPLOAD_DIR / str(tenant_id) / str(project_id) / filename

# RLS auf DB-Ebene
# Siehe sql/004_rls_policies.sql
```

---

## Implementierung

### Bereits implementiert ✅

- `services/ifc_service.py` - IFC Parsing mit ifcopenshell
- `services/dxf_service.py` - DXF Parsing mit ezdxf
- `api/routers/upload.py` - Upload & Process Endpoints
- `django/views/models.py` - Django Upload View

### Nächste Schritte 🔄

1. **Status-Endpoint** für Progress-Tracking
2. **Async Processing** für große Dateien
3. **XKT-Konvertierung** für 3D-Viewer
4. **Batch-Import** für mehrere Dateien

---

## Referenzen

- **IFC Schema**: https://standards.buildingsmart.org/IFC/
- **ifcopenshell API**: https://blenderbim.org/docs-python/ifcopenshell/
- **ezdxf Docs**: https://ezdxf.readthedocs.io/
- **Implementation**: `packages/cad-services/src/cad_services/services/`

---

**Erstellt:** 2026-02-02  
**Letzte Änderung:** 2026-02-02  
**Review-Status:** Approved
