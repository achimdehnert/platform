"""
Unified Navigation Context Processor
100% DB-DRIVEN - NO HARDCODED NAVIGATION!

All navigation data comes from:
- domain_arts (Domains)
- navigation_sections (Sections)
- navigation_items (Items)
- core_hubs (Hub) - Controls section visibility via is_active
"""

from django.conf import settings
from django.db.models import Q

from apps.bfagent.models_domains import DomainArt
from apps.control_center.models_navigation import NavigationItem, NavigationSection


def unified_navigation(request):
    """
    Load complete navigation hierarchy from database.
    NO HARDCODED ITEMS - 100% DB-DRIVEN!
    
    Hub Integration:
    - Sections linked to a Hub are only shown if Hub.is_active=True
    - Sections without a Hub link are always shown (if is_active=True)

    Returns:
        dict: Complete navigation tree with domains, sections, and items
    """

    # Feature flag check
    use_unified_nav = getattr(settings, "USE_UNIFIED_NAVIGATION", False)

    if not use_unified_nav:
        return {"unified_navigation_enabled": False}

    # Detect current domain from URL
    current_domain = get_current_domain(request)
    current_domain_slug = current_domain.slug if current_domain else None

    # ============================================================================
    # 1. LOAD ALL DOMAINS FROM DB
    # ============================================================================
    all_domains = DomainArt.objects.all().order_by("name")

    navigation_tree = []

    for domain in all_domains:
        # ========================================================================
        # 2. LOAD SECTIONS FOR THIS DOMAIN FROM DB
        # Hub-aware: Only show sections where linked Hub is active (or no Hub linked)
        # ========================================================================
        sections = NavigationSection.objects.filter(
            domain_id=domain, is_active=True
        ).filter(
            # Show if: no Hub linked OR linked Hub is active
            Q(hub__isnull=True) | Q(hub__is_active=True)
        ).order_by("order", "name")

        section_list = []

        for section in sections:
            # ====================================================================
            # 3. LOAD ITEMS FOR THIS SECTION FROM DB
            # ====================================================================
            items = NavigationItem.objects.filter(
                section=section,  # Pass section object, not section.id
                is_active=True,
                parent__isnull=True,  # Top-level items only (use parent, not parent_id)
            ).order_by("order", "name")

            # Normalize item data
            item_list = []
            for item in items:
                item_list.append(
                    {
                        "id": item.id,
                        "name": item.name,
                        "url": item.get_url(request),
                        "icon": item.icon,
                        "badge_text": item.badge_text,
                        "badge_color": item.badge_color,
                        "opens_in_new_tab": item.opens_in_new_tab,
                    }
                )

            # Build section dict
            section_list.append(
                {
                    "id": section.id,
                    "code": section.code,
                    "name": section.name,
                    "icon": section.icon,
                    "color": section.color,
                    "is_collapsible": section.is_collapsible,
                    "is_collapsed_default": section.is_collapsed_default,
                    "url": section.get_url(),
                    "items": item_list,
                }
            )

        # ========================================================================
        # 4. BUILD DOMAIN DICT (Flat structure for template)
        # ========================================================================
        # Only add domain if it has sections
        if section_list:
            navigation_tree.append(
                {
                    "id": domain.id,
                    "slug": domain.slug,
                    "name": domain.display_name or domain.name,
                    "icon": domain.icon or "bi-folder",
                    "color": domain.color or "primary",
                    "dashboard_url": f"/{domain.slug}/",
                    "is_active": domain.is_active,
                    "is_experimental": domain.is_experimental,
                    "sections": section_list,
                    "section_count": len(section_list),
                }
            )

    return {
        "unified_navigation_enabled": True,
        "navigation_tree": navigation_tree,
        "current_domain_slug": current_domain_slug,
        "active_domains": [d for d in navigation_tree if d["is_active"]],
        "inactive_domains": [d for d in navigation_tree if not d["is_active"]],
    }


def get_current_domain(request):
    """
    Detect current domain from URL path.

    Args:
        request: Django request object

    Returns:
        DomainArt instance or None
    """
    path = request.path

    # Map URL patterns to domain slugs
    domain_map = {
        "/control-center/": "control-center",
        "/writing-hub/": "writing-hub",
        "/illustrations/": "illustration-hub",
        "/expert-hub/": "expert-hub",
        "/support-hub/": "support-hub",
        "/dlm-hub/": "dlm-hub",
    }

    for url_prefix, domain_slug in domain_map.items():
        if path.startswith(url_prefix):
            try:
                return DomainArt.objects.get(slug=domain_slug)
            except DomainArt.DoesNotExist:
                pass

    return None


def active_domain_context(request):
    """
    Provide current active domain in context.

    Returns:
        dict: Current domain information
    """
    current_domain = get_current_domain(request)

    return {
        "current_domain": current_domain,
        "current_domain_slug": current_domain.slug if current_domain else None,
    }


def available_domains_context(request):
    """
    Provide list of all available domains for dropdowns (Bug/Feature Reporter).
    
    Returns:
        dict: List of active domains with slug, display_name, and icon
    """
    domains = DomainArt.objects.filter(is_active=True).order_by('display_name')
    
    return {
        "available_domains": domains,
    }
