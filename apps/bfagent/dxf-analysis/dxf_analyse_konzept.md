# Konzept: DXF/DWG Analyse & Erkennung

## Fokus: Auswertung, Extraktion und semantische Erkennung

---

## 1. DWG vs. DXF - Entscheidung

### Empfehlung: DWG→DXF Konvertierung ✓

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     DWG-UNTERSTÜTZUNG ARCHITEKTUR                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────┐      ┌──────────────────┐      ┌───────────────────────┐   │
│  │  DWG-     │      │   ODA File       │      │     ezdxf             │   │
│  │  Datei    │─────▶│   Converter      │─────▶│     Analyse           │   │
│  │           │      │   (kostenlos)    │      │                       │   │
│  └───────────┘      └──────────────────┘      └───────────────────────┘   │
│                              │                                             │
│                              ▼                                             │
│                     ┌──────────────────┐                                   │
│                     │   Temporäre      │                                   │
│                     │   DXF-Datei      │                                   │
│                     └──────────────────┘                                   │
│                                                                             │
│  Alternativ: ezdxf.addons.odafc (integriert ODA automatisch)               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Vergleich der Ansätze

| Kriterium | DWG→DXF (Empfohlen) | Native DWG |
|-----------|---------------------|------------|
| **Python-Library** | ✅ ezdxf (hervorragend) | ❌ Keine reine Python-Lib |
| **Kosten** | ✅ Kostenlos (ODA Converter) | ❌ ODA SDK: $0-$25k/Jahr |
| **Setup-Komplexität** | ✅ 1 Tool installieren | ❌ C++ SDK kompilieren |
| **Datenverlust** | ✅ Minimal (~99% erhalten) | ✅ Keiner |
| **Performance** | ⚡ Sehr gut | ⚡ Etwas besser |
| **Wartbarkeit** | ✅ Einfach | ❌ Komplex |
| **Community-Support** | ✅ Aktiv (ezdxf) | ⚠ Begrenzt |

### Was bei Konvertierung erhalten bleibt

✅ **Vollständig erhalten:**
- Alle geometrischen Entities (LINE, CIRCLE, ARC, POLYLINE, etc.)
- Layer-Struktur und -Eigenschaften
- Block-Definitionen und INSERT-Referenzen
- Attribut-Daten (ATTRIB, ATTDEF)
- Texte (TEXT, MTEXT)
- Bemaßungen (DIMENSION)
- Schraffuren (HATCH)
- Koordinatensystem und Einheiten

⚠ **Möglicherweise eingeschränkt:**
- Proprietäre AutoCAD-Objekte (Proxy Objects)
- Einige spezielle 3D-Solids (ACIS-Daten)
- Embedded OLE-Objekte

---

## 2. Übersicht der Analysemöglichkeiten

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DXF/DWG ANALYSE-PIPELINE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────────┐ │
│  │   INPUT     │──▶│  PARSING    │──▶│  ANALYSE    │──▶│    OUTPUT       │ │
│  │             │   │             │   │             │   │                 │ │
│  │ • DXF       │   │ • Entities  │   │ • Geometrie │   │ • JSON/CSV      │ │
│  │ • DWG→DXF   │   │ • Layers    │   │ • Topologie │   │ • Reports       │ │
│  │             │   │ • Blocks    │   │ • Semantik  │   │ • Visualisierung│ │
│  └─────────────┘   └─────────────┘   └─────────────┘   └─────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Analyse-Ebenen

### Ebene 1: Strukturelle Analyse (Low-Level)

| Kategorie | Was wird analysiert | Anwendung |
|-----------|---------------------|-----------|
| **Entitäten** | Typen, Anzahl, Verteilung | Zeichnungskomplexität |
| **Layer** | Namen, Farben, Sichtbarkeit | Organisation verstehen |
| **Blöcke** | Definitionen, Referenzen, Attribute | Symbole identifizieren |
| **Header** | Version, Einheiten, Koordinatensystem | Kompatibilität prüfen |

### Ebene 2: Geometrische Analyse (Mid-Level)

| Kategorie | Was wird analysiert | Anwendung |
|-----------|---------------------|-----------|
| **Bounding Box** | Min/Max Koordinaten, Ausdehnung | Zeichnungsgröße |
| **Abstände** | Punkt-zu-Punkt, Punkt-zu-Linie | Maßkontrolle |
| **Winkel** | Zwischen Linien, Bögen | Geometrieprüfung |
| **Flächen** | Geschlossene Polygone, Schraffuren | Flächenberechnung |
| **Schnittpunkte** | Linien-Kreuzungen | Topologie |

### Ebene 3: Semantische Analyse (High-Level)

| Kategorie | Was wird analysiert | Anwendung |
|-----------|---------------------|-----------|
| **Zeichnungstyp** | Grundriss, Schnitt, Detail | Klassifikation |
| **Objekte** | Türen, Fenster, Möbel (über Blöcke) | Inventar |
| **Bemaßungen** | Werte, Toleranzen | Maßextraktion |
| **Texte** | Beschriftungen, Legenden | Metadaten |
| **Beziehungen** | Welche Objekte gehören zusammen | Strukturverständnis |

---

## 3. Entity-Typen und ihre Eigenschaften

### 3.1 Basis-Entitäten

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          DXF ENTITY HIERARCHIE                           │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  GEOMETRISCHE PRIMITIVES                                                 │
│  ├── POINT          (x, y, z)                                           │
│  ├── LINE           (start, end)                                        │
│  ├── CIRCLE         (center, radius)                                    │
│  ├── ARC            (center, radius, start_angle, end_angle)            │
│  ├── ELLIPSE        (center, major_axis, ratio, start, end)             │
│  └── RAY/XLINE      (point, direction) - unendliche Linien              │
│                                                                          │
│  KOMPLEXE KURVEN                                                         │
│  ├── LWPOLYLINE     (points[], closed, width) - 2D                      │
│  ├── POLYLINE       (vertices[], closed) - 2D/3D                        │
│  ├── SPLINE         (control_points[], knots[], degree)                 │
│  └── HELIX          (axis, radius, turns)                               │
│                                                                          │
│  FLÄCHEN & KÖRPER                                                        │
│  ├── HATCH          (boundary, pattern, solid)                          │
│  ├── SOLID          (4 Punkte) - gefülltes Viereck                      │
│  ├── 3DFACE         (4 Punkte) - 3D Fläche                              │
│  ├── MESH           (vertices, faces)                                   │
│  └── 3DSOLID        (ACIS data) - B-Rep Körper                          │
│                                                                          │
│  TEXT & ANNOTATION                                                       │
│  ├── TEXT           (insert, height, text, rotation)                    │
│  ├── MTEXT          (insert, width, text) - Multiline                   │
│  ├── DIMENSION      (measurement, text, geometry)                       │
│  ├── LEADER         (vertices, annotation)                              │
│  └── TOLERANCE      (GD&T symbols)                                      │
│                                                                          │
│  REFERENZEN                                                              │
│  ├── INSERT         (block_name, position, scale, rotation)             │
│  ├── ATTRIB         (tag, value) - Block-Attribut                       │
│  └── XREF           (external file reference)                           │
│                                                                          │
│  SPEZIAL                                                                 │
│  ├── IMAGE          (path, insertion, size)                             │
│  ├── VIEWPORT       (view definition)                                   │
│  └── TABLE          (rows, columns, cells)                              │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Extrahierbare Attribute pro Entity

| Entity | Primäre Attribute | Sekundäre Attribute |
|--------|-------------------|---------------------|
| LINE | start, end | layer, color, linetype, lineweight |
| CIRCLE | center, radius | layer, color, linetype |
| ARC | center, radius, start_angle, end_angle | layer, color |
| LWPOLYLINE | vertices, closed, const_width | layer, elevation |
| TEXT | insert, text, height, rotation | layer, style, halign, valign |
| MTEXT | insert, text, width, char_height | layer, style, attachment |
| INSERT | name, insert, xscale, yscale, rotation | layer, attribs[] |
| DIMENSION | measurement, defpoint, text_midpoint | dimstyle, override |
| HATCH | boundary_paths, pattern_name, scale | layer, solid_fill |

---

## 4. Analyse-Module im Detail

### 4.1 Modul: Entity-Analyse

```
┌─────────────────────────────────────────────────────────────────┐
│                    ENTITY ANALYSE WORKFLOW                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  INPUT: DXF Document                                            │
│     │                                                           │
│     ▼                                                           │
│  ┌─────────────────────────────────────────────┐               │
│  │ 1. ENUMERATION                              │               │
│  │    • Alle Entities durchlaufen              │               │
│  │    • Nach Typ gruppieren                    │               │
│  │    • Zählen und kategorisieren              │               │
│  └──────────────────┬──────────────────────────┘               │
│                     ▼                                           │
│  ┌─────────────────────────────────────────────┐               │
│  │ 2. ATTRIBUT-EXTRAKTION                      │               │
│  │    • Geometrie-Daten extrahieren            │               │
│  │    • DXF-Attribute auslesen                 │               │
│  │    • Extended Data (XDATA) prüfen           │               │
│  └──────────────────┬──────────────────────────┘               │
│                     ▼                                           │
│  ┌─────────────────────────────────────────────┐               │
│  │ 3. NORMALISIERUNG                           │               │
│  │    • Koordinaten transformieren             │               │
│  │    • Einheiten konvertieren                 │               │
│  │    • Redundanzen entfernen                  │               │
│  └──────────────────┬──────────────────────────┘               │
│                     ▼                                           │
│  OUTPUT: Strukturierte Entity-Daten (JSON/DataFrame)            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Modul: Geometrische Analyse

**Funktionalitäten:**

| Funktion | Beschreibung | Output |
|----------|--------------|--------|
| `calculate_distances()` | Abstände zwischen Entities | Distance Matrix |
| `find_intersections()` | Schnittpunkte finden | Point List |
| `detect_parallel()` | Parallele Linien erkennen | Line Pairs |
| `detect_perpendicular()` | Rechtwinklige Verbindungen | Line Pairs |
| `calculate_areas()` | Flächen geschlossener Polygone | Area List |
| `calculate_perimeters()` | Umfänge berechnen | Perimeter List |
| `find_nearest_neighbor()` | Nächste Nachbarn finden | Entity Pairs |
| `cluster_entities()` | Räumliche Gruppierung | Clusters |

### 4.3 Modul: Topologie-Analyse

```
TOPOLOGIE-BEZIEHUNGEN:

1. KONNEKTIVITÄT
   • Welche Linien sind verbunden?
   • Wo sind die Knotenpunkte?
   • Gibt es offene Enden?

2. ENTHALTENSEIN (Containment)
   • Welche Punkte liegen in welchen Polygonen?
   • Verschachtelte Konturen erkennen
   • Räume/Bereiche identifizieren

3. NACHBARSCHAFT (Adjacency)
   • Welche Entities grenzen aneinander?
   • Gemeinsame Kanten finden
   • Lücken erkennen

4. HIERARCHIE
   • Block-Verschachtelungen
   • Layer-Gruppen
   • Logische Zusammengehörigkeit
```

### 4.4 Modul: Text- und Bemaßungs-Extraktion

**Text-Kategorien:**

| Kategorie | Erkennungsmerkmal | Beispiele |
|-----------|-------------------|-----------|
| Raumbeschriftung | Position in geschlossenem Polygon | "Wohnzimmer", "Bad" |
| Bemaßungstext | Teil einer DIMENSION-Entity | "2500", "1,50 m" |
| Legende | Gruppiert, oft in Tabelle | Materialbezeichnungen |
| Titel | Große Schrift, oft zentriert | Zeichnungstitel |
| Positionsnummern | Nummerisch, mit Leader | "1", "2", "A1" |
| Kommentare/Notizen | MTEXT, längerer Text | Anweisungen |

### 4.5 Modul: Block/Symbol-Erkennung

```
BLOCK-ANALYSE WORKFLOW:

1. BLOCK-DEFINITIONEN SAMMELN
   • Name, Base Point
   • Enthaltene Entities
   • Attribute-Definitionen (ATTDEF)

2. BLOCK-REFERENZEN (INSERT) FINDEN
   • Position (x, y, z)
   • Skalierung (xscale, yscale, zscale)
   • Rotation
   • Attribut-Werte (ATTRIB)

3. SYMBOL-KLASSIFIKATION
   • Standard-Symbole erkennen (Türen, Fenster, Steckdosen)
   • Benutzerdefinierte Symbole katalogisieren
   • Häufigkeit und Verteilung analysieren

4. ATTRIBUT-EXTRAKTION
   • Tag-Value Paare auslesen
   • Stücklisten generieren
   • Metadaten extrahieren
```

### 4.6 Modul: Layer-Analyse

| Analyse | Beschreibung | Nutzen |
|---------|--------------|--------|
| Layer-Inventar | Alle Layer mit Eigenschaften | Strukturübersicht |
| Entity-Verteilung | Anzahl Entities pro Layer | Komplexitätsanalyse |
| Namenskonventionen | Muster in Layer-Namen erkennen | Standardkonformität |
| Farbschema | Farb-Layer Zuordnung | Visualisierungslogik |
| Leere Layer | Layer ohne Entities | Aufräumpotential |
| Layer-Hierarchie | Verschachtelungen (via Namen) | Organisation |

---

## 5. Semantische Erkennung

### 5.1 Zeichnungstyp-Klassifikation

```
┌─────────────────────────────────────────────────────────────────┐
│                 ZEICHNUNGSTYP-ERKENNUNG                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  MERKMALE → KLASSIFIKATION                                      │
│                                                                 │
│  ┌─────────────────┐    ┌──────────────────────────────────┐   │
│  │ Viele HATCH     │    │                                  │   │
│  │ Rechteckige     │───▶│  GRUNDRISS (Floor Plan)          │   │
│  │ geschl. Formen  │    │                                  │   │
│  └─────────────────┘    └──────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────┐    ┌──────────────────────────────────┐   │
│  │ Horizontale +   │    │                                  │   │
│  │ Vertikale       │───▶│  SCHNITT (Section)               │   │
│  │ Schraffuren     │    │                                  │   │
│  └─────────────────┘    └──────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────┐    ┌──────────────────────────────────┐   │
│  │ Kreise, Bögen   │    │                                  │   │
│  │ Mittellinie     │───▶│  TECHNISCHE ZEICHNUNG            │   │
│  │ Layer           │    │  (Mechanical Drawing)            │   │
│  └─────────────────┘    └──────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────┐    ┌──────────────────────────────────┐   │
│  │ Viele DIMENSIONs│    │                                  │   │
│  │ Toleranzen      │───▶│  FERTIGUNGSZEICHNUNG             │   │
│  │ GD&T Symbole    │    │  (Manufacturing Drawing)         │   │
│  └─────────────────┘    └──────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────┐    ┌──────────────────────────────────┐   │
│  │ Linien-Netzwerk │    │                                  │   │
│  │ Symbole (Blöcke)│───▶│  SCHALTPLAN / P&ID               │   │
│  │ Verbindungen    │    │  (Schematic / Piping)            │   │
│  └─────────────────┘    └──────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Objekterkennung in Grundrissen

| Objekt | Erkennungsmerkmale | Block-Namen (typisch) |
|--------|---------------------|----------------------|
| Tür | Bogen + Linie, Öffnung in Wand | DOOR, TÜR, D-* |
| Fenster | Parallele Linien in Wand | WINDOW, FENSTER, W-* |
| Treppe | Parallele Stufen-Linien | STAIR, TREPPE |
| Aufzug | Rechteck mit X oder Diagonalen | ELEVATOR, LIFT |
| Sanitär | Spezifische Block-Formen | WC, SINK, BATH |
| Möbel | Diverse Block-Definitionen | DESK, TABLE, CHAIR |
| Elektro | Kleine Symbole | OUTLET, SWITCH, LAMP |

### 5.3 Maß- und Toleranz-Extraktion

```
DIMENSION-ANALYSE:

1. DIMENSION-TYPEN ERKENNEN
   • Linear (horizontal, vertical, aligned)
   • Angular (Winkel)
   • Radial (Radius, Diameter)
   • Ordinate (Koordinaten)
   • Arc Length

2. WERTE EXTRAHIEREN
   • Gemessener Wert (measurement)
   • Override-Text (wenn abweichend)
   • Toleranzen (+/- Werte)
   • Prefix/Suffix

3. BEZUGSOBJEKTE FINDEN
   • Welche Geometrie wird bemaßt?
   • Definition Points analysieren
   • Zuordnung zu Entities
```

---

## 6. Qualitäts- und Validierungsanalyse

### 6.1 Prüfpunkte

| Kategorie | Prüfung | Schweregrad |
|-----------|---------|-------------|
| **Geometrie** | Doppelte Entities | Warnung |
| | Sehr kurze Linien (<0.1mm) | Info |
| | Nicht geschlossene Polygone | Warnung |
| | Selbstüberschneidende Polylinien | Fehler |
| **Layer** | Entities auf Layer "0" | Info |
| | Leere Layer | Info |
| | Inkonsistente Namenskonventionen | Warnung |
| **Text** | Texthöhe = 0 | Fehler |
| | Leere Textfelder | Warnung |
| | Nicht-Standard Schriftarten | Info |
| **Blöcke** | Unbenutzte Block-Definitionen | Info |
| | Fehlende Block-Definitionen | Fehler |
| | Verschachtelte Blöcke >5 Ebenen | Warnung |
| **Bemaßungen** | Override ohne Grund | Warnung |
| | Fehlender Bemaßungsstil | Fehler |

### 6.2 Statistik-Dashboard

```
┌─────────────────────────────────────────────────────────────────┐
│                    DXF ANALYSE REPORT                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  DATEI-INFO                                                     │
│  ├── Dateiname:     beispiel.dxf                               │
│  ├── Version:       AC1027 (AutoCAD 2013)                      │
│  ├── Einheiten:     Millimeter                                 │
│  └── Dateigröße:    2.4 MB                                     │
│                                                                 │
│  GEOMETRIE-ÜBERSICHT                                           │
│  ├── Bounding Box:  (0, 0) - (15000, 8000) mm                  │
│  ├── Zeichnungsgröße: 15.0 x 8.0 m                             │
│  └── Geschätzte Fläche: 120 m²                                 │
│                                                                 │
│  ENTITY-STATISTIK                                              │
│  ├── LINE:          1,234 (45%)                                │
│  ├── LWPOLYLINE:      456 (17%)                                │
│  ├── CIRCLE:          123 (5%)                                 │
│  ├── ARC:             234 (9%)                                 │
│  ├── TEXT/MTEXT:      345 (13%)                                │
│  ├── INSERT:          156 (6%)                                 │
│  ├── DIMENSION:        89 (3%)                                 │
│  └── Sonstige:         67 (2%)                                 │
│  ────────────────────────────                                  │
│  GESAMT:            2,704 Entities                             │
│                                                                 │
│  LAYER-STATISTIK                                               │
│  ├── Anzahl Layer:  24                                         │
│  ├── Mit Entities:  18                                         │
│  └── Leere Layer:   6                                          │
│                                                                 │
│  QUALITÄTSPRÜFUNG                                              │
│  ├── ✓ Keine doppelten Entities                                │
│  ├── ⚠ 12 sehr kurze Linien gefunden                          │
│  ├── ⚠ 3 nicht geschlossene Polygone                          │
│  └── ✓ Alle Blöcke definiert                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. Export-Formate

### 7.1 Strukturierte Datenformate

| Format | Anwendung | Vorteile |
|--------|-----------|----------|
| **JSON** | API, Web | Hierarchisch, flexibel |
| **CSV** | Excel, Tabellen | Einfach, universell |
| **GeoJSON** | GIS-Systeme | Geo-Standard |
| **Pandas DataFrame** | Python Analyse | Mächtig, flexibel |
| **SQLite** | Große Datenmengen | Queryable |
| **XML** | Enterprise | Strukturiert |

### 7.2 Export-Beispiele

**JSON-Export Struktur:**
```json
{
  "file_info": {
    "filename": "beispiel.dxf",
    "version": "AC1027",
    "units": "mm"
  },
  "statistics": {
    "total_entities": 2704,
    "by_type": {"LINE": 1234, "CIRCLE": 123}
  },
  "layers": [
    {"name": "WALLS", "color": 7, "entity_count": 456}
  ],
  "entities": [
    {
      "type": "LINE",
      "layer": "WALLS",
      "start": [0, 0],
      "end": [1000, 0]
    }
  ],
  "blocks": [
    {
      "name": "DOOR",
      "insert_count": 12,
      "attributes": ["WIDTH", "TYPE"]
    }
  ],
  "texts": [
    {"content": "Wohnzimmer", "position": [5000, 4000], "height": 200}
  ],
  "dimensions": [
    {"value": 2500, "unit": "mm", "type": "linear"}
  ]
}
```

---

## 8. Technologie-Empfehlungen

### 8.1 Kern-Stack

| Komponente | Empfehlung | Begründung |
|------------|------------|------------|
| DXF-Parsing | `ezdxf` 1.4.x | Beste Python-Lib, aktiv gepflegt |
| Geometrie | `shapely` | Topologie-Operationen |
| Numerik | `numpy` | Schnelle Berechnungen |
| Datenanalyse | `pandas` | Strukturierte Auswertung |
| Visualisierung | `matplotlib` | DXF-Addon verfügbar |
| ML/Klassifikation | `scikit-learn` | Standard für ML |

### 8.2 Optionale Erweiterungen

| Für | Empfehlung | Anwendung |
|-----|------------|-----------|
| DWG-Support | ODA File Converter | Konvertierung |
| OCR | `pytesseract` | Gescannte Zeichnungen |
| Deep Learning | `PyTorch` / `TensorFlow` | Symbol-Erkennung |
| Räumliche Indizes | `rtree` | Schnelle Nachbarsuche |
| Graph-Analyse | `networkx` | Topologie |

---

## 9. Installation & Setup

### 9.1 Python-Pakete

```bash
# Basis-Installation
pip install ezdxf[draw]  # Mit Visualisierung
pip install numpy pandas shapely

# Optional für erweiterte Analyse
pip install scikit-learn  # ML-Klassifikation
pip install networkx      # Graph-Analyse
pip install rtree         # Räumliche Indizes
```

### 9.2 ODA File Converter (für DWG-Support)

**Download:** https://www.opendesign.com/guestfiles/oda_file_converter

**Windows:**
```
1. Installer herunterladen (.exe)
2. Installieren (Standard: C:\Program Files\ODA\ODAFileConverter)
3. Fertig - wird automatisch gefunden
```

**Linux (Ubuntu/Debian):**
```bash
# DEB-Paket
sudo dpkg -i ODAFileConverter_QT6_lnxX64_*.deb
sudo apt-get install -f  # Abhängigkeiten

# Oder als AppImage (keine Installation nötig)
chmod +x ODAFileConverter_*.AppImage
./ODAFileConverter_*.AppImage
```

**Linux (Fedora/RHEL):**
```bash
sudo rpm -i ODAFileConverter_QT6_lnxX64_*.rpm
```

**macOS:**
```bash
# DMG herunterladen und installieren
# Oder via Homebrew (falls verfügbar)
```

### 9.3 Verwendung im Code

```python
from dxf_analysis_toolkit import DXFAnalyzer, DWGConverter

# Automatisch: DXF oder DWG
analyzer = DXFAnalyzer("zeichnung.dwg")  # Konvertiert automatisch
report = analyzer.full_analysis()

# Manuell: DWG zu DXF konvertieren
converter = DWGConverter()
if converter.is_available:
    dxf_path = converter.convert_to_dxf("input.dwg", "output.dxf")
```

---

## 10. Roadmap

### Phase 1: Basis-Analyse ✅
- [x] Entity-Extraktion
- [x] Layer-Analyse
- [x] Statistiken
- [x] Bounding Box
- [x] **DWG-Unterstützung** (via ODA Converter)

### Phase 2: Geometrische Analyse
- [ ] Abstands-Berechnung
- [ ] Schnittpunkt-Erkennung
- [ ] Flächen-Berechnung
- [ ] Topologie-Graph

### Phase 3: Semantische Erkennung
- [ ] Zeichnungstyp-Klassifikation
- [ ] Block/Symbol-Erkennung
- [ ] Text-Kategorisierung
- [ ] Maß-Extraktion

### Phase 4: Qualität & Export
- [ ] Validierungs-Engine
- [ ] Multi-Format Export
- [ ] Report-Generator
- [ ] API/CLI Interface

---

*Version: 2.1 - Mit DWG-Unterstützung*
*Stand: Dezember 2025*
