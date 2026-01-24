"""
Location Views
"""

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required

from .models import BaseLocation, LocationLayer


@staff_member_required
def location_list(request):
    """List all locations (admin only)."""
    locations = BaseLocation.objects.all().order_by('country', 'name')
    return render(request, 'locations/location_list.html', {'locations': locations})


@staff_member_required
def location_detail(request, pk):
    """Location detail view."""
    location = get_object_or_404(BaseLocation, pk=pk)
    layers = location.layers.all()
    return render(request, 'locations/location_detail.html', {
        'location': location,
        'layers': layers,
    })


def location_search(request):
    """API: Search for locations."""
    query = request.GET.get('q', '')
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    locations = BaseLocation.objects.filter(
        name__icontains=query
    )[:10]
    
    results = [
        {
            'id': loc.id,
            'name': loc.name,
            'country': loc.country,
            'display': f"{loc.name}, {loc.country}",
        }
        for loc in locations
    ]
    
    return JsonResponse({'results': results})


def location_generate(request):
    """API: Generate location on-demand."""
    # TODO: Implement with LocationGenerator service
    return JsonResponse({
        'status': 'not_implemented',
        'message': 'Location generation will be implemented with Claude API',
    })
