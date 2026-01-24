"""
Graph Core Views - Framework Explorer and Graph Visualization
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Q, Subquery, OuterRef
from django.core.paginator import Paginator

from django.utils import timezone

from .models import (
    Framework, FrameworkPhase, FrameworkStep,
    NodeType, EdgeType, GraphNode, GraphEdge,
    ProjectFramework, PhaseProgress, StepProgress
)
from apps.bfagent.models import BookProjects


# =============================================================================
# FRAMEWORK VIEWS
# =============================================================================

@login_required
def framework_list(request):
    """List all available frameworks"""
    domain_filter = request.GET.get('domain', '')
    
    frameworks = Framework.objects.filter(is_active=True)
    
    if domain_filter:
        frameworks = frameworks.filter(domain=domain_filter)
    
    # Order and get frameworks - use model properties for counts
    frameworks = frameworks.order_by('domain', 'sort_order', 'name')
    
    # Group by domain
    domains = {}
    for fw in frameworks:
        domain = fw.get_domain_display()
        if domain not in domains:
            domains[domain] = []
        domains[domain].append(fw)
    
    context = {
        'frameworks': frameworks,
        'domains': domains,
        'domain_choices': Framework.DomainType.choices,
        'current_domain': domain_filter,
        'title': 'Story & Workflow Frameworks',
    }
    return render(request, 'graph_core/framework_list.html', context)


@login_required
def framework_detail(request, slug):
    """Detail view for a framework with all phases and steps"""
    framework = get_object_or_404(Framework, slug=slug, is_active=True)
    
    # Use direct query instead of reverse relation
    phases = FrameworkPhase.objects.filter(framework=framework).order_by('order')
    
    # Calculate total estimated metrics using direct queries
    total_steps = FrameworkStep.objects.filter(phase__framework=framework).count()
    total_chapters = 0
    total_words = 0
    for step in FrameworkStep.objects.filter(phase__framework=framework):
        total_chapters += step.estimated_chapters or 0
        total_words += step.estimated_word_count or 0
    
    context = {
        'framework': framework,
        'phases': phases,
        'total_steps': total_steps,
        'total_chapters': total_chapters,
        'total_words': total_words,
        'title': framework.display_name,
    }
    return render(request, 'graph_core/framework_detail.html', context)


@login_required
def framework_apply(request, slug, project_id):
    """Apply a framework to a project"""
    framework = get_object_or_404(Framework, slug=slug, is_active=True)
    project = get_object_or_404(BookProjects, id=project_id)
    
    if request.method == 'POST':
        # Check if already applied
        existing = ProjectFramework.objects.filter(
            project=project,
            framework=framework
        ).first()
        
        if existing:
            return JsonResponse({
                'success': False,
                'error': f'Framework "{framework.display_name}" is already applied to this project.'
            })
        
        # Make this the primary if no other frameworks
        is_primary = not project.assigned_frameworks.exists()
        
        pf = ProjectFramework.objects.create(
            project=project,
            framework=framework,
            is_primary=is_primary
        )
        pf.start()
        
        return JsonResponse({
            'success': True,
            'message': f'Framework "{framework.display_name}" applied successfully!',
            'project_framework_id': pf.id
        })
    
    context = {
        'framework': framework,
        'project': project,
        'title': f'Apply {framework.display_name}',
    }
    return render(request, 'graph_core/framework_apply.html', context)


# =============================================================================
# GRAPH EXPLORER VIEWS
# =============================================================================

@login_required
def graph_explorer(request, project_id):
    """Main graph explorer view with Cytoscape.js visualization"""
    project = get_object_or_404(BookProjects, id=project_id)
    
    # Get all nodes and edges for this project
    nodes = GraphNode.objects.filter(project=project, is_active=True)
    edges = GraphEdge.objects.filter(project=project, is_active=True)
    
    # Get available node and edge types
    node_types = NodeType.objects.filter(
        Q(domain='story') | Q(domain='custom')
    ).order_by('name')
    
    edge_types = EdgeType.objects.filter(
        Q(domain='story') | Q(domain='custom')
    ).order_by('name')
    
    # Get assigned frameworks
    frameworks = project.assigned_frameworks.select_related('framework').all()
    
    context = {
        'project': project,
        'nodes': nodes,
        'edges': edges,
        'node_types': node_types,
        'edge_types': edge_types,
        'frameworks': frameworks,
        'node_count': nodes.count(),
        'edge_count': edges.count(),
        'title': f'Graph Explorer - {project.title}',
    }
    return render(request, 'graph_core/explorer.html', context)


@login_required
def graph_data(request, project_id):
    """API endpoint returning Cytoscape.js formatted graph data"""
    project = get_object_or_404(BookProjects, id=project_id)
    
    nodes = GraphNode.objects.filter(project=project, is_active=True)
    edges = GraphEdge.objects.filter(project=project, is_active=True)
    
    elements = []
    
    # Add nodes
    for node in nodes:
        elements.append(node.to_cytoscape())
    
    # Add edges
    for edge in edges:
        elements.append(edge.to_cytoscape())
    
    # Get style definitions from node/edge types
    node_types = NodeType.objects.filter(
        Q(domain='story') | Q(domain='custom')
    )
    edge_types = EdgeType.objects.filter(
        Q(domain='story') | Q(domain='custom')
    )
    
    styles = []
    
    # Node styles
    for nt in node_types:
        styles.append({
            'selector': f'node.{nt.name}',
            'style': {
                'background-color': nt.color,
                'shape': nt.shape,
                'label': 'data(label)',
            }
        })
    
    # Edge styles
    for et in edge_types:
        styles.append({
            'selector': f'edge.{et.name}',
            'style': {
                'line-color': et.color,
                'line-style': et.line_style,
                'target-arrow-shape': et.arrow_shape if et.is_directed else 'none',
                'target-arrow-color': et.color,
                'curve-style': 'bezier',
            }
        })
    
    return JsonResponse({
        'elements': elements,
        'styles': styles,
    })


# =============================================================================
# NODE CRUD
# =============================================================================

@login_required
@require_http_methods(["POST"])
def node_create(request, project_id):
    """Create a new graph node"""
    project = get_object_or_404(BookProjects, id=project_id)
    
    import json
    data = json.loads(request.body)
    
    node_type = get_object_or_404(NodeType, id=data.get('node_type_id'))
    
    node = GraphNode.objects.create(
        project=project,
        node_type=node_type,
        name=data.get('name', 'New Node'),
        description=data.get('description', ''),
        properties=data.get('properties', {}),
        position_x=data.get('position_x', 100),
        position_y=data.get('position_y', 100),
        created_by=request.user,
    )
    
    return JsonResponse({
        'success': True,
        'node': node.to_cytoscape(),
        'node_id': node.id,
    })


@login_required
@require_http_methods(["POST"])
def node_update(request, project_id, node_id):
    """Update an existing graph node"""
    project = get_object_or_404(BookProjects, id=project_id)
    node = get_object_or_404(GraphNode, id=node_id, project=project)
    
    import json
    data = json.loads(request.body)
    
    if 'name' in data:
        node.name = data['name']
    if 'description' in data:
        node.description = data['description']
    if 'properties' in data:
        node.properties = data['properties']
    if 'position_x' in data:
        node.position_x = data['position_x']
    if 'position_y' in data:
        node.position_y = data['position_y']
    if 'custom_color' in data:
        node.custom_color = data['custom_color']
    
    node.save()
    
    return JsonResponse({
        'success': True,
        'node': node.to_cytoscape(),
    })


@login_required
@require_http_methods(["DELETE", "POST"])
def node_delete(request, project_id, node_id):
    """Delete a graph node"""
    project = get_object_or_404(BookProjects, id=project_id)
    node = get_object_or_404(GraphNode, id=node_id, project=project)
    
    node_name = node.name
    node.delete()
    
    return JsonResponse({
        'success': True,
        'message': f'Node "{node_name}" deleted.',
    })


# =============================================================================
# EDGE CRUD
# =============================================================================

@login_required
@require_http_methods(["POST"])
def edge_create(request, project_id):
    """Create a new graph edge"""
    project = get_object_or_404(BookProjects, id=project_id)
    
    import json
    data = json.loads(request.body)
    
    edge_type = get_object_or_404(EdgeType, id=data.get('edge_type_id'))
    source = get_object_or_404(GraphNode, id=data.get('source_id'), project=project)
    target = get_object_or_404(GraphNode, id=data.get('target_id'), project=project)
    
    edge = GraphEdge.objects.create(
        project=project,
        edge_type=edge_type,
        source=source,
        target=target,
        label=data.get('label', ''),
        weight=data.get('weight', 1.0),
        properties=data.get('properties', {}),
    )
    
    return JsonResponse({
        'success': True,
        'edge': edge.to_cytoscape(),
        'edge_id': edge.id,
    })


@login_required
@require_http_methods(["DELETE", "POST"])
def edge_delete(request, project_id, edge_id):
    """Delete a graph edge"""
    project = get_object_or_404(BookProjects, id=project_id)
    edge = get_object_or_404(GraphEdge, id=edge_id, project=project)
    
    edge.delete()
    
    return JsonResponse({
        'success': True,
        'message': 'Edge deleted.',
    })


# =============================================================================
# DASHBOARD
# =============================================================================

@login_required
def dashboard(request):
    """Graph Core dashboard - overview of frameworks and projects"""
    
    # Framework stats
    framework_stats = {
        'total': Framework.objects.filter(is_active=True).count(),
        'story': Framework.objects.filter(is_active=True, domain='story').count(),
        'software': Framework.objects.filter(is_active=True, domain='software').count(),
    }
    
    # Recent frameworks
    recent_frameworks = Framework.objects.filter(
        is_active=True
    ).order_by('-created_at')[:5]
    
    # Projects with frameworks
    projects_with_frameworks = ProjectFramework.objects.select_related(
        'project', 'framework'
    ).order_by('-updated_at')[:10]
    
    # Node/Edge type counts
    node_type_count = NodeType.objects.count()
    edge_type_count = EdgeType.objects.count()
    
    context = {
        'framework_stats': framework_stats,
        'recent_frameworks': recent_frameworks,
        'projects_with_frameworks': projects_with_frameworks,
        'node_type_count': node_type_count,
        'edge_type_count': edge_type_count,
        'title': 'Graph Core Dashboard',
    }
    return render(request, 'graph_core/dashboard.html', context)


# =============================================================================
# PROJECT WORKFLOW VIEWS - Integrated Framework + Project View
# =============================================================================

@login_required
def project_workflow(request, project_id):
    """
    Integrated workflow view showing project with framework phases checklist
    """
    project = get_object_or_404(BookProjects, id=project_id)
    
    # Get primary framework assignment or first one
    project_framework = ProjectFramework.objects.filter(
        project=project
    ).select_related('framework', 'current_phase', 'current_step').first()
    
    if not project_framework:
        # No framework assigned - redirect to framework selection
        return redirect('graph_core:framework-list')
    
    # Get phase progress with steps
    phase_progress = project_framework.get_phase_progress()
    
    # Calculate stats
    total_steps = sum(len(p['steps']) for p in phase_progress)
    completed_steps = sum(
        1 for p in phase_progress 
        for s in p['steps'] 
        if s['is_complete']
    )
    
    # Available frameworks for switching
    available_frameworks = Framework.objects.filter(
        is_active=True,
        domain=project_framework.framework.domain
    ).exclude(id=project_framework.framework_id)
    
    context = {
        'project': project,
        'project_framework': project_framework,
        'framework': project_framework.framework,
        'phase_progress': phase_progress,
        'total_steps': total_steps,
        'completed_steps': completed_steps,
        'available_frameworks': available_frameworks,
        'title': f'{project.title} - Workflow',
    }
    return render(request, 'graph_core/project_workflow.html', context)


@login_required
@require_http_methods(["POST"])
def toggle_step(request, project_framework_id, step_id):
    """Toggle step completion status via AJAX"""
    pf = get_object_or_404(ProjectFramework, id=project_framework_id)
    step = get_object_or_404(FrameworkStep, id=step_id)
    
    # Get or create step progress
    sp, created = StepProgress.objects.get_or_create(
        project_framework=pf,
        step=step
    )
    
    # Toggle completion
    sp.is_complete = not sp.is_complete
    sp.completed_at = timezone.now() if sp.is_complete else None
    sp.save()
    
    # Update phase progress if all steps complete
    phase = step.phase
    phase_steps = FrameworkStep.objects.filter(phase=phase)
    completed_count = StepProgress.objects.filter(
        project_framework=pf,
        step__in=phase_steps,
        is_complete=True
    ).count()
    
    phase_complete = completed_count == phase_steps.count()
    
    # Update or create phase progress
    pp, _ = PhaseProgress.objects.get_or_create(
        project_framework=pf,
        phase=phase
    )
    pp.is_complete = phase_complete
    pp.completed_at = timezone.now() if phase_complete else None
    pp.save()
    
    # Update overall progress
    pf.update_progress()
    
    return JsonResponse({
        'success': True,
        'step_complete': sp.is_complete,
        'phase_complete': phase_complete,
        'progress_percent': round(pf.progress_percent, 1),
        'completed_steps': completed_count,
        'total_steps': phase_steps.count(),
    })


@login_required
@require_http_methods(["POST"])
def update_step_notes(request, project_framework_id, step_id):
    """Update notes for a step via AJAX"""
    pf = get_object_or_404(ProjectFramework, id=project_framework_id)
    step = get_object_or_404(FrameworkStep, id=step_id)
    
    notes = request.POST.get('notes', '')
    
    sp, created = StepProgress.objects.get_or_create(
        project_framework=pf,
        step=step
    )
    sp.notes = notes
    sp.save()
    
    return JsonResponse({
        'success': True,
        'notes': sp.notes,
    })


@login_required
def select_framework(request, project_id):
    """Select a framework to apply to a project"""
    project = get_object_or_404(BookProjects, id=project_id)
    
    # Check if project already has a framework
    existing = ProjectFramework.objects.filter(project=project).first()
    
    # Get all story frameworks
    frameworks = Framework.objects.filter(
        is_active=True,
        domain='story'
    ).order_by('sort_order', 'name')
    
    if request.method == 'POST':
        framework_id = request.POST.get('framework_id')
        if framework_id:
            framework = get_object_or_404(Framework, id=framework_id)
            
            if existing:
                # Update existing assignment
                existing.framework = framework
                existing.current_phase = None
                existing.current_step = None
                existing.progress_percent = 0
                existing.started_at = None
                existing.completed_at = None
                existing.save()
                # Clear old progress
                PhaseProgress.objects.filter(project_framework=existing).delete()
                StepProgress.objects.filter(project_framework=existing).delete()
                existing.start()
                pf = existing
            else:
                # Create new assignment
                pf = ProjectFramework.objects.create(
                    project=project,
                    framework=framework,
                    is_primary=True
                )
                pf.start()
            
            return redirect('graph_core:project-workflow', project_id=project.id)
    
    context = {
        'project': project,
        'frameworks': frameworks,
        'existing': existing,
        'title': f'Select Framework for {project.title}',
    }
    return render(request, 'graph_core/select_framework.html', context)
