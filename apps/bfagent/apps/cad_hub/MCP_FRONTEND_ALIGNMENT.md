# MCP Backend ↔ CAD Hub Frontend Alignment Analysis

**Datum:** 11. Dezember 2025  
**MCP Backend:** `c:\Users\achim\github\mcp-hub\cad_mcp\`  
**Frontend:** `C:\Users\achim\github\bfagent\apps\cad_hub\`

---

## 📊 MCP Backend - Verfügbare Funktionalitäten

### 🔵 MCP Tools (aus tools.py)

#### 1. DIN 277 Tools
| Tool | Funktion | Status |
|------|----------|--------|
| `calculate_din277` | Flächenberechnung nach DIN 277:2021 (BGF, NRF, NF1-7, VF, TF, KGF, BRI) | ✅ Implementiert |
| `classify_room_din277` | Raum-Klassifizierung nach DIN 277 (NF1-7, VF, TF) | ✅ Implementiert |

**Output:** BGF, NRF, NF1-NF7, VF, TF, KGF, BRI, Klassifizierungen mit Confidence

#### 2. WoFlV Tools (Wohnflächenverordnung)
| Tool | Funktion | Status |
|------|----------|--------|
| `calculate_woflv` | Wohnflächenberechnung nach WoFlV mit Anrechnungsfaktoren | ✅ Implementiert |
| `get_woflv_factor` | Anrechnungsfaktor für Raum ermitteln (Höhe, Raumtyp) | ✅ Implementiert |

**Output:** Wohnfläche, Anrechnungsfaktoren, Raum-Details

#### 3. Raumbuch Tools
| Tool | Funktion | Status |
|------|----------|--------|
| `generate_raumbuch` | Professionelles Raumbuch-Dokument (DOCX/HTML) generieren | ✅ Implementiert |

**Output:** DOCX/HTML Raumbuch mit DIN 277 + WoFlV Berechnungen, Geschoss-Zusammenfassungen

#### 4. GAEB Tools (Leistungsverzeichnis)
| Tool | Funktion | Status |
|------|----------|--------|
| `generate_gaeb_lv` | GAEB X84 Leistungsverzeichnis generieren | ✅ Implementiert |
| `create_lv_from_zones` | LV-Positionen aus CAD-Zonen (Massenermittlung) | ✅ Implementiert |

**Output:** GAEB X84 Files, Excel, Positionen, Mengen, Preise, Summen

#### 5. PDF/Plan Parser Tools
| Tool | Funktion | Status |
|------|----------|--------|
| `parse_plan_image` | Bauplan-Bild mit Vision AI parsen (Räume, Türen, Fenster) | ✅ Implementiert |
| `export_rooms_to_ifc` | Räume nach IFC exportieren | ✅ Implementiert |

**Output:** Extrahierte Räume, Türen, Fenster mit Koordinaten, IFC Export

---

### 🔵 Handler Manifest (aus handlers_manifest.py)

#### INPUT Handlers
| Handler | Beschreibung | External Dependencies |
|---------|--------------|----------------------|
| `dwg_parser` | DWG/DXF Parser - Geometrie, Räume, Türen, Fenster, Wände | ODA File Converter |
| `ifc_parser` | IFC/BIM Parser - Spaces, Building Elements, Properties (IFC2X3, IFC4) | IfcOpenShell |
| `pdf_parser` | PDF Plan Parser - OCR, Computer Vision für gescannte Pläne | OpenCV, Tesseract OCR |

#### PROCESSING Handlers
| Handler | Beschreibung | External Dependencies |
|---------|--------------|----------------------|
| `din277_calculator` | DIN 277:2021 Calculator - BGF, NRF, NF1-7, VF, TF, KGF, BRI | - |
| `woflv_calculator` | WoFlV Calculator - Wohnfläche mit Balkon-Faktoren | - |

#### OUTPUT Handlers
| Handler | Beschreibung | External Dependencies |
|---------|--------------|----------------------|
| `raumbuch_generator` | Excel Raumbuch Generator - Räume, Flächen, Ausstattung | - |
| `gaeb_generator` | GAEB X84 Generator - Leistungsverzeichnis für Ausschreibungen | - |
| `ifc_exporter` | IFC Exporter - IFC2X3/IFC4 für BIM Interoperabilität | IfcOpenShell |

#### INTEGRATION Handlers
| Handler | Beschreibung | External Dependencies |
|---------|--------------|----------------------|
| `archicad_api` | ArchiCAD API - Bidirektionale Datenübertragung (Port 19723) | ArchiCAD + JSON API |

#### TRANSFORM Handlers
| Handler | Beschreibung | External Dependencies |
|---------|--------------|----------------------|
| `dwg_converter` | DWG zu DXF Converter | ODA File Converter |

---

## 🎯 Frontend (CAD Hub) - Aktueller Stand

### ✅ Implementierte Features
| Feature | Status | Details |
|---------|--------|---------|
| Dashboard | ✅ OK | Projekt-/Modell-/Raum-Übersicht |
| Projekt-Management | ✅ OK | List, Detail, Create |
| Modell-Upload | ✅ OK | IFC Upload |
| Raum-Liste | ✅ OK | Mit Filterung + HTMX |
| DIN 277 Flächenübersicht | ✅ OK | Nutzt IFC MCP API |
| WoFlV Wohnflächenberechnung | ✅ OK | Nutzt IFC MCP API |
| Raumbuch Export | ✅ OK | Excel Export |
| GAEB Export | ✅ OK | GAEB LV Export |

### ⚠️ Teilweise Implementiert
| Feature | Status | Fehlend |
|---------|--------|---------|
| Floor (Geschoss) | ⚠️ Teilweise | Keine UI (nur Model + Admin) |
| Window (Fenster) | ❌ Fehlt komplett | Kein Model/View/Template |

---

## 🔴 Lücken-Analyse: MCP Backend ↔ Frontend

### 1️⃣ **KRITISCHE LÜCKEN**

#### A. Fenster (Windows)
**MCP Backend:**
- ✅ `parse_plan_image` Tool extrahiert Fenster
- ✅ DWG Parser extrahiert Fenster
- ✅ IFC Parser extrahiert Fenster

**Frontend CAD Hub:**
- ❌ **Kein Window Model**
- ❌ **Keine WindowListView**
- ❌ **Keine Templates**
- ❌ **Keine Window-Tabelle in DB**

**Impact:** HOCH - MCP liefert Fenster-Daten, aber Frontend kann sie nicht anzeigen/speichern

#### B. Türen (Doors)
**MCP Backend:**
- ✅ `parse_plan_image` Tool extrahiert Türen
- ✅ DWG Parser extrahiert Türen
- ✅ IFC Parser extrahiert Türen

**Frontend CAD Hub:**
- ❌ **Kein Door Model**
- ❌ **Keine DoorListView**
- ❌ **Keine Templates**
- ❌ **Keine Door-Tabelle in DB**

**Impact:** HOCH - MCP liefert Tür-Daten, aber Frontend kann sie nicht anzeigen/speichern

#### C. Wände (Walls)
**MCP Backend:**
- ✅ DWG Parser extrahiert Wände
- ✅ IFC Parser extrahiert Wände

**Frontend CAD Hub:**
- ❌ **Kein Wall Model**
- ❌ **Keine Wall-Ansicht**

**Impact:** MITTEL - Für Konstruktionsanalyse relevant

---

### 2️⃣ **WICHTIGE LÜCKEN**

#### D. DWG/DXF Import
**MCP Backend:**
- ✅ `dwg_parser` Handler
- ✅ `dwg_converter` Handler (DWG → DXF)

**Frontend CAD Hub:**
- ❌ **Kein DWG/DXF Upload**
- ✅ Nur IFC Upload implementiert

**Impact:** HOCH - Viele Architekten arbeiten mit AutoCAD (DWG/DXF)

#### E. PDF Plan Parser
**MCP Backend:**
- ✅ `parse_plan_image` Tool
- ✅ Vision AI für gescannte Pläne

**Frontend CAD Hub:**
- ❌ **Kein PDF Upload**
- ❌ **Keine OCR-Ansicht**

**Impact:** MITTEL - Für Legacy-Pläne wichtig

#### F. ArchiCAD Integration
**MCP Backend:**
- ✅ `archicad_api` Handler
- ✅ Bidirektionale Synchronisation

**Frontend CAD Hub:**
- ❌ **Keine ArchiCAD Verbindung**
- ❌ **Kein Sync-UI**

**Impact:** MITTEL - Für ArchiCAD-Nutzer wichtig

---

### 3️⃣ **KLEINERE LÜCKEN**

#### G. Geschoss-UI (Floor)
**MCP Backend:**
- ✅ Floor-Daten in IFC
- ✅ Floor-Zuordnung in Räumen

**Frontend CAD Hub:**
- ✅ Floor Model existiert
- ❌ **Keine FloorListView**
- ❌ **Keine Floor-Templates**

**Impact:** NIEDRIG - Floor-Daten werden über Räume angezeigt

#### H. Raum-Klassifizierung
**MCP Backend:**
- ✅ `classify_room_din277` Tool
- ✅ Automatische Klassifizierung mit Confidence

**Frontend CAD Hub:**
- ⚠️ **Teilweise:** DIN 277 wird berechnet, aber nicht pro Raum angezeigt
- ❌ **Keine Confidence-Anzeige**

**Impact:** NIEDRIG - Funktioniert, könnte verbessert werden

---

## 🛠️ Benötigte Komponenten für vollständige Integration

### Phase 1: Kritische Features (Fenster + Türen)

#### 1. Database Models
```python
# apps/cad_hub/models.py

class Window(models.Model):
    """Fenster (IfcWindow)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    ifc_model = models.ForeignKey(IFCModel, on_delete=models.CASCADE, related_name='windows')
    floor = models.ForeignKey(Floor, on_delete=models.SET_NULL, null=True, blank=True)
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True)
    
    ifc_guid = models.CharField(max_length=36)
    number = models.CharField(max_length=50, blank=True)
    name = models.CharField(max_length=100, blank=True)
    
    # Geometrie
    width = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    height = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    area = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    
    # Position
    wall_position = models.CharField(max_length=50, blank=True)  # North, South, East, West
    elevation = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    
    # Eigenschaften
    material = models.CharField(max_length=100, blank=True)
    glazing_type = models.CharField(max_length=100, blank=True)
    u_value = models.DecimalField(max_digits=5, decimal_places=2, null=True)  # Wärmedurchgangskoeffizient
    
    class Meta:
        db_table = 'cad_hub_window'
        ordering = ['floor', 'number']

class Door(models.Model):
    """Tür (IfcDoor)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    ifc_model = models.ForeignKey(IFCModel, on_delete=models.CASCADE, related_name='doors')
    floor = models.ForeignKey(Floor, on_delete=models.SET_NULL, null=True, blank=True)
    from_room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, related_name='doors_from')
    to_room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, related_name='doors_to')
    
    ifc_guid = models.CharField(max_length=36)
    number = models.CharField(max_length=50, blank=True)
    name = models.CharField(max_length=100, blank=True)
    
    # Geometrie
    width = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    height = models.DecimalField(max_digits=10, decimal_places=3, null=True)
    
    # Eigenschaften
    door_type = models.CharField(max_length=50, blank=True)  # Single, Double, Sliding
    material = models.CharField(max_length=100, blank=True)
    fire_rating = models.CharField(max_length=20, blank=True)  # T30, T60, T90
    
    class Meta:
        db_table = 'cad_hub_door'
        ordering = ['floor', 'number']
```

#### 2. Views
```python
# apps/cad_hub/views.py

class WindowListView(HtmxMixin, ListView):
    """Fensterliste mit Filterung"""
    model = Window
    template_name = 'cad_hub/window_list.html'
    partial_template_name = 'cad_hub/partials/_window_table.html'
    context_object_name = 'windows'
    paginate_by = 50
    
    def get_queryset(self):
        model_id = self.kwargs['model_id']
        qs = Window.objects.filter(ifc_model_id=model_id).select_related('floor', 'room')
        
        # Filter
        if floor_id := self.request.GET.get('floor'):
            qs = qs.filter(floor_id=floor_id)
        if room_id := self.request.GET.get('room'):
            qs = qs.filter(room_id=room_id)
        if wall := self.request.GET.get('wall'):
            qs = qs.filter(wall_position=wall)
            
        return qs

class DoorListView(HtmxMixin, ListView):
    """Türliste mit Filterung"""
    model = Door
    template_name = 'cad_hub/door_list.html'
    partial_template_name = 'cad_hub/partials/_door_table.html'
    context_object_name = 'doors'
    paginate_by = 50
    
    def get_queryset(self):
        model_id = self.kwargs['model_id']
        return Door.objects.filter(ifc_model_id=model_id).select_related('floor', 'from_room', 'to_room')
```

#### 3. Templates
```
cad_hub/templates/cad_hub/
├── window_list.html
├── door_list.html
└── partials/
    ├── _window_table.html
    └── _door_table.html
```

#### 4. URLs
```python
# apps/cad_hub/urls.py
urlpatterns += [
    path('model/<uuid:model_id>/windows/', views.WindowListView.as_view(), name='window_list'),
    path('model/<uuid:model_id>/doors/', views.DoorListView.as_view(), name='door_list'),
]
```

---

### Phase 2: Wichtige Features

#### 5. DWG/DXF Upload
- DWGUploadView
- DWG → IFC Konvertierung via MCP Backend
- Progress-Tracking

#### 6. PDF Plan Upload
- PDFPlanUploadView
- Vision AI Integration
- Extrahierte Daten-Review

#### 7. ArchiCAD Integration
- ArchiCADConnectionView
- Sync-Status Dashboard
- Bidirektionale Updates

---

### Phase 3: Optimierungen

#### 8. Floor UI
- FloorListView
- Floor-Detail mit Räumen/Fenstern/Türen
- Geschoss-Übersicht

#### 9. Raum-Klassifizierung
- DIN 277 Kategorie pro Raum
- Confidence-Anzeige
- Manuelle Korrektur-Möglichkeit

---

## 📋 Prioritäten-Matrix

| Feature | MCP Backend | Frontend | Priorität | Aufwand | Impact |
|---------|-------------|----------|-----------|---------|--------|
| **Fenster** | ✅ | ❌ | 🔴 KRITISCH | 4h | HOCH |
| **Türen** | ✅ | ❌ | 🔴 KRITISCH | 4h | HOCH |
| **DWG Upload** | ✅ | ❌ | 🟠 WICHTIG | 6h | HOCH |
| **Wände** | ✅ | ❌ | 🟡 MITTEL | 3h | MITTEL |
| **PDF Upload** | ✅ | ❌ | 🟡 MITTEL | 5h | MITTEL |
| **ArchiCAD Sync** | ✅ | ❌ | 🟡 MITTEL | 8h | MITTEL |
| **Floor UI** | ✅ | ⚠️ | 🟢 NIEDRIG | 2h | NIEDRIG |
| **Raum-Klassifizierung** | ✅ | ⚠️ | 🟢 NIEDRIG | 1h | NIEDRIG |

---

## 🚀 Empfohlener Implementierungs-Plan

### Sprint 1: Fenster + Türen (Critical Path)
**Ziel:** MCP-extrahierte Fenster/Türen im Frontend anzeigen

**Tasks:**
1. ✅ Window + Door Models erstellen
2. ✅ Migrations generieren
3. ✅ WindowListView + DoorListView erstellen
4. ✅ Templates erstellen
5. ✅ URLs registrieren
6. ✅ Navigation im Dashboard ergänzen
7. ✅ MCP Integration testen

**Dauer:** 8 Stunden  
**Blocker:** Keine

---

### Sprint 2: DWG Upload (High Value)
**Ziel:** DWG/DXF Dateien hochladen und verarbeiten

**Tasks:**
1. ✅ DWGUploadView erstellen
2. ✅ MCP dwg_parser Integration
3. ✅ Konvertierung DWG → IFC
4. ✅ Progress-Tracking
5. ✅ Templates + URLs

**Dauer:** 6 Stunden  
**Abhängigkeiten:** Sprint 1 (für Fenster/Türen)

---

### Sprint 3: Floor UI + Optimierungen
**Ziel:** Geschoss-Übersicht vervollständigen

**Tasks:**
1. ✅ FloorListView
2. ✅ Floor-Detail-Ansicht
3. ✅ Templates
4. ✅ Raum-Klassifizierung verbessern

**Dauer:** 3 Stunden  
**Nice-to-Have**

---

## ✅ Zusammenfassung

**MCP Backend ist vollständig:**
- ✅ 15 Tools implementiert
- ✅ 10 Handler verfügbar
- ✅ DIN 277, WoFlV, GAEB, Raumbuch
- ✅ DWG, IFC, PDF Parser
- ✅ ArchiCAD Integration

**Frontend CAD Hub Lücken:**
- ❌ **Fenster** (kritisch)
- ❌ **Türen** (kritisch)
- ❌ **DWG/DXF Upload** (wichtig)
- ⚠️ **Floor UI** (teilweise)

**Nächster Schritt:**
**Sprint 1 starten** - Window + Door Models, Views, Templates erstellen (8h Aufwand)

---

**Status:** 🔴 **Frontend hinkt MCP Backend hinterher**  
**Action Required:** Window + Door Features implementieren für vollständige MCP Integration
