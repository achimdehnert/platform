"""
Dynamic Navigation Template Tags
Automatically generate domain-aware, permission-based navigation
"""

import re
import codecs

from django import template
from django.db.models import Q
from django.template import Library
from django.urls import NoReverseMatch, reverse
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe

from ..models_navigation import NavigationItem, NavigationSection
from ..utils.domain_detection import get_current_domain_code

register = template.Library()


# ============================================================================
# Markdown/Unicode Filters for LLM Response Rendering
# ============================================================================

def _decode_unicode_escapes(text):
    """Decode JSON-style unicode escapes like \\u000A to actual characters."""
    if not text:
        return text
    try:
        return codecs.decode(text, 'unicode_escape')
    except (UnicodeDecodeError, ValueError):
        def replace_unicode(match):
            try:
                return chr(int(match.group(1), 16))
            except ValueError:
                return match.group(0)
        return re.sub(r'\\u([0-9a-fA-F]{4})', replace_unicode, text)


@register.filter(name='render_markdown')
def render_markdown(value):
    """
    Simple markdown-to-HTML conversion for feedback content.
    Handles: **bold**, `code`, ```code blocks```, newlines, and unicode escapes.
    """
    if not value:
        return ''
    
    # Decode unicode escapes first
    text = _decode_unicode_escapes(str(value))
    
    # Escape HTML
    text = escape(text)
    
    # Convert code blocks (```)
    def replace_code_block(match):
        code = match.group(1)
        return f'<pre class="bg-dark text-light p-2 rounded"><code>{code}</code></pre>'
    text = re.sub(r'```(?:\w+)?\n?(.*?)```', replace_code_block, text, flags=re.DOTALL)
    
    # Convert inline code (`code`)
    text = re.sub(r'`([^`]+)`', r'<code class="bg-light px-1 rounded">\1</code>', text)
    
    # Convert bold (**text**)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    
    # Convert --- to horizontal rule
    text = re.sub(r'\n---\n', '<hr class="my-2">', text)
    
    # Convert newlines to <br>
    text = text.replace('\n', '<br>')
    
    return mark_safe(text)


@register.filter
def get_item(dictionary, key):
    """Get item from dictionary by key in templates."""
    if dictionary is None:
        return []
    return dictionary.get(key, [])


@register.inclusion_tag("control_center/navigation/dynamic_sidebar.html", takes_context=True)
def dynamic_sidebar(context, domain=None, current_section=None):
    """
    Generate dynamic sidebar based on user permissions and domain

    Usage:
    {% load navigation_tags %}
    {% dynamic_sidebar domain="bookwriting" current_section="workflow_engine" %}
    """
    request = context["request"]
    user = request.user

    # Auto-detect domain if not provided
    if not domain:
        domain = get_current_domain_code(request)

    # Get navigation sections with domain filtering
    # Hub-aware: Only show sections where linked Hub is active (or no Hub linked)
    sections = NavigationSection.objects.filter(is_active=True).filter(
        Q(hub__isnull=True) | Q(hub__is_active=True)
    )

    # Apply domain filtering if domain is specified
    if domain:
        # Filter sections that either have no domain restrictions or include the specified domain
        sections = sections.filter(Q(domains__isnull=True) | Q(domains__code=domain)).distinct()

    sections = sections.order_by("order", "name")

    visible_sections = []
    for section in sections:
        if section.is_visible_for_user(user, domain):
            # Get visible navigation items for this section (simplified)
            items = []
            nav_items = section.navigation_items.filter(is_active=True, parent__isnull=True)

            # Apply domain filtering to navigation items
            if domain:
                nav_items = nav_items.filter(
                    Q(domains__isnull=True) | Q(domains__code=domain)
                ).distinct()

            nav_items = nav_items.order_by("order", "name")

            for item in nav_items:
                # Skip permission check for now to avoid M2M issues
                # Get children if this is a dropdown
                children = []
                if item.item_type == "dropdown":
                    for child in item.children.filter(is_active=True).order_by("order", "name"):
                        # Skip child permission check too
                        children.append(
                            {
                                "item": child,
                                "url": child.get_url(request),
                                "is_current": is_current_url(request, child.get_url(request)),
                            }
                        )

                items.append(
                    {
                        "item": item,
                        "url": item.get_url(request),
                        "children": children,
                        "is_current": is_current_url(request, item.get_url(request)),
                    }
                )

            if items:  # Only include sections that have visible items
                visible_sections.append(
                    {
                        "section": section,
                        "items": items,
                        "is_current": section.code == current_section,
                    }
                )

    return {
        "sections": visible_sections,
        "domain": domain,
        "current_section": current_section,
        "user": user,
        "request": request,
    }


@register.inclusion_tag("control_center/navigation/breadcrumb.html", takes_context=True)
def dynamic_breadcrumb(context, items=None):
    """
    Generate dynamic breadcrumb navigation

    Usage:
    {% dynamic_breadcrumb items=breadcrumb_items %}

    Where breadcrumb_items is a list of dicts:
    [
        {'name': 'Control Center', 'url': '/control-center/'},
        {'name': 'Workflow V2', 'url': '/control-center/workflow-v2/'},
        {'name': 'Wizard', 'url': None}  # Current page (no URL)
    ]
    """
    if not items:
        items = []

    return {"items": items, "request": context["request"]}


@register.simple_tag(takes_context=True)
def navigation_url(context, url_name, **kwargs):
    """
    Generate URL with error handling

    Usage:
    {% navigation_url 'control_center:workflow-v2-dashboard' domain='bookwriting' %}
    """
    try:
        return reverse(url_name, kwargs=kwargs)
    except NoReverseMatch:
        return "#"


@register.simple_tag
def navigation_badge(text, color="primary", small=False):
    """
    Generate navigation badge HTML

    Usage:
    {% navigation_badge 'V2' 'success' %}
    {% navigation_badge 'NEW' 'warning' small=True %}
    """
    size_class = "badge-sm" if small else ""
    return format_html('<span class="badge bg-{} ms-2 {}">{}</span>', color, size_class, text)


@register.filter
def has_navigation_permission(user, permission_codename):
    """
    Check if user has specific navigation permission

    Usage:
    {% if user|has_navigation_permission:'workflow.view_workflow' %}
    """
    return user.has_perm(permission_codename)


@register.filter
def in_navigation_group(user, group_name):
    """
    Check if user is in specific group

    Usage:
    {% if user|in_navigation_group:'workflow_managers' %}
    """
    return user.groups.filter(name=group_name).exists()


def is_current_url(request, url):
    """
    Helper function to check if URL matches current request path
    """
    if not url or url == "#":
        return False

    current_path = request.path

    # Exact match
    if current_path == url:
        return True

    # Partial match for parent URLs
    if current_path.startswith(url) and url != "/":
        return True

    return False


@register.inclusion_tag("control_center/navigation/domain_selector.html", takes_context=True)
def domain_selector(context, current_domain=None):
    """
    Generate domain selector dropdown

    Usage:
    {% domain_selector current_domain='bookwriting' %}
    """
    from ..models_workflow_domains import WorkflowDomain

    user = context["request"].user

    # Get domains user has access to
    domains = WorkflowDomain.objects.filter(is_active=True).order_by("name")

    # TODO: Add domain-specific permission filtering
    accessible_domains = []
    for domain in domains:
        # For now, all active domains are accessible
        # Later: Add permission checks based on user roles
        accessible_domains.append(domain)

    return {
        "domains": accessible_domains,
        "current_domain": current_domain,
        "request": context["request"],
    }


@register.simple_tag
def navigation_icon(icon_class, size="", color=""):
    """
    Generate navigation icon HTML

    Usage:
    {% navigation_icon 'bi-house' %}
    {% navigation_icon 'bi-gear' size='fs-5' color='text-primary' %}
    """
    classes = [icon_class]
    if size:
        classes.append(size)
    if color:
        classes.append(color)

    return format_html('<i class="{}"></i>', " ".join(classes))


@register.inclusion_tag("control_center/navigation/quick_actions.html", takes_context=True)
def navigation_quick_actions(context, domain=None, limit=5):
    """
    Generate quick action buttons based on domain and user permissions

    Usage:
    {% navigation_quick_actions domain='bookwriting' limit=3 %}
    """
    user = context["request"].user

    # Get quick action items (items marked with specific badge or type)
    quick_actions = (
        NavigationItem.objects.filter(
            is_active=True, badge_text__in=["QUICK", "NEW", "HOT"], section__is_active=True
        )
        .select_related("section")
        .order_by("order")[:limit]
    )

    visible_actions = []
    for action in quick_actions:
        if action.is_visible_for_user(user, domain):
            visible_actions.append({"item": action, "url": action.get_url(context["request"])})

    return {"actions": visible_actions, "domain": domain, "request": context["request"]}


@register.simple_tag(takes_context=True)
def get_navigation_for_domain(context, domain_code):
    """
    Get navigation sections and items for a specific domain
    
    Usage:
    {% get_navigation_for_domain 'bookwriting' as dynamic_sections %}
    {% for section in dynamic_sections %}
        ...
    {% endfor %}
    """
    request = context["request"]
    user = request.user
    
    # Get active sections
    # Hub-aware: Only show sections where linked Hub is active (or no Hub linked)
    sections = NavigationSection.objects.filter(is_active=True).filter(
        Q(hub__isnull=True) | Q(hub__is_active=True)
    )
    
    # For ManyToMany fields, we need to handle "no domains" differently
    # Include sections with no domain assignments (universal) OR matching domain
    if domain_code:
        # Get sections that either have no domains or have the specified domain
        all_sections = sections.order_by("order", "name")
        filtered_sections = []
        for section in all_sections:
            # Check if section has no domains (universal) or has the specified domain
            if not section.domains.exists() or section.domains.filter(code=domain_code).exists():
                filtered_sections.append(section.id)
        sections = NavigationSection.objects.filter(id__in=filtered_sections).order_by("order", "name")
    else:
        sections = sections.order_by("order", "name")
    
    result = []
    for section in sections:
        if section.is_visible_for_user(user, domain_code):
            # Get items for this section
            items = section.navigation_items.filter(is_active=True, parent__isnull=True)
            
            # Same ManyToMany fix for items
            if domain_code:
                all_items = items.order_by("order", "name")
                filtered_items = []
                for item in all_items:
                    if not item.domains.exists() or item.domains.filter(code=domain_code).exists():
                        filtered_items.append(item.id)
                items = section.navigation_items.filter(id__in=filtered_items, is_active=True, parent__isnull=True)
            
            items = items.order_by("order", "name")
            
            section_items = []
            for item in items:
                section_items.append({
                    'code': item.code,
                    'name': item.name,
                    'icon': item.icon,
                    'url': item.get_url(request),
                    'badge_text': item.badge_text,
                    'badge_color': item.badge_color,
                })
            
            if section_items:
                result.append({
                    'code': section.code,
                    'name': section.name,
                    'icon': section.icon,
                    'items': section_items,
                })
    
    return result
