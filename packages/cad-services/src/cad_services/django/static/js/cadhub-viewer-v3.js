/**
 * CAD-Hub Viewer V3
 * 
 * Basierend auf xeokit SDK v3 mit:
 * - Scene Module (Geometrie)
 * - Data Module (Semantik/Properties)
 * - XGFLoader (optimiertes Format)
 * - TreeView (Modellstruktur)
 * - BCF Support (Collaboration)
 */

// ============================================================
// VIEWER V3 CLASS
// ============================================================

class CADHubViewerV3 {
    constructor(options = {}) {
        this.options = {
            canvasId: 'xeokit-canvas',
            treeViewId: 'model-tree',
            propertyPanelId: 'property-panel',
            backgroundColor: [0.95, 0.95, 0.95],
            edgesEnabled: true,
            saoEnabled: true,
            ...options
        };
        
        // Core components
        this.scene = null;
        this.data = null;
        this.viewer = null;
        this.view = null;
        this.renderer = null;
        
        // Plugins
        this.cameraControl = null;
        this.cameraFlight = null;
        this.treeView = null;
        this.bcf = null;
        
        // State
        this.models = new Map();
        this.selectedObjects = [];
        this.sectionPlanes = [];
        
        // Event emitter
        this._listeners = {};
    }
    
    // ========== INITIALIZATION ==========
    
    async init() {
        if (typeof xeokit === 'undefined') {
            throw new Error('xeokit SDK not loaded. Include @xeokit/xeokit-sdk');
        }
        
        try {
            // 1. Create Scene (geometry container)
            this.scene = new xeokit.Scene();
            
            // 2. Create Data (semantic container)
            this.data = new xeokit.Data();
            
            // 3. Create WebGL Renderer
            this.renderer = new xeokit.WebGLRenderer({});
            
            // 4. Create Viewer
            this.viewer = new xeokit.Viewer({
                id: "cadhub-viewer",
                scene: this.scene,
                renderer: this.renderer
            });
            
            // 5. Create View (canvas + camera)
            this.view = this.viewer.createView({
                id: "mainView",
                canvasId: this.options.canvasId,
                backgroundColor: this.options.backgroundColor
            });
            
            // 6. Camera Control
            this.cameraControl = new xeokit.CameraControl(this.view, {
                navMode: "orbit",
                followPointer: true,
                dollyRate: 15,
                panRate: 0.5
            });
            
            // 7. Camera Flight (animations)
            this.cameraFlight = new xeokit.CameraFlight(this.view, {
                duration: 0.5
            });
            
            // 8. Setup picking
            this._setupPicking();
            
            // 9. Initialize TreeView if container exists
            if (document.getElementById(this.options.treeViewId)) {
                this._initTreeView();
            }
            
            console.log('CAD-Hub Viewer V3 initialized');
            this._emit('initialized');
            
            return this;
            
        } catch (error) {
            console.error('Failed to initialize viewer:', error);
            throw error;
        }
    }
    
    // ========== MODEL LOADING ==========
    
    /**
     * Load model with automatic format detection
     * @param {Object} config - Loading configuration
     * @param {string} config.id - Model ID
     * @param {string} config.src - Model URL
     * @param {string} config.datamodelSrc - DataModel JSON URL (optional)
     * @param {string} config.format - Format hint ('xgf', 'ifc', 'gltf')
     */
    async loadModel(config) {
        const { id, src, datamodelSrc, format } = config;
        
        // Detect format from URL if not specified
        const detectedFormat = format || this._detectFormat(src);
        
        this._showLoading(true, `Loading ${detectedFormat.toUpperCase()}...`);
        
        try {
            // Create SceneModel for geometry
            const sceneModelResult = this.scene.createModel({ id });
            if (!sceneModelResult.ok) {
                throw new Error(`Failed to create SceneModel: ${sceneModelResult.error}`);
            }
            const sceneModel = sceneModelResult.value;
            
            // Create DataModel for semantics
            const dataModelResult = this.data.createModel({ id });
            if (!dataModelResult.ok) {
                throw new Error(`Failed to create DataModel: ${dataModelResult.error}`);
            }
            const dataModel = dataModelResult.value;
            
            // Load based on format
            switch (detectedFormat) {
                case 'xgf':
                    await this._loadXGF(src, datamodelSrc, sceneModel, dataModel);
                    break;
                case 'ifc':
                    await this._loadIFC(src, sceneModel, dataModel);
                    break;
                case 'gltf':
                case 'glb':
                    await this._loadGLTF(src, sceneModel);
                    break;
                default:
                    throw new Error(`Unsupported format: ${detectedFormat}`);
            }
            
            // Store reference
            this.models.set(id, { sceneModel, dataModel, format: detectedFormat });
            
            // Fit to view
            this.fitToModel(id);
            
            // Update tree view
            if (this.treeView) {
                this._updateTreeView();
            }
            
            this._emit('modelLoaded', { id, format: detectedFormat });
            console.log(`Model loaded: ${id} (${detectedFormat})`);
            
            return { sceneModel, dataModel };
            
        } catch (error) {
            console.error('Failed to load model:', error);
            this._emit('error', { message: error.message });
            throw error;
        } finally {
            this._showLoading(false);
        }
    }
    
    async _loadXGF(xgfUrl, datamodelUrl, sceneModel, dataModel) {
        const xgfLoader = new xeokit.XGFLoader();
        
        // Load geometry
        const xgfResponse = await fetch(xgfUrl);
        const xgfData = await xgfResponse.arrayBuffer();
        await xgfLoader.load({ fileData: xgfData, sceneModel });
        
        // Load semantic data if available
        if (datamodelUrl) {
            const datamodelLoader = new xeokit.DataModelParamsLoader();
            const datamodelResponse = await fetch(datamodelUrl);
            const datamodelParams = await datamodelResponse.json();
            await datamodelLoader.load({ dataModelParams: datamodelParams, dataModel });
        }
    }
    
    async _loadIFC(ifcUrl, sceneModel, dataModel) {
        const ifcLoader = new xeokit.IFCLoader({
            wasmPath: this.options.wasmPath || '/static/js/web-ifc/'
        });
        
        const response = await fetch(ifcUrl);
        const fileData = await response.arrayBuffer();
        
        await ifcLoader.load({ fileData, sceneModel, dataModel });
    }
    
    async _loadGLTF(gltfUrl, sceneModel) {
        const gltfLoader = new xeokit.GLTFLoader();
        
        const response = await fetch(gltfUrl);
        const fileData = await response.arrayBuffer();
        
        await gltfLoader.load({ fileData, sceneModel });
    }
    
    _detectFormat(url) {
        const ext = url.split('.').pop().toLowerCase().split('?')[0];
        const formatMap = {
            'xgf': 'xgf',
            'ifc': 'ifc',
            'gltf': 'gltf',
            'glb': 'glb',
            'json': 'xgf'  // Assume XGF if JSON
        };
        return formatMap[ext] || 'xgf';
    }
    
    // ========== NAVIGATION ==========
    
    fitToModel(modelId = null) {
        if (modelId && this.models.has(modelId)) {
            const { sceneModel } = this.models.get(modelId);
            this.cameraFlight.flyTo({ aabb: sceneModel.aabb });
        } else if (this.scene.aabb) {
            this.cameraFlight.flyTo({ aabb: this.scene.aabb });
        }
    }
    
    fitToObjects(objectIds) {
        if (objectIds && objectIds.length > 0) {
            const aabb = this._computeAABB(objectIds);
            if (aabb) {
                this.cameraFlight.flyTo({ aabb });
            }
        }
    }
    
    setView(viewName) {
        const aabb = this.scene.aabb || [-10, -10, -10, 10, 10, 10];
        const center = [
            (aabb[0] + aabb[3]) / 2,
            (aabb[1] + aabb[4]) / 2,
            (aabb[2] + aabb[5]) / 2
        ];
        const size = Math.max(
            aabb[3] - aabb[0],
            aabb[4] - aabb[1],
            aabb[5] - aabb[2]
        );
        const dist = size * 1.5;
        
        const views = {
            front:  { eye: [center[0], center[1], center[2] + dist], up: [0, 1, 0] },
            back:   { eye: [center[0], center[1], center[2] - dist], up: [0, 1, 0] },
            left:   { eye: [center[0] - dist, center[1], center[2]], up: [0, 1, 0] },
            right:  { eye: [center[0] + dist, center[1], center[2]], up: [0, 1, 0] },
            top:    { eye: [center[0], center[1] + dist, center[2]], up: [0, 0, -1] },
            bottom: { eye: [center[0], center[1] - dist, center[2]], up: [0, 0, 1] },
            iso:    { eye: [center[0] + dist * 0.7, center[1] + dist * 0.7, center[2] + dist * 0.7], up: [0, 1, 0] }
        };
        
        const viewConfig = views[viewName] || views.iso;
        this.cameraFlight.flyTo({
            look: center,
            eye: viewConfig.eye,
            up: viewConfig.up
        });
    }
    
    // ========== SELECTION ==========
    
    _setupPicking() {
        const picker = new xeokit.Picker(this.scene);
        
        this.view.canvas.canvas.addEventListener('click', (e) => {
            const hit = picker.pick({
                canvasPos: [e.offsetX, e.offsetY],
                pickSurface: true
            });
            
            if (hit) {
                this._onObjectPicked(hit);
            } else {
                this.clearSelection();
            }
        });
    }
    
    _onObjectPicked(hit) {
        const objectId = hit.entity?.id;
        if (!objectId) return;
        
        // Clear previous selection
        this.clearSelection();
        
        // Highlight new selection
        const sceneObject = this.scene.objects[objectId];
        if (sceneObject) {
            sceneObject.highlighted = true;
            this.selectedObjects.push(objectId);
        }
        
        // Get properties from Data module
        const properties = this.getObjectProperties(objectId);
        
        // Emit event
        this._emit('objectSelected', { objectId, properties, hit });
        
        // Update property panel
        this._updatePropertyPanel(properties);
    }
    
    clearSelection() {
        this.selectedObjects.forEach(id => {
            const obj = this.scene.objects[id];
            if (obj) obj.highlighted = false;
        });
        this.selectedObjects = [];
        this._emit('selectionCleared');
    }
    
    selectObjects(objectIds, additive = false) {
        if (!additive) this.clearSelection();
        
        objectIds.forEach(id => {
            const obj = this.scene.objects[id];
            if (obj) {
                obj.highlighted = true;
                this.selectedObjects.push(id);
            }
        });
        
        this._emit('objectsSelected', { objectIds });
    }
    
    // ========== SEMANTIC QUERIES ==========
    
    getObjectProperties(objectId) {
        const dataObject = this.data.objects[objectId];
        if (!dataObject) {
            return { id: objectId, type: 'Unknown', note: 'Not in DataModel' };
        }
        
        const properties = {
            id: dataObject.id,
            type: dataObject.type,
            name: dataObject.name,
            propertySets: []
        };
        
        // Get property sets
        if (dataObject.propertySets) {
            dataObject.propertySets.forEach(ps => {
                properties.propertySets.push({
                    name: ps.name,
                    properties: ps.properties || {}
                });
            });
        }
        
        return properties;
    }
    
    /**
     * Query objects by IFC type within a spatial element
     * @param {string} startObjectId - Starting object (e.g., IfcBuildingStorey)
     * @param {string[]} includeTypes - IFC types to find (e.g., ['IfcDoor', 'IfcWindow'])
     */
    queryObjects(startObjectId, includeTypes) {
        const resultIds = [];
        
        const result = xeokit.searchObjects(this.data, {
            startObjectId,
            includeObjects: includeTypes,
            includeRelated: ['IfcRelAggregates', 'IfcRelContainedInSpatialStructure'],
            resultObjectIds: resultIds
        });
        
        if (!result.ok) {
            console.error('Query failed:', result.error);
            return [];
        }
        
        return resultIds;
    }
    
    // ========== VISIBILITY ==========
    
    showAll() {
        Object.values(this.scene.objects).forEach(obj => {
            obj.visible = true;
            obj.xrayed = false;
        });
    }
    
    hideObjects(objectIds) {
        objectIds.forEach(id => {
            const obj = this.scene.objects[id];
            if (obj) obj.visible = false;
        });
    }
    
    isolateObjects(objectIds) {
        // Hide all
        Object.values(this.scene.objects).forEach(obj => {
            obj.visible = false;
        });
        
        // Show selected
        objectIds.forEach(id => {
            const obj = this.scene.objects[id];
            if (obj) obj.visible = true;
        });
        
        // Fit to isolated
        this.fitToObjects(objectIds);
    }
    
    xrayAll(except = []) {
        Object.entries(this.scene.objects).forEach(([id, obj]) => {
            obj.xrayed = !except.includes(id);
        });
    }
    
    // ========== SECTION PLANES ==========
    
    addSectionPlane(axis, position = 0.5) {
        const aabb = this.scene.aabb;
        if (!aabb) return null;
        
        const center = [
            (aabb[0] + aabb[3]) / 2,
            (aabb[1] + aabb[4]) / 2,
            (aabb[2] + aabb[5]) / 2
        ];
        
        const directions = { x: [1, 0, 0], y: [0, 1, 0], z: [0, 0, 1] };
        const axisIndex = { x: 0, y: 1, z: 2 }[axis];
        
        const pos = [...center];
        pos[axisIndex] = aabb[axisIndex] + (aabb[axisIndex + 3] - aabb[axisIndex]) * position;
        
        const sectionPlane = new xeokit.SectionPlane(this.scene, {
            pos,
            dir: directions[axis],
            active: true
        });
        
        this.sectionPlanes.push(sectionPlane);
        return sectionPlane;
    }
    
    clearSectionPlanes() {
        this.sectionPlanes.forEach(sp => sp.destroy());
        this.sectionPlanes = [];
    }
    
    // ========== BCF VIEWPOINTS ==========
    
    saveBCFViewpoint(options = {}) {
        if (!this.bcf) {
            this.bcf = new xeokit.BCFViewpointsPlugin(this.viewer);
        }
        
        return this.bcf.getViewpoint({
            spacesVisible: false,
            openingsVisible: false,
            spaceBoundariesVisible: false,
            ...options
        });
    }
    
    loadBCFViewpoint(viewpoint) {
        if (!this.bcf) {
            this.bcf = new xeokit.BCFViewpointsPlugin(this.viewer);
        }
        
        this.bcf.setViewpoint(viewpoint, { duration: 0.5 });
    }
    
    // ========== TREE VIEW ==========
    
    _initTreeView() {
        const container = document.getElementById(this.options.treeViewId);
        if (!container) return;
        
        this.treeView = new xeokit.TreeViewPlugin(this.viewer, {
            containerElement: container,
            hierarchy: "containment",
            autoExpandDepth: 2
        });
        
        this.treeView.on("nodeTitleClicked", (e) => {
            const objectId = e.treeViewNode.objectId;
            if (objectId) {
                this.selectObjects([objectId]);
                this.fitToObjects([objectId]);
            }
        });
    }
    
    _updateTreeView() {
        // TreeView updates automatically when models are loaded
    }
    
    // ========== PROPERTY PANEL ==========
    
    _updatePropertyPanel(properties) {
        const panel = document.getElementById(this.options.propertyPanelId);
        if (!panel) return;
        
        let html = '<table class="table table-sm table-borderless mb-0">';
        
        // Basic properties
        html += `<tr><th class="text-muted">ID</th><td>${properties.id}</td></tr>`;
        html += `<tr><th class="text-muted">Type</th><td>${properties.type}</td></tr>`;
        if (properties.name) {
            html += `<tr><th class="text-muted">Name</th><td>${properties.name}</td></tr>`;
        }
        
        // Property sets
        if (properties.propertySets && properties.propertySets.length > 0) {
            properties.propertySets.forEach(ps => {
                html += `<tr><th colspan="2" class="bg-light">${ps.name}</th></tr>`;
                Object.entries(ps.properties || {}).forEach(([key, value]) => {
                    html += `<tr><th class="text-muted ps-3">${key}</th><td>${value}</td></tr>`;
                });
            });
        }
        
        html += '</table>';
        panel.innerHTML = html;
    }
    
    // ========== UTILITIES ==========
    
    _computeAABB(objectIds) {
        let minX = Infinity, minY = Infinity, minZ = Infinity;
        let maxX = -Infinity, maxY = -Infinity, maxZ = -Infinity;
        
        objectIds.forEach(id => {
            const obj = this.scene.objects[id];
            if (obj && obj.aabb) {
                minX = Math.min(minX, obj.aabb[0]);
                minY = Math.min(minY, obj.aabb[1]);
                minZ = Math.min(minZ, obj.aabb[2]);
                maxX = Math.max(maxX, obj.aabb[3]);
                maxY = Math.max(maxY, obj.aabb[4]);
                maxZ = Math.max(maxZ, obj.aabb[5]);
            }
        });
        
        if (minX === Infinity) return null;
        return [minX, minY, minZ, maxX, maxY, maxZ];
    }
    
    _showLoading(show, message = 'Loading...') {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.style.display = show ? 'flex' : 'none';
            const msgEl = overlay.querySelector('.loading-message');
            if (msgEl) msgEl.textContent = message;
        }
    }
    
    // ========== EVENTS ==========
    
    on(event, callback) {
        if (!this._listeners[event]) {
            this._listeners[event] = [];
        }
        this._listeners[event].push(callback);
    }
    
    off(event, callback) {
        if (this._listeners[event]) {
            this._listeners[event] = this._listeners[event].filter(cb => cb !== callback);
        }
    }
    
    _emit(event, data = {}) {
        if (this._listeners[event]) {
            this._listeners[event].forEach(cb => cb(data));
        }
    }
    
    // ========== CLEANUP ==========
    
    destroy() {
        this.clearSectionPlanes();
        if (this.treeView) this.treeView.destroy();
        if (this.viewer) this.viewer.destroy();
        
        this.scene = null;
        this.data = null;
        this.viewer = null;
        this.view = null;
    }
}

// ============================================================
// EXPORT
// ============================================================

window.CADHubViewerV3 = CADHubViewerV3;

// Module export for bundlers
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { CADHubViewerV3 };
}
