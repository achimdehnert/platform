"""
Research Hub - Views
====================

Web interface for the Research Hub domain.
"""

import json
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods, require_POST
from django.core.paginator import Paginator

from ..models import ResearchProject, ResearchSource, ResearchFinding
from ..handlers import WebSearchHandler, FactCheckHandler, SummaryHandler
from ..services import ResearchService, get_research_service

logger = logging.getLogger(__name__)


@login_required
def dashboard(request):
    """Research Hub dashboard."""
    projects = ResearchProject.objects.filter(
        owner=request.user,
        is_active=True
    ).order_by('-updated_at')[:5]
    
    # Stats
    total_projects = ResearchProject.objects.filter(owner=request.user).count()
    active_projects = ResearchProject.objects.filter(
        owner=request.user,
        status__in=['draft', 'in_progress']
    ).count()
    total_sources = ResearchSource.objects.filter(
        project__owner=request.user
    ).count()
    total_findings = ResearchFinding.objects.filter(
        project__owner=request.user
    ).count()
    
    context = {
        'title': 'Research Hub',
        'projects': projects,
        'stats': {
            'total_projects': total_projects,
            'active_projects': active_projects,
            'total_sources': total_sources,
            'total_findings': total_findings,
        }
    }
    return render(request, 'research/dashboard.html', context)


@login_required
def project_list(request):
    """List all research projects."""
    projects = ResearchProject.objects.filter(
        owner=request.user,
        is_active=True
    ).order_by('-updated_at')
    
    # Filtering
    status = request.GET.get('status')
    if status:
        projects = projects.filter(status=status)
    
    # Pagination
    paginator = Paginator(projects, 12)
    page = request.GET.get('page', 1)
    projects = paginator.get_page(page)
    
    context = {
        'title': 'Research Projects',
        'projects': projects,
        'status_choices': ResearchProject.Status.choices,
    }
    return render(request, 'research/project_list.html', context)


@login_required
def project_create(request):
    """Create a new research project."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        query = request.POST.get('query', '').strip()
        description = request.POST.get('description', '').strip()
        research_type = request.POST.get('research_type', 'quick_facts')
        output_format = request.POST.get('output_format', 'markdown')
        citation_style = request.POST.get('citation_style', 'apa')
        require_peer_reviewed = request.POST.get('require_peer_reviewed') == 'on'
        
        if not name:
            messages.error(request, 'Project name is required.')
            return render(request, 'research/project_form.html', {
                'title': 'New Research Project'
            })
        
        project = ResearchProject.objects.create(
            name=name,
            query=query,
            description=description,
            research_type=research_type,
            output_format=output_format,
            citation_style=citation_style,
            require_peer_reviewed=require_peer_reviewed,
            owner=request.user
        )
        
        messages.success(request, f'Project "{name}" created successfully.')
        return redirect('research:project_detail', pk=project.pk)
    
    context = {
        'title': 'New Research Project',
        'phases': ResearchProject.get_phases(),
    }
    return render(request, 'research/project_form.html', context)


@login_required
def project_detail(request, pk):
    """View research project details."""
    project = get_object_or_404(
        ResearchProject,
        pk=pk,
        owner=request.user
    )
    
    sources = project.sources.order_by('-relevance_score')[:20]
    findings = project.findings.order_by('-importance')[:20]
    results = project.results.order_by('-created_at')[:10]
    
    context = {
        'title': project.name,
        'project': project,
        'sources': sources,
        'findings': findings,
        'results': results,
        'phases': ResearchProject.get_phases(),
    }
    return render(request, 'research/project_detail.html', context)


@login_required
def project_edit(request, pk):
    """Edit research project."""
    project = get_object_or_404(
        ResearchProject,
        pk=pk,
        owner=request.user
    )
    
    if request.method == 'POST':
        project.name = request.POST.get('name', project.name).strip()
        project.query = request.POST.get('query', project.query).strip()
        project.description = request.POST.get('description', project.description).strip()
        project.status = request.POST.get('status', project.status)
        project.research_type = request.POST.get('research_type', project.research_type)
        project.output_format = request.POST.get('output_format', project.output_format)
        project.citation_style = request.POST.get('citation_style', project.citation_style)
        project.require_peer_reviewed = request.POST.get('require_peer_reviewed') == 'on'
        project.save()
        
        messages.success(request, 'Project updated successfully.')
        return redirect('research:project_detail', pk=project.pk)
    
    context = {
        'title': f'Edit: {project.name}',
        'project': project,
        'status_choices': ResearchProject.Status.choices,
    }
    return render(request, 'research/project_form.html', context)


@login_required
@require_POST
def project_delete(request, pk):
    """Delete research project."""
    project = get_object_or_404(
        ResearchProject,
        pk=pk,
        owner=request.user
    )
    
    project.is_active = False
    project.save()
    
    messages.success(request, f'Project "{project.name}" deleted.')
    return redirect('research:project_list')


@login_required
@require_POST
def perform_search(request, pk):
    """Perform web search for a project."""
    project = get_object_or_404(
        ResearchProject,
        pk=pk,
        owner=request.user
    )
    
    query = request.POST.get('query', project.query)
    count = int(request.POST.get('count', 10))
    
    handler = WebSearchHandler()
    result = handler.execute(
        project_id=project.pk,
        query=query,
        options={'count': count}
    )
    
    if result.get('success'):
        messages.success(
            request,
            f"Found {result.get('sources_found', 0)} sources."
        )
        project.status = ResearchProject.Status.IN_PROGRESS
        project.current_phase = 'quellen_sammeln'
        project.save()
    else:
        messages.error(request, f"Search failed: {result.get('error')}")
    
    return redirect('research:project_detail', pk=project.pk)


@login_required
@require_POST
def perform_fact_check(request, pk):
    """Perform fact check for project findings."""
    project = get_object_or_404(
        ResearchProject,
        pk=pk,
        owner=request.user
    )
    
    handler = FactCheckHandler()
    result = handler.execute(project_id=project.pk)
    
    if result.get('success'):
        messages.success(
            request,
            f"Checked {result.get('claims_checked', 0)} claims. "
            f"Verified: {result.get('verified_true', 0)}, "
            f"False: {result.get('verified_false', 0)}, "
            f"Unknown: {result.get('unknown', 0)}"
        )
        project.current_phase = 'analyse'
        project.save()
    else:
        messages.error(request, f"Fact check failed: {result.get('error')}")
    
    return redirect('research:project_detail', pk=project.pk)


@login_required
@require_POST
def generate_summary(request, pk):
    """Generate summary for a project."""
    project = get_object_or_404(
        ResearchProject,
        pk=pk,
        owner=request.user
    )
    
    output_format = request.POST.get('format', 'markdown')
    
    handler = SummaryHandler()
    result = handler.execute(
        project_id=project.pk,
        options={'format': output_format}
    )
    
    if result.get('success'):
        messages.success(request, 'Summary generated successfully.')
        project.current_phase = 'zusammenfassung'
        project.save()
    else:
        messages.error(request, f"Summary failed: {result.get('error')}")
    
    return redirect('research:project_detail', pk=project.pk)


# =============================================================================
# API Endpoints
# =============================================================================

@login_required
@require_POST
def api_quick_search(request):
    """Quick search API endpoint."""
    try:
        data = json.loads(request.body)
        query = data.get('query', '')
        count = data.get('count', 5)
        
        if not query:
            return JsonResponse({
                'success': False,
                'error': 'Query is required'
            }, status=400)
        
        service = get_research_service()
        results = service.quick_search(query, count=count)
        
        return JsonResponse({
            'success': True,
            'query': query,
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Quick search error: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_POST
def api_fact_check(request):
    """Fact check API endpoint."""
    try:
        data = json.loads(request.body)
        claim = data.get('claim', '')
        context = data.get('context', '')
        
        if not claim:
            return JsonResponse({
                'success': False,
                'error': 'Claim is required'
            }, status=400)
        
        service = get_research_service()
        result = service.fact_check(claim, context=context)
        
        return JsonResponse({
            'success': True,
            **result
        })
        
    except Exception as e:
        logger.error(f"Fact check error: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def project_export(request, pk, format):
    """Export project in specified format."""
    from django.http import HttpResponse
    from .services import get_export_service
    
    project = get_object_or_404(ResearchProject, pk=pk)
    export_service = get_export_service()
    
    if format == 'markdown':
        content = export_service.export_markdown(project)
        response = HttpResponse(content, content_type='text/markdown')
        response['Content-Disposition'] = f'attachment; filename="{project.name}.md"'
        
    elif format == 'latex':
        content = export_service.export_latex(project)
        response = HttpResponse(content, content_type='application/x-latex')
        response['Content-Disposition'] = f'attachment; filename="{project.name}.tex"'
        
    elif format == 'bibtex':
        content = export_service.export_bibtex(project)
        response = HttpResponse(content, content_type='application/x-bibtex')
        response['Content-Disposition'] = f'attachment; filename="{project.name}.bib"'
        
    elif format == 'docx':
        content = export_service.export_docx(project)
        response = HttpResponse(content, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename="{project.name}.docx"'
        
    else:
        return JsonResponse({'error': f'Unknown format: {format}'}, status=400)
    
    return response
