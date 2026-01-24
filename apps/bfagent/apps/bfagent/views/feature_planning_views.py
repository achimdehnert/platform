"""
Feature Planning Dashboard Views - Django/HTMX
"""
from django.shortcuts import render, get_object_or_404
from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Count
from apps.bfagent.models_registry import ComponentRegistry, ComponentStatus, ComponentType


@require_http_methods(["GET"])
def feature_planning_dashboard(request: HttpRequest, domain_filter: str = None) -> HttpResponse:
    """Main Feature Planning Dashboard"""
    
    # Get filters
    status_filter = request.GET.get('status', '')
    type_filter = request.GET.get('type', '')
    priority_filter = request.GET.get('priority', '')
    owner_filter = request.GET.get('owner', '')
    
    # Base query
    features = ComponentRegistry.objects.all()
    
    # Domain filter (if domain-specific dashboard)
    if domain_filter:
        features = features.filter(domain=domain_filter)
    
    features = features.order_by('-proposed_at')
    
    # Apply filters
    if status_filter:
        features = features.filter(status=status_filter)
    
    if type_filter:
        features = features.filter(component_type=type_filter)
    
    if priority_filter:
        features = features.filter(priority=priority_filter)
    
    if owner_filter:
        features = features.filter(owner__username=owner_filter)
    
    # Get available filter options
    available_types = ComponentType.choices
    available_statuses = ComponentStatus.choices
    available_owners = (
        ComponentRegistry.objects
        .exclude(owner=None)
        .values_list('owner__username', flat=True)
        .distinct()
    )
    
    # Calculate statistics
    total_count = ComponentRegistry.objects.count()
    
    status_stats = {}
    for status_code, status_label in ComponentStatus.choices:
        count = ComponentRegistry.objects.filter(status=status_code).count()
        status_stats[status_code] = {'label': status_label, 'count': count}
    
    priority_stats = {}
    for priority in ['critical', 'high', 'medium', 'low', 'backlog']:
        count = ComponentRegistry.objects.filter(priority=priority).count()
        priority_stats[priority] = count
    
    # Dynamic URL names based on namespace
    namespace = request.resolver_match.namespace
    url_prefix = f'{namespace}:feature-planning'
    
    context = {
        'features': features[:100],  # Limit for performance
        'available_types': available_types,
        'available_statuses': available_statuses,
        'available_owners': available_owners,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'priority_filter': priority_filter,
        'owner_filter': owner_filter,
        'total_count': total_count,
        'status_stats': status_stats,
        'priority_stats': priority_stats,
        # Dynamic URLs - no hardcoding in templates!
        'url_list': f'{url_prefix}-list',
        'url_detail': f'{url_prefix}-detail',
        'url_create': f'{url_prefix}-create',
        'url_update': f'{url_prefix}-update',
        'url_delete': f'{url_prefix}-delete',
        'domain_filter': domain_filter,
    }
    
    return render(request, 'bfagent/feature_planning/dashboard.html', context)


@require_http_methods(["GET"])
def feature_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Feature detail view (HTMX partial)"""
    feature = get_object_or_404(ComponentRegistry, pk=pk)
    
    context = {
        'feature': feature,
    }
    
    return render(request, 'bfagent/feature_planning/detail_modal.html', context)


@require_http_methods(["GET"])
def feature_list_partial(request: HttpRequest, domain_filter: str = None) -> HttpResponse:
    """Feature list partial (HTMX) - Returns just the table rows"""
    
    # Same filtering logic as dashboard
    status_filter = request.GET.get('status', '')
    type_filter = request.GET.get('type', '')
    priority_filter = request.GET.get('priority', '')
    owner_filter = request.GET.get('owner', '')
    
    features = ComponentRegistry.objects.all()
    
    # Domain filter (if domain-specific dashboard)
    if domain_filter:
        features = features.filter(domain=domain_filter)
    
    features = features.order_by('-proposed_at')
    
    if status_filter:
        features = features.filter(status=status_filter)
    
    if type_filter:
        features = features.filter(component_type=type_filter)
    
    if priority_filter:
        features = features.filter(priority=priority_filter)
    
    if owner_filter:
        features = features.filter(owner__username=owner_filter)
    
    # Dynamic URL names based on namespace
    namespace = request.resolver_match.namespace
    url_prefix = f'{namespace}:feature-planning'
    
    context = {
        'features': features[:100],
        # Dynamic URLs - no hardcoding in templates!
        'url_detail': f'{url_prefix}-detail',
        'url_update': f'{url_prefix}-update',
        'url_delete': f'{url_prefix}-delete',
    }
    
    return render(request, 'bfagent/feature_planning/feature_list.html', context)


# Domain-specific wrappers for Book Writing domain
@require_http_methods(["GET"])
def feature_planning_dashboard_book(request: HttpRequest) -> HttpResponse:
    """Book Writing Domain Feature Planning Dashboard"""
    return feature_planning_dashboard(request, domain_filter='book')


@require_http_methods(["GET"])
def feature_list_partial_book(request: HttpRequest) -> HttpResponse:
    """Book Writing Domain Feature List Partial"""
    return feature_list_partial(request, domain_filter='book')


# ============================================================================
# CRUD OPERATIONS (Dashboard UI)
# ============================================================================

from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages


@login_required
@require_http_methods(["GET", "POST"])
def feature_create(request: HttpRequest) -> HttpResponse:
    """Create new feature (HTMX modal form)"""
    if request.method == "POST":
        # Create new feature
        name = request.POST.get('name')
        component_type = request.POST.get('component_type')
        description = request.POST.get('description', '')
        priority = request.POST.get('priority', 'medium')
        domain = request.POST.get('domain', '')
        
        # Generate identifier
        identifier = f"proposed.{component_type}.{name.lower().replace(' ', '_')}"
        
        feature = ComponentRegistry.objects.create(
            identifier=identifier,
            name=name,
            component_type=component_type,
            description=description,
            priority=priority,
            domain=domain,
            status=ComponentStatus.PROPOSED,
            proposed_at=timezone.now(),
            module_path='',
            file_path='',
        )
        
        # Return success message + close modal + refresh page
        response = HttpResponse()
        response['HX-Trigger'] = 'closeModal'
        return response
    
    # GET: Show form
    namespace = request.resolver_match.namespace
    url_prefix = f'{namespace}:feature-planning'
    
    context = {
        'available_types': ComponentType.choices,
        'url_create': f'{url_prefix}-create',
    }
    return render(request, 'bfagent/feature_planning/create_form.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def feature_update(request: HttpRequest, pk: int) -> HttpResponse:
    """Update feature (HTMX modal form)"""
    feature = get_object_or_404(ComponentRegistry, pk=pk)
    
    if request.method == "POST":
        # Update feature
        feature.name = request.POST.get('name', feature.name)
        feature.description = request.POST.get('description', feature.description)
        feature.priority = request.POST.get('priority', feature.priority)
        feature.status = request.POST.get('status', feature.status)
        
        # Update owner
        owner_id = request.POST.get('owner')
        if owner_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            feature.owner = User.objects.get(pk=owner_id)
        
        feature.save()
        
        # Return success + refresh
        response = HttpResponse(status=204)
        response['HX-Trigger'] = 'featureUpdated'
        return response
    
    # GET: Show form
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # Dynamic URLs
    namespace = request.resolver_match.namespace
    url_prefix = f'{namespace}:feature-planning'
    
    context = {
        'feature': feature,
        'available_statuses': ComponentStatus.choices,
        'available_users': User.objects.filter(is_active=True),
        'url_update': f'{url_prefix}-update',
    }
    return render(request, 'bfagent/feature_planning/edit_form.html', context)


@login_required
@require_http_methods(["POST", "DELETE"])
def feature_delete(request: HttpRequest, pk: int) -> HttpResponse:
    """Delete feature"""
    feature = get_object_or_404(ComponentRegistry, pk=pk)
    feature.delete()
    
    # Return empty content for hx-swap to remove the row
    response = HttpResponse("")
    response['HX-Trigger'] = 'featureDeleted'
    return response


@login_required
@require_POST
def feature_change_status(request: HttpRequest, pk: int) -> HttpResponse:
    """Quick status change"""
    feature = get_object_or_404(ComponentRegistry, pk=pk)
    new_status = request.POST.get('status')
    
    if new_status:
        old_status = feature.status
        feature.status = new_status
        
        # Update timestamps based on status
        if new_status == 'in_progress' and not feature.started_at:
            feature.started_at = timezone.now()
        elif new_status == 'active' and not feature.completed_at:
            feature.completed_at = timezone.now()
        
        feature.save()
    
    # Return updated row
    namespace = request.resolver_match.namespace
    url_prefix = f'{namespace}:feature-planning'
    
    context = {
        'features': [feature],
        'url_detail': f'{url_prefix}-detail',
        'url_update': f'{url_prefix}-update',
        'url_delete': f'{url_prefix}-delete',
    }
    return render(request, 'bfagent/feature_planning/feature_list.html', context)
