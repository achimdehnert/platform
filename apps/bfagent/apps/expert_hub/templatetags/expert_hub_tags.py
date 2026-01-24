"""Expert Hub custom template tags and filters."""

from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Zugriff auf Dictionary-Wert per Key im Template.
    
    Verwendung: {{ my_dict|get_item:key_variable }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.filter
def percentage(value, total):
    """
    Berechnet Prozentsatz.
    
    Verwendung: {{ completed|percentage:total }}
    """
    try:
        return int((value / total) * 100) if total > 0 else 0
    except (ValueError, TypeError):
        return 0


@register.simple_tag
def phase_has_content(phase_content_map, phase_id):
    """
    Prüft ob eine Phase Inhalt hat.
    
    Verwendung: {% phase_has_content phase_content_map phase.id as has_content %}
    """
    if phase_content_map is None:
        return False
    return phase_content_map.get(phase_id, False)
