"""
Travel Story - Complete End-to-End Pipeline
============================================
Von Formular-Eingabe bis generierte Story.
"""

import json
from datetime import date

# Import all modules
from models import (
    TripInput, Stop, ReaderPreferences,
    TransportType, AccommodationType, TripType, ReadingSpeed, ReadingContext,
)
from calculator import calculate_reading_schedule
from story_models import StoryPreferences
from story_mapper import map_story_to_travel
from agent_prompts import StoryContext
from story_generator import generate_story, GeneratedStory


def print_header(text: str):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_section(text: str):
    """Print a section header"""
    print(f"\n{'─' * 50}")
    print(f"  {text}")
    print(f"{'─' * 50}")


def run_full_pipeline():
    """
    Führt die komplette Pipeline durch:
    1. Reise-Input (simuliert Formular)
    2. Lesezeit-Berechnung
    3. Story-Mapping
    4. Story-Generierung (Mock)
    5. Export
    """
    
    print_header("🌍 TRAVEL STORY - VOLLSTÄNDIGE PIPELINE")
    
    # ═══════════════════════════════════════════════════════════════
    # PHASE 1: INPUT
    # ═══════════════════════════════════════════════════════════════
    
    print_section("📝 PHASE 1: Reise-Eingabe")
    
    # Simuliere Formular-Eingabe
    trip_input = TripInput(
        name="Romantischer Städtetrip Barcelona & Rom",
        origin="München",
        departure_date=date(2025, 7, 15),
        return_date=date(2025, 7, 22),
        trip_type=TripType.ROMANTIC,
        transport_type=TransportType.FLIGHT,
        stops=[
            Stop(order=1, city="Barcelona", nights=3, accommodation=AccommodationType.HOTEL),
            Stop(order=2, city="Rom", nights=4, accommodation=AccommodationType.AIRBNB),
        ],
        preferences=ReaderPreferences(
            reading_speed=ReadingSpeed.AVERAGE,
            reading_contexts=[
                ReadingContext.TRANSPORT,
                ReadingContext.EVENING,
            ],
        ),
    )
    
    story_prefs = StoryPreferences(
        genre="romantic_suspense",
        spice_level="moderate",
        location_sync="exact",
        ending="happy",
        triggers_avoid=["violence", "crash"],
    )
    
    print(f"  Reise: {trip_input.name}")
    print(f"  Route: {trip_input.origin} → Barcelona → Rom → {trip_input.origin}")
    print(f"  Dauer: {trip_input.total_days} Tage")
    print(f"  Genre: {story_prefs.genre}")
    
    # ═══════════════════════════════════════════════════════════════
    # PHASE 2: BERECHNUNG
    # ═══════════════════════════════════════════════════════════════
    
    print_section("⏱️  PHASE 2: Lesezeit-Berechnung")
    
    reading_schedule = calculate_reading_schedule(trip_input)
    
    print(f"  Verfügbare Lesezeit: {reading_schedule.total_reading_minutes} Minuten")
    print(f"  Wort-Budget: {reading_schedule.total_word_budget:,} Wörter")
    print(f"  Empfohlene Kapitel: {reading_schedule.recommended_chapters}")
    
    # ═══════════════════════════════════════════════════════════════
    # PHASE 3: MAPPING
    # ═══════════════════════════════════════════════════════════════
    
    print_section("🗺️  PHASE 3: Story-Mapping")
    
    story_outline = map_story_to_travel(
        reading_schedule=reading_schedule,
        story_preferences=story_prefs,
        trip_origin=trip_input.origin,
    )
    
    print(f"  Kapitel: {story_outline.total_chapters}")
    print(f"  Ziel-Wörter: {story_outline.total_words:,}")
    
    # Zeige Beat-Verteilung
    print("\n  Kapitel-Übersicht:")
    for ch in story_outline.chapters[:5]:
        beat = ch.beats[0].value if ch.beats else "—"
        print(f"    Kap. {ch.chapter_number}: {ch.story_location[:20]:<20} | {beat}")
    if len(story_outline.chapters) > 5:
        print(f"    ... und {len(story_outline.chapters) - 5} weitere")
    
    # ═══════════════════════════════════════════════════════════════
    # PHASE 4: STORY-KONTEXT DEFINIEREN
    # ═══════════════════════════════════════════════════════════════
    
    print_section("👤 PHASE 4: Story-Kontext")
    
    # In Produktion würde dies durch User-Input oder AI generiert
    story_context = StoryContext(
        title="Schatten über dem Mittelmeer",
        genre="romantic_suspense",
        protagonist_name="Elena",
        protagonist_description="32, Kunsthistorikerin aus München. Kürzlich geschieden, auf der Suche nach Neuanfang.",
        setting_description="Sommer in Barcelona und Rom. Kunst, Geheimnisse, mediterrane Nächte.",
        central_conflict="Elena entdeckt bei ihrer Recherche einen Kunstfälschungsring und gerät in Gefahr.",
        love_interest_name="Marco",
        love_interest_description="35, italienischer Journalist. Investigativ, charmant, mit eigenen Geheimnissen.",
        antagonist_name="Der Kurator",
        antagonist_description="Mysteriöse Figur hinter dem Fälschungsring. Einflussreich, gefährlich.",
    )
    
    print(f"  Titel: {story_context.title}")
    print(f"  Protagonistin: {story_context.protagonist_name}")
    print(f"  Love Interest: {story_context.love_interest_name}")
    print(f"  Konflikt: {story_context.central_conflict[:60]}...")
    
    # ═══════════════════════════════════════════════════════════════
    # PHASE 5: GENERIERUNG
    # ═══════════════════════════════════════════════════════════════
    
    print_section("✍️  PHASE 5: Story-Generierung (Mock)")
    
    def progress_callback(current, total, chapter):
        bar_length = 30
        progress = current / total
        filled = int(bar_length * progress)
        bar = "█" * filled + "░" * (bar_length - filled)
        print(f"\r  [{bar}] Kapitel {current}/{total}: {chapter.word_count} Wörter", end="")
    
    # Generiere mit Mock-Client (keine echten API-Calls)
    generated_story = generate_story(
        story_outline=story_outline,
        story_context=story_context,
        story_preferences=story_prefs,
        use_mock=True,
        progress_callback=progress_callback,
    )
    
    print("\n")  # Neue Zeile nach Progress-Bar
    print(f"  ✅ Generierung abgeschlossen!")
    print(f"  Kapitel: {len(generated_story.chapters)}")
    print(f"  Wörter: {generated_story.total_words:,}")
    
    # ═══════════════════════════════════════════════════════════════
    # PHASE 6: EXPORT
    # ═══════════════════════════════════════════════════════════════
    
    print_section("💾 PHASE 6: Export")
    
    # Save JSON
    json_file = "generated_story.json"
    generated_story.save_json(json_file)
    print(f"  ✅ JSON: {json_file}")
    
    # Save Markdown
    md_file = "generated_story.md"
    generated_story.save_markdown(md_file)
    print(f"  ✅ Markdown: {md_file}")
    
    # ═══════════════════════════════════════════════════════════════
    # ZUSAMMENFASSUNG
    # ═══════════════════════════════════════════════════════════════
    
    print_header("📊 ZUSAMMENFASSUNG")
    
    print(f"""
  REISE
  ─────────────────────────────────────
  Name:          {trip_input.name}
  Route:         {trip_input.origin} → Barcelona → Rom → {trip_input.origin}
  Dauer:         {trip_input.total_days} Tage
  Typ:           {trip_input.trip_type.value}
  
  LESEZEIT
  ─────────────────────────────────────
  Verfügbar:     {reading_schedule.total_reading_minutes} Minuten
  Kontexte:      {', '.join(c.value for c in trip_input.preferences.reading_contexts)}
  
  STORY
  ─────────────────────────────────────
  Titel:         {story_context.title}
  Genre:         {story_prefs.genre}
  Kapitel:       {len(generated_story.chapters)}
  Wörter:        {generated_story.total_words:,}
  Spice:         {story_prefs.spice_level}
  
  DATEIEN
  ─────────────────────────────────────
  JSON:          {json_file}
  Markdown:      {md_file}
""")
    
    return generated_story


def show_sample_chapter(story: GeneratedStory, chapter_num: int = 1):
    """Zeige ein Beispiel-Kapitel"""
    print_header(f"📖 BEISPIEL: KAPITEL {chapter_num}")
    
    if chapter_num <= len(story.chapters):
        ch = story.chapters[chapter_num - 1]
        print(f"""
  Kapitel:       {ch.chapter_number}
  Titel:         {ch.title}
  Ort (Story):   {ch.story_location}
  Ort (Leser):   {ch.reader_location}
  Datum:         {ch.reading_date}
  Wörter:        {ch.word_count}
  
  INHALT (Auszug):
  ─────────────────────────────────────
{ch.content[:500]}...
""")
    else:
        print(f"  Kapitel {chapter_num} existiert nicht.")


def show_chapter_schedule(story: GeneratedStory):
    """Zeige den Kapitel-Zeitplan"""
    print_header("📅 KAPITEL-ZEITPLAN")
    
    print(f"\n  {'Datum':<12} {'Ort':<18} {'Kap.':<5} {'Wörter':>8}")
    print(f"  {'─' * 45}")
    
    current_date = None
    for ch in story.chapters:
        date_str = ch.reading_date if ch.reading_date != current_date else ""
        current_date = ch.reading_date
        location = ch.reader_location[:16]
        print(f"  {date_str:<12} {location:<18} {ch.chapter_number:<5} {ch.word_count:>8,}")
    
    print(f"  {'─' * 45}")
    print(f"  {'GESAMT':<12} {'':<18} {len(story.chapters):<5} {story.total_words:>8,}")


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Run pipeline
    story = run_full_pipeline()
    
    # Show extras
    show_sample_chapter(story, 1)
    show_chapter_schedule(story)
    
    print_header("✅ PIPELINE ABGESCHLOSSEN")
    print("\n  Die generierten Dateien können nun weiterverarbeitet werden.")
    print("  In Produktion würde der echte LLM-Client verwendet werden.\n")
