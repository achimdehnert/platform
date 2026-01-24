#!/usr/bin/env python
"""Create Workflow Visualizer Template"""
import os
from pathlib import Path

# Template file
template_file = Path('apps/bfagent/templates/bfagent/workflow/visualizer.html')

visualizer_html = '''{% extends "bfagent/base.html" %}
{% load static %}

{% block title %}Workflow Visualizer - {{ domain_type.display_name }}{% endblock %}

{% block extra_css %}
<style>
    .mermaid {
        background: white;
        border-radius: 8px;
        padding: 20px;
        margin: 20px 0;
    }
    .step-legend {
        display: flex;
        gap: 20px;
        flex-wrap: wrap;
        margin: 20px 0;
    }
    .legend-item {
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .legend-color {
        width: 20px;
        height: 20px;
        border-radius: 4px;
    }
</style>
{% endblock %}

{% block extra_js %}
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>
    mermaid.initialize({ 
        startOnLoad: true,
        theme: 'default',
        flowchart: {
            curve: 'basis',
            padding: 20
        }
    });
</script>
{% endblock %}

{% block content %}
<div class="container-fluid py-4">
    <!-- Header -->
    <div class="row mb-4">
        <div class="col-12">
            <nav aria-label="breadcrumb">
                <ol class="breadcrumb">
                    <li class="breadcrumb-item"><a href="{% url 'workflow_dashboard' %}">Workflow Dashboard</a></li>
                    <li class="breadcrumb-item">{{ domain_art.display_name }}</li>
                    <li class="breadcrumb-item active">{{ domain_type.display_name }} Visualizer</li>
                </ol>
            </nav>
            
            <h1 class="display-5">
                <i class="bi bi-diagram-3"></i>
                {{ domain_type.display_name }} Workflow
            </h1>
            <p class="lead text-muted">{{ domain_type.description }}</p>
        </div>
    </div>

    <!-- Actions -->
    <div class="row mb-3">
        <div class="col-12">
            <a href="{% url 'workflow_builder' domain_art.slug domain_type.slug %}" class="btn btn-primary">
                <i class="bi bi-list-task"></i> Builder View
            </a>
            <a href="{% url 'workflow_dashboard' %}" class="btn btn-outline-secondary">
                <i class="bi bi-arrow-left"></i> Back to Dashboard
            </a>
        </div>
    </div>

    <!-- Legend -->
    <div class="card mb-4">
        <div class="card-body">
            <h5 class="card-title">Legend</h5>
            <div class="step-legend">
                <div class="legend-item">
                    <div class="legend-color" style="background: #e3f2fd;"></div>
                    <span>Workflow Step</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #fff3cd;"></div>
                    <span>Required Step</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #d1ecf1;"></div>
                    <span>Optional Step</span>
                </div>
            </div>
        </div>
    </div>

    <!-- Workflow Diagram -->
    <div class="card">
        <div class="card-header bg-primary text-white">
            <h3 class="mb-0">
                <i class="bi bi-diagram-3-fill"></i>
                Workflow Flow Diagram
            </h3>
        </div>
        <div class="card-body">
            <div class="mermaid">
                graph TD
                    Start([Start Workflow]) --> Step1
                    {% for step in workflow_steps %}
                        {% if forloop.first %}
                            Step{{ forloop.counter }}[{{ step.phase.name }}]
                        {% else %}
                            Step{{ forloop.counter0 }} --> Step{{ forloop.counter }}
                            Step{{ forloop.counter }}[{{ step.phase.name }}]
                        {% endif %}
                        
                        {% if step.is_required %}
                            style Step{{ forloop.counter }} fill:#fff3cd,stroke:#856404,stroke-width:2px
                        {% else %}
                            style Step{{ forloop.counter }} fill:#d1ecf1,stroke:#0c5460
                        {% endif %}
                    {% endfor %}
                    Step{{ workflow_steps|length }} --> End([Workflow Complete])
                    
                    style Start fill:#28a745,stroke:#1e7e34,color:#fff
                    style End fill:#dc3545,stroke:#bd2130,color:#fff
            </div>
        </div>
    </div>

    <!-- Workflow Steps Details -->
    <div class="row mt-4">
        <div class="col-12">
            <div class="card">
                <div class="card-header">
                    <h4 class="mb-0">Workflow Steps ({{ workflow_steps|length }})</h4>
                </div>
                <div class="card-body">
                    <div class="table-responsive">
                        <table class="table table-hover">
                            <thead>
                                <tr>
                                    <th>#</th>
                                    <th>Phase</th>
                                    <th>Description</th>
                                    <th>Status</th>
                                    <th>Required</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for step in workflow_steps %}
                                <tr>
                                    <td>{{ forloop.counter }}</td>
                                    <td>
                                        <strong>{{ step.phase.name }}</strong>
                                    </td>
                                    <td>{{ step.phase.description|default:"No description" }}</td>
                                    <td>
                                        <span class="badge bg-secondary">{{ step.status|default:"pending" }}</span>
                                    </td>
                                    <td>
                                        {% if step.is_required %}
                                            <span class="badge bg-warning">Required</span>
                                        {% else %}
                                            <span class="badge bg-info">Optional</span>
                                        {% endif %}
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Statistics -->
    <div class="row mt-4">
        <div class="col-md-4">
            <div class="card text-center">
                <div class="card-body">
                    <h2 class="display-4">{{ workflow_steps|length }}</h2>
                    <p class="text-muted">Total Steps</p>
                </div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card text-center">
                <div class="card-body">
                    <h2 class="display-4">{{ required_count }}</h2>
                    <p class="text-muted">Required Steps</p>
                </div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card text-center">
                <div class="card-body">
                    <h2 class="display-4">{{ optional_count }}</h2>
                    <p class="text-muted">Optional Steps</p>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
'''

print(f'📝 Creating {template_file}...')
with open(template_file, 'w', encoding='utf-8') as f:
    f.write(visualizer_html)

print(f'✅ Created: {template_file}')
print(f'📊 Size: {os.path.getsize(template_file)} bytes')
print('\n🚀 Visualizer template ready!')
print('   Reload: http://localhost:8000/bookwriting/workflow/')