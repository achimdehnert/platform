"""
Trip Models - Core Travel Data
"""

from django.db import models
from django.conf import settings
from datetime import timedelta


class Trip(models.Model):
    """Eine Reise des Users"""
    
    class TripType(models.TextChoices):
        CITY = 'city', 'Städtereise'
        BEACH = 'beach', 'Strandurlaub'
        WELLNESS = 'wellness', 'Wellness'
        BACKPACKING = 'backpacking', 'Backpacking'
        BUSINESS = 'business', 'Geschäftsreise'
        FAMILY = 'family', 'Familienurlaub'
        ADVENTURE = 'adventure', 'Abenteuerreise'
        CRUISE = 'cruise', 'Kreuzfahrt'
    
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Entwurf'
        READY = 'ready', 'Bereit zur Generierung'
        GENERATING = 'generating', 'Story wird generiert'
        COMPLETED = 'completed', 'Abgeschlossen'
        ARCHIVED = 'archived', 'Archiviert'
    
    # Beziehungen
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='trips',
    )
    
    # Basis-Daten
    name = models.CharField(max_length=200)
    trip_type = models.CharField(
        max_length=20,
        choices=TripType.choices,
        default=TripType.CITY,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    
    # Reisedaten
    origin = models.CharField(max_length=100, help_text='Startort')
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Berechnet (nach Calculator)
    total_reading_minutes = models.PositiveIntegerField(default=0)
    recommended_chapters = models.PositiveIntegerField(default=0)
    recommended_words = models.PositiveIntegerField(default=0)
    
    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Reise'
        verbose_name_plural = 'Reisen'
    
    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date})"
    
    @property
    def duration_days(self) -> int:
        return (self.end_date - self.start_date).days + 1
    
    @property
    def stops_count(self) -> int:
        return self.stops.count()
    
    def get_stop_for_date(self, date):
        """Get the stop for a specific date."""
        return self.stops.filter(
            arrival_date__lte=date,
            departure_date__gte=date,
        ).first()


class Stop(models.Model):
    """Ein Stopp auf der Reise"""
    
    class AccommodationType(models.TextChoices):
        HOTEL = 'hotel', 'Hotel'
        AIRBNB = 'airbnb', 'Airbnb/Ferienwohnung'
        HOSTEL = 'hostel', 'Hostel'
        CAMPING = 'camping', 'Camping'
        FRIENDS = 'friends', 'Bei Freunden'
        RESORT = 'resort', 'Resort'
        CRUISE = 'cruise', 'Kreuzfahrtschiff'
        OTHER = 'other', 'Sonstiges'
    
    # Beziehungen
    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name='stops',
    )
    
    # Location
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    
    # Optional: Link to BaseLocation (lazy-loaded)
    base_location = models.ForeignKey(
        'locations.BaseLocation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='trip_stops',
    )
    
    # Daten
    arrival_date = models.DateField()
    departure_date = models.DateField()
    
    # Unterkunft
    accommodation_type = models.CharField(
        max_length=20,
        choices=AccommodationType.choices,
        default=AccommodationType.HOTEL,
    )
    accommodation_name = models.CharField(max_length=200, blank=True)
    
    # Reihenfolge
    order = models.PositiveIntegerField(default=0)
    
    # Notizen
    notes = models.TextField(blank=True, help_text='Notizen zum Aufenthalt')
    
    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'arrival_date']
        verbose_name = 'Stopp'
        verbose_name_plural = 'Stopps'
    
    def __str__(self):
        return f"{self.city}, {self.country}"
    
    @property
    def nights(self) -> int:
        return (self.departure_date - self.arrival_date).days
    
    @property
    def has_pool_time(self) -> bool:
        """Check if this accommodation type typically has pool/beach time."""
        return self.accommodation_type in [
            self.AccommodationType.RESORT,
            self.AccommodationType.HOTEL,
        ] or self.trip.trip_type in ['beach', 'wellness']


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
        related_name='transports',
    )
    from_stop = models.ForeignKey(
        Stop,
        on_delete=models.CASCADE,
        related_name='departures',
        null=True,
        blank=True,
        help_text='Null = von Origin',
    )
    to_stop = models.ForeignKey(
        Stop,
        on_delete=models.CASCADE,
        related_name='arrivals',
    )
    
    # Transport-Details
    transport_type = models.CharField(
        max_length=20,
        choices=TransportType.choices,
        default=TransportType.FLIGHT,
    )
    duration_minutes = models.PositiveIntegerField(
        help_text='Gesamte Reisezeit in Minuten',
    )
    departure_datetime = models.DateTimeField(null=True, blank=True)
    
    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['departure_datetime']
        verbose_name = 'Transport'
        verbose_name_plural = 'Transporte'
    
    def __str__(self):
        from_name = self.from_stop.city if self.from_stop else self.trip.origin
        return f"{from_name} → {self.to_stop.city} ({self.get_transport_type_display()})"
    
    @property
    def reading_efficiency(self) -> float:
        """Get reading efficiency for this transport type."""
        efficiency_map = {
            self.TransportType.FLIGHT: 0.55,
            self.TransportType.TRAIN: 0.80,
            self.TransportType.BUS: 0.50,
            self.TransportType.CAR_PASSENGER: 0.40,
            self.TransportType.CAR_DRIVER: 0.0,
            self.TransportType.FERRY: 0.60,
            self.TransportType.OTHER: 0.30,
        }
        return efficiency_map.get(self.transport_type, 0.30)
    
    @property
    def reading_minutes(self) -> int:
        """Calculate effective reading time during transport."""
        return int(self.duration_minutes * self.reading_efficiency)
