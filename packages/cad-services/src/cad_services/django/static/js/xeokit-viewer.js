/**
 * xeokit Viewer Controller
 * 
 * Häufigste Use Cases für CAD-Hub:
 * - Modell laden (XKT Format)
 * - Navigation (Orbit, Pan, Zoom)
 * - Objekt-Selektion
 * - Schnittebenen (Section Planes)
 * - Messung (Distance)
 * - Isolieren/Ausblenden
 * - BCF Viewpoints
 */

class CADHubViewer {
    constructor(canvasId, options = {}) {
        this.canvasId = canvasId;
        this.options = {
            backgroundColor: [0.1, 0.1, 0.15],
            saoEnabled: true,
            edgesEnabled: true,
            ...options
        };
        
        this.viewer = null;
        this.model = null;
        this.selectedObjects = [];
        this.sectionPlanes = [];
        this.measurements = [];
        
        this._init();
    }
    
    /**
     * Initialize xeokit Viewer
     */
    _init() {
        // Check if xeokit is loaded
        if (typeof xeokit === 'undefined') {
            console.error('xeokit SDK not loaded');
            return;
        }
        
        this.viewer = new xeokit.Viewer({
            canvasId: this.canvasId,
            transparent: false,
            saoEnabled: this.options.saoEnabled
        });
        
        // Set background
        this.viewer.scene.canvas.backgroundColor = this.options.backgroundColor;
        
        // Enable edges for better visibility
        if (this.options.edgesEnabled) {
            this.viewer.scene.edgeMaterial.edgeColor = [0.3, 0.3, 0.3];
            this.viewer.scene.edgeMaterial.edgeAlpha = 0.5;
        }
        
        // Setup camera
        this.viewer.camera.eye = [10, 10, 10];
        this.viewer.camera.look = [0, 0, 0];
        this.viewer.camera.up = [0, 1, 0];
        
        // Setup input controls
        this._setupControls();
        
        // Setup picking (selection)
        this._setupPicking();
        
        console.log('CADHub Viewer initialized');
    }
    
    /**
     * Setup navigation controls
     */
    _setupControls() {
        // Camera control already enabled by default
        // Configure for better CAD navigation
        const cameraControl = this.viewer.cameraControl;
        
        cameraControl.navMode = "orbit";
        cameraControl.followPointer = true;
        cameraControl.dollyRate = 15;
        cameraControl.panRate = 0.5;
        cameraControl.rotationInertia = 0.5;
    }
    
    /**
     * Setup object picking/selection
     */
    _setupPicking() {
        const viewer = this.viewer;
        const self = this;
        
        viewer.scene.input.on("mouseclicked", (coords) => {
            const hit = viewer.scene.pick({
                canvasPos: coords,
                pickSurface: true
            });
            
            if (hit) {
                const entity = hit.entity;
                self._onObjectPicked(entity, hit);
            } else {
                self._clearSelection();
            }
        });
    }
    
    /**
     * Handle object selection
     */
    _onObjectPicked(entity, hit) {
        // Clear previous selection
        this._clearSelection();
        
        // Highlight selected
        entity.highlighted = true;
        this.selectedObjects.push(entity);
        
        // Dispatch event for UI
        const event = new CustomEvent('objectSelected', {
            detail: {
                id: entity.id,
                name: entity.name || entity.id,
                position: hit.worldPos,
                normal: hit.worldNormal,
                properties: this._getObjectProperties(entity.id)
            }
        });
        document.dispatchEvent(event);
        
        console.log('Selected:', entity.id);
    }
    
    /**
     * Clear selection
     */
    _clearSelection() {
        this.selectedObjects.forEach(entity => {
            entity.highlighted = false;
        });
        this.selectedObjects = [];
        
        document.dispatchEvent(new CustomEvent('selectionCleared'));
    }
    
    // ========== MODEL LOADING ==========
    
    /**
     * Load model - auto-detects format (IFC, XKT, XGF, glTF)
     * @param {string} modelUrl - URL to model file
     * @param {string} metadataUrl - Optional URL to metadata JSON
     * @param {string} format - Optional format hint ('ifc', 'xkt', 'xgf', 'gltf')
     */
    async loadModel(modelUrl, metadataUrl = null, format = null) {
        if (!this.viewer) {
            throw new Error('Viewer not initialized');
        }
        
        // Auto-detect format from URL
        if (!format) {
            const ext = modelUrl.split('.').pop().toLowerCase();
            format = ext;
        }
        
        this._showLoading(true);
        
        try {
            let loader;
            const modelConfig = {
                id: "model",
                edges: this.options.edgesEnabled
            };
            
            switch (format) {
                case 'ifc':
                    // Direct IFC loading (for smaller files <50MB)
                    // Requires web-ifc WASM
                    loader = new xeokit.IFCLoaderPlugin(this.viewer, {
                        wasmPath: '/static/js/web-ifc/'
                    });
                    modelConfig.src = modelUrl;
                    break;
                    
                case 'xgf':
                    // New optimized format (recommended for large files)
                    loader = new xeokit.XGFLoaderPlugin(this.viewer);
                    modelConfig.src = modelUrl;
                    break;
                    
                case 'gltf':
                case 'glb':
                    loader = new xeokit.GLTFLoaderPlugin(this.viewer);
                    modelConfig.src = modelUrl;
                    break;
                    
                case 'xkt':
                default:
                    // Legacy XKT format
                    loader = new xeokit.XKTLoaderPlugin(this.viewer);
                    modelConfig.src = modelUrl;
                    if (metadataUrl) {
                        modelConfig.metaModelSrc = metadataUrl;
                    }
                    break;
            }
            
            this.model = await loader.load(modelConfig);
            
            // Fit model in view
            this.viewer.cameraFlight.flyTo({
                aabb: this.model.aabb,
                duration: 1
            });
            
            console.log(`Model loaded (${format}):`, modelUrl);
            this._updateStats();
            
            return this.model;
            
        } catch (error) {
            console.error('Failed to load model:', error);
            throw error;
        } finally {
            this._showLoading(false);
        }
    }
    
    /**
     * Load IFC directly (small files <50MB)
     * Uses web-ifc WASM for browser-side parsing
     */
    async loadIFC(ifcUrl) {
        return this.loadModel(ifcUrl, null, 'ifc');
    }
    
    /**
     * Load XGF model (optimized format for large files)
     */
    async loadXGF(xgfUrl, metadataUrl = null) {
        return this.loadModel(xgfUrl, metadataUrl, 'xgf');
    }
    
    // ========== NAVIGATION ==========
    
    /**
     * Fit view to model or selection
     */
    fitToView(entityIds = null) {
        if (entityIds && entityIds.length > 0) {
            this.viewer.cameraFlight.flyTo({
                entityIds: entityIds,
                duration: 0.5
            });
        } else if (this.model) {
            this.viewer.cameraFlight.flyTo({
                aabb: this.model.aabb,
                duration: 0.5
            });
        }
    }
    
    /**
     * Set predefined view
     * @param {string} view - "front", "back", "left", "right", "top", "bottom", "iso"
     */
    setView(view) {
        const aabb = this.model ? this.model.aabb : [-10, -10, -10, 10, 10, 10];
        const center = [
            (aabb[0] + aabb[3]) / 2,
            (aabb[1] + aabb[4]) / 2,
            (aabb[2] + aabb[5]) / 2
        ];
        const size = Math.max(aabb[3] - aabb[0], aabb[4] - aabb[1], aabb[5] - aabb[2]);
        const dist = size * 2;
        
        const views = {
            front: { eye: [center[0], center[1], center[2] + dist], up: [0, 1, 0] },
            back: { eye: [center[0], center[1], center[2] - dist], up: [0, 1, 0] },
            left: { eye: [center[0] - dist, center[1], center[2]], up: [0, 1, 0] },
            right: { eye: [center[0] + dist, center[1], center[2]], up: [0, 1, 0] },
            top: { eye: [center[0], center[1] + dist, center[2]], up: [0, 0, -1] },
            bottom: { eye: [center[0], center[1] - dist, center[2]], up: [0, 0, 1] },
            iso: { eye: [center[0] + dist, center[1] + dist, center[2] + dist], up: [0, 1, 0] }
        };
        
        const viewConfig = views[view] || views.iso;
        
        this.viewer.cameraFlight.flyTo({
            look: center,
            eye: viewConfig.eye,
            up: viewConfig.up,
            duration: 0.5
        });
    }
    
    // ========== SECTION PLANES ==========
    
    /**
     * Add section plane
     * @param {string} axis - "x", "y", "z"
     * @param {number} position - Position along axis (0-1 normalized)
     */
    addSectionPlane(axis, position = 0.5) {
        if (!this.model) return null;
        
        const aabb = this.model.aabb;
        const center = [
            (aabb[0] + aabb[3]) / 2,
            (aabb[1] + aabb[4]) / 2,
            (aabb[2] + aabb[5]) / 2
        ];
        
        const directions = {
            x: [1, 0, 0],
            y: [0, 1, 0],
            z: [0, 0, 1]
        };
        
        const axisIndex = { x: 0, y: 1, z: 2 }[axis];
        const pos = [...center];
        pos[axisIndex] = aabb[axisIndex] + (aabb[axisIndex + 3] - aabb[axisIndex]) * position;
        
        const sectionPlane = new xeokit.SectionPlane(this.viewer.scene, {
            pos: pos,
            dir: directions[axis],
            active: true
        });
        
        this.sectionPlanes.push(sectionPlane);
        
        return sectionPlane;
    }
    
    /**
     * Remove all section planes
     */
    clearSectionPlanes() {
        this.sectionPlanes.forEach(plane => plane.destroy());
        this.sectionPlanes = [];
    }
    
    // ========== VISIBILITY ==========
    
    /**
     * Isolate objects (hide everything else)
     * @param {string[]} entityIds - IDs to show
     */
    isolate(entityIds) {
        if (!this.model) return;
        
        // Hide all
        this.viewer.scene.setObjectsVisible(this.viewer.scene.objectIds, false);
        
        // Show selected
        this.viewer.scene.setObjectsVisible(entityIds, true);
        
        // Fit to isolated
        this.fitToView(entityIds);
    }
    
    /**
     * Show all objects
     */
    showAll() {
        if (!this.model) return;
        this.viewer.scene.setObjectsVisible(this.viewer.scene.objectIds, true);
    }
    
    /**
     * Hide specific objects
     */
    hide(entityIds) {
        this.viewer.scene.setObjectsVisible(entityIds, false);
    }
    
    /**
     * Set objects transparency
     */
    setTransparency(entityIds, opacity = 0.3) {
        entityIds.forEach(id => {
            const entity = this.viewer.scene.objects[id];
            if (entity) {
                entity.opacity = opacity;
            }
        });
    }
    
    // ========== MEASUREMENT ==========
    
    /**
     * Enable distance measurement mode
     */
    enableMeasurement() {
        if (!this._distanceMeasurement) {
            this._distanceMeasurement = new xeokit.DistanceMeasurementsPlugin(this.viewer);
        }
        this._distanceMeasurement.control.activate();
    }
    
    /**
     * Disable measurement mode
     */
    disableMeasurement() {
        if (this._distanceMeasurement) {
            this._distanceMeasurement.control.deactivate();
        }
    }
    
    /**
     * Clear all measurements
     */
    clearMeasurements() {
        if (this._distanceMeasurement) {
            this._distanceMeasurement.clear();
        }
    }
    
    // ========== BCF VIEWPOINTS ==========
    
    /**
     * Save current view as BCF viewpoint
     */
    saveBCFViewpoint() {
        if (!this._bcfViewpoints) {
            this._bcfViewpoints = new xeokit.BCFViewpointsPlugin(this.viewer);
        }
        
        return this._bcfViewpoints.getViewpoint({
            spacesVisible: false,
            openingsVisible: false,
            spaceBoundariesVisible: false
        });
    }
    
    /**
     * Restore BCF viewpoint
     */
    loadBCFViewpoint(viewpoint) {
        if (!this._bcfViewpoints) {
            this._bcfViewpoints = new xeokit.BCFViewpointsPlugin(this.viewer);
        }
        
        this._bcfViewpoints.setViewpoint(viewpoint, {
            duration: 0.5
        });
    }
    
    // ========== TREE / STRUCTURE ==========
    
    /**
     * Get model structure tree
     */
    getStructureTree() {
        if (!this.model || !this.model.metaModel) {
            return null;
        }
        
        const metaModel = this.model.metaModel;
        return this._buildTree(metaModel.rootMetaObjects);
    }
    
    _buildTree(metaObjects) {
        return metaObjects.map(metaObject => ({
            id: metaObject.id,
            name: metaObject.name,
            type: metaObject.type,
            children: metaObject.children ? this._buildTree(metaObject.children) : []
        }));
    }
    
    // ========== PROPERTIES ==========
    
    /**
     * Get object properties
     */
    _getObjectProperties(objectId) {
        if (!this.model || !this.model.metaModel) {
            return {};
        }
        
        const metaObject = this.model.metaModel.metaObjects[objectId];
        if (!metaObject) {
            return {};
        }
        
        return {
            id: metaObject.id,
            name: metaObject.name,
            type: metaObject.type,
            parent: metaObject.parent ? metaObject.parent.id : null,
            propertySet: metaObject.propertySet || {}
        };
    }
    
    // ========== UTILITIES ==========
    
    _showLoading(show) {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.style.display = show ? 'flex' : 'none';
        }
    }
    
    _updateStats() {
        const objectCount = document.getElementById('info-objects');
        const triangleCount = document.getElementById('info-triangles');
        
        if (objectCount && this.model) {
            objectCount.textContent = Object.keys(this.viewer.scene.objects).length;
        }
        if (triangleCount && this.viewer.scene.canvas) {
            triangleCount.textContent = this.viewer.scene.canvas.numTriangles || 0;
        }
    }
    
    /**
     * Destroy viewer
     */
    destroy() {
        if (this.viewer) {
            this.viewer.destroy();
            this.viewer = null;
        }
    }
}

// Export for use
window.CADHubViewer = CADHubViewer;
