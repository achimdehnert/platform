"""
Domain Dashboard Views
Generic dashboards for ALL domains - active, inactive, experimental
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from apps.bfagent.models_domains import DomainArt
from apps.control_center.models_navigation import NavigationSection


@login_required
def home_dashboard(request):
    """
    Home Page with ALL domain tiles.
    Shows active, inactive, and experimental domains.
    """
    
    # Get all domains and group them
    all_domains = DomainArt.objects.all().order_by('name')
    
    # Categorize domains
    active_domains = []
    experimental_domains = []
    inactive_domains = []
    
    for domain in all_domains:
        # Get section count for this domain
        section_count = NavigationSection.objects.filter(
            domain_id=domain.id,
            is_active=True
        ).count()
        
        domain_data = {
            'domain': domain,
            'section_count': section_count,
            'dashboard_url': f'/{domain.slug}/',
        }
        
        if domain.is_active and not domain.is_experimental:
            active_domains.append(domain_data)
        elif domain.is_experimental:
            experimental_domains.append(domain_data)
        else:
            inactive_domains.append(domain_data)
    
    context = {
        'all_domains': all_domains,
        'active_domains': active_domains,
        'experimental_domains': experimental_domains,
        'inactive_domains': inactive_domains,
        'total_domains': all_domains.count(),
    }
    
    return render(request, 'hub/home_domain_tiles.html', context)


@login_required
def generic_domain_dashboard(request, domain_slug):
    """
    Generic dashboard for ANY domain.
    Loads sections and items from DB dynamically.
    Creates dashboard widgets from sections.
    """
    
    # Get domain
    domain = get_object_or_404(DomainArt, slug=domain_slug)
    
    # Get all sections for this domain with their items
    sections = NavigationSection.objects.filter(
        domain_id=domain,
        is_active=True
    ).order_by('order', 'name').prefetch_related('navigation_items')
    
    # Build dashboard widgets from sections
    dashboard_widgets = []
    for section in sections:
        # Get active items for this section
        items = section.navigation_items.filter(
            is_active=True,
            parent__isnull=True  # Top-level items only
        ).order_by('order', 'name')
        
        if items.exists():
            widget = {
                'section': section,
                'items': items,
                'widget_type': _determine_widget_type(section, items),
                'color': section.color or '#6c757d',
                'icon': section.icon or 'bi-folder',
            }
            dashboard_widgets.append(widget)
    
    # Get domain statistics
    stats = get_domain_stats(domain)
    
    context = {
        'domain': domain,
        'sections': sections,
        'dashboard_widgets': dashboard_widgets,
        'stats': stats,
    }
    
    return render(request, 'hub/generic_domain_dashboard_v2.html', context)


def _determine_widget_type(section, items):
    """
    Determine the best widget type based on section and items.
    Returns: 'card_grid', 'list', 'stats', or 'links'
    """
    item_count = items.count()
    
    # Small number of items = card grid
    if item_count <= 6:
        return 'card_grid'
    # Many items = list view
    elif item_count > 6:
        return 'list'
    else:
        return 'links'


def get_domain_stats(domain):
    """
    Get domain-specific statistics.
    Returns basic stats to avoid import errors.
    """
    stats = {
        'sections': NavigationSection.objects.filter(
            domain_id=domain,
            is_active=True
        ).count(),
    }
    
    # Keep it simple - just return section count for now
    return stats


def get_domain_recent_activity(domain):
    """
    Get recent activity for this domain.
    Returns empty list - simplified to avoid import errors.
    """
    return []


def get_domain_quick_actions(domain):
    """
    Get quick action buttons for this domain.
    Returns empty list - simplified.
    """
    return []
