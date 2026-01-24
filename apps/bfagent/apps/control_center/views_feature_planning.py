"""
Control Center - Feature Planning Dashboard
Integration of ComponentRegistry with Global Feature Registry
"""

from django.shortcuts import render, get_object_or_404
from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count, Q
from apps.bfagent.models_registry import ComponentRegistry, ComponentStatus, ComponentType
from apps.bfagent.models_domains import DomainArt

# Import Global Feature Registry
from apps.core.features import get_global_feature_registry, get_domain_registry


@require_http_methods(["GET"])
def feature_planning_dashboard(request: HttpRequest) -> HttpResponse:
    """
    Unified Feature Planning Dashboard
    Combines ComponentRegistry (DB) with GlobalFeatureRegistry (Code)
    """
    
    # Get registries
    feature_registry = get_global_feature_registry()
    domain_registry = get_domain_registry()
    
    # Get filters
    status_filter = request.GET.get('status', '')
    type_filter = request.GET.get('type', '')
    priority_filter = request.GET.get('priority', '')
    domain_filter = request.GET.get('domain', '')
    view_mode = request.GET.get('view', 'all')  # 'all', 'db', 'code'
    
    # Get ComponentRegistry features (DB)
    db_features = ComponentRegistry.objects.all().order_by('-proposed_at')
    
    # Apply filters
    if status_filter:
        db_features = db_features.filter(status=status_filter)
    
    if type_filter:
        db_features = db_features.filter(component_type=type_filter)
    
    if priority_filter:
        db_features = db_features.filter(priority=priority_filter)
    
    if domain_filter:
        db_features = db_features.filter(domain=domain_filter)
    
    # Get Code Features (GlobalFeatureRegistry)
    code_features = []
    if view_mode in ['all', 'code']:
        all_features = feature_registry.features.values()
        
        for feature in all_features:
            # Apply domain filter
            if domain_filter and not feature.is_available_for_domain(domain_filter):
                continue
            
            # Apply status filter
            if status_filter and feature.status.value != status_filter:
                continue
            
            # Apply priority filter
            if priority_filter and feature.priority.value != priority_filter:
                continue
            
            code_features.append(feature)
    
    # Calculate statistics
    global_report = feature_registry.generate_global_report()
    
    # Generate domain reports from database (DomainArt model)
    domain_reports = {}
    for domain in DomainArt.objects.filter(is_active=True):
        # Count features per domain from ComponentRegistry
        # Match by slug, name, or partial match (e.g., "book" matches "book-creation")
        domain_features = ComponentRegistry.objects.filter(
            Q(domain=domain.slug) |
            Q(domain=domain.name) |
            Q(domain__icontains=domain.slug.split('-')[0])  # Match first part of slug
        )
        active_count = domain_features.filter(status=ComponentStatus.ACTIVE).count()
        
        domain_reports[domain.slug] = {
            'domain_name': domain.display_name,
            'total_features': domain_features.count(),
            'active_features': active_count,
            'cross_domain_features': 0,  # Not applicable for DB-based
            'base_handler_v2_count': 0,  # Legacy field
            'legacy_handler_count': 0,   # Legacy field
            'icon': domain.icon,
            'color': domain.color,
        }
    
    # DB Statistics
    db_total = ComponentRegistry.objects.count()
    db_status_stats = {}
    for status_code, status_label in ComponentStatus.choices:
        count = ComponentRegistry.objects.filter(status=status_code).count()
        db_status_stats[status_code] = {'label': status_label, 'count': count}
    
    # Get available filter options
    available_types = ComponentType.choices
    available_statuses = ComponentStatus.choices
    # Load domains from database (DomainArt model)
    available_domains = [
        (domain.slug, domain.display_name)
        for domain in DomainArt.objects.filter(is_active=True).order_by('display_name')
    ]
    
    context = {
        # Features
        'db_features': db_features[:100],
        'code_features': code_features,
        'view_mode': view_mode,
        
        # Filters
        'status_filter': status_filter,
        'type_filter': type_filter,
        'priority_filter': priority_filter,
        'domain_filter': domain_filter,
        'available_types': available_types,
        'available_statuses': available_statuses,
        'available_domains': available_domains,
        
        # Statistics
        'db_total': db_total,
        'db_status_stats': db_status_stats,
        'global_report': global_report,
        'domain_reports': domain_reports,
        
        # Registries
        'feature_registry': feature_registry,
        'domain_registry': domain_registry,
    }
    
    return render(request, 'control_center/feature_planning/dashboard.html', context)


@require_http_methods(["GET"])
def domain_features_view(request: HttpRequest, domain_id: str) -> HttpResponse:
    """Domain-specific feature view"""
    # Get domain from database (DomainArt model)
    domain = DomainArt.objects.filter(slug=domain_id, is_active=True).first()
    if not domain:
        return HttpResponse("Domain not found", status=404)
    
    # Get features for this domain from database
    # Match by slug, name, or partial match
    db_features = ComponentRegistry.objects.filter(
        Q(domain=domain_id) |
        Q(domain=domain.name) |
        Q(domain__icontains=domain_id.split('-')[0])
    ).order_by('-proposed_at')
    
    # Calculate domain statistics
    active_count = db_features.filter(status=ComponentStatus.ACTIVE).count()
    domain_report = {
        'domain_name': domain.display_name,
        'total_features': db_features.count(),
        'active_features': active_count,
        'icon': domain.icon,
        'color': domain.color,
    }
    
    # Get status breakdown
    status_breakdown = {}
    for status_code, status_label in ComponentStatus.choices:
        count = db_features.filter(status=status_code).count()
        if count > 0:
            status_breakdown[status_code] = {'label': status_label, 'count': count}
    
    context = {
        'domain': domain,
        'domain_report': domain_report,
        'db_features': db_features,
        'status_breakdown': status_breakdown,
    }
    
    return render(request, 'control_center/feature_planning/domain_detail.html', context)


@require_http_methods(["GET"])
def cross_domain_features_view(request: HttpRequest) -> HttpResponse:
    """View for cross-domain features"""
    feature_registry = get_global_feature_registry()
    
    cross_domain_features = feature_registry.get_cross_domain_features()
    shared_handlers = feature_registry.get_shared_handlers()
    
    context = {
        'cross_domain_features': cross_domain_features,
        'shared_handlers': shared_handlers,
    }
    
    return render(request, 'control_center/feature_planning/cross_domain.html', context)


@require_http_methods(["GET"])
def feature_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Feature detail view (HTMX partial)"""
    feature = get_object_or_404(ComponentRegistry, pk=pk)
    
    # Check if there's a corresponding code feature
    feature_registry = get_global_feature_registry()
    code_feature = None
    
    # Try to match by identifier or name
    for feat_id, feat in feature_registry.features.items():
        if feat.name.lower() == feature.name.lower():
            code_feature = feat
            break
    
    context = {
        'feature': feature,
        'code_feature': code_feature,
    }
    
    return render(request, 'control_center/feature_planning/detail_modal.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def feature_create(request: HttpRequest) -> HttpResponse:
    """Create new feature (HTMX modal form)"""
    if request.method == "POST":
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
            owner=request.user,
            module_path='',
            file_path='',
        )
        
        # Return success message + close modal + refresh page
        response = HttpResponse()
        response['HX-Trigger'] = 'closeModal,featureCreated'
        return response
    
    # GET: Show form
    # Load domains from database (DomainArt model)
    available_domains = [
        (domain.slug, domain.display_name)
        for domain in DomainArt.objects.filter(is_active=True).order_by('display_name')
    ]
    
    context = {
        'available_types': ComponentType.choices,
        'available_domains': available_domains,
    }
    return render(request, 'control_center/feature_planning/create_form.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def feature_update(request: HttpRequest, pk: int) -> HttpResponse:
    """Update feature (HTMX modal form)"""
    feature = get_object_or_404(ComponentRegistry, pk=pk)
    
    if request.method == "POST":
        feature.name = request.POST.get('name', feature.name)
        feature.description = request.POST.get('description', feature.description)
        feature.priority = request.POST.get('priority', feature.priority)
        feature.status = request.POST.get('status', feature.status)
        feature.domain = request.POST.get('domain', feature.domain)
        
        # Update owner
        owner_id = request.POST.get('owner')
        if owner_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                feature.owner = User.objects.get(pk=owner_id)
            except User.DoesNotExist:
                pass
        
        feature.save()
        
        response = HttpResponse(status=204)
        response['HX-Trigger'] = 'featureUpdated'
        return response
    
    # GET: Show form
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # Load domains from database (DomainArt model)
    available_domains = [
        (domain.slug, domain.display_name)
        for domain in DomainArt.objects.filter(is_active=True).order_by('display_name')
    ]
    
    context = {
        'feature': feature,
        'available_statuses': ComponentStatus.choices,
        'available_users': User.objects.filter(is_active=True),
        'available_domains': available_domains,
    }
    return render(request, 'control_center/feature_planning/edit_form.html', context)


@login_required
@require_http_methods(["POST", "DELETE"])
def feature_delete(request: HttpRequest, pk: int) -> HttpResponse:
    """Delete feature"""
    feature = get_object_or_404(ComponentRegistry, pk=pk)
    feature.delete()
    
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
        feature.status = new_status
        
        # Update timestamps based on status
        if new_status == 'in_progress' and not feature.started_at:
            feature.started_at = timezone.now()
        elif new_status == 'active' and not feature.completed_at:
            feature.completed_at = timezone.now()
        
        feature.save()
    
    context = {
        'features': [feature],
    }
    return render(request, 'control_center/feature_planning/feature_row.html', context)


@require_http_methods(["GET"])
def migration_progress_view(request: HttpRequest) -> HttpResponse:
    """View showing migration progress to BaseHandler v2.0"""
    feature_registry = get_global_feature_registry()
    
    global_report = feature_registry.generate_global_report()
    
    # Get all handlers and categorize them
    v2_handlers = [h for h in feature_registry.handlers.values() if h.is_base_handler_v2]
    legacy_handlers = [h for h in feature_registry.handlers.values() if not h.is_base_handler_v2]
    
    # Group by domain
    handlers_by_domain = {}
    for handler in feature_registry.handlers.values():
        for domain in handler.domains:
            if domain not in handlers_by_domain:
                handlers_by_domain[domain] = {'v2': [], 'legacy': []}
            
            if handler.is_base_handler_v2:
                handlers_by_domain[domain]['v2'].append(handler)
            else:
                handlers_by_domain[domain]['legacy'].append(handler)
    
    context = {
        'global_report': global_report,
        'v2_handlers': v2_handlers,
        'legacy_handlers': legacy_handlers,
        'handlers_by_domain': handlers_by_domain,
    }
    
    return render(request, 'control_center/feature_planning/migration_progress.html', context)
