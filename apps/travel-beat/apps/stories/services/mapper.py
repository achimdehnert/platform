"""
Story Mapper - Maps Trip Data to Story Structure

Converts:
- Trip stops → Story locations
- Reading time → Chapter word counts
- Travel days → Story timeline
- Story beats → Chapter assignments
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

from apps.trips.services import ReadingTimeCalculator, CalculationResult


@dataclass
class ChapterPlan:
    """Plan for a single chapter."""
    chapter_number: int
    date: date
    location_city: str
    location_country: str
    story_beat: str
    pacing_type: str
    word_count: int
    reading_slot: str  # morning, afternoon, evening, transport
    transport_type: Optional[str] = None


@dataclass
class StoryPlan:
    """Complete story plan mapped from trip."""
    trip_id: int
    total_chapters: int
    total_words: int
    chapters: list[ChapterPlan] = field(default_factory=list)
    

class StoryMapper:
    """Maps trip data to story structure."""
    
    # Story beat sequence (16 beats, Blake Snyder's Save the Cat)
    STORY_BEATS = [
        ('opening_image', 'reflective'),
        ('setup', 'emotional'),
        ('catalyst', 'action'),
        ('debate', 'emotional'),
        ('break_into_two', 'transitional'),
        ('b_story', 'emotional'),
        ('fun_and_games', 'action'),
        ('fun_and_games', 'action'),
        ('midpoint', 'climax'),
        ('bad_guys_close_in', 'action'),
        ('all_is_lost', 'emotional'),
        ('dark_night', 'reflective'),
        ('break_into_three', 'transitional'),
        ('finale', 'climax'),
        ('finale', 'action'),
        ('final_image', 'resolution'),
    ]
    
    # Minimum beats for shorter stories
    SHORT_STORY_BEATS = [
        ('opening_image', 'reflective'),
        ('catalyst', 'action'),
        ('fun_and_games', 'action'),
        ('midpoint', 'climax'),
        ('all_is_lost', 'emotional'),
        ('finale', 'climax'),
        ('final_image', 'resolution'),
    ]
    
    WORDS_PER_MINUTE = 250  # Average reading speed
    
    def __init__(self, trip, user=None):
        self.trip = trip
        self.user = user
        self.reading_speed = user.reading_speed if user else self.WORDS_PER_MINUTE
    
    def calculate_reading_time(self) -> CalculationResult:
        """Calculate available reading time for the trip."""
        calculator = ReadingTimeCalculator(self.trip, self.user)
        return calculator.calculate()
    
    def map_to_story_plan(self) -> StoryPlan:
        """Map trip to complete story plan."""
        
        # Calculate reading time
        reading_result = self.calculate_reading_time()
        
        # Determine number of chapters based on reading slots
        reading_slots = self._extract_reading_slots(reading_result)
        num_chapters = len(reading_slots)
        
        # Select appropriate beat structure
        if num_chapters <= 7:
            beats = self.SHORT_STORY_BEATS[:num_chapters]
        else:
            beats = self._distribute_beats(num_chapters)
        
        # Create chapter plans
        chapters = []
        total_words = 0
        
        for i, (slot, (beat, pacing)) in enumerate(zip(reading_slots, beats)):
            word_count = slot['minutes'] * self.reading_speed
            
            chapter = ChapterPlan(
                chapter_number=i + 1,
                date=slot['date'],
                location_city=slot['city'],
                location_country=slot['country'],
                story_beat=beat,
                pacing_type=pacing,
                word_count=word_count,
                reading_slot=slot['slot_type'],
                transport_type=slot.get('transport_type'),
            )
            chapters.append(chapter)
            total_words += word_count
        
        return StoryPlan(
            trip_id=self.trip.id,
            total_chapters=num_chapters,
            total_words=total_words,
            chapters=chapters,
        )
    
    def _extract_reading_slots(self, reading_result: CalculationResult) -> list[dict]:
        """Extract reading slots from calculation result."""
        slots = []
        
        for day in reading_result.daily_breakdown:
            # Get location for this day
            stop = self._get_stop_for_date(day.date)
            city = stop.city if stop else self.trip.origin
            country = stop.country if stop else ""
            
            # Transport reading
            if day.transport_minutes > 30:
                slots.append({
                    'date': day.date,
                    'city': city,
                    'country': country,
                    'minutes': day.transport_minutes,
                    'slot_type': 'transport',
                    'transport_type': day.transport_type,
                })
            
            # Evening reading
            if day.evening_minutes > 20:
                slots.append({
                    'date': day.date,
                    'city': city,
                    'country': country,
                    'minutes': day.evening_minutes,
                    'slot_type': 'evening',
                })
        
        return slots
    
    def _get_stop_for_date(self, target_date: date):
        """Get the stop the traveler is at on a given date."""
        stops = list(self.trip.stops.order_by('arrival_date'))
        
        current_stop = None
        for stop in stops:
            if stop.arrival_date <= target_date:
                if stop.departure_date is None or stop.departure_date >= target_date:
                    current_stop = stop
            else:
                break
        
        return current_stop
    
    def _distribute_beats(self, num_chapters: int) -> list[tuple[str, str]]:
        """Distribute story beats across chapters."""
        
        if num_chapters >= 16:
            # Full beat sheet, possibly with extras
            beats = list(self.STORY_BEATS)
            # Add extra "fun_and_games" chapters if needed
            while len(beats) < num_chapters:
                beats.insert(7, ('fun_and_games', 'action'))
            return beats[:num_chapters]
        
        elif num_chapters >= 10:
            # Condense some beats
            return [
                ('opening_image', 'reflective'),
                ('setup', 'emotional'),
                ('catalyst', 'action'),
                ('break_into_two', 'transitional'),
                ('b_story', 'emotional'),
                ('fun_and_games', 'action'),
                ('midpoint', 'climax'),
                ('bad_guys_close_in', 'action'),
                ('all_is_lost', 'emotional'),
                ('dark_night', 'reflective'),
                ('finale', 'climax'),
                ('final_image', 'resolution'),
            ][:num_chapters]
        
        else:
            # Use short story beats
            return self.SHORT_STORY_BEATS[:num_chapters]
    
    def get_locations_for_story(self) -> list[dict]:
        """Get location information for story generation."""
        locations = []
        
        # Add origin
        locations.append({
            'city': self.trip.origin,
            'country': '',  # Origin might not have country
            'type': 'origin',
            'atmosphere': 'familiar',
        })
        
        # Add stops
        for stop in self.trip.stops.order_by('arrival_date'):
            locations.append({
                'city': stop.city,
                'country': stop.country,
                'type': 'destination',
                'atmosphere': stop.notes or 'neutral',
                'arrival_date': stop.arrival_date,
                'departure_date': stop.departure_date,
            })
        
        return locations
