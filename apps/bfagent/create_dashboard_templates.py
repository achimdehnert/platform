#!/usr/bin/env python
"""Create Workflow Dashboard Templates"""
import os
from pathlib import Path

# Template directory
template_dir = Path('apps/bfagent/templates/bfagent/workflow')
template_dir.mkdir(parents=True, exist_ok=True)

# === 1. Dashboard Template ===
dashboard_html = '''{% extends "bfagent/base.html" %}
{% load static %}

{% block title %}{{ page_title }}{% endblock %}

{% block extra_css %}
<style>
    .workflow-card {
        transition: transform 0.2s, box-shadow 0.2s;
        border-left: 4px solid var(--bs-primary);
    }
    .workflow-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
    }
    .stat-card {
        background: linear-gradient(135deg, var(--bs-primary) 0%, var(--bs-info) 100%);
        color: white;
    }
    .domain-badge {
        font-size: 0.75rem;
        padding: 0.25rem 0.5rem;
    }
</style>
{% endblock %}

{% block content %}
<div class="container-fluid py-4">
    <!-- Header -->
    <div class="row mb-4">
        <div class="col-12">
            <h1 class="display-4">
                <i class="bi bi-diagram-3"></i>
                Workflow Dashboard
            </h1>
            <p class="lead text-muted">Multi-Hub Framework - Workflow Orchestration</p>
        </div>
    </div>

    <!-- Statistics -->
    <div class="row g-3 mb-4">
        <div class="col-md-3">
            <div class="card stat-card">
                <div class="card-body text-center">
                    <h3 class="display-5 mb-0">{{ stats.total_domains }}</h3>
                    <p class="mb-0">Domain Arts</p>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stat-card">
                <div class="card-body text-center">
                    <h3 class="display-5 mb-0">{{ stats.total_phases }}</h3>
                    <p class="mb-0">Workflow Phases</p>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stat-card">
                <div class="card-body text-center">
                    <h3 class="display-5 mb-0">{{ stats.total_actions }}</h3>
                    <p class="mb-0">Agent Actions</p>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stat-card">
                <div class="card-body text-center">
                    <h3 class="display-5 mb-0">{{ stats.active_projects }}</h3>
                    <p class="mb-0">Active Projects</p>
                </div>
            </div>
        </div>
    </div>

    <!-- Domain Arts -->
    <div class="row">
        {% for domain in domain_arts %}
        <div class="col-12 mb-4">
            <div class="card">
                <div class="card-header bg-primary text-white">
                    <h3 class="mb-0">
                        <i class="bi bi-{{ domain.icon|default:'box' }}"></i>
                        {{ domain.display_name }}
                        <span class="badge bg-light text-dark ms-2">{{ domain.total_types }} types</span>
                    </h3>
                    <p class="mb-0 small">{{ domain.description }}</p>
                </div>
                <div class="card-body">
                    <div class="row g-3">
                        {% for dtype in domain.domain_types.all %}
                        <div class="col-md-6 col-lg-4">
                            <div class="card workflow-card h-100">
                                <div class="card-body">
                                    <h5 class="card-title">
                                        <i class="bi bi-{{ dtype.effective_icon|default:'file-earmark' }}"></i>
                                        {{ dtype.display_name }}
                                    </h5>
                                    <p class="card-text text-muted small">{{ dtype.description|truncatewords:15 }}</p>
                                    <div class="d-flex justify-content-between align-items-center">
                                        <span class="badge bg-info">{{ dtype.phase_count }} phases</span>
                                        <div class="btn-group btn-group-sm">
                                            <a href="{% url 'bfagent:workflow_builder' domain.name dtype.name %}" 
                                               class="btn btn-outline-primary">
                                                <i class="bi bi-hammer"></i> Builder
                                            </a>
                                            <a href="{% url 'bfagent:workflow_visualizer' domain.name dtype.name %}" 
                                               class="btn btn-outline-info">
                                                <i class="bi bi-diagram-2"></i> Visualize
                                            </a>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        {% empty %}
                        <div class="col-12">
                            <p class="text-muted">No domain types configured yet.</p>
                        </div>
                        {% endfor %}
                    </div>
                </div>
            </div>
        </div>
        {% empty %}
        <div class="col-12">
            <div class="alert alert-info">
                <i class="bi bi-info-circle"></i>
                No domain arts configured yet. Please set up your domains in the admin panel.
            </div>
        </div>
        {% endfor %}
    </div>
</div>
{% endblock %}
'''

# === 2. Builder Template ===
builder_html = '''{% extends "bfagent/base.html" %}
{% load static %}

{% block title %}{{ page_title }}{% endblock %}

{% block extra_css %}
<style>
    .step-card {
        transition: all 0.2s;
        border-left: 4px solid var(--bs-secondary);
    }
    .step-card.required {
        border-left-color: var(--bs-danger);
    }
    .step-card:hover {
        background-color: var(--bs-light);
    }
    .action-badge {
        font-size: 0.7rem;
    }
</style>
{% endblock %}

{% block content %}
<div class="container-fluid py-4">
    <!-- Header -->
    <div class="row mb-4">
        <div class="col-12">
            <nav aria-label="breadcrumb">
                <ol class="breadcrumb">
                    <li class="breadcrumb-item"><a href="{% url 'bfagent:workflow_dashboard' %}">Workflows</a></li>
                    <li class="breadcrumb-item">{{ domain.display_name }}</li>
                    <li class="breadcrumb-item active">{{ domain_type.display_name }}</li>
                </ol>
            </nav>
            <h1 class="display-4">
                <i class="bi bi-{{ domain_type.effective_icon }}"></i>
                {{ domain_type.display_name }} Workflow
            </h1>
            <p class="lead text-muted">{{ domain_type.description }}</p>
        </div>
    </div>

    <!-- Workflow Steps -->
    <div class="row">
        <div class="col-12">
            <div class="card">
                <div class="card-header bg-primary text-white">
                    <h3 class="mb-0">Workflow Steps ({{ steps|length }})</h3>
                </div>
                <div class="card-body">
                    {% for step in steps %}
                    <div class="card step-card mb-3 {% if step.is_required %}required{% endif %}">
                        <div class="card-body">
                            <div class="row align-items-center">
                                <div class="col-auto">
                                    <h2 class="text-muted mb-0">{{ forloop.counter }}</h2>
                                </div>
                                <div class="col">
                                    <h5 class="mb-1">
                                        {{ step.phase_name }}
                                        {% if step.is_required %}
                                        <span class="badge bg-danger">Required</span>
                                        {% else %}
                                        <span class="badge bg-secondary">Optional</span>
                                        {% endif %}
                                        <span class="badge bg-info">{{ step.hub_name }}</span>
                                    </h5>
                                    <p class="text-muted mb-0 small">Order: {{ step.order }}</p>
                                </div>
                                <div class="col-auto">
                                    <button class="btn btn-sm btn-outline-primary" 
                                            onclick="showStepDetails({{ forloop.counter0 }})">
                                        <i class="bi bi-info-circle"></i> Details
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
                <div class="card-footer">
                    <button class="btn btn-success" onclick="executeWorkflow()">
                        <i class="bi bi-play-fill"></i> Execute Workflow
                    </button>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
function showStepDetails(index) {
    alert('Step details for step ' + (index + 1));
}

function executeWorkflow() {
    if (confirm('Execute workflow for {{ domain_type.display_name }}?')) {
        fetch('{% url "bfagent:workflow_execute" %}', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': '{{ csrf_token }}'
            },
            body: JSON.stringify({
                domain_art: '{{ domain.name }}',
                domain_type: '{{ domain_type.name }}'
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Workflow executed successfully!');
            } else {
                alert('Workflow execution failed: ' + data.error);
            }
        });
    }
}
</script>
{% endblock %}
'''

# === 3. Error Template ===
error_html = '''{% extends "bfagent/base.html" %}

{% block title %}Workflow Error{% endblock %}

{% block content %}
<div class="container py-5">
    <div class="row justify-content-center">
        <div class="col-md-8">
            <div class="alert alert-danger">
                <h2><i class="bi bi-exclamation-triangle"></i> Workflow Error</h2>
                <p class="mb-0">{{ error }}</p>
            </div>
            <a href="{% url 'bfagent:workflow_dashboard' %}" class="btn btn-primary">
                <i class="bi bi-arrow-left"></i> Back to Dashboard
            </a>
        </div>
    </div>
</div>
{% endblock %}
'''

# Write templates
templates = {
    'dashboard.html': dashboard_html,
    'builder.html': builder_html,
    'error.html': error_html,
}

for filename, content in templates.items():
    filepath = template_dir / filename
    print(f'📝 Creating {filepath}...')
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'✅ Created: {filepath} ({os.path.getsize(filepath)} bytes)')

print(f'\n✅ Created {len(templates)} templates in {template_dir}')
print('\n🚀 Next: Create URL routing')