# Travel Story - Technische Dokumentation

## Teil 2: Datenmodelle

---

## Inhaltsverzeichnis

1. [Übersicht](#1-übersicht)
2. [trips App](#2-trips-app)
3. [locations App](#3-locations-app)
4. [worlds App](#4-worlds-app)
5. [stories App](#5-stories-app)
6. [Beziehungen](#6-beziehungen)

---

## 1. Übersicht

### ER-Diagramm (vereinfacht)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│   ┌──────────┐         ┌──────────┐         ┌──────────┐                   │
│   │   User   │────────▶│   Trip   │────────▶│   Stop   │                   │
│   │          │    1:n  │          │    1:n  │          │                   │
│   └──────────┘         └──────────┘         └──────────┘                   │
│        │                    │                    │                          │
│        │                    │                    │                          │
│        │ 1:1                │ 1:1                │ n:1                      │
│        ▼                    ▼                    ▼                          │
│   ┌──────────┐         ┌──────────┐         ┌────────────┐                 │
│   │UserWorld │         │  Story   │         │BaseLocation│                 │
│   │          │         │          │         │  (shared)  │                 │
│   └──────────┘         └──────────┘         └────────────┘                 │
│        │                    │                    │                          │
│        │ 1:n                │ 1:n                │ 1:n                      │
│        ▼                    ▼                    ▼                          │
│   ┌──────────┐         ┌──────────┐         ┌────────────┐                 │
│   │Character │         │ Chapter  │         │LocationLayer│                │
│   │          │         │          │         │  (shared)  │                 │
│   └──────────┘         └──────────┘         └────────────┘                 │
│        │                                                                    │
│        │ via UserWorld                                                      │
│        ▼                                                                    │
│   ┌──────────────┐     ┌──────────────┐                                    │
│   │PersonalPlace │     │LocationMemory│                                    │
│   └──────────────┘     └──────────────┘                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. trips App

### Trip Model

```python
# trips/models.py

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Trip(models.Model):
    """Eine Reise des Users"""
    
    class TripType(models.TextChoices):
        CITY = 'city', 'Städtereise'
        BEACH = 'beach', 'Strandurlaub'
        WELLNESS = 'wellness', 'Wellness'
        BACKPACKING = 'backpacking', 'Backpacking'
        BUSINESS = 'business', 'Geschäftsreise'
        FAMILY = 'family', 'Familienurlaub'
    
    # Beziehungen
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='trips'
    )
    
    # Basis-Daten
    name = models.CharField(max_length=200)
    trip_type = models.CharField(
        max_length=20,
        choices=TripType.choices,
        default=TripType.CITY
    )
    
    # Daten
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Berechnet
    total_reading_minutes = models.PositiveIntegerField(default=0)
    recommended_chapters = models.PositiveIntegerField(default=0)
    recommended_words = models.PositiveIntegerField(default=0)
    
    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date})"
    
    @property
    def duration_days(self) -> int:
        return (self.end_date - self.start_date).days + 1
    
    @property
    def stops_count(self) -> int:
        return self.stops.count()
```

### Stop Model

```python
class Stop(models.Model):
    """Ein Stopp auf der Reise"""
    
    class AccommodationType(models.TextChoices):
        HOTEL = 'hotel', 'Hotel'
        AIRBNB = 'airbnb', 'Airbnb/Ferienwohnung'
        HOSTEL = 'hostel', 'Hostel'
        CAMPING = 'camping', 'Camping'
        FRIENDS = 'friends', 'Bei Freunden'
        OTHER = 'other', 'Sonstiges'
    
    # Beziehungen
    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name='stops'
    )
    
    # Location (Referenz zu shared BaseLocation)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    base_location = models.ForeignKey(
        'locations.BaseLocation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Daten
    arrival_date = models.DateField()
    departure_date = models.DateField()
    
    # Unterkunft
    accommodation_type = models.CharField(
        max_length=20,
        choices=AccommodationType.choices,
        default=AccommodationType.HOTEL
    )
    
    # Reihenfolge
    order = models.PositiveIntegerField(default=0)
    
    # Berechnet
    reading_minutes = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'arrival_date']
    
    def __str__(self):
        return f"{self.city}, {self.country}"
    
    @property
    def nights(self) -> int:
        return (self.departure_date - self.arrival_date).days
```

### Transport Model

```python
class Transport(models.Model):
    """Transport zwischen zwei Stopps"""
    
    class TransportType(models.TextChoices):
        FLIGHT = 'flight', 'Flugzeug'
        TRAIN = 'train', 'Zug'
        BUS = 'bus', 'Bus'
        CAR_DRIVER = 'car_driver', 'Auto (Fahrer)'
        CAR_PASSENGER = 'car_passenger', 'Auto (Beifahrer)'
        FERRY = 'ferry', 'Fähre'
        OTHER = 'other', 'Sonstiges'
    
    # Beziehungen
    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name='transports'
    )
    from_stop = models.ForeignKey(
        Stop,
        on_delete=models.CASCADE,
        related_name='departures'
    )
    to_stop = models.ForeignKey(
        Stop,
        on_delete=models.CASCADE,
        related_name='arrivals'
    )
    
    # Details
    transport_type = models.CharField(
        max_length=20,
        choices=TransportType.choices
    )
    duration_minutes = models.PositiveIntegerField()
    
    # Berechnet
    reading_minutes = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"{self.from_stop.city} → {self.to_stop.city} ({self.transport_type})"
```

### Datenbank-Schema (SQL)

```sql
-- trips_trip
CREATE TABLE trips_trip (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    trip_type VARCHAR(20) NOT NULL DEFAULT 'city',
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    total_reading_minutes INTEGER DEFAULT 0,
    recommended_chapters INTEGER DEFAULT 0,
    recommended_words INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_trips_user ON trips_trip(user_id);
CREATE INDEX idx_trips_dates ON trips_trip(start_date, end_date);

-- trips_stop
CREATE TABLE trips_stop (
    id SERIAL PRIMARY KEY,
    trip_id INTEGER NOT NULL REFERENCES trips_trip(id) ON DELETE CASCADE,
    base_location_id VARCHAR(100) REFERENCES locations_baselocation(id) ON DELETE SET NULL,
    city VARCHAR(100) NOT NULL,
    country VARCHAR(100) NOT NULL,
    arrival_date DATE NOT NULL,
    departure_date DATE NOT NULL,
    accommodation_type VARCHAR(20) NOT NULL DEFAULT 'hotel',
    "order" INTEGER DEFAULT 0,
    reading_minutes INTEGER DEFAULT 0
);

CREATE INDEX idx_stops_trip ON trips_stop(trip_id);

-- trips_transport
CREATE TABLE trips_transport (
    id SERIAL PRIMARY KEY,
    trip_id INTEGER NOT NULL REFERENCES trips_trip(id) ON DELETE CASCADE,
    from_stop_id INTEGER NOT NULL REFERENCES trips_stop(id) ON DELETE CASCADE,
    to_stop_id INTEGER NOT NULL REFERENCES trips_stop(id) ON DELETE CASCADE,
    transport_type VARCHAR(20) NOT NULL,
    duration_minutes INTEGER NOT NULL,
    reading_minutes INTEGER DEFAULT 0
);
```

---

## 3. locations App

### BaseLocation Model

```python
# locations/models.py

from django.db import models
from django.contrib.postgres.fields import ArrayField


class BaseLocation(models.Model):
    """
    Shared Base Location - Schicht 1
    Einmal generiert, für alle User nutzbar.
    """
    
    # Primary Key = normalized city name
    id = models.CharField(max_length=100, primary_key=True)
    
    # Basis-Daten
    name = models.CharField(max_length=200)
    country = models.CharField(max_length=100)
    region = models.CharField(max_length=100, blank=True)
    
    # Geo
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    timezone = models.CharField(max_length=50, default='UTC')
    
    # Details (JSONB)
    languages = ArrayField(
        models.CharField(max_length=50),
        default=list
    )
    currency = models.CharField(max_length=10, default='EUR')
    climate = models.TextField(blank=True)
    best_seasons = ArrayField(
        models.CharField(max_length=20),
        default=list
    )
    
    # Viertel (JSONB Array)
    districts = models.JSONField(default=list)
    # Format: [{"name": "...", "local_name": "...", "vibe": "...", "description": "..."}]
    
    population = models.PositiveIntegerField(null=True, blank=True)
    known_for = ArrayField(
        models.CharField(max_length=100),
        default=list
    )
    
    # Meta
    source = models.CharField(max_length=50, default='web_research')
    quality_score = models.FloatField(default=0.0)
    generated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Base Location'
        verbose_name_plural = 'Base Locations'
    
    def __str__(self):
        return f"{self.name}, {self.country}"
```

### LocationLayer Model

```python
class LocationLayer(models.Model):
    """
    Genre-spezifischer Layer - Schicht 2
    Shared, aber pro Genre unterschiedlich.
    """
    
    class LayerType(models.TextChoices):
        ROMANCE = 'romance', 'Romance'
        THRILLER = 'thriller', 'Thriller'
        MYSTERY = 'mystery', 'Mystery'
        FOODIE = 'foodie', 'Foodie'
        ART = 'art', 'Kunst & Kultur'
        HISTORY = 'history', 'Geschichte'
        ADVENTURE = 'adventure', 'Abenteuer'
        NIGHTLIFE = 'nightlife', 'Nachtleben'
    
    # Beziehungen
    location = models.ForeignKey(
        BaseLocation,
        on_delete=models.CASCADE,
        related_name='layers'
    )
    layer_type = models.CharField(
        max_length=20,
        choices=LayerType.choices
    )
    
    # Atmosphären nach Tageszeit (JSONB)
    atmospheres = models.JSONField(default=dict)
    # Format: {"morning": "...", "afternoon": "...", "evening": "...", "night": "..."}
    
    # Orte (JSONB Array)
    places = models.JSONField(default=list)
    # Format: [{"name": "...", "type": "...", "district": "...", 
    #           "relevance_score": 5, "description": "...", 
    #           "atmosphere": "...", "story_potential": "..."}]
    
    # Sensorische Details (JSONB)
    sensory = models.JSONField(default=dict)
    # Format: {"smells": [...], "sounds": [...], "textures": [...], 
    #          "tastes": [...], "visuals": [...]}
    
    # Story-Elemente
    story_hooks = ArrayField(
        models.TextField(),
        default=list
    )
    scene_settings = ArrayField(
        models.TextField(),
        default=list
    )
    potential_conflicts = ArrayField(
        models.TextField(),
        default=list
    )
    
    # Meta
    quality_score = models.FloatField(default=0.0)
    generated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Location Layer'
        verbose_name_plural = 'Location Layers'
        unique_together = ['location', 'layer_type']
    
    def __str__(self):
        return f"{self.location.name} - {self.layer_type}"
```

### ResearchCache Model

```python
class ResearchCache(models.Model):
    """Cache für LLM-generierte Daten"""
    
    query_key = models.CharField(max_length=255, unique=True)
    result = models.JSONField()
    
    hit_count = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        verbose_name = 'Research Cache'
        indexes = [
            models.Index(fields=['query_key']),
            models.Index(fields=['expires_at']),
        ]
    
    @property
    def is_expired(self) -> bool:
        from django.utils import timezone
        return timezone.now() > self.expires_at
```

---

## 4. worlds App

### UserWorld Model

```python
# worlds/models.py

from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField

User = get_user_model()


class UserWorld(models.Model):
    """
    User-spezifische Welt - Schicht 3
    Personalisierung und Story-Kontinuität.
    """
    
    # 1:1 mit User
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='world'
    )
    
    # Story-Universum
    universe_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Name für Ihr Story-Universum"
    )
    
    # Interessen (für Layer-Auswahl)
    interests_primary = ArrayField(
        models.CharField(max_length=20),
        default=list,
        help_text="Primäre Interessen (Layer-Types)"
    )
    interests_secondary = ArrayField(
        models.CharField(max_length=20),
        default=list
    )
    interests_avoid = ArrayField(
        models.CharField(max_length=20),
        default=list,
        help_text="Themen, die vermieden werden sollen"
    )
    
    # Trigger-Vermeidung
    triggers_avoid = ArrayField(
        models.TextField(),
        default=list,
        help_text="Themen/Szenarien, die vermieden werden sollen"
    )
    
    # Präferenzen
    preferred_spice_level = models.CharField(
        max_length=20,
        default='mild',
        choices=[
            ('none', 'Keine expliziten Szenen'),
            ('mild', 'Mild'),
            ('moderate', 'Moderat'),
            ('spicy', 'Explizit'),
        ]
    )
    preferred_ending = models.CharField(
        max_length=20,
        default='happy',
        choices=[
            ('happy', 'Happy End'),
            ('sad', 'Tragisch'),
            ('open', 'Offen'),
            ('surprise', 'Überraschung'),
        ]
    )
    
    # Statistiken
    stories_generated = models.PositiveIntegerField(default=0)
    total_words_read = models.BigIntegerField(default=0)
    favorite_locations = ArrayField(
        models.CharField(max_length=100),
        default=list
    )
    
    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"World: {self.user.username}"
    
    def get_excluded_places(self, location_id: str) -> list:
        """Hole ausgeschlossene Orte für eine Location"""
        return list(
            self.personal_places
            .filter(location_id=location_id, use_in_story=False)
            .values_list('name', flat=True)
        )
```

### Character Model

```python
class Character(models.Model):
    """Story-Charakter im User-Universum"""
    
    class Role(models.TextChoices):
        PROTAGONIST = 'protagonist', 'Protagonist'
        LOVE_INTEREST = 'love_interest', 'Love Interest'
        ANTAGONIST = 'antagonist', 'Antagonist'
        SIDEKICK = 'sidekick', 'Sidekick'
        MENTOR = 'mentor', 'Mentor'
        OTHER = 'other', 'Andere'
    
    # Beziehungen
    world = models.ForeignKey(
        UserWorld,
        on_delete=models.CASCADE,
        related_name='characters'
    )
    
    # Basis
    name = models.CharField(max_length=100)
    full_name = models.CharField(max_length=200, blank=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.OTHER
    )
    
    # Story-Kontext
    introduced_in = models.CharField(
        max_length=200,
        blank=True,
        help_text="Story, in der der Charakter eingeführt wurde"
    )
    current_status = models.TextField(
        blank=True,
        help_text="Aktueller Status des Charakters"
    )
    
    # Details (JSONB)
    known_facts = ArrayField(
        models.TextField(),
        default=list,
        help_text="Bekannte Fakten über den Charakter"
    )
    relationships = models.JSONField(
        default=dict,
        help_text="Beziehungen zu anderen Charakteren"
    )
    # Format: {"Marco": "Partner", "Anna": "Schwester"}
    
    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.role})"
```

### PersonalPlace Model

```python
class PersonalPlace(models.Model):
    """Persönlicher Ort des Users"""
    
    class PlaceType(models.TextChoices):
        RESTAURANT = 'restaurant', 'Restaurant'
        BAR = 'bar', 'Bar'
        CAFE = 'cafe', 'Café'
        HOTEL = 'hotel', 'Hotel'
        MUSEUM = 'museum', 'Museum'
        LANDMARK = 'landmark', 'Sehenswürdigkeit'
        VIEWPOINT = 'viewpoint', 'Aussichtspunkt'
        PARK = 'park', 'Park'
        BEACH = 'beach', 'Strand'
        HIDDEN_GEM = 'hidden_gem', 'Geheimtipp'
        OTHER = 'other', 'Sonstiges'
    
    class Sentiment(models.TextChoices):
        POSITIVE = 'positive', 'Positiv'
        NEGATIVE = 'negative', 'Negativ'
        NEUTRAL = 'neutral', 'Neutral'
    
    # Beziehungen
    world = models.ForeignKey(
        UserWorld,
        on_delete=models.CASCADE,
        related_name='personal_places'
    )
    
    # Location
    location_id = models.CharField(
        max_length=100,
        help_text="ID der BaseLocation"
    )
    
    # Details
    name = models.CharField(max_length=200)
    place_type = models.CharField(
        max_length=20,
        choices=PlaceType.choices,
        default=PlaceType.OTHER
    )
    note = models.TextField(
        blank=True,
        help_text="Persönliche Notiz"
    )
    
    # Verwendung
    use_in_story = models.BooleanField(
        default=True,
        help_text="Soll dieser Ort in Stories verwendet werden?"
    )
    sentiment = models.CharField(
        max_length=20,
        choices=Sentiment.choices,
        default=Sentiment.NEUTRAL
    )
    
    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['location_id', 'name']
    
    def __str__(self):
        status = "✓" if self.use_in_story else "✗"
        return f"{status} {self.name} ({self.location_id})"
```

### LocationMemory Model

```python
class LocationMemory(models.Model):
    """Story-Erinnerung an einem Ort"""
    
    # Beziehungen
    world = models.ForeignKey(
        UserWorld,
        on_delete=models.CASCADE,
        related_name='location_memories'
    )
    
    # Location & Story
    location_id = models.CharField(max_length=100)
    story = models.ForeignKey(
        'stories.Story',
        on_delete=models.CASCADE,
        related_name='location_memories'
    )
    chapter_number = models.PositiveIntegerField()
    
    # Ereignis
    event = models.TextField(
        help_text="Was ist passiert?"
    )
    characters_involved = ArrayField(
        models.CharField(max_length=100),
        default=list
    )
    emotional_tone = models.CharField(
        max_length=50,
        help_text="Emotionaler Ton (romantic, tense, sad, ...)"
    )
    
    # Referenzierbarkeit
    can_reference = models.BooleanField(
        default=True,
        help_text="Kann in zukünftigen Stories referenziert werden?"
    )
    
    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['location_id', '-created_at']
    
    def __str__(self):
        return f"{self.location_id}: {self.event[:50]}..."
```

---

## 5. stories App

### Story Model

```python
# stories/models.py

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Story(models.Model):
    """Eine generierte Geschichte"""
    
    class Genre(models.TextChoices):
        ROMANCE = 'romance', 'Romance'
        THRILLER = 'thriller', 'Thriller'
        ROMANTIC_SUSPENSE = 'romantic_suspense', 'Romantic Suspense'
        MYSTERY = 'mystery', 'Mystery'
        COZY_MYSTERY = 'cozy_mystery', 'Cozy Mystery'
    
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Entwurf'
        GENERATING = 'generating', 'Wird generiert'
        COMPLETE = 'complete', 'Fertig'
        ERROR = 'error', 'Fehler'
    
    # Beziehungen
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='stories'
    )
    trip = models.OneToOneField(
        'trips.Trip',
        on_delete=models.SET_NULL,
        null=True,
        related_name='story'
    )
    
    # Basis
    title = models.CharField(max_length=300)
    genre = models.CharField(
        max_length=30,
        choices=Genre.choices
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    
    # Story-Kontext (JSONB)
    context = models.JSONField(default=dict)
    # Format: {"protagonist": {...}, "love_interest": {...}, 
    #          "antagonist": {...}, "central_conflict": "...", ...}
    
    # Statistiken
    total_chapters = models.PositiveIntegerField(default=0)
    total_words = models.PositiveIntegerField(default=0)
    
    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name_plural = 'Stories'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
```

### Chapter Model

```python
class Chapter(models.Model):
    """Ein Kapitel einer Story"""
    
    # Beziehungen
    story = models.ForeignKey(
        Story,
        on_delete=models.CASCADE,
        related_name='chapters'
    )
    
    # Basis
    number = models.PositiveIntegerField()
    title = models.CharField(max_length=200)
    
    # Content
    content = models.TextField()
    word_count = models.PositiveIntegerField(default=0)
    
    # Location-Sync
    story_location = models.CharField(
        max_length=100,
        blank=True,
        help_text="Wo spielt das Kapitel?"
    )
    reader_location = models.CharField(
        max_length=100,
        blank=True,
        help_text="Wo ist der Leser?"
    )
    reading_date = models.DateField(
        null=True, blank=True,
        help_text="Wann soll gelesen werden?"
    )
    
    # Story-Beat (JSONB)
    beat_info = models.JSONField(default=dict)
    # Format: {"beat_name": "HOOK", "pacing": "action", 
    #          "emotional_tone": "...", "special_instructions": [...]}
    
    # Generierung
    model_used = models.CharField(max_length=50, blank=True)
    generated_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['number']
        unique_together = ['story', 'number']
    
    def __str__(self):
        return f"{self.story.title} - Kapitel {self.number}: {self.title}"
```

### ReadingProgress Model

```python
class ReadingProgress(models.Model):
    """Lesefortschritt eines Users"""
    
    # Beziehungen
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reading_progress'
    )
    story = models.ForeignKey(
        Story,
        on_delete=models.CASCADE,
        related_name='reading_progress'
    )
    chapter = models.ForeignKey(
        Chapter,
        on_delete=models.CASCADE,
        related_name='reading_progress'
    )
    
    # Fortschritt
    progress_percent = models.FloatField(default=0.0)
    is_completed = models.BooleanField(default=False)
    
    # Zeit
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    reading_time_seconds = models.PositiveIntegerField(default=0)
    
    class Meta:
        unique_together = ['user', 'story', 'chapter']
    
    def __str__(self):
        status = "✓" if self.is_completed else f"{self.progress_percent:.0f}%"
        return f"{self.user.username}: {self.chapter} - {status}"
```

---

## 6. Beziehungen

### Übersicht

```
User
 │
 ├──1:n──▶ Trip ───1:n──▶ Stop ───n:1──▶ BaseLocation
 │          │                               │
 │          └──1:1──▶ Story ───1:n──▶ Chapter
 │                      │
 │                      └──1:n──▶ LocationMemory
 │
 └──1:1──▶ UserWorld
             │
             ├──1:n──▶ Character
             ├──1:n──▶ PersonalPlace
             └──1:n──▶ LocationMemory

BaseLocation ───1:n──▶ LocationLayer
```

### Foreign Keys

| Von | Zu | Typ | On Delete |
|-----|-----|-----|-----------|
| Trip | User | FK | CASCADE |
| Stop | Trip | FK | CASCADE |
| Stop | BaseLocation | FK | SET_NULL |
| Transport | Trip | FK | CASCADE |
| Story | User | FK | CASCADE |
| Story | Trip | 1:1 | SET_NULL |
| Chapter | Story | FK | CASCADE |
| UserWorld | User | 1:1 | CASCADE |
| Character | UserWorld | FK | CASCADE |
| PersonalPlace | UserWorld | FK | CASCADE |
| LocationMemory | UserWorld | FK | CASCADE |
| LocationMemory | Story | FK | CASCADE |
| LocationLayer | BaseLocation | FK | CASCADE |
| ReadingProgress | User | FK | CASCADE |
| ReadingProgress | Story | FK | CASCADE |
| ReadingProgress | Chapter | FK | CASCADE |

---

## Nächster Teil

→ **Teil 3: API & Views** (Django Views, HTMX Endpoints)
