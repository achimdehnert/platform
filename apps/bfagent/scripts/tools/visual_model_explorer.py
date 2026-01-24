#!/usr/bin/env python
"""
Visual Model Explorer for BF Agent v2.0.0
Interactive web-based UI for model exploration and CRUDConfig editing
"""
import os
from datetime import datetime

import django
from django.apps import apps
from django.db import models
from flask_cors import CORS

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()


class ModelExplorer:
    """Model exploration and analysis engine"""

    def __init__(self):
        """Function description."""
        self.models = {}
        self.relationships = []
        self.app_name = "bfagent"

    def scan_models(self):
        """Scan all models and their relationships"""
        try:
            app_config = apps.get_app_config(self.app_name)

            for model in app_config.get_models():
                model_data = self._analyze_model(model)
                self.models[model.__name__] = model_data

            # Build relationship graph
            self._build_relationships()

        except Exception as e:
            print(f"Error scanning models: {e}")

    def _analyze_model(self, model) -> Dict[str, Any]:
        """Analyze a single model"""
        model_data = {
            "name": model.__name__,
            "app": model._meta.app_label,
            "db_table": model._meta.db_table,
            "verbose_name": str(model._meta.verbose_name),
            "verbose_name_plural": str(model._meta.verbose_name_plural),
            "fields": {},
            "relationships": [],
            "methods": [],
            "properties": [],
            "has_crud_config": hasattr(model, "CRUDConfig"),
            "crud_config": None,
            "field_count": 0,
            "relationship_count": 0,
        }

        # Analyze fields
        for field in model._meta.get_fields():
            field_info = {
                "name": field.name,
                "type": field.__class__.__name__,
                "verbose_name": getattr(field, "verbose_name", field.name),
                "help_text": getattr(field, "help_text", ""),
                "max_length": getattr(field, "max_length", None),
                "null": getattr(field, "null", False),
                "blank": getattr(field, "blank", False),
                "default": str(getattr(field, "default", None)),
                "choices": getattr(field, "choices", None),
                "db_index": getattr(field, "db_index", False),
                "unique": getattr(field, "unique", False),
            }

            # Handle relationships
            if isinstance(field, (models.ForeignKey, models.ManyToManyField, models.OneToOneField)):
                related_model = field.related_model
                relationship_info = {
                    "field": field.name,
                    "type": field.__class__.__name__,
                    "related_model": related_model.__name__,
                    "related_app": related_model._meta.app_label,
                    "related_name": getattr(field, "related_name", None),
                    "on_delete": (
                        getattr(field, "on_delete", None).__name__
                        if hasattr(field, "on_delete")
                        else None
                    ),
                }
                model_data["relationships"].append(relationship_info)
                model_data["relationship_count"] += 1

            model_data["fields"][field.name] = field_info
            model_data["field_count"] += 1

        # Analyze CRUDConfig
        if model_data["has_crud_config"]:
            crud_config = model.CRUDConfig
            model_data["crud_config"] = {
                "list_display": getattr(crud_config, "list_display", []),
                "list_filter": getattr(crud_config, "list_filter", []),
                "search_fields": getattr(crud_config, "search_fields", []),
                "ordering": getattr(crud_config, "ordering", []),
                "form_fields": getattr(crud_config, "form_fields", []),
                "form_layout": getattr(crud_config, "form_layout", {}),
                "readonly_fields": getattr(crud_config, "readonly_fields", []),
                "actions": getattr(crud_config, "actions", {}),
                "htmx_config": getattr(crud_config, "htmx_config", {}),
                "permissions": getattr(crud_config, "permissions", {}),
            }

        # Analyze methods and properties
        for attr_name in dir(model):
            if not attr_name.startswith("_"):
                attr = getattr(model, attr_name, None)
                if callable(attr) and not isinstance(attr, type):
                    model_data["methods"].append(attr_name)
                elif isinstance(attr, property):
                    model_data["properties"].append(attr_name)

        return model_data

    def _build_relationships(self):
        """Build relationship graph data"""
        for model_name, model_data in self.models.items():
            for rel in model_data["relationships"]:
                self.relationships.append(
                    {
                        "source": model_name,
                        "target": rel["related_model"],
                        "type": rel["type"],
                        "field": rel["field"],
                        "label": f"{rel['field']} ({rel['type']})",
                    }
                )

    def get_model_graph_data(self):
        """Get data for D3.js visualization"""
        nodes = []
        links = []

        # Create nodes
        for model_name, model_data in self.models.items():
            nodes.append(
                {
                    "id": model_name,
                    "name": model_name,
                    "group": 1 if model_data["has_crud_config"] else 2,
                    "field_count": model_data["field_count"],
                    "relationship_count": model_data["relationship_count"],
                    "has_crud": model_data["has_crud_config"],
                }
            )

        # Create links
        for rel in self.relationships:
            # Only add if both nodes exist
            if rel["source"] in self.models and rel["target"] in self.models:
                links.append(
                    {
                        "source": rel["source"],
                        "target": rel["target"],
                        "type": rel["type"],
                        "label": rel["label"],
                        "value": 1,
                    }
                )

        return {"nodes": nodes, "links": links}

    def update_crud_config(self, model_name: str, config_data: Dict[str, Any]) -> bool:
        """Update CRUDConfig for a model (simulation)"""
        # This would actually update the model's CRUDConfig
        # For now, we just validate the data
        if model_name not in self.models:
            return False

        model_data = self.models[model_name]
        field_names = set(model_data["fields"].keys())

        # Validate fields in config
        for field_list_name in ["list_display", "list_filter", "search_fields", "form_fields"]:
            if field_list_name in config_data:
                invalid_fields = [
                    f
                    for f in config_data[field_list_name]
                    if f
                    and f not in field_names
                    and f not in model_data["methods"]
                    and f not in model_data["properties"]
                ]
                if invalid_fields:
                    return False

        return True


# Flask application
app = Flask(__name__)
CORS(app)
explorer = ModelExplorer()


# HTML template with embedded JavaScript
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>BF Agent Model Explorer</title>
    <meta charset="utf-8">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 0;
            background: #f5f5f5;
        }

        .header {
            background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
            color: white;
            padding: 1rem 2rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .container {
            display: flex;
            height: calc(100vh - 80px);
        }

        .sidebar {
            width: 300px;
            background: white;
            border-right: 1px solid #ddd;
            overflow-y: auto;
            padding: 1rem;
        }

        .main-content {
            flex: 1;
            display: flex;
            flex-direction: column;
        }

        .visualization {
            flex: 1;
            background: white;
            margin: 1rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            position: relative;
        }

        .model-details {
            height: 300px;
            background: white;
            margin: 0 1rem 1rem 1rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            padding: 1rem;
            overflow-y: auto;
        }

        .model-item {
            padding: 0.5rem;
            margin: 0.25rem 0;
            cursor: pointer;
            border-radius: 4px;
            transition: all 0.2s;
        }

        .model-item:hover {
            background: #f0f0f0;
        }

        .model-item.selected {
            background: #007bff;
            color: white;
        }

        .model-item.has-crud::after {
            content: "✓";
            float: right;
            color: #28a745;
        }

        .model-item.selected.has-crud::after {
            color: white;
        }

        .stats {
            display: flex;
            gap: 1rem;
            margin-bottom: 1rem;
        }

        .stat-card {
            background: white;
            padding: 1rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
            flex: 1;
        }

        .stat-value {
            font-size: 2rem;
            font-weight: bold;
            color: #007bff;
        }

        .stat-label {
            color: #666;
            font-size: 0.9rem;
        }

        /* Graph styles */
        .node {
            cursor: pointer;
        }

        .node circle {
            stroke: #fff;
            stroke-width: 2px;
        }

        .node text {
            font: 12px sans-serif;
            pointer-events: none;
            text-anchor: middle;
            fill: #333;
        }

        .link {
            fill: none;
            stroke: #999;
            stroke-width: 2px;
            stroke-opacity: 0.6;
        }

        .link.ForeignKey {
            stroke: #007bff;
        }

        .link.ManyToManyField {
            stroke: #28a745;
            stroke-dasharray: 5,5;
        }

        .link.OneToOneField {
            stroke: #dc3545;
        }

        .link-label {
            font: 10px sans-serif;
            fill: #666;
        }

        /* Tabs */
        .tabs {
            display: flex;
            border-bottom: 2px solid #ddd;
            margin-bottom: 1rem;
        }

        .tab {
            padding: 0.5rem 1rem;
            cursor: pointer;
            border-bottom: 2px solid transparent;
            transition: all 0.2s;
        }

        .tab:hover {
            background: #f0f0f0;
        }

        .tab.active {
            border-bottom-color: #007bff;
            color: #007bff;
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
        }

        /* Forms */
        .field-group {
            margin-bottom: 1rem;
        }

        .field-group label {
            display: block;
            margin-bottom: 0.25rem;
            font-weight: 500;
        }

        .field-group input, .field-group select {
            width: 100%;
            padding: 0.5rem;
            border: 1px solid #ddd;
            border-radius: 4px;
        }

        .field-list {
            max-height: 150px;
            overflow-y: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 0.5rem;
        }

        .field-checkbox {
            margin: 0.25rem 0;
        }

        .btn {
            background: #007bff;
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            cursor: pointer;
            transition: background 0.2s;
        }

        .btn:hover {
            background: #0056b3;
        }

        .btn-success {
            background: #28a745;
        }

        .btn-success:hover {
            background: #218838;
        }

        /* Field table */
        .field-table {
            width: 100%;
            border-collapse: collapse;
        }

        .field-table th {
            background: #f8f9fa;
            padding: 0.5rem;
            text-align: left;
            border-bottom: 2px solid #ddd;
        }

        .field-table td {
            padding: 0.5rem;
            border-bottom: 1px solid #eee;
        }

        .field-type {
            background: #e9ecef;
            padding: 0.125rem 0.5rem;
            border-radius: 12px;
            font-size: 0.85rem;
        }

        .tooltip {
            position: absolute;
            text-align: center;
            padding: 8px;
            font: 12px sans-serif;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            border-radius: 4px;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.2s;
        }
    </style>
    <script src="https://d3js.org/d3.v7.min.js"></script>
</head>
<body>
    <div class="header">
        <h1>🔍 BF Agent Model Explorer</h1>
        <p style="margin: 0; opacity: 0.8;">Interactive visualization and CRUDConfig editor</p>
    </div>

    <div class="stats" style="padding: 1rem;">
        <div class="stat-card">
            <div class="stat-value" id="total-models">0</div>
            <div class="stat-label">Total Models</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" id="crud-models">0</div>
            <div class="stat-label">With CRUDConfig</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" id="total-relationships">0</div>
            <div class="stat-label">Relationships</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" id="total-fields">0</div>
            <div class="stat-label">Total Fields</div>
        </div>
    </div>

    <div class="container">
        <div class="sidebar">
            <h3>Models</h3>
            <input type="text" id="model-search" placeholder="Search models..." style="width: 100%; padding: 0.5rem; margin-bottom: 1rem;">
            <div id="model-list"></div>
        </div>

        <div class="main-content">
            <div class="visualization" id="graph-container">
                <div style="position: absolute; top: 10px; right: 10px; z-index: 10;">
                    <button class="btn" onclick="resetZoom()">Reset View</button>
                    <button class="btn" onclick="toggleForceLayout()">Toggle Physics</button>
                </div>
                <svg id="graph"></svg>
            </div>

            <div class="model-details">
                <div class="tabs">
                    <div class="tab active" onclick="switchTab('fields')">Fields</div>
                    <div class="tab" onclick="switchTab('crud')">CRUDConfig</div>
                    <div class="tab" onclick="switchTab('relationships')">Relationships</div>
                    <div class="tab" onclick="switchTab('methods')">Methods & Properties</div>
                </div>

                <div id="fields-tab" class="tab-content active">
                    <h4>Model Fields</h4>
                    <div id="fields-content">Select a model to view fields</div>
                </div>

                <div id="crud-tab" class="tab-content">
                    <h4>CRUDConfig Editor</h4>
                    <div id="crud-content">Select a model to edit CRUDConfig</div>
                </div>

                <div id="relationships-tab" class="tab-content">
                    <h4>Relationships</h4>
                    <div id="relationships-content">Select a model to view relationships</div>
                </div>

                <div id="methods-tab" class="tab-content">
                    <h4>Methods & Properties</h4>
                    <div id="methods-content">Select a model to view methods</div>
                </div>
            </div>
        </div>
    </div>

    <div class="tooltip"></div>

    <script>
        let graphData = null;
        let selectedModel = null;
        let simulation = null;
        let svg = null;
        let g = null;
        let forceEnabled = true;

        // Initialize
        async function init() {
            // Load data
            const response = await fetch('/api/models');
            const data = await response.json();

            // Update stats
            document.getElementById('total-models').textContent = data.stats.total_models;
            document.getElementById('crud-models').textContent = data.stats.models_with_crud;
            document.getElementById('total-relationships').textContent = data.stats.total_relationships;
            document.getElementById('total-fields').textContent = data.stats.total_fields;

            // Render model list
            renderModelList(data.models);

            // Load graph data
            const graphResponse = await fetch('/api/graph');
            graphData = await graphResponse.json();

            // Render graph
            renderGraph();
        }

        function renderModelList(models) {
            const modelList = document.getElementById('model-list');
            modelList.innerHTML = '';

            Object.entries(models).forEach(([name, model]) => {
                const div = document.createElement('div');
                div.className = 'model-item';
                if (model.has_crud_config) {
                    div.className += ' has-crud';
                }
                div.textContent = name;
                div.onclick = () => selectModel(name);
                modelList.appendChild(div);
            });
        }

        async function selectModel(modelName) {
            // Update selection
            document.querySelectorAll('.model-item').forEach(item => {
                item.classList.remove('selected');
                if (item.textContent === modelName) {
                    item.classList.add('selected');
                }
            });

            selectedModel = modelName;

            // Load model details
            const response = await fetch(`/api/model/${modelName}`);
            const model = await response.json();

            // Update all tabs
            updateFieldsTab(model);
            updateCrudTab(model);
            updateRelationshipsTab(model);
            updateMethodsTab(model);

            // Highlight in graph
            highlightNode(modelName);
        }

        function updateFieldsTab(model) {
            const content = document.getElementById('fields-content');

            let html = '<table class="field-table"><thead><tr>';
            html += '<th>Field Name</th><th>Type</th><th>Required</th><th>Indexed</th>';
            html += '</tr></thead><tbody>';

            Object.entries(model.fields).forEach(([name, field]) => {
                html += '<tr>';
                html += `<td><strong>${name}</strong><br><small>${field.verbose_name}</small></td>`;
                html += `<td><span class="field-type">${field.type}</span></td>`;
                html += `<td>${!field.blank ? '✓' : ''}</td>`;
                html += `<td>${field.db_index ? '✓' : ''}</td>`;
                html += '</tr>';
            });

            html += '</tbody></table>';
            content.innerHTML = html;
        }

        function updateCrudTab(model) {
            const content = document.getElementById('crud-content');

            if (!model.has_crud_config) {
                content.innerHTML = '<p>This model does not have a CRUDConfig. <button class="btn" onclick="createCrudConfig()">Create CRUDConfig</button></p>';
                return;
            }

            let html = '<form id="crud-form">';

            // List Display
            html += '<div class="field-group">';
            html += '<label>List Display Fields:</label>';
            html += '<div class="field-list">';
            Object.keys(model.fields).forEach(field => {
                const checked = model.crud_config.list_display.includes(field) ? 'checked' : '';
                html += `<div class="field-checkbox">`;
                html += `<label><input type="checkbox" name="list_display" value="${field}" ${checked}> ${field}</label>`;
                html += `</div>`;
            });
            html += '</div></div>';

            // Search Fields
            html += '<div class="field-group">';
            html += '<label>Search Fields:</label>';
            html += '<div class="field-list">';
            Object.keys(model.fields).forEach(field => {
                const checked = model.crud_config.search_fields.includes(field) ? 'checked' : '';
                html += `<div class="field-checkbox">`;
                html += `<label><input type="checkbox" name="search_fields" value="${field}" ${checked}> ${field}</label>`;
                html += `</div>`;
            });
            html += '</div></div>';

            // List Filters
            html += '<div class="field-group">';
            html += '<label>List Filters:</label>';
            html += '<div class="field-list">';
            Object.keys(model.fields).forEach(field => {
                const checked = model.crud_config.list_filter.includes(field) ? 'checked' : '';
                html += `<div class="field-checkbox">`;
                html += `<label><input type="checkbox" name="list_filter" value="${field}" ${checked}> ${field}</label>`;
                html += `</div>`;
            });
            html += '</div></div>';

            html += '<button type="button" class="btn btn-success" onclick="saveCrudConfig()">Save CRUDConfig</button>';
            html += '</form>';

            content.innerHTML = html;
        }

        function updateRelationshipsTab(model) {
            const content = document.getElementById('relationships-content');

            if (model.relationships.length === 0) {
                content.innerHTML = '<p>No relationships defined.</p>';
                return;
            }

            let html = '<table class="field-table"><thead><tr>';
            html += '<th>Field</th><th>Type</th><th>Related Model</th><th>Related Name</th>';
            html += '</tr></thead><tbody>';

            model.relationships.forEach(rel => {
                html += '<tr>';
                html += `<td>${rel.field}</td>`;
                html += `<td><span class="field-type">${rel.type}</span></td>`;
                html += `<td>${rel.related_model}</td>`;
                html += `<td>${rel.related_name || '-'}</td>`;
                html += '</tr>';
            });

            html += '</tbody></table>';
            content.innerHTML = html;
        }

        function updateMethodsTab(model) {
            const content = document.getElementById('methods-content');

            let html = '';

            if (model.methods.length > 0) {
                html += '<h5>Methods:</h5><ul>';
                model.methods.forEach(method => {
                    html += `<li>${method}()</li>`;
                });
                html += '</ul>';
            }

            if (model.properties.length > 0) {
                html += '<h5>Properties:</h5><ul>';
                model.properties.forEach(prop => {
                    html += `<li>@property ${prop}</li>`;
                });
                html += '</ul>';
            }

            if (!model.methods.length && !model.properties.length) {
                html = '<p>No custom methods or properties.</p>';
            }

            content.innerHTML = html;
        }

        function switchTab(tabName) {
            // Update active tab
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            event.target.classList.add('active');

            // Update content
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            document.getElementById(`${tabName}-tab`).classList.add('active');
        }

        function renderGraph() {
            const container = document.getElementById('graph-container');
            const width = container.clientWidth;
            const height = container.clientHeight;

            // Create SVG
            svg = d3.select('#graph')
                .attr('width', width)
                .attr('height', height);

            // Create group for zoom
            g = svg.append('g');

            // Define arrow markers
            svg.append('defs').selectAll('marker')
                .data(['ForeignKey', 'ManyToManyField', 'OneToOneField'])
                .enter().append('marker')
                .attr('id', d => `arrow-${d}`)
                .attr('viewBox', '0 -5 10 10')
                .attr('refX', 30)
                .attr('refY', 0)
                .attr('markerWidth', 6)
                .attr('markerHeight', 6)
                .attr('orient', 'auto')
                .append('path')
                .attr('d', 'M0,-5L10,0L0,5')
                .attr('fill', d => {
                    const colors = {
                        'ForeignKey': '#007bf',
                        'ManyToManyField': '#28a745',
                        'OneToOneField': '#dc3545'
                    };
                    return colors[d];
                });

            // Create zoom behavior
            const zoom = d3.zoom()
                .scaleExtent([0.1, 4])
                .on('zoom', (event) => {
                    g.attr('transform', event.transform);
                });

            svg.call(zoom);

            // Create simulation
            simulation = d3.forceSimulation(graphData.nodes)
                .force('link', d3.forceLink(graphData.links).id(d => d.id).distance(150))
                .force('charge', d3.forceManyBody().strength(-500))
                .force('center', d3.forceCenter(width / 2, height / 2))
                .force('collision', d3.forceCollide().radius(40));

            // Create links
            const link = g.append('g')
                .attr('class', 'links')
                .selectAll('line')
                .data(graphData.links)
                .enter().append('line')
                .attr('class', d => `link ${d.type}`)
                .attr('marker-end', d => `url(#arrow-${d.type})`);

            // Create link labels
            const linkLabel = g.append('g')
                .attr('class', 'link-labels')
                .selectAll('text')
                .data(graphData.links)
                .enter().append('text')
                .attr('class', 'link-label')
                .text(d => d.label);

            // Create nodes
            const node = g.append('g')
                .attr('class', 'nodes')
                .selectAll('g')
                .data(graphData.nodes)
                .enter().append('g')
                .attr('class', 'node')
                .call(drag(simulation));

            // Add circles
            node.append('circle')
                .attr('r', d => 20 + Math.sqrt(d.field_count) * 2)
                .attr('fill', d => d.has_crud ? '#007bf' : '#dc3545')
                .on('click', (event, d) => selectModel(d.id));

            // Add labels
            node.append('text')
                .text(d => d.name)
                .attr('y', d => 25 + Math.sqrt(d.field_count) * 2);

            // Add tooltips
            const tooltip = d3.select('.tooltip');

            node.on('mouseover', (event, d) => {
                tooltip.transition().duration(200).style('opacity', .9);
                tooltip.html(`<strong>${d.name}</strong><br>Fields: ${d.field_count}<br>Relations: ${d.relationship_count}`)
                    .style('left', (event.pageX + 10) + 'px')
                    .style('top', (event.pageY - 28) + 'px');
            })
            .on('mouseout', () => {
                tooltip.transition().duration(500).style('opacity', 0);
            });

            // Update positions on tick
            simulation.on('tick', () => {
                link
                    .attr('x1', d => d.source.x)
                    .attr('y1', d => d.source.y)
                    .attr('x2', d => d.target.x)
                    .attr('y2', d => d.target.y);

                linkLabel
                    .attr('x', d => (d.source.x + d.target.x) / 2)
                    .attr('y', d => (d.source.y + d.target.y) / 2);

                node.attr('transform', d => `translate(${d.x},${d.y})`);
            });
        }

        function drag(simulation) {
            function dragstarted(event) {
                if (!event.active) simulation.alphaTarget(0.3).restart();
                event.subject.fx = event.subject.x;
                event.subject.fy = event.subject.y;
            }

            function dragged(event) {
                event.subject.fx = event.x;
                event.subject.fy = event.y;
            }

            function dragended(event) {
                if (!event.active) simulation.alphaTarget(0);
                event.subject.fx = null;
                event.subject.fy = null;
            }

            return d3.drag()
                .on('start', dragstarted)
                .on('drag', dragged)
                .on('end', dragended);
        }

        function highlightNode(modelName) {
            d3.selectAll('.node circle')
                .style('stroke-width', d => d.id === modelName ? 4 : 2)
                .style('stroke', d => d.id === modelName ? '#ffc107' : '#fff');
        }

        function resetZoom() {
            svg.transition().duration(750).call(
                d3.zoom().transform,
                d3.zoomIdentity
            );
        }

        function toggleForceLayout() {
            forceEnabled = !forceEnabled;
            if (forceEnabled) {
                simulation.restart();
            } else {
                simulation.stop();
            }
        }

        async function saveCrudConfig() {
            const form = document.getElementById('crud-form');
            const formData = new FormData(form);

            const config = {
                list_display: formData.getAll('list_display'),
                search_fields: formData.getAll('search_fields'),
                list_filter: formData.getAll('list_filter')
            };

            const response = await fetch(`/api/model/${selectedModel}/crud`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(config)
            });

            if (response.ok) {
                alert('CRUDConfig saved successfully!');
            } else {
                alert('Error saving CRUDConfig');
            }
        }

        // Search functionality
        document.getElementById('model-search').addEventListener('input', (e) => {
            const search = e.target.value.toLowerCase();
            document.querySelectorAll('.model-item').forEach(item => {
                const show = item.textContent.toLowerCase().includes(search);
                item.style.display = show ? 'block' : 'none';
            });
        });

        // Initialize on load
        window.addEventListener('load', init);
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    """Serve the main HTML page"""
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/models")
def get_models():
    """Get all models data"""
    explorer.scan_models()

    stats = {
        "total_models": len(explorer.models),
        "models_with_crud": sum(1 for m in explorer.models.values() if m["has_crud_config"]),
        "total_relationships": len(explorer.relationships),
        "total_fields": sum(m["field_count"] for m in explorer.models.values()),
    }

    return jsonify({"models": explorer.models, "stats": stats})


@app.route("/api/model/<model_name>")
def get_model(model_name):
    """Get single model details"""
    if model_name not in explorer.models:
        explorer.scan_models()

    if model_name in explorer.models:
        return jsonify(explorer.models[model_name])
    else:
        return jsonify({"error": "Model not found"}), 404


@app.route("/api/model/<model_name>/crud", methods=["POST"])
def update_crud_config(model_name):
    """Update CRUDConfig for a model"""
    data = request.json

    if explorer.update_crud_config(model_name, data):
        return jsonify({"status": "success"})
    else:
        return jsonify({"error": "Invalid configuration"}), 400


@app.route("/api/graph")
def get_graph():
    """Get graph visualization data"""
    if not explorer.models:
        explorer.scan_models()

    return jsonify(explorer.get_model_graph_data())


@app.route("/api/export/<format>")
def export_data(format):
    """Export model data in various formats"""
    if not explorer.models:
        explorer.scan_models()

    if format == "json":
        return jsonify(
            {
                "models": explorer.models,
                "relationships": explorer.relationships,
                "generated_at": datetime.now().isoformat(),
            }
        )

    elif format == "dot":
        # Generate Graphviz DOT format
        dot = "digraph ModelGraph {\n"
        dot += "  rankdir=LR;\n"
        dot += "  node [shape=record];\n"

        for model_name, model in explorer.models.items():
            fields = "\\n".join(
                f"{name}: {field['type']}" for name, field in list(model["fields"].items())[:5]
            )
            dot += f'  {model_name} [label="{model_name}|{fields}"];\n'

        for rel in explorer.relationships:
            dot += f'  {rel["source"]} -> {rel["target"]} [label="{rel["field"]}"];\n'

        dot += "}"

        response = app.response_class(response=dot, status=200, mimetype="text/plain")
        response.headers["Content-Disposition"] = "attachment; filename=models.dot"
        return response

    else:
        return jsonify({"error": "Unsupported format"}), 400


def run_server(host="127.0.0.1", port=5000, debug=True):
    """Run the Flask server"""
    print("\n🚀 Starting BF Agent Model Explorer")
    print(f"📍 Open your browser at: http://{host}:{port}")
    print(f"📊 Models will be loaded from: {explorer.app_name}")
    print("\nPress Ctrl+C to stop the server\n")

    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Visual Model Explorer for BF Agent")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=5000, help="Port to bind to")
    parser.add_argument("--no-debug", action="store_true", help="Disable debug mode")
    parser.add_argument("--app", default="bfagent", help="Django app name")

    args = parser.parse_args()

    explorer.app_name = args.app
    run_server(host=args.host, port=args.port, debug=not args.no_debug)
