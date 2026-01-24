"""
Context processors for Control Center
DUAL MODE: Supports both old (DomainSection) and new (NavigationSection) schemas
"""
from django.conf import settings
from .navigation_helpers import (
    get_sections_for_domain,
    get_section_items,
    get_item_url,
    normalize_section_data,
    normalize_item_data
)

try:
    from .models_navigation import NavigationSection, NavigationItem, UserNavigationPreference
except ImportError:
    NavigationSection = None
    NavigationItem = None
    UserNavigationPreference = None


def dynamic_navigation_context(request):
    """
    Add dynamic navigation data to all Control Center pages
    DUAL MODE: Works with both old and new navigation schemas
    """
    # Only add navigation context for Control Center pages
    if not request.path.startswith('/control-center/'):
        return {}
    
    # Skip for unauthenticated users
    if not request.user.is_authenticated:
        return {
            'dynamic_navigation': [],
            'navigation_preferences': {},
            'navigation_enabled': False,
        }
    
    try:
        # Detect domain from URL
        domain_slug = 'control-center'  # Default for /control-center/ URLs
        
        # Use dual-mode helper to get sections
        sections = get_sections_for_domain(domain_slug, request.user)
        
        navigation_data = []
        user_preferences = {}
        
        # Get user preferences for collapsed sections
        preferences = UserNavigationPreference.objects.filter(
            user=request.user
        ).values('section_id', 'is_collapsed')
        user_preferences = {
            pref['section_id']: pref['is_collapsed'] 
            for pref in preferences
        }
        
        for section in sections:
            # Normalize section data (works for both schemas)
            section_data = normalize_section_data(section)
            
            # Get user preferences for this section (NEW schema only)
            is_collapsed = False
            is_hidden = False
            if UserNavigationPreference and settings.NAVIGATION_FEATURES.get('USE_NEW_SCHEMA'):
                try:
                    user_pref = UserNavigationPreference.objects.get(
                        user=request.user, 
                        section=section
                    )
                    is_collapsed = user_pref.is_collapsed
                    is_hidden = user_pref.is_hidden
                except UserNavigationPreference.DoesNotExist:
                    is_collapsed = getattr(section, 'is_collapsed_default', False)
            
            if is_hidden:
                continue
            
            # Get active items using dual-mode helper
            items = get_section_items(section, request.user)
            
            section_items = []
            for item in items:
                # Normalize item data (works for both schemas)
                item_data = normalize_item_data(item)
                item_data['url'] = get_item_url(item, request)
                
                # Add extra fields for new schema
                if settings.NAVIGATION_FEATURES.get('USE_NEW_SCHEMA'):
                    item_data.update({
                        'code': getattr(item, 'code', ''),
                        'opens_in_new_tab': getattr(item, 'opens_in_new_tab', False),
                        'item_type': getattr(item, 'item_type', 'link'),
                        'children': [],  # TODO: Implement children support
                    })
                
                section_items.append(item_data)
            
            if section_items:  # Only add section if it has visible items
                section_dict = {
                    'id': section_data['id'],
                    'code': section_data['code'],
                    'name': section_data['name'],
                    'description': section_data['description'],
                    'icon': section_data['icon'],
                    'color': section_data.get('color', 'primary'),
                    'is_collapsible': getattr(section, 'is_collapsible', True),
                    'is_collapsed': is_collapsed,
                    'items': section_items,
                }
                navigation_data.append(section_dict)
        
        return {
            'dynamic_navigation': navigation_data,
            'navigation_preferences': user_preferences,
            'navigation_enabled': True,
        }
    except Exception as e:
        # Graceful fallback if navigation system is not available
        print(f"Navigation context processor error: {e}")  # Debug output
        return {
            'dynamic_navigation': [],
            'navigation_preferences': {},
            'navigation_enabled': False,
        }


def control_center_context(request):
    """
    General Control Center context data
    """
    if not request.path.startswith('/control-center/'):
        return {}
    
    return {
        'control_center_active': True,
        'page_section': 'control_center',
        'breadcrumb_base': 'Control Center',
    }
