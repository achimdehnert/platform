"""
Migration Registry Views - Django/HTMX Dashboard
"""
from django.shortcuts import render, get_object_or_404
from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Avg
from apps.bfagent.models_registry import MigrationRegistry


@require_http_methods(["GET"])
def migration_dashboard(request: HttpRequest) -> HttpResponse:
    """Main Migration Registry Dashboard"""
    
    # Get filters from request
    app_filter = request.GET.get('app', '')
    risk_filter = request.GET.get('risk', '')  # safe/careful/risky/critical
    status_filter = request.GET.get('status', '')  # all/applied/pending
    
    # Base query
    migrations = MigrationRegistry.objects.all().order_by('app_label', 'migration_number')
    
    # Apply filters
    if app_filter:
        migrations = migrations.filter(app_label=app_filter)
    
    if risk_filter:
        risk_ranges = {
            'safe': (0, 30),
            'careful': (31, 50),
            'risky': (51, 70),
            'critical': (71, 100),
        }
        if risk_filter in risk_ranges:
            min_score, max_score = risk_ranges[risk_filter]
            migrations = migrations.filter(
                complexity_score__gte=min_score,
                complexity_score__lte=max_score
            )
    
    if status_filter == 'applied':
        migrations = migrations.filter(is_applied=True)
    elif status_filter == 'pending':
        migrations = migrations.filter(is_applied=False)
    
    # Get available apps for filter dropdown
    available_apps = (
        MigrationRegistry.objects
        .values_list('app_label', flat=True)
        .distinct()
        .order_by('app_label')
    )
    
    # Calculate statistics
    total_count = MigrationRegistry.objects.count()
    applied_count = MigrationRegistry.objects.filter(is_applied=True).count()
    pending_count = total_count - applied_count
    
    risk_stats = {
        'safe': MigrationRegistry.objects.filter(complexity_score__lte=30).count(),
        'careful': MigrationRegistry.objects.filter(
            complexity_score__gte=31, complexity_score__lte=50
        ).count(),
        'risky': MigrationRegistry.objects.filter(
            complexity_score__gte=51, complexity_score__lte=70
        ).count(),
        'critical': MigrationRegistry.objects.filter(complexity_score__gte=71).count(),
    }
    
    # Dynamic URL names based on namespace
    namespace = request.resolver_match.namespace
    url_prefix = f'{namespace}:migration-registry'
    
    context = {
        'migrations': migrations[:100],  # Limit to 100 for performance
        'available_apps': available_apps,
        'app_filter': app_filter,
        'risk_filter': risk_filter,
        'status_filter': status_filter,
        'total_count': total_count,
        'applied_count': applied_count,
        'pending_count': pending_count,
        'risk_stats': risk_stats,
        # Dynamic URLs - no hardcoding in templates!
        'url_list': f'{url_prefix}-list',
        'url_detail': f'{url_prefix}-detail',
    }
    
    return render(request, 'bfagent/migration_registry/dashboard.html', context)


@require_http_methods(["GET"])
def migration_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Migration detail view (HTMX partial)"""
    migration = get_object_or_404(MigrationRegistry, pk=pk)
    
    context = {
        'migration': migration,
    }
    
    return render(request, 'bfagent/migration_registry/detail_modal.html', context)


@require_http_methods(["GET"])
def migration_list_partial(request: HttpRequest) -> HttpResponse:
    """
    Migration list partial (HTMX)
    Returns just the table rows
    """
    # Same filtering logic as dashboard
    app_filter = request.GET.get('app', '')
    risk_filter = request.GET.get('risk', '')
    status_filter = request.GET.get('status', '')
    
    migrations = MigrationRegistry.objects.all().order_by('app_label', 'migration_number')
    
    if app_filter:
        migrations = migrations.filter(app_label=app_filter)
    
    if risk_filter:
        risk_ranges = {
            'safe': (0, 30),
            'careful': (31, 50),
            'risky': (51, 70),
            'critical': (71, 100),
        }
        if risk_filter in risk_ranges:
            min_score, max_score = risk_ranges[risk_filter]
            migrations = migrations.filter(
                complexity_score__gte=min_score,
                complexity_score__lte=max_score
            )
    
    if status_filter == 'applied':
        migrations = migrations.filter(is_applied=True)
    elif status_filter == 'pending':
        migrations = migrations.filter(is_applied=False)
    
    # Dynamic URL names based on namespace
    namespace = request.resolver_match.namespace
    url_prefix = f'{namespace}:migration-registry'
    
    context = {
        'migrations': migrations[:100],
        # Dynamic URLs - no hardcoding in templates!
        'url_detail': f'{url_prefix}-detail',
    }
    
    return render(request, 'bfagent/migration_registry/migration_list.html', context)
