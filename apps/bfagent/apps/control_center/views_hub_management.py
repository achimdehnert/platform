"""
Hub Management Views for Control Center.

Provides UI for managing Hubs via the Hub Registry.
Requires USE_HUB_REGISTRY feature flag to be enabled.
"""

import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods

from apps.core.feature_flags import is_feature_enabled, FEATURES
from apps.core.hub_registry import hub_registry
from apps.core.event_bus import event_bus
from apps.core.events import Events

logger = logging.getLogger(__name__)


def is_admin(user):
    """Check if user is admin/staff."""
    return user.is_staff or user.is_superuser


@login_required
@user_passes_test(is_admin)
def hub_management_dashboard(request):
    """
    Dashboard for Hub Management.
    
    Shows all registered hubs with their status and controls.
    """
    context = {
        'title': 'Hub-Verwaltung',
        'feature_enabled': is_feature_enabled('USE_HUB_REGISTRY'),
        'feature_flags': FEATURES.copy(),
        'hubs': [],
        'hub_stats': {
            'total': 0,
            'active': 0,
            'inactive': 0,
            'production': 0,
            'beta': 0,
            'development': 0,
        }
    }
    
    if is_feature_enabled('USE_HUB_REGISTRY'):
        all_hubs = hub_registry.get_all_hubs()
        
        for hub_id, info in all_hubs.items():
            hub_data = {
                'id': hub_id,
                'name': info.manifest.name,
                'description': info.manifest.description,
                'version': info.manifest.version,
                'status': info.manifest.status.value,
                'is_active': info.is_active,
                'category': info.manifest.category.value,
                'dependencies': info.manifest.dependencies,
                'icon': info.manifest.icon,
            }
            context['hubs'].append(hub_data)
            
            # Update stats
            context['hub_stats']['total'] += 1
            if info.is_active:
                context['hub_stats']['active'] += 1
            else:
                context['hub_stats']['inactive'] += 1
            
            status = info.manifest.status.value
            if status == 'production':
                context['hub_stats']['production'] += 1
            elif status == 'beta':
                context['hub_stats']['beta'] += 1
            elif status == 'development':
                context['hub_stats']['development'] += 1
    
    return render(request, 'control_center/hub_management/dashboard.html', context)


@login_required
@user_passes_test(is_admin)
@require_http_methods(['POST'])
def hub_toggle_status(request, hub_id: str):
    """
    Toggle hub active status via HTMX.
    
    Args:
        hub_id: ID of the hub to toggle
    """
    if not is_feature_enabled('USE_HUB_REGISTRY'):
        return JsonResponse({
            'success': False,
            'error': 'Hub Registry feature is disabled'
        }, status=400)
    
    action = request.POST.get('action', 'toggle')
    
    try:
        if action == 'activate':
            success = hub_registry.activate_hub(hub_id)
            if success:
                event_bus.publish(Events.HUB_ACTIVATED, hub_id=hub_id, user=request.user.username)
                messages.success(request, f'Hub "{hub_id}" wurde aktiviert.')
        elif action == 'deactivate':
            success = hub_registry.deactivate_hub(hub_id)
            if success:
                event_bus.publish(Events.HUB_DEACTIVATED, hub_id=hub_id, user=request.user.username)
                messages.success(request, f'Hub "{hub_id}" wurde deaktiviert.')
        else:
            # Toggle
            hub_info = hub_registry.get_hub_info(hub_id)
            if hub_info and hub_info.is_active:
                success = hub_registry.deactivate_hub(hub_id)
                event_bus.publish(Events.HUB_DEACTIVATED, hub_id=hub_id, user=request.user.username)
            else:
                success = hub_registry.activate_hub(hub_id)
                event_bus.publish(Events.HUB_ACTIVATED, hub_id=hub_id, user=request.user.username)
        
        if request.headers.get('HX-Request'):
            # Return partial for HTMX
            hub_info = hub_registry.get_hub_info(hub_id)
            return render(request, 'control_center/hub_management/_hub_row.html', {
                'hub': {
                    'id': hub_id,
                    'name': hub_info.manifest.name if hub_info else hub_id,
                    'is_active': hub_info.is_active if hub_info else False,
                    'status': hub_info.manifest.status.value if hub_info else 'unknown',
                }
            })
        
        return redirect('control_center:hub_management')
        
    except Exception as e:
        logger.error(f"Error toggling hub {hub_id}: {e}")
        if request.headers.get('HX-Request'):
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
        messages.error(request, f'Fehler: {str(e)}')
        return redirect('control_center:hub_management')


@login_required
@user_passes_test(is_admin)
def hub_detail(request, hub_id: str):
    """
    Detail view for a specific hub.
    
    Args:
        hub_id: ID of the hub
    """
    if not is_feature_enabled('USE_HUB_REGISTRY'):
        messages.warning(request, 'Hub Registry Feature ist deaktiviert.')
        return redirect('control_center:dashboard')
    
    hub_info = hub_registry.get_hub_info(hub_id)
    
    if not hub_info:
        messages.error(request, f'Hub "{hub_id}" nicht gefunden.')
        return redirect('control_center:hub_management')
    
    context = {
        'title': f'Hub: {hub_info.manifest.name}',
        'hub': {
            'id': hub_id,
            'name': hub_info.manifest.name,
            'description': hub_info.manifest.description,
            'version': hub_info.manifest.version,
            'status': hub_info.manifest.status.value,
            'is_active': hub_info.is_active,
            'category': hub_info.manifest.category.value,
            'dependencies': hub_info.manifest.dependencies,
            'icon': hub_info.manifest.icon,
            'entry_point': hub_info.manifest.entry_point,
        },
        'recent_events': event_bus.get_recent_events(limit=10),
    }
    
    return render(request, 'control_center/hub_management/detail.html', context)


@login_required
@user_passes_test(is_admin)
def feature_flags_view(request):
    """
    View and manage feature flags.
    """
    from apps.core.feature_flags import enable_feature, disable_feature
    
    if request.method == 'POST':
        flag_name = request.POST.get('flag')
        action = request.POST.get('action')
        
        if flag_name and action:
            if action == 'enable':
                enable_feature(flag_name)
                messages.success(request, f'Feature "{flag_name}" aktiviert.')
            elif action == 'disable':
                disable_feature(flag_name)
                messages.success(request, f'Feature "{flag_name}" deaktiviert.')
        
        if request.headers.get('HX-Request'):
            return render(request, 'control_center/hub_management/_feature_flags.html', {
                'feature_flags': FEATURES.copy()
            })
        
        return redirect('control_center:feature_flags')
    
    context = {
        'title': 'Feature Flags',
        'feature_flags': FEATURES.copy(),
    }
    
    return render(request, 'control_center/hub_management/feature_flags.html', context)


@login_required
@user_passes_test(is_admin)
def event_log_view(request):
    """
    View recent events from the event bus.
    """
    limit = int(request.GET.get('limit', 50))
    
    context = {
        'title': 'Event Log',
        'events': event_bus.get_recent_events(limit=limit),
        'event_bus_enabled': is_feature_enabled('USE_EVENT_BUS'),
    }
    
    return render(request, 'control_center/hub_management/event_log.html', context)
