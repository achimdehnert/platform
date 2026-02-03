# xeokit SDK v3 - Optimale Implementierung für CAD-Hub

**Basierend auf:** xeokit SDK User Guide & Whitepaper  
**Stand:** 2026-02-02

## 1. Architektur-Übersicht

### xeokit SDK Module für CAD-Hub

```
┌─────────────────────────────────────────────────────────────┐
│                     CAD-Hub Frontend                        │
├─────────────────────────────────────────────────────────────┤
│  @xeokit/sdk/viewer      │  @xeokit/sdk/treeview           │
│  (3D Viewer + Camera)    │  (Modellstruktur-Baum)          │
├──────────────────────────┼──────────────────────────────────┤
│  @xeokit/sdk/scene       │  @xeokit/sdk/data               │
│  (3D Objekte/Geometrie)  │  (Semantik/Properties)          │
├──────────────────────────┼──────────────────────────────────┤
│  @xeokit/sdk/bcf         │  @xeokit/sdk/pick               │
│  (BCF Viewpoints)        │  (Objekt-Selektion)             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     CAD-Hub Backend                         │
├─────────────────────────────────────────────────────────────┤
│  xeoconvert CLI          │  Konvertierungs-Pipeline        │
│  --pipeline ifc2xgf      │  IFC → XGF + DataModelParams    │
└─────────────────────────────────────────────────────────────┘
```

## 2. Empfohlene Lade-Strategie

### Entscheidungsmatrix

| Dateigröße | Format | Loader | Konvertierung |
|------------|--------|--------|---------------|
| < 20 MB | IFC | IFCLoader | Keine (direkt) |
| 20-100 MB | IFC | XGFLoader | ifc2xgf |
| > 100 MB | IFC | XGFLoader | ifc2xgf + Streaming |
| Beliebig | glTF | GLTFLoader | Optional gltf2xgf |
| Beliebig | LAS/LAZ | LASLoader | Optional las2xgf |

### Implementierung in Python

```python
# services/model_strategy_service.py
from dataclasses import dataclass
from enum import Enum

class LoadStrategy(Enum):
    DIRECT_IFC = "direct_ifc"      # IFCLoader im Browser
    CONVERT_XGF = "convert_xgf"    # Vorab-Konvertierung
    STREAMING = "streaming"         # Große Dateien

@dataclass
class ModelLoadConfig:
    strategy: LoadStrategy
    primary_url: str
    metadata_url: str | None = None
    chunk_size: int | None = None

def get_load_strategy(file_size_mb: float, format: str) -> ModelLoadConfig:
    """Bestimme optimale Lade-Strategie."""
    
    if format == "ifc":
        if file_size_mb < 20:
            return ModelLoadConfig(
                strategy=LoadStrategy.DIRECT_IFC,
                primary_url="/media/ifc/{model_id}.ifc"
            )
        else:
            return ModelLoadConfig(
                strategy=LoadStrategy.CONVERT_XGF,
                primary_url="/media/xgf/{model_id}.xgf",
                metadata_url="/media/xgf/{model_id}.json"
            )
    
    # Weitere Formate...
```

## 3. Frontend-Architektur

### 3.1 Viewer Setup (Empfohlen)

```javascript
// static/js/cadhub-viewer-v3.js
import * as xeokit from "@xeokit/xeokit-sdk";

class CADHubViewerV3 {
    constructor(canvasId) {
        // 1. Scene erstellen (Geometrie-Container)
        this.scene = new xeokit.Scene();
        
        // 2. Data erstellen (Semantik-Container)
        this.data = new xeokit.Data();
        
        // 3. WebGL Renderer
        this.renderer = new xeokit.WebGLRenderer({});
        
        // 4. Viewer mit Canvas
        this.viewer = new xeokit.Viewer({
            id: "viewer",
            scene: this.scene,
            renderer: this.renderer
        });
        
        // 5. View (Canvas + Kamera)
        this.view = this.viewer.createView({
            id: "mainView",
            canvasId: canvasId
        });
        
        // 6. Kamera-Steuerung
        this.cameraControl = new xeokit.CameraControl(this.view);
        
        // 7. Kamera-Flug (Animationen)
        this.cameraFlight = new xeokit.CameraFlight(this.view);
    }
}
```

### 3.2 Model Loading (XGF - Empfohlen)

```javascript
async loadXGF(xgfUrl, datamodelUrl) {
    // SceneModel für Geometrie
    const sceneModelResult = this.scene.createModel({ id: "model" });
    if (!sceneModelResult.ok) throw new Error(sceneModelResult.error);
    
    // DataModel für Semantik
    const dataModelResult = this.data.createModel({ id: "model" });
    if (!dataModelResult.ok) throw new Error(dataModelResult.error);
    
    const sceneModel = sceneModelResult.value;
    const dataModel = dataModelResult.value;
    
    // XGF Loader
    const xgfLoader = new xeokit.XGFLoader();
    
    // Parallel laden
    await Promise.all([
        xgfLoader.load({ src: xgfUrl, sceneModel }),
        this.loadDataModel(datamodelUrl, dataModel)
    ]);
    
    // Kamera auf Modell ausrichten
    this.cameraFlight.flyTo({ aabb: sceneModel.aabb });
}
```

### 3.3 Data Module Integration

```javascript
// Semantische Abfragen (z.B. alle Türen einer Etage finden)
queryObjects(startObjectId, includeTypes) {
    const resultIds = [];
    
    const result = xeokit.searchObjects(this.data, {
        startObjectId: startObjectId,      // z.B. IfcBuildingStorey GUID
        includeObjects: includeTypes,       // z.B. ["IfcDoor", "IfcWindow"]
        includeRelated: ["IfcRelAggregates", "IfcRelContainedInSpatialStructure"],
        resultObjectIds: resultIds
    });
    
    if (!result.ok) {
        console.error("Query failed:", result.error);
        return [];
    }
    
    return resultIds;
}

// Properties abrufen
getObjectProperties(objectId) {
    const dataObject = this.data.objects[objectId];
    if (!dataObject) return null;
    
    return {
        id: dataObject.id,
        type: dataObject.type,
        name: dataObject.name,
        propertySets: dataObject.propertySets?.map(ps => ({
            name: ps.name,
            properties: ps.properties
        }))
    };
}
```

## 4. TreeView Integration

```javascript
// Modellstruktur-Baum
initTreeView(containerId) {
    this.treeView = new xeokit.TreeViewPlugin(this.viewer, {
        containerElement: document.getElementById(containerId),
        hierarchy: "containment",  // IFC Spatial Structure
        autoExpandDepth: 2
    });
    
    // Klick-Handler
    this.treeView.on("nodeTitleClicked", (e) => {
        const objectId = e.treeViewNode.objectId;
        
        // Im Viewer markieren
        this.view.setObjectsSelected([objectId], true);
        
        // Zur Ansicht fliegen
        this.cameraFlight.flyTo({ 
            aabb: this.scene.objects[objectId].aabb 
        });
        
        // Event für UI
        this.emit("objectSelected", this.getObjectProperties(objectId));
    });
}
```

## 5. BCF Integration (BIM Collaboration)

```javascript
// BCF Viewpoint speichern
saveBCFViewpoint() {
    const bcf = new xeokit.BCFViewpointsPlugin(this.viewer);
    
    return bcf.getViewpoint({
        spacesVisible: false,
        openingsVisible: false,
        spaceBoundariesVisible: false,
        // Snapshot optional
        snapshot: {
            format: "png",
            width: 400,
            height: 300
        }
    });
}

// BCF Viewpoint laden
loadBCFViewpoint(viewpoint) {
    const bcf = new xeokit.BCFViewpointsPlugin(this.viewer);
    bcf.setViewpoint(viewpoint, { duration: 1.0 });
}
```

## 6. Backend Konvertierung

### 6.1 xeoconvert Pipeline

```bash
# Installation
npm install -g @xeokit/xeoconvert

# IFC → XGF (Empfohlen)
xeoconvert --pipeline ifc2xgf \
    --ifc model.ifc \
    --xgf model.xgf \
    --datamodel model.json

# glTF → XGF
xeoconvert --pipeline gltf2xgf \
    --gltf model.gltf \
    --xgf model.xgf

# LAS → XGF (Point Clouds)
xeoconvert --pipeline las2xgf \
    --las pointcloud.las \
    --xgf pointcloud.xgf
```

### 6.2 Python Integration

```python
# services/xgf_converter_service.py
import subprocess
from pathlib import Path

class XGFConverterService:
    """Konvertiert Modelle zu XGF via xeoconvert."""
    
    def convert_ifc_to_xgf(
        self, 
        ifc_path: Path,
        output_dir: Path
    ) -> tuple[Path, Path]:
        """
        Konvertiert IFC zu XGF + DataModelParams.
        
        Returns:
            Tuple von (xgf_path, datamodel_path)
        """
        xgf_path = output_dir / f"{ifc_path.stem}.xgf"
        datamodel_path = output_dir / f"{ifc_path.stem}.json"
        
        cmd = [
            "xeoconvert",
            "--pipeline", "ifc2xgf",
            "--ifc", str(ifc_path),
            "--xgf", str(xgf_path),
            "--datamodel", str(datamodel_path)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Conversion failed: {result.stderr}")
        
        return xgf_path, datamodel_path
```

## 7. Use Cases für CAD-Hub

### 7.1 BIM Model Visualization ✅

- Mehrere Modelle gleichzeitig laden (Federated Models)
- IFC, glTF, LAS/LAZ Support
- Optimierte Konvertierung zu XGF

### 7.2 Interactive Analysis ✅

- **Schnittebenen** (Section Planes)
- **X-Ray Modus** (Durchsichtige Wände)
- **Objekt-Selektion** (Picking)
- **Messung** (Distance Measurement)

### 7.3 BCF Collaboration ✅

- Viewpoints speichern/laden
- Issue Tracking mit 3D-Kontext
- Export für externe BIM-Tools

### 7.4 Semantische Abfragen ✅

- IFC-Typen filtern (Doors, Windows, Walls)
- PropertySets durchsuchen
- Räumliche Hierarchie navigieren

### 7.5 Digital Twin (Zukünftig)

- IoT-Daten mit BIM verknüpfen
- Echtzeit-Updates
- Asset Management

## 8. Empfohlene Paket-Struktur

```
packages/cad-services/
├── src/cad_services/
│   ├── django/
│   │   ├── static/
│   │   │   └── js/
│   │   │       ├── cadhub-viewer-v3.js    # Neuer Viewer
│   │   │       ├── cadhub-treeview.js     # TreeView
│   │   │       └── cadhub-bcf.js          # BCF Support
│   │   └── templates/
│   │       └── cadhub/viewer/
│   │           └── model_viewer_3d.html   # Template
│   └── services/
│       ├── xgf_converter_service.py       # XGF Konvertierung
│       └── model_strategy_service.py      # Lade-Strategie
├── media/
│   ├── ifc/       # Original IFC Dateien
│   └── xgf/       # Konvertierte XGF + JSON
└── package.json   # npm dependencies
```

## 9. npm Dependencies

```json
{
  "dependencies": {
    "@xeokit/xeokit-sdk": "^3.0.0"
  },
  "devDependencies": {
    "@xeokit/xeoconvert": "^3.0.0"
  }
}
```

## 10. Migrations-Plan

### Phase 1: XGF Konvertierung (Sofort)
- [ ] xeoconvert CLI installieren
- [ ] XGFConverterService implementieren
- [ ] Upload-Flow anpassen (Auto-Konvertierung)

### Phase 2: Viewer V3 (Diese Woche)
- [ ] cadhub-viewer-v3.js erstellen
- [ ] Scene + Data Module integrieren
- [ ] XGFLoader implementieren

### Phase 3: TreeView + BCF (Nächste Woche)
- [ ] TreeView Plugin einbinden
- [ ] BCF Viewpoints implementieren
- [ ] Property Panel verbessern

### Phase 4: Advanced Features (Später)
- [ ] Multi-Model Support
- [ ] LAS/LAZ Point Clouds
- [ ] Federated Model Viewing

## 11. Performance-Tipps

1. **Immer XGF verwenden** für Dateien > 20MB
2. **DataModelParams separat laden** (parallel)
3. **TreeView autoExpandDepth: 2** (nicht alle Ebenen)
4. **Lazy Loading** für Properties
5. **WebGL2** bevorzugen (automatisch)
