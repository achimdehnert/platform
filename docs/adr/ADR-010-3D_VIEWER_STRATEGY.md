# ADR-010: 3D-Viewer Strategie für CAD-Hub

| Attribut | Wert |
|----------|------|
| **Status** | Proposed |
| **Datum** | 2026-02-02 |
| **Aktualisiert** | 2026-02-02 |
| **Autor** | IT-Architekt |
| **Deciders** | Architektur-Team |
| **Relates to** | [ADR-008](ADR-008-USE_CASE_ANALYSIS.md), [ADR-009](ADR-009-IFC_DXF_PROCESSING.md) |

---

## Kontext

Architekten und Brandschutz-Sachverständige benötigen eine Web-basierte 3D-Visualisierung von BIM-Modellen. Die Lösung muss:

- Große IFC-Modelle (100k+ Elemente) performant darstellen
- Auf Standard-Hardware im Browser laufen
- Interaktionen wie Selektion, Schnitte, Messungen unterstützen
- BCF-Viewpoints für Issue-Tracking ermöglichen

## Entscheidung

### Empfehlung: xeokit-sdk (Phase 1) mit web-ifc Fallback

```text
┌─────────────────────────────────────────────────────────────────────┐
│  3D-VIEWER ARCHITEKTUR                                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐       │
│  │   IFC File   │─────▶│ XKT Converter│─────▶│  XKT File    │       │
│  │   (Server)   │      │  (Server)    │      │  (Cache)     │       │
│  └──────────────┘      └──────────────┘      └──────┬───────┘       │
│                                                      │               │
│                                                      ▼               │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    BROWSER                                    │   │
│  │  ┌────────────────────────────────────────────────────────┐  │   │
│  │  │  xeokit-sdk Viewer                                     │  │   │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │  │   │
│  │  │  │ XKTLoader   │  │ BCFViewpoint│  │ Annotations │    │  │   │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘    │  │   │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │  │   │
│  │  │  │ NavCube     │  │ SectionPlane│  │ DistanceMeas│    │  │   │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘    │  │   │
│  │  └────────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Bibliotheks-Vergleich

| Kriterium | xeokit-sdk | web-ifc + Three.js | IFC.js |
|-----------|------------|-------------------|--------|
| **Lizenz** | AGPL-3.0 / Commercial | MIT | AGPL-3.0 |
| **IFC4.3 Support** | ✅ Vollständig | ⚠️ Teilweise | ⚠️ Teilweise |
| **Performance (100k)** | ✅ Exzellent | ⚠️ Gut | ⚠️ Gut |
| **BCF Support** | ✅ Native | ❌ Manuell | ⚠️ Basis |
| **Documentation** | ✅ Umfangreich | ⚠️ Basic | ⚠️ Basic |
| **Enterprise Ready** | ✅ Ja | ❌ Nein | ❌ Nein |
| **Kosten (SaaS)** | ~5k€/Jahr | Kostenlos | ~3k€/Jahr |

**Entscheidung:** xeokit-sdk für Production, web-ifc für Prototyping/Fallback.

---

## XKT-Konvertierung

### Warum XKT?

| Format | Ladezeit (50MB IFC) | Dateigröße | Streaming |
|--------|---------------------|------------|-----------|
| IFC direkt | ~15s | 50 MB | ❌ Nein |
| glTF | ~8s | 120 MB | ⚠️ Teilweise |
| **XKT** | **~2s** | **8 MB** | ✅ Ja |

### Konvertierungs-Pipeline

```python
# services/xkt_converter.py (geplant)
import subprocess
from pathlib import Path

def convert_ifc_to_xkt(ifc_path: Path, output_dir: Path) -> Path:
    """Konvertiert IFC zu XKT für schnelles Laden."""
    xkt_path = output_dir / f"{ifc_path.stem}.xkt"
    
    # Option 1: xeokit-convert CLI
    subprocess.run([
        "xeokit-convert",
        "-i", str(ifc_path),
        "-o", str(xkt_path),
        "-f", "xkt"
    ], check=True)
    
    return xkt_path
```

### Caching-Strategie

```text
┌─────────────────────────────────────────────────────────────────────┐
│  XKT CACHING                                                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. Upload IFC                                                       │
│     └─ Speichern unter: /uploads/{tenant}/{project}/{model}.ifc     │
│                                                                      │
│  2. Process Request                                                  │
│     └─ Check: Existiert XKT-Cache?                                  │
│        ├─ JA: Return cached XKT path                                │
│        └─ NEIN: Convert & Cache                                     │
│                                                                      │
│  3. Cache Location                                                   │
│     └─ /cache/xkt/{tenant}/{project}/{model}_{hash}.xkt             │
│                                                                      │
│  4. Cache Invalidation                                               │
│     └─ Bei IFC-Update: Hash ändert sich → neuer Cache              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Viewer Features

### Phase 1: Basis-Viewer

| Feature | Beschreibung | Priorität |
|---------|--------------|-----------|
| Model Loading | XKT laden & darstellen | Must |
| Navigation | Orbit, Pan, Zoom, First-Person | Must |
| NavCube | Orientierungswürfel | Must |
| Selection | Klick auf Element → Highlight | Must |
| Properties | Ausgewähltes Element → PropertyPanel | Must |
| Tree View | IFC-Struktur als Baum | Should |

### Phase 2: Analyse-Tools

| Feature | Beschreibung | Priorität |
|---------|--------------|-----------|
| Section Planes | Schnittebenen X/Y/Z | Must |
| Distance Measurement | Abstände messen | Should |
| Area Measurement | Flächen messen | Should |
| Annotations | Notizen am Modell | Could |
| BCF Viewpoints | Issues mit Viewpoint speichern | Should |

### Phase 3: Collaboration

| Feature | Beschreibung | Priorität |
|---------|--------------|-----------|
| BCF Import/Export | buildingSMART Standard | Should |
| Share Viewpoint | URL mit Kamera-Position | Could |
| Multi-User | Mehrere Nutzer gleichzeitig | Could |
| Comments | Kommentare an Elementen | Could |

---

## Integration

### Django Template

```html
<!-- templates/cadhub/viewer/model_viewer.html -->
{% extends "cadhub/base.html" %}
{% load static %}

{% block extra_css %}
<link rel="stylesheet" href="{% static 'css/xeokit-viewer.css' %}">
{% endblock %}

{% block content %}
<div id="viewer-container" class="viewer-fullscreen">
    <canvas id="xeokit-canvas"></canvas>
    
    <!-- Navigation Cube -->
    <div id="nav-cube-container"></div>
    
    <!-- Property Panel -->
    <div id="property-panel" class="viewer-panel">
        <h5>Eigenschaften</h5>
        <div id="property-content"></div>
    </div>
    
    <!-- Tree View -->
    <div id="tree-panel" class="viewer-panel">
        <h5>Modellstruktur</h5>
        <div id="tree-content"></div>
    </div>
    
    <!-- Toolbar -->
    <div id="viewer-toolbar">
        <button id="btn-section" title="Schnittebene">
            <i class="bi bi-layers-half"></i>
        </button>
        <button id="btn-measure" title="Messen">
            <i class="bi bi-rulers"></i>
        </button>
        <button id="btn-fit" title="Modell einpassen">
            <i class="bi bi-fullscreen"></i>
        </button>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script src="{% static 'js/xeokit-sdk.min.js' %}"></script>
<script>
const viewer = new xeokit.Viewer({
    canvasId: "xeokit-canvas",
    transparent: true
});

// NavCube
new xeokit.NavCubePlugin(viewer, {
    canvasId: "nav-cube-container"
});

// Load XKT Model
const xktLoader = new xeokit.XKTLoaderPlugin(viewer);
const model = xktLoader.load({
    id: "{{ model.pk }}",
    src: "{% url 'cadhub:model-xkt' model.pk %}",
    edges: true
});

model.on("loaded", () => {
    viewer.cameraFlight.flyTo(model);
});

// Selection Handler
viewer.scene.input.on("pick", (e) => {
    if (e.entity) {
        showProperties(e.entity.id);
    }
});
</script>
{% endblock %}
```

### API Endpoint für XKT

```python
# api/routers/viewer.py
from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()

@router.get("/models/{model_id}/xkt")
async def get_model_xkt(model_id: int, tenant_id: int = Depends(get_tenant)):
    """Liefert XKT-Datei für 3D-Viewer."""
    model = await get_model(model_id, tenant_id)
    
    xkt_path = get_or_create_xkt(model.source_file_path)
    
    return FileResponse(
        xkt_path,
        media_type="application/octet-stream",
        filename=f"{model.name}.xkt"
    )
```

---

## Lizenz-Überlegungen

### xeokit Lizenzmodell

| Nutzung | Lizenz | Kosten |
|---------|--------|--------|
| Open Source Projekt | AGPL-3.0 | Kostenlos |
| Interne Nutzung | AGPL-3.0 | Kostenlos |
| SaaS / Commercial | Commercial | ~5.000€/Jahr |

### Empfehlung

1. **Development**: AGPL-3.0 (kostenlos)
2. **Production SaaS**: Commercial License erforderlich
3. **Fallback**: web-ifc + Three.js für Budget-Constraints

---

## Performance-Optimierung

### Empfohlene Strategien

| Strategie | Beschreibung | Impact |
|-----------|--------------|--------|
| XKT Format | Optimiertes Binary statt IFC | Hoch |
| LOD (Level of Detail) | Vereinfachte Geometrie bei Entfernung | Mittel |
| Frustum Culling | Nicht-sichtbare Objekte ausblenden | Hoch |
| Lazy Loading | Große Modelle in Chunks laden | Mittel |
| WebGL 2.0 | Moderne GPU-Features nutzen | Mittel |

### Benchmark-Ziele

| Metrik | Zielwert |
|--------|----------|
| Time to First Render | < 3s |
| FPS (Navigation) | > 30 fps |
| Memory (100k Elements) | < 500 MB |
| XKT Conversion | < 30s für 100MB IFC |

---

## Implementierungsplan

### Phase 1: Basis (2 Wochen)

- [ ] xeokit-sdk in Static Files einbinden
- [ ] XKT Converter Service implementieren
- [ ] Basis-Viewer Template erstellen
- [ ] Model Loading + Navigation

### Phase 2: Features (2 Wochen)

- [ ] Property Panel mit IFC-Daten
- [ ] Tree View für Modellstruktur
- [ ] Section Planes
- [ ] Distance Measurement

### Phase 3: Integration (1 Woche)

- [ ] BCF Viewpoint Support
- [ ] URL-basiertes Viewpoint Sharing
- [ ] Integration in Projekt-Detail-Seite

---

## Risiken

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| xeokit Lizenzkosten steigen | Niedrig | Hoch | web-ifc Fallback vorbereiten |
| Performance bei sehr großen Modellen | Mittel | Mittel | LOD, Streaming, Hardware-Anforderungen |
| Browser-Kompatibilität | Niedrig | Mittel | WebGL 2.0 Fallback, Browser-Matrix testen |

---

## Alternativen

### Alternative A: web-ifc + Three.js

**Pro:**
- MIT-Lizenz (kostenlos)
- Mehr Kontrolle über Rendering

**Contra:**
- Kein BCF Support
- Weniger Features out-of-box
- Mehr Entwicklungsaufwand

### Alternative B: Autodesk Forge

**Pro:**
- Enterprise-Support
- Viele Features

**Contra:**
- Hohe Kosten (~10k€+/Jahr)
- Vendor Lock-in
- Cloud-only

**Fazit:** xeokit bietet das beste Preis-Leistungs-Verhältnis für unsere Anforderungen.

---

## Referenzen

- **xeokit SDK**: [xeokit.github.io/xeokit-sdk](https://xeokit.github.io/xeokit-sdk/)
- **xeokit-convert**: [github.com/xeokit/xeokit-convert](https://github.com/xeokit/xeokit-convert)
- **web-ifc**: [github.com/IFCjs/web-ifc](https://github.com/IFCjs/web-ifc)
- **BCF Standard**: [buildingsmart.org/standards/bsi-standards/bcf](https://technical.buildingsmart.org/standards/bcf/)

---

**Erstellt:** 2026-02-02  
**Letzte Änderung:** 2026-02-02  
**Review-Status:** Pending Review
