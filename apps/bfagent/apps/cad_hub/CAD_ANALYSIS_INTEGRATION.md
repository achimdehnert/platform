# CAD Analysis Integration - Dokumentation

## 🎯 Übersicht

Die CAD Analysis Integration erweitert den CAD Hub um 4 Hauptanwendungsszenarien basierend auf dem CAD MCP Server.

## 📁 Erstellte Dateien

### Service Layer
- `apps/cad_hub/services/mcp_bridge.py` - MCP Bridge Service (~600 Zeilen)

### Views
- `apps/cad_hub/views_analysis.py` - Alle Analysis Views (~400 Zeilen)

### Templates
- `apps/cad_hub/templates/cad_hub/analysis/dashboard.html` - Analyse-Dashboard
- `apps/cad_hub/templates/cad_hub/analysis/format_analyzer.html` - Format-Analyse
- `apps/cad_hub/templates/cad_hub/analysis/nl_query.html` - NL Query (Chat)
- `apps/cad_hub/templates/cad_hub/analysis/dxf_quality.html` - DXF Qualitätsprüfung
- `apps/cad_hub/templates/cad_hub/analysis/batch_analyze.html` - Batch-Analyse

---

## 🔄 Datenfluss-Szenarien

### Szenario 1: Format-Analyse (IFC-Upload mit Auto-Analyse)

**URL:** `/cad-hub/analyze/`

**Ablauf:**
```
User → Upload CAD-Datei → CADMCPBridge.analyze_file()
                        → Format erkennen (IFC, DXF, IGES, FBX, ...)
                        → Parser aufrufen
                        → AnalysisResult zurückgeben
                        → Ergebnis in UI anzeigen
```

**Features:**
- Drag & Drop Upload
- Auto-Format-Erkennung
- Unterstützte Formate: IFC, DXF, DWG, IGES, FBX, GLTF, GLB, 3MF, PLY, STEP
- Historie der letzten Analysen

---

### Szenario 2: DXF Qualitätsprüfung

**URL:** `/cad-hub/dxf-quality/`

**Ablauf:**
```
User → Upload DXF → CADMCPBridge.check_dxf_quality()
                  → Maßketten analysieren (Dimension Chains)
                  → Schnittdarstellungen analysieren (Section Views)
                  → Qualitäts-Score berechnen
                  → Issues identifizieren
                  → DXFQualityResult zurückgeben
```

**Features:**
- Maßketten-Validierung (Überbestimmung, Schließfehler)
- Schnittdarstellungen-Erkennung
- Material-Erkennung via Schraffur-Pattern
- Qualitäts-Score (0-100)

---

### Szenario 3: Natural Language Query

**URL:** `/cad-hub/nl-query/`

**Ablauf:**
```
User → Frage eingeben → CADMCPBridge.query_natural_language()
                      → Pattern Matching auf Frage
                      → Django ORM Query auf Modell-Daten
                      → Antwort generieren
                      → NLQueryResult zurückgeben
```

**Unterstützte Fragen:**
- "Welcher Raum ist am größten?"
- "Wie viele Türen gibt es?"
- "Gesamtfläche aller Räume?"
- "Liste alle Räume"
- "Welcher Raum ist am kleinsten?"
- "Wie viele Fenster hat das Gebäude?"

**Features:**
- Chat-Interface
- Modell-Auswahl
- Beispiel-Fragen
- Chat-Historie

---

### Szenario 4: Batch-Analyse

**URL:** `/cad-hub/batch-analyze/`

**Ablauf:**
```
User → Mehrere Dateien hochladen → CADMCPBridge.batch_analyze()
                                 → Für jede Datei: analyze_file()
                                 → Zusammenfassung erstellen
                                 → BatchResult zurückgeben
```

**Features:**
- Multi-File Upload
- Fortschrittsanzeige
- Zusammenfassung (Gesamt/Erfolgreich/Fehlgeschlagen)
- Einzelergebnisse pro Datei

---

## 🏗️ Architektur

```
┌─────────────────────────────────────────────────────────────────┐
│                        CAD Hub (Django)                         │
├─────────────────────────────────────────────────────────────────┤
│  views_analysis.py      │  services/mcp_bridge.py               │
│  ─────────────────      │  ──────────────────────               │
│  FormatAnalyzerView     │  CADMCPBridge                         │
│  DXFQualityView         │    ├── analyze_file()                 │
│  NL2CADQueryView        │    ├── check_dxf_quality()            │
│  BatchAnalyzeView       │    ├── query_natural_language()       │
│                         │    └── batch_analyze()                │
└─────────────────────────┴───────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                     CAD MCP Server (Optional)                   │
├─────────────────────────────────────────────────────────────────┤
│  parse_iges  │  parse_fbx  │  analyze_dimension_chains          │
│  parse_dwg   │  parse_ifc  │  analyze_section_views             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔗 URL-Struktur

| URL | View | Beschreibung |
|-----|------|--------------|
| `/cad-hub/analysis/` | `AnalysisDashboardView` | Analyse-Dashboard |
| `/cad-hub/analyze/` | `FormatAnalyzerView` | Format-Analyse UI |
| `/cad-hub/analyze/api/` | `FormatAnalyzeAPIView` | Format-Analyse API |
| `/cad-hub/dxf-quality/` | `DXFQualityView` | DXF Qualitätsprüfung UI |
| `/cad-hub/dxf-quality/api/` | `DXFQualityAPIView` | DXF Qualitätsprüfung API |
| `/cad-hub/nl-query/` | `NL2CADQueryView` | NL Query UI |
| `/cad-hub/nl-query/api/` | `NL2CADQueryAPIView` | NL Query API |
| `/cad-hub/batch-analyze/` | `BatchAnalyzeView` | Batch-Analyse UI |
| `/cad-hub/batch-analyze/api/` | `BatchAnalyzeAPIView` | Batch-Analyse API |
| `/cad-hub/formats/` | `SupportedFormatsView` | Unterstützte Formate |

---

## 🧪 Verwendung

### MCP Bridge direkt nutzen

```python
from apps.cad_hub.services.mcp_bridge import get_mcp_bridge

# Bridge instanziieren
bridge = get_mcp_bridge()

# Datei analysieren
result = await bridge.analyze_file("/path/to/model.ifc")
print(result.data)

# DXF Qualitätsprüfung
quality = await bridge.check_dxf_quality("/path/to/drawing.dxf")
print(f"Score: {quality.quality_score}")

# NL Query
answer = await bridge.query_natural_language(
    question="Welcher Raum ist am größten?",
    model_id=uuid.UUID("...")
)
print(answer.answer)

# Batch-Analyse
batch = await bridge.batch_analyze("/path/to/folder/", extensions=[".ifc", ".dxf"])
print(f"Analyzed: {batch.analyzed}/{batch.total_files}")
```

### Convenience Functions

```python
from apps.cad_hub.services import (
    analyze_cad_file,
    check_dxf_quality,
    ask_cad_question,
    batch_analyze_directory,
)

# Einfache Analyse
result = await analyze_cad_file("model.ifc")

# DXF prüfen
quality = await check_dxf_quality("drawing.dxf")

# Frage stellen
answer = await ask_cad_question("Wie viele Räume?", model_id=uuid)

# Batch
batch = await batch_analyze_directory("/folder/")
```

---

## 📊 Data Classes

### AnalysisResult
```python
@dataclass
class AnalysisResult:
    success: bool
    file_path: str
    format: CADFormat
    data: Dict[str, Any]
    markdown_report: str
    errors: List[str]
    warnings: List[str]
```

### DXFQualityResult
```python
@dataclass
class DXFQualityResult:
    success: bool
    file_path: str
    dimension_chains: Dict[str, Any]
    section_views: Dict[str, Any]
    quality_score: float
    issues: List[Dict[str, Any]]
```

### NLQueryResult
```python
@dataclass
class NLQueryResult:
    success: bool
    query: str
    answer: str
    data: Any
    source_file: str
    confidence: float
```

### BatchResult
```python
@dataclass
class BatchResult:
    success: bool
    total_files: int
    analyzed: int
    failed: int
    results: List[AnalysisResult]
    summary: Dict[str, Any]
```

---

## 🔧 Konfiguration

### settings.py

```python
# CAD MCP Server URL (für Remote-Modus)
CAD_MCP_URL = "http://localhost:8001"

# MCP Bridge Modus: "local" oder "remote"
CAD_MCP_MODE = "local"  # Standard: lokale Parser verwenden
```

---

## ✅ Status

- [x] MCP Bridge Service implementiert
- [x] Format-Analyse View & Template
- [x] DXF Qualitätsprüfung View & Template
- [x] NL Query View & Template
- [x] Batch-Analyse View & Template
- [x] URLs registriert
- [x] Django Check bestanden

---

## 🚀 Nächste Schritte

1. **Navigation erweitern** - Analyse-Links in Sidebar hinzufügen
2. **MCP Server Integration** - Remote-Modus testen
3. **Weitere NL Queries** - Mehr Fragemuster unterstützen
4. **Export-Funktionen** - Analyse-Reports als PDF/Excel
