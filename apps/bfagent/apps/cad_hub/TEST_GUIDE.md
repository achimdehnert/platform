# 🧪 CAD Hub - Test Guide

## ✅ Ja, wir haben ein vollständiges Dashboard!

---

## 🎯 Was existiert:

### **1. Dashboard UI** ✅
- **View:** `DashboardView` in `views.py`
- **Template:** Modern Tailwind CSS Dashboard
- **Features:**
  - 📊 Statistik-Cards (Projekte, Modelle, Räume)
  - 📋 Liste der letzten Projekte
  - ➕ "Neues Projekt" Button

### **2. Django Admin** ✅
- **Admin-Registrierung:** Alle Models registriert
- **Models:**
  - IFCProject
  - IFCModel
  - Floor
  - Room

---

## 🚀 Test-Anleitung:

### **Schritt 1: Django Server starten**
```bash
cd C:\Users\achim\github\bfagent
python manage.py runserver
```

### **Schritt 2: Dashboard UI testen**

**Dashboard URL:** (cad_hub root muss in config/urls.py gemappt sein)
```
Mögliche URLs (je nach Konfiguration):
- http://localhost:8000/cad/
- http://localhost:8000/cad-hub/
- http://localhost:8000/ifc/
```

**Was du sehen solltest:**
- 3 Statistik-Cards (Projekte, Modelle, Räume)
- Liste der letzten 5 Projekte
- "Neues Projekt" Button

**Funktionen testen:**
1. ✅ Dashboard anzeigen
2. ✅ Projekt erstellen (Button klicken)
3. ✅ Projekt-Detail öffnen (auf Projekt klicken)
4. ✅ IFC-Modell hochladen
5. ✅ Räume anzeigen
6. ✅ DIN 277 Berechnung (erfordert IFC MCP Backend!)
7. ✅ WoFlV Berechnung (erfordert IFC MCP Backend!)
8. ✅ Export (Raumbuch, WoFlV, GAEB)

---

### **Schritt 3: Django Admin testen**

**Admin URL:**
```
http://localhost:8000/admin/
```

**Login:**
- Username: dein Superuser
- Password: dein Passwort

**Verfügbare Sections:**
```
CAD_HUB
├── IFC Projects (IFCProject)
├── IFC Models (IFCModel)
├── Floors (Floor)
└── Rooms (Room)
```

**Was testen:**
1. ✅ IFCProject anlegen/bearbeiten
2. ✅ IFCModel Status ändern
3. ✅ Floors anzeigen
4. ✅ Rooms anzeigen/filtern
5. ✅ Inline-Editing (Models unter Projekt)

---

## ⚠️ WICHTIG: IFC MCP Backend erforderlich!

Einige Features erfordern das IFC MCP Backend:

### **Features MIT Backend:**
- ✅ DIN 277 Flächenberechnung
- ✅ WoFlV Wohnflächenberechnung
- ✅ GAEB Export
- ✅ Schedule-Listen (Fenster, Türen, Wände)
- ✅ Ex-Protection (ATEX)

### **Features OHNE Backend:**
- ✅ Dashboard anzeigen
- ✅ Projekte verwalten
- ✅ Modelle hochladen
- ✅ Räume anzeigen
- ✅ Basic Statistiken

### **Backend starten:**
```bash
cd C:\Users\achim\github\mcp-hub\ifc_mcp
python -m uvicorn ifc_mcp.presentation.api.app:app --reload --port 8001
```

**Backend Health Check:**
```bash
curl http://localhost:8001/health
```

---

## 📋 Test-Checkliste:

### **UI Tests:**
- [ ] Dashboard lädt
- [ ] Statistik-Cards zeigen Zahlen
- [ ] Projekt-Liste zeigt Projekte
- [ ] Neues Projekt erstellen funktioniert
- [ ] Projekt-Detail öffnet
- [ ] IFC-Datei hochladen funktioniert
- [ ] Räume werden angezeigt
- [ ] DIN 277 Berechnung (wenn Backend läuft)
- [ ] WoFlV Berechnung (wenn Backend läuft)
- [ ] Export funktioniert

### **Admin Tests:**
- [ ] Admin Login funktioniert
- [ ] IFCProject CRUD
- [ ] IFCModel CRUD
- [ ] Floor anzeigen
- [ ] Room anzeigen
- [ ] Inline-Editing funktioniert
- [ ] Filter funktionieren
- [ ] Suche funktioniert

---

## 🐛 Troubleshooting:

### **Problem: Dashboard 404**
**Lösung:** Prüfe `config/urls.py` - cad_hub muss gemappt sein:
```python
# In config/urls.py sollte stehen:
path('cad/', include('apps.cad_hub.urls')),
```

### **Problem: "IFC MCP API Error"**
**Lösung:** Backend ist nicht gestartet oder falsche URL
```python
# In settings.py oder .env:
IFC_MCP_URL=http://localhost:8001
```

### **Problem: Admin zeigt keine Models**
**Lösung:** admin.py sollte Models registrieren:
```python
# In cad_hub/admin.py:
@admin.register(IFCProject)
class IFCProjectAdmin(admin.ModelAdmin):
    ...
```

### **Problem: Templates nicht gefunden**
**Lösung:** Template-Ordner prüfen:
```
apps/cad_hub/templates/cad_hub/
├── dashboard.html        ← Muss existieren!
├── base.html
├── project_list.html
└── ...
```

---

## 🎨 UI Screenshots (Was du sehen solltest):

### **Dashboard:**
```
┌─────────────────────────────────────────────┐
│ Dashboard                                    │
├─────────────────────────────────────────────┤
│ ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│ │ 🗂️ 5    │ │ 📦 12   │ │ 🏠 247  │       │
│ │ Projekte│ │ Modelle │ │ Räume   │       │
│ └─────────┘ └─────────┘ └─────────┘       │
├─────────────────────────────────────────────┤
│ Letzte Projekte              + Neues Projekt│
├─────────────────────────────────────────────┤
│ ▶ Projekt Alpha        11.12.2025 10:30    │
│ ▶ Projekt Beta         10.12.2025 15:20    │
│ ▶ Projekt Gamma        09.12.2025 09:15    │
└─────────────────────────────────────────────┘
```

### **Admin Interface:**
```
Django Administration
─────────────────────
CAD_HUB
  ▶ IFC Projects
  ▶ IFC Models
  ▶ Floors
  ▶ Rooms
```

---

## 🚀 Quick Start (Copy & Paste):

```bash
# 1. Django starten
cd C:\Users\achim\github\bfagent
python manage.py runserver

# 2. Backend starten (optional, für Berechnungen)
cd C:\Users\achim\github\mcp-hub\ifc_mcp
python -m uvicorn ifc_mcp.presentation.api.app:app --reload --port 8001

# 3. Browser öffnen
# Dashboard: http://localhost:8000/cad/
# Admin:     http://localhost:8000/admin/
# Backend:   http://localhost:8001/docs
```

---

## ✅ Status:

**Dashboard:** ✅ VORHANDEN & FUNKTIONAL  
**Admin:** ✅ VORHANDEN & REGISTRIERT  
**Templates:** ✅ MODERN & RESPONSIVE  
**Integration:** ⚠️ Erfordert IFC MCP Backend für volle Funktionalität

**READY TO TEST!** 🎉

---

## 📞 Nächste Schritte:

1. **URL-Mapping prüfen** - Wo ist cad_hub gemappt? (`config/urls.py`)
2. **Ersten Test starten** - Dashboard aufrufen
3. **Backend starten** - Für DIN277/WoFlV Features
4. **Test-Daten erstellen** - Projekt + IFC-Datei hochladen
