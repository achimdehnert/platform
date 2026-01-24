"""
Travel Story - Complete Pipeline Example
========================================
Verbindet Intake → Calculator → Mapper
"""

import json
from datetime import date

from models import (
    TripInput, Stop, ReaderPreferences,
    TransportType, AccommodationType, TripType, ReadingSpeed, ReadingContext,
)
from calculator import calculate_reading_schedule
from story_models import StoryPreferences, LocationSyncType
from story_mapper import map_story_to_travel


def run_complete_pipeline():
    """
    Führt die komplette Pipeline durch:
    1. Trip-Input definieren
    2. Lesezeit berechnen
    3. Story auf Reise mappen
    4. Ergebnis ausgeben
    """
    
    print("=" * 70)
    print("🌍 TRAVEL STORY - COMPLETE PIPELINE")
    print("=" * 70)
    
    # ═══════════════════════════════════════════════════════════════
    # SCHRITT 1: Trip Input (simuliert Form-Eingabe)
    # ═══════════════════════════════════════════════════════════════
    
    print("\n📝 SCHRITT 1: Reisedaten erfassen")
    print("-" * 50)
    
    trip = TripInput(
        name="Sommerurlaub Barcelona & Rom 2025",
        origin="München",
        departure_date=date(2025, 7, 15),
        return_date=date(2025, 7, 24),
        trip_type=TripType.ROMANTIC,
        transport_type=TransportType.FLIGHT,
        stops=[
            Stop(
                order=1,
                city="Barcelona",
                nights=4,
                accommodation=AccommodationType.HOTEL,
            ),
            Stop(
                order=2,
                city="Rom",
                nights=5,
                accommodation=AccommodationType.AIRBNB,
            ),
        ],
        preferences=ReaderPreferences(
            reading_speed=ReadingSpeed.AVERAGE,
            reading_contexts=[
                ReadingContext.TRANSPORT,
                ReadingContext.MORNING,
                ReadingContext.EVENING,
            ],
        ),
    )
    
    print(f"  Reise: {trip.name}")
    print(f"  Route: {trip.origin} → {' → '.join(s.city for s in trip.stops)} → {trip.origin}")
    print(f"  Zeitraum: {trip.departure_date} bis {trip.return_date} ({trip.total_days} Tage)")
    print(f"  Typ: {trip.trip_type.value}")
    
    # ═══════════════════════════════════════════════════════════════
    # SCHRITT 2: Lesezeit berechnen
    # ═══════════════════════════════════════════════════════════════
    
    print("\n⏱️  SCHRITT 2: Lesezeit berechnen")
    print("-" * 50)
    
    reading_schedule = calculate_reading_schedule(trip)
    
    print(f"  Gesamte Lesezeit: {reading_schedule.total_reading_minutes} Minuten")
    print(f"  Wort-Budget: {reading_schedule.total_word_budget:,} Wörter")
    print(f"  Empfohlene Kapitel: {reading_schedule.recommended_chapters}")
    print(f"  Empfohlene Story-Länge: {reading_schedule.recommended_word_count:,} Wörter")
    
    print("\n  Tagesverteilung:")
    for day in reading_schedule.daily_schedules[:3]:  # Erste 3 Tage
        print(f"    Tag {day.day_number} ({day.location}): {day.total_reading_minutes} min")
    print(f"    ... und {len(reading_schedule.daily_schedules) - 3} weitere Tage")
    
    # ═══════════════════════════════════════════════════════════════
    # SCHRITT 3: Story-Präferenzen definieren
    # ═══════════════════════════════════════════════════════════════
    
    print("\n📚 SCHRITT 3: Story-Präferenzen")
    print("-" * 50)
    
    story_prefs = StoryPreferences(
        genre="romantic_suspense",
        spice_level="moderate",
        location_sync="exact",
        ending="happy",
        triggers_avoid=["violence", "crash"],
    )
    
    print(f"  Genre: {story_prefs.genre}")
    print(f"  Spice-Level: {story_prefs.spice_level}")
    print(f"  Location-Sync: {story_prefs.location_sync}")
    print(f"  Ending: {story_prefs.ending}")
    
    # ═══════════════════════════════════════════════════════════════
    # SCHRITT 4: Story auf Reise mappen
    # ═══════════════════════════════════════════════════════════════
    
    print("\n🗺️  SCHRITT 4: Story-Mapping")
    print("-" * 50)
    
    story_outline = map_story_to_travel(
        reading_schedule=reading_schedule,
        story_preferences=story_prefs,
        trip_origin=trip.origin,
    )
    
    print(f"  Story-Titel: {story_outline.title}")
    print(f"  Kapitelanzahl: {story_outline.total_chapters}")
    print(f"  Gesamtwörter: {story_outline.total_words:,}")
    
    # Akt-Übersicht
    print("\n  Akt-Verteilung:")
    act_summary = story_outline._get_act_summary()
    for act, data in act_summary.items():
        chapter_range = f"Kap. {min(data['chapters'])}-{max(data['chapters'])}" if data['chapters'] else "—"
        print(f"    {act}: {chapter_range} ({data['word_count']:,} Wörter)")
    
    # ═══════════════════════════════════════════════════════════════
    # SCHRITT 5: Detaillierte Kapitelübersicht
    # ═══════════════════════════════════════════════════════════════
    
    print("\n📖 SCHRITT 5: Kapitelübersicht")
    print("-" * 50)
    
    for ch in story_outline.chapters:
        print(f"\n  Kapitel {ch.chapter_number}")
        print(f"    📅 Datum: {ch.reading_date} | Kontext: {ch.reading_context}")
        print(f"    📍 Leser: {ch.reader_location} | Story: {ch.story_location}")
        print(f"    📊 Akt: {ch.act.value} | Beat: {', '.join(b.value for b in ch.beats)}")
        print(f"    🎭 Pacing: {ch.pacing.value} | Ton: {ch.emotional_tone[:40]}...")
        print(f"    📝 Wörter: {ch.word_target:,}")
        if ch.special_instructions:
            print(f"    ⚡ Anweisungen: {ch.special_instructions[0][:50]}...")
    
    # ═══════════════════════════════════════════════════════════════
    # SCHRITT 6: JSON Export
    # ═══════════════════════════════════════════════════════════════
    
    print("\n" + "=" * 70)
    print("💾 SCHRITT 6: JSON Export")
    print("-" * 50)
    
    # Kombiniertes Output
    complete_output = {
        "trip_input": {
            "name": trip.name,
            "origin": trip.origin,
            "stops": [{"city": s.city, "nights": s.nights} for s in trip.stops],
            "dates": {
                "departure": trip.departure_date.isoformat(),
                "return": trip.return_date.isoformat(),
            },
        },
        "reading_schedule": reading_schedule.to_dict(),
        "story_outline": story_outline.to_dict(),
    }
    
    # Save to file
    output_file = "complete_travel_story_output.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(complete_output, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"  ✅ Gespeichert: {output_file}")
    print(f"  📊 Dateigröße: {len(json.dumps(complete_output)):,} Zeichen")
    
    # Print sample
    print("\n  JSON-Vorschau (Kapitel 1):")
    ch1 = story_outline.chapters[0].to_dict()
    print(json.dumps(ch1, indent=4, ensure_ascii=False)[:500] + "...")
    
    return complete_output


def show_travel_beat_summary(output: dict):
    """
    Zeigt eine kompakte Travel-Beat-Übersicht.
    """
    print("\n" + "=" * 70)
    print("📋 TRAVEL BEAT SUMMARY")
    print("=" * 70)
    
    chapters = output["story_outline"]["chapters"]
    
    # Group by date
    by_date = {}
    for ch in chapters:
        d = ch["reading_date"]
        if d not in by_date:
            by_date[d] = []
        by_date[d].append(ch)
    
    print(f"\n{'Datum':<12} {'Ort':<15} {'Kap.':<5} {'Akt':<8} {'Beat':<20} {'Wörter':>8}")
    print("-" * 70)
    
    for date_str, chs in by_date.items():
        for i, ch in enumerate(chs):
            date_col = date_str if i == 0 else ""
            location = ch["reader_location"][:13] if i == 0 else ""
            beat = ch["beats"][0][:18] if ch["beats"] else ""
            
            print(f"{date_col:<12} {location:<15} {ch['chapter_number']:<5} {ch['act']:<8} {beat:<20} {ch['word_target']:>8,}")
    
    print("-" * 70)
    total_words = sum(ch["word_target"] for ch in chapters)
    print(f"{'GESAMT':<12} {'':<15} {len(chapters):<5} {'':<8} {'':<20} {total_words:>8,}")


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    output = run_complete_pipeline()
    show_travel_beat_summary(output)
    
    print("\n" + "=" * 70)
    print("✅ Pipeline erfolgreich abgeschlossen!")
    print("=" * 70)
