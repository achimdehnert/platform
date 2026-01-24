"""
Navigation System Helpers - Dual Mode Support
Supports both old (DomainSection) and new (NavigationSection) systems in parallel
"""
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist


def get_sections_for_domain(domain_slug, user=None):
    """
    Get navigation sections for domain - supports dual mode
    
    Args:
        domain_slug: Domain slug (e.g., 'control-center', 'writing-hub')
        user: User object for permission filtering (optional)
    
    Returns:
        List of sections (either DomainSection or NavigationSection objects)
    """
    use_new = settings.NAVIGATION_FEATURES.get('USE_NEW_SCHEMA', False)
    debug = settings.NAVIGATION_FEATURES.get('DEBUG_NAVIGATION', False)
    
    if debug:
        print(f"🔍 get_sections_for_domain(domain={domain_slug}, use_new={use_new})")
    
    try:
        if use_new:
            # NEW: Use NavigationSection with domain_id FK
            from apps.core.models import DomainArt
            from .models_navigation import NavigationSection
            
            try:
                domain = DomainArt.objects.get(slug=domain_slug)
                sections = NavigationSection.objects.filter(
                    domain_id=domain.id,
                    is_active=True
                ).prefetch_related('navigation_items').order_by('order', 'name')
                
                if debug:
                    print(f"  ✅ NEW schema: Found {sections.count()} sections for domain_id={domain.id}")
            except DomainArt.DoesNotExist:
                if debug:
                    print(f"  ⚠️  Domain '{domain_slug}' not found")
                sections = []
        else:
            # OLD: Use DomainSection (legacy)
            from apps.core.models import DomainArt, DomainSection
            
            try:
                domain = DomainArt.objects.get(slug=domain_slug)
                sections = DomainSection.objects.filter(
                    domain_art=domain,
                    is_active=True
                ).prefetch_related('items').order_by('display_order', 'display_name')
                
                if debug:
                    print(f"  ✅ OLD schema: Found {sections.count()} sections for domain_art={domain.id}")
            except (DomainArt.DoesNotExist, ObjectDoesNotExist):
                if debug:
                    print(f"  ⚠️  Domain '{domain_slug}' not found in old schema")
                sections = []
        
        # Permission filtering (works for both)
        if user and sections:
            filtered = []
            for section in sections:
                if hasattr(section, 'is_visible_for_user'):
                    if section.is_visible_for_user(user):
                        filtered.append(section)
                else:
                    # No permission check, include all
                    filtered.append(section)
            sections = filtered
            
            if debug:
                print(f"  🔒 After permission filter: {len(sections)} sections")
        
        return list(sections)
        
    except Exception as e:
        if debug:
            print(f"  ❌ Error: {e}")
        return []


def get_section_items(section, user=None):
    """
    Get items for section - supports dual mode
    
    Args:
        section: Section object (DomainSection or NavigationSection)
        user: User object for permission filtering (optional)
    
    Returns:
        List of items (DomainSectionItem or NavigationItem objects)
    """
    use_new = settings.NAVIGATION_FEATURES.get('USE_NEW_SCHEMA', False)
    debug = settings.NAVIGATION_FEATURES.get('DEBUG_NAVIGATION', False)
    
    try:
        if use_new:
            # NEW: NavigationItem
            items = section.navigation_items.filter(is_active=True).order_by('order', 'name')
            if debug:
                print(f"  📋 NEW schema: {items.count()} items for section '{section.name}'")
        else:
            # OLD: DomainSectionItem
            items = section.items.filter(is_active=True).order_by('display_order', 'display_name')
            if debug:
                print(f"  📋 OLD schema: {items.count()} items for section '{section.display_name}'")
        
        # Permission filtering
        if user and items:
            filtered = []
            for item in items:
                if hasattr(item, 'is_visible_for_user'):
                    if item.is_visible_for_user(user):
                        filtered.append(item)
                else:
                    filtered.append(item)
            items = filtered
            
            if debug:
                print(f"    🔒 After permission filter: {len(items)} items")
        
        return list(items)
        
    except Exception as e:
        if debug:
            print(f"  ❌ Error getting items: {e}")
        return []


def get_item_url(item, request=None):
    """
    Get URL for navigation item - supports both schemas
    
    Args:
        item: Item object (DomainSectionItem or NavigationItem)
        request: HTTP request for URL building (optional)
    
    Returns:
        str: URL for the item
    """
    use_new = settings.NAVIGATION_FEATURES.get('USE_NEW_SCHEMA', False)
    
    try:
        if use_new:
            # NEW: NavigationItem has url_name
            if item.url_name:
                from django.urls import reverse
                try:
                    return reverse(item.url_name, kwargs=item.url_params or {})
                except:
                    return item.external_url or '#'
            return item.external_url or '#'
        else:
            # OLD: DomainSectionItem has url field
            return getattr(item, 'url', '#') or '#'
    except:
        return '#'


def normalize_section_data(section):
    """
    Normalize section data to consistent format
    Works with both DomainSection and NavigationSection
    
    Args:
        section: Section object
    
    Returns:
        dict: Normalized section data
    """
    use_new = settings.NAVIGATION_FEATURES.get('USE_NEW_SCHEMA', False)
    
    if use_new:
        # NEW schema
        return {
            'id': section.id,
            'code': getattr(section, 'code', section.slug),
            'slug': section.slug,
            'name': section.name,
            'description': section.description,
            'icon': section.icon,
            'color': section.color,
            'order': section.order,
            'is_active': section.is_active,
        }
    else:
        # OLD schema
        return {
            'id': section.id,
            'code': section.slug,
            'slug': section.slug,
            'name': section.display_name,
            'description': section.description,
            'icon': section.icon,
            'color': section.color,
            'order': section.display_order,
            'is_active': section.is_active,
        }


def normalize_item_data(item):
    """
    Normalize item data to consistent format
    Works with both DomainSectionItem and NavigationItem
    
    Args:
        item: Item object
    
    Returns:
        dict: Normalized item data
    """
    use_new = settings.NAVIGATION_FEATURES.get('USE_NEW_SCHEMA', False)
    
    if use_new:
        # NEW schema
        return {
            'id': item.id,
            'name': item.name,
            'description': item.description,
            'icon': item.icon,
            'badge_text': item.badge_text,
            'badge_color': item.badge_color,
            'url': get_item_url(item),
        }
    else:
        # OLD schema
        return {
            'id': item.id,
            'name': item.display_name,
            'description': item.description,
            'icon': item.icon,
            'badge_text': getattr(item, 'badge_text', ''),
            'badge_color': getattr(item, 'badge_color', 'primary'),
            'url': item.url or '#',
        }
