"""
Django Context Processors

Inject global context variables into all templates.

Feature: #147 - Domain-Aware Sidebar Navigation
"""
from .utils.sidebar_config import get_sidebar_for_domain, get_all_domains


def sidebar_navigation(request):
    """
    Inject domain-aware sidebar navigation into template context.

    Automatically detects the current domain from the URL namespace
    and provides the appropriate sidebar configuration.

    Args:
        request: Django HTTP request object

    Returns:
        Dictionary with:
        - sidebar_sections: List of sidebar sections for current domain
        - sidebar_domain_name: Human-readable domain name
        - sidebar_domain_icon: Bootstrap icon class
        - current_domain: Domain identifier
        - all_domains: List of all available domains

    Example in template:
        {% for section in sidebar_sections %}
            <h6>{{ section.title }}</h6>
            {% for item in section.items %}
                <a href="{% url item.url %}">
                    <i class="{{ item.icon }}"></i> {{ item.name }}
                </a>
            {% endfor %}
        {% endfor %}
    """
    # Determine current domain from URL namespace
    domain = 'bookwriting'  # Default

    if request.resolver_match and request.resolver_match.namespace:
        namespace = request.resolver_match.namespace

        # Extract domain from namespace
        # Examples:
        # - 'bfagent' -> check path for domain indicators
        # - 'medtrans:something' -> 'medtrans'
        # - 'control_center:dashboard' -> 'control_center'
        # - 'features:something' -> 'control_center'

        if ':' in namespace:
            # Get first part of namespace
            domain_part = namespace.split(':')[0]
            if domain_part in ['medtrans', 'genagent', 'control_center', 'features']:
                domain = 'control_center' if domain_part == 'features' else domain_part
        elif namespace in ['medtrans', 'genagent', 'control_center']:
            domain = namespace

        # Check URL path for domain indicators if still default
        if domain == 'bookwriting' and request.path:
            path = request.path.lower()
            if '/medtrans/' in path or path.startswith('/translation/'):
                domain = 'medtrans'
            elif '/genagent/' in path or '/workflow-builder/' in path:
                domain = 'genagent'
            elif '/control-center/' in path or '/features/' in path:
                domain = 'control_center'

    # Get sidebar configuration for domain
    sidebar_config = get_sidebar_for_domain(domain)

    return {
        'sidebar_sections': sidebar_config['sections'],
        'sidebar_domain_name': sidebar_config['domain_name'],
        'sidebar_domain_icon': sidebar_config['domain_icon'],
        'current_domain': domain,
        'all_domains': get_all_domains(),
    }


def theme_context(request):
    """
    Inject theme-related context variables.

    Returns:
        Dictionary with theme preferences
    """
    # Get theme from session or cookie, default to 'light'
    theme = request.session.get('theme', 'light')

    return {
        'current_theme': theme,
        'theme_is_dark': theme == 'dark',
    }
