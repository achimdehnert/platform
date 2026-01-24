# 🚀 IFC Dashboard - MCP-basierte Optimierungen V2

## Übersicht

Die Django cad_hub App wurde basierend auf **BauCAD Hub MCP** Best Practices optimiert.

---

## 🔧 Services (Vollständig)

### 1. IFC Parser Service
**Quelle:** `cad_mcp/parsers/ifc_parser.py`

- Vollständige Quantity-Extraktion (NetFloorArea, Height, Volume, Perimeter)
- DIN 277 Raumklassifizierung
- Einheiten-Handling (mm/cm/m)
- Property Set Extraktion

### 2. DIN 277 Calculator ✅
**Quelle:** `cad_mcp/standards/din277.py`

```python
from .services import DIN277Calculator

calculator = DIN277Calculator()
result = calculator.calculate_from_rooms(rooms, bgf=1000)

# Ergebnis: BGF, KGF, NRF, NF1-7, TF, VF, BRI, Kennzahlen
```

### 3. WoFlV Calculator ✅ NEU
**Quelle:** `cad_mcp/standards/woflv.py`

```python
from .services import WoFlVCalculator

calculator = WoFlVCalculator()
result = calculator.calculate_from_rooms(rooms)

# Ergebnis:
# - wohnflaeche_gesamt
# - wohnflaeche_100 (100% angerechnet)
# - wohnflaeche_50 (50% - Dachschrägen)
# - wohnflaeche_25 (25% - Balkone)
# - nicht_angerechnet (Keller, Garage)
# - anrechnungsquote
```

**Anrechnungsfaktoren:**
| Raumtyp | Faktor |
|---------|--------|
| Wohnraum, Küche, Bad | 100% |
| Höhe 1-2m, Wintergarten | 50% |
| Balkon, Terrasse | 25% |
| Keller, Garage | 0% |

### 4. GAEB Generator ✅ NEU
**Quelle:** `cad_mcp/generators/gaeb.py`

```python
from .services import (
    GAEBGenerator, Leistungsverzeichnis, LosGruppe, 
    Position, MengenEinheit, MassenermittlungHelper
)

# LV aus Räumen erstellen
positionen = MassenermittlungHelper.from_rooms(
    rooms, gewerk="Bodenbelag", oz_prefix="01"
)

lv = Leistungsverzeichnis(
    projekt_name="Sanierung EFH",
    lose=[LosGruppe(oz="01", bezeichnung="Bodenbeläge", positionen=positionen)]
)

generator = GAEBGenerator()
xml_output = generator.generate_xml(lv)     # GAEB X84
excel_output = generator.generate_excel(lv)  # Alternative
```

### 5. Raumbuch Export
**Quelle:** `cad_mcp/generators/raumbuch.py`

- 3 Excel-Sheets (Raumbuch, DIN 277, Geschosse)
- Professionelle Formatierung
- DIN 277 Kennzahlen

---

## 📁 Neue Dateistruktur

```
cad_hub/
├── services/
│   ├── __init__.py
│   ├── ifc_parser.py        # ✅ Optimiert
│   ├── din277_calculator.py # ✅ DIN 277:2021
│   ├── woflv_calculator.py  # ✅ NEU - Wohnfläche
│   ├── gaeb_generator.py    # ✅ NEU - Ausschreibung
│   └── export_service.py    # ✅ Raumbuch
├── templates/
│   └── cad_hub/
│       ├── woflv_summary.html      # ✅ NEU
│       └── partials/
│           └── _woflv_summary.html # ✅ NEU
├── views.py                 # ✅ +3 neue Views
└── urls.py                  # ✅ +3 neue URLs
```

---

## 🌐 Neue URLs

| URL | View | Funktion |
|-----|------|----------|
| `/cad/model/{id}/woflv/` | WoFlVSummaryView | Wohnflächen-Übersicht |
| `/cad/model/{id}/export/woflv/` | ExportWoFlVView | WoFlV Excel Export |
| `/cad/model/{id}/export/gaeb/` | ExportGAEBView | LV Export (XML/Excel) |

---

## 🔗 Integration mit BauCAD Hub MCP

Die Services sind **1:1 kompatibel** mit den MCP Handlers:

| Django Service | MCP Handler |
|----------------|-------------|
| `DIN277Calculator` | `din277_calculator` |
| `WoFlVCalculator` | `woflv_calculator` |
| `GAEBGenerator` | `gaeb_generator` |
| `IFCParserService` | `ifc_parser` |
| `RaumbuchExportService` | `raumbuch_generator` |

---

## 📊 Feature Matrix

| Feature | Status | MCP-Quelle |
|---------|--------|------------|
| IFC Parsing | ✅ | `parsers/ifc_parser.py` |
| DIN 277:2021 | ✅ | `standards/din277.py` |
| WoFlV | ✅ NEU | `standards/woflv.py` |
| GAEB X84 | ✅ NEU | `generators/gaeb.py` |
| Raumbuch Excel | ✅ | `generators/raumbuch.py` |
| ArchiCAD API | ⬜ | `integrations/archicad.py` |
| BCF Export | ⬜ | Noch nicht implementiert |

---

## 🚀 Installation

```bash
# 1. Entpacken
tar -xzf cad_hub_v2_optimized.tar.gz -C apps/

# 2. Dependencies
pip install ifcopenshell openpyxl

# 3. Migrations
python manage.py makemigrations cad_hub
python manage.py migrate

# 4. Starten
python manage.py runserver
```

---

## 📈 Nächste Schritte

1. **ArchiCAD Integration** - Direkte Verbindung über JSON API
2. **BCF Export** - Issue-Tracking für BIM-Koordination  
3. **STLB-Bau Mapping** - Standardleistungsbuch-Referenzen
4. **Celery Tasks** - Async IFC Processing

---

*Basiert auf: BauCAD Hub MCP v1.0, Tapir ArchiCAD MCP, IFC MCP*
