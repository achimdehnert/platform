#!/usr/bin/env python
"""
Automatic List Template Generator
Generates Bootstrap 5 list templates with filters for all ListView classes
"""
import os
import sys
from pathlib import Path

# Django Setup
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

import django
django.setup()

from django.apps import apps
from apps.bfagent.models import *


def get_template_skeleton():
    """Return template skeleton - using function to avoid f-string conflicts"""
    return '''{{% extends "base.html" %}}
{{% load static %}}

{{% block title %}}{title}{{% endblock %}}

{{% block content %}}
<div class="container-fluid">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2><i class="bi bi-{icon}"></i> {title}</h2>
        <a href="{{% url 'bfagent:{model_lower}-create' %}}" class="btn btn-primary">
            <i class="bi bi-plus-circle"></i> Create {model_name}
        </a>
    </div>

    <!-- Filters -->
    <div class="card mb-3">
        <div class="card-body">
            <form method="get" class="row g-3">
{filter_fields}
                
                <div class="col-md-2 d-flex align-items-end">
                    <button type="submit" class="btn btn-secondary w-100">
                        <i class="bi bi-funnel"></i> Filter
                    </button>
                </div>
            </form>
        </div>
    </div>

    <!-- Results -->
    <div class="card">
        <div class="card-body">
            {{% if {context_name} %}}
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
{table_headers}
                                <th class="text-end">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {{% for item in {context_name} %}}
                                <tr>
{table_cells}
                                    <td class="text-end">
                                        <div class="btn-group btn-group-sm" role="group">
                                            <a href="{{% url 'bfagent:{model_lower}-detail' item.pk %}}" 
                                               class="btn btn-outline-primary" title="View">
                                                <i class="bi bi-eye"></i>
                                            </a>
                                            <a href="{{% url 'bfagent:{model_lower}-update' item.pk %}}" 
                                               class="btn btn-outline-secondary" title="Edit">
                                                <i class="bi bi-pencil"></i>
                                            </a>
                                            <a href="{{% url 'bfagent:{model_lower}-delete' item.pk %}}" 
                                               class="btn btn-outline-danger" title="Delete">
                                                <i class="bi bi-trash"></i>
                                            </a>
                                        </div>
                                    </td>
                                </tr>
                            {{% endfor %}}
                        </tbody>
                    </table>
                </div>

                <!-- Pagination -->
                {{% if is_paginated %}}
                    <nav aria-label="Page navigation">
                        <ul class="pagination justify-content-center">
                            {{% if page_obj.has_previous %}}
                                <li class="page-item">
                                    <a class="page-link" href="?page=1">First</a>
                                </li>
                                <li class="page-item">
                                    <a class="page-link" href="?page={{{{ page_obj.previous_page_number }}}}">Previous</a>
                                </li>
                            {{% endif %}}

                            <li class="page-item active">
                                <span class="page-link">
                                    Page {{{{ page_obj.number }}}} of {{{{ page_obj.paginator.num_pages }}}}
                                </span>
                            </li>

                            {{% if page_obj.has_next %}}
                                <li class="page-item">
                                    <a class="page-link" href="?page={{{{ page_obj.next_page_number }}}}">Next</a>
                                </li>
                                <li class="page-item">
                                    <a class="page-link" href="?page={{{{ page_obj.paginator.num_pages }}}}">Last</a>
                                </li>
                            {{% endif %}}
                        </ul>
                    </nav>
                {{% endif %}}

            {{% else %}}
                <div class="alert alert-info">
                    <i class="bi bi-info-circle"></i> 
                    No {model_name} found.
                    <a href="{{% url 'bfagent:{model_lower}-create' %}}" class="alert-link">Create one now</a>
                </div>
            {{% endif %}}
        </div>
    </div>
</div>
{{% endblock %}}
'''


ICON_MAP = {
    'BookProjects': 'book',
    'Agents': 'robot',
    'BookChapters': 'file-text',
    'Characters': 'person',
    'Llms': 'cpu',
    'StoryArc': 'diagram-3',
    'PlotPoint': 'pin-map',
    'AgentExecutions': 'gear',
    'AgentArtifacts': 'box',
    'Genre': 'tags',
    'TargetAudience': 'people-fill',
    'WorkflowPhase': 'list-task',
    'WorkflowTemplate': 'folder',
    'WorkflowPhaseStep': 'arrow-right-circle',
    'AgentAction': 'lightning',
    'PhaseActionConfig': 'link-45deg',
    'BookTypes': 'collection',
    'QueryPerformanceLog': 'speedometer2',
    'WritingStatus': 'check2-circle',
    'ProjectPhaseHistory': 'clock-history',
    'ActionTemplate': 'link-45deg',
    'PromptTemplate': 'file-earmark-text',
}


def generate_filter_fields(model):
    """Generate filter field HTML"""
    fields = []
    
    # Get ForeignKey fields
    for field in model._meta.get_fields():
        if field.many_to_one and not field.auto_created:
            related_model_name = field.related_model.__name__.lower()
            fields.append(f'''                <div class="col-md-3">
                    <label for="{field.name}" class="form-label">{field.name.replace('_', ' ').title()}</label>
                    <select name="{field.name}" id="{field.name}" class="form-select">
                        <option value="">All</option>
                        {{% for item in all_{field.name}s %}}
                            <option value="{{{{ item.id }}}}" {{% if current_filters.{field.name} == item.id|stringformat:"s" %}}selected{{% endif %}}>
                                {{{{ item.name }}}}
                            </option>
                        {{% endfor %}}
                    </select>
                </div>''')
    
    # Add search field
    fields.append('''                <div class="col-md-4">
                    <label for="search" class="form-label">Search</label>
                    <input type="text" name="q" id="search" class="form-control" 
                           placeholder="Search..." 
                           value="{{ current_filters.q }}">
                </div>''')
    
    return '\n'.join(fields)


def generate_table_headers(model):
    """Generate table headers"""
    headers = []
    
    # Get display fields from CRUDConfig if available
    if hasattr(model, 'CRUDConfig') and hasattr(model.CRUDConfig, 'list_display'):
        display_fields = model.CRUDConfig.list_display[:5]  # Max 5 columns
    else:
        # Default: name, created_at, etc.
        display_fields = []
        for field in model._meta.get_fields():
            if field.name in ['name', 'title', 'display_name']:
                display_fields.append(field.name)
                break
        if len(display_fields) < 2:
            display_fields.extend(['created_at', 'updated_at'][:2-len(display_fields)])
    
    for field_name in display_fields:
        header = field_name.replace('_', ' ').title()
        headers.append(f'                                <th>{header}</th>')
    
    return '\n'.join(headers)


def generate_table_cells(model):
    """Generate table cells"""
    cells = []
    
    # Get display fields from CRUDConfig if available
    if hasattr(model, 'CRUDConfig') and hasattr(model.CRUDConfig, 'list_display'):
        display_fields = model.CRUDConfig.list_display[:5]
    else:
        display_fields = []
        for field in model._meta.get_fields():
            if field.name in ['name', 'title', 'display_name']:
                display_fields.append(field.name)
                break
        if len(display_fields) < 2:
            display_fields.extend(['created_at', 'updated_at'][:2-len(display_fields)])
    
    for field_name in display_fields:
        if 'date' in field_name or field_name in ['created_at', 'updated_at']:
            cells.append(f'                                    <td>{{{{ item.{field_name}|date:"Y-m-d H:i" }}}}</td>')
        else:
            cells.append(f'                                    <td>{{{{ item.{field_name}|default:"-" }}}}</td>')
    
    return '\n'.join(cells)


def generate_template(model_name):
    """Generate complete template for a model"""
    model = apps.get_model('bfagent', model_name)
    model_lower = model_name.lower()
    icon = ICON_MAP.get(model_name, 'list')
    
    # Generate components
    filter_fields = generate_filter_fields(model)
    table_headers = generate_table_headers(model)
    table_cells = generate_table_cells(model)
    
    # Context name (pluralize)
    context_name = f"{model_lower}s" if not model_lower.endswith('s') else model_lower
    
    # Get template skeleton
    template_skeleton = get_template_skeleton()
    
    # Fill template
    template = template_skeleton.format(
        icon=icon,
        model_name=model_name,
        model_lower=model_lower,
        context_name=context_name,
        title=f"{model_name} List",
        filter_fields=filter_fields,
        table_headers=table_headers,
        table_cells=table_cells,
    )
    
    return template


def main():
    """Generate templates for all models"""
    template_dir = Path(__file__).parent.parent / 'templates' / 'bfagent'
    template_dir.mkdir(parents=True, exist_ok=True)
    
    models_to_generate = [
        'Characters',
        'StoryArc',
        'PlotPoint',
        'BookTypes',
        'WorkflowPhase',
        'WorkflowPhaseStep',
        'AgentArtifacts',
    ]
    
    print("\n🚀 TEMPLATE GENERATOR")
    print("=" * 80)
    print()
    
    for model_name in models_to_generate:
        template_path = template_dir / f"{model_name.lower()}_list.html"
        
        if template_path.exists():
            print(f"⏭️  SKIP: {model_name} (template exists)")
            continue
        
        try:
            template_content = generate_template(model_name)
            template_path.write_text(template_content, encoding='utf-8')
            print(f"✅ CREATED: {model_name} → {template_path.name}")
        except Exception as e:
            print(f"❌ ERROR: {model_name} - {e}")
    
    print()
    print("=" * 80)
    print("✅ TEMPLATE GENERATION COMPLETE")
    print()


if __name__ == '__main__':
    main()
