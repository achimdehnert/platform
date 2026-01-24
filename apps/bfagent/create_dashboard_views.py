#!/usr/bin/env python
"""Create Workflow Dashboard Views and Templates"""
import os
from pathlib import Path

# Create views file
views_dir = Path('apps/bfagent/views')
views_file = views_dir / 'workflow_dashboard.py'

views_content = '''"""
Workflow Dashboard Views
Multi-Hub Framework UI for workflow management and visualization
"""

from typing import Dict, Any, Optional
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Q, Prefetch
from django.utils import timezone

from apps.bfagent.models import (
    WorkflowPhase,
    DomainArt,
    DomainType,
    DomainPhase,
    PhaseActionConfig,
    AgentAction,
    BookProjects,
)
from apps.bfagent.services import (
    get_orchestrator,
    get_integrated_orchestrator,
    WorkflowContext,
)


@login_required
@require_http_methods(["GET"])
def workflow_dashboard(request: HttpRequest) -> HttpResponse:
    """
    Main workflow dashboard
    Shows overview of all workflows and domains
    """
    # Get all domain arts with their types and phase counts
    domain_arts = DomainArt.objects.filter(
        is_active=True
    ).prefetch_related(
        Prefetch(
            'domain_types',
            queryset=DomainType.objects.filter(is_active=True).annotate(
                phase_count=Count('domain_phases', filter=Q(domain_phases__is_active=True))
            )
        )
    ).annotate(
        total_types=Count('domain_types', filter=Q(domain_types__is_active=True))
    )
    
    # Get workflow statistics
    stats = {
        'total_domains': domain_arts.count(),
        'total_phases': WorkflowPhase.objects.filter(is_active=True).count(),
        'total_actions': AgentAction.objects.filter(is_active=True).count(),
        'active_projects': BookProjects.objects.filter(
            created_at__gte=timezone.now() - timezone.timedelta(days=30)
        ).count(),
    }
    
    context = {
        'domain_arts': domain_arts,
        'stats': stats,
        'page_title': 'Workflow Dashboard',
    }
    
    return render(request, 'bfagent/workflow/dashboard.html', context)


@login_required
@require_http_methods(["GET"])
def workflow_builder(request: HttpRequest, domain_art: str, domain_type: str) -> HttpResponse:
    """
    Workflow builder interface
    Shows workflow steps for a specific domain type
    """
    orchestrator = get_orchestrator()
    
    try:
        # Build workflow
        steps = orchestrator.build_workflow(domain_art, domain_type)
        
        # Get domain info
        domain = DomainArt.objects.get(name=domain_art, is_active=True)
        dtype = DomainType.objects.get(
            domain_art=domain,
            name=domain_type,
            is_active=True
        )
        
        # Get phase configurations with actions
        domain_phases = DomainPhase.objects.filter(
            domain_type=dtype,
            is_active=True
        ).select_related('workflow_phase').prefetch_related(
            Prefetch(
                'workflow_phase__phase_actions',
                queryset=PhaseActionConfig.objects.filter(
                    action__is_active=True
                ).select_related('action').order_by('order')
            )
        ).order_by('sort_order')
        
        context = {
            'domain': domain,
            'domain_type': dtype,
            'steps': steps,
            'domain_phases': domain_phases,
            'page_title': f'{dtype.display_name} Workflow',
        }
        
        return render(request, 'bfagent/workflow/builder.html', context)
        
    except Exception as e:
        context = {
            'error': str(e),
            'domain_art': domain_art,
            'domain_type': domain_type,
        }
        return render(request, 'bfagent/workflow/error.html', context, status=404)


@login_required
@require_http_methods(["POST"])
def workflow_execute(request: HttpRequest) -> JsonResponse:
    """
    Execute workflow via AJAX
    Returns JSON with execution results
    """
    import json
    
    try:
        data = json.loads(request.body)
        
        domain_art = data.get('domain_art')
        domain_type = data.get('domain_type')
        project_id = data.get('project_id')
        
        if not all([domain_art, domain_type]):
            return JsonResponse({
                'success': False,
                'error': 'Missing required parameters'
            }, status=400)
        
        # Create workflow context
        context = WorkflowContext(
            domain_art=domain_art,
            domain_type=domain_type,
            project_id=project_id,
            user_id=request.user.id,
            data=data.get('context_data', {})
        )
        
        # Execute workflow
        orchestrator = get_integrated_orchestrator()
        results = orchestrator.execute_workflow_with_handlers(context)
        
        return JsonResponse({
            'success': results['status'] == 'success',
            'results': results,
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def workflow_phase_detail(request: HttpRequest, phase_id: int) -> HttpResponse:
    """
    Detailed view of a workflow phase
    Shows actions, configurations, and execution history
    """
    phase = get_object_or_404(
        WorkflowPhase.objects.prefetch_related(
            Prefetch(
                'phase_actions',
                queryset=PhaseActionConfig.objects.select_related(
                    'action', 'action__agent'
                ).order_by('order')
            )
        ),
        pk=phase_id
    )
    
    # Get domains using this phase
    domain_phases = DomainPhase.objects.filter(
        workflow_phase=phase,
        is_active=True
    ).select_related('domain_type__domain_art')
    
    context = {
        'phase': phase,
        'domain_phases': domain_phases,
        'page_title': f'Phase: {phase.name}',
    }
    
    return render(request, 'bfagent/workflow/phase_detail.html', context)


@login_required
@require_http_methods(["GET"])
def workflow_visualizer(request: HttpRequest, domain_art: str, domain_type: str) -> HttpResponse:
    """
    Interactive workflow visualizer
    Shows workflow as interactive diagram
    """
    orchestrator = get_orchestrator()
    
    try:
        steps = orchestrator.build_workflow(domain_art, domain_type)
        
        # Get domain info
        domain = DomainArt.objects.get(name=domain_art, is_active=True)
        dtype = DomainType.objects.get(
            domain_art=domain,
            name=domain_type,
            is_active=True
        )
        
        # Build visualization data
        viz_data = {
            'nodes': [],
            'edges': [],
        }
        
        for i, step in enumerate(steps):
            viz_data['nodes'].append({
                'id': f'step_{i}',
                'label': step.phase_name,
                'order': step.order,
                'required': step.is_required,
                'hub': step.hub_name,
            })
            
            # Add edges (connections between steps)
            if i > 0:
                viz_data['edges'].append({
                    'from': f'step_{i-1}',
                    'to': f'step_{i}',
                })
        
        context = {
            'domain': domain,
            'domain_type': dtype,
            'viz_data': viz_data,
            'page_title': f'{dtype.display_name} Workflow Visualizer',
        }
        
        return render(request, 'bfagent/workflow/visualizer.html', context)
        
    except Exception as e:
        context = {
            'error': str(e),
            'domain_art': domain_art,
            'domain_type': domain_type,
        }
        return render(request, 'bfagent/workflow/error.html', context, status=404)


@login_required
@require_http_methods(["GET"])
def workflow_api_info(request: HttpRequest) -> JsonResponse:
    """
    API endpoint for workflow information
    Returns available workflows and their configurations
    """
    domain_arts = DomainArt.objects.filter(
        is_active=True
    ).prefetch_related(
        'domain_types'
    )
    
    data = {
        'workflows': []
    }
    
    for domain in domain_arts:
        for dtype in domain.domain_types.filter(is_active=True):
            orchestrator = get_orchestrator()
            try:
                steps = orchestrator.build_workflow(domain.name, dtype.name)
                data['workflows'].append({
                    'domain_art': domain.name,
                    'domain_type': dtype.name,
                    'display_name': dtype.display_name,
                    'description': dtype.description,
                    'step_count': len(steps),
                    'steps': [
                        {
                            'name': step.phase_name,
                            'order': step.order,
                            'required': step.is_required,
                            'hub': step.hub_name,
                        }
                        for step in steps
                    ]
                })
            except Exception as e:
                continue
    
    return JsonResponse(data)
'''

# Write views file
print(f'📝 Creating {views_file}...')
views_dir.mkdir(parents=True, exist_ok=True)
with open(views_file, 'w', encoding='utf-8') as f:
    f.write(views_content)

print(f'✅ Created: {views_file}')
print(f'📊 Size: {os.path.getsize(views_file)} bytes')
print('\n🚀 Next: Create dashboard templates')