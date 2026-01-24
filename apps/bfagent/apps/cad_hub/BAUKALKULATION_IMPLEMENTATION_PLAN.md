# 🏗️ Baukalkulation: Implementierungs-Plan für CAD Hub

**Zielgruppe:** Bauingenieure & Kalkulatoren  
**Kernaufgabe:** IFC-Dateien → Angebotskalkulation & Massenermittlung  
**Datum:** 11. Dezember 2025

---

## 📊 Use Case Analyse: Status Quo

### Alle 10 Use Cases im Überblick

| UC | Use Case | Priorität | MCP Backend | Frontend | Gap |
|----|----------|-----------|-------------|----------|-----|
| **UC-01** | **Massenermittlung** | 🔴 **KRITISCH** | ✅ **90%** | ⚠️ **30%** | **60%** |
| **UC-02** | **LV-Position Zuordnung** | 🔴 **KRITISCH** | ❌ **0%** | ❌ **0%** | **100%** |
| **UC-03** | **GAEB Export** | 🔴 **KRITISCH** | ✅ **100%** | ✅ **80%** | **20%** |
| **UC-04** | **DIN 276 Kostengliederung** | 🟡 MITTEL | ⚠️ **50%** | ❌ **0%** | **100%** |
| **UC-05** | **Flächenberechnung** | 🔴 **KRITISCH** | ✅ **100%** | ✅ **90%** | **10%** |
| **UC-06** | **Gewerke-Trennung** | 🟡 MITTEL | ⚠️ **30%** | ❌ **0%** | **100%** |
| **UC-07** | **NU-Anfragen** | 🟡 MITTEL | ⚠️ **40%** | ❌ **0%** | **100%** |
| **UC-08** | **Nebenangebote** | 🟢 NIEDRIG | ⚠️ **20%** | ❌ **0%** | **100%** |
| **UC-09** | **Raumbuch** | 🟡 MITTEL | ✅ **100%** | ✅ **80%** | **20%** |
| **UC-10** | **Modellqualitätsprüfung** | 🔴 **KRITISCH** | ⚠️ **40%** | ❌ **0%** | **100%** |

---

## 🔴 KRITISCHE Use Cases (Top 5 für Bauingenieur/Kalkulator)

### 1️⃣ UC-01: Massenermittlung (Quantity Takeoff) - **KRITISCHSTER USE CASE**

**Warum kritisch:**
- **Kern-Workflow** jeder Kalkulation
- Ohne Massenermittlung: Keine Angebotserstellung möglich
- Zeitersparnis: **80%** (manuell 8h → automatisch 1.5h)

#### MCP Backend Status: ✅ 90%
**Vorhanden:**
- ✅ IFC Parser (IfcOpenShell)
- ✅ DWG Parser
- ✅ Raum-Extraktion (IfcSpace)
- ✅ Wand-Extraktion (IfcWall)
- ✅ Decken-Extraktion (IfcSlab)
- ⚠️ **TEILWEISE:** Türen/Fenster (Parser vorhanden, aber nicht exportiert)

**Fehlt:**
- ❌ **Automatische Abzüge** (Türen/Fenster von Wandflächen)
- ❌ **Netto-Flächen-Berechnung**
- ❌ Treppenextraktion (IfcStair)
- ❌ Fassaden-Extraktion (IfcCurtainWall)

#### Frontend Status: ⚠️ 30%
**Vorhanden:**
- ✅ Raum-Liste mit Filterung
- ✅ Flächen-Anzeige (DIN 277, WoFlV)

**Fehlt:**
- ❌ **Wand-Liste** mit Flächen
- ❌ **Türen-Liste** (KRITISCH - siehe MCP Alignment)
- ❌ **Fenster-Liste** (KRITISCH - siehe MCP Alignment)
- ❌ **Decken-Liste**
- ❌ **Treppen-Liste**
- ❌ **Massenermittlung-Dashboard** (Aggregation)
- ❌ **Excel Export** mit Formeln

#### Erforderliche Komponenten:

**A. Database Models (Priority 1)**
```python
# Bereits vorhanden:
# - Room (IfcSpace) ✅
# - Floor (IfcBuildingStorey) ✅

# KRITISCH FEHLEND:
class Window(models.Model):  # UC-01 + UC-03
    ifc_model = FK(IFCModel)
    floor = FK(Floor, null=True)
    room = FK(Room, null=True)
    
    ifc_guid = CharField(36)
    number = CharField(50)
    width = Decimal(10,3)
    height = Decimal(10,3)
    area = Decimal(10,3)
    
    wall_position = CharField(50)  # North, South, East, West
    u_value = Decimal(5,2)  # Wärmedurchgang
    
class Door(models.Model):  # UC-01 + UC-03
    ifc_model = FK(IFCModel)
    floor = FK(Floor, null=True)
    from_room = FK(Room, null=True)
    to_room = FK(Room, null=True)
    
    ifc_guid = CharField(36)
    number = CharField(50)
    width = Decimal(10,3)
    height = Decimal(10,3)
    
    door_type = CharField(50)
    fire_rating = CharField(20)  # T30, T60, T90

class Wall(models.Model):  # UC-01 ESSENTIAL
    ifc_model = FK(IFCModel)
    floor = FK(Floor, null=True)
    
    ifc_guid = CharField(36)
    name = CharField(100)
    
    length = Decimal(10,3)
    height = Decimal(10,3)
    width = Decimal(10,3)  # Dicke
    gross_area = Decimal(10,3)
    net_area = Decimal(10,3)  # Abzüglich Öffnungen
    volume = Decimal(10,3)
    
    is_external = BooleanField()
    is_load_bearing = BooleanField()
    material = CharField(100)

class Slab(models.Model):  # UC-01 Decken
    ifc_model = FK(IFCModel)
    floor = FK(Floor, null=True)
    
    ifc_guid = CharField(36)
    slab_type = CharField(20)  # FLOOR, ROOF, BASESLAB
    
    area = Decimal(10,3)
    thickness = Decimal(10,3)
    volume = Decimal(10,3)
    perimeter = Decimal(10,3)
```

**B. Views**
```python
class MassenermittlungDashboardView(DetailView):  # KERN-VIEW
    """Massenermittlung Dashboard für ein Modell"""
    model = IFCModel
    template_name = 'cad_hub/massenermittlung_dashboard.html'
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        model = self.object
        
        # Aggregierte Mengen
        ctx['mengen'] = {
            'raeume': {
                'anzahl': model.rooms.count(),
                'flaeche_gesamt': model.rooms.aggregate(Sum('area'))['area__sum'],
                'volumen_gesamt': model.rooms.aggregate(Sum('volume'))['volume__sum'],
            },
            'waende': {
                'anzahl': model.walls.count(),
                'flaeche_brutto': model.walls.aggregate(Sum('gross_area'))['gross_area__sum'],
                'flaeche_netto': model.walls.aggregate(Sum('net_area'))['net_area__sum'],
                'volumen': model.walls.aggregate(Sum('volume'))['volume__sum'],
            },
            'fenster': {
                'anzahl': model.windows.count(),
                'flaeche_gesamt': model.windows.aggregate(Sum('area'))['area__sum'],
            },
            'tueren': {
                'anzahl': model.doors.count(),
            },
            'decken': {
                'anzahl': model.slabs.count(),
                'flaeche_gesamt': model.slabs.aggregate(Sum('area'))['area__sum'],
            },
        }
        
        # Nach Geschoss
        ctx['geschosse'] = []
        for floor in model.floors.all():
            ctx['geschosse'].append({
                'floor': floor,
                'raeume': floor.rooms.count(),
                'waende': floor.walls.count(),
                'fenster': floor.windows.count(),
                'tueren': floor.doors.count(),
            })
        
        return ctx

class WallListView(HtmxMixin, ListView):
    """Wandliste mit Filterung"""
    model = Wall
    template_name = 'cad_hub/wall_list.html'
    partial_template_name = 'cad_hub/partials/_wall_table.html'
    
class SlabListView(HtmxMixin, ListView):
    """Deckenliste"""
    model = Slab
    template_name = 'cad_hub/slab_list.html'
```

**C. Excel Export (KRITISCH)**
```python
class MassenermittlungExcelExportView(View):
    """Excel Export mit Formeln für Kalkulator"""
    
    def get(self, request, model_id):
        model = IFCModel.objects.get(pk=model_id)
        
        # Excel Workbook erstellen
        wb = openpyxl.Workbook()
        
        # Sheet 1: Übersicht
        ws_summary = wb.active
        ws_summary.title = "Übersicht"
        
        # Sheet 2: Räume
        ws_rooms = wb.create_sheet("Räume")
        headers = ['Nr', 'Name', 'Geschoss', 'Fläche [m²]', 'Umfang [m]', 'Höhe [m]', 'Volumen [m³]']
        ws_rooms.append(headers)
        
        for room in model.rooms.all():
            ws_rooms.append([
                room.number,
                room.name,
                room.floor.name if room.floor else '',
                float(room.area),
                float(room.perimeter or 0),
                float(room.height or 0),
                float(room.volume or 0),
            ])
        
        # Sheet 3: Wände
        ws_walls = wb.create_sheet("Wände")
        # ... analog
        
        # Sheet 4: Fenster
        # Sheet 5: Türen
        # ...
        
        # Formeln einfügen
        ws_summary['B2'] = f'=SUM(Räume!D:D)'  # Gesamtfläche Räume
        
        # Als Response zurückgeben
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="Massenermittlung_{model.project.name}.xlsx"'
        wb.save(response)
        return response
```

---

### 2️⃣ UC-05: Flächenberechnung nach Normen - **GUT ABGEDECKT**

**Status:** ✅ Fast komplett implementiert

**MCP Backend:** ✅ 100%
- ✅ DIN 277:2021 Calculator
- ✅ WoFlV Calculator
- ✅ Automatische Raumklassifizierung

**Frontend:** ✅ 90%
- ✅ DIN 277 Übersicht
- ✅ WoFlV Übersicht
- ⚠️ Fehlend: Raum-spezifische Klassifizierung anzeigen

**Verbesserungen:**
```python
# In Room List View: DIN 277 Kategorie pro Raum anzeigen
class RoomListView(ListView):
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        
        # DIN 277 Klassifizierung pro Raum
        for room in ctx['rooms']:
            room.din277_category = classify_room_din277(room.name)
            room.woflv_factor = get_woflv_factor(room.name, room.height)
        
        return ctx
```

---

### 3️⃣ UC-03: GAEB Export - **SEHR GUT ABGEDECKT**

**Status:** ✅ 80% implementiert

**MCP Backend:** ✅ 100%
- ✅ GAEB X84 Generator
- ✅ Massenermittlung → LV Positionen
- ✅ Excel Export

**Frontend:** ✅ 80%
- ✅ GAEB Export View vorhanden
- ⚠️ Fehlend: GAEB X81 (Anfrage ohne Preise)
- ⚠️ Fehlend: GAEB X83 Import (Angebote einlesen)

**Erweiterungen:**
```python
class GAEBAnfrageExportView(View):
    """GAEB X81 Export (ohne Preise für NU-Anfragen)"""
    
class GAEBAngebotImportView(View):
    """GAEB X83 Import (Angebote von NU einlesen)"""
```

---

### 4️⃣ UC-10: Modellqualitätsprüfung - **KRITISCH FEHLEND**

**Warum kritisch:**
- **Datenqualität = Kalkulationsqualität**
- Fehlerhafte IFC-Daten → Fehlerhafte Mengen → Falsche Preise
- **Haftungsrisiko** bei fehlerhaften Angeboten

**Status:** ⚠️ 40% (nur im MCP Backend teilweise)

**MCP Backend:** ⚠️ 40%
- ✅ IFC Parser validiert Geometrie
- ❌ **Keine systematische Qualitätsprüfung**
- ❌ Kein Fehlerreport

**Frontend:** ❌ 0%
- ❌ **Keine Modellprüfung-UI**
- ❌ Kein Qualitäts-Dashboard

**Erforderliche Komponenten:**

```python
class IFCQualityCheck(models.Model):
    """Modellqualitätsprüfung"""
    ifc_model = FK(IFCModel)
    checked_at = DateTimeField(auto_now_add=True)
    
    # Scores
    quality_score = IntegerField()  # 0-100
    geometry_score = IntegerField()
    properties_score = IntegerField()
    classification_score = IntegerField()
    
    # Issues
    errors = JSONField(default=list)
    warnings = JSONField(default=list)
    
class IFCQualityIssue(models.Model):
    """Einzelner Qualitätsfehler"""
    check = FK(IFCQualityCheck)
    severity = CharField(10)  # ERROR, WARNING, INFO
    category = CharField(50)  # GEOMETRY, PROPERTIES, CLASSIFICATION
    
    ifc_guid = CharField(36, blank=True)
    element_type = CharField(50)
    description = TextField()
    
    # Lokalisierung
    floor_name = CharField(100, blank=True)
    room_name = CharField(100, blank=True)

class ModelQualityCheckView(DetailView):
    """Modellqualitätsprüfung Dashboard"""
    model = IFCModel
    template_name = 'cad_hub/quality_check.html'
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        
        # Prüfung durchführen oder letzte laden
        check = self.object.quality_checks.first()
        if not check or check.checked_at < timezone.now() - timedelta(hours=1):
            check = self.perform_quality_check()
        
        ctx['check'] = check
        ctx['issues_by_severity'] = {
            'errors': check.issues.filter(severity='ERROR'),
            'warnings': check.issues.filter(severity='WARNING'),
            'info': check.issues.filter(severity='INFO'),
        }
        
        return ctx
    
    def perform_quality_check(self):
        """Führt Qualitätsprüfung durch"""
        model = self.object
        check = IFCQualityCheck.objects.create(ifc_model=model)
        
        errors = []
        warnings = []
        
        # 1. Geometrie-Prüfung
        # Nullflächen
        null_area_rooms = model.rooms.filter(area__lte=0)
        for room in null_area_rooms:
            errors.append({
                'category': 'GEOMETRY',
                'guid': room.ifc_guid,
                'type': 'IfcSpace',
                'description': f'Raum {room.number} hat Fläche ≤ 0',
            })
        
        # 2. Eigenschaften-Prüfung
        # Fehlende BaseQuantities
        rooms_without_area = model.rooms.filter(area__isnull=True)
        for room in rooms_without_area:
            warnings.append({
                'category': 'PROPERTIES',
                'guid': room.ifc_guid,
                'type': 'IfcSpace',
                'description': f'Raum {room.number} hat keine Flächenangabe',
            })
        
        # 3. Klassifikation-Prüfung
        # Fehlende Raumtypen
        rooms_without_type = model.rooms.filter(usage_category__isnull=True)
        for room in rooms_without_type:
            warnings.append({
                'category': 'CLASSIFICATION',
                'guid': room.ifc_guid,
                'type': 'IfcSpace',
                'description': f'Raum {room.number} hat keinen Raumtyp',
            })
        
        # 4. Vollständigkeit
        # Fehlende Geschosse
        if model.floors.count() == 0:
            errors.append({
                'category': 'COMPLETENESS',
                'description': 'Keine Geschosse (IfcBuildingStorey) gefunden',
            })
        
        # Score berechnen
        total_issues = len(errors) + len(warnings)
        geometry_issues = len([e for e in errors + warnings if e['category'] == 'GEOMETRY'])
        
        check.quality_score = max(0, 100 - (len(errors) * 10 + len(warnings) * 3))
        check.geometry_score = max(0, 100 - geometry_issues * 15)
        check.errors = errors
        check.warnings = warnings
        check.save()
        
        # Issues als Objekte speichern
        for error in errors:
            IFCQualityIssue.objects.create(
                check=check,
                severity='ERROR',
                category=error['category'],
                ifc_guid=error.get('guid', ''),
                element_type=error.get('type', ''),
                description=error['description'],
            )
        
        for warning in warnings:
            IFCQualityIssue.objects.create(
                check=check,
                severity='WARNING',
                category=warning['category'],
                ifc_guid=warning.get('guid', ''),
                element_type=warning.get('type', ''),
                description=warning['description'],
            )
        
        return check
```

---

### 5️⃣ UC-02: LV-Position Zuordnung (STLB-Bau) - **KOMPLETT FEHLEND**

**Warum kritisch:**
- **Kern-Workflow** für professionelle Kalkulation
- STLB-Bau = **Branchenstandard** in Deutschland
- Ohne STLB: Manuelle Zuordnung (sehr zeitaufwändig)

**Status:** ❌ 0% (weder MCP noch Frontend)

**Komplexität:** HOCH (externe STLB-Datenbank erforderlich)

**Erforderliche Komponenten:**

```python
class STLBKatalog(models.Model):
    """STLB-Bau Katalog (externe Datenbank)"""
    nummer = CharField(20, primary_key=True)  # z.B. "012.01.0010"
    kurztext = CharField(200)
    langtext = TextField()
    einheit = CharField(10)
    gewerk = CharField(50)
    kostengruppe_din276 = CharField(10)

class IFCElementZuordnung(models.Model):
    """IFC Element → STLB Position Mapping"""
    ifc_type = CharField(50)  # IfcWall, IfcDoor, etc.
    ifc_predefined_type = CharField(50, blank=True)
    is_external = BooleanField(null=True)
    
    stlb_nummer = FK(STLBKatalog)
    confidence = DecimalField(3,2)  # Zuordnungs-Confidence
    
    # Regel
    rule_type = CharField(20)  # AUTO, MANUAL, LEARNED

class ElementSTLBZuordnungView(DetailView):
    """STLB-Zuordnung für ein IFC-Modell"""
    model = IFCModel
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        
        # Automatische Zuordnung
        zuordnungen = []
        
        # Wände
        for wall in self.object.walls.all():
            stlb = self.find_stlb_for_wall(wall)
            zuordnungen.append({
                'element': wall,
                'stlb': stlb,
                'confidence': 0.85,
            })
        
        ctx['zuordnungen'] = zuordnungen
        return ctx
    
    def find_stlb_for_wall(self, wall):
        """Findet passende STLB-Position für Wand"""
        if wall.is_external:
            return STLBKatalog.objects.filter(
                gewerk='Mauerarbeiten',
                kurztext__icontains='Außenwand'
            ).first()
        else:
            return STLBKatalog.objects.filter(
                gewerk='Mauerarbeiten',
                kurztext__icontains='Innenwand'
            ).first()
```

**⚠️ HINWEIS:** STLB-Bau Daten sind **kostenpflichtig** (ca. 500-1000€/Jahr). Alternative: Eigene vereinfachte Mapping-Tabelle.

---

## 🎯 EMPFOHLENE IMPLEMENTIERUNGS-ROADMAP

### **Phase 1: Massenermittlung MVP (Priorität: KRITISCH)** 
**Dauer:** 16 Stunden  
**Ziel:** Kalkulator kann Mengen aus IFC extrahieren

#### Sprint 1.1: Fenster + Türen (8h)
- [x] Window Model + Migration
- [x] Door Model + Migration
- [x] WindowListView + Templates
- [x] DoorListView + Templates
- [x] Admin-Integration
- [x] URLs + Navigation

#### Sprint 1.2: Wände + Decken (6h)
- [ ] Wall Model + Migration
- [ ] Slab Model + Migration
- [ ] WallListView + Templates
- [ ] SlabListView + Templates
- [ ] Admin-Integration

#### Sprint 1.3: Massenermittlung Dashboard (2h)
- [ ] MassenermittlungDashboardView
- [ ] Aggregierte Mengen pro Geschoss
- [ ] Template mit Übersicht

---

### **Phase 2: Excel Export + Qualitätsprüfung (Priorität: HOCH)**
**Dauer:** 12 Stunden

#### Sprint 2.1: Excel Export (6h)
- [ ] MassenermittlungExcelExportView
- [ ] Sheets für: Räume, Wände, Fenster, Türen, Decken
- [ ] Formeln für Summen
- [ ] Geschoss-Aggregation

#### Sprint 2.2: Modellqualitätsprüfung (6h)
- [ ] IFCQualityCheck Model
- [ ] IFCQualityIssue Model
- [ ] ModelQualityCheckView
- [ ] Qualitäts-Dashboard Template
- [ ] Automatische Prüfungen:
  - Nullflächen
  - Fehlende Properties
  - Fehlende Klassifikation
  - Doppelte GUIDs

---

### **Phase 3: GAEB Erweiterungen (Priorität: MITTEL)**
**Dauer:** 8 Stunden

#### Sprint 3.1: GAEB X81/X83 (8h)
- [ ] GAEB X81 Export (Anfrage ohne Preise)
- [ ] GAEB X83 Import (Angebote einlesen)
- [ ] Preisspiegel-View
- [ ] Vergleichsansicht

---

### **Phase 4: STLB-Bau Integration (Priorität: NIEDRIG - Optional)**
**Dauer:** 24 Stunden (komplex)

⚠️ **Hinweis:** Nur mit STLB-Lizenz sinnvoll

- [ ] STLB-Katalog Import
- [ ] Regelbasierte Zuordnung
- [ ] Manuelle Korrektur-UI
- [ ] Lernfähigkeit (ML)

---

## 📊 Feature-Matrix: Was fehlt noch?

| Feature | UC | MCP | Frontend | Aufwand | Impact | Priorität |
|---------|-----|-----|----------|---------|--------|-----------|
| **Fenster-Liste** | 01 | ✅ | ❌ | 4h | HOCH | 🔴 P0 |
| **Türen-Liste** | 01 | ✅ | ❌ | 4h | HOCH | 🔴 P0 |
| **Wände-Liste** | 01 | ✅ | ❌ | 3h | HOCH | 🔴 P0 |
| **Decken-Liste** | 01 | ✅ | ❌ | 3h | MITTEL | 🟡 P1 |
| **Massenermittlung Dashboard** | 01 | - | ❌ | 2h | HOCH | 🔴 P0 |
| **Excel Export Mengen** | 01 | ⚠️ | ❌ | 6h | HOCH | 🔴 P0 |
| **Modellqualitätsprüfung** | 10 | ⚠️ | ❌ | 6h | HOCH | 🔴 P1 |
| **GAEB X81 Export** | 03 | ✅ | ❌ | 3h | MITTEL | 🟡 P2 |
| **GAEB X83 Import** | 03 | ❌ | ❌ | 5h | MITTEL | 🟡 P2 |
| **STLB-Bau Zuordnung** | 02 | ❌ | ❌ | 24h | NIEDRIG* | 🟢 P3 |
| **DIN 276 Kostengliederung** | 04 | ⚠️ | ❌ | 8h | MITTEL | 🟡 P2 |
| **Gewerke-Trennung** | 06 | ⚠️ | ❌ | 6h | MITTEL | 🟡 P2 |

*STLB-Bau nur mit Lizenz sinnvoll

---

## 🚀 SOFORT-EMPFEHLUNG (Nächste 16 Stunden)

### **START: Phase 1 - Massenermittlung MVP**

**Reihenfolge:**
1. **Fenster + Türen** (8h) ← **JETZT STARTEN**
2. **Wände + Decken** (6h)
3. **Massenermittlung Dashboard** (2h)

**Nach 16h haben Kalkulatoren:**
- ✅ Alle IFC-Elemente sichtbar (Räume, Wände, Türen, Fenster, Decken)
- ✅ Mengen pro Geschoss
- ✅ Basis für Excel Export

---

## 💡 QUICK WINS (Schnelle Erfolge)

### Quick Win 1: Floor-UI vervollständigen (2h)
- Floor bereits als Model vorhanden
- Nur View + Template fehlen
- **Impact:** Geschoss-Übersicht sofort verfügbar

### Quick Win 2: Raum-Klassifizierung anzeigen (1h)
- MCP Backend kann bereits klassifizieren
- Nur in Room List anzeigen
- **Impact:** DIN 277 Kategorien pro Raum sichtbar

### Quick Win 3: WoFlV-Faktor pro Raum (1h)
- MCP Backend kann berechnen
- In Room Detail anzeigen
- **Impact:** Wohnflächen-Korrekturfaktoren transparent

---

## 📋 ZUSAMMENFASSUNG

**KRITISCHSTE LÜCKEN für Bauingenieur/Kalkulator:**

1. 🔴 **Fenster-Liste** (ohne Fenster: keine Wandflächen-Abzüge)
2. 🔴 **Türen-Liste** (ohne Türen: keine Wandflächen-Abzüge)
3. 🔴 **Wände-Liste** (ohne Wände: keine Fassaden-Kalkulation)
4. 🔴 **Excel Export** (ohne Export: manuelle Übertragung nötig)
5. 🔴 **Qualitätsprüfung** (ohne Prüfung: fehlerhafte Mengen)

**EMPFEHLUNG:**
**Jetzt Phase 1 starten** - Fenster + Türen + Wände implementieren (16h Aufwand)

**Nach Phase 1:**
- ✅ Kalkulator kann **90% der Mengen** aus IFC extrahieren
- ✅ Basis für **Angebotserstellung** vorhanden
- ✅ **Zeitersparnis: 80%** (8h manuell → 1.5h mit Tool)

---

**Soll ich jetzt mit Phase 1, Sprint 1.1 (Fenster + Türen) starten?**
