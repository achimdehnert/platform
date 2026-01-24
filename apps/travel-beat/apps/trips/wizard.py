"""
Trip Wizard Views - Multi-Step Trip Creation

Session-based wizard for creating trips with:
1. Basic trip info
2. Stops/destinations
3. Story preferences
4. Review & generate
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse

from .models import Trip, Stop
from .forms import TripBasicsForm, StopFormSet, StoryPreferencesForm
from .services import ReadingTimeCalculator
from apps.stories.models import Story


WIZARD_SESSION_KEY = 'trip_wizard_data'


def get_wizard_data(request):
    """Get wizard data from session."""
    return request.session.get(WIZARD_SESSION_KEY, {})


def set_wizard_data(request, data):
    """Store wizard data in session."""
    request.session[WIZARD_SESSION_KEY] = data
    request.session.modified = True


def clear_wizard_data(request):
    """Clear wizard data from session."""
    if WIZARD_SESSION_KEY in request.session:
        del request.session[WIZARD_SESSION_KEY]


@login_required
def wizard_step1(request):
    """Step 1: Basic trip information."""
    wizard_data = get_wizard_data(request)
    
    if request.method == 'POST':
        form = TripBasicsForm(request.POST)
        if form.is_valid():
            # Store in session
            wizard_data['basics'] = {
                'name': form.cleaned_data['name'],
                'origin': form.cleaned_data['origin'],
                'start_date': form.cleaned_data['start_date'].isoformat(),
                'end_date': form.cleaned_data['end_date'].isoformat(),
                'trip_type': form.cleaned_data['trip_type'],
            }
            set_wizard_data(request, wizard_data)
            return redirect('trips:wizard_step2')
    else:
        # Pre-fill from session if exists
        initial = {}
        if 'basics' in wizard_data:
            initial = wizard_data['basics'].copy()
            # Convert date strings back
            if 'start_date' in initial:
                from datetime import date
                initial['start_date'] = date.fromisoformat(initial['start_date'])
            if 'end_date' in initial:
                initial['end_date'] = date.fromisoformat(initial['end_date'])
        form = TripBasicsForm(initial=initial)
    
    return render(request, 'trips/wizard/step1_basics.html', {
        'form': form,
        'step': 1,
    })


@login_required
def wizard_step2(request):
    """Step 2: Trip stops."""
    wizard_data = get_wizard_data(request)
    
    # Must have completed step 1
    if 'basics' not in wizard_data:
        messages.warning(request, 'Bitte zuerst die Reisedaten eingeben.')
        return redirect('trips:wizard_step1')
    
    # Create temporary trip for formset
    trip = Trip(user=request.user)
    
    if request.method == 'POST':
        formset = StopFormSet(request.POST, instance=trip, prefix='stops')
        if formset.is_valid():
            # Store stops in session
            stops_data = []
            for form in formset:
                if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                    stop_data = {
                        'city': form.cleaned_data['city'],
                        'country': form.cleaned_data['country'],
                        'arrival_date': form.cleaned_data['arrival_date'].isoformat() if form.cleaned_data.get('arrival_date') else None,
                        'departure_date': form.cleaned_data['departure_date'].isoformat() if form.cleaned_data.get('departure_date') else None,
                        'accommodation_type': form.cleaned_data.get('accommodation_type', 'hotel'),
                        'notes': form.cleaned_data.get('notes', ''),
                    }
                    stops_data.append(stop_data)
            
            wizard_data['stops'] = stops_data
            set_wizard_data(request, wizard_data)
            return redirect('trips:wizard_step3')
    else:
        # Pre-fill from session
        initial = []
        if 'stops' in wizard_data:
            from datetime import date
            for stop in wizard_data['stops']:
                stop_initial = stop.copy()
                if stop_initial.get('arrival_date'):
                    stop_initial['arrival_date'] = date.fromisoformat(stop_initial['arrival_date'])
                if stop_initial.get('departure_date'):
                    stop_initial['departure_date'] = date.fromisoformat(stop_initial['departure_date'])
                initial.append(stop_initial)
        
        formset = StopFormSet(instance=trip, prefix='stops', initial=initial if initial else None)
    
    return render(request, 'trips/wizard/step2_stops.html', {
        'formset': formset,
        'step': 2,
    })


@login_required
def wizard_step3(request):
    """Step 3: Story preferences."""
    wizard_data = get_wizard_data(request)
    
    # Must have completed steps 1 and 2
    if 'basics' not in wizard_data:
        return redirect('trips:wizard_step1')
    if 'stops' not in wizard_data:
        return redirect('trips:wizard_step2')
    
    if request.method == 'POST':
        form = StoryPreferencesForm(request.POST)
        if form.is_valid():
            # Store preferences
            triggers = form.cleaned_data.get('triggers_avoid', '')
            triggers_list = [t.strip() for t in triggers.split(',') if t.strip()] if triggers else []
            
            wizard_data['preferences'] = {
                'genre': form.cleaned_data['genre'],
                'spice_level': form.cleaned_data['spice_level'],
                'ending_type': form.cleaned_data['ending_type'],
                'protagonist_name': form.cleaned_data.get('protagonist_name', ''),
                'protagonist_gender': form.cleaned_data['protagonist_gender'],
                'triggers_avoid': triggers_list,
                'user_notes': form.cleaned_data.get('user_notes', ''),
            }
            set_wizard_data(request, wizard_data)
            return redirect('trips:wizard_step4')
    else:
        # Pre-fill from session
        initial = wizard_data.get('preferences', {})
        if initial.get('triggers_avoid'):
            initial['triggers_avoid'] = ', '.join(initial['triggers_avoid'])
        form = StoryPreferencesForm(initial=initial)
    
    return render(request, 'trips/wizard/step3_preferences.html', {
        'form': form,
        'step': 3,
    })


@login_required
def wizard_step4(request):
    """Step 4: Review and generate."""
    wizard_data = get_wizard_data(request)
    
    # Must have completed all steps
    if 'basics' not in wizard_data:
        return redirect('trips:wizard_step1')
    if 'stops' not in wizard_data:
        return redirect('trips:wizard_step2')
    if 'preferences' not in wizard_data:
        return redirect('trips:wizard_step3')
    
    # Create preview trip object (not saved yet)
    from datetime import date
    basics = wizard_data['basics']
    
    trip = Trip(
        user=request.user,
        name=basics['name'],
        origin=basics['origin'],
        start_date=date.fromisoformat(basics['start_date']),
        end_date=date.fromisoformat(basics['end_date']),
        trip_type=basics['trip_type'],
    )
    
    if request.method == 'POST':
        # Save everything and start generation
        trip.save()
        
        # Create stops
        for i, stop_data in enumerate(wizard_data['stops']):
            Stop.objects.create(
                trip=trip,
                order=i,
                city=stop_data['city'],
                country=stop_data['country'],
                arrival_date=date.fromisoformat(stop_data['arrival_date']) if stop_data.get('arrival_date') else None,
                departure_date=date.fromisoformat(stop_data['departure_date']) if stop_data.get('departure_date') else None,
                accommodation_type=stop_data.get('accommodation_type', 'hotel'),
                notes=stop_data.get('notes', ''),
            )
        
        # Create story
        prefs = wizard_data['preferences']
        story = Story.objects.create(
            user=request.user,
            trip=trip,
            title=f"Story: {trip.name}",
            genre=prefs['genre'],
            spice_level=prefs['spice_level'],
            ending_type=prefs['ending_type'],
            protagonist_name=prefs.get('protagonist_name', ''),
            protagonist_gender=prefs.get('protagonist_gender', 'female'),
            triggers_avoid=prefs.get('triggers_avoid', []),
            user_notes=prefs.get('user_notes', ''),
            status=Story.Status.PENDING,
        )
        
        # Clear wizard data
        clear_wizard_data(request)
        
        # Update trip status
        trip.status = Trip.Status.GENERATING
        trip.save()
        
        messages.success(request, 'Reise erstellt! Story-Generierung gestartet.')
        return redirect('stories:progress', pk=story.pk)
    
    # Calculate estimated reading time
    calculation = None
    try:
        # Create temporary stops for calculation
        trip._prefetched_objects_cache = {'stops': []}
        for i, stop_data in enumerate(wizard_data['stops']):
            stop = Stop(
                trip=trip,
                order=i,
                city=stop_data['city'],
                country=stop_data['country'],
                arrival_date=date.fromisoformat(stop_data['arrival_date']) if stop_data.get('arrival_date') else None,
                departure_date=date.fromisoformat(stop_data['departure_date']) if stop_data.get('departure_date') else None,
                accommodation_type=stop_data.get('accommodation_type', 'hotel'),
            )
            trip._prefetched_objects_cache['stops'].append(stop)
        
        calculator = ReadingTimeCalculator(trip, request.user)
        result = calculator.calculate()
        calculation = {
            'total_minutes': result.total_reading_minutes,
            'estimated_chapters': max(3, result.total_reading_minutes // 30),
            'estimated_words': result.total_reading_minutes * 250,
        }
    except Exception:
        pass
    
    return render(request, 'trips/wizard/step4_review.html', {
        'trip': trip,
        'preferences': wizard_data['preferences'],
        'calculation': calculation,
        'step': 4,
    })


@login_required
def wizard_cancel(request):
    """Cancel wizard and clear session data."""
    clear_wizard_data(request)
    messages.info(request, 'Reiseerstellung abgebrochen.')
    return redirect('trips:dashboard')
