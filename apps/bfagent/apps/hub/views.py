from django.contrib.auth.decorators import login_required
from django.shortcuts import render


def landing_page(request):
    """Landing page for non-authenticated users"""
    return render(request, 'landing.html')


@login_required
def central_dashboard(request):
    """Central Hub Dashboard - Entry point for all BF Agent domains"""
    
    # Import models
    from apps.bfagent.models import BookProjects, Characters, BookChapters
    from apps.medtrans.models import Customer, Presentation
    from apps.presentation_studio.models import Presentation as PptxPresentation
    from apps.genagent.models import Phase, Action, ExecutionLog
    from apps.control_center.registry import ToolRegistry
    
    # Check user groups
    user_groups = list(request.user.groups.values_list('name', flat=True))
    has_bookwriting = 'BookWriting' in user_groups or request.user.is_superuser
    has_medtrans = 'MedicalTranslation' in user_groups or request.user.is_superuser
    has_genagent = 'GenAgent' in user_groups or request.user.is_superuser
    
    # Build domains data structure (only include domains user has access to)
    domains = []
    
    # Book Writing Studio (only if user has BookWriting group)
    if has_bookwriting:
        book_projects_count = BookProjects.objects.filter(user=request.user).count()
        characters_count = Characters.objects.count()
        chapters_count = BookChapters.objects.count()
        
        domains.append({
            'name': 'Book Writing Studio',
            'subtitle': 'Workflow Agent',
            'icon': 'bi-book',
            'url': '/bookwriting/books/',
            'description': 'Write books with AI assistance. Manage characters, chapters, and story development.',
            'color': 'primary',
            'stats': [
                {'label': 'Books', 'value': book_projects_count},
                {'label': 'Characters', 'value': characters_count},
                {'label': 'Chapters', 'value': chapters_count},
                {'label': 'Active', 'value': '✓' if book_projects_count > 0 else '—'},
            ]
        })
    
    # Medical Translation (only if user has MedicalTranslation group)
    if has_medtrans:
        customers_count = Customer.objects.filter(user=request.user).count()
        presentations_count = Presentation.objects.filter(customer__user=request.user).count()
        completed_translations = Presentation.objects.filter(
            customer__user=request.user,
            status='completed'
        ).count()
        
        domains.append({
            'name': 'Medical Translation',
            'icon': 'bi-translate',
            'url': '/medtrans/',
            'description': 'Professional PPTX translation with DeepL. Manage customers and translation projects.',
            'color': 'danger',
            'stats': [
                {'label': 'Customers', 'value': customers_count},
                {'label': 'Presentations', 'value': presentations_count},
                {'label': 'Completed', 'value': completed_translations},
                {'label': 'Active', 'value': '✓' if presentations_count > completed_translations else '—'},
            ]
        })
    
    # PPTX Studio (available to all authenticated users)
    pptx_presentations = PptxPresentation.objects.filter(uploaded_by=request.user).count()
    pptx_completed = PptxPresentation.objects.filter(
        uploaded_by=request.user,
        enhancement_status='completed'
    ).count()
    pptx_ready = PptxPresentation.objects.filter(
        uploaded_by=request.user,
        enhancement_status='ready'
    ).count()
    
    domains.append({
        'name': 'PPTX Studio',
        'subtitle': 'Presentation Enhancement',
        'icon': 'bi-file-earmark-slides',
        'url': '/pptx-studio/',
        'description': 'Enhance PowerPoint presentations with AI-generated concept slides. Upload, enhance, download.',
        'color': 'warning',
        'stats': [
            {'label': 'Presentations', 'value': pptx_presentations},
            {'label': 'Completed', 'value': pptx_completed},
            {'label': 'Ready', 'value': pptx_ready},
            {'label': 'Active', 'value': '✓' if pptx_presentations > 0 else '—'},
        ]
    })
    
    # GenAgent Framework (only if user has GenAgent group)
    if has_genagent:
        phases_count = Phase.objects.count()
        actions_count = Action.objects.count()
        recent_executions = ExecutionLog.objects.filter(
            status='success'
        ).count()
        active_phases = Phase.objects.filter(is_active=True).count()
        
        domains.append({
            'name': 'Book Writing Studio 2.0',
            'subtitle': 'Beta - Next Generation',
            'badge': 'BETA',
            'icon': 'bi-robot',
            'url': '/genagent/',
            'description': 'Next-generation book writing with handler-based architecture, workflow phases, and domain templates.',
            'color': 'success',
            'stats': [
                {'label': 'Phases', 'value': phases_count},
                {'label': 'Actions', 'value': actions_count},
                {'label': 'Executions', 'value': recent_executions},
                {'label': 'Active', 'value': f'{active_phases}/{phases_count}' if phases_count > 0 else '—'},
            ]
        })
    
    # Control Center (only for superuser/admin)
    if request.user.is_superuser:
        tool_registry = ToolRegistry()
        tools_count = len(tool_registry.list_tools())
        system_health = tool_registry.get_system_health()
        
        domains.append({
            'name': 'Control Center',
            'icon': 'bi-gear',
            'url': '/control-center/',
            'description': 'System tools, monitoring, and development utilities. Manage your BF Agent instance.',
            'color': 'info',
            'stats': [
                {'label': 'Tools', 'value': tools_count},
                {'label': 'Health', 'value': f"{system_health.get('health_percentage', 0)}%"},
                {'label': 'Status', 'value': system_health.get('status', 'Unknown')},
                {'label': 'Ready', 'value': system_health.get('ready_tools', 0)},
            ]
        })
    
    context = {
        'domains': domains,
        'user': request.user,
    }
    
    return render(request, 'hub/dashboard.html', context)
