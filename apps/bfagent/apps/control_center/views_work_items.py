# -*- coding: utf-8 -*-
"""
Control Center - Unified Work Items Views

Ersetzt die fragmentierten Test Studio + Feature Planning Views
mit einem einheitlichen Work Item Management System.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.core.paginator import Paginator
from django.utils import timezone

from apps.core.models import (
    WorkItem,
    WorkItemType,
    WorkItemStatus,
    WorkItemPriority,
    LLMTier,
    BugDetails,
    FeatureDetails,
    TaskDetails,
    WorkItemLLMAssignment,
    WorkItemComment,
)
from apps.bfagent.models_domains import DomainArt


# =============================================================================
# DASHBOARD & LIST VIEWS
# =============================================================================

@require_http_methods(["GET"])
def work_items_dashboard(request: HttpRequest) -> HttpResponse:
    """
    Unified Work Items Dashboard
    Zeigt Übersicht aller Work Items mit Statistiken
    """
    
    # Statistiken
    total = WorkItem.objects.count()
    by_type = {
        'bugs': WorkItem.objects.filter(item_type=WorkItemType.BUG).count(),
        'features': WorkItem.objects.filter(item_type=WorkItemType.FEATURE).count(),
        'tasks': WorkItem.objects.filter(item_type=WorkItemType.TASK).count(),
        'other': WorkItem.objects.exclude(
            item_type__in=[WorkItemType.BUG, WorkItemType.FEATURE, WorkItemType.TASK]
        ).count(),
    }
    
    by_status = {}
    for status_code, status_label in WorkItemStatus.choices:
        by_status[status_code] = {
            'label': status_label,
            'count': WorkItem.objects.filter(status=status_code).count()
        }
    
    by_priority = {}
    for priority_code, priority_label in WorkItemPriority.choices:
        by_priority[priority_code] = {
            'label': priority_label,
            'count': WorkItem.objects.filter(priority=priority_code).count()
        }
    
    # Recent Items
    recent_items = WorkItem.objects.select_related(
        'domain', 'assigned_to', 'created_by'
    ).order_by('-created_at')[:10]
    
    # In Progress Items
    in_progress = WorkItem.objects.filter(
        status=WorkItemStatus.IN_PROGRESS
    ).select_related('domain', 'assigned_to')[:5]
    
    # Blocked Items
    blocked = WorkItem.objects.filter(
        status=WorkItemStatus.BLOCKED
    ).select_related('domain', 'assigned_to')[:5]
    
    context = {
        'total': total,
        'by_type': by_type,
        'by_status': by_status,
        'by_priority': by_priority,
        'recent_items': recent_items,
        'in_progress': in_progress,
        'blocked': blocked,
        'work_item_types': WorkItemType.choices,
        'work_item_statuses': WorkItemStatus.choices,
        'work_item_priorities': WorkItemPriority.choices,
    }
    
    return render(request, 'control_center/work_items/dashboard.html', context)


@require_http_methods(["GET"])
def work_items_list(request: HttpRequest, item_type: str = None) -> HttpResponse:
    """
    Liste aller Work Items mit Filter und Pagination
    """
    
    # Base queryset
    queryset = WorkItem.objects.select_related(
        'domain', 'assigned_to', 'created_by'
    ).order_by('-created_at')
    
    # Filter by type (from URL or query param)
    type_filter = item_type or request.GET.get('type', '')
    if type_filter:
        queryset = queryset.filter(item_type=type_filter)
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    # Filter by priority
    priority_filter = request.GET.get('priority', '')
    if priority_filter:
        queryset = queryset.filter(priority=priority_filter)
    
    # Filter by domain
    domain_filter = request.GET.get('domain', '')
    if domain_filter:
        queryset = queryset.filter(domain_id=domain_filter)
    
    # Search
    search = request.GET.get('q', '')
    if search:
        queryset = queryset.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(identifier__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(queryset, 25)
    page = request.GET.get('page', 1)
    items = paginator.get_page(page)
    
    # Filter options
    domains = DomainArt.objects.all()
    
    context = {
        'items': items,
        'type_filter': type_filter,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'domain_filter': domain_filter,
        'search': search,
        'domains': domains,
        'work_item_types': WorkItemType.choices,
        'work_item_statuses': WorkItemStatus.choices,
        'work_item_priorities': WorkItemPriority.choices,
    }
    
    return render(request, 'control_center/work_items/list.html', context)


@require_http_methods(["GET"])
def work_items_kanban(request: HttpRequest) -> HttpResponse:
    """
    Kanban Board für Work Items
    Gruppiert nach Status
    """
    
    # Filter by type
    type_filter = request.GET.get('type', '')
    
    # Get items per status column
    columns = {}
    kanban_statuses = [
        WorkItemStatus.BACKLOG,
        WorkItemStatus.TODO,
        WorkItemStatus.IN_PROGRESS,
        WorkItemStatus.IN_REVIEW,
        WorkItemStatus.TESTING,
        WorkItemStatus.DONE,
    ]
    
    for status in kanban_statuses:
        queryset = WorkItem.objects.filter(status=status).select_related(
            'domain', 'assigned_to'
        ).order_by('-priority', '-created_at')[:20]
        
        if type_filter:
            queryset = queryset.filter(item_type=type_filter)
        
        columns[status] = {
            'label': WorkItemStatus(status).label,
            'items': list(queryset),
            'count': queryset.count(),
        }
    
    context = {
        'columns': columns,
        'type_filter': type_filter,
        'work_item_types': WorkItemType.choices,
        'kanban_statuses': kanban_statuses,
    }
    
    return render(request, 'control_center/work_items/kanban.html', context)


# =============================================================================
# DETAIL & CRUD VIEWS
# =============================================================================

@require_http_methods(["GET"])
def work_item_detail(request: HttpRequest, pk) -> HttpResponse:
    """Detail View für ein Work Item"""
    
    item = get_object_or_404(
        WorkItem.objects.select_related(
            'domain', 'assigned_to', 'created_by', 'parent', 'llm_override'
        ),
        pk=pk
    )
    
    # Get type-specific details
    bug_details = None
    feature_details = None
    task_details = None
    
    if item.item_type == WorkItemType.BUG:
        bug_details = getattr(item, 'bug_details', None)
    elif item.item_type == WorkItemType.FEATURE:
        feature_details = getattr(item, 'feature_details', None)
    elif item.item_type == WorkItemType.TASK:
        task_details = getattr(item, 'task_details', None)
    
    # Get comments
    comments = item.comments.select_related('author').order_by('-created_at')[:20]
    
    # Get LLM assignments
    llm_assignments = item.llm_assignments.select_related('llm_used').order_by('-created_at')[:5]
    
    # Get children
    children = item.children.all()[:10]
    
    context = {
        'item': item,
        'bug_details': bug_details,
        'feature_details': feature_details,
        'task_details': task_details,
        'comments': comments,
        'llm_assignments': llm_assignments,
        'children': children,
        'work_item_statuses': WorkItemStatus.choices,
        'work_item_priorities': WorkItemPriority.choices,
        'llm_tiers': LLMTier.choices,
    }
    
    return render(request, 'control_center/work_items/detail.html', context)


@require_http_methods(["GET", "POST"])
def work_item_create(request: HttpRequest) -> HttpResponse:
    """Erstellt ein neues Work Item"""
    
    if request.method == 'POST':
        # Get form data
        item_type = request.POST.get('item_type', WorkItemType.TASK)
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        priority = request.POST.get('priority', WorkItemPriority.MEDIUM)
        domain_id = request.POST.get('domain', None)
        
        if not title:
            messages.error(request, 'Titel ist erforderlich')
            return redirect('work-item-create')
        
        # Create Work Item
        item = WorkItem.objects.create(
            item_type=item_type,
            title=title,
            description=description,
            priority=priority,
            domain_id=domain_id if domain_id else None,
            created_by=request.user if request.user.is_authenticated else None,
            status=WorkItemStatus.BACKLOG,
        )
        
        # Create type-specific details
        if item_type == WorkItemType.BUG:
            BugDetails.objects.create(
                work_item=item,
                url=request.POST.get('bug_url', ''),
                actual_behavior=request.POST.get('actual_behavior', ''),
                expected_behavior=request.POST.get('expected_behavior', ''),
                steps_to_reproduce=request.POST.get('steps_to_reproduce', ''),
            )
        elif item_type == WorkItemType.FEATURE:
            FeatureDetails.objects.create(
                work_item=item,
                user_story=request.POST.get('user_story', ''),
                specification=request.POST.get('specification', ''),
            )
        elif item_type == WorkItemType.TASK:
            estimated_hours = request.POST.get('estimated_hours', None)
            TaskDetails.objects.create(
                work_item=item,
                estimated_hours=float(estimated_hours) if estimated_hours else None,
            )
        
        messages.success(request, f'Work Item {item.identifier} erstellt')
        return redirect('work-item-detail', pk=item.pk)
    
    # GET - Show form
    domains = DomainArt.objects.all()
    
    context = {
        'domains': domains,
        'work_item_types': WorkItemType.choices,
        'work_item_priorities': WorkItemPriority.choices,
        'default_type': request.GET.get('type', WorkItemType.TASK),
    }
    
    return render(request, 'control_center/work_items/create.html', context)


# =============================================================================
# API ENDPOINTS (HTMX)
# =============================================================================

@require_POST
def work_item_update_status(request: HttpRequest, pk) -> HttpResponse:
    """Updates Work Item Status (HTMX)"""
    
    item = get_object_or_404(WorkItem, pk=pk)
    new_status = request.POST.get('status')
    
    if new_status and new_status in dict(WorkItemStatus.choices):
        item.status = new_status
        item.save()
        
        return HttpResponse(f'''
            <span class="badge bg-{'success' if new_status == 'done' else 'primary'}">
                {WorkItemStatus(new_status).label}
            </span>
        ''')
    
    return HttpResponse('Invalid status', status=400)


@require_POST
def work_item_update_priority(request: HttpRequest, pk) -> HttpResponse:
    """Updates Work Item Priority (HTMX)"""
    
    item = get_object_or_404(WorkItem, pk=pk)
    new_priority = request.POST.get('priority')
    
    if new_priority and new_priority in dict(WorkItemPriority.choices):
        item.priority = new_priority
        item.save()
        
        colors = {
            'critical': 'danger',
            'high': 'warning',
            'medium': 'info',
            'low': 'success',
        }
        
        return HttpResponse(f'''
            <span class="badge bg-{colors.get(new_priority, 'secondary')}">
                {WorkItemPriority(new_priority).label}
            </span>
        ''')
    
    return HttpResponse('Invalid priority', status=400)


@require_POST
def work_item_add_comment(request: HttpRequest, pk) -> HttpResponse:
    """Adds a comment to Work Item (HTMX)"""
    
    item = get_object_or_404(WorkItem, pk=pk)
    content = request.POST.get('content', '').strip()
    comment_type = request.POST.get('comment_type', 'comment')
    
    if not content:
        return HttpResponse('Comment content required', status=400)
    
    comment = WorkItemComment.objects.create(
        work_item=item,
        content=content,
        comment_type=comment_type,
        author=request.user if request.user.is_authenticated else None,
    )
    
    return render(request, 'control_center/work_items/partials/comment.html', {
        'comment': comment
    })


@require_POST
def work_item_assign_llm(request: HttpRequest, pk) -> HttpResponse:
    """Creates LLM Assignment for Work Item"""
    
    item = get_object_or_404(WorkItem, pk=pk)
    
    # Auto-classify if not already done
    if not item.llm_tier:
        item._auto_classify()
        item.save()
    
    # Create assignment
    assignment = WorkItemLLMAssignment.objects.create(
        work_item=item,
        initial_tier=item.llm_tier or LLMTier.TIER_2,
        current_tier=item.llm_tier or LLMTier.TIER_2,
        status=WorkItemLLMAssignment.Status.PENDING,
    )
    
    return JsonResponse({
        'success': True,
        'assignment_id': str(assignment.id),
        'tier': assignment.current_tier,
    })


@require_http_methods(["GET"])
def work_item_cascade_context(request: HttpRequest, pk) -> JsonResponse:
    """
    Returns Work Item context for Cascade AI integration
    Used by MCP tools
    """
    
    item = get_object_or_404(
        WorkItem.objects.select_related('domain'),
        pk=pk
    )
    
    context = {
        'id': str(item.id),
        'identifier': item.identifier,
        'type': item.item_type,
        'title': item.title,
        'description': item.description,
        'status': item.status,
        'priority': item.priority,
        'domain': item.domain.slug if item.domain else None,
        'llm_tier': item.llm_tier,
        'complexity': item.get_effective_complexity(),
        'tags': item.tags,
    }
    
    # Add type-specific details
    if item.item_type == WorkItemType.BUG:
        try:
            bug = item.bug_details
            context['bug'] = {
                'url': bug.url,
                'actual_behavior': bug.actual_behavior,
                'expected_behavior': bug.expected_behavior,
                'steps_to_reproduce': bug.steps_to_reproduce,
            }
        except BugDetails.DoesNotExist:
            pass
    
    elif item.item_type == WorkItemType.FEATURE:
        try:
            feature = item.feature_details
            context['feature'] = {
                'user_story': feature.user_story,
                'specification': feature.specification,
                'module_path': feature.module_path,
            }
        except FeatureDetails.DoesNotExist:
            pass
    
    return JsonResponse(context)
