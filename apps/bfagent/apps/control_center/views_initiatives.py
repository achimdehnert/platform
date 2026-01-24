"""
Initiative Management Views

CRUD operations and workflow management for Initiatives (Epics/Concepts).
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.bfagent.models_testing import Initiative, TestRequirement


# =============================================================================
# LIST & DASHBOARD
# =============================================================================

@login_required
def initiative_list(request):
    """List all initiatives with filtering."""
    status_filter = request.GET.get('status', '')
    domain_filter = request.GET.get('domain', '')
    
    initiatives = Initiative.objects.all()
    
    if status_filter:
        initiatives = initiatives.filter(status=status_filter)
    if domain_filter:
        initiatives = initiatives.filter(domain=domain_filter)
    
    # Group by status for Kanban view
    kanban_data = {
        'analysis': initiatives.filter(status='analysis'),
        'concept': initiatives.filter(status='concept'),
        'planning': initiatives.filter(status='planning'),
        'in_progress': initiatives.filter(status='in_progress'),
        'review': initiatives.filter(status='review'),
        'completed': initiatives.filter(status='completed'),
    }
    
    context = {
        'initiatives': initiatives,
        'kanban_data': kanban_data,
        'status_filter': status_filter,
        'domain_filter': domain_filter,
        'status_choices': Initiative._meta.get_field('status').choices,
        'domain_choices': Initiative._meta.get_field('domain').choices,
    }
    return render(request, 'control_center/initiatives/list.html', context)


@login_required
def initiative_dashboard(request):
    """Dashboard overview of all initiatives."""
    initiatives = Initiative.objects.all()
    
    # Stats
    stats = {
        'total': initiatives.count(),
        'in_analysis': initiatives.filter(status='analysis').count(),
        'in_concept': initiatives.filter(status='concept').count(),
        'in_progress': initiatives.filter(status='in_progress').count(),
        'completed': initiatives.filter(status='completed').count(),
    }
    
    # Recent initiatives
    recent = initiatives.order_by('-updated_at')[:5]
    
    # By domain
    by_domain = {}
    for domain_code, domain_name in Initiative._meta.get_field('domain').choices:
        count = initiatives.filter(domain=domain_code).count()
        if count > 0:
            by_domain[domain_name] = count
    
    context = {
        'stats': stats,
        'recent_initiatives': recent,
        'by_domain': by_domain,
    }
    return render(request, 'control_center/initiatives/dashboard.html', context)


# =============================================================================
# DETAIL VIEW
# =============================================================================

@login_required
def initiative_detail(request, pk):
    """Detail view of a single initiative with its requirements."""
    from apps.bfagent.models_testing import RequirementFeedback, MCPUsageLog
    from django.utils import timezone
    from datetime import timedelta
    
    initiative = get_object_or_404(Initiative, pk=pk)
    requirements = initiative.requirements.all().order_by('-priority', '-created_at')
    
    # Progress stats
    total_reqs = requirements.count()
    completed_reqs = requirements.filter(status__in=['done', 'completed']).count()
    in_progress_reqs = requirements.filter(status='in_progress').count()
    draft_reqs = requirements.filter(status='draft').count()
    ready_reqs = requirements.filter(status='ready').count()
    blocked_reqs = requirements.filter(status='blocked').count()
    
    # Group requirements by status for Kanban board
    kanban_statuses = [
        ('draft', 'Entwurf'),
        ('ready', 'Bereit'),
        ('in_progress', 'In Arbeit'),
        ('blocked', 'Blockiert'),
        ('done', 'Erledigt'),
    ]
    requirements_by_status = {}
    for status_code, _ in kanban_statuses:
        requirements_by_status[status_code] = list(
            requirements.filter(status=status_code)
        )
    
    # Workflow phases
    workflow_phases = [
        ('kickoff', 'Kickoff'),
        ('research', 'Recherche'),
        ('analysis', 'Analyse'),
        ('design', 'Design'),
        ('implementation', 'Implementierung'),
        ('testing', 'Testing'),
        ('documentation', 'Dokumentation'),
        ('review', 'Review'),
        ('deployment', 'Deployment'),
    ]
    
    # Active tasks (requirements in_progress)
    active_tasks = requirements.filter(status='in_progress')
    
    # Recent feedback for this initiative's requirements
    requirement_ids = list(requirements.values_list('id', flat=True))
    recent_feedback = RequirementFeedback.objects.filter(
        requirement_id__in=requirement_ids
    ).select_related('requirement').order_by('-created_at')[:8]
    
    # MCP Stats for this initiative (last 7 days)
    mcp_stats = None
    n8n_status = None
    try:
        last_7d = timezone.now() - timedelta(days=7)
        mcp_logs = MCPUsageLog.objects.filter(
            initiative=initiative,
            created_at__gte=last_7d
        )
        total_calls = mcp_logs.count()
        if total_calls > 0:
            success_count = mcp_logs.filter(status='success').count()
            error_count = mcp_logs.filter(status='error').count()
            mcp_stats = {
                'total_calls': total_calls,
                'success_count': success_count,
                'error_count': error_count,
                'success_rate': (success_count / total_calls * 100) if total_calls > 0 else 0,
                'error_rate': (error_count / total_calls * 100) if total_calls > 0 else 0,
            }
        
        # n8n webhook stats (check feedback for webhook triggers)
        webhook_feedback = recent_feedback.filter(content__icontains='n8n')
        if webhook_feedback.exists():
            n8n_status = {
                'webhooks_triggered': webhook_feedback.count(),
                'last_trigger': webhook_feedback.first().created_at if webhook_feedback.exists() else None
            }
    except Exception:
        pass
    
    context = {
        'initiative': initiative,
        'requirements': requirements,
        'requirements_by_status': requirements_by_status,
        'kanban_statuses': kanban_statuses,
        'total_reqs': total_reqs,
        'completed_reqs': completed_reqs,
        'in_progress_reqs': in_progress_reqs,
        'draft_reqs': draft_reqs,
        'ready_reqs': ready_reqs,
        'blocked_reqs': blocked_reqs,
        'status_choices': Initiative._meta.get_field('status').choices,
        'workflow_phases': workflow_phases,
        'active_tasks': active_tasks,
        'recent_feedback': recent_feedback,
        'mcp_stats': mcp_stats,
        'n8n_status': n8n_status,
    }
    return render(request, 'control_center/initiatives/detail.html', context)


# =============================================================================
# CREATE
# =============================================================================

@login_required
def initiative_create(request):
    """Create a new initiative."""
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        domain = request.POST.get('domain', 'core')
        priority = request.POST.get('priority', 'medium')
        analysis = request.POST.get('analysis', '').strip()
        concept = request.POST.get('concept', '').strip()
        
        if not title:
            messages.error(request, 'Titel ist erforderlich.')
            return redirect('control_center:initiative-create')
        
        initiative = Initiative.objects.create(
            title=title,
            description=description,
            domain=domain,
            priority=priority,
            analysis=analysis,
            concept=concept,
            status='analysis' if not concept else 'concept',
            created_by=request.user,
        )
        
        messages.success(request, f'Initiative "{initiative.title}" erstellt.')
        return redirect('control_center:initiative-detail', pk=initiative.pk)
    
    context = {
        'domain_choices': Initiative._meta.get_field('domain').choices,
        'priority_choices': Initiative._meta.get_field('priority').choices,
    }
    return render(request, 'control_center/initiatives/create.html', context)


# =============================================================================
# UPDATE
# =============================================================================

@login_required
def initiative_update(request, pk):
    """Update an existing initiative."""
    initiative = get_object_or_404(Initiative, pk=pk)
    
    if request.method == 'POST':
        initiative.title = request.POST.get('title', initiative.title).strip()
        initiative.description = request.POST.get('description', initiative.description).strip()
        initiative.domain = request.POST.get('domain', initiative.domain)
        initiative.priority = request.POST.get('priority', initiative.priority)
        initiative.analysis = request.POST.get('analysis', initiative.analysis).strip()
        initiative.concept = request.POST.get('concept', initiative.concept).strip()
        initiative.save()
        
        messages.success(request, f'Initiative "{initiative.title}" aktualisiert.')
        return redirect('control_center:initiative-detail', pk=initiative.pk)
    
    context = {
        'initiative': initiative,
        'domain_choices': Initiative._meta.get_field('domain').choices,
        'priority_choices': Initiative._meta.get_field('priority').choices,
    }
    return render(request, 'control_center/initiatives/edit.html', context)


# =============================================================================
# DELETE
# =============================================================================

@login_required
@require_POST
def initiative_delete(request, pk):
    """Delete an initiative."""
    initiative = get_object_or_404(Initiative, pk=pk)
    title = initiative.title
    initiative.delete()
    
    messages.success(request, f'Initiative "{title}" gelöscht.')
    return redirect('control_center:initiative-list')


# =============================================================================
# WORKFLOW / STATUS TRANSITIONS
# =============================================================================

@login_required
@require_POST
def initiative_change_status(request, pk):
    """Change the status of an initiative (workflow transition)."""
    initiative = get_object_or_404(Initiative, pk=pk)
    new_status = request.POST.get('status')
    
    valid_statuses = [s[0] for s in Initiative._meta.get_field('status').choices]
    
    if new_status not in valid_statuses:
        messages.error(request, f'Ungültiger Status: {new_status}')
        return redirect('control_center:initiative-detail', pk=pk)
    
    old_status = initiative.get_status_display()
    initiative.status = new_status
    initiative.save()
    
    messages.success(request, f'Status geändert: {old_status} → {initiative.get_status_display()}')
    
    # HTMX response
    if request.headers.get('HX-Request'):
        return render(request, 'control_center/initiatives/partials/status_badge.html', {
            'initiative': initiative
        })
    
    return redirect('control_center:initiative-detail', pk=pk)


@login_required
@require_POST
def initiative_change_workflow_phase(request, pk):
    """Change the workflow phase of an initiative."""
    initiative = get_object_or_404(Initiative, pk=pk)
    new_phase = request.POST.get('workflow_phase')
    
    valid_phases = ['kickoff', 'research', 'analysis', 'design', 'implementation', 
                    'testing', 'documentation', 'review', 'deployment']
    
    if new_phase not in valid_phases:
        messages.error(request, f'Ungültige Phase: {new_phase}')
        return redirect('control_center:initiative-detail', pk=pk)
    
    old_phase = initiative.workflow_phase
    initiative.workflow_phase = new_phase
    initiative.save()
    
    # Log activity if model supports it
    if hasattr(initiative, 'log_activity'):
        initiative.log_activity(
            action='status_change',
            details=f'Workflow-Phase: {old_phase} → {new_phase}',
            actor=request.user.username
        )
    
    messages.success(request, f'Workflow-Phase geändert: {old_phase} → {new_phase}')
    return redirect('control_center:initiative-detail', pk=pk)


# =============================================================================
# ADD REQUIREMENT TO INITIATIVE
# =============================================================================

@login_required
def initiative_add_requirement(request, pk):
    """Add a new requirement/task to an initiative."""
    initiative = get_object_or_404(Initiative, pk=pk)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        category = request.POST.get('category', 'feature')
        priority = request.POST.get('priority', 'medium')
        
        if not name:
            messages.error(request, 'Name ist erforderlich.')
            return redirect('control_center:initiative-detail', pk=pk)
        
        requirement = TestRequirement.objects.create(
            name=name,
            description=description,
            category=category,
            priority=priority,
            domain=initiative.domain,
            initiative=initiative,
            status='draft',
            created_by=request.user,
        )
        
        messages.success(request, f'Requirement "{requirement.name}" hinzugefügt.')
        
        # HTMX response
        if request.headers.get('HX-Request'):
            return render(request, 'control_center/initiatives/partials/requirement_row.html', {
                'requirement': requirement
            })
        
        return redirect('control_center:initiative-detail', pk=pk)
    
    context = {
        'initiative': initiative,
        'category_choices': TestRequirement._meta.get_field('category').choices,
        'priority_choices': TestRequirement._meta.get_field('priority').choices,
    }
    return render(request, 'control_center/initiatives/add_requirement.html', context)


# =============================================================================
# KANBAN VIEW
# =============================================================================

@login_required
def initiative_kanban(request):
    """Kanban board view of initiatives."""
    initiatives = Initiative.objects.all()
    
    columns = [
        ('analysis', 'In Analyse', 'bi-search', 'info'),
        ('concept', 'Konzept', 'bi-lightbulb', 'warning'),
        ('planning', 'Planung', 'bi-clipboard-check', 'primary'),
        ('in_progress', 'In Arbeit', 'bi-gear', 'success'),
        ('review', 'Review', 'bi-eye', 'secondary'),
        ('completed', 'Abgeschlossen', 'bi-check-circle', 'success'),
    ]
    
    kanban_data = []
    for status_code, status_name, icon, color in columns:
        items = initiatives.filter(status=status_code)
        kanban_data.append({
            'code': status_code,
            'name': status_name,
            'icon': icon,
            'color': color,
            'items': items,
            'count': items.count(),
        })
    
    context = {
        'kanban_data': kanban_data,
    }
    return render(request, 'control_center/initiatives/kanban.html', context)


# =============================================================================
# API ENDPOINTS (for HTMX/AJAX)
# =============================================================================

@login_required
def initiative_list_partial(request):
    """Return partial HTML for initiative list (HTMX)."""
    initiatives = Initiative.objects.all()
    
    status_filter = request.GET.get('status', '')
    domain_filter = request.GET.get('domain', '')
    
    if status_filter:
        initiatives = initiatives.filter(status=status_filter)
    if domain_filter:
        initiatives = initiatives.filter(domain=domain_filter)
    
    return render(request, 'control_center/initiatives/partials/list_items.html', {
        'initiatives': initiatives
    })


@login_required
@require_POST
def initiative_quick_create(request):
    """Quick create initiative via HTMX."""
    title = request.POST.get('title', '').strip()
    domain = request.POST.get('domain', 'core')
    
    if not title:
        return JsonResponse({'error': 'Titel erforderlich'}, status=400)
    
    initiative = Initiative.objects.create(
        title=title,
        description='',
        domain=domain,
        status='analysis',
        created_by=request.user,
    )
    
    return render(request, 'control_center/initiatives/partials/initiative_card.html', {
        'initiative': initiative
    })


# =============================================================================
# KANBAN BOARD AJAX ENDPOINTS
# =============================================================================

@login_required
@require_POST
def requirement_update_status(request, pk, req_pk):
    """Update requirement status via Kanban drag & drop."""
    initiative = get_object_or_404(Initiative, pk=pk)
    requirement = get_object_or_404(TestRequirement, pk=req_pk, initiative=initiative)
    
    new_status = request.POST.get('status', '')
    valid_statuses = ['draft', 'ready', 'in_progress', 'blocked', 'done', 'completed']
    
    if new_status not in valid_statuses:
        return JsonResponse({'error': 'Ungültiger Status'}, status=400)
    
    old_status = requirement.status
    requirement.status = new_status
    requirement.save()
    
    # Log activity
    initiative.log_activity(
        action='status_change',
        details=f"Requirement '{requirement.name}': {old_status} → {new_status}",
        actor='user'
    )
    
    return JsonResponse({'success': True, 'old_status': old_status, 'new_status': new_status})


@login_required
def requirement_preview(request, pk, req_pk):
    """Preview requirement details in modal with activity dashboard."""
    from apps.bfagent.models_testing import MCPUsageLog
    
    initiative = get_object_or_404(Initiative, pk=pk)
    requirement = get_object_or_404(TestRequirement, pk=req_pk, initiative=initiative)
    
    # Get other requirements for dependency dropdown (exclude self)
    other_requirements = initiative.requirements.exclude(pk=req_pk).order_by('name')
    
    # MCP Logs for this requirement
    mcp_logs = None
    mcp_stats = None
    try:
        mcp_logs = MCPUsageLog.objects.filter(
            requirement=requirement
        ).order_by('-created_at')[:10]
        
        if mcp_logs.exists():
            total = mcp_logs.count()
            success = mcp_logs.filter(status='success').count()
            error = mcp_logs.filter(status='error').count()
            mcp_stats = {
                'total_calls': total,
                'success_count': success,
                'error_count': error,
            }
    except Exception:
        pass
    
    return render(request, 'control_center/initiatives/partials/requirement_preview.html', {
        'requirement': requirement,
        'initiative': initiative,
        'other_requirements': other_requirements,
        'mcp_logs': mcp_logs,
        'mcp_stats': mcp_stats,
    })


@login_required
@require_POST
def requirement_update_dependency(request, pk, req_pk):
    """Update requirement dependency."""
    initiative = get_object_or_404(Initiative, pk=pk)
    requirement = get_object_or_404(TestRequirement, pk=req_pk, initiative=initiative)
    
    depends_on_id = request.POST.get('depends_on', '').strip()
    
    if depends_on_id:
        depends_on = get_object_or_404(TestRequirement, pk=depends_on_id, initiative=initiative)
        requirement.depends_on = depends_on
    else:
        requirement.depends_on = None
    
    requirement.save()
    
    # Log activity
    initiative.log_activity(
        action='comment',
        details=f"Abhängigkeit für '{requirement.name}' geändert: {depends_on.name if depends_on_id else 'Keine'}",
        actor='user'
    )
    
    return JsonResponse({'success': True})


@login_required
@require_POST
def requirement_delete(request, pk, req_pk):
    """Delete a requirement."""
    initiative = get_object_or_404(Initiative, pk=pk)
    requirement = get_object_or_404(TestRequirement, pk=req_pk, initiative=initiative)
    
    name = requirement.name
    requirement.delete()
    
    # Log activity
    initiative.log_activity(
        action='comment',
        details=f"Requirement '{name}' gelöscht",
        actor='user'
    )
    
    return JsonResponse({'success': True})


@login_required
@require_POST
def requirement_add_comment(request, pk, req_pk):
    """Add a comment to a requirement."""
    from apps.bfagent.models_testing import RequirementFeedback
    
    initiative = get_object_or_404(Initiative, pk=pk)
    requirement = get_object_or_404(TestRequirement, pk=req_pk, initiative=initiative)
    
    content = request.POST.get('content', '').strip()
    if not content:
        return JsonResponse({'error': 'Inhalt erforderlich'}, status=400)
    
    RequirementFeedback.objects.create(
        requirement=requirement,
        feedback_type='comment',
        content=content,
        author=request.user,
        is_from_cascade=False
    )
    
    return JsonResponse({'success': True})


@login_required
@require_POST
def requirement_analyze(request, pk, req_pk):
    """Trigger Cascade analysis or respond to user question."""
    from apps.bfagent.models_testing import RequirementFeedback
    
    initiative = get_object_or_404(Initiative, pk=pk)
    requirement = get_object_or_404(TestRequirement, pk=req_pk, initiative=initiative)
    
    question = request.POST.get('question', '').strip()
    
    if question:
        # User asked a question - generate contextual response
        # Check for common questions
        q_lower = question.lower()
        
        if 'start' in q_lower or 'anfang' in q_lower or 'beginn' in q_lower:
            if requirement.can_start:
                response = f"""✅ **Ja, wir können starten!**

Das Requirement "{requirement.name}" ist bereit:
- Status: {requirement.get_status_display()}
- Keine blockierenden Abhängigkeiten
- Priorität: {requirement.get_priority_display()}

👉 Klicke auf **"Freigeben & Starten"** um zu beginnen."""
            else:
                response = f"""⏳ **Noch nicht bereit zum Starten**

Blockiert durch: {requirement.depends_on.name if requirement.depends_on else 'Unbekannt'}
Status der Abhängigkeit: {requirement.depends_on.get_status_display() if requirement.depends_on else '-'}

Bitte warte bis die Abhängigkeit erledigt ist."""
        
        elif 'beschreib' in q_lower or 'was ist' in q_lower or 'worum geht' in q_lower:
            response = f"""📋 **{requirement.name}**

{requirement.description or 'Keine Beschreibung vorhanden.'}

**Kategorie:** {requirement.get_category_display()}
**Priorität:** {requirement.get_priority_display()}"""
        
        elif 'hilf' in q_lower or 'help' in q_lower:
            response = """🤖 **Wie kann ich helfen?**

Ich kann:
- Fragen zum Requirement beantworten
- Prüfen ob wir starten können
- Eine Qualitätsanalyse durchführen
- Den Status erklären

Einfach fragen!"""
        
        else:
            # Generic response to the question
            response = f"""🤖 **Antwort auf: "{question}"**

Zum Requirement "{requirement.name}":
- **Status:** {requirement.get_status_display()}
- **Kann starten:** {"✅ Ja" if requirement.can_start else "⏳ Nein (Abhängigkeit)"}
- **Priorität:** {requirement.get_priority_display()}

Für eine vollständige Analyse nutze das MCP-Tool `bfagent_analyze_requirement`."""
        
        feedback_type = 'comment'
    else:
        # No question - run standard analysis
        response = f"""**Requirement-Analyse: {requirement.name}**

✅ **Sinnhaftigkeit:** Requirement ist klar definiert.
📋 **Status:** {requirement.get_status_display()}
🔗 **Abhängigkeit:** {requirement.depends_on.name if requirement.depends_on else 'Keine'}

**Kann starten:** {"✅ Ja" if requirement.can_start else "⏳ Wartet auf Abhängigkeit"}"""
        feedback_type = 'solution'
    
    RequirementFeedback.objects.create(
        requirement=requirement,
        feedback_type=feedback_type,
        content=response,
        author=request.user,
        is_from_cascade=True
    )
    
    return JsonResponse({'success': True, 'message': 'Antwort erstellt'})


@login_required
@require_POST
def requirement_approve(request, pk, req_pk):
    """Approve and start work on a requirement."""
    from apps.bfagent.models_testing import RequirementFeedback
    
    initiative = get_object_or_404(Initiative, pk=pk)
    requirement = get_object_or_404(TestRequirement, pk=req_pk, initiative=initiative)
    
    # Check if can start
    if not requirement.can_start:
        return JsonResponse({'error': 'Abhängigkeit noch nicht erledigt'}, status=400)
    
    # Update status to in_progress
    old_status = requirement.status
    requirement.status = 'in_progress'
    requirement.save()
    
    # Add feedback
    RequirementFeedback.objects.create(
        requirement=requirement,
        feedback_type='progress',
        content=f"✅ Freigegeben und gestartet (vorher: {old_status})",
        author=request.user,
        is_from_cascade=False
    )
    
    # Log activity
    initiative.log_activity(
        action='status_change',
        details=f"Requirement '{requirement.name}' freigegeben und gestartet",
        actor='user'
    )
    
    return JsonResponse({'success': True})


# =============================================================================
# AI-POWERED RESEARCH & REQUIREMENT GENERATION
# =============================================================================

@login_required
@require_POST
def initiative_start_research(request, pk):
    """
    Start AI-powered research and requirement generation for an initiative.
    
    Reads the analysis field for folder paths, analyzes documents,
    and uses LLM to generate requirements.
    """
    from apps.bfagent.models_testing import RequirementFeedback, MCPUsageLog
    from apps.bfagent.services.llm_client import generate_text, LlmRequest
    from django.conf import settings
    from pathlib import Path
    import os
    import re
    
    initiative = get_object_or_404(Initiative, pk=pk)
    
    # Log start of research
    initiative.log_activity(
        action='analysis_started',
        details=f'KI-gestützte Recherche gestartet für Phase: {initiative.workflow_phase}',
        actor=request.user.username
    )
    
    # Extract folder path from analysis field
    analysis_text = initiative.analysis or ''
    folder_paths = re.findall(r'[a-zA-Z]:[\\\/][\w\\\/\-_.]+|\/[\w\/\-_.]+', analysis_text)
    
    documents_content = []
    files_found = []
    
    # Read documents from found paths
    for folder_path in folder_paths:
        path = Path(folder_path)
        if path.exists() and path.is_dir():
            for file_path in path.glob('**/*'):
                if file_path.is_file() and file_path.suffix.lower() in ['.txt', '.md', '.pdf', '.docx', '.doc']:
                    try:
                        if file_path.suffix.lower() in ['.txt', '.md']:
                            content = file_path.read_text(encoding='utf-8', errors='ignore')[:5000]
                            documents_content.append(f"### {file_path.name}\n{content}\n")
                            files_found.append(str(file_path))
                    except Exception as e:
                        pass
    
    # Build LLM prompt
    system_prompt = """Du bist ein erfahrener Projektmanager und Business Analyst.
Analysiere die bereitgestellten Dokumente und Projektbeschreibung.
Leite daraus konkrete, umsetzbare Requirements ab.

Für jedes Requirement liefere:
1. **Name**: Kurzer, prägnanter Titel
2. **Beschreibung**: Was genau soll umgesetzt werden
3. **Kategorie**: feature, enhancement, oder bug_fix
4. **Priorität**: critical, high, medium, oder low
5. **Akzeptanzkriterien**: 2-3 messbare Kriterien

Antworte im folgenden JSON-Format:
```json
{
  "requirements": [
    {
      "name": "...",
      "description": "...",
      "category": "feature",
      "priority": "high",
      "acceptance_criteria": ["...", "..."]
    }
  ],
  "analysis_summary": "Zusammenfassung der Analyse"
}
```"""
    
    user_prompt = f"""## Initiative: {initiative.title}

### Beschreibung
{initiative.description}

### Analyse-Kontext
{initiative.analysis}

### Gefundene Dokumente ({len(files_found)} Dateien)
{chr(10).join(documents_content[:10]) if documents_content else 'Keine Dokumente gefunden.'}

---
Bitte analysiere diese Informationen und generiere passende Requirements für diese Initiative."""

    try:
        # Get LLM configuration
        api_endpoint = getattr(settings, 'OPENAI_API_BASE', 'https://api.openai.com')
        api_key = getattr(settings, 'OPENAI_API_KEY', '')
        model = getattr(settings, 'DEFAULT_LLM_MODEL', 'gpt-4o-mini')
        
        llm_request = LlmRequest(
            provider='openai',
            api_endpoint=api_endpoint,
            api_key=api_key,
            model=model,
            system=system_prompt,
            prompt=user_prompt,
            temperature=0.7,
            max_tokens=3000
        )
        
        result = generate_text(llm_request)
        
        if result.get('ok') and result.get('text'):
            response_text = result['text']
            
            # Try to parse JSON from response
            import json
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(1))
                    requirements_data = data.get('requirements', [])
                    analysis_summary = data.get('analysis_summary', '')
                    
                    # Create requirements
                    created_count = 0
                    for req_data in requirements_data:
                        TestRequirement.objects.create(
                            initiative=initiative,
                            name=req_data.get('name', 'Unnamed Requirement'),
                            description=req_data.get('description', ''),
                            category=req_data.get('category', 'feature'),
                            priority=req_data.get('priority', 'medium'),
                            acceptance_criteria=req_data.get('acceptance_criteria', []),
                            domain=initiative.domain,
                            status='draft',
                            created_by=request.user
                        )
                        created_count += 1
                    
                    # Update initiative with analysis summary
                    if analysis_summary:
                        initiative.concept = (initiative.concept or '') + f"\n\n## KI-Analyse\n{analysis_summary}"
                        initiative.save()
                    
                    # Log success
                    MCPUsageLog.objects.create(
                        tool_name='initiative_start_research',
                        tool_category='llm',
                        arguments={'initiative_id': str(pk), 'files_analyzed': len(files_found)},
                        result_summary=f'{created_count} Requirements generiert',
                        status='success',
                        initiative=initiative,
                        llm_model=model
                    )
                    
                    initiative.log_activity(
                        action='requirement_added',
                        details=f'KI hat {created_count} Requirements aus {len(files_found)} Dokumenten generiert',
                        actor='cascade'
                    )
                    
                    messages.success(request, f'✅ {created_count} Requirements wurden generiert!')
                    return redirect('control_center:initiative-detail', pk=pk)
                    
                except json.JSONDecodeError:
                    pass
            
            # Fallback: Save raw response as feedback
            initiative.log_activity(
                action='analysis_started',
                details=f'KI-Analyse abgeschlossen (kein strukturiertes Ergebnis): {response_text[:500]}...',
                actor='cascade'
            )
            messages.warning(request, 'Analyse abgeschlossen, aber keine Requirements extrahiert. Siehe Aktivitäten.')
            
        else:
            messages.error(request, f'LLM-Fehler: {result.get("error", "Unbekannt")}')
            
    except Exception as e:
        messages.error(request, f'Fehler bei der Analyse: {str(e)}')
        initiative.log_activity(
            action='error',
            details=f'Recherche-Fehler: {str(e)}',
            actor='system'
        )
    
    return redirect('control_center:initiative-detail', pk=pk)


@login_required
def initiative_research_status(request, pk):
    """Get current research/analysis status for an initiative."""
    from apps.bfagent.models_testing import MCPUsageLog
    
    initiative = get_object_or_404(Initiative, pk=pk)
    
    # Get recent MCP logs for this initiative
    recent_logs = MCPUsageLog.objects.filter(
        initiative=initiative
    ).order_by('-created_at')[:5]
    
    # Get requirement count
    req_count = initiative.requirements.count()
    
    return JsonResponse({
        'initiative_id': str(pk),
        'workflow_phase': initiative.workflow_phase,
        'requirement_count': req_count,
        'recent_activity': [
            {
                'tool': log.tool_name,
                'status': log.status,
                'summary': log.result_summary,
                'created_at': log.created_at.isoformat()
            }
            for log in recent_logs
        ]
    })
