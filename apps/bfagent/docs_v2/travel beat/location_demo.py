"""
Travel Story - Location Database
================================
Part 4: Test & Demo

Demonstriert alle 3 Schichten in Aktion.
"""

import json
from datetime import datetime

from location_models import (
    BaseLocation, LocationLayer, UserWorld, MergedLocationData,
    LayerType, PlaceType, PersonalPlace, StoryCharacter, LocationMemory,
)
from location_repository import LocationRepository
from location_generator import LocationGenerator


def print_header(text: str):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_section(text: str):
    print(f"\n{'─' * 50}")
    print(f"  {text}")
    print(f"{'─' * 50}")


def demo_location_system():
    """
    Vollständige Demo des Location-Systems.
    """
    print_header("🗺️  LOCATION DATABASE DEMO")
    
    # ═══════════════════════════════════════════════════════════════
    # SETUP
    # ═══════════════════════════════════════════════════════════════
    
    print_section("Setup: Repository & Generator")
    
    # In-Memory DB für Demo
    repo = LocationRepository(":memory:")
    generator = LocationGenerator(repo)
    
    print("  ✅ Repository initialisiert (in-memory)")
    print("  ✅ Generator bereit (mit Mock-LLM)")
    
    # ═══════════════════════════════════════════════════════════════
    # SCHICHT 1: BASE_LOCATION
    # ═══════════════════════════════════════════════════════════════
    
    print_section("SCHICHT 1: Base Location (shared)")
    
    # Erste Anfrage: Generiert und speichert
    print("\n  Erste Anfrage für 'Barcelona'...")
    barcelona = generator.get_base_location("Barcelona", "Spanien")
    
    print(f"  ✅ Barcelona generiert:")
    print(f"     Name: {barcelona.name}")
    print(f"     Land: {barcelona.country}")
    print(f"     Region: {barcelona.region}")
    print(f"     Einwohner: {barcelona.population:,}")
    print(f"     Sprachen: {', '.join(barcelona.languages)}")
    print(f"     Viertel: {len(barcelona.districts)}")
    for d in barcelona.districts[:3]:
        print(f"       - {d.name}: {d.vibe}")
    
    # Zweite Anfrage: Aus DB
    print("\n  Zweite Anfrage für 'Barcelona'...")
    barcelona2 = generator.get_base_location("Barcelona")
    print(f"  ✅ Aus DB geladen (kein LLM-Call)")
    
    # Weitere Stadt
    print("\n  Anfrage für 'Rom'...")
    rom = generator.get_base_location("Rom", "Italien")
    print(f"  ✅ Rom generiert: {rom.name}, {len(rom.districts)} Viertel")
    
    # ═══════════════════════════════════════════════════════════════
    # SCHICHT 2: LOCATION_LAYER
    # ═══════════════════════════════════════════════════════════════
    
    print_section("SCHICHT 2: Location Layer (shared, genre-spezifisch)")
    
    # Romance Layer für Barcelona
    print("\n  Generiere 'romance' Layer für Barcelona...")
    bcn_romance = generator.get_location_layer("barcelona", LayerType.ROMANCE, "Barcelona")
    
    print(f"  ✅ Romance-Layer generiert:")
    print(f"     Orte: {len(bcn_romance.places)}")
    print(f"     Story-Hooks: {len(bcn_romance.story_hooks)}")
    
    print("\n     Atmosphären:")
    for time, atm in list(bcn_romance.atmospheres.items())[:2]:
        print(f"       {time}: {atm[:80]}...")
    
    print("\n     Top Romance-Orte:")
    for place in bcn_romance.places[:3]:
        print(f"       - {place.name} ({place.place_type.value})")
        print(f"         Story-Potenzial: {place.story_potential[:60]}...")
    
    # Thriller Layer für Barcelona
    print("\n  Generiere 'thriller' Layer für Barcelona...")
    bcn_thriller = generator.get_location_layer("barcelona", LayerType.THRILLER, "Barcelona")
    
    print(f"  ✅ Thriller-Layer generiert:")
    print(f"     Orte: {len(bcn_thriller.places)}")
    
    print("\n     Top Thriller-Orte:")
    for place in bcn_thriller.places[:2]:
        print(f"       - {place.name} ({place.place_type.value})")
        print(f"         {place.description[:60]}...")
    
    # ═══════════════════════════════════════════════════════════════
    # SCHICHT 3: USER_WORLD
    # ═══════════════════════════════════════════════════════════════
    
    print_section("SCHICHT 3: User World (user-spezifisch)")
    
    # Erstelle User World
    user_world = UserWorld(
        user_id="user_demo_123",
        interests_primary=[LayerType.ROMANCE, LayerType.FOODIE],
        interests_secondary=[LayerType.ART],
        interests_avoid=[LayerType.ADVENTURE],
        story_universe_name="elena_universe",
        preferred_spice_level="moderate",
        preferred_ending="happy",
        triggers_avoid=["violence", "crash"],
    )
    
    # Füge persönliche Orte hinzu
    user_world.personal_places = [
        PersonalPlace(
            location_id="barcelona",
            name="Can Paixano",
            place_type=PlaceType.BAR,
            note="Meine Entdeckung 2019, beste Cava der Stadt!",
            use_in_story=True,
            sentiment="positive",
        ),
        PersonalPlace(
            location_id="barcelona",
            name="Sagrada Familia",
            place_type=PlaceType.LANDMARK,
            note="War dort mit Ex-Freund - bitte nicht verwenden",
            use_in_story=False,  # AUSSCHLUSS
            sentiment="negative",
        ),
    ]
    
    # Füge Charaktere hinzu
    user_world.characters = [
        StoryCharacter(
            name="Elena",
            full_name="Elena Berger",
            role="protagonist",
            introduced_in="story_001",
            current_status="In Beziehung mit Marco",
            known_facts=[
                "32 Jahre, Kunsthistorikerin",
                "Kürzlich geschieden",
                "Liebt Cava",
                "Hat Höhenangst überwunden",
            ],
            relationships={"Marco": "Partner", "Der Kurator": "Antagonist"},
        ),
        StoryCharacter(
            name="Marco",
            full_name="Marco Conti",
            role="love_interest",
            introduced_in="story_001",
            current_status="Partner von Elena",
            known_facts=[
                "35 Jahre, Journalist",
                "Italiener aus Rom",
                "Narbe am Handgelenk",
            ],
            relationships={"Elena": "Partnerin"},
        ),
    ]
    
    # Füge Location-Erinnerungen hinzu
    user_world.location_memories = [
        LocationMemory(
            location_id="barcelona",
            story_id="story_001",
            chapter=3,
            event="Elena und Marco begegneten sich zum ersten Mal am Strand von Barceloneta",
            characters_involved=["Elena", "Marco"],
            emotional_tone="romantic",
            can_reference=True,
        ),
        LocationMemory(
            location_id="barcelona",
            story_id="story_001",
            chapter=8,
            event="Erstes Date in El Xampanyet - der Abend, an dem alles begann",
            characters_involved=["Elena", "Marco"],
            emotional_tone="romantic",
            can_reference=True,
        ),
    ]
    
    # Speichern
    repo.save_user_world(user_world)
    print(f"  ✅ User World erstellt für: {user_world.user_id}")
    print(f"     Story-Universum: {user_world.story_universe_name}")
    print(f"     Charaktere: {len(user_world.characters)}")
    print(f"     Persönliche Orte: {len(user_world.personal_places)}")
    print(f"     Erinnerungen: {len(user_world.location_memories)}")
    
    print("\n     Charaktere:")
    for char in user_world.characters:
        print(f"       - {char.name} ({char.role}): {char.current_status}")
    
    print("\n     Persönliche Orte in Barcelona:")
    for pp in user_world.personal_places:
        status = "✓ verwenden" if pp.use_in_story else "✗ AUSSCHLUSS"
        print(f"       - {pp.name}: {status}")
        print(f"         \"{pp.note}\"")
    
    # ═══════════════════════════════════════════════════════════════
    # MERGE: Alle 3 Schichten kombinieren
    # ═══════════════════════════════════════════════════════════════
    
    print_section("MERGE: Alle 3 Schichten kombinieren")
    
    # Lade User World aus DB
    loaded_world = repo.get_user_world("user_demo_123")
    
    # Hole gemergete Location-Daten
    merged = generator.get_merged_location(
        city="Barcelona",
        country="Spanien",
        layer_type=LayerType.ROMANCE,
        user_world=loaded_world,
    )
    
    print(f"  ✅ Merged Location Data für Barcelona (Romance):")
    print(f"     Name: {merged.name}, {merged.country}")
    print(f"     Layer: {merged.layer_type.value}")
    print(f"     Orte (nach Filter): {len(merged.places)}")
    print(f"     Persönliche Orte: {len(merged.personal_places)}")
    print(f"     Ausschlüsse: {merged.excluded_places}")
    print(f"     Erinnerungen: {len(merged.location_memories)}")
    
    # ═══════════════════════════════════════════════════════════════
    # PROMPT CONTEXT: Für Story-Generator
    # ═══════════════════════════════════════════════════════════════
    
    print_section("PROMPT CONTEXT: Für Story-Generator")
    
    prompt_context = merged.to_prompt_context()
    
    print("\n  Generierter Prompt-Kontext:")
    print("  " + "-" * 50)
    # Zeige ersten Teil
    for line in prompt_context.split("\n")[:30]:
        print(f"  {line}")
    print("  ...")
    print("  " + "-" * 50)
    
    # ═══════════════════════════════════════════════════════════════
    # STATISTIKEN
    # ═══════════════════════════════════════════════════════════════
    
    print_section("Datenbank-Statistiken")
    
    stats = repo.get_stats()
    print(f"  Base Locations: {stats['base_locations']}")
    print(f"  Location Layers: {stats['location_layers']}")
    print(f"  User Worlds: {stats['user_worlds']}")
    print(f"  Cache Einträge: {stats['cache_entries']}")
    print(f"  Cache Hits: {stats['cache_hits']}")
    
    # Liste alle Locations
    print("\n  Verfügbare Locations:")
    for loc_id, name, country in repo.list_base_locations():
        layers = repo.get_layers_for_location(loc_id)
        layer_str = ", ".join(l.value for l in layers)
        print(f"    - {name} ({country})")
        if layers:
            print(f"      Layers: {layer_str}")


def demo_story_continuity():
    """
    Demo: Wie Kontinuität über mehrere Stories funktioniert.
    """
    print_header("📚 STORY-KONTINUITÄT DEMO")
    
    print("""
  SZENARIO:
  ─────────────────────────────────────────────────────────────
  User hat bereits 2 Stories mit Elena & Marco generiert.
  Jetzt plant sie eine dritte Reise nach Barcelona.
  
  Das System kennt:
  - Elena & Marco's Geschichte
  - Wo sie schon waren
  - Was dort passiert ist
  
  NEUE STORY KANN DARAUF AUFBAUEN:
  ─────────────────────────────────────────────────────────────
  
  Kapitel 3, Barcelona:
  
  "Elena stand wieder am Strand von Barceloneta. Hier hatte alles 
   angefangen - jene zufällige Begegnung vor zwei Jahren, als Marco 
   ihren Sonnenhut aufgefangen hatte, bevor der Wind ihn ins Meer 
   trug. Sie lächelte bei der Erinnerung.
   
   Heute war alles anders. Heute wusste sie, wer er wirklich war.
   Und heute hatte sie einen Ring in der Tasche..."
   
  → Das System weiß:
    - Barceloneta war Ort der ersten Begegnung (story_001, chapter 3)
    - Elena & Marco sind jetzt zusammen
    - Der emotionale Ton war "romantic"
    
  → Das ermöglicht:
    - Callback zu früheren Momenten
    - Charakter-Entwicklung zeigen
    - Emotionale Kontinuität
    """)


def demo_exclusion_system():
    """
    Demo: Wie Ausschlüsse funktionieren.
    """
    print_header("🚫 AUSSCHLUSS-SYSTEM DEMO")
    
    print("""
  SZENARIO:
  ─────────────────────────────────────────────────────────────
  User hat "Sagrada Familia" ausgeschlossen mit Notiz:
  "War dort mit Ex-Freund - bitte nicht verwenden"
  
  WAS PASSIERT:
  ─────────────────────────────────────────────────────────────
  
  1. Generator lädt Barcelona Romance-Layer
     → 8 romantische Orte inklusive "Sagrada Familia"
  
  2. Merge mit User World
     → Check excluded_places
     → "Sagrada Familia" wird ENTFERNT
  
  3. Story-Generator erhält
     → 7 Orte (ohne Sagrada Familia)
     → Explizite Anweisung: "NICHT VERWENDEN: Sagrada Familia"
  
  ERGEBNIS:
  ─────────────────────────────────────────────────────────────
  Die generierte Story erwähnt die Sagrada Familia nie.
  Stattdessen nutzt sie andere Wahrzeichen wie:
  - Bunkers del Carmel (Aussicht)
  - Palau de la Música (Kultur)
  - Barceloneta Strand (Romantik)
  
  → User kann entspannt lesen ohne negative Assoziationen
    """)


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Haupt-Demo
    demo_location_system()
    
    # Konzept-Demos
    demo_story_continuity()
    demo_exclusion_system()
    
    print_header("✅ DEMO ABGESCHLOSSEN")
    print("""
  Das Location-System bietet:
  
  ✓ On-Demand Generation (nur bei Bedarf)
  ✓ Shared Base (einmal generiert, für alle nutzbar)
  ✓ Genre-spezifische Layers (Romance ≠ Thriller)
  ✓ User-spezifische Personalisierung
  ✓ Story-Kontinuität über mehrere Bücher
  ✓ Ausschluss-System für sensible Orte
  ✓ Caching für Performance
  
  Nächste Schritte:
  → Integration mit Story-Generator
  → Echte LLM-Anbindung (statt Mock)
  → Web-Research für aktuelle Details
    """)
