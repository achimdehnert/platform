"""
API Views for BF Agent
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET"])
def domains_list(request):
    """
    API endpoint to get list of available domains from DomainArt model.
    Used by bug reporter and requirement creator modals.
    """
    from apps.bfagent.models_domains import DomainArt
    
    domains = DomainArt.objects.filter(is_active=True).order_by('display_name')
    
    return JsonResponse({
        'success': True,
        'domains': [
            {
                'slug': d.slug,
                'name': d.name,
                'display_name': d.display_name,
                'icon': d.icon,
                'color': d.color,
            }
            for d in domains
        ]
    })
