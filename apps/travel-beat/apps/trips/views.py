"""
Trip Views - CRUD and Dashboard
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse

from .models import Trip, Stop, Transport


def landing_page(request):
    """Public landing page."""
    if request.user.is_authenticated:
        return redirect('trips:dashboard')
    return render(request, 'trips/landing.html')


@login_required
def dashboard(request):
    """User dashboard with trips and stories."""
    trips = Trip.objects.filter(user=request.user).select_related()[:10]
    
    # Stats
    stats = {
        'total_trips': Trip.objects.filter(user=request.user).count(),
        'stories_generated': request.user.stories_generated,
        'stories_remaining': request.user.stories_remaining,
    }
    
    context = {
        'trips': trips,
        'stats': stats,
    }
    return render(request, 'trips/dashboard.html', context)


@login_required
def trip_list(request):
    """List all trips."""
    trips = Trip.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'trips/trip_list.html', {'trips': trips})


@login_required
def trip_create(request):
    """Create new trip - Multi-step form."""
    if request.method == 'POST':
        # Handle form submission
        trip = Trip.objects.create(
            user=request.user,
            name=request.POST.get('name', 'Meine Reise'),
            trip_type=request.POST.get('trip_type', 'city'),
            origin=request.POST.get('origin', ''),
            start_date=request.POST.get('start_date'),
            end_date=request.POST.get('end_date'),
        )
        messages.success(request, f'Reise "{trip.name}" erstellt!')
        return redirect('trips:trip_edit', pk=trip.pk)
    
    return render(request, 'trips/trip_create.html')


@login_required
def trip_detail(request, pk):
    """Trip detail view."""
    trip = get_object_or_404(Trip, pk=pk, user=request.user)
    stops = trip.stops.all()
    transports = trip.transports.all()
    
    context = {
        'trip': trip,
        'stops': stops,
        'transports': transports,
    }
    return render(request, 'trips/trip_detail.html', context)


@login_required
def trip_edit(request, pk):
    """Edit trip - Add stops, transports."""
    trip = get_object_or_404(Trip, pk=pk, user=request.user)
    
    if request.method == 'POST':
        # Update trip
        trip.name = request.POST.get('name', trip.name)
        trip.trip_type = request.POST.get('trip_type', trip.trip_type)
        trip.origin = request.POST.get('origin', trip.origin)
        trip.save()
        messages.success(request, 'Reise aktualisiert!')
        return redirect('trips:trip_detail', pk=trip.pk)
    
    context = {
        'trip': trip,
        'stops': trip.stops.all(),
    }
    return render(request, 'trips/trip_edit.html', context)


@login_required
def trip_delete(request, pk):
    """Delete trip."""
    trip = get_object_or_404(Trip, pk=pk, user=request.user)
    
    if request.method == 'POST':
        name = trip.name
        trip.delete()
        messages.success(request, f'Reise "{name}" gelöscht.')
        return redirect('trips:trip_list')
    
    return render(request, 'trips/trip_confirm_delete.html', {'trip': trip})


@login_required
def trip_calculate(request, pk):
    """Calculate reading time for trip."""
    from apps.trips.services import ReadingTimeCalculator
    
    trip = get_object_or_404(Trip, pk=pk, user=request.user)
    
    calculator = ReadingTimeCalculator()
    result = calculator.calculate(trip, reading_speed=request.user.reading_speed)
    
    # Update trip
    trip.total_reading_minutes = result.total_minutes
    trip.recommended_chapters = result.recommended_chapters
    trip.recommended_words = result.total_words
    trip.status = Trip.Status.READY
    trip.save()
    
    messages.success(
        request,
        f'Berechnet: {result.total_minutes} Min Lesezeit, '
        f'{result.recommended_chapters} Kapitel empfohlen.'
    )
    
    if request.headers.get('HX-Request'):
        return render(request, 'trips/partials/trip_stats.html', {'trip': trip})
    
    return redirect('trips:trip_detail', pk=trip.pk)


@login_required
def trip_generate_story(request, pk):
    """Trigger story generation for trip."""
    trip = get_object_or_404(Trip, pk=pk, user=request.user)
    
    # Check if user can generate
    if not request.user.can_generate_story:
        messages.error(request, 'Du hast dein Story-Limit erreicht. Upgrade auf Premium!')
        return redirect('trips:trip_detail', pk=trip.pk)
    
    # TODO: Trigger Celery task
    trip.status = Trip.Status.GENERATING
    trip.save()
    
    messages.info(request, 'Story-Generierung gestartet! Du wirst benachrichtigt, wenn sie fertig ist.')
    return redirect('stories:story_progress', trip_id=trip.pk)


# ============================================================================
# HTMX Partials
# ============================================================================

@login_required
def stop_add(request, pk):
    """Add stop to trip (HTMX)."""
    trip = get_object_or_404(Trip, pk=pk, user=request.user)
    
    if request.method == 'POST':
        stop = Stop.objects.create(
            trip=trip,
            city=request.POST.get('city', ''),
            country=request.POST.get('country', ''),
            arrival_date=request.POST.get('arrival_date'),
            departure_date=request.POST.get('departure_date'),
            accommodation_type=request.POST.get('accommodation_type', 'hotel'),
            order=trip.stops.count(),
        )
        
        if request.headers.get('HX-Request'):
            return render(request, 'trips/partials/stop_card.html', {'stop': stop})
        
        return redirect('trips:trip_edit', pk=trip.pk)
    
    return render(request, 'trips/partials/stop_form.html', {'trip': trip})


@login_required
def stop_edit(request, pk):
    """Edit stop (HTMX)."""
    stop = get_object_or_404(Stop, pk=pk, trip__user=request.user)
    
    if request.method == 'POST':
        stop.city = request.POST.get('city', stop.city)
        stop.country = request.POST.get('country', stop.country)
        stop.arrival_date = request.POST.get('arrival_date', stop.arrival_date)
        stop.departure_date = request.POST.get('departure_date', stop.departure_date)
        stop.accommodation_type = request.POST.get('accommodation_type', stop.accommodation_type)
        stop.save()
        
        if request.headers.get('HX-Request'):
            return render(request, 'trips/partials/stop_card.html', {'stop': stop})
    
    return render(request, 'trips/partials/stop_form.html', {'stop': stop})


@login_required
def stop_delete(request, pk):
    """Delete stop (HTMX)."""
    stop = get_object_or_404(Stop, pk=pk, trip__user=request.user)
    
    if request.method == 'DELETE' or request.method == 'POST':
        stop.delete()
        return HttpResponse('')  # Empty response for HTMX
    
    return render(request, 'trips/partials/stop_confirm_delete.html', {'stop': stop})
