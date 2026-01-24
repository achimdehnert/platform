"""
Test Studio Views - Test Requirements Management & Test Generation
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.contrib import messages
import json

from apps.bfagent.models_testing import (
    TestRequirement,
    TestCase,
    RequirementTestLink,
    TestExecution,
    TestCoverageReport,
    RequirementFeedback,
)
from apps.bfagent.handlers.test_generation_handler import TestGenerationHandler


@login_required
def requirements_list(request):
    """List all test requirements with optional domain, category, priority, status filter and search"""
    from django.db.models import Q
    
    requirements = TestRequirement.objects.all()
    
    # Text search (name, description)
    search_query = request.GET.get('q', '').strip()
    if search_query:
        requirements = requirements.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(notes__icontains=search_query)
        )
    
    # Domain filter (Cross-Domain Support)
    current_domain = request.GET.get('domain', '')
    if current_domain:
        requirements = requirements.filter(domain=current_domain)
    
    # Category filter (Bugs/Features/Enhancements)
    current_category = request.GET.get('category', '')
    if current_category:
        requirements = requirements.filter(category=current_category)
    
    # Priority filter
    current_priority = request.GET.get('priority', '')
    if current_priority:
        requirements = requirements.filter(priority=current_priority)
    
    # Status filter - exclude done/completed by default unless explicitly requested
    current_status = request.GET.get('status', '')
    show_completed = request.GET.get('show_completed', '')
    if current_status:
        requirements = requirements.filter(status=current_status)
    elif not show_completed:
        # Hide completed/done/obsolete items by default
        requirements = requirements.exclude(status__in=['done', 'completed', 'archived', 'obsolete'])
    
    # Sort by priority (critical first), then by date
    priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    requirements = sorted(requirements, key=lambda r: (priority_order.get(r.priority, 99), -r.created_at.timestamp()))
    
    # Count by category (for tabs) - must respect ALL active filters
    base_qs = TestRequirement.objects.all()
    if current_domain:
        base_qs = base_qs.filter(domain=current_domain)
    # Apply status filter to counts (same logic as display filter)
    if current_status:
        base_qs = base_qs.filter(status=current_status)
    elif not show_completed:
        base_qs = base_qs.exclude(status__in=['done', 'completed', 'archived', 'obsolete'])
    # Apply priority filter to counts
    if current_priority:
        base_qs = base_qs.filter(priority=current_priority)
    
    counts = {
        'total': base_qs.count(),
        'bugs': base_qs.filter(category='bug_fix').count(),
        'features': base_qs.filter(category='feature').count(),
        'enhancements': base_qs.filter(category='enhancement').count(),
    }
    
    # Add coverage data and status tracking
    from apps.bfagent.models_testing import RequirementFeedback
    
    requirements_data = []
    for req in requirements:
        coverage, _ = TestCoverageReport.objects.get_or_create(requirement=req)
        coverage.update_coverage()
        
        # Get latest feedback/status updates for tracking
        latest_feedback = req.feedbacks.filter(
            feedback_type__in=['progress', 'solution', 'blocker']
        ).first()
        
        # Get last status change from notes or feedback
        last_activity = req.feedbacks.first()
        
        requirements_data.append({
            'requirement': req,
            'coverage': coverage,
            'latest_feedback': latest_feedback,
            'last_activity': last_activity,
            'feedback_count': req.feedbacks.count(),
        })
    
    return render(request, 'bfagent/test_studio/requirements_list.html', {
        'requirements_data': requirements_data,
        'current_domain': current_domain,
        'current_category': current_category,
        'current_priority': current_priority,
        'current_status': current_status,
        'search_query': search_query,
        'counts': counts,
    })


@login_required
def requirements_kanban(request):
    """Kanban board view for test requirements"""
    from apps.bfagent.models_cascade import CascadeWorkSession
    
    requirements = TestRequirement.objects.all()
    
    # Category filter
    current_category = request.GET.get('category', '')
    if current_category:
        requirements = requirements.filter(category=current_category)
    
    # Get active cascade sessions
    active_sessions = {
        str(s.requirement_id): s 
        for s in CascadeWorkSession.objects.filter(status__in=['pending', 'running'])
    }
    
    # Sort by priority
    priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    
    # Group by status into columns
    columns = {
        'draft': [],
        'ready': [],
        'in_progress': [],
        'done': [],
    }
    
    for req in requirements:
        # Add cascade session info
        session = active_sessions.get(str(req.id))
        if session:
            req.cascade_session = session
            req.cascade_status = f"{session.current_iteration}/{session.max_iterations}"
        else:
            req.cascade_session = None
            req.cascade_status = None
        
        status = req.status if req.status in columns else 'draft'
        columns[status].append(req)
    
    # Sort each column by priority
    for status in columns:
        columns[status] = sorted(columns[status], key=lambda r: priority_order.get(r.priority, 99))
    
    return render(request, 'bfagent/test_studio/requirements_kanban.html', {
        'columns': columns,
        'current_category': current_category,
    })


@login_required
def requirement_create(request):
    """Create new test requirement"""
    from apps.bfagent.models_domains import DomainArt
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        category = request.POST.get('category', 'feature')
        priority = request.POST.get('priority', 'medium')
        domain = request.POST.get('domain', 'core')  # Cross-domain support
        # Support both 'url' and 'source_url' (from bug reporter modal)
        url = request.POST.get('url') or request.POST.get('source_url', '')
        
        # Parse acceptance criteria from JSON
        criteria_json = request.POST.get('acceptance_criteria', '[]')
        try:
            acceptance_criteria = json.loads(criteria_json)
        except (json.JSONDecodeError, ValueError):
            acceptance_criteria = []
        
        requirement = TestRequirement.objects.create(
            name=name,
            description=description,
            category=category,
            priority=priority,
            domain=domain,
            url=url,
            acceptance_criteria=acceptance_criteria,
            created_by=request.user,
        )
        
        # Check if AJAX request (from hotbutton)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            from django.urls import reverse
            return JsonResponse({
                'success': True,
                'message': f'Requirement "{name}" erstellt!',
                'redirect_url': reverse('control_center:test-studio-requirement-detail', kwargs={'pk': requirement.id}),
                'requirement_id': str(requirement.id),
            })
        
        messages.success(request, f'Requirement "{name}" created!')
        return redirect('control_center:test-studio-requirement-detail', pk=requirement.id)
    
    # Get available domains from database
    available_domains = DomainArt.objects.filter(is_active=True).order_by('display_name')
    
    # Pre-select category from URL parameter (e.g., ?category=enhancement)
    preselect_category = request.GET.get('category', '')
    
    return render(request, 'bfagent/test_studio/requirement_form.html', {
        'available_domains': available_domains,
        'preselect_category': preselect_category,
    })


@login_required
def requirement_detail(request, pk):
    """View requirement details with activity dashboard"""
    from apps.bfagent.models_testing import RequirementFeedback, MCPUsageLog
    
    requirement = get_object_or_404(TestRequirement, pk=pk)
    coverage, _ = TestCoverageReport.objects.get_or_create(requirement=requirement)
    coverage.update_coverage()
    
    # Get test links
    test_links = RequirementTestLink.objects.filter(
        requirement=requirement
    ).select_related('test_case')
    
    # Organize by criterion
    criteria_with_tests = []
    for idx, criterion in enumerate(requirement.acceptance_criteria):
        criterion_id = criterion.get('id', f'crit_{idx}')
        links = [link for link in test_links if link.criterion_id == criterion_id]
        
        criteria_with_tests.append({
            'id': criterion_id,
            'criterion': criterion,
            'links': links,
            'test_count': len(links),
            'status': links[0].status if links else 'pending',
        })
    
    # Get feedbacks (newest first for activity dashboard)
    feedbacks = RequirementFeedback.objects.filter(
        requirement=requirement
    ).select_related('author').order_by('-created_at')
    feedback_types = RequirementFeedback.FeedbackType.choices
    
    # MCP Stats for activity dashboard
    mcp_stats = None
    try:
        mcp_logs = MCPUsageLog.objects.filter(requirement=requirement)
        total = mcp_logs.count()
        if total > 0:
            success = mcp_logs.filter(status='success').count()
            error = mcp_logs.filter(status='error').count()
            mcp_stats = {
                'total_calls': total,
                'success_count': success,
                'error_count': error,
                'success_rate': (success / total * 100) if total > 0 else 0,
            }
    except Exception:
        pass
    
    # LLM Assignment für Hybrid-Workflow (nur für Bug-Fixes)
    llm_assignment = None
    estimated_cost = 0.01
    if requirement.category == 'bug_fix':
        from apps.bfagent.models_testing import BugLLMAssignment
        llm_assignment = BugLLMAssignment.objects.filter(requirement=requirement).first()
        
        # Kosten-Schätzung basierend auf Tier
        if llm_assignment:
            tier_costs = {'tier_1': 0.002, 'tier_2': 0.01, 'tier_3': 0.05}
            estimated_cost = tier_costs.get(llm_assignment.current_tier, 0.01)
    
    # Available LLMs für Code Refactoring
    from apps.bfagent.models import Llms
    available_llms = Llms.objects.filter(is_active=True).values('id', 'name')
    
    return render(request, 'bfagent/test_studio/requirement_detail.html', {
        'requirement': requirement,
        'coverage': coverage,
        'criteria_with_tests': criteria_with_tests,
        'feedbacks': feedbacks,
        'feedback_types': feedback_types,
        'mcp_stats': mcp_stats,
        'llm_assignment': llm_assignment,
        'estimated_cost': estimated_cost,
        'available_llms': available_llms,
    })


@login_required
@require_http_methods(["POST"])
def requirement_status_change(request, pk):
    """
    API endpoint to change requirement status.
    Used by status buttons on detail page.
    """
    requirement = get_object_or_404(TestRequirement, pk=pk)
    
    try:
        data = json.loads(request.body)
        new_status = data.get('status')
        
        valid_statuses = ['draft', 'ready', 'in_progress', 'done', 'completed', 'blocked', 'obsolete', 'archived']
        if new_status not in valid_statuses:
            return JsonResponse({'success': False, 'error': f'Invalid status: {new_status}'})
        
        old_status = requirement.status
        requirement.status = new_status
        requirement.save()
        
        # Create ChangelogEntry when requirement is completed
        changelog_created = False
        if new_status in ['done', 'completed'] and old_status not in ['done', 'completed']:
            try:
                from apps.bfagent.models_documentation import ChangelogEntry
                # Only create if no entry exists yet
                if not hasattr(requirement, 'changelog_entry') or requirement.changelog_entry is None:
                    ChangelogEntry.create_from_requirement(requirement)
                    changelog_created = True
            except Exception as e:
                # Don't fail the status change if changelog fails
                pass
        
        return JsonResponse({
            'success': True,
            'message': f'Status changed to {new_status}',
            'new_status': new_status,
            'changelog_created': changelog_created,
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'})


@login_required
@require_http_methods(["POST"])
def requirement_update_tier(request, pk):
    """
    API endpoint to update LLM tier for a requirement (Hybrid-Workflow).
    """
    from apps.bfagent.models_testing import BugLLMAssignment
    from apps.bfagent.services.bug_llm_router import BugLLMRouter
    
    requirement = get_object_or_404(TestRequirement, pk=pk)
    
    try:
        data = json.loads(request.body)
        new_tier = data.get('tier', 'tier_1')
        
        valid_tiers = ['tier_1', 'tier_2', 'tier_3']
        if new_tier not in valid_tiers:
            return JsonResponse({'success': False, 'error': f'Invalid tier: {new_tier}'})
        
        # Assignment holen oder erstellen
        assignment = BugLLMAssignment.objects.filter(requirement=requirement).first()
        
        if not assignment:
            router = BugLLMRouter()
            assignment = router.create_assignment(requirement)
        
        # Tier aktualisieren
        assignment.current_tier = new_tier
        assignment.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Tier updated to {new_tier}',
            'tier': new_tier,
            'requirement_name': requirement.name,
            'description': requirement.description,
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["POST"])
def requirement_update_status(request, pk):
    """
    API endpoint to update requirement status (draft, ready, in_progress, done, obsolete).
    """
    requirement = get_object_or_404(TestRequirement, pk=pk)
    
    try:
        data = json.loads(request.body)
        new_status = data.get('status')
        
        valid_statuses = ['draft', 'ready', 'in_progress', 'done', 'completed', 'blocked', 'obsolete', 'archived']
        if new_status not in valid_statuses:
            return JsonResponse({'success': False, 'error': f'Invalid status: {new_status}'})
        
        old_status = requirement.status
        requirement.status = new_status
        requirement.save()
        
        # Log the status change
        RequirementFeedback.objects.create(
            requirement=requirement,
            feedback_type='progress',
            content=f'Status geändert: {old_status} → {new_status}',
            author=request.user if request.user.is_authenticated else None
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Status updated to {new_status}',
            'status': new_status,
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["POST"])
def requirement_update_doc_status(request, pk):
    """
    API endpoint to update documentation status for a requirement.
    """
    requirement = get_object_or_404(TestRequirement, pk=pk)
    
    try:
        data = json.loads(request.body)
        new_status = data.get('doc_status')
        
        valid_statuses = ['not_checked', 'exists', 'needs_update', 'needs_creation', 'updated', 'created']
        if new_status not in valid_statuses:
            return JsonResponse({'success': False, 'error': f'Invalid doc_status: {new_status}'})
        
        requirement.doc_status = new_status
        requirement.doc_checked_at = timezone.now()
        requirement.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Documentation status updated to {new_status}',
            'doc_status': new_status,
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'})


@login_required
@require_http_methods(["POST"])
def requirement_update_doc_notes(request, pk):
    """
    API endpoint to update documentation notes for a requirement.
    """
    requirement = get_object_or_404(TestRequirement, pk=pk)
    
    try:
        data = json.loads(request.body)
        notes = data.get('doc_notes', '')
        
        requirement.doc_notes = notes
        requirement.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Documentation notes saved',
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'})


@login_required
@require_http_methods(["POST"])
def requirement_add_feedback(request, pk):
    """
    API endpoint to add feedback to a requirement.
    Supports both JSON and FormData (for file uploads).
    """
    from apps.bfagent.models_testing import RequirementFeedback
    
    requirement = get_object_or_404(TestRequirement, pk=pk)
    
    # Check if it's FormData or JSON
    content_type = request.content_type or ''
    
    if 'multipart/form-data' in content_type:
        # FormData submission (with potential file upload)
        content = request.POST.get('content', '').strip()
        feedback_type = request.POST.get('feedback_type', 'comment')
        screenshot = request.FILES.get('screenshot')
    else:
        # JSON submission
        try:
            data = json.loads(request.body)
            content = data.get('content', '').strip()
            feedback_type = data.get('feedback_type', 'comment')
            screenshot = None
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'})
    
    if not content:
        return JsonResponse({'success': False, 'error': 'Content is required'})
    
    valid_types = [t[0] for t in RequirementFeedback.FeedbackType.choices]
    if feedback_type not in valid_types:
        feedback_type = 'comment'
    
    feedback = RequirementFeedback.objects.create(
        requirement=requirement,
        author=request.user,
        content=content,
        feedback_type=feedback_type,
        screenshot=screenshot,
        is_from_cascade=False
    )
    
    return JsonResponse({
        'success': True,
        'message': 'Feedback added',
        'feedback': {
            'id': feedback.id,
            'content': feedback.content,
            'feedback_type': feedback.feedback_type,
            'feedback_type_display': feedback.get_feedback_type_display(),
            'author': feedback.author.username if feedback.author else 'Anonymous',
            'created_at': feedback.created_at.strftime('%d.%m.%Y %H:%M'),
            'has_screenshot': bool(feedback.screenshot),
            'screenshot_url': feedback.screenshot.url if feedback.screenshot else None,
        }
    })


@login_required
@require_http_methods(["POST"])
def feedback_delete(request, feedback_id):
    """
    API endpoint to delete a feedback entry.
    Only the author can delete their own feedback.
    """
    from apps.bfagent.models_testing import RequirementFeedback
    
    feedback = get_object_or_404(RequirementFeedback, pk=feedback_id)
    
    # Check ownership
    if feedback.author != request.user and not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Keine Berechtigung'})
    
    feedback.delete()
    return JsonResponse({'success': True, 'message': 'Feedback gelöscht'})


@login_required
@require_http_methods(["POST"])
def requirement_delete(request, pk):
    """
    API endpoint to delete a requirement.
    """
    requirement = get_object_or_404(TestRequirement, pk=pk)
    name = requirement.name
    
    try:
        requirement.delete()
        return JsonResponse({
            'success': True,
            'message': f'Requirement "{name}" gelöscht',
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["POST"])
def requirement_update(request, pk):
    """
    API endpoint to update requirement fields (name, description).
    """
    requirement = get_object_or_404(TestRequirement, pk=pk)
    
    try:
        data = json.loads(request.body)
        
        if 'name' in data:
            requirement.name = data['name'].strip()
        if 'description' in data:
            requirement.description = data['description']
        
        requirement.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Requirement aktualisiert',
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def requirement_cascade_context(request, pk):
    """
    API endpoint for Cascade button - returns full requirement context as JSON.
    Used by the 'Cascade arbeite daran' button to generate complete task context.
    """
    requirement = get_object_or_404(TestRequirement, pk=pk)
    
    # Build acceptance criteria text
    criteria_text = ""
    for idx, criterion in enumerate(requirement.acceptance_criteria, 1):
        scenario = criterion.get('scenario', criterion.get('then', 'Unbenannt'))
        given = criterion.get('given', '')
        when = criterion.get('when', '')
        then = criterion.get('then', '')
        
        if given or when or then:
            criteria_text += f"\n{idx}. **{scenario}**\n"
            if given:
                criteria_text += f"   - Given: {given}\n"
            if when:
                criteria_text += f"   - When: {when}\n"
            if then:
                criteria_text += f"   - Then: {then}\n"
        else:
            criteria_text += f"\n{idx}. {scenario}\n"
    
    # Get feedbacks for this requirement
    from apps.bfagent.models_testing import RequirementFeedback
    feedbacks = RequirementFeedback.objects.filter(requirement=requirement).order_by('-created_at')
    
    feedbacks_text = ""
    open_questions = []
    blockers = []
    
    for fb in feedbacks:
        author = fb.author.username if fb.author else 'Cascade'
        fb_type = fb.get_feedback_type_display()
        feedbacks_text += f"\n- [{fb_type}] {author} ({fb.created_at:%d.%m.%Y %H:%M}): {fb.content}"
        
        if fb.feedback_type == 'question':
            open_questions.append(fb.content)
        elif fb.feedback_type == 'blocker':
            blockers.append(fb.content)
    
    # Build Initiative context if linked
    initiative_context = None
    if requirement.initiative:
        ini = requirement.initiative
        initiative_context = {
            'id': str(ini.pk),
            'title': ini.title,
            'description': ini.description or '',
            'analysis': ini.analysis or '',
            'concept': ini.concept or '',
            'workflow_phase': ini.workflow_phase,
            'detail_url': request.build_absolute_uri(f'/control-center/initiatives/{ini.pk}/'),
        }
    
    # Build context for Cascade
    context_data = {
        'id': str(requirement.id),
        'name': requirement.name,
        'domain': requirement.domain,
        'category': requirement.category,
        'priority': requirement.priority,
        'status': requirement.status,
        'description': requirement.description or '',
        'acceptance_criteria': criteria_text or 'Keine Akzeptanzkriterien definiert.',
        'url': requirement.url or '',
        'actual_behavior': requirement.actual_behavior or '',
        'expected_behavior': requirement.expected_behavior or '',
        'detail_url': request.build_absolute_uri(f'/control-center/test-studio/requirements/{requirement.id}/'),
        'created_at': requirement.created_at.strftime('%Y-%m-%d %H:%M') if requirement.created_at else '',
        'tags': requirement.tags or [],
        # Feedback integration
        'feedbacks': feedbacks_text if feedbacks_text else 'Kein Feedback vorhanden.',
        'open_questions': open_questions,
        'blockers': blockers,
        'feedback_count': feedbacks.count(),
        # Initiative context
        'initiative': initiative_context,
    }
    
    return JsonResponse(context_data)


@login_required
def open_feedbacks_api(request):
    """
    API endpoint to get all open questions and blockers across all requirements.
    Used by Cascade to fetch work items.
    """
    from apps.bfagent.models_testing import RequirementFeedback
    
    # Get open questions and blockers
    open_items = RequirementFeedback.objects.filter(
        feedback_type__in=['question', 'blocker']
    ).select_related('requirement', 'author').order_by('-created_at')[:20]
    
    items = []
    for fb in open_items:
        items.append({
            'id': fb.id,
            'type': fb.feedback_type,
            'type_display': fb.get_feedback_type_display(),
            'content': fb.content,
            'requirement_id': str(fb.requirement.id),
            'requirement_name': fb.requirement.name,
            'author': fb.author.username if fb.author else 'Anonymous',
            'created_at': fb.created_at.strftime('%d.%m.%Y %H:%M'),
            'url': f'/control-center/test-studio/requirements/{fb.requirement.id}/',
        })
    
    # Summary for Cascade
    blockers = [i for i in items if i['type'] == 'blocker']
    questions = [i for i in items if i['type'] == 'question']
    
    summary = f"## Offene Arbeit\n\n"
    
    if blockers:
        summary += f"### 🔴 {len(blockers)} Blocker\n"
        for b in blockers:
            summary += f"- **{b['requirement_name']}**: {b['content'][:100]}...\n"
    
    if questions:
        summary += f"\n### ❓ {len(questions)} Fragen\n"
        for q in questions:
            summary += f"- **{q['requirement_name']}**: {q['content'][:100]}...\n"
    
    return JsonResponse({
        'items': items,
        'blocker_count': len(blockers),
        'question_count': len(questions),
        'summary': summary,
    })


@login_required
@require_http_methods(["POST"])
def generate_test(request, requirement_id, criterion_index):
    """Generate test from acceptance criterion"""
    requirement = get_object_or_404(TestRequirement, pk=requirement_id)
    
    # Get criterion
    if criterion_index >= len(requirement.acceptance_criteria):
        return JsonResponse({'success': False, 'error': 'Invalid criterion index'})
    
    criterion = requirement.acceptance_criteria[criterion_index]
    criterion_id = criterion.get('id', f'crit_{criterion_index}')
    framework = request.POST.get('framework', 'robot')
    
    # Generate test using handler
    handler = TestGenerationHandler()
    result = handler.execute({
        'requirement': requirement,
        'criterion': criterion,
        'framework': framework
    })
    
    if not result['success']:
        return JsonResponse(result)
    
    # Create test case
    test_case = TestCase.objects.create(
        test_id=f"test_{requirement.id}_{criterion_id}",
        name=criterion.get('scenario', 'Unnamed Test'),
        description=f"Auto-generated from requirement: {requirement.name}",
        framework=framework,
        test_type=criterion.get('test_type', 'integration'),
        test_code=result['test_code'],
        file_path=result['file_path'],
        is_auto_generated=True,
        generation_metadata={'requirement_id': str(requirement.id), 'criterion_id': criterion_id},
        tags=requirement.tags + [framework, 'auto-generated'],
    )
    
    # Create link
    link, _ = RequirementTestLink.objects.update_or_create(
        requirement=requirement,
        criterion_id=criterion_id,
        defaults={
            'test_case': test_case,
            'link_type': 'auto',
            'status': 'implemented',
        }
    )
    
    # Update coverage
    coverage, _ = TestCoverageReport.objects.get_or_create(requirement=requirement)
    coverage.update_coverage()
    
    return JsonResponse({
        'success': True,
        'test_case_id': str(test_case.id),
        'test_code': result['test_code'],
        'file_path': result['file_path'],
        'coverage_percentage': coverage.coverage_percentage,
    })


@login_required
def test_case_detail(request, pk):
    """View test case details and execution history"""
    from apps.bfagent.models_testing import TestCaseFeedback
    
    test_case = get_object_or_404(TestCase, pk=pk)
    
    # Get last 10 executions
    executions = TestExecution.objects.filter(
        test_case=test_case
    ).select_related('executed_by').order_by('-executed_at')[:10]
    
    # Get linked requirement (if exists)
    requirement = None
    try:
        link = test_case.requirement_links.first()
        if link:
            requirement = link.requirement
    except Exception:
        pass
    
    # Attach requirement to test_case for template
    test_case.requirement = requirement
    
    # Get feedbacks
    feedbacks = TestCaseFeedback.objects.filter(test_case=test_case).select_related('author')
    feedback_types = TestCaseFeedback.FeedbackType.choices
    
    return render(request, 'bfagent/test_studio/test_case_detail.html', {
        'test_case': test_case,
        'executions': executions,
        'feedbacks': feedbacks,
        'feedback_types': feedback_types,
    })


@login_required
@require_http_methods(["POST"])
def testcase_add_feedback(request, pk):
    """
    API endpoint to add feedback to a test case.
    Supports both JSON and FormData (for file uploads).
    """
    from apps.bfagent.models_testing import TestCaseFeedback
    
    test_case = get_object_or_404(TestCase, pk=pk)
    
    content_type = request.content_type or ''
    
    if 'multipart/form-data' in content_type:
        content = request.POST.get('content', '').strip()
        feedback_type = request.POST.get('feedback_type', 'comment')
        screenshot = request.FILES.get('screenshot')
    else:
        try:
            data = json.loads(request.body)
            content = data.get('content', '').strip()
            feedback_type = data.get('feedback_type', 'comment')
            screenshot = None
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'})
    
    if not content:
        return JsonResponse({'success': False, 'error': 'Content is required'})
    
    valid_types = [t[0] for t in TestCaseFeedback.FeedbackType.choices]
    if feedback_type not in valid_types:
        feedback_type = 'comment'
    
    feedback = TestCaseFeedback.objects.create(
        test_case=test_case,
        author=request.user,
        content=content,
        feedback_type=feedback_type,
        screenshot=screenshot,
        is_from_cascade=False
    )
    
    return JsonResponse({
        'success': True,
        'message': 'Feedback added',
        'feedback': {
            'id': feedback.id,
            'content': feedback.content,
            'feedback_type': feedback.feedback_type,
            'feedback_type_display': feedback.get_feedback_type_display(),
            'author': feedback.author.username if feedback.author else 'Anonymous',
            'created_at': feedback.created_at.strftime('%d.%m.%Y %H:%M'),
            'has_screenshot': bool(feedback.screenshot),
            'screenshot_url': feedback.screenshot.url if feedback.screenshot else None,
        }
    })


@login_required
@require_http_methods(["POST"])
def testcase_feedback_delete(request, feedback_id):
    """
    API endpoint to delete a test case feedback entry.
    Only the author can delete their own feedback.
    """
    from apps.bfagent.models_testing import TestCaseFeedback
    
    feedback = get_object_or_404(TestCaseFeedback, pk=feedback_id)
    
    if feedback.author != request.user and not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Keine Berechtigung'})
    
    feedback.delete()
    return JsonResponse({'success': True, 'message': 'Feedback gelöscht'})


@login_required
def fix_plan_list(request):
    """List all fix plans"""
    from apps.bfagent.models_testing import BugFixPlan
    
    status_filter = request.GET.get('status', 'all')
    
    plans = BugFixPlan.objects.select_related(
        'requirement', 'created_by', 'approved_by'
    ).order_by('-created_at')
    
    if status_filter != 'all':
        plans = plans.filter(status=status_filter)
    
    return render(request, 'bfagent/test_studio/fix_plan_list.html', {
        'plans': plans,
        'status_filter': status_filter,
    })


@login_required
def fix_plan_detail(request, plan_id):
    """View fix plan details with handler code"""
    from apps.bfagent.models_testing import BugFixPlan
    
    plan = get_object_or_404(
        BugFixPlan.objects.select_related('requirement', 'created_by', 'approved_by'),
        pk=plan_id
    )
    
    return render(request, 'bfagent/test_studio/fix_plan_detail.html', {
        'plan': plan,
    })


@login_required
@require_http_methods(["POST"])
def approve_fix_plan(request, plan_id):
    """Approve a fix plan"""
    from apps.bfagent.models_testing import BugFixPlan
    from django.utils import timezone
    
    plan = get_object_or_404(BugFixPlan, pk=plan_id)
    
    if plan.status != 'pending':
        return JsonResponse({
            'success': False,
            'error': f'Cannot approve plan with status: {plan.status}'
        })
    
    plan.status = 'approved'
    plan.approved_by = request.user
    plan.approved_at = timezone.now()
    plan.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Fix plan approved',
        'status': plan.status
    })


@login_required
@require_http_methods(["POST"])
def reject_fix_plan(request, plan_id):
    """Reject a fix plan"""
    from apps.bfagent.models_testing import BugFixPlan
    
    plan = get_object_or_404(BugFixPlan, pk=plan_id)
    
    if plan.status != 'pending':
        return JsonResponse({
            'success': False,
            'error': f'Cannot reject plan with status: {plan.status}'
        })
    
    plan.status = 'rejected'
    plan.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Fix plan rejected',
        'status': plan.status
    })


@login_required
@require_http_methods(["POST"])
def execute_fix_plan(request, plan_id):
    """Execute an approved fix plan"""
    from apps.bfagent.models_testing import BugFixPlan
    from django.utils import timezone
    import traceback
    
    plan = get_object_or_404(BugFixPlan, pk=plan_id)
    
    if plan.status != 'approved':
        return JsonResponse({
            'success': False,
            'error': f'Can only execute approved plans. Current status: {plan.status}'
        })
    
    plan.status = 'executing'
    plan.save()
    
    try:
        # Execute the generated handler code
        exec_globals = {}
        exec(plan.handler_code, exec_globals)
        
        if 'execute_fix' not in exec_globals:
            raise Exception("Handler code missing execute_fix function")
        
        result = exec_globals['execute_fix']()
        
        if result.get('success'):
            plan.status = 'executed'
            plan.executed_at = timezone.now()
            plan.execution_result = result
            plan.execution_log = f"Successfully executed at {timezone.now()}"
            
            # Save rollback data if provided
            if 'rollback_id' in result:
                plan.rollback_data = {'rollback_id': result['rollback_id']}
            
            plan.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Fix executed successfully',
                'result': result
            })
        else:
            plan.status = 'failed'
            plan.execution_result = result
            plan.execution_log = f"Failed: {result.get('error', 'Unknown error')}"
            plan.save()
            
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Execution failed')
            })
            
    except Exception as e:
        plan.status = 'failed'
        plan.execution_log = traceback.format_exc()
        plan.save()
        
        return JsonResponse({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })


@login_required
@require_http_methods(["POST"])
def bug_to_test(request):
    """Convert bug report to test requirement or mark as fixed"""
    from apps.bfagent.handlers.bug_to_test_handler import BugToTestHandler
    
    try:
        # Parse bug report data
        url = request.POST.get('url', '')
        domain = request.POST.get('domain', 'core')  # Domain from form
        priority = request.POST.get('priority', 'medium')  # Priority from form
        actual_behavior = request.POST.get('actual_behavior', '')
        expected_behavior = request.POST.get('expected_behavior', '')
        screenshot = request.POST.get('screenshot', '')  # Base64
        console_logs = request.POST.get('console_logs', '')
        network_logs = request.POST.get('network_logs', '')
        action = request.POST.get('action', 'create_test')
        
        # Check if action is "mark_fixed"
        if action == 'mark_fixed':
            # Mark bug as fixed without creating test
            # Store in a simple BugReport table or update existing requirement
            from apps.bfagent.models import TestRequirement
            
            # Try to find existing requirement with same URL and behavior
            existing = TestRequirement.objects.filter(
                url=url,
                actual_behavior=actual_behavior
            ).first()
            
            if existing:
                existing.status = 'completed'
                existing.notes = f"Marked as fixed by {request.user.username}"
                existing.save()
                
                return JsonResponse({
                    'success': True,
                    'message': 'Bug marked as fixed',
                    'requirement_id': str(existing.id)
                })
            else:
                # Create new requirement with status "fixed"
                requirement = TestRequirement.objects.create(
                    name=f"Bug fix: {actual_behavior[:50]}...",
                    description=actual_behavior,
                    expected_behavior=expected_behavior,
                    url=url,
                    actual_behavior=actual_behavior,
                    domain=domain,
                    status='completed',
                    priority=priority,
                    category='bug_fix',
                    created_by=request.user,
                    notes=f"Directly marked as fixed by {request.user.username}"
                )
                
                return JsonResponse({
                    'success': True,
                    'message': 'Bug documented and marked as fixed',
                    'requirement_id': str(requirement.id)
                })
        
        # Default: Create test requirement
        handler = BugToTestHandler()
        result = handler.execute({
            'url': url,
            'domain': domain,
            'priority': priority,
            'actual_behavior': actual_behavior,
            'expected_behavior': expected_behavior,
            'screenshot': screenshot,
            'console_logs': console_logs,
            'network_logs': network_logs,
            'user': request.user
        })
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'requirement_id': result['requirement_id'],
                'test_case_id': result['test_case_id'],
                'message': result['message'],
                'redirect_url': f"/bookwriting/test-studio/requirements/{result['requirement_id']}/"
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Unknown error')
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_http_methods(["POST"])
def run_test(request, test_case_id):
    """Execute a test case"""
    from apps.bfagent.models import TestExecution
    import subprocess
    import tempfile
    import os
    import time
    from datetime import datetime
    
    test_case = get_object_or_404(TestCase, pk=test_case_id)
    
    try:
        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.robot', delete=False) as f:
            f.write(test_case.test_code)
            temp_file = f.name
        
        # Start timer
        start_time = time.time()
        
        # Execute test based on framework
        if test_case.framework == 'robot':
            result = subprocess.run(
                ['robot', '--outputdir', tempfile.gettempdir(), temp_file],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Parse results
            success = result.returncode == 0
            output = result.stdout + result.stderr
            
        elif test_case.framework == 'pytest':
            result = subprocess.run(
                ['pytest', '-v', temp_file],
                capture_output=True,
                text=True,
                timeout=60
            )
            success = result.returncode == 0
            output = result.stdout + result.stderr
            
        else:
            return JsonResponse({
                'success': False,
                'error': f'Framework {test_case.framework} not yet supported for execution'
            })
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Create execution record with FULL output
        execution = TestExecution.objects.create(
            test_case=test_case,
            result='passed' if success else 'failed',
            duration=float(duration) if duration else 1.0,
            error_message=output if not success else 'Test passed successfully',
            error_traceback=result.stderr if not success and result.stderr else '',
            log_file_path=temp_file,
            executed_by=request.user,
            execution_metadata={
                'framework': test_case.framework,
                'temp_file': temp_file,
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'full_output_length': len(output)
            }
        )
        
        # Update test case status
        test_case.status = 'passed' if success else 'failed'
        test_case.last_executed_at = datetime.now()
        test_case.save()
        
        # Clean up
        try:
            os.unlink(temp_file)
        except (OSError, PermissionError):
            pass
        
        return JsonResponse({
            'success': True,
            'execution_id': str(execution.id),
            'result': execution.result,
            'output': output[:1000],  # Send first 1000 chars
            'full_output_available': len(output) > 1000
        })
        
    except subprocess.TimeoutExpired:
        return JsonResponse({
            'success': False,
            'error': 'Test execution timed out (60s limit)'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_http_methods(["GET"])
def bugs_for_page(request):
    """Get all bugs for a specific page URL"""
    from apps.bfagent.models import TestRequirement
    
    try:
        url = request.GET.get('url', '')
        
        if not url:
            return JsonResponse({
                'success': False,
                'error': 'URL parameter required'
            })
        
        # Find all bug-related requirements for this URL
        bugs = TestRequirement.objects.filter(
            url__icontains=url,
            category='bug_fix'
        ).order_by('-created_at')
        
        # Format bugs data
        bugs_data = []
        for bug in bugs:
            bugs_data.append({
                'id': str(bug.id),
                'title': bug.name,
                'actual_behavior': bug.actual_behavior or bug.description or bug.name,
                'expected_behavior': bug.expected_behavior or '',
                'status': bug.status,
                'status_label': bug.get_status_display() if hasattr(bug, 'get_status_display') else bug.status.replace('_', ' ').title(),
                'priority': bug.priority,
                'created_at': bug.created_at.strftime('%Y-%m-%d %H:%M') if hasattr(bug, 'created_at') else '',
                'created_by': bug.created_by.username if bug.created_by else 'Unknown',
                'url': bug.url or ''
            })
        
        return JsonResponse({
            'success': True,
            'bugs': bugs_data,
            'count': len(bugs_data)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_http_methods(["POST"])
def fix_bug(request, bug_id):
    """Mark a bug as fixed"""
    from apps.bfagent.models import TestRequirement
    import json
    
    try:
        bug = get_object_or_404(TestRequirement, pk=bug_id)
        
        # Parse JSON body
        try:
            data = json.loads(request.body)
            new_status = data.get('status', 'fixed')
        except json.JSONDecodeError:
            new_status = 'fixed'
        
        # Update status
        old_status = bug.status
        bug.status = new_status
        
        # Add note about who fixed it
        if not bug.notes:
            bug.notes = ''
        bug.notes += f"\n[{request.user.username}] Marked as {new_status} from {old_status}"
        
        bug.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Bug #{bug_id} marked as {new_status}',
            'bug_id': bug_id,
            'old_status': old_status,
            'new_status': new_status
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@require_http_methods(["POST"])
def requirement_quick_status(request, pk):
    """Quick status change from list view"""
    from apps.bfagent.models_testing import RequirementFeedback
    
    try:
        requirement = get_object_or_404(TestRequirement, pk=pk)
        data = json.loads(request.body)
        new_status = data.get('status')
        
        if not new_status:
            return JsonResponse({'success': False, 'error': 'Status required'})
        
        old_status = requirement.status
        requirement.status = new_status
        
        # Add note about status change
        if not requirement.notes:
            requirement.notes = ''
        requirement.notes += f"\n[{request.user.username}] Status: {old_status} → {new_status}"
        
        requirement.save()
        
        # Create feedback entry for status tracking
        RequirementFeedback.objects.create(
            requirement=requirement,
            author=request.user,
            feedback_type='progress',
            content=f"Status geändert: {old_status} → {new_status}",
            is_from_cascade=False
        )
        
        return JsonResponse({
            'success': True,
            'old_status': old_status,
            'new_status': new_status
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_http_methods(["DELETE"])
def requirement_quick_delete(request, pk):
    """Quick delete from list view"""
    try:
        requirement = get_object_or_404(TestRequirement, pk=pk)
        name = requirement.name
        requirement.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Requirement "{name}" deleted'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
