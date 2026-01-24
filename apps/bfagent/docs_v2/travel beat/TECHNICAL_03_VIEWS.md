# Travel Story - Technische Dokumentation

## Teil 3: Views & HTMX

---

## Inhaltsverzeichnis

1. [HTMX Grundlagen](#1-htmx-grundlagen)
2. [URL-Struktur](#2-url-struktur)
3. [trips Views](#3-trips-views)
4. [stories Views](#4-stories-views)
5. [worlds Views](#5-worlds-views)
6. [HTMX Patterns](#6-htmx-patterns)

---

## 1. HTMX Grundlagen

### Warum HTMX?

- **Kein JavaScript-Framework** nötig
- **Server-rendered HTML** bleibt Kern
- **Progressive Enhancement** out-of-the-box
- **Django-freundlich** - Templates bleiben zentral

### Kern-Attribute

```html
<!-- GET Request -->
<button hx-get="/api/data/" hx-target="#result">
    Laden
</button>

<!-- POST Request -->
<form hx-post="/trips/create/" hx-target="#trip-list" hx-swap="beforeend">
    ...
</form>

<!-- Trigger -->
<input hx-get="/search/" 
       hx-trigger="keyup changed delay:300ms"
       hx-target="#results">

<!-- Swap Strategien -->
hx-swap="innerHTML"     <!-- Standard -->
hx-swap="outerHTML"     <!-- Element ersetzen -->
hx-swap="beforeend"     <!-- Ans Ende anfügen -->
hx-swap="afterbegin"    <!-- Am Anfang einfügen -->
hx-swap="delete"        <!-- Element löschen -->
```

### Django Integration

```python
# views.py
from django.http import HttpResponse
from django.template.loader import render_to_string

def htmx_view(request):
    # Prüfen ob HTMX Request
    is_htmx = request.headers.get('HX-Request') == 'true'
    
    if is_htmx:
        # Nur Partial zurückgeben
        html = render_to_string('partials/item.html', context)
        return HttpResponse(html)
    else:
        # Volle Seite
        return render(request, 'full_page.html', context)
```

---

## 2. URL-Struktur

### trips App

```python
# trips/urls.py
from django.urls import path
from . import views

app_name = 'trips'

urlpatterns = [
    # CRUD
    path('', views.TripListView.as_view(), name='list'),
    path('create/', views.TripCreateView.as_view(), name='create'),
    path('<int:pk>/', views.TripDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.TripUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.TripDeleteView.as_view(), name='delete'),
    
    # Stops (HTMX Partials)
    path('<int:trip_id>/stops/add/', views.StopAddView.as_view(), name='stop_add'),
    path('stops/<int:pk>/edit/', views.StopEditView.as_view(), name='stop_edit'),
    path('stops/<int:pk>/delete/', views.StopDeleteView.as_view(), name='stop_delete'),
    
    # Transport (HTMX Partials)
    path('<int:trip_id>/transport/add/', views.TransportAddView.as_view(), name='transport_add'),
    
    # Calculate (HTMX)
    path('<int:pk>/calculate/', views.TripCalculateView.as_view(), name='calculate'),
]
```

### stories App

```python
# stories/urls.py
app_name = 'stories'

urlpatterns = [
    # List & Detail
    path('', views.StoryListView.as_view(), name='list'),
    path('<int:pk>/', views.StoryDetailView.as_view(), name='detail'),
    
    # Generate (Celery Task)
    path('generate/<int:trip_id>/', views.StoryGenerateView.as_view(), name='generate'),
    path('generate/<int:pk>/status/', views.StoryStatusView.as_view(), name='status'),
    
    # Read
    path('<int:story_id>/chapter/<int:chapter>/', views.ChapterReadView.as_view(), name='read'),
    path('<int:story_id>/chapter/<int:chapter>/progress/', views.ChapterProgressView.as_view(), name='progress'),
    
    # Export
    path('<int:pk>/export/md/', views.ExportMarkdownView.as_view(), name='export_md'),
    path('<int:pk>/export/epub/', views.ExportEpubView.as_view(), name='export_epub'),
]
```

### worlds App

```python
# worlds/urls.py
app_name = 'worlds'

urlpatterns = [
    # Dashboard
    path('', views.WorldDashboardView.as_view(), name='dashboard'),
    
    # Characters (HTMX)
    path('characters/', views.CharacterListView.as_view(), name='character_list'),
    path('characters/add/', views.CharacterAddView.as_view(), name='character_add'),
    path('characters/<int:pk>/edit/', views.CharacterEditView.as_view(), name='character_edit'),
    path('characters/<int:pk>/delete/', views.CharacterDeleteView.as_view(), name='character_delete'),
    
    # Personal Places (HTMX)
    path('places/', views.PlaceListView.as_view(), name='place_list'),
    path('places/add/', views.PlaceAddView.as_view(), name='place_add'),
    path('places/<int:pk>/toggle/', views.PlaceToggleView.as_view(), name='place_toggle'),
    
    # Settings
    path('settings/', views.WorldSettingsView.as_view(), name='settings'),
]
```

---

## 3. trips Views

### TripCreateView

```python
# trips/views.py
from django.views.generic import CreateView, UpdateView, DeleteView, DetailView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.template.loader import render_to_string
from .models import Trip, Stop, Transport
from .forms import TripForm, StopFormSet


class TripCreateView(LoginRequiredMixin, CreateView):
    """Neue Reise erstellen"""
    
    model = Trip
    form_class = TripForm
    template_name = 'trips/trip_form.html'
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        
        # HTMX: Redirect via Header
        if self.request.headers.get('HX-Request'):
            response = HttpResponse()
            response['HX-Redirect'] = self.object.get_absolute_url()
        
        return response


class StopAddView(LoginRequiredMixin, CreateView):
    """Stop hinzufügen (HTMX Partial)"""
    
    model = Stop
    fields = ['city', 'country', 'arrival_date', 'departure_date', 'accommodation_type']
    template_name = 'trips/partials/stop_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['trip'] = Trip.objects.get(pk=self.kwargs['trip_id'])
        return context
    
    def form_valid(self, form):
        trip = Trip.objects.get(pk=self.kwargs['trip_id'])
        form.instance.trip = trip
        form.instance.order = trip.stops.count()
        self.object = form.save()
        
        # HTMX: Return nur das neue Stop-Element
        html = render_to_string(
            'trips/partials/stop_item.html',
            {'stop': self.object},
            request=self.request
        )
        
        response = HttpResponse(html)
        response['HX-Trigger'] = 'stopAdded'  # Für eventuelle Updates
        return response
    
    def form_invalid(self, form):
        # Bei Fehler: Form mit Errors zurückgeben
        html = render_to_string(
            'trips/partials/stop_form.html',
            {'form': form, 'trip': Trip.objects.get(pk=self.kwargs['trip_id'])},
            request=self.request
        )
        return HttpResponse(html, status=422)


class StopDeleteView(LoginRequiredMixin, DeleteView):
    """Stop löschen (HTMX)"""
    
    model = Stop
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        
        # HTMX: Leere Response, Element wird client-seitig entfernt
        return HttpResponse(status=200)
```

### TripCalculateView

```python
from .services import ReadingTimeCalculator


class TripCalculateView(LoginRequiredMixin, View):
    """Lesezeit berechnen (HTMX)"""
    
    def post(self, request, pk):
        trip = get_object_or_404(Trip, pk=pk, user=request.user)
        
        # Calculator Service aufrufen
        calculator = ReadingTimeCalculator()
        result = calculator.calculate(trip)
        
        # Trip aktualisieren
        trip.total_reading_minutes = result.total_minutes
        trip.recommended_chapters = result.recommended_chapters
        trip.recommended_words = result.recommended_words
        trip.save()
        
        # Partial mit Ergebnis zurückgeben
        html = render_to_string(
            'trips/partials/calculation_result.html',
            {'trip': trip, 'result': result},
            request=request
        )
        
        return HttpResponse(html)
```

---

## 4. stories Views

### StoryGenerateView

```python
# stories/views.py
from django.views import View
from django.http import JsonResponse
from .tasks import generate_story_task


class StoryGenerateView(LoginRequiredMixin, View):
    """Story-Generierung starten"""
    
    template_name = 'stories/generate_form.html'
    
    def get(self, request, trip_id):
        """Formular für Story-Einstellungen"""
        trip = get_object_or_404(Trip, pk=trip_id, user=request.user)
        form = StorySettingsForm()
        
        return render(request, self.template_name, {
            'trip': trip,
            'form': form,
        })
    
    def post(self, request, trip_id):
        """Generierung starten"""
        trip = get_object_or_404(Trip, pk=trip_id, user=request.user)
        form = StorySettingsForm(request.POST)
        
        if not form.is_valid():
            # HTMX: Form mit Errors
            if request.headers.get('HX-Request'):
                html = render_to_string(
                    'stories/partials/generate_form.html',
                    {'form': form, 'trip': trip},
                    request=request
                )
                return HttpResponse(html, status=422)
            return render(request, self.template_name, {'form': form, 'trip': trip})
        
        # Story erstellen
        story = Story.objects.create(
            user=request.user,
            trip=trip,
            title=form.cleaned_data['title'],
            genre=form.cleaned_data['genre'],
            context=form.cleaned_data.get('context', {}),
            status=Story.Status.GENERATING,
        )
        
        # Celery Task starten
        generate_story_task.delay(story.id)
        
        # HTMX: Redirect zu Status-Seite
        if request.headers.get('HX-Request'):
            response = HttpResponse()
            response['HX-Redirect'] = reverse('stories:status', args=[story.id])
            return response
        
        return redirect('stories:status', pk=story.id)


class StoryStatusView(LoginRequiredMixin, View):
    """Generierungs-Status (HTMX Polling)"""
    
    def get(self, request, pk):
        story = get_object_or_404(Story, pk=pk, user=request.user)
        
        # HTMX Partial für Polling
        if request.headers.get('HX-Request'):
            html = render_to_string(
                'stories/partials/generation_status.html',
                {'story': story},
                request=request
            )
            response = HttpResponse(html)
            
            # Polling stoppen wenn fertig
            if story.status in [Story.Status.COMPLETE, Story.Status.ERROR]:
                response['HX-Trigger'] = 'generationComplete'
            
            return response
        
        return render(request, 'stories/generation_status.html', {'story': story})
```

### ChapterReadView

```python
class ChapterReadView(LoginRequiredMixin, View):
    """Kapitel lesen"""
    
    def get(self, request, story_id, chapter):
        story = get_object_or_404(Story, pk=story_id, user=request.user)
        chapter_obj = get_object_or_404(Chapter, story=story, number=chapter)
        
        # Lesefortschritt laden/erstellen
        progress, _ = ReadingProgress.objects.get_or_create(
            user=request.user,
            story=story,
            chapter=chapter_obj,
        )
        
        context = {
            'story': story,
            'chapter': chapter_obj,
            'progress': progress,
            'prev_chapter': story.chapters.filter(number__lt=chapter).last(),
            'next_chapter': story.chapters.filter(number__gt=chapter).first(),
        }
        
        # HTMX: Nur Content
        if request.headers.get('HX-Request'):
            return render(request, 'stories/partials/chapter_content.html', context)
        
        return render(request, 'stories/chapter_read.html', context)


class ChapterProgressView(LoginRequiredMixin, View):
    """Lesefortschritt speichern (HTMX)"""
    
    def post(self, request, story_id, chapter):
        story = get_object_or_404(Story, pk=story_id, user=request.user)
        chapter_obj = get_object_or_404(Chapter, story=story, number=chapter)
        
        progress, _ = ReadingProgress.objects.get_or_create(
            user=request.user,
            story=story,
            chapter=chapter_obj,
        )
        
        # Fortschritt aus Request
        percent = float(request.POST.get('progress', 0))
        progress.progress_percent = min(100, max(0, percent))
        
        if percent >= 100:
            progress.is_completed = True
            progress.completed_at = timezone.now()
        
        progress.save()
        
        return HttpResponse(status=204)  # No Content
```

---

## 5. worlds Views

### WorldDashboardView

```python
# worlds/views.py
from django.views.generic import TemplateView
from .models import UserWorld


class WorldDashboardView(LoginRequiredMixin, TemplateView):
    """User World Dashboard"""
    
    template_name = 'worlds/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # World laden oder erstellen
        world, created = UserWorld.objects.get_or_create(
            user=self.request.user
        )
        
        context['world'] = world
        context['characters'] = world.characters.all()[:5]
        context['places'] = world.personal_places.all()[:5]
        context['memories'] = world.location_memories.all()[:5]
        
        return context


class CharacterAddView(LoginRequiredMixin, CreateView):
    """Charakter hinzufügen (HTMX)"""
    
    model = Character
    form_class = CharacterForm
    template_name = 'worlds/partials/character_form.html'
    
    def form_valid(self, form):
        world = self.request.user.world
        form.instance.world = world
        self.object = form.save()
        
        # HTMX: Return Character Card
        html = render_to_string(
            'worlds/partials/character_card.html',
            {'character': self.object},
            request=self.request
        )
        
        response = HttpResponse(html)
        response['HX-Trigger'] = 'characterAdded'
        return response


class PlaceToggleView(LoginRequiredMixin, View):
    """Ort ein/ausschließen (HTMX Toggle)"""
    
    def post(self, request, pk):
        place = get_object_or_404(
            PersonalPlace, 
            pk=pk, 
            world__user=request.user
        )
        
        # Toggle
        place.use_in_story = not place.use_in_story
        place.save()
        
        # HTMX: Updated Element zurückgeben
        html = render_to_string(
            'worlds/partials/place_item.html',
            {'place': place},
            request=request
        )
        
        return HttpResponse(html)
```

---

## 6. HTMX Patterns

### Pattern 1: Inline Edit

```html
<!-- worlds/partials/character_card.html -->
<div id="character-{{ character.id }}" class="card">
    <h3>{{ character.name }}</h3>
    <p>{{ character.role }}</p>
    
    <!-- Edit Button -->
    <button hx-get="{% url 'worlds:character_edit' character.id %}"
            hx-target="#character-{{ character.id }}"
            hx-swap="outerHTML">
        Bearbeiten
    </button>
</div>

<!-- Wird zu Edit-Form wenn geklickt -->
```

```html
<!-- worlds/partials/character_edit_form.html -->
<form id="character-{{ character.id }}"
      hx-post="{% url 'worlds:character_edit' character.id %}"
      hx-target="this"
      hx-swap="outerHTML"
      class="card editing">
    
    {{ form.as_p }}
    
    <button type="submit">Speichern</button>
    <button type="button"
            hx-get="{% url 'worlds:character_detail' character.id %}"
            hx-target="#character-{{ character.id }}"
            hx-swap="outerHTML">
        Abbrechen
    </button>
</form>
```

### Pattern 2: Infinite Scroll

```html
<!-- stories/story_list.html -->
<div id="story-list">
    {% for story in stories %}
        {% include 'stories/partials/story_card.html' %}
    {% endfor %}
</div>

{% if has_more %}
<div hx-get="{% url 'stories:list' %}?page={{ next_page }}"
     hx-trigger="revealed"
     hx-target="#story-list"
     hx-swap="beforeend"
     hx-select="#story-list > *">
    <!-- Lädt mehr wenn sichtbar -->
    <span class="loading">Lade mehr...</span>
</div>
{% endif %}
```

### Pattern 3: Polling für Status

```html
<!-- stories/partials/generation_status.html -->
<div id="generation-status"
     {% if story.status == 'generating' %}
     hx-get="{% url 'stories:status' story.id %}"
     hx-trigger="every 2s"
     hx-swap="outerHTML"
     {% endif %}>
    
    {% if story.status == 'generating' %}
        <div class="progress">
            <div class="progress-bar" style="width: {{ story.progress }}%"></div>
        </div>
        <p>Kapitel {{ story.chapters_generated }} von {{ story.total_chapters }}...</p>
    
    {% elif story.status == 'complete' %}
        <div class="success">
            <h3>✓ Story fertig!</h3>
            <a href="{% url 'stories:detail' story.id %}">Lesen</a>
        </div>
    
    {% elif story.status == 'error' %}
        <div class="error">
            <h3>✗ Fehler bei der Generierung</h3>
            <p>{{ story.error_message }}</p>
        </div>
    {% endif %}
</div>
```

### Pattern 4: Form mit dynamischen Feldern

```html
<!-- trips/trip_form.html -->
<form hx-post="{% url 'trips:create' %}" hx-target="body">
    {% csrf_token %}
    
    {{ form.name }}
    {{ form.start_date }}
    {{ form.end_date }}
    {{ form.trip_type }}
    
    <!-- Stops Container -->
    <div id="stops-container">
        {% for stop_form in stop_formset %}
            {% include 'trips/partials/stop_form.html' with form=stop_form %}
        {% endfor %}
    </div>
    
    <!-- Add Stop Button -->
    <button type="button"
            hx-get="{% url 'trips:stop_form_empty' %}"
            hx-target="#stops-container"
            hx-swap="beforeend">
        + Stopp hinzufügen
    </button>
    
    <button type="submit">Reise speichern</button>
</form>
```

### Pattern 5: Bestätigungs-Dialog

```html
<!-- Lösch-Button mit Bestätigung -->
<button hx-delete="{% url 'trips:stop_delete' stop.id %}"
        hx-confirm="Stopp '{{ stop.city }}' wirklich löschen?"
        hx-target="#stop-{{ stop.id }}"
        hx-swap="outerHTML swap:1s"
        class="btn-danger">
    Löschen
</button>
```

### Pattern 6: Out-of-Band Updates

```python
# views.py - Mehrere Elemente gleichzeitig updaten

def stop_add(request, trip_id):
    # ... Stop erstellen ...
    
    # Mehrere Partials zurückgeben
    stop_html = render_to_string(
        'trips/partials/stop_item.html',
        {'stop': stop}
    )
    
    # Out-of-band: Trip-Summary aktualisieren
    summary_html = render_to_string(
        'trips/partials/trip_summary.html',
        {'trip': trip}
    )
    
    # Kombinierte Response
    html = f"""
    {stop_html}
    <div id="trip-summary" hx-swap-oob="true">
        {summary_html}
    </div>
    """
    
    return HttpResponse(html)
```

```html
<!-- Template -->
<div id="trip-summary">
    {{ trip.stops.count }} Stopps • {{ trip.total_reading_minutes }} Min Lesezeit
</div>

<div id="stops-list">
    {% for stop in trip.stops.all %}
        {% include 'trips/partials/stop_item.html' %}
    {% endfor %}
</div>

<!-- Wenn Stop hinzugefügt wird, werden BEIDE aktualisiert -->
```

---

## Nächster Teil

→ **Teil 4: Services & Celery** (Business Logic, Background Tasks)
