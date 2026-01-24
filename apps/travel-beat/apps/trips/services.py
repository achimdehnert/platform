"""
Trip Services - Reading Time Calculator
"""

from dataclasses import dataclass, field
from typing import List
from datetime import date, timedelta

from .models import Trip, Stop, Transport


@dataclass
class DaySchedule:
    """Lesezeit für einen Tag"""
    date: date
    location: str
    morning_minutes: int = 0
    transport_minutes: int = 0
    pool_minutes: int = 0
    evening_minutes: int = 0
    
    @property
    def total_minutes(self) -> int:
        return (
            self.morning_minutes + 
            self.transport_minutes + 
            self.pool_minutes + 
            self.evening_minutes
        )


@dataclass
class CalculationResult:
    """Ergebnis der Lesezeit-Berechnung"""
    total_minutes: int
    total_words: int
    recommended_chapters: int
    daily_schedule: List[DaySchedule] = field(default_factory=list)
    
    @property
    def hours(self) -> float:
        return self.total_minutes / 60


class ReadingTimeCalculator:
    """Berechnet verfügbare Lesezeit für eine Reise"""
    
    # Lesegeschwindigkeit (Wörter pro Minute)
    WORDS_PER_MINUTE = {
        'slow': 200,
        'normal': 250,
        'fast': 300,
    }
    
    WORDS_PER_CHAPTER = 3500
    MAX_CHAPTERS = 30
    MIN_CHAPTERS = 5
    
    # Abend-Lesezeit nach Unterkunft (Minuten)
    EVENING_READING = {
        'hotel': 45,
        'airbnb': 50,
        'hostel': 30,
        'camping': 20,
        'friends': 25,
        'resort': 60,
        'cruise': 75,
        'other': 30,
    }
    
    # Morgen-Lesezeit (vor dem Aufstehen)
    MORNING_READING = {
        'hotel': 20,
        'airbnb': 25,
        'hostel': 10,
        'camping': 10,
        'friends': 15,
        'resort': 30,
        'cruise': 30,
        'other': 15,
    }
    
    # Pool/Strand-Zeit nach Reisetyp (Minuten pro Tag)
    POOL_READING = {
        'beach': 90,
        'wellness': 75,
        'city': 0,
        'backpacking': 15,
        'business': 0,
        'family': 30,
        'adventure': 20,
        'cruise': 60,
    }
    
    def calculate(self, trip: Trip, reading_speed: str = 'normal') -> CalculationResult:
        """
        Berechne Lesezeit für eine Reise.
        """
        wpm = self.WORDS_PER_MINUTE.get(reading_speed, 250)
        
        daily_schedules = []
        current_date = trip.start_date
        
        while current_date <= trip.end_date:
            schedule = self._calculate_day(trip, current_date)
            daily_schedules.append(schedule)
            current_date += timedelta(days=1)
        
        total_minutes = sum(d.total_minutes for d in daily_schedules)
        total_words = int(total_minutes * wpm)
        
        # Empfohlene Kapitelzahl berechnen
        recommended_chapters = max(
            self.MIN_CHAPTERS,
            min(self.MAX_CHAPTERS, total_words // self.WORDS_PER_CHAPTER)
        )
        
        return CalculationResult(
            total_minutes=total_minutes,
            total_words=total_words,
            recommended_chapters=recommended_chapters,
            daily_schedule=daily_schedules,
        )
    
    def _calculate_day(self, trip: Trip, day: date) -> DaySchedule:
        """Berechne Lesezeit für einen Tag"""
        
        # Aktueller Stopp finden
        stop = trip.get_stop_for_date(day)
        
        if not stop:
            # Transit-Tag ohne Stopp
            return DaySchedule(date=day, location="Transit")
        
        location = f"{stop.city}, {stop.country}"
        
        # Basis-Lesezeiten
        morning = self.MORNING_READING.get(stop.accommodation_type, 15)
        evening = self.EVENING_READING.get(stop.accommodation_type, 30)
        pool = self.POOL_READING.get(trip.trip_type, 0)
        
        # Transport an diesem Tag?
        transport_minutes = 0
        transports = trip.transports.filter(
            departure_datetime__date=day
        )
        for transport in transports:
            transport_minutes += transport.reading_minutes
        
        # Erster Tag: weniger Morgen-Lesezeit (Anreise)
        if day == trip.start_date:
            morning = 0
        
        # Letzter Tag: weniger Abend-Lesezeit (Abreise)
        if day == trip.end_date:
            evening = evening // 2
            pool = 0
        
        # Abreisetag vom Stopp
        if day == stop.departure_date and day != trip.end_date:
            evening = evening // 2
        
        return DaySchedule(
            date=day,
            location=location,
            morning_minutes=morning,
            transport_minutes=transport_minutes,
            pool_minutes=pool,
            evening_minutes=evening,
        )
